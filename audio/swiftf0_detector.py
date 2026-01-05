#!/usr/bin/env python3
"""
Rocky Audio - SwiftF0 Pitch Detection Engine (P4_SWIFTF0)
Deploy to: ~/.roxy/audio/swiftf0_detector.py
Story: MEGAZORD Phase 2

SwiftF0 Specifications:
    - 95K parameters (vs 24M for CREPE)
    - 42× faster than CREPE on CPU
    - 91.8% harmonic mean accuracy at 10dB SNR
    - ONNX-based (no GPU required, but GPU accelerates)

Requirements:
    pip install swift-f0 websockets aiohttp sounddevice numpy

Usage:
    python swiftf0_detector.py                    # Default: capture from mic
    python swiftf0_detector.py --device 3         # Specific audio device
    python swiftf0_detector.py --list-devices     # List audio devices
    python swiftf0_detector.py --demo             # Test with synthetic tone

Ports:
    - WebSocket: 8768 (SwiftF0 pitch data)
    - Metrics: 9768 (Prometheus /metrics)
"""

import asyncio
import json
import os
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional
import argparse
import threading

import numpy as np

# SwiftF0 - the star of the show
from swift_f0 import SwiftF0

# WebSocket for Apollo bridge
try:
    import websockets
except ImportError:
    websockets = None

# Audio capture
try:
    import sounddevice as sd
except ImportError:
    sd = None
    print("[SWIFTF0] WARNING: sounddevice not installed. Run: pip install sounddevice")

# HTTP server for Prometheus metrics
try:
    from aiohttp import web
except ImportError:
    web = None
    print("[SWIFTF0] WARNING: aiohttp not installed. Metrics endpoint disabled.")


# ==============================================================================
# PROMETHEUS METRICS
# ==============================================================================

@dataclass
class PrometheusMetrics:
    """Thread-safe metrics collector for Prometheus exposition."""

    # Counters
    pitch_detections_total: int = 0
    pitch_detections_confident: int = 0
    websocket_connections_total: int = 0
    websocket_messages_sent: int = 0
    audio_frames_processed: int = 0

    # Gauges
    current_frequency_hz: float = 0.0
    current_midi_note: float = 0.0
    current_confidence: float = 0.0
    current_latency_ms: float = 0.0
    websocket_clients_active: int = 0
    model_ready: int = 0

    # Histograms
    latency_samples: deque = field(default_factory=lambda: deque(maxlen=1000))
    confidence_samples: deque = field(default_factory=lambda: deque(maxlen=1000))

    # Metadata
    start_time: float = field(default_factory=time.time)
    engine_name: str = "P4_SWIFTF0"
    sample_rate: int = 16000

    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_pitch(self, freq: float, midi: float, confidence: float, latency_ms: float):
        with self._lock:
            self.pitch_detections_total += 1
            self.current_frequency_hz = freq
            self.current_midi_note = midi
            self.current_confidence = confidence
            self.current_latency_ms = latency_ms
            self.latency_samples.append(latency_ms)
            self.confidence_samples.append(confidence)
            if confidence >= 0.5:
                self.pitch_detections_confident += 1

    def record_websocket_connect(self):
        with self._lock:
            self.websocket_connections_total += 1
            self.websocket_clients_active += 1

    def record_websocket_disconnect(self):
        with self._lock:
            self.websocket_clients_active = max(0, self.websocket_clients_active - 1)

    def record_websocket_send(self):
        with self._lock:
            self.websocket_messages_sent += 1

    def record_audio_frame(self):
        with self._lock:
            self.audio_frames_processed += 1

    def to_prometheus(self) -> str:
        with self._lock:
            lines = []

            lines.append("# HELP swiftf0_info SwiftF0 detector metadata")
            lines.append("# TYPE swiftf0_info gauge")
            lines.append(f'swiftf0_info{{engine="{self.engine_name}",sample_rate="{self.sample_rate}"}} 1')

            lines.append("# HELP swiftf0_uptime_seconds Detector uptime")
            lines.append("# TYPE swiftf0_uptime_seconds counter")
            lines.append(f"swiftf0_uptime_seconds {time.time() - self.start_time:.1f}")

            lines.append("# HELP swiftf0_detections_total Total pitch detections")
            lines.append("# TYPE swiftf0_detections_total counter")
            lines.append(f"swiftf0_detections_total {self.pitch_detections_total}")

            lines.append("# HELP swiftf0_detections_confident Confident detections")
            lines.append("# TYPE swiftf0_detections_confident counter")
            lines.append(f"swiftf0_detections_confident {self.pitch_detections_confident}")

            lines.append("# HELP swiftf0_current_frequency_hz Current frequency")
            lines.append("# TYPE swiftf0_current_frequency_hz gauge")
            lines.append(f"swiftf0_current_frequency_hz {self.current_frequency_hz:.2f}")

            lines.append("# HELP swiftf0_current_confidence Current confidence")
            lines.append("# TYPE swiftf0_current_confidence gauge")
            lines.append(f"swiftf0_current_confidence {self.current_confidence:.3f}")

            lines.append("# HELP swiftf0_current_latency_ms Current latency")
            lines.append("# TYPE swiftf0_current_latency_ms gauge")
            lines.append(f"swiftf0_current_latency_ms {self.current_latency_ms:.2f}")

            lines.append("# HELP swiftf0_websocket_clients Active clients")
            lines.append("# TYPE swiftf0_websocket_clients gauge")
            lines.append(f"swiftf0_websocket_clients {self.websocket_clients_active}")

            if self.latency_samples:
                latencies = list(self.latency_samples)
                lines.append("# HELP swiftf0_latency_ms_summary Latency summary")
                lines.append("# TYPE swiftf0_latency_ms_summary summary")
                lines.append(f'swiftf0_latency_ms_summary{{quantile="0.5"}} {np.percentile(latencies, 50):.2f}')
                lines.append(f'swiftf0_latency_ms_summary{{quantile="0.95"}} {np.percentile(latencies, 95):.2f}')
                lines.append(f'swiftf0_latency_ms_summary{{quantile="0.99"}} {np.percentile(latencies, 99):.2f}')

            return "\n".join(lines) + "\n"


