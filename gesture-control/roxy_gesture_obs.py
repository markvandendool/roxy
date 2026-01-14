#!/usr/bin/env python3
"""
Roxy Gesture-Controlled OBS
Real-time hand gesture recognition using MediaPipe to control OBS.

Gestures:
- 👍 Thumbs Up: Toggle Recording
- ✋ Open Palm: Start Recording  
- ✊ Closed Fist: Stop Recording
- ✌️ Peace Sign: Take Screenshot
"""
import asyncio
import json
import time
import cv2
import mediapipe as mp
import websockets
from threading import Thread
from queue import Queue
import signal
import sys

# OBS WebSocket configuration
OBS_HOST = 'localhost'
OBS_PORT = 4455

# Gesture detection settings
GESTURE_COOLDOWN = 2.0  # Seconds between actions
GESTURE_CONFIDENCE = 0.7  # Hand detection confidence threshold


class OBSWebSocket:
    """Async OBS WebSocket v5 client"""
    
    def __init__(self, host: str = OBS_HOST, port: int = OBS_PORT):
        self.host = host
        self.port = port
        self.ws = None
        self.message_id = 0
        
    async def connect(self):
        uri = f'ws://{self.host}:{self.port}'
        self.ws = await websockets.connect(uri)
        await self.ws.recv()  # Hello
        await self.ws.send(json.dumps({'op': 1, 'd': {'rpcVersion': 1}}))
        identified = json.loads(await self.ws.recv())
        if identified.get('op') != 2:
            raise Exception(f'OBS auth failed: {identified}')
        return True
    
    async def disconnect(self):
        if self.ws:
            await self.ws.close()
    
    async def call(self, request_type: str, request_data: dict = None) -> dict:
        self.message_id += 1
        request = {'op': 6, 'd': {'requestType': request_type, 'requestId': str(self.message_id)}}
        if request_data:
            request['d']['requestData'] = request_data
        await self.ws.send(json.dumps(request))
        while True:
            response = json.loads(await self.ws.recv())
            if response.get('op') == 7 and response.get('d', {}).get('requestId') == str(self.message_id):
                return response['d']


class GestureDetector:
    """MediaPipe hand gesture detector"""
    
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=GESTURE_CONFIDENCE,
            min_tracking_confidence=0.5
        )
        self.last_gesture_time = 0
        
    def detect(self, frame):
        """Detect hand gesture in frame"""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)
        
        gesture = None
        landmarks = None
        
        if results.multi_hand_landmarks:
            hand = results.multi_hand_landmarks[0]
            landmarks = hand
            
            # Get finger states (extended or not)
            fingers = self._get_finger_states(hand)
            
            # Detect gestures
            if self._is_thumbs_up(hand, fingers):
                gesture = "thumbs_up"
            elif self._is_open_palm(fingers):
                gesture = "open_palm"
            elif self._is_closed_fist(fingers):
                gesture = "closed_fist"
            elif self._is_peace_sign(fingers):
                gesture = "peace_sign"
        
        return gesture, landmarks
    
    def _get_finger_states(self, hand):
        """Get which fingers are extended"""
        lm = hand.landmark
        
        # Finger tip and base indices
        tips = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky
        bases = [2, 6, 10, 14, 18]
        
        fingers = []
        
        # Thumb (check x for left/right hand)
        if lm[tips[0]].x < lm[bases[0]].x:
            fingers.append(True)  # Thumb extended
        else:
            fingers.append(False)
        
        # Other fingers (check y - lower is extended)
        for i in range(1, 5):
            if lm[tips[i]].y < lm[bases[i]].y:
                fingers.append(True)
            else:
                fingers.append(False)
        
        return fingers
    
    def _is_thumbs_up(self, hand, fingers):
        """Thumb up, other fingers closed"""
        lm = hand.landmark
        # Thumb should be above other fingertips
        thumb_tip = lm[4]
        return (fingers[0] and not any(fingers[1:]) and 
                thumb_tip.y < lm[8].y)  # Thumb above index
    
    def _is_open_palm(self, fingers):
        """All fingers extended"""
        return all(fingers)
    
    def _is_closed_fist(self, fingers):
        """All fingers closed"""
        return not any(fingers)
    
    def _is_peace_sign(self, fingers):
        """Index and middle extended, others closed"""
        return (not fingers[0] and  # Thumb closed
                fingers[1] and      # Index extended
                fingers[2] and      # Middle extended
                not fingers[3] and  # Ring closed
                not fingers[4])     # Pinky closed
    
    def should_trigger(self):
        """Check if enough time passed since last gesture"""
        now = time.time()
        if now - self.last_gesture_time > GESTURE_COOLDOWN:
            self.last_gesture_time = now
            return True
        return False
    
    def draw_landmarks(self, frame, landmarks):
        """Draw hand landmarks on frame"""
        if landmarks:
            self.mp_draw.draw_landmarks(
                frame, landmarks, self.mp_hands.HAND_CONNECTIONS
            )


