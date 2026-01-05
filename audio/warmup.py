#!/usr/bin/env python3
"""
ROXY Pitch Detector Preload Service
Warms up GPU kernels on boot for instant pitch detection.

Run as systemd oneshot to eliminate cold start latency.
"""

import os
import sys
import time

# Ensure we're using the right GPU
os.environ['ROCR_VISIBLE_DEVICES'] = '1'  # RX 6900 XT

def warmup():
    """Warmup pitch detection models for instant response."""
    print("[WARMUP] Starting pitch detector warmup...")
    start = time.perf_counter()

    # Import and warmup TorchCrepe
    import torch
    import torchcrepe
    import numpy as np

    # Find the best GPU (RX 6900 XT if available)
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            name = torch.cuda.get_device_name(i)
            if "6900" in name:
                device = torch.device(f"cuda:{i}")
                break
        else:
            device = torch.device("cuda:0")
    else:
        device = torch.device("cpu")
    print(f"[WARMUP] Device: {device} ({torch.cuda.get_device_name(device) if device.type == 'cuda' else 'CPU'})")

    # Generate dummy audio
    dummy = torch.randn(1, 48000).to(device)

    # Run 5 warmup passes to compile all GPU kernels
    print("[WARMUP] Compiling GPU kernels (5 passes)...")
    for i in range(5):
        with torch.no_grad():
            torchcrepe.predict(
                dummy,
                48000,
                hop_length=512,
                model='tiny',
                device=device,
                return_periodicity=True,
            )
        print(f"[WARMUP] Pass {i+1}/5 complete")

    # Also warmup SwiftF0
    print("[WARMUP] Warming up SwiftF0...")
    from swift_f0 import SwiftF0
    detector = SwiftF0(fmin=50, fmax=1000, confidence_threshold=0.3)
    dummy_audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
    for i in range(3):
        detector.detect_from_array(dummy_audio, 16000)

    elapsed = time.perf_counter() - start
    print(f"[WARMUP] Complete in {elapsed:.1f}s - pitch detection ready!")

    # Write marker file for systemd
    with open('/tmp/roxy-pitch-warmed', 'w') as f:
        f.write(f"warmed_at={time.time()}\n")

    return 0


if __name__ == "__main__":
    sys.exit(warmup())
