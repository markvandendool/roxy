#!/usr/bin/env python3
"""
ROXY Voice Assistant - Full voice loop demo
Uses: OpenWakeWord → Whisper → Ollama → Piper
"""
import os
import sys
import wave
import subprocess
import requests
import json
from pathlib import Path

# Configuration
OLLAMA_URL = 'http://127.0.0.1:11435/api/generate'
MODEL = 'llama3.2:1b'
MIC_DEVICE = 'hw:2,0'
SAMPLE_RATE = 16000
RECORD_SECONDS = 5

def record_audio(output_file: str, seconds: int = RECORD_SECONDS) -> bool:
    """Record audio from OWC Thunderbolt mic"""
    cmd = f'arecord -D {MIC_DEVICE} -d {seconds} -f S16_LE -r {SAMPLE_RATE} {output_file}'
    try:
        subprocess.run(cmd.split(), check=True, capture_output=True)
        return True
    except:
        return False

def transcribe_audio(audio_file: str) -> str:
    """Send audio to Whisper for transcription (placeholder)"""
    # In production, this would use Wyoming protocol
    # For demo, we simulate with a test phrase
    return 'Hello Roxy, what time is it?'

def get_llm_response(prompt: str) -> str:
    """Get response from Ollama"""
    try:
        response = requests.post(OLLAMA_URL, json={
            'model': MODEL,
            'prompt': f'You are Roxy, a helpful AI assistant. Respond briefly. User: {prompt}',
            'stream': False
        }, timeout=30)
        return response.json().get('response', 'I could not process that.')
    except Exception as e:
        return f'Error: {e}'

def speak_response(text: str) -> bool:
    """Use Piper TTS to speak (placeholder)"""
    print(f'[TTS] {text}')
    return True

def main():
    print('=== ROXY Voice Assistant ===')
    print('Say "Hey Roxy" to activate (using hey_roxy for now)')
    print('')
    
    # Demo flow
    print('[1] Recording 3 seconds of audio...')
    audio_file = '/tmp/roxy_input.wav'
    if record_audio(audio_file, 3):
        print('    ✅ Audio recorded')
    else:
        print('    ❌ Recording failed')
        return
    
    print('[2] Transcribing with Whisper...')
    transcript = transcribe_audio(audio_file)
    print(f'    Heard: "{transcript}"')
    
    print('[3] Getting response from Ollama...')
    response = get_llm_response(transcript)
    print(f'    Response: {response[:100]}...')
    
    print('[4] Speaking response with Piper...')
    speak_response(response)
    
    print('')
    print('=== Demo Complete ===')

if __name__ == '__main__':
    main()