class RoxyGestureController:
    """Main gesture controller for OBS"""
    
    def __init__(self):
        self.obs = OBSWebSocket()
        self.detector = GestureDetector()
        self.action_queue = Queue()
        self.running = False
        self.loop = None
        
    async def connect_obs(self):
        """Connect to OBS"""
        try:
            await self.obs.connect()
            print("✅ Connected to OBS")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to OBS: {e}")
            return False
    
    async def execute_gesture_action(self, gesture: str):
        """Execute OBS action for gesture"""
        try:
            if gesture == "thumbs_up":
                result = await self.obs.call('ToggleRecord')
                is_rec = result.get('responseData', {}).get('outputActive', False)
                print(f"👍 Toggle Recording: {'🔴 Started' if is_rec else '⚪ Stopped'}")
                
            elif gesture == "open_palm":
                status = await self.obs.call('GetRecordStatus')
                if not status.get('responseData', {}).get('outputActive', False):
                    await self.obs.call('StartRecord')
                    print("✋ Started Recording 🔴")
                else:
                    print("✋ Already Recording")
                    
            elif gesture == "closed_fist":
                status = await self.obs.call('GetRecordStatus')
                if status.get('responseData', {}).get('outputActive', False):
                    await self.obs.call('StopRecord')
                    print("✊ Stopped Recording ⚪")
                else:
                    print("✊ Not Recording")
                    
            elif gesture == "peace_sign":
                await self.obs.call('SaveSourceScreenshot', {
                    'sourceName': 'Scene',
                    'imageFormat': 'png',
                    'imageFilePath': f'/home/mark/Pictures/screenshot_{int(time.time())}.png'
                })
                print("✌️ Screenshot saved!")
                
        except Exception as e:
            print(f"❌ Action error: {e}")
    
    async def process_actions(self):
        """Process action queue"""
        while self.running:
            if not self.action_queue.empty():
                gesture = self.action_queue.get()
                await self.execute_gesture_action(gesture)
            await asyncio.sleep(0.1)
    
    def camera_loop(self):
        """Camera capture and gesture detection loop"""
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Cannot open camera")
            self.running = False
            return
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        print("\n🎥 Camera active - Show gestures to control OBS")
        print("   👍 Thumbs Up: Toggle Recording")
        print("   ✋ Open Palm: Start Recording")
        print("   ✊ Closed Fist: Stop Recording")
        print("   ✌️ Peace Sign: Screenshot")
        print("   Press 'q' to quit\n")
        
        while self.running:
            ret, frame = cap.read()
            if not ret:
                continue
            
            frame = cv2.flip(frame, 1)  # Mirror
            
            gesture, landmarks = self.detector.detect(frame)
            self.detector.draw_landmarks(frame, landmarks)
            
            # Display gesture
            status = "No gesture"
            color = (200, 200, 200)
            if gesture:
                status = {
                    "thumbs_up": "👍 Thumbs Up",
                    "open_palm": "✋ Open Palm",
                    "closed_fist": "✊ Closed Fist",
                    "peace_sign": "✌️ Peace Sign"
                }.get(gesture, gesture)
                color = (0, 255, 0)
                
                if self.detector.should_trigger():
                    self.action_queue.put(gesture)
                    color = (0, 255, 255)
            
            cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                       1, color, 2)
            cv2.putText(frame, "Roxy Gesture Control", (10, 470), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
            
            cv2.imshow('Roxy Gesture Control', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.running = False
                break
        
        cap.release()
        cv2.destroyAllWindows()
    
    async def run(self):
        """Main run loop"""
        self.running = True
        
        if not await self.connect_obs():
            return
        
        # Start camera in separate thread
        camera_thread = Thread(target=self.camera_loop, daemon=True)
        camera_thread.start()
        
        # Process actions in main async loop
        await self.process_actions()
        
        await self.obs.disconnect()
        print("\n👋 Roxy Gesture Control stopped")


def main():
    print("=" * 50)
    print("🤖 Roxy Gesture-Controlled OBS")
    print("=" * 50)
    
    controller = RoxyGestureController()
    
    def signal_handler(sig, frame):
        print("\n🛑 Stopping...")
        controller.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        asyncio.run(controller.run())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
