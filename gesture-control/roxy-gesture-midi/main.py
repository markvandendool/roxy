#!/usr/bin/env python3
"""
ROXY Gesture to OBS Controller
Main application combining gesture recognition with MIDI output to OBS
"""
import cv2
import time
import argparse
import logging
from typing import Optional, Dict
from gesture_recognition import HandTracker, GestureType, HandPosition, GESTURE_OBS_MAPPING
from midi_controller import OBSMidiController

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class GestureOBSController:
    """Main controller connecting gesture recognition to OBS via MIDI"""
    
    def __init__(self, midi_port: Optional[str] = None, camera_id: int = 0,
                 gesture_cooldown: float = 0.5, show_preview: bool = True):
        """
        Initialize the gesture-to-OBS controller.
        
        Args:
            midi_port: MIDI port name (None for auto-detect)
            camera_id: Camera device ID
            gesture_cooldown: Minimum time between repeated gestures (seconds)
            show_preview: Whether to show the camera preview window
        """
        self.camera_id = camera_id
        self.gesture_cooldown = gesture_cooldown
        self.show_preview = show_preview
        
        # Gesture timing
        self.last_gesture_time: Dict[GestureType, float] = {}
        self.current_gesture: Optional[GestureType] = None
        self.gesture_start_time: float = 0
        self.gesture_hold_threshold = 0.3  # Seconds to hold gesture before action
        
        # Scene navigation state
        self.current_scene = 1
        self.max_scenes = 8
        
        # Initialize components
        logger.info("Initializing hand tracker...")
        self.hand_tracker = HandTracker(max_hands=2)
        
        logger.info("Initializing MIDI controller...")
        self.midi_controller = OBSMidiController(midi_port)
        
        logger.info("Opening camera...")
        self.camera = cv2.VideoCapture(camera_id)
        if not self.camera.isOpened():
            raise RuntimeError(f"Failed to open camera {camera_id}")
        
        # Set camera resolution
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        logger.info("Gesture-to-OBS controller initialized!")
    
    def _can_trigger_gesture(self, gesture: GestureType) -> bool:
        """Check if enough time has passed since last trigger of this gesture"""
        last_time = self.last_gesture_time.get(gesture, 0)
        return time.time() - last_time >= self.gesture_cooldown
    
    def _execute_obs_action(self, action: str) -> bool:
        """Execute an OBS action via MIDI"""
        # Handle special navigation actions
        if action == 'prev_scene':
            self.current_scene = max(1, self.current_scene - 1)
            return self.midi_controller.send_scene(self.current_scene)
        
        elif action == 'next_scene':
            self.current_scene = min(self.max_scenes, self.current_scene + 1)
            return self.midi_controller.send_scene(self.current_scene)
        
        # Handle direct scene switches
        elif action.startswith('scene_'):
            scene_num = int(action.split('_')[1])
            self.current_scene = scene_num
            return self.midi_controller.send_scene(scene_num)
        
        # Handle other actions
        else:
            return self.midi_controller.send_action(action)
    
    def _process_gesture(self, hand: HandPosition):
        """Process detected gesture and trigger OBS action if appropriate"""
        gesture = hand.gesture
        
        if gesture == GestureType.NONE or gesture == GestureType.OPEN_PALM:
            # Reset gesture state on neutral gestures
            self.current_gesture = None
            return
        
        # Get mapped OBS action
        action = GESTURE_OBS_MAPPING.get(gesture)
        if not action:
            return
        
        # Check if this is a new gesture or continuation
        current_time = time.time()
        
        if gesture != self.current_gesture:
            # New gesture detected
            self.current_gesture = gesture
            self.gesture_start_time = current_time
            logger.debug(f"New gesture detected: {gesture.value}")
        
        elif current_time - self.gesture_start_time >= self.gesture_hold_threshold:
            # Gesture held long enough
            if self._can_trigger_gesture(gesture):
                logger.info(f"Triggering: {gesture.value} -> {action}")
                
                if self._execute_obs_action(action):
                    self.last_gesture_time[gesture] = current_time
                    # Visual feedback would go here
    
    def _process_continuous_controls(self, hands: list):
        """Process hand position for continuous OBS controls"""
        if not hands:
            return
        
        # Use primary hand (first detected) for continuous control
        primary = hands[0]
        
        # Map Y position to zoom (hand high = zoom in)
        # zoom_value = 1.0 - primary.y  # Inverted so higher hand = more zoom
        # self.midi_controller.send_continuous('zoom_level', zoom_value)
        
        # Map X position could control blur or other effects
        # Only enable these when specific gesture is held
        pass
    
    def _draw_overlay(self, frame) -> None:
        """Draw status overlay on the frame"""
        h, w, _ = frame.shape
        
        # Draw current scene indicator
        cv2.putText(frame, f"Scene: {self.current_scene}/{self.max_scenes}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # Draw gesture hint box
        hints = [
            "Gestures:",
            "Point = Scene 1",
            "Peace = Scene 2",
            "3 Fingers = Scene 3",
            "Fist = Mute",
            "Thumbs Up = Record",
            "Pinch = Toggle Cam",
            "Swipe L/R = Prev/Next"
        ]
        
        y_offset = 60
        for hint in hints:
            cv2.putText(frame, hint, (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 20
    
    def run(self):
        """Main processing loop"""
        logger.info("Starting gesture recognition loop...")
        logger.info("Press 'q' to quit, 'r' to reset scene to 1")
        
        fps_time = time.time()
        frame_count = 0
        
        try:
            while True:
                ret, frame = self.camera.read()
                if not ret:
                    logger.error("Failed to read from camera")
                    break
                
                # Process frame
                annotated_frame, hands = self.hand_tracker.process_frame(frame)
                
                # Process gestures for each hand
                for hand in hands:
                    self._process_gesture(hand)
                
                # Process continuous controls
                self._process_continuous_controls(hands)
                
                if self.show_preview:
                    # Draw overlay
                    self._draw_overlay(annotated_frame)
                    
                    # Calculate FPS
                    frame_count += 1
                    if time.time() - fps_time >= 1.0:
                        fps = frame_count / (time.time() - fps_time)
                        frame_count = 0
                        fps_time = time.time()
                        cv2.putText(annotated_frame, f"FPS: {fps:.1f}",
                                    (annotated_frame.shape[1] - 120, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    cv2.imshow('ROXY Gesture OBS Control', annotated_frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    logger.info("Quit requested")
                    break
                elif key == ord('r'):
                    self.current_scene = 1
                    self.midi_controller.send_scene(1)
                    logger.info("Reset to Scene 1")
                elif ord('1') <= key <= ord('8'):
                    scene = key - ord('0')
                    self.current_scene = scene
                    self.midi_controller.send_scene(scene)
                    logger.info(f"Manual scene switch: {scene}")
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        
        finally:
            self.close()
    
    def close(self):
        """Clean up resources"""
        logger.info("Shutting down...")
        self.camera.release()
        cv2.destroyAllWindows()
        self.hand_tracker.close()
        self.midi_controller.close()
        logger.info("Shutdown complete")


def main():
    parser = argparse.ArgumentParser(
        description='ROXY Gesture to OBS Controller',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Gestures:
  Point (1 finger)    -> Scene 1
  Peace (2 fingers)   -> Scene 2
  3 fingers           -> Scene 3
  4 fingers           -> Scene 4
  Rock on             -> Scene 5
  Thumbs up           -> Start recording
  Closed fist         -> Toggle mute
  Pinch               -> Toggle camera
  Swipe left/right    -> Previous/Next scene
  Swipe up            -> Toggle overlay
  Swipe down          -> Stop recording
  Open palm           -> Neutral (no action)

Keyboard shortcuts (in preview window):
  q         -> Quit
  r         -> Reset to Scene 1
  1-8       -> Direct scene switch
'''
    )
    
    parser.add_argument('--midi-port', '-m', type=str, default=None,
                        help='MIDI port name (default: auto-detect virtual MIDI)')
    parser.add_argument('--camera', '-c', type=int, default=0,
                        help='Camera device ID (default: 0)')
    parser.add_argument('--cooldown', '-d', type=float, default=0.5,
                        help='Gesture cooldown in seconds (default: 0.5)')
    parser.add_argument('--no-preview', action='store_true',
                        help='Disable camera preview window')
    parser.add_argument('--list-midi', action='store_true',
                        help='List available MIDI ports and exit')
    parser.add_argument('--list-cameras', action='store_true',
                        help='List available cameras and exit')
    
    args = parser.parse_args()
    
    if args.list_midi:
        import mido
        print("Available MIDI outputs:")
        for port in mido.get_output_names():
            print(f"  - {port}")
        return
    
    if args.list_cameras:
        print("Checking cameras...")
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(f"  Camera {i}: {w}x{h}")
                cap.release()
        return
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║           ROXY Gesture to OBS Controller                  ║
║                                                           ║
║  Hand gestures -> MIDI -> obs-midi-mg -> OBS Studio       ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    controller = GestureOBSController(
        midi_port=args.midi_port,
        camera_id=args.camera,
        gesture_cooldown=args.cooldown,
        show_preview=not args.no_preview
    )
    
    controller.run()


if __name__ == '__main__':
    main()
