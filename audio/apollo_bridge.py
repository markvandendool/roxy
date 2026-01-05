#!/usr/bin/env python3
"""
Rocky Audio - Apollo Bridge
Deploy to: ~/.roxy/audio/apollo_bridge.py
Story: RAF-007

Bridges pitch detection to MindSong's Apollo audio system via WebSocket.
Connects:
  - Pitch Detector (ws://127.0.0.1:8767) -> receives pitch events
  - Apollo MCP (ws://127.0.0.1:8766) -> sends chord/note events
"""

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Optional

try:
    import websockets
except ImportError:
    print("ERROR: websockets not installed. Run: pip install websockets")
    exit(1)


@dataclass
class ChordDetection:
    """Chord detected from pitch analysis."""
    root: str
    quality: str  # major, minor, 7, maj7, min7, dim, aug, etc.
    notes: list[str]
    confidence: float
    timestamp: float


class ApolloBridge:
    """Bridge between Rocky pitch detection and Apollo audio system."""

    # Simple chord quality detection based on intervals
    CHORD_INTERVALS = {
        (0, 4, 7): "major",
        (0, 3, 7): "minor",
        (0, 4, 7, 10): "7",
        (0, 4, 7, 11): "maj7",
        (0, 3, 7, 10): "min7",
        (0, 3, 6): "dim",
        (0, 4, 8): "aug",
        (0, 5, 7): "sus4",
        (0, 2, 7): "sus2",
    }

    NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    def __init__(
        self,
        pitch_ws_url: str = "ws://127.0.0.1:8767",
        apollo_ws_url: str = "ws://127.0.0.1:8766",
    ):
        self.pitch_ws_url = pitch_ws_url
        self.apollo_ws_url = apollo_ws_url
        self.pitch_ws: Optional[websockets.WebSocketClientProtocol] = None
        self.apollo_ws: Optional[websockets.WebSocketClientProtocol] = None

        # Note buffer for chord detection (last N notes)
        self.note_buffer: list[tuple[int, float, float]] = []  # (midi, confidence, timestamp)
        self.buffer_window_ms = 200  # Window for chord detection
        self.min_notes_for_chord = 2

        # Stats
        self.notes_received = 0
        self.chords_detected = 0
        self.messages_sent = 0

    async def connect_pitch_detector(self):
        """Connect to the pitch detector WebSocket."""
        while True:
            try:
                self.pitch_ws = await websockets.connect(self.pitch_ws_url)
                print(f"[APOLLO.BRIDGE] Connected to pitch detector: {self.pitch_ws_url}")
                return
            except Exception as e:
                print(f"[APOLLO.BRIDGE] Pitch detector not available: {e}")
                print("[APOLLO.BRIDGE] Retrying in 2s...")
                await asyncio.sleep(2)

    async def connect_apollo(self):
        """Connect to Apollo MCP WebSocket."""
        while True:
            try:
                self.apollo_ws = await websockets.connect(self.apollo_ws_url)
                print(f"[APOLLO.BRIDGE] Connected to Apollo: {self.apollo_ws_url}")
                return
            except Exception as e:
                print(f"[APOLLO.BRIDGE] Apollo not available: {e}")
                print("[APOLLO.BRIDGE] Retrying in 2s...")
                await asyncio.sleep(2)

    def detect_chord(self) -> Optional[ChordDetection]:
        """Detect chord from buffered notes."""
        now = time.time() * 1000
        cutoff = now - self.buffer_window_ms

        # Filter recent notes
        recent = [(midi, conf, ts) for midi, conf, ts in self.note_buffer if ts > cutoff]
        self.note_buffer = recent

        if len(recent) < self.min_notes_for_chord:
            return None

        # Get unique pitch classes
        notes = sorted(set(int(round(midi)) % 12 for midi, _, _ in recent))

        if len(notes) < 2:
            return None

        # Try to match a chord
        root = notes[0]
        intervals = tuple(n - root for n in notes)

        # Normalize intervals (wrap around)
        intervals = tuple(sorted(set(i % 12 for i in intervals)))

        quality = self.CHORD_INTERVALS.get(intervals, None)
        if not quality:
            # Try inversions
            for i in range(1, len(notes)):
                root = notes[i]
                intervals = tuple(sorted(set((n - root) % 12 for n in notes)))
                quality = self.CHORD_INTERVALS.get(intervals, None)
                if quality:
                    break

        if not quality:
            return None

        root_name = self.NOTE_NAMES[root]
        note_names = [self.NOTE_NAMES[n] for n in notes]
        avg_conf = sum(conf for _, conf, _ in recent) / len(recent)

        self.chords_detected += 1

        return ChordDetection(
            root=root_name,
            quality=quality,
            notes=note_names,
            confidence=avg_conf,
            timestamp=time.time(),
        )

    async def send_to_apollo(self, chord: ChordDetection):
        """Send chord detection to Apollo."""
        if not self.apollo_ws:
            return

        message = {
            "type": "chord_detected",
            "data": {
                "root": chord.root,
                "quality": chord.quality,
                "notes": chord.notes,
                "confidence": chord.confidence,
                "timestamp": chord.timestamp,
                "display": f"{chord.root}{chord.quality}",
            }
        }

        try:
            await self.apollo_ws.send(json.dumps(message))
            self.messages_sent += 1
        except Exception as e:
            print(f"[APOLLO.BRIDGE] Send error: {e}")
            self.apollo_ws = None

    async def process_pitch_events(self):
        """Main loop: receive pitch events and detect chords."""
        await self.connect_pitch_detector()

        while True:
            try:
                if not self.pitch_ws:
                    await self.connect_pitch_detector()
                    continue

                message = await self.pitch_ws.recv()
                data = json.loads(message)

                if data.get("type") == "pitch":
                    pitch_data = data["data"]
                    midi = pitch_data["midi"]
                    conf = pitch_data["confidence"]
                    ts = pitch_data["timestamp"] * 1000  # Convert to ms

                    self.note_buffer.append((midi, conf, ts))
                    self.notes_received += 1

                    # Try to detect chord
                    chord = self.detect_chord()
                    if chord:
                        print(f"[APOLLO.BRIDGE] Chord: {chord.root}{chord.quality} "
                              f"({', '.join(chord.notes)}) conf={chord.confidence:.2f}")

                        if self.apollo_ws:
                            await self.send_to_apollo(chord)
                        else:
                            # Try to reconnect
                            asyncio.create_task(self.connect_apollo())

            except websockets.ConnectionClosed:
                print("[APOLLO.BRIDGE] Pitch detector disconnected, reconnecting...")
                self.pitch_ws = None
                await asyncio.sleep(1)
            except Exception as e:
                print(f"[APOLLO.BRIDGE] Error: {e}")
                await asyncio.sleep(1)

    async def run(self):
        """Start the bridge."""
        print("[APOLLO.BRIDGE] Starting Rocky-Apollo bridge...")

        # Try to connect to Apollo (optional, will retry)
        asyncio.create_task(self.connect_apollo())

        # Main loop
        await self.process_pitch_events()


async def main():
    bridge = ApolloBridge()
    await bridge.run()


if __name__ == "__main__":
    asyncio.run(main())
