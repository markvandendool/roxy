#!/usr/bin/env python3
"""
ROXY STT Client - LUNA-S3
Connects to Wyoming-Whisper for speech-to-text
"""

import asyncio
import wave
import io
from pathlib import Path

# Wyoming protocol client
WHISPER_HOST = 'localhost'
WHISPER_PORT = 10300

async def transcribe_audio(audio_path: str) -> dict:
    """Transcribe audio file using Wyoming-Whisper."""
    import socket
    import json
    
    # Read audio file
    with open(audio_path, 'rb') as f:
        audio_data = f.read()
    
    # Connect to Wyoming-Whisper
    reader, writer = await asyncio.open_connection(WHISPER_HOST, WHISPER_PORT)
    
    try:
        # Send transcribe request (Wyoming protocol)
        request = {
            'type': 'transcribe',
            'data': {'wav_bytes': len(audio_data)}
        }
        writer.write(json.dumps(request).encode() + b'\n')
        writer.write(audio_data)
        await writer.drain()
        
        # Read response
        response = await reader.readline()
        result = json.loads(response.decode())
        return result
    finally:
        writer.close()
        await writer.wait_closed()

async def transcribe_microphone(duration_sec: int = 5) -> dict:
    """Record from microphone and transcribe."""
    import subprocess
    import tempfile
    
    # Record audio using arecord
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        temp_path = f.name
    
    try:
        subprocess.run([
            'arecord', '-d', str(duration_sec),
            '-f', 'S16_LE', '-r', '16000', '-c', '1',
            temp_path
        ], check=True, capture_output=True)
        
        return await transcribe_audio(temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)

if __name__ == '__main__':
    print('🎤 ROXY STT Client')
    print(f'   Whisper: {WHISPER_HOST}:{WHISPER_PORT}')
