#!/usr/bin/env python3
"""
Test the Hey Roxy wake word detection in real-time.
"""
import time
import numpy as np
from pathlib import Path
import sounddevice as sd
from scipy import signal
from openwakeword import Model, get_pretrained_model_paths

MODELS_DIR = Path('/opt/roxy/wakeword/models')
VERIFIER_PATH = MODELS_DIR / 'hey_roxy_verifier.joblib'

TARGET_RATE = 16000
CHUNK = 1280

frame_count = 0

def main():
    global frame_count
    
    print('=' * 60)
    print('HEY ROXY Wake Word Listener')
    print('=' * 60)
    
    model_paths = get_pretrained_model_paths()
    jarvis_path = next((p for p in model_paths if 'hey_jarvis' in p), None)
    
    if not jarvis_path:
        print('Error: hey_jarvis model not found')
        return
    
    print(f'Model: hey_jarvis')
    
    if VERIFIER_PATH.exists():
        print(f'Verifier: {VERIFIER_PATH.name}')
        model = Model(
            wakeword_model_paths=[jarvis_path],
            custom_verifier_models={'hey_jarvis_v0.1': str(VERIFIER_PATH)},
            custom_verifier_threshold=0.3
        )
    else:
        print('Verifier: none (base model)')
        model = Model(wakeword_model_paths=[jarvis_path])
    
    # Use pipewire
    devices = sd.query_devices()
    device_idx = next((i for i, d in enumerate(devices) if d['name'] == 'pipewire'), None)
    if device_idx is None:
        device_idx = sd.default.device[0]
    
    info = sd.query_devices(device_idx)
    native_rate = int(info['default_samplerate'])
    native_chunk = int(CHUNK * native_rate / TARGET_RATE)
    
    print(f'Device: pipewire @ {native_rate}Hz')
    print()
    print('>>> LISTENING - Say "Hey Jarvis" <<<')
    print('(Will show . every 50 frames to confirm active)')
    print()
    
    def audio_callback(indata, frames, time_info, status):
        global frame_count
        frame_count += 1
        
        if frame_count % 50 == 0:
            print('.', end='', flush=True)
        
        audio_float = indata[:, 0]
        if native_rate != TARGET_RATE:
            num_samples = int(len(audio_float) * TARGET_RATE / native_rate)
            audio_float = signal.resample(audio_float, num_samples)
        
        audio = (audio_float * 32767).astype(np.int16)
        prediction = model.predict(audio)
        
        for name, score in prediction.items():
            if score > 0.5:
                print(f'\n🎤 DETECTED! Score: {score:.2f}')
    
    try:
        with sd.InputStream(
            device=device_idx,
            channels=1,
            samplerate=native_rate,
            blocksize=native_chunk,
            dtype='float32',
            callback=audio_callback
        ):
            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print('\nDone.')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    main()
