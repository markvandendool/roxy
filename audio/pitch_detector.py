#!/usr/bin/env python3
"""
Rocky Audio - Real-time Pitch Detection with TorchCrepe
Deploy to: ~/.roxy/audio/pitch_detector.py
Story: RAF-005 (CORRECTED: Uses RX 6900 XT, NOT W5700X)

Requirements:
    pip install torchcrepe torch torchaudio numpy websockets sounddevice aiohttp

Hardware:
    - GPU: RX 6900 XT (ROCR_VISIBLE_DEVICES=1)
    - Audio: PipeWire with quantum=128
    - Target latency: <30ms pitch detection

Usage:
    python pitch_detector.py                    # Default: capture from mic
    python pitch_detector.py --device 3         # Specific audio device
    python pitch_detector.py --list-devices     # List audio devices
    python pitch_detector.py --demo             # Test with synthetic tone

Metrics:
    - Prometheus metrics exposed on http://localhost:9767/metrics
    - Compatible with ROXY Prometheus stack
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

import torch
import torchaudio
import torchcrepe

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
    print("[ROCKY.PITCH] WARNING: sounddevice not installed. Run: pip install sounddevice")

# HTTP server for Prometheus metrics
try:
    from aiohttp import web
except ImportError:
    web = None
    print("[ROCKY.PITCH] WARNING: aiohttp not installed. Metrics endpoint disabled. Run: pip install aiohttp")


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
    gpu_warmup_complete: int = 0

    # Histograms (stored as lists for percentile calculation)
    latency_samples: deque = field(default_factory=lambda: deque(maxlen=1000))
    confidence_samples: deque = field(default_factory=lambda: deque(maxlen=1000))

    # Metadata
    start_time: float = field(default_factory=time.time)
    model_name: str = "tiny"
    device_name: str = "unknown"
    sample_rate: int = 48000

    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_pitch(self, freq: float, midi: float, confidence: float, latency_ms: float):
        """Record a pitch detection result."""
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
        """Export metrics in Prometheus text format."""
        with self._lock:
            lines = []

            # Header
            lines.append("# HELP pitch_detector_info Pitch detector metadata")
            lines.append("# TYPE pitch_detector_info gauge")
            lines.append(f'pitch_detector_info{{model="{self.model_name}",device="{self.device_name}",sample_rate="{self.sample_rate}"}} 1')

            # Uptime
            lines.append("# HELP pitch_detector_uptime_seconds Detector uptime in seconds")
            lines.append("# TYPE pitch_detector_uptime_seconds counter")
            lines.append(f"pitch_detector_uptime_seconds {time.time() - self.start_time:.1f}")

            # Counters
            lines.append("# HELP pitch_detections_total Total pitch detections attempted")
            lines.append("# TYPE pitch_detections_total counter")
            lines.append(f"pitch_detections_total {self.pitch_detections_total}")

            lines.append("# HELP pitch_detections_confident Pitch detections above confidence threshold")
            lines.append("# TYPE pitch_detections_confident counter")
            lines.append(f"pitch_detections_confident {self.pitch_detections_confident}")

            lines.append("# HELP websocket_connections_total Total WebSocket connections")
            lines.append("# TYPE websocket_connections_total counter")
            lines.append(f"websocket_connections_total {self.websocket_connections_total}")

            lines.append("# HELP websocket_messages_sent_total Total WebSocket messages sent")
            lines.append("# TYPE websocket_messages_sent_total counter")
            lines.append(f"websocket_messages_sent_total {self.websocket_messages_sent}")

            lines.append("# HELP audio_frames_processed_total Total audio frames processed")
            lines.append("# TYPE audio_frames_processed_total counter")
            lines.append(f"audio_frames_processed_total {self.audio_frames_processed}")

            # Gauges
            lines.append("# HELP pitch_current_frequency_hz Current detected frequency in Hz")
            lines.append("# TYPE pitch_current_frequency_hz gauge")
            lines.append(f"pitch_current_frequency_hz {self.current_frequency_hz:.2f}")

            lines.append("# HELP pitch_current_midi_note Current MIDI note number")
            lines.append("# TYPE pitch_current_midi_note gauge")
            lines.append(f"pitch_current_midi_note {self.current_midi_note:.2f}")

            lines.append("# HELP pitch_current_confidence Current detection confidence (0-1)")
            lines.append("# TYPE pitch_current_confidence gauge")
            lines.append(f"pitch_current_confidence {self.current_confidence:.3f}")

            lines.append("# HELP pitch_current_latency_ms Current detection latency in ms")
            lines.append("# TYPE pitch_current_latency_ms gauge")
            lines.append(f"pitch_current_latency_ms {self.current_latency_ms:.2f}")

            lines.append("# HELP websocket_clients_active Current active WebSocket clients")
            lines.append("# TYPE websocket_clients_active gauge")
            lines.append(f"websocket_clients_active {self.websocket_clients_active}")

            lines.append("# HELP gpu_warmup_complete GPU warmup completed (0/1)")
            lines.append("# TYPE gpu_warmup_complete gauge")
            lines.append(f"gpu_warmup_complete {self.gpu_warmup_complete}")

            # Latency histogram buckets
            if self.latency_samples:
                latencies = list(self.latency_samples)
                lines.append("# HELP pitch_latency_ms_summary Pitch detection latency summary")
                lines.append("# TYPE pitch_latency_ms_summary summary")
                lines.append(f'pitch_latency_ms_summary{{quantile="0.5"}} {np.percentile(latencies, 50):.2f}')
                lines.append(f'pitch_latency_ms_summary{{quantile="0.9"}} {np.percentile(latencies, 90):.2f}')
                lines.append(f'pitch_latency_ms_summary{{quantile="0.95"}} {np.percentile(latencies, 95):.2f}')
                lines.append(f'pitch_latency_ms_summary{{quantile="0.99"}} {np.percentile(latencies, 99):.2f}')
                lines.append(f"pitch_latency_ms_summary_sum {sum(latencies):.2f}")
                lines.append(f"pitch_latency_ms_summary_count {len(latencies)}")

            # Confidence histogram
            if self.confidence_samples:
                confs = list(self.confidence_samples)
                lines.append("# HELP pitch_confidence_summary Pitch confidence summary")
                lines.append("# TYPE pitch_confidence_summary summary")
                lines.append(f'pitch_confidence_summary{{quantile="0.5"}} {np.percentile(confs, 50):.3f}')
                lines.append(f'pitch_confidence_summary{{quantile="0.9"}} {np.percentile(confs, 90):.3f}')
                lines.append(f"pitch_confidence_summary_sum {sum(confs):.3f}")
                lines.append(f"pitch_confidence_summary_count {len(confs)}")

            return "\n".join(lines) + "\n"


# Global metrics instance
metrics = PrometheusMetrics()


@dataclass
class PitchResult:
    """Single pitch detection result."""
    timestamp: float
    frequency: float  # Hz
    midi_note: float  # MIDI note number (can be fractional for cents)
    confidence: float
    latency_ms: float
    note_name: str


class RockyPitchDetector:
    """Real-time pitch detection optimized for guitar."""

    # Note names for display
    NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    def __init__(
        self,
        sample_rate: int = 48000,
        hop_length: int = 512,  # ~10.7ms at 48kHz
        model: str = "tiny",  # tiny/small/medium/large/full
        device: str = "cuda:1",  # cuda:1 = RX 6900 XT, cuda:0 = integrated
        confidence_threshold: float = 0.5,
        websocket_port: int = 8767,
    ):
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.websocket_port = websocket_port

        # Select device - prefer RX 6900 XT (cuda:1), fallback to any GPU, then CPU
        if "cuda" in device and torch.cuda.is_available():
            # Try to find RX 6900 XT
            target_device = None
            for i in range(torch.cuda.device_count()):
                name = torch.cuda.get_device_name(i)
                if "6900" in name:  # RX 6900 XT
                    target_device = i
                    break
            
            if target_device is not None:
                self.device = torch.device(f"cuda:{target_device}")
                print(f"[ROCKY.PITCH] Using GPU: {torch.cuda.get_device_name(target_device)} (device {target_device})")
            elif ":" in device:
                # Specific device requested
                idx = int(device.split(":")[1])
                if idx < torch.cuda.device_count():
                    self.device = torch.device(device)
                    print(f"[ROCKY.PITCH] Using GPU: {torch.cuda.get_device_name(idx)} (device {idx})")
                else:
                    self.device = torch.device("cuda:0")
                    print(f"[ROCKY.PITCH] Using GPU: {torch.cuda.get_device_name(0)} (device 0)")
            else:
                self.device = torch.device("cuda:0")
                print(f"[ROCKY.PITCH] Using GPU: {torch.cuda.get_device_name(0)} (device 0)")
        else:
            self.device = torch.device("cpu")
            print("[ROCKY.PITCH] Using CPU (GPU not available)")

        # Latency tracking
        self.latency_buffer = deque(maxlen=100)

        # Audio buffer for streaming
        self.audio_buffer = np.array([], dtype=np.float32)
        self.buffer_size = 1024  # Minimum samples for detection

        # WebSocket clients
        self.ws_clients = set()
        
        # Audio capture state
        self.is_capturing = False
        self.audio_queue = asyncio.Queue()

        print(f"[ROCKY.PITCH] Initialized: model={model}, sr={sample_rate}, hop={hop_length}")

        # Update metrics metadata
        metrics.model_name = model
        metrics.device_name = str(self.device)
        metrics.sample_rate = sample_rate

        # Warmup GPU with dummy inference
        if "cuda" in str(self.device):
            print("[ROCKY.PITCH] Warming up GPU...")
            dummy = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 24000, dtype=np.float32))
            dummy_tensor = torch.from_numpy(dummy).float().unsqueeze(0).to(self.device)
            with torch.no_grad():
                for _ in range(3):  # 3 warmup passes
                    torchcrepe.predict(
                        dummy_tensor,
                        self.sample_rate,
                        hop_length=self.hop_length,
                        model=self.model,
                        device=self.device,
                        return_periodicity=True,
                    )
            metrics.gpu_warmup_complete = 1
            print("[ROCKY.PITCH] GPU warmed up ✓")

    def freq_to_midi(self, freq: float) -> float:
        """Convert frequency to MIDI note number."""
        if freq <= 0:
            return 0
        return 69 + 12 * np.log2(freq / 440.0)

    def midi_to_note_name(self, midi: float) -> str:
        """Convert MIDI note to note name with octave."""
        if midi <= 0:
            return "---"
        note_idx = int(round(midi)) % 12
        octave = int(round(midi)) // 12 - 1
        cents = int((midi - round(midi)) * 100)
        cents_str = f"+{cents}" if cents > 0 else str(cents) if cents < 0 else ""
        return f"{self.NOTE_NAMES[note_idx]}{octave}{cents_str}"

    async def detect_pitch(self, audio: np.ndarray) -> Optional[PitchResult]:
        """
        Detect pitch from audio samples.

        Args:
            audio: Float32 audio samples, mono, normalized to [-1, 1]

        Returns:
            PitchResult or None if no confident pitch detected
        """
        start_time = time.perf_counter()

        # Convert to torch tensor
        audio_tensor = torch.from_numpy(audio).float().unsqueeze(0).to(self.device)

        # Run CREPE
        with torch.no_grad():
            pitch, confidence = torchcrepe.predict(
                audio_tensor,
                self.sample_rate,
                hop_length=self.hop_length,
                model=self.model,
                device=self.device,
                return_periodicity=True,
            )

        # Get most confident pitch in this frame
        pitch = pitch.squeeze().cpu().numpy()
        confidence = confidence.squeeze().cpu().numpy()

        # Find best pitch
        if len(pitch) == 0:
            return None

        best_idx = np.argmax(confidence)
        best_conf = confidence[best_idx]
        best_freq = pitch[best_idx]

        if best_conf < self.confidence_threshold:
            return None

        latency_ms = (time.perf_counter() - start_time) * 1000
        self.latency_buffer.append(latency_ms)

        midi_note = self.freq_to_midi(best_freq)
        note_name = self.midi_to_note_name(midi_note)

        # Record metrics
        metrics.record_pitch(float(best_freq), float(midi_note), float(best_conf), latency_ms)

        return PitchResult(
            timestamp=time.time(),
            frequency=float(best_freq),
            midi_note=float(midi_note),
            confidence=float(best_conf),
            latency_ms=latency_ms,
            note_name=note_name,
        )

    def process_audio_chunk(self, chunk: np.ndarray) -> Optional[PitchResult]:
        """Process incoming audio chunk (for streaming)."""
        self.audio_buffer = np.concatenate([self.audio_buffer, chunk])

        if len(self.audio_buffer) >= self.buffer_size:
            # Process buffer
            result = asyncio.get_event_loop().run_until_complete(
                self.detect_pitch(self.audio_buffer[:self.buffer_size])
            )
            # Slide buffer
            self.audio_buffer = self.audio_buffer[self.hop_length:]
            return result
        return None

    async def broadcast_result(self, result: PitchResult):
        """Broadcast pitch result to WebSocket clients."""
        if not self.ws_clients:
            return

        message = json.dumps({
            "type": "pitch",
            "data": {
                "frequency": result.frequency,
                "midi": result.midi_note,
                "note": result.note_name,
                "confidence": result.confidence,
                "latency_ms": result.latency_ms,
                "timestamp": result.timestamp,
            }
        })

        # Broadcast to all clients
        disconnected = set()
        for ws in self.ws_clients:
            try:
                await ws.send(message)
                metrics.record_websocket_send()
            except Exception:
                disconnected.add(ws)

        self.ws_clients -= disconnected

    async def websocket_handler(self, websocket):
        """Handle WebSocket connections (websockets 11.0+ API)."""
        self.ws_clients.add(websocket)
        metrics.record_websocket_connect()
        print(f"[ROCKY.PITCH] WebSocket client connected ({len(self.ws_clients)} total)")
        try:
            async for message in websocket:
                # Handle incoming commands
                data = json.loads(message)
                if data.get("type") == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))
        except Exception as e:
            print(f"[ROCKY.PITCH] WebSocket error: {e}")
        finally:
            self.ws_clients.discard(websocket)
            metrics.record_websocket_disconnect()
            print(f"[ROCKY.PITCH] WebSocket client disconnected ({len(self.ws_clients)} remaining)")

    def get_stats(self) -> dict:
        """Get performance statistics."""
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
    """Main entry point - start detector with WebSocket server."""
    parser = argparse.ArgumentParser(description="Rocky Pitch Detector - Real-time pitch detection with TorchCrepe")
    parser.add_argument('--device', type=int, default=None, help='Audio input device index')
    parser.add_argument('--list-devices', action='store_true', help='List available audio devices')
    parser.add_argument('--demo', action='store_true', help='Run demo with synthetic tone')
    parser.add_argument('--model', choices=['tiny', 'small', 'medium', 'large', 'full'], default='tiny', help='CREPE model size')
    parser.add_argument('--port', type=int, default=8767, help='WebSocket server port')
    parser.add_argument('--metrics-port', type=int, default=9767, help='Prometheus metrics HTTP port')
    args = parser.parse_args()
    
    # List devices mode
    if args.list_devices:
        if sd is None:
            print("[ERROR] sounddevice not installed")
            sys.exit(1)
        print("\n[ROCKY.PITCH] Available audio devices:")
        print(sd.query_devices())
        sys.exit(0)
    
    detector = RockyPitchDetector(
        sample_rate=48000,
        hop_length=512,
        model=args.model,
        confidence_threshold=0.5,
        websocket_port=args.port,
    )
    
    # Demo mode
    if args.demo:
        print("[ROCKY.PITCH] Demo mode: testing with synthetic 440Hz tone")
        t = np.linspace(0, 0.5, 24000, dtype=np.float32)
        test_audio = np.sin(2 * np.pi * 440 * t)
        result = await detector.detect_pitch(test_audio)
        if result:
            print(f"[ROCKY.PITCH] Detected: {result.note_name} ({result.frequency:.1f}Hz) "
                  f"conf={result.confidence:.2f} latency={result.latency_ms:.1f}ms")
        print(f"[ROCKY.PITCH] Stats: {detector.get_stats()}")
        return
    
    # Check requirements
    if sd is None:
        print("[ERROR] sounddevice required for audio capture. Run: pip install sounddevice")
        sys.exit(1)
    if websockets is None:
        print("[ERROR] websockets required for browser bridge. Run: pip install websockets")
        sys.exit(1)
    
    # Audio callback - puts samples in queue
    def audio_callback(indata, frames, time_info, status):
        if status:
            print(f"[ROCKY.PITCH] Audio status: {status}")
        # Convert to mono float32
        audio = indata[:, 0].astype(np.float32)
        metrics.record_audio_frame()
        try:
            detector.audio_queue.put_nowait(audio.copy())
        except asyncio.QueueFull:
            pass  # Drop frames if processing can't keep up
    
    # Detection loop - processes audio from queue
    async def detection_loop():
        buffer = np.array([], dtype=np.float32)
        min_samples = 1024  # Minimum for detection
        
        print("[ROCKY.PITCH] Detection loop started")
        while True:
            try:
                # Get audio chunk (non-blocking with timeout)
                chunk = await asyncio.wait_for(detector.audio_queue.get(), timeout=0.1)
                buffer = np.concatenate([buffer, chunk])
                
                # Process when we have enough
                if len(buffer) >= min_samples:
                    result = await detector.detect_pitch(buffer[:min_samples])
                    
                    if result:
                        # Broadcast to WebSocket clients
                        await detector.broadcast_result(result)
                        
                        # Log occasionally
                        if len(detector.latency_buffer) % 20 == 0:
                            stats = detector.get_stats()
                            print(f"[ROCKY.PITCH] {result.note_name} ({result.frequency:.1f}Hz) "
                                  f"conf={result.confidence:.2f} lat={result.latency_ms:.1f}ms "
                                  f"avg={stats['avg_latency_ms']:.1f}ms")
                    
                    # Slide buffer (keep some overlap)
                    buffer = buffer[512:]
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"[ROCKY.PITCH] Detection error: {e}")
    
    # Determine audio device
    device_idx = args.device
    if device_idx is None:
        # Auto-detect: prefer "Monitor" for loopback, else default input
        try:
            devices = sd.query_devices()
            for i, d in enumerate(devices):
                if 'monitor' in d['name'].lower() and d['max_input_channels'] > 0:
                    device_idx = i
                    print(f"[ROCKY.PITCH] Auto-selected monitor device: {d['name']}")
                    break
        except Exception:
            pass
    
    device_info = sd.query_devices(device_idx, 'input') if device_idx else sd.query_devices(kind='input')
    print(f"[ROCKY.PITCH] Using audio device: {device_info['name']}")
    
    # Start audio capture
    stream = sd.InputStream(
        device=device_idx,
        channels=1,
        samplerate=48000,
        blocksize=512,  # ~10.7ms blocks
        callback=audio_callback,
    )
    
    print(f"[ROCKY.PITCH] Starting WebSocket server on ws://127.0.0.1:{detector.websocket_port}")
    print("[ROCKY.PITCH] Browser clients can connect to receive pitch data")

    # Prometheus metrics HTTP server
    metrics_runner = None
    if web is not None:
        async def metrics_handler(request):
            """Prometheus metrics endpoint."""
            return web.Response(
                text=metrics.to_prometheus(),
                content_type='text/plain; version=0.0.4'
            )

        async def health_handler(request):
            """Health check endpoint."""
            return web.Response(
                text=json.dumps({
                    "status": "healthy",
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
        print(f"[ROCKY.PITCH] Prometheus metrics: http://0.0.0.0:{args.metrics_port}/metrics")
    else:
        print("[ROCKY.PITCH] WARNING: aiohttp not installed, metrics endpoint disabled")

    print("[ROCKY.PITCH] Press Ctrl+C to stop\n")

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
        print("\n[ROCKY.PITCH] Stopped by user")