metrics = PrometheusMetrics()


@dataclass
class PitchResult:
    """Single pitch detection result."""
    timestamp: float
    frequency: float
    midi_note: float
    confidence: float
    latency_ms: float
    note_name: str
    engine: str = "P4_SWIFTF0"


class SwiftF0Detector:
    """Real-time pitch detection using SwiftF0 (42× faster than CREPE)."""

    NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    def __init__(
        self,
        sample_rate: int = 16000,  # SwiftF0 native rate
        fmin: float = 50.0,
        fmax: float = 1000.0,
        confidence_threshold: float = 0.5,
        websocket_port: int = 8768,
    ):
        self.sample_rate = sample_rate
        self.confidence_threshold = confidence_threshold
        self.websocket_port = websocket_port

        # Initialize SwiftF0
        print("[SWIFTF0] Initializing SwiftF0 (95K params, ONNX runtime)...")
        self.model = SwiftF0(
            fmin=fmin,
            fmax=fmax,
            confidence_threshold=confidence_threshold,
        )
        metrics.model_ready = 1
        print("[SWIFTF0] Model ready!")

        # Latency tracking
        self.latency_buffer = deque(maxlen=100)

        # Audio buffer
        self.audio_buffer = np.array([], dtype=np.float32)
        self.buffer_size = 2048  # ~128ms at 16kHz

        # WebSocket clients
        self.ws_clients = set()

        # Audio capture
        self.is_capturing = False
        self.audio_queue = asyncio.Queue()

        metrics.sample_rate = sample_rate
        print(f"[SWIFTF0] Config: sr={sample_rate}, fmin={fmin}, fmax={fmax}")

    def freq_to_midi(self, freq: float) -> float:
        if freq <= 0:
            return 0
        return 69 + 12 * np.log2(freq / 440.0)

    def midi_to_note_name(self, midi: float) -> str:
        if midi <= 0:
            return "---"
        note_idx = int(round(midi)) % 12
        octave = int(round(midi)) // 12 - 1
        cents = int((midi - round(midi)) * 100)
        cents_str = f"+{cents}" if cents > 0 else str(cents) if cents < 0 else ""
        return f"{self.NOTE_NAMES[note_idx]}{octave}{cents_str}"

    async def detect_pitch(self, audio: np.ndarray) -> Optional[PitchResult]:
        """Detect pitch from audio samples."""
        start_time = time.perf_counter()

        # SwiftF0 detection
        result = self.model.detect_from_array(audio, self.sample_rate)

        if result is None or result.confidence is None:
            return None

        # Find most confident frame
        valid = result.confidence > self.confidence_threshold
        if not valid.any():
            return None

        # Average over valid frames
        best_freq = float(np.mean(result.pitch_hz[valid]))
        best_conf = float(np.mean(result.confidence[valid]))

        latency_ms = (time.perf_counter() - start_time) * 1000
        self.latency_buffer.append(latency_ms)

        midi_note = self.freq_to_midi(best_freq)
        note_name = self.midi_to_note_name(midi_note)

        metrics.record_pitch(best_freq, midi_note, best_conf, latency_ms)

        return PitchResult(
            timestamp=time.time(),
            frequency=best_freq,
            midi_note=midi_note,
            confidence=best_conf,
            latency_ms=latency_ms,
            note_name=note_name,
            engine="P4_SWIFTF0",
        )

    async def broadcast_result(self, result: PitchResult):
        """Broadcast pitch result to WebSocket clients."""
        if not self.ws_clients:
            return

        message = json.dumps({
            "type": "pitch",
            "engine": "P4_SWIFTF0",
            "data": {
                "frequency": result.frequency,
                "midi": result.midi_note,
                "note": result.note_name,
                "confidence": result.confidence,
                "latency_ms": result.latency_ms,
                "timestamp": result.timestamp,
            }
        })

        disconnected = set()
        for ws in self.ws_clients:
            try:
                await ws.send(message)
                metrics.record_websocket_send()
            except Exception:
                disconnected.add(ws)

        self.ws_clients -= disconnected

    async def websocket_handler(self, websocket):
        """Handle WebSocket connections."""
        self.ws_clients.add(websocket)
        metrics.record_websocket_connect()
        print(f"[SWIFTF0] Client connected ({len(self.ws_clients)} total)")
        try:
            async for message in websocket:
                data = json.loads(message)
                if data.get("type") == "ping":
                    await websocket.send(json.dumps({"type": "pong", "engine": "P4_SWIFTF0"}))
        except Exception as e:
            print(f"[SWIFTF0] WebSocket error: {e}")
        finally:
            self.ws_clients.discard(websocket)
            metrics.record_websocket_disconnect()
            print(f"[SWIFTF0] Client disconnected ({len(self.ws_clients)} remaining)")

    def get_stats(self) -> dict:
        latencies = list(self.latency_buffer)
        if not latencies:
            return {"avg_latency_ms": 0, "min_latency_ms": 0, "max_latency_ms": 0}
        return {
            "avg_latency_ms": np.mean(latencies),
            "min_latency_ms": np.min(latencies),
            "max_latency_ms": np.max(latencies),
            "p95_latency_ms": np.percentile(latencies, 95) if len(latencies) >= 20 else 0,
        }


