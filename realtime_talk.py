#!/usr/bin/env python3
"""
ROXY Real-Time Talk - Ultra-Simple Voice Chat
Just start talking! Interrupt anytime!

This uses your existing ROXY infrastructure with expert routing.
"""

import asyncio
import numpy as np
import threading
import queue
import time
import sys
from pathlib import Path

# Audio
import pyaudio

# STT - prefer faster-whisper
try:
    from faster_whisper import WhisperModel
    WHISPER_TYPE = "faster"
except ImportError:
    import whisper
    WHISPER_TYPE = "openai"

# TTS - prefer edge-tts for quality, pyttsx3 as fallback
try:
    import edge_tts
    import sounddevice as sd
    from pydub import AudioSegment
    import io
    TTS_TYPE = "edge"
except ImportError:
    try:
        import pyttsx3
        TTS_TYPE = "pyttsx3"
    except ImportError:
        TTS_TYPE = "none"

# ROXY client
import requests


class RealtimeTalk:
    """
    Simple real-time voice conversation with ROXY.
    
    Features:
    - VAD-based speech detection
    - Whisper transcription
    - Expert routing via ROXY /expert endpoint
    - Interruptible TTS
    """
    
    def __init__(self):
        print("\n🔧 Initializing ROXY Real-Time Talk...")
        
        # Audio config
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 1024  # ~64ms at 16kHz
        self.format = pyaudio.paInt16
        
        # VAD config
        self.silence_threshold = 400  # Amplitude threshold
        self.min_speech_frames = 8    # ~0.5s minimum speech
        self.max_silence_frames = 24  # ~1.5s silence to end
        
        # State
        self.is_listening = False
        self.is_speaking = False
        self.should_stop = False
        self.speech_frames = []
        self.silence_count = 0
        self.audio_queue = queue.Queue()
        
        # PyAudio
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
        # Load Whisper model
        print(f"  Loading Whisper ({WHISPER_TYPE})...")
        if WHISPER_TYPE == "faster":
            self.whisper = WhisperModel(
                "tiny",
                device="cpu",
                compute_type="int8"
            )
        else:
            self.whisper = whisper.load_model("tiny")
        print(f"  ✓ Whisper ready ({WHISPER_TYPE})")
        
        # TTS setup
        print(f"  Setting up TTS ({TTS_TYPE})...")
        if TTS_TYPE == "pyttsx3":
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 180)
        self.tts_voice = "en-US-ChristopherNeural"  # Edge TTS voice
        print(f"  ✓ TTS ready ({TTS_TYPE})")
        
        # ROXY connection
        token_file = Path.home() / ".roxy" / "secret.token"
        self.roxy_token = token_file.read_text().strip() if token_file.exists() else ""
        self.roxy_url = "http://127.0.0.1:8766"
        print("  ✓ ROXY connection configured")
        
    def start(self):
        """Start the voice conversation"""
        print("\n" + "="*60)
        print("🎤 ROXY REAL-TIME TALK")
        print("="*60)
        print("Just start talking! I'll respond when you pause.")
        print("You can interrupt me anytime by speaking.")
        print("Say 'goodbye', 'exit', or 'quit' to stop.")
        print("Press Ctrl+C to force quit.")
        print("="*60)
        print("\n🟢 Listening...\n")
        
        # Start audio input stream
        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=self._audio_callback
        )
        
        self.stream.start_stream()
        
        try:
            # Run main loop
            asyncio.run(self._process_loop())
        finally:
            self._cleanup()
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Real-time audio input callback"""
        
        # Convert to numpy
        audio = np.frombuffer(in_data, dtype=np.int16)
        amplitude = np.abs(audio).mean()
        
        # Check for speech
        if amplitude > self.silence_threshold:
            # User is speaking!
            self.silence_count = 0
            
            # Interrupt TTS if playing
            if self.is_speaking:
                self._interrupt_tts()
            
            # Accumulate speech
            self.speech_frames.append(audio)
            
            if not self.is_listening:
                self.is_listening = True
                print("\r🔴 Listening...           ", end="", flush=True)
        else:
            # Silence
            if self.is_listening:
                self.silence_count += 1
                self.speech_frames.append(audio)  # Include trailing silence
                
                if self.silence_count >= self.max_silence_frames:
                    # End of utterance
                    if len(self.speech_frames) >= self.min_speech_frames:
                        # Queue for processing
                        audio_data = np.concatenate(self.speech_frames)
                        self.audio_queue.put(audio_data)
                    
                    self.speech_frames = []
                    self.silence_count = 0
                    self.is_listening = False
        
        return (None, pyaudio.paContinue)
    
    def _interrupt_tts(self):
        """Stop TTS playback"""
        if self.is_speaking:
            print("\n🔴 [Interrupted!]")
            self.is_speaking = False
            if TTS_TYPE == "pyttsx3":
                self.tts_engine.stop()
            elif TTS_TYPE == "edge":
                sd.stop()
    
    async def _process_loop(self):
        """Main processing loop"""
        
        while not self.should_stop:
            try:
                # Get audio from queue
                audio_data = self.audio_queue.get(timeout=0.1)
                
                print("\r🟡 Processing...          ", end="", flush=True)
                
                # Transcribe
                text = self._transcribe(audio_data)
                
                if not text or len(text.strip()) < 2:
                    print("\r🟢 Listening...           ", end="", flush=True)
                    continue
                
                print(f"\r👤 You: {text}")
                
                # Check for exit
                if any(word in text.lower() for word in ['goodbye', 'exit', 'quit', 'stop listening']):
                    await self._speak("Goodbye! Talk to you later.")
                    self.should_stop = True
                    break
                
                # Get ROXY response
                response, expert = await self._query_roxy(text)
                
                print(f"🤖 ROXY [{expert}]: {response}")
                
                # Speak response
                await self._speak(response)
                
                print("\r🟢 Listening...           ", end="", flush=True)
                
            except queue.Empty:
                await asyncio.sleep(0.01)
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("\r🟢 Listening...           ", end="", flush=True)
    
    def _transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio with Whisper"""
        
        # Convert to float32
        audio_float = audio.astype(np.float32) / 32768.0
        
        if WHISPER_TYPE == "faster":
            segments, _ = self.whisper.transcribe(
                audio_float,
                language="en",
                beam_size=1,
                vad_filter=True
            )
            return " ".join([s.text for s in segments]).strip()
        else:
            result = self.whisper.transcribe(
                audio_float,
                language="en",
                fp16=False
            )
            return result["text"].strip()
    
    async def _query_roxy(self, text: str) -> tuple:
        """Query ROXY with expert routing"""
        
        headers = {
            "X-ROXY-Token": self.roxy_token,
            "Content-Type": "application/json"
        }
        
        try:
            # Try expert endpoint first
            r = requests.post(
                f"{self.roxy_url}/expert",
                headers=headers,
                json={"query": text},
                timeout=30
            )
            
            if r.status_code == 200:
                data = r.json()
                return (
                    data.get("response", "I'm not sure how to answer that."),
                    data.get("query_type", "general")
                )
        except:
            pass
        
        # Fallback to /run endpoint
        try:
            r = requests.post(
                f"{self.roxy_url}/run",
                headers=headers,
                json={"command": text},
                timeout=30
            )
            
            if r.status_code == 200:
                data = r.json()
                return (
                    data.get("response", data.get("result", str(data))),
                    "fallback"
                )
        except Exception as e:
            return (f"Sorry, I had trouble connecting: {e}", "error")
        
        return ("I'm having trouble thinking right now.", "error")
    
    async def _speak(self, text: str):
        """Speak text with interruption support"""
        
        if not text.strip():
            return
        
        self.is_speaking = True
        
        try:
            if TTS_TYPE == "edge":
                await self._speak_edge(text)
            elif TTS_TYPE == "pyttsx3":
                self._speak_pyttsx3(text)
            else:
                print(f"🔊 {text}")
        except Exception as e:
            print(f"⚠️ TTS error: {e}")
        finally:
            self.is_speaking = False
    
    async def _speak_edge(self, text: str):
        """Speak using Edge TTS (high quality)"""
        
        communicate = edge_tts.Communicate(text, self.tts_voice, rate="+10%")
        audio_data = b""
        
        async for chunk in communicate.stream():
            if not self.is_speaking:  # Interrupted
                return
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        
        if not self.is_speaking:
            return
        
        # Play audio
        try:
            audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
            samples = np.array(audio.get_array_of_samples()).astype(np.float32) / 32768.0
            sd.play(samples, samplerate=audio.frame_rate)
            
            # Wait for playback with interruption check
            while sd.get_stream().active and self.is_speaking:
                await asyncio.sleep(0.1)
        except Exception as e:
            print(f"⚠️ Audio playback error: {e}")
    
    def _speak_pyttsx3(self, text: str):
        """Speak using pyttsx3 (offline)"""
        
        # Split into sentences for interruptibility
        sentences = text.replace('!', '.').replace('?', '.').split('.')
        
        for sentence in sentences:
            if not sentence.strip() or not self.is_speaking:
                break
            
            self.tts_engine.say(sentence)
            self.tts_engine.runAndWait()
    
    def _cleanup(self):
        """Clean up resources"""
        print("\n\n👋 Shutting down...")
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        self.audio.terminate()
        print("✓ Audio closed")


def main():
    """Main entry point"""
    
    # Check ROXY is running
    try:
        token_file = Path.home() / ".roxy" / "secret.token"
        token = token_file.read_text().strip() if token_file.exists() else ""
        
        r = requests.get(
            "http://127.0.0.1:8766/health",
            headers={"X-ROXY-Token": token},
            timeout=5
        )
        
        if r.status_code != 200:
            print("❌ ROXY is not responding. Start it first:")
            print("   systemctl --user start roxy-core")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Cannot connect to ROXY: {e}")
        print("   Make sure ROXY is running: systemctl --user status roxy-core")
        sys.exit(1)
    
    # Start conversation
    talk = RealtimeTalk()
    talk.start()


if __name__ == "__main__":
    main()
