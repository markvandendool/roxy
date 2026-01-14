#!/usr/bin/env python3
"""
ROXY Gesture Recognition for OBS Control
Uses MediaPipe hand tracking to detect gestures and send MIDI to OBS
"""
import cv2
import mediapipe as mp
import numpy as np
from typing import Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GestureType(Enum):
    """Recognized gestures for OBS control"""
    NONE = "none"
    OPEN_PALM = "open_palm"           # All fingers extended
    CLOSED_FIST = "closed_fist"       # All fingers closed
    POINTING_UP = "pointing_up"       # Index finger up only
    PEACE_SIGN = "peace_sign"         # Index + middle up
    THUMBS_UP = "thumbs_up"           # Thumb extended
    PINCH = "pinch"                   # Thumb and index touching
    THREE_FINGERS = "three_fingers"   # Index + middle + ring
    FOUR_FINGERS = "four_fingers"     # All except thumb
    ROCK_ON = "rock_on"               # Index + pinky
    SWIPE_LEFT = "swipe_left"         # Motion gesture
    SWIPE_RIGHT = "swipe_right"       # Motion gesture
    SWIPE_UP = "swipe_up"             # Motion gesture
    SWIPE_DOWN = "swipe_down"         # Motion gesture


@dataclass
class HandPosition:
    """Tracked hand position data"""
    x: float  # Normalized 0-1
    y: float  # Normalized 0-1
    z: float  # Depth
    gesture: GestureType
    confidence: float
    is_left_hand: bool
    velocity_x: float = 0.0
    velocity_y: float = 0.0


# MediaPipe hand landmark indices
class HandLandmark:
    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4
    INDEX_MCP = 5
    INDEX_PIP = 6
    INDEX_DIP = 7
    INDEX_TIP = 8
    MIDDLE_MCP = 9
    MIDDLE_PIP = 10
    MIDDLE_DIP = 11
    MIDDLE_TIP = 12
    RING_MCP = 13
    RING_PIP = 14
    RING_DIP = 15
    RING_TIP = 16
    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20


class GestureRecognizer:
    """Recognizes hand gestures from MediaPipe landmarks"""
    
    def __init__(self, motion_threshold: float = 0.05, swipe_velocity: float = 0.3):
        self.motion_threshold = motion_threshold
        self.swipe_velocity = swipe_velocity
        self.prev_position = None
        self.prev_time = None
        
    def _distance(self, p1, p2) -> float:
        """Calculate 3D distance between two landmarks"""
        return np.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)
    
    def _is_finger_extended(self, landmarks, tip_idx: int, pip_idx: int, mcp_idx: int) -> bool:
        """Check if a finger is extended (tip is above PIP joint)"""
        tip = landmarks[tip_idx]
        pip = landmarks[pip_idx]
        mcp = landmarks[mcp_idx]
        
        # For fingers, check if tip is further from palm than PIP
        # Using y-coordinate (inverted: smaller y = higher on screen)
        return tip.y < pip.y
    
    def _is_thumb_extended(self, landmarks, is_left_hand: bool) -> bool:
        """Check if thumb is extended (different logic due to thumb orientation)"""
        thumb_tip = landmarks[HandLandmark.THUMB_TIP]
        thumb_mcp = landmarks[HandLandmark.THUMB_MCP]
        index_mcp = landmarks[HandLandmark.INDEX_MCP]
        
        # Thumb is extended if tip is further from index MCP than thumb MCP
        if is_left_hand:
            return thumb_tip.x > thumb_mcp.x
        else:
            return thumb_tip.x < thumb_mcp.x
    
    def _get_finger_states(self, landmarks, is_left_hand: bool) -> Tuple[bool, bool, bool, bool, bool]:
        """Get extended state of all 5 fingers: (thumb, index, middle, ring, pinky)"""
        thumb = self._is_thumb_extended(landmarks, is_left_hand)
        index = self._is_finger_extended(landmarks, HandLandmark.INDEX_TIP, HandLandmark.INDEX_PIP, HandLandmark.INDEX_MCP)
        middle = self._is_finger_extended(landmarks, HandLandmark.MIDDLE_TIP, HandLandmark.MIDDLE_PIP, HandLandmark.MIDDLE_MCP)
        ring = self._is_finger_extended(landmarks, HandLandmark.RING_TIP, HandLandmark.RING_PIP, HandLandmark.RING_MCP)
        pinky = self._is_finger_extended(landmarks, HandLandmark.PINKY_TIP, HandLandmark.PINKY_PIP, HandLandmark.PINKY_MCP)
        
        return (thumb, index, middle, ring, pinky)
    
    def recognize(self, landmarks, is_left_hand: bool = False) -> Tuple[GestureType, float]:
        """Recognize gesture from hand landmarks"""
        if not landmarks:
            return GestureType.NONE, 0.0
        
        fingers = self._get_finger_states(landmarks, is_left_hand)
        thumb, index, middle, ring, pinky = fingers
        
        # Count extended fingers
        extended_count = sum(fingers)
        
        # Check for pinch (thumb tip near index tip)
        pinch_distance = self._distance(landmarks[HandLandmark.THUMB_TIP], landmarks[HandLandmark.INDEX_TIP])
        if pinch_distance < 0.05:
            return GestureType.PINCH, 0.95
        
        # Static gestures based on finger states
        if extended_count == 0:
            return GestureType.CLOSED_FIST, 0.9
        
        if extended_count == 5:
            return GestureType.OPEN_PALM, 0.9
        
        if thumb and not index and not middle and not ring and not pinky:
            return GestureType.THUMBS_UP, 0.85
        
        if not thumb and index and not middle and not ring and not pinky:
            return GestureType.POINTING_UP, 0.9
        
        if not thumb and index and middle and not ring and not pinky:
            return GestureType.PEACE_SIGN, 0.9
        
        if not thumb and index and middle and ring and not pinky:
            return GestureType.THREE_FINGERS, 0.85
        
        if not thumb and index and middle and ring and pinky:
            return GestureType.FOUR_FINGERS, 0.85
        
        if not thumb and index and not middle and not ring and pinky:
            return GestureType.ROCK_ON, 0.8
        
        return GestureType.NONE, 0.0
    
    def detect_motion(self, current_pos: Tuple[float, float], current_time: float) -> Optional[GestureType]:
        """Detect swipe gestures from motion"""
        if self.prev_position is None or self.prev_time is None:
            self.prev_position = current_pos
            self.prev_time = current_time
            return None
        
        dt = current_time - self.prev_time
        if dt <= 0:
            return None
        
        dx = current_pos[0] - self.prev_position[0]
        dy = current_pos[1] - self.prev_position[1]
        
        velocity_x = dx / dt
        velocity_y = dy / dt
        
        self.prev_position = current_pos
        self.prev_time = current_time
        
        # Detect swipes
        if abs(velocity_x) > self.swipe_velocity and abs(velocity_x) > abs(velocity_y):
            if velocity_x > 0:
                return GestureType.SWIPE_RIGHT
            else:
                return GestureType.SWIPE_LEFT
        
        if abs(velocity_y) > self.swipe_velocity and abs(velocity_y) > abs(velocity_x):
            if velocity_y > 0:
                return GestureType.SWIPE_DOWN
            else:
                return GestureType.SWIPE_UP
        
        return None


