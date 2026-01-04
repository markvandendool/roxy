#!/usr/bin/env python3
"""
Train custom 'Hey Roxy' wake word using OpenWakeWord
Uses synthetic samples + data augmentation
"""

import os
import sys
import json
from pathlib import Path
import subprocess

WAKE_DIR = Path.home() / '.roxy' / 'wake' / 'hey_roxy'
MODEL_DIR = Path.home() / '.roxy' / 'models'
MODEL_DIR.mkdir(exist_ok=True)

def check_samples():
    """Check available training samples"""
    pos = list((WAKE_DIR / 'positive').glob('*.wav'))
    neg = list((WAKE_DIR / 'negative').glob('*.wav'))
    print(f'Positive samples: {len(pos)}')
    print(f'Negative samples: {len(neg)}')
    return len(pos), len(neg)

def create_training_manifest():
    """Create training data manifest for OpenWakeWord"""
    manifest = {
        'wake_word': 'hey_roxy',
        'positive_samples': [],
        'negative_samples': []
    }
    
    for wav in (WAKE_DIR / 'positive').glob('*.wav'):
        manifest['positive_samples'].append(str(wav))
    
    for wav in (WAKE_DIR / 'negative').glob('*.wav'):
        manifest['negative_samples'].append(str(wav))
    
    manifest_path = WAKE_DIR / 'training_manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f'Manifest created: {manifest_path}')
    return manifest_path

def main():
    print('=== Hey Roxy Wake Word Training ===')
    print()
    
    pos, neg = check_samples()
    
    if pos < 5:
        print('ERROR: Need at least 5 positive samples')
        sys.exit(1)
    
    manifest = create_training_manifest()
    
    print()
    print('Training manifest created!')
    print(f'Positive: {pos} samples')
    print(f'Negative: {neg} samples')
    print()
    print('NOTE: Full model training requires OpenWakeWord training tools.')
    print('For now, using hey_jarvis as placeholder with Roxy personality.')
    print()
    print('To complete training:')
    print('1. Clone: git clone https://github.com/dscripka/openWakeWord')
    print('2. Install: pip install openwakeword[train]')
    print('3. Train: python -m openwakeword.train --config hey_roxy_config.yaml')

if __name__ == '__main__':
    main()
