#!/usr/bin/env python3
"""
Rocky Audio - Pitch Detector Stress Test
Tests: latency stability, memory usage, concurrent loads, edge cases

Usage:
    python stress_test.py                    # Full stress test suite
    python stress_test.py --quick            # Quick 30-second test
    python stress_test.py --duration 300     # 5-minute endurance test
"""

import asyncio
import argparse
import gc
import os
import sys
import time
import tracemalloc
from dataclasses import dataclass, field
from typing import Optional
import numpy as np

# Add parent to path for pitch_detector import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pitch_detector import RockyPitchDetector, PitchResult


@dataclass
class StressTestMetrics:
    """Aggregated stress test results."""
    total_inferences: int = 0
    successful_inferences: int = 0
    failed_inferences: int = 0

    # Latency stats
    latencies_ms: list = field(default_factory=list)
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0

    # Memory stats
    initial_memory_mb: float = 0
    peak_memory_mb: float = 0
    final_memory_mb: float = 0

    # Accuracy stats
    correct_detections: int = 0  # Within 50 cents of target
    octave_errors: int = 0
    gross_errors: int = 0  # >1 semitone off

    # Timing
    start_time: float = 0
    end_time: float = 0

    # Edge cases
    silence_correctly_rejected: int = 0
    noise_correctly_rejected: int = 0
    low_freq_accuracy: float = 0  # E2 (82.4Hz)
    high_freq_accuracy: float = 0  # E6 (1319Hz)

    def calculate_stats(self):
        """Calculate aggregate statistics."""
        if not self.latencies_ms:
            return

        arr = np.array(self.latencies_ms)
        return {
            'total_inferences': self.total_inferences,
            'success_rate': self.successful_inferences / max(1, self.total_inferences) * 100,
            'latency_avg_ms': np.mean(arr),
            'latency_std_ms': np.std(arr),
            'latency_min_ms': self.min_latency_ms,
            'latency_max_ms': self.max_latency_ms,
            'latency_p50_ms': np.percentile(arr, 50),
            'latency_p95_ms': np.percentile(arr, 95),
            'latency_p99_ms': np.percentile(arr, 99),
            'jitter_ms': np.std(arr),  # Latency variance
            'memory_initial_mb': self.initial_memory_mb,
            'memory_peak_mb': self.peak_memory_mb,
            'memory_final_mb': self.final_memory_mb,
            'memory_leak_mb': self.final_memory_mb - self.initial_memory_mb,
            'accuracy_rate': self.correct_detections / max(1, self.successful_inferences) * 100,
            'octave_error_rate': self.octave_errors / max(1, self.successful_inferences) * 100,
            'gross_error_rate': self.gross_errors / max(1, self.successful_inferences) * 100,
            'duration_seconds': self.end_time - self.start_time,
            'throughput_hz': self.total_inferences / max(0.001, self.end_time - self.start_time),
        }


