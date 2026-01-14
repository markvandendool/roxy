#!/usr/bin/env python3
"""
Rocky Vision - MediaPipe Hand Tracking for Chord Detection
Story: RAF-006
Target: 21 3D landmarks at 30 FPS, CPU inference

Requirements:
    pip install mediapipe opencv-python numpy websockets
"""

import asyncio
import json
import time
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
import threading

try:
    import cv2
    import numpy as np
    try:
        import mediapipe as mp
        MP_VERSION = getattr(mp, "__version__", "unknown")
        # MediaPipe 0.10+ uses Tasks API, try legacy first
        if hasattr(mp, 'solutions'):
            # Legacy API (mediapipe < 0.10)
            MP_LEGACY = True
        else:
            MP_LEGACY = False
    except ImportError:
        MP_LEGACY = False
        mp = None
        MP_VERSION = "not-installed"
except ImportError as e:
    print(f"ERROR: Missing dependency: {e}")
    print("Run: pip install -r requirements-vision.txt")
    exit(1)

try:
    import websockets
except ImportError:
    websockets = None


@dataclass
class HandLandmarks:
    """21 hand landmarks with 3D coordinates."""
    landmarks: List[tuple]  # [(x, y, z), ...] normalized 0-1
    handedness: str  # "Left" or "Right"
    confidence: float
    timestamp: float


@dataclass
class ChordShape:
    """Detected chord shape from hand position."""
    name: str
    confidence: float
    finger_positions: dict
    timestamp: float


