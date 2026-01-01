#!/usr/bin/env python3
"""
ROXY Text-to-Speech Service
Uses Piper TTS for fast, high-quality voice synthesis
"""
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_DIR = Path('/opt/roxy/voice/tts/models')

# Voice profiles - different personas/moods
VOICES = {
    'roxy': {
        'model': 'en_US-libritts_r-medium.onnx',
        'speaker': 0,  # Will tune this for best female voice
        'description': 'Roxy - friendly AI assistant'
    },
    'amy': {
        'model': 'en_US-amy-medium.onnx', 
        'speaker': 0,
        'description': 'Amy - clear, professional'
    },
    'kusal': {
        'model': 'en_US-kusal-medium.onnx',
        'speaker': 0, 
        'description': 'Kusal - warm, friendly'
    }
}

class RoxyTTS:
    def __init__(self, voice: str = 'roxy'):
        self.set_voice(voice)
        
    def set_voice(self, voice: str):
        if voice not in VOICES:
            raise ValueError(f'Unknown voice: {voice}. Available: {list(VOICES.keys())}')
        self.voice_config = VOICES[voice]
        self.model_path = MODEL_DIR / self.voice_config['model']
        self.config_path = self.model_path.with_suffix('.onnx.json')
        
        if not self.model_path.exists():
            raise FileNotFoundError(f'Voice model not found: {self.model_path}')
        
        # Load config to find available speakers
        if self.config_path.exists():
            with open(self.config_path) as f:
                config = json.load(f)
                self.num_speakers = config.get('num_speakers', 1)
                logger.info(f'Loaded voice: {voice} ({self.num_speakers} speakers)')
        else:
            self.num_speakers = 1
            
    def synthesize(self, text: str, output_path: Optional[str] = None, 
                   speaker: Optional[int] = None) -> str:
        """Convert text to speech, return path to audio file"""
        if output_path is None:
            output_path = tempfile.mktemp(suffix='.wav')
            
        speaker = speaker if speaker is not None else self.voice_config['speaker']
        
        cmd = [
            'piper',
            '--model', str(self.model_path),
            '--output_file', output_path,
        ]
        
        if self.num_speakers > 1:
            cmd.extend(['--speaker', str(speaker)])
        
        try:
            result = subprocess.run(
                cmd,
                input=text,
                text=True,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f'Piper error: {result.stderr}')
                raise RuntimeError(f'TTS failed: {result.stderr}')
                
            logger.info(f'Synthesized: "{text[:50]}..." -> {output_path}')
            return output_path
            
        except subprocess.TimeoutExpired:
            raise RuntimeError('TTS synthesis timed out')
    
    def speak(self, text: str, speaker: Optional[int] = None):
        """Synthesize and play audio immediately"""
        wav_path = self.synthesize(text, speaker=speaker)
        try:
            # Play using aplay (ALSA)
            subprocess.run(['aplay', '-q', wav_path], check=True, timeout=60)
        finally:
            os.unlink(wav_path)
    
    def list_voices(self):
        """List available voice configurations"""
        return VOICES


async def main():
    import asyncio
    
    tts = RoxyTTS('roxy')
    
    print('=' * 50)
    print('ROXY TTS Service Test')
    print('=' * 50)
    
    # Test libritts with different speakers
    print('\nTesting libritts_r speakers...')
    for speaker_id in [0, 1, 2, 100, 200]:
        print(f'  Speaker {speaker_id}...')
        try:
            tts.speak(f'Hello, I am Roxy, your AI assistant. This is speaker {speaker_id}.', speaker=speaker_id)
        except Exception as e:
            print(f'    Error: {e}')
            break


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