class HandTracker:
    """Hand tracking with MediaPipe"""
    
    def __init__(self, max_hands: int = 2, min_detection_confidence: float = 0.7,
                 min_tracking_confidence: float = 0.5):
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            max_num_hands=max_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.gesture_recognizer = GestureRecognizer()
    
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, List[HandPosition]]:
        """Process a frame and return annotated frame + hand positions"""
        # Flip for selfie view
        frame = cv2.flip(frame, 1)
        
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        hand_positions = []
        current_time = time.time()
        
        if results.multi_hand_landmarks:
            for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                # Draw landmarks
                self.mp_draw.draw_landmarks(
                    frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
                )
                
                # Determine hand type
                is_left = False
                if results.multi_handedness:
                    handedness = results.multi_handedness[idx].classification[0]
                    # MediaPipe reports handedness as if looking at the person
                    is_left = handedness.label == 'Right'  # Flipped due to mirror
                
                # Get palm center (wrist)
                wrist = hand_landmarks.landmark[HandLandmark.WRIST]
                
                # Recognize gesture
                gesture, confidence = self.gesture_recognizer.recognize(
                    hand_landmarks.landmark, is_left
                )
                
                # Detect motion gestures
                motion_gesture = self.gesture_recognizer.detect_motion(
                    (wrist.x, wrist.y), current_time
                )
                
                # Use motion gesture if detected
                if motion_gesture:
                    gesture = motion_gesture
                    confidence = 0.7
                
                hand_pos = HandPosition(
                    x=wrist.x,
                    y=wrist.y,
                    z=wrist.z,
                    gesture=gesture,
                    confidence=confidence,
                    is_left_hand=is_left
                )
                hand_positions.append(hand_pos)
                
                # Draw gesture label
                h, w, _ = frame.shape
                text_pos = (int(wrist.x * w), int(wrist.y * h) - 20)
                cv2.putText(
                    frame, f"{gesture.value} ({confidence:.2f})",
                    text_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
                )
        
        return frame, hand_positions
    
    def close(self):
        """Release resources"""
        self.hands.close()


# Gesture to OBS action mapping
GESTURE_OBS_MAPPING = {
    GestureType.OPEN_PALM: None,  # No action, neutral
    GestureType.CLOSED_FIST: 'toggle_mute',
    GestureType.POINTING_UP: 'scene_1',
    GestureType.PEACE_SIGN: 'scene_2',
    GestureType.THREE_FINGERS: 'scene_3',
    GestureType.FOUR_FINGERS: 'scene_4',
    GestureType.THUMBS_UP: 'start_recording',
    GestureType.PINCH: 'toggle_camera',
    GestureType.ROCK_ON: 'scene_5',
    GestureType.SWIPE_LEFT: 'prev_scene',
    GestureType.SWIPE_RIGHT: 'next_scene',
    GestureType.SWIPE_UP: 'toggle_overlay',
    GestureType.SWIPE_DOWN: 'stop_recording',
}


if __name__ == '__main__':
    print("=== ROXY Gesture Recognition Test ===")
    print("Gestures:")
    for gesture, action in GESTURE_OBS_MAPPING.items():
        if action:
            print(f"  {gesture.value:15} -> {action}")
    
    print("\nStarting camera... Press 'q' to quit")
    
    cap = cv2.VideoCapture(0)
    tracker = HandTracker()
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        annotated_frame, hands = tracker.process_frame(frame)
        
        # Display gesture info
        for hand in hands:
            action = GESTURE_OBS_MAPPING.get(hand.gesture)
            if action:
                print(f"[{hand.gesture.value}] -> OBS: {action}")
        
        cv2.imshow('ROXY Gesture Control', annotated_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    tracker.close()
