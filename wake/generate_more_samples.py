#!/usr/bin/env python3
"""Generate more wake word samples with expanded variations"""

import subprocess
from pathlib import Path
import random

WAKE_DIR = Path.home() / '.roxy' / 'wake' / 'hey_roxy'
POSITIVE_DIR = WAKE_DIR / 'positive'
NEGATIVE_DIR = WAKE_DIR / 'negative'

PIPER_BIN = str(Path.home() / '.local' / 'bin' / 'piper')
VOICE_MODEL = str(Path.home() / '.roxy' / 'voices' / 'en_US-lessac-medium.onnx')

# Extended positive samples
POSITIVE_EXTENDED = [
    'Hey Roxy',
    'Hey Roxy!',
    'Hey, Roxy',
    'hey roxy',
    'Hey Roxy?',
    'Hey Roxy.',
    'hey, roxy',
    'HEY ROXY',
    'Hey roxy',
    'hey Roxy',
    'Hey  Roxy',  # extra space
    'Heyyy Roxy',
    'Hey Roxy, please',
    'Hey Roxy, can you',
    'Hey Roxy, what is',
]

# Extended negative samples - confusable words
NEGATIVE_EXTENDED = [
    'Hey Rocky',
    'Hey Roxie',
    'Hey proxy',
    'Hey foxy',
    'Hey Moxy',
    'Hey boxy',
    'okay',
    'hey',
    'hello',
    'hi there',
    'hey siri',
    'alexa',
    'hey google',
    'hey cortana',
    'roxy',  # just the name
    'roxanne',
    'rocky road',
    'hey there',
    'hey you',
    'hay',
    'hooray',
    'hey rocky balboa',
    'proxy server',
    'foxy lady',
    'what',
    'huh',
    'sorry',
    'excuse me',
    'pardon',
    'never mind',
]

def generate_sample(text: str, output_path: Path):
    cmd = [PIPER_BIN, '--model', VOICE_MODEL, '--output_file', str(output_path)]
    try:
        result = subprocess.run(cmd, input=text.encode(), capture_output=True, timeout=10)
        return result.returncode == 0
    except:
        return False

def main():
    print('=== Generating Extended Wake Word Samples ===')
    
    # Start numbering after existing files
    existing_pos = len(list(POSITIVE_DIR.glob('*.wav')))
    existing_neg = len(list(NEGATIVE_DIR.glob('*.wav')))
    
    new_pos = 0
    for i, phrase in enumerate(POSITIVE_EXTENDED):
        output = POSITIVE_DIR / f'hey_roxy_{existing_pos + i:03d}.wav'
        if not output.exists():
            if generate_sample(phrase, output):
                new_pos += 1
                print(f'✓ {phrase}')
    
    new_neg = 0
    for i, phrase in enumerate(NEGATIVE_EXTENDED):
        output = NEGATIVE_DIR / f'negative_{existing_neg + i:03d}.wav'
        if not output.exists():
            if generate_sample(phrase, output):
                new_neg += 1
                print(f'✓ {phrase}')
    
    total_pos = len(list(POSITIVE_DIR.glob('*.wav')))
    total_neg = len(list(NEGATIVE_DIR.glob('*.wav')))
    
    print(f'\n=== Summary ===')
    print(f'New positive: {new_pos}, New negative: {new_neg}')
    print(f'Total positive: {total_pos}, Total negative: {total_neg}')
    print(f'Grand total: {total_pos + total_neg} samples')

if __name__ == '__main__':
    main()
