#!/usr/bin/env python3
"""
ROXY Voice Pipeline
Wake Word -> STT -> Command Processing -> TTS Response
"""
import asyncio
import json
import logging
from typing import Callable, Optional
import pyaudio
import numpy as np
import wave
import tempfile
import os

from wakeword.detector import WakeWordDetector
from transcription.client import WhisperClient
from tts.service import RoxyTTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Audio config
SAMPLE_RATE = 16000
CHUNK_SIZE = 1280
RECORD_SECONDS = 5  # Max recording after wake word

class VoicePipeline:
    def __init__(self, command_handler: Optional[Callable] = None):
        self.command_handler = command_handler or self.default_handler
        self.tts = RoxyTTS('roxy')
        self.stt = WhisperClient()
        self.wake_detector = WakeWordDetector(
            callback=self._on_wake_word,
            threshold=0.5
        )
        self.listening_for_command = False
        self.running = False
        
    async def default_handler(self, command: str) -> str:
        """Default command handler - just echo back"""
        return f"I heard you say: {command}"
    
    async def _on_wake_word(self, model: str, score: float):
        """Called when wake word is detected"""
        if self.listening_for_command:
            return
            
        logger.info(f'🎤 Wake word detected! Listening for command...')
        self.listening_for_command = True
        
        try:
            # Play acknowledgment sound (beep)
            self.tts.speak('Yes?')
            
            # Record command audio
            audio_path = await self._record_command()
            
            if audio_path:
                # Transcribe
                logger.info('Transcribing...')
                text = await self.stt.transcribe(audio_path)
                logger.info(f'Heard: "{text}"')
                
                if text and text.strip():
                    # Process command
                    response = await self.command_handler(text)
                    
                    # Speak response
                    if response:
                        self.tts.speak(response)
                else:
                    self.tts.speak('Sorry, I didn\'t catch that.')
                    
                os.unlink(audio_path)
                
        except Exception as e:
            logger.error(f'Pipeline error: {e}')
            self.tts.speak('Sorry, something went wrong.')
        finally:
            self.listening_for_command = False
    
    async def _record_command(self, timeout: float = RECORD_SECONDS) -> Optional[str]:
        """Record audio for command after wake word"""
        p = pyaudio.PyAudio()
        frames = []
        
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE
            )
            
            logger.info(f'Recording for {timeout}s...')
            
            # Record for timeout seconds or until silence
            chunks_to_record = int(SAMPLE_RATE * timeout / CHUNK_SIZE)
            silent_chunks = 0
            
            for i in range(chunks_to_record):
                data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                frames.append(data)
                
                # Simple silence detection
                audio = np.frombuffer(data, dtype=np.int16)
                volume = np.abs(audio).mean()
                
                if volume < 500:  # Silence threshold
                    silent_chunks += 1
                    if silent_chunks > 20:  # ~1.5s of silence
                        logger.info('Silence detected, stopping recording')
                        break
                else:
                    silent_chunks = 0
                    
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
        
        if not frames:
            return None
            
        # Save to WAV file
        wav_path = tempfile.mktemp(suffix='.wav')
        with wave.open(wav_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b''.join(frames))
            
        return wav_path
    
    async def start(self):
        """Start the voice pipeline"""
        self.running = True
        logger.info('Starting ROXY voice pipeline...')
        
        # Announce ready
        self.tts.speak('Roxy is ready.')
        
        # Start wake word detection
        await self.wake_detector.listen()
    
    def stop(self):
        self.running = False
        self.wake_detector.stop()


async def demo_command_handler(command: str) -> str:
    """Demo command handler"""
    command_lower = command.lower()
    
    if 'time' in command_lower:
        from datetime import datetime
        now = datetime.now()
        return f'The time is {now.strftime("%I:%M %p")}'
        
    elif 'weather' in command_lower:
        return 'I don\'t have weather integration yet, but it\'s probably nice outside!'
        
    elif 'hello' in command_lower or 'hi' in command_lower:
        return 'Hello! How can I help you?'
        
    elif 'thank' in command_lower:
        return 'You\'re welcome!'
        
    elif 'name' in command_lower:
        return 'I\'m Roxy, your AI assistant.'
        
    else:
        return f'I heard: {command}. Command processing coming soon!'


async def main():
    print('=' * 60)
    print('ROXY Voice Pipeline')
    print('Say "Hey Jarvis" to activate (interim wake word)')
    print('Press Ctrl+C to stop')
    print('=' * 60)
    
    pipeline = VoicePipeline(command_handler=demo_command_handler)
    
    try:
        await pipeline.start()
    except KeyboardInterrupt:
        pipeline.stop()
        print('\nStopped.')


if __name__ == '__main__':
    asyncio.run(main())
