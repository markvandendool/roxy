#!/usr/bin/env python3
"""
Train a custom 'Hey Roxy' wake word verifier using openWakeWord.
Requires positive samples (saying 'Hey Roxy') and negative samples (other speech).
"""
import os
from pathlib import Path
from openwakeword import train_custom_verifier

SAMPLES_DIR = Path('/opt/roxy/wakeword/samples')
POSITIVE_DIR = SAMPLES_DIR / 'positive'
NEGATIVE_DIR = SAMPLES_DIR / 'negative'
MODELS_DIR = Path('/opt/roxy/wakeword/models')

def count_wavs(directory):
    return len(list(Path(directory).glob('*.wav')))

def main():
    # Check samples
    pos_count = count_wavs(POSITIVE_DIR)
    neg_count = count_wavs(NEGATIVE_DIR)
    
    print(f'Positive samples (Hey Roxy): {pos_count}')
    print(f'Negative samples (other speech): {neg_count}')
    
    if pos_count < 5:
        print(f'\nError: Need at least 5 positive samples, found {pos_count}')
        print('Run: python3 record_samples.py positive')
        return
    
    if neg_count < 5:
        print(f'\nError: Need at least 5 negative samples, found {neg_count}')
        print('Run: python3 record_samples.py negative')
        return
    
    # Create output directory
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = MODELS_DIR / 'hey_roxy_verifier.joblib'
    
    print('\nTraining custom verifier model...')
    print('Using hey_jarvis as base model (phonetically similar)')
    print('This may take a few minutes...\n')
    
    # Train the custom verifier
    train_custom_verifier(
        positive_reference_clips=str(POSITIVE_DIR),
        negative_reference_clips=str(NEGATIVE_DIR),
        output_path=str(output_path),
        model_name='hey_jarvis'
    )
    
    print(f'\nModel saved to: {output_path}')
    print('\nTo use this model, update the Wyoming OpenWakeWord config.')
    print('The verifier improves false-positive rejection for your voice.')

if __name__ == '__main__':
    main()
