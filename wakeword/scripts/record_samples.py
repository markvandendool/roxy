#!/usr/bin/env python3
"""
Record samples for 'Hey Roxy' wake word training.
Usage:
  python3 record_samples.py positive   # Record 'Hey Roxy' samples
  python3 record_samples.py negative   # Record other speech samples
"""
import os
import sys
import time
import subprocess
from pathlib import Path

SAMPLES_DIR = Path('/opt/roxy/wakeword/samples')
SAMPLE_DURATION = 2  # seconds
NUM_SAMPLES = 15  # Number of samples to record per type

def record_sample(filename, duration=2):
    """Record a single audio sample using arecord."""
    cmd = [
        'arecord',
        '-D', 'plughw:9,0',  # USB Advanced Audio Device
        '-f', 'S16_LE',
        '-r', '16000',
        '-c', '1',
        '-d', str(duration),
        filename
    ]
    subprocess.run(cmd, check=True, capture_output=True)

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['positive', 'negative']:
        print('Usage: python3 record_samples.py [positive|negative]')
        print('  positive - Record "Hey Roxy" wake word samples')
        print('  negative - Record other speech (not wake word)')
        sys.exit(1)
    
    sample_type = sys.argv[1]
    output_dir = SAMPLES_DIR / sample_type
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Count existing samples
    existing = len(list(output_dir.glob('*.wav')))
    
    print('=' * 60)
    if sample_type == 'positive':
        print('POSITIVE SAMPLES: Say "Hey Roxy" for each recording')
        prefix = 'hey_roxy'
    else:
        print('NEGATIVE SAMPLES: Say random phrases (NOT "Hey Roxy")')
        print('Examples: "Hello there", "Good morning", "What time is it"')
        prefix = 'negative'
    print('=' * 60)
    print(f'\nExisting samples: {existing}')
    print(f'Will record {NUM_SAMPLES} more samples.')
    print()
    input('Press ENTER when ready to start...')
    
    for i in range(NUM_SAMPLES):
        sample_num = existing + i
        filename = output_dir / f'{prefix}_{sample_num:03d}.wav'
        print(f'\n[{i+1}/{NUM_SAMPLES}] Get ready...')
        time.sleep(1)
        if sample_type == 'positive':
            print('>>> SAY "HEY ROXY" NOW <<<')
        else:
            print('>>> SAY ANY PHRASE (not Hey Roxy) NOW <<<')
        try:
            record_sample(str(filename), SAMPLE_DURATION)
            print(f'Saved: {filename.name}')
        except Exception as e:
            print(f'Error recording: {e}')
        time.sleep(0.5)
    
    total = len(list(output_dir.glob('*.wav')))
    print('\n' + '=' * 60)
    print(f'Recording complete! Total {sample_type} samples: {total}')
    print('=' * 60)
    
    # Show next step
    pos_count = len(list((SAMPLES_DIR / 'positive').glob('*.wav')))
    neg_count = len(list((SAMPLES_DIR / 'negative').glob('*.wav')))
    print(f'\nProgress: {pos_count} positive, {neg_count} negative')
    if pos_count >= 5 and neg_count >= 5:
        print('\nReady to train! Run: python3 train_hey_roxy.py')
    elif sample_type == 'positive':
        print('\nNext: python3 record_samples.py negative')
    else:
        print('\nNext: python3 record_samples.py positive')

if __name__ == '__main__':
    main()
