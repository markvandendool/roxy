#!/usr/bin/env python3
"""Generate synthetic wake word samples using Piper TTS"""

import subprocess
import os
from pathlib import Path

WAKE_DIR = Path.home() / '.roxy' / 'wake' / 'hey_roxy'
POSITIVE_DIR = WAKE_DIR / 'positive'
NEGATIVE_DIR = WAKE_DIR / 'negative'

# Positive samples - variations of "Hey Roxy"
POSITIVE_PHRASES = [
    'Hey Roxy',
    'Hey Roxy!',
    'Hey, Roxy',
    'hey roxy',
    'Hey Roxy?',
]

# Negative samples - similar but NOT the wake phrase
NEGATIVE_PHRASES = [
    'Hey Rocky',
    'Hey Roxie',
    'Hey proxy',
    'Hey foxy',
    'okay',
    'hey',
    'hello',
    'hi there',
    'hey siri',
    'alexa',
    'hey google',
]

PIPER_BIN = str(Path.home() / '.local' / 'bin' / 'piper')
VOICE_MODEL = str(Path.home() / '.roxy' / 'voices' / 'en_US-lessac-medium.onnx')

def generate_sample(text: str, output_path: Path, speed: float = 1.0):
    """Generate a single audio sample using Piper"""
    cmd = [
        PIPER_BIN,
        '--model', VOICE_MODEL,
        '--output_file', str(output_path),
    ]
    
    try:
        result = subprocess.run(
            cmd,
            input=text.encode(),
            capture_output=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f'✓ Generated: {output_path.name}')
            return True
        else:
            print(f'✗ Failed: {text} - {result.stderr.decode()}')
            return False
    except Exception as e:
        print(f'✗ Error: {text} - {e}')
        return False

def main():
    print('=== Generating Wake Word Training Samples ===')
    print(f'Piper binary: {PIPER_BIN}')
    print(f'Voice model: {VOICE_MODEL}')
    
    # Generate positive samples
    print(f'\n--- Positive Samples (Hey Roxy) ---')
    for i, phrase in enumerate(POSITIVE_PHRASES):
        output = POSITIVE_DIR / f'hey_roxy_{i:03d}.wav'
        generate_sample(phrase, output)
    
    # Generate negative samples
    print(f'\n--- Negative Samples (Not Hey Roxy) ---')
    for i, phrase in enumerate(NEGATIVE_PHRASES):
        output = NEGATIVE_DIR / f'negative_{i:03d}.wav'
        generate_sample(phrase, output)
    
    # Count results
    pos_count = len(list(POSITIVE_DIR.glob('*.wav')))
    neg_count = len(list(NEGATIVE_DIR.glob('*.wav')))
    
    print(f'\n=== Summary ===')
    print(f'Positive samples: {pos_count}')
    print(f'Negative samples: {neg_count}')
    print(f'Total: {pos_count + neg_count}')

if __name__ == '__main__':
    main()