class RoxyHandTracker:
    """Real-time hand tracking for chord shape detection."""

    # Finger landmark indices
    FINGER_TIPS = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky
    FINGER_PIPS = [3, 6, 10, 14, 18]  # Second joints

    # Basic chord shapes (simplified - fret hand positions)
    CHORD_SHAPES = {
        "C": {"index": "down", "middle": "down", "ring": "up", "pinky": "up"},
        "G": {"index": "up", "middle": "down", "ring": "down", "pinky": "down"},
        "D": {"index": "down", "middle": "down", "ring": "down", "pinky": "up"},
        "Am": {"index": "down", "middle": "down", "ring": "up", "pinky": "up"},
        "Em": {"index": "down", "middle": "down", "ring": "up", "pinky": "up"},
        "F": {"index": "bar", "middle": "down", "ring": "down", "pinky": "down"},
    }

    def __init__(
        self,
        camera_id: int = 0,
        max_hands: int = 2,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5,
        websocket_port: int = 8768,
    ):
        self.camera_id = camera_id
        self.websocket_port = websocket_port
        self.mp_legacy = MP_LEGACY

        # MediaPipe setup - handle both legacy and Tasks API
        if MP_LEGACY:
            # Legacy API (mediapipe < 0.10)
            self.mp_hands = mp.solutions.hands
            self.mp_drawing = mp.solutions.drawing_utils
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=max_hands,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence,
            )
        else:
            # Tasks API (mediapipe >= 0.10)
            # Note: MediaPipe 0.10+ removed solutions API, requires Tasks API with model files
            # Set up placeholder - full implementation needs hand_landmarker.task model
            self.mp_hands = None
            self.mp_drawing = None
            self.hands = None
            print(f"[ROXY.VISION] Mediapipe version {MP_VERSION} detected (Tasks API)")
            print("[ROXY.VISION] Tasks API requires mediapipe>=0.10 and hand_landmarker.task; repo default pins mediapipe<0.10 for stability.")
            roxy_root = os.environ.get("ROXY_ROOT", str(Path.home() / ".roxy"))
            print(f"[ROXY.VISION] To enable Tasks API: wget -O {roxy_root}/vision/hand_landmarker.task \\")
            print("  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task")

        # State
        self.running = False
        self.current_hands: List[HandLandmarks] = []
        self.current_chord: Optional[ChordShape] = None
        self.ws_clients = set()

        # Stats
        self.frames_processed = 0
        self.fps = 0.0
        self.last_fps_time = time.time()

        print(f"[ROXY.VISION] Initialized MediaPipe Hands (camera={camera_id})")

    def get_finger_state(self, landmarks: List[tuple]) -> dict:
        """Determine if each finger is up/down based on landmarks."""
        states = {}

        # Thumb (special case - horizontal movement)
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        states["thumb"] = "out" if thumb_tip[0] > thumb_ip[0] else "in"

        # Other fingers - compare tip Y to PIP Y
        finger_names = ["index", "middle", "ring", "pinky"]
        for i, name in enumerate(finger_names):
            tip_idx = self.FINGER_TIPS[i + 1]
            pip_idx = self.FINGER_PIPS[i + 1]
            # Lower Y = higher on screen (finger up)
            states[name] = "up" if landmarks[tip_idx][1] < landmarks[pip_idx][1] else "down"

        return states

    def detect_chord_shape(self, finger_states: dict) -> Optional[ChordShape]:
        """Match finger positions to known chord shapes."""
        best_match = None
        best_score = 0

        for chord_name, expected in self.CHORD_SHAPES.items():
            score = 0
            for finger, expected_state in expected.items():
                if finger in finger_states:
                    actual = finger_states[finger]
                    if expected_state == "bar":
                        # Bar chord - index should be flat
                        score += 0.5 if actual == "down" else 0
                    elif actual == expected_state:
                        score += 1

            normalized_score = score / len(expected)
            if normalized_score > best_score and normalized_score > 0.6:
                best_score = normalized_score
                best_match = ChordShape(
                    name=chord_name,
                    confidence=normalized_score,
                    finger_positions=finger_states,
                    timestamp=time.time(),
                )

        return best_match

    def process_frame(self, frame: np.ndarray) -> List[HandLandmarks]:
        """Process a single frame and return detected hands."""
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process with MediaPipe
        results = self.hands.process(rgb_frame)

        hands = []
        if results.multi_hand_landmarks:
            for i, hand_landmarks in enumerate(results.multi_hand_landmarks):
                # Extract landmarks
                landmarks = [
                    (lm.x, lm.y, lm.z)
                    for lm in hand_landmarks.landmark
                ]

                # Get handedness
                handedness = "Right"
                if results.multi_handedness:
                    handedness = results.multi_handedness[i].classification[0].label
                    confidence = results.multi_handedness[i].classification[0].score
                else:
                    confidence = 0.0

                hands.append(HandLandmarks(
                    landmarks=landmarks,
                    handedness=handedness,
                    confidence=confidence,
                    timestamp=time.time(),
                ))

        return hands

    async def broadcast(self, data: dict):
        """Broadcast data to WebSocket clients."""
        if not self.ws_clients:
            return

        message = json.dumps(data)
        disconnected = set()

        for ws in self.ws_clients:
            try:
                await ws.send(message)
            except:
                disconnected.add(ws)

        self.ws_clients -= disconnected

    async def websocket_handler(self, websocket, path):
        """Handle WebSocket connections."""
        self.ws_clients.add(websocket)
        print(f"[ROXY.VISION] Client connected ({len(self.ws_clients)} total)")

        try:
            async for message in websocket:
                data = json.loads(message)
                if data.get("type") == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))
        except:
            pass
        finally:
            self.ws_clients.discard(websocket)
            print(f"[ROXY.VISION] Client disconnected ({len(self.ws_clients)} remaining)")

    async def capture_loop(self):
        """Main capture and processing loop."""
        cap = cv2.VideoCapture(self.camera_id)

        if not cap.isOpened():
            print(f"[ROXY.VISION] ERROR: Cannot open camera {self.camera_id}")
            return

        # Set camera properties for low latency
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        print(f"[ROXY.VISION] Camera opened, starting capture...")
        self.running = True

        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    await asyncio.sleep(0.01)
                    continue

                # Process frame
                self.current_hands = self.process_frame(frame)
                self.frames_processed += 1

                # Update FPS
                now = time.time()
                if now - self.last_fps_time >= 1.0:
                    self.fps = self.frames_processed / (now - self.last_fps_time)
                    self.frames_processed = 0
                    self.last_fps_time = now

                # Detect chord shapes
                for hand in self.current_hands:
                    if hand.handedness == "Left":  # Fret hand for right-handed guitar
                        finger_states = self.get_finger_state(hand.landmarks)
                        chord = self.detect_chord_shape(finger_states)

                        if chord and (not self.current_chord or
                                      chord.name != self.current_chord.name):
                            self.current_chord = chord
                            print(f"[ROXY.VISION] Chord: {chord.name} "
                                  f"(confidence={chord.confidence:.2f})")

                            # Broadcast
                            await self.broadcast({
                                "type": "chord_shape",
                                "data": {
                                    "chord": chord.name,
                                    "confidence": chord.confidence,
                                    "fingers": chord.finger_positions,
                                    "timestamp": chord.timestamp,
                                }
                            })

                # Broadcast hand data
                if self.current_hands:
                    await self.broadcast({
                        "type": "hands",
                        "data": {
                            "count": len(self.current_hands),
                            "hands": [
                                {
                                    "handedness": h.handedness,
                                    "confidence": h.confidence,
                                    "landmarks": h.landmarks[:5],  # Just fingertips for bandwidth
                                }
                                for h in self.current_hands
                            ],
                            "fps": self.fps,
                        }
                    })

                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.001)

        finally:
            cap.release()
            self.running = False
            print("[ROXY.VISION] Camera released")

    async def run(self):
        """Start hand tracker with WebSocket server."""
        print(f"[ROXY.VISION] Starting on port {self.websocket_port}...")

        if websockets:
            async with websockets.serve(
                self.websocket_handler,
                "127.0.0.1",
                self.websocket_port
            ):
                print(f"[ROXY.VISION] WebSocket server ready")
                await self.capture_loop()
        else:
            print("[ROXY.VISION] WebSockets not available, running capture only")
            await self.capture_loop()


async def main():
    tracker = RoxyHandTracker(
        camera_id=0,
        websocket_port=8768,
    )
    await tracker.run()


if __name__ == "__main__":
    asyncio.run(main())
