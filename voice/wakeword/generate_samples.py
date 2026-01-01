#!/usr/bin/env python3
"""Generate wake word training samples using Wyoming-Piper."""

import asyncio
import json
import wave
import struct
from pathlib import Path

PIPER_HOST = 'localhost'
PIPER_PORT = 10200
OUTPUT_DIR = Path('/opt/roxy/voice/wakeword/samples')

# Wake word variations
POSITIVE_PHRASES = [
    'Hey Roxy', 'Hey Roxy', 'Hey Roxy',  # Core phrase
    'hey roxy', 'HEY ROXY', 'Hey roxy',
    'Hey Roxie', 'hey roxie',
    'Hay Roxy', 'hay roxy',
]

# Negative samples (should NOT trigger)
NEGATIVE_PHRASES = [
    'Hello there', 'Hey Google', 'Hey Siri', 'Alexa',
    'Hey Rocky', 'Proxy server', 'Foxy lady',
    'Okay computer', 'Hey assistant',
    'The weather today', 'Play some music',
]

async def synthesize(text: str, output_path: Path):
    """Synthesize speech using Wyoming-Piper."""
    reader, writer = await asyncio.open_connection(PIPER_HOST, PIPER_PORT)
    
    try:
        # Wyoming synthesize request
        request = {'type': 'synthesize', 'data': {'text': text}}
        writer.write(json.dumps(request).encode() + b'\n')
        await writer.drain()
        
        # Read response header
        header = await reader.readline()
        info = json.loads(header.decode())
        
        # Read audio data
        audio_len = info.get('data', {}).get('wav_bytes', 0)
        if audio_len > 0:
            audio_data = await reader.read(audio_len)
            output_path.write_bytes(audio_data)
            return True
        return False
    except Exception as e:
        print(f'Error: {e}')
        return False
    finally:
        writer.close()
        await writer.wait_closed()

async def main():
    print('Generating positive samples...')
    pos_dir = OUTPUT_DIR / 'positive'
    for i, phrase in enumerate(POSITIVE_PHRASES):
        path = pos_dir / f'hey_roxy_{i:03d}.wav'
        if await synthesize(phrase, path):
            print(f'  ✅ {path.name}: "{phrase}"')
        else:
            print(f'  ❌ Failed: "{phrase}"')
    
    print('\nGenerating negative samples...')
    neg_dir = OUTPUT_DIR / 'negative'
    for i, phrase in enumerate(NEGATIVE_PHRASES):
        path = neg_dir / f'negative_{i:03d}.wav'
        if await synthesize(phrase, path):
            print(f'  ✅ {path.name}: "{phrase}"')
        else:
            print(f'  ❌ Failed: "{phrase}"')
    
    pos_count = len(list(pos_dir.glob('*.wav')))
    neg_count = len(list(neg_dir.glob('*.wav')))
    print(f'\n📊 Generated {pos_count} positive, {neg_count} negative samples')

if __name__ == '__main__':
    asyncio.run(main())
