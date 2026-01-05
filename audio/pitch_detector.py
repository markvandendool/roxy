#!/usr/bin/env python3
"""
Real-time pitch detection using TorchCrepe on AMD GPU (RX 6900 XT)
Target: <20ms latency for live music teaching
"""
import time
import numpy as np
import torch
import sys

# Force ROCm/HIP for AMD GPU
if torch.cuda.is_available():
    DEVICE = torch.device('cuda:0')  # RX 6900 XT (ROCR_VISIBLE_DEVICES=1 maps to cuda:0)
    print(f"🎯 Using GPU: {torch.cuda.get_device_name(0)}")
else:
    DEVICE = torch.device('cpu')
    print("⚠️ GPU not available, using CPU")

# Audio config
SAMPLE_RATE = 48000
BUFFER_SIZE = 1024  # ~21ms at 48kHz
HOP_SIZE = 512      # ~10.7ms between predictions

def load_crepe():
    """Load TorchCrepe model"""
    try:
        import torchcrepe
        print("✅ TorchCrepe loaded")
        return torchcrepe
    except ImportError:
        print("❌ TorchCrepe not installed. Run: pip install torchcrepe")
        return None

def hz_to_note(freq):
    """Convert frequency to note name"""
    if freq <= 0:
        return "---"
    A4 = 440.0
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    semitones = 12 * np.log2(freq / A4)
    note_num = int(round(semitones)) + 9  # A4 is 9 semitones above C4
    octave = 4 + (note_num // 12)
    note_idx = note_num % 12
    return f"{notes[note_idx]}{octave}"

def detect_pitch_batch(audio_buffer, crepe):
    """Detect pitch from audio buffer with timing"""
    start = time.perf_counter()
    
    # Convert to torch tensor
    audio = torch.tensor(audio_buffer, dtype=torch.float32, device=DEVICE).unsqueeze(0)
    
    # Run inference
    with torch.no_grad():
        pitch, confidence = crepe.predict(
            audio,
            SAMPLE_RATE,
            hop_length=HOP_SIZE,
            model='tiny',  # tiny/small/medium/large/full
            decoder=crepe.decode.viterbi,
            device=DEVICE,
            return_periodicity=True,
            batch_size=1
        )
    
    elapsed_ms = (time.perf_counter() - start) * 1000
    
    # Get dominant pitch
    conf_mask = confidence > 0.5
    if conf_mask.any():
        avg_pitch = pitch[conf_mask].mean().item()
        avg_conf = confidence[conf_mask].mean().item()
    else:
        avg_pitch = 0
        avg_conf = 0
    
    return avg_pitch, avg_conf, elapsed_ms

def benchmark(crepe, iterations=20):
    """Benchmark pitch detection latency"""
    print(f"\n🔬 Benchmarking {iterations} iterations...")
    
    # Synthetic audio (sine wave at A4)
    t = np.linspace(0, BUFFER_SIZE / SAMPLE_RATE, BUFFER_SIZE, dtype=np.float32)
    test_audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    
    latencies = []
    for i in range(iterations):
        pitch, conf, latency_ms = detect_pitch_batch(test_audio, crepe)
        latencies.append(latency_ms)
        if i < 5 or i == iterations - 1:
            note = hz_to_note(pitch)
            print(f"  [{i+1:2d}] {pitch:7.1f} Hz ({note:4s}) conf={conf:.2f} latency={latency_ms:.1f}ms")
    
    latencies = latencies[3:]  # Skip warmup
    print(f"\n📊 Results (excluding warmup):")
    print(f"   Min: {min(latencies):.1f}ms")
    print(f"   Max: {max(latencies):.1f}ms")
    print(f"   Avg: {np.mean(latencies):.1f}ms")
    print(f"   Std: {np.std(latencies):.1f}ms")
    
    target = 20.0
    if np.mean(latencies) < target:
        print(f"   ✅ PASS: Under {target}ms target!")
    else:
        print(f"   ❌ FAIL: Above {target}ms target")
    
    return np.mean(latencies)

def live_detection(crepe, duration=10):
    """Live pitch detection from microphone"""
    try:
        import sounddevice as sd
    except ImportError:
        print("❌ sounddevice not installed. Run: pip install sounddevice")
        return
    
    print(f"\n🎤 Live detection for {duration}s (speak/sing/play into mic)...")
    print("   Press Ctrl+C to stop\n")
    
    buffer = np.zeros(BUFFER_SIZE, dtype=np.float32)
    
    def callback(indata, frames, time_info, status):
        nonlocal buffer
        buffer = indata[:, 0].copy()
    
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback, blocksize=BUFFER_SIZE):
            start_time = time.time()
            while time.time() - start_time < duration:
                if np.abs(buffer).max() > 0.01:  # Only process if audio present
                    pitch, conf, latency = detect_pitch_batch(buffer, crepe)
                    if conf > 0.5:
                        note = hz_to_note(pitch)
                        bar = '█' * int(conf * 20)
                        print(f"\r  {note:4s} ({pitch:6.1f} Hz) {bar:20s} {latency:5.1f}ms", end='', flush=True)
                time.sleep(0.02)
    except KeyboardInterrupt:
        pass
    print("\n")

if __name__ == '__main__':
    crepe = load_crepe()
    if crepe is None:
        sys.exit(1)
    
    # Run benchmark
    avg_latency = benchmark(crepe)
    
    # Optional live test
    if len(sys.argv) > 1 and sys.argv[1] == '--live':
        live_detection(crepe)
    else:
        print("\nRun with --live for microphone test")