async def main():
    parser = argparse.ArgumentParser(description="SwiftF0 Pitch Detector (P4 Engine)")
    parser.add_argument('--device', type=int, default=None, help='Audio input device index')
    parser.add_argument('--list-devices', action='store_true', help='List audio devices')
    parser.add_argument('--demo', action='store_true', help='Run demo with synthetic tone')
    parser.add_argument('--port', type=int, default=8768, help='WebSocket port')
    parser.add_argument('--metrics-port', type=int, default=9768, help='Prometheus metrics port')
    args = parser.parse_args()

    if args.list_devices:
        if sd is None:
            print("[ERROR] sounddevice not installed")
            sys.exit(1)
        print("\n[SWIFTF0] Available audio devices:")
        print(sd.query_devices())
        sys.exit(0)

    detector = SwiftF0Detector(
        sample_rate=16000,
        fmin=50.0,
        fmax=1000.0,
        confidence_threshold=0.5,
        websocket_port=args.port,
    )

    if args.demo:
        print("[SWIFTF0] Demo mode: testing with 440Hz tone")
        t = np.linspace(0, 0.5, 8000, dtype=np.float32)
        test_audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        result = await detector.detect_pitch(test_audio)
        if result:
            print(f"[SWIFTF0] Detected: {result.note_name} ({result.frequency:.1f}Hz) "
                  f"conf={result.confidence:.2f} latency={result.latency_ms:.1f}ms")
        print(f"[SWIFTF0] Stats: {detector.get_stats()}")
        return

    if sd is None or websockets is None:
        print("[ERROR] Missing dependencies. Run: pip install sounddevice websockets")
        sys.exit(1)

    # Audio callback
    def audio_callback(indata, frames, time_info, status):
        if status:
            print(f"[SWIFTF0] Audio status: {status}")
        audio = indata[:, 0].astype(np.float32)
        metrics.record_audio_frame()
        try:
            detector.audio_queue.put_nowait(audio.copy())
        except asyncio.QueueFull:
            pass

    # Detection loop
    async def detection_loop():
        buffer = np.array([], dtype=np.float32)
        min_samples = 2048

        print("[SWIFTF0] Detection loop started")
        while True:
            try:
                chunk = await asyncio.wait_for(detector.audio_queue.get(), timeout=0.1)
                buffer = np.concatenate([buffer, chunk])

                if len(buffer) >= min_samples:
                    result = await detector.detect_pitch(buffer[:min_samples])

                    if result:
                        await detector.broadcast_result(result)

                        if len(detector.latency_buffer) % 20 == 0:
                            stats = detector.get_stats()
                            print(f"[SWIFTF0] {result.note_name} ({result.frequency:.1f}Hz) "
                                  f"conf={result.confidence:.2f} lat={result.latency_ms:.1f}ms "
                                  f"avg={stats['avg_latency_ms']:.1f}ms")

                    buffer = buffer[512:]

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"[SWIFTF0] Detection error: {e}")

    # Auto-detect device
    device_idx = args.device
    if device_idx is None:
        try:
            devices = sd.query_devices()
            for i, d in enumerate(devices):
                if 'monitor' in d['name'].lower() and d['max_input_channels'] > 0:
                    device_idx = i
                    print(f"[SWIFTF0] Auto-selected: {d['name']}")
                    break
        except Exception:
            pass

    device_info = sd.query_devices(device_idx, 'input') if device_idx else sd.query_devices(kind='input')
    print(f"[SWIFTF0] Using audio device: {device_info['name']}")

    stream = sd.InputStream(
        device=device_idx,
        channels=1,
        samplerate=16000,
        blocksize=512,
        callback=audio_callback,
    )

    print(f"[SWIFTF0] WebSocket server: ws://127.0.0.1:{detector.websocket_port}")

    # Prometheus metrics
    metrics_runner = None
    if web is not None:
        async def metrics_handler(request):
            return web.Response(
                text=metrics.to_prometheus(),
                content_type='text/plain; version=0.0.4'
            )

        async def health_handler(request):
            return web.Response(
                text=json.dumps({
                    "status": "healthy",
                    "engine": "P4_SWIFTF0",
                    "uptime_seconds": time.time() - metrics.start_time,
                    "detections": metrics.pitch_detections_total,
                    "clients": metrics.websocket_clients_active,
                }),
                content_type='application/json'
            )

        app = web.Application()
        app.router.add_get('/metrics', metrics_handler)
        app.router.add_get('/health', health_handler)
        app.router.add_get('/', health_handler)

        metrics_runner = web.AppRunner(app)
        await metrics_runner.setup()
        site = web.TCPSite(metrics_runner, '0.0.0.0', args.metrics_port)
        await site.start()
        print(f"[SWIFTF0] Prometheus metrics: http://0.0.0.0:{args.metrics_port}/metrics")

    print("[SWIFTF0] Press Ctrl+C to stop\n")

    try:
        async with websockets.serve(detector.websocket_handler, "127.0.0.1", detector.websocket_port):
            with stream:
                detector.is_capturing = True
                await detection_loop()
    finally:
        if metrics_runner:
            await metrics_runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SWIFTF0] Stopped by user")