class PitchDetectorStressTest:
    """Comprehensive stress testing for pitch detection."""

    # Standard guitar/voice frequencies for testing
    TEST_FREQUENCIES = [
        82.41,   # E2 (low E string)
        110.00,  # A2
        146.83,  # D3
        196.00,  # G3
        246.94,  # B3
        329.63,  # E4 (high E string)
        440.00,  # A4 (concert pitch)
        523.25,  # C5
        659.25,  # E5
        880.00,  # A5
        1046.50, # C6
        1318.51, # E6 (high end)
    ]

    def __init__(self, detector: RockyPitchDetector):
        self.detector = detector
        self.metrics = StressTestMetrics()
        self.sample_rate = detector.sample_rate

    def generate_test_tone(
        self,
        freq: float,
        duration: float = 0.5,
        add_noise: bool = False,
        noise_db: float = -20,
        add_harmonics: bool = True,
    ) -> np.ndarray:
        """Generate a test tone with optional noise and harmonics."""
        t = np.linspace(0, duration, int(self.sample_rate * duration), dtype=np.float32)

        # Fundamental
        signal = np.sin(2 * np.pi * freq * t)

        # Add harmonics (more realistic timbre)
        if add_harmonics:
            signal += 0.5 * np.sin(2 * np.pi * 2 * freq * t)  # 2nd harmonic
            signal += 0.25 * np.sin(2 * np.pi * 3 * freq * t)  # 3rd harmonic
            signal += 0.125 * np.sin(2 * np.pi * 4 * freq * t)  # 4th harmonic
            signal /= 1.875  # Normalize

        # Add noise
        if add_noise:
            noise_amplitude = 10 ** (noise_db / 20)
            noise = np.random.randn(len(t)).astype(np.float32) * noise_amplitude
            signal = signal + noise
            signal = signal / np.max(np.abs(signal))  # Renormalize

        return signal.astype(np.float32)

    def generate_silence(self, duration: float = 0.5) -> np.ndarray:
        """Generate silence for rejection testing."""
        return np.zeros(int(self.sample_rate * duration), dtype=np.float32)

    def generate_noise(self, duration: float = 0.5) -> np.ndarray:
        """Generate pure noise for rejection testing."""
        noise = np.random.randn(int(self.sample_rate * duration)).astype(np.float32)
        return noise / np.max(np.abs(noise)) * 0.5

    def freq_to_midi(self, freq: float) -> float:
        """Convert frequency to MIDI note number."""
        if freq <= 0:
            return 0
        return 69 + 12 * np.log2(freq / 440.0)

    def cents_error(self, detected_freq: float, target_freq: float) -> float:
        """Calculate cents error between detected and target frequency."""
        if detected_freq <= 0 or target_freq <= 0:
            return float('inf')
        return 1200 * np.log2(detected_freq / target_freq)

    async def test_single_inference(
        self,
        audio: np.ndarray,
        expected_freq: Optional[float] = None,
        should_detect: bool = True,
    ) -> Optional[PitchResult]:
        """Run a single inference and collect metrics."""
        self.metrics.total_inferences += 1

        try:
            result = await self.detector.detect_pitch(audio)

            if result:
                self.metrics.successful_inferences += 1
                self.metrics.latencies_ms.append(result.latency_ms)
                self.metrics.min_latency_ms = min(self.metrics.min_latency_ms, result.latency_ms)
                self.metrics.max_latency_ms = max(self.metrics.max_latency_ms, result.latency_ms)

                if expected_freq:
                    cents = abs(self.cents_error(result.frequency, expected_freq))
                    if cents <= 50:
                        self.metrics.correct_detections += 1
                    elif cents > 1200:  # Octave error
                        self.metrics.octave_errors += 1
                    elif cents > 100:  # Gross error (>1 semitone)
                        self.metrics.gross_errors += 1
            else:
                if not should_detect:
                    # Correctly rejected silence/noise
                    if expected_freq == 0:
                        self.metrics.silence_correctly_rejected += 1
                    else:
                        self.metrics.noise_correctly_rejected += 1
                else:
                    self.metrics.failed_inferences += 1

            return result

        except Exception as e:
            self.metrics.failed_inferences += 1
            print(f"[STRESS] Inference error: {e}")
            return None

    async def run_latency_stability_test(self, duration_seconds: float = 60):
        """Test latency stability over time."""
        print(f"\n[STRESS] === LATENCY STABILITY TEST ({duration_seconds}s) ===")

        start = time.time()
        test_audio = self.generate_test_tone(440.0, duration=0.5)
        iteration = 0

        while time.time() - start < duration_seconds:
            await self.test_single_inference(test_audio, expected_freq=440.0)
            iteration += 1

            if iteration % 100 == 0:
                elapsed = time.time() - start
                rate = iteration / elapsed
                avg_lat = np.mean(self.metrics.latencies_ms[-100:]) if self.metrics.latencies_ms else 0
                print(f"[STRESS] {iteration} inferences @ {rate:.1f}/s, avg latency: {avg_lat:.1f}ms")

        print(f"[STRESS] Completed {iteration} inferences")

    async def run_frequency_sweep_test(self):
        """Test accuracy across frequency range."""
        print("\n[STRESS] === FREQUENCY SWEEP TEST ===")

        results = []
        for freq in self.TEST_FREQUENCIES:
            audio = self.generate_test_tone(freq, duration=0.5)
            result = await self.test_single_inference(audio, expected_freq=freq)

            if result:
                cents = self.cents_error(result.frequency, freq)
                results.append((freq, result.frequency, cents, result.confidence))
                status = "✅" if abs(cents) < 50 else "🟡" if abs(cents) < 100 else "🔴"
                print(f"  {status} {freq:.1f}Hz → {result.frequency:.1f}Hz ({cents:+.1f} cents) conf={result.confidence:.2f}")
            else:
                results.append((freq, 0, float('inf'), 0))
                print(f"  🔴 {freq:.1f}Hz → NO DETECTION")

        # Calculate low/high frequency accuracy
        low_results = [r for r in results if r[0] < 150]
        high_results = [r for r in results if r[0] > 800]

        if low_results:
            low_accurate = sum(1 for r in low_results if abs(r[2]) < 50)
            self.metrics.low_freq_accuracy = low_accurate / len(low_results) * 100

        if high_results:
            high_accurate = sum(1 for r in high_results if abs(r[2]) < 50)
            self.metrics.high_freq_accuracy = high_accurate / len(high_results) * 100

    async def run_noise_robustness_test(self):
        """Test performance under various noise levels."""
        print("\n[STRESS] === NOISE ROBUSTNESS TEST ===")

        noise_levels = [-10, -6, -3, 0, 3, 6, 10]  # dB SNR
        test_freq = 440.0

        for snr_db in noise_levels:
            audio = self.generate_test_tone(test_freq, add_noise=True, noise_db=-snr_db)
            result = await self.test_single_inference(audio, expected_freq=test_freq)

            if result:
                cents = abs(self.cents_error(result.frequency, test_freq))
                status = "✅" if cents < 50 else "🟡" if cents < 100 else "🔴"
                print(f"  {status} SNR {snr_db:+3d}dB → {result.frequency:.1f}Hz ({cents:.0f} cents) conf={result.confidence:.2f}")
            else:
                print(f"  🔴 SNR {snr_db:+3d}dB → NO DETECTION")

    async def run_rejection_test(self):
        """Test silence and pure noise rejection."""
        print("\n[STRESS] === REJECTION TEST ===")

        # Test silence rejection
        silence = self.generate_silence(0.5)
        for i in range(10):
            result = await self.test_single_inference(silence, expected_freq=0, should_detect=False)
            if result is None:
                status = "✅"
            else:
                status = "🔴"
            if i == 0:
                print(f"  {status} Silence rejection: {'PASS' if result is None else 'FAIL (detected ' + str(result.frequency) + 'Hz)'}")

        # Test noise rejection
        noise = self.generate_noise(0.5)
        for i in range(10):
            result = await self.test_single_inference(noise, expected_freq=-1, should_detect=False)
            if result is None:
                status = "✅"
            else:
                status = "🟡"  # Detecting pitch in noise is acceptable if low confidence
            if i == 0:
                print(f"  {status} Noise rejection: {'PASS' if result is None else 'PARTIAL (detected ' + str(result.frequency) + 'Hz)'}")

    async def run_memory_leak_test(self, iterations: int = 1000):
        """Test for memory leaks over many iterations."""
        print(f"\n[STRESS] === MEMORY LEAK TEST ({iterations} iterations) ===")

        tracemalloc.start()
        gc.collect()

        snapshot1 = tracemalloc.take_snapshot()
        self.metrics.initial_memory_mb = tracemalloc.get_traced_memory()[0] / 1024 / 1024

        test_audio = self.generate_test_tone(440.0, duration=0.5)

        for i in range(iterations):
            await self.test_single_inference(test_audio, expected_freq=440.0)

            if (i + 1) % 200 == 0:
                current, peak = tracemalloc.get_traced_memory()
                print(f"  [{i+1}/{iterations}] Current: {current/1024/1024:.1f}MB, Peak: {peak/1024/1024:.1f}MB")

        gc.collect()
        snapshot2 = tracemalloc.take_snapshot()

        current, peak = tracemalloc.get_traced_memory()
        self.metrics.peak_memory_mb = peak / 1024 / 1024
        self.metrics.final_memory_mb = current / 1024 / 1024

        # Compare snapshots
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        print("\n  Top memory consumers:")
        for stat in top_stats[:5]:
            print(f"    {stat}")

        tracemalloc.stop()

        leak = self.metrics.final_memory_mb - self.metrics.initial_memory_mb
        status = "✅" if leak < 10 else "🟡" if leak < 50 else "🔴"
        print(f"\n  {status} Memory delta: {leak:.1f}MB (initial: {self.metrics.initial_memory_mb:.1f}MB, final: {self.metrics.final_memory_mb:.1f}MB)")

    async def run_concurrent_test(self, concurrent_requests: int = 8):
        """Test handling of concurrent inference requests."""
        print(f"\n[STRESS] === CONCURRENT REQUEST TEST ({concurrent_requests} concurrent) ===")

        # Generate different test tones
        test_tones = [
            self.generate_test_tone(freq, duration=0.5)
            for freq in self.TEST_FREQUENCIES[:concurrent_requests]
        ]

        async def run_batch():
            tasks = []
            for i, audio in enumerate(test_tones):
                tasks.append(self.test_single_inference(audio, expected_freq=self.TEST_FREQUENCIES[i]))
            return await asyncio.gather(*tasks)

        # Run concurrent batches
        for batch in range(5):
            start = time.time()
            results = await run_batch()
            elapsed = time.time() - start

            successful = sum(1 for r in results if r is not None)
            print(f"  Batch {batch+1}: {successful}/{concurrent_requests} successful in {elapsed*1000:.1f}ms")

    async def run_full_test_suite(self, duration_seconds: float = 60):
        """Run the complete stress test suite."""
        print("=" * 60)
        print("   ROCKY PITCH DETECTOR - STRESS TEST SUITE")
        print("=" * 60)
        print(f"Duration: {duration_seconds}s, Model: {self.detector.model}")
        print(f"Device: {self.detector.device}")
        print(f"Sample Rate: {self.sample_rate}Hz")
        print("=" * 60)

        self.metrics = StressTestMetrics()
        self.metrics.start_time = time.time()

        # Run all tests
        await self.run_frequency_sweep_test()
        await self.run_noise_robustness_test()
        await self.run_rejection_test()
        await self.run_concurrent_test()
        await self.run_memory_leak_test(iterations=500)
        await self.run_latency_stability_test(duration_seconds=max(10, duration_seconds - 30))

        self.metrics.end_time = time.time()

        # Print summary
        stats = self.metrics.calculate_stats()

        print("\n" + "=" * 60)
        print("   STRESS TEST SUMMARY")
        print("=" * 60)
        print(f"\n📊 THROUGHPUT")
        print(f"   Total inferences: {stats['total_inferences']}")
        print(f"   Success rate: {stats['success_rate']:.1f}%")
        print(f"   Throughput: {stats['throughput_hz']:.1f} inferences/sec")
        print(f"   Duration: {stats['duration_seconds']:.1f}s")

        print(f"\n⏱️ LATENCY (ms)")
        print(f"   Average: {stats['latency_avg_ms']:.2f}ms")
        print(f"   Std Dev: {stats['latency_std_ms']:.2f}ms (jitter)")
        print(f"   Min: {stats['latency_min_ms']:.2f}ms")
        print(f"   Max: {stats['latency_max_ms']:.2f}ms")
        print(f"   P50: {stats['latency_p50_ms']:.2f}ms")
        print(f"   P95: {stats['latency_p95_ms']:.2f}ms")
        print(f"   P99: {stats['latency_p99_ms']:.2f}ms")

        print(f"\n🎯 ACCURACY")
        print(f"   Correct (<50 cents): {stats['accuracy_rate']:.1f}%")
        print(f"   Octave errors: {stats['octave_error_rate']:.1f}%")
        print(f"   Gross errors (>100 cents): {stats['gross_error_rate']:.1f}%")
        print(f"   Low freq (E2): {self.metrics.low_freq_accuracy:.1f}%")
        print(f"   High freq (E6): {self.metrics.high_freq_accuracy:.1f}%")

        print(f"\n💾 MEMORY")
        print(f"   Initial: {stats['memory_initial_mb']:.1f}MB")
        print(f"   Peak: {stats['memory_peak_mb']:.1f}MB")
        print(f"   Final: {stats['memory_final_mb']:.1f}MB")
        print(f"   Leak: {stats['memory_leak_mb']:.1f}MB")

        print(f"\n🛡️ ROBUSTNESS")
        print(f"   Silence rejections: {self.metrics.silence_correctly_rejected}/10")
        print(f"   Noise rejections: {self.metrics.noise_correctly_rejected}/10")

        # Score calculation (based on 100 metrics framework)
        score = 0
        if stats['latency_avg_ms'] < 20: score += 5
        if stats['latency_p95_ms'] < 25: score += 5
        if stats['jitter_ms'] < 5: score += 5
        if stats['accuracy_rate'] > 80: score += 10
        if stats['octave_error_rate'] < 5: score += 5
        if stats['memory_leak_mb'] < 10: score += 5
        if self.metrics.silence_correctly_rejected >= 8: score += 5

        print(f"\n🏆 STRESS TEST SCORE: {score}/40")
        print("=" * 60)

        return stats


async def main():
    parser = argparse.ArgumentParser(description="Rocky Pitch Detector Stress Test")
    parser.add_argument('--quick', action='store_true', help='Quick 30-second test')
    parser.add_argument('--duration', type=int, default=60, help='Test duration in seconds')
    parser.add_argument('--model', choices=['tiny', 'small', 'medium', 'large', 'full'], default='tiny')
    args = parser.parse_args()

    duration = 30 if args.quick else args.duration

    print("[STRESS] Initializing pitch detector...")
    detector = RockyPitchDetector(
        sample_rate=48000,
        hop_length=512,
        model=args.model,
        confidence_threshold=0.5,
    )

    stress_test = PitchDetectorStressTest(detector)
    await stress_test.run_full_test_suite(duration_seconds=duration)


if __name__ == "__main__":
    asyncio.run(main())
