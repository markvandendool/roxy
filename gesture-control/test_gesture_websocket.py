#!/usr/bin/env python3
"""
Roxy OBS Gesture Test - Direct WebSocket Control
Tests gesture detection triggering OBS recording via WebSocket.
Bypasses MIDI plugin for direct control.
"""
import asyncio
import json
import time
import websockets

# OBS WebSocket configuration  
OBS_HOST = 'localhost'
OBS_PORT = 4455

class OBSWebSocket:
    """OBS WebSocket v5 client"""
    
    def __init__(self, host: str = OBS_HOST, port: int = OBS_PORT):
        self.host = host
        self.port = port
        self.ws = None
        self.message_id = 0
        
    async def connect(self):
        uri = f'ws://{self.host}:{self.port}'
        self.ws = await websockets.connect(uri)
        
        # Receive Hello
        hello = json.loads(await self.ws.recv())
        
        # Identify (no auth)
        await self.ws.send(json.dumps({'op': 1, 'd': {'rpcVersion': 1}}))
        identified = json.loads(await self.ws.recv())
        
        if identified.get('op') != 2:
            raise Exception(f'OBS auth failed: {identified}')
        
        return True
    
    async def disconnect(self):
        if self.ws:
            await self.ws.close()
            self.ws = None
    
    async def call(self, request_type: str, request_data: dict = None) -> dict:
        if not self.ws:
            await self.connect()
        
        self.message_id += 1
        request = {
            'op': 6,
            'd': {
                'requestType': request_type,
                'requestId': str(self.message_id)
            }
        }
        if request_data:
            request['d']['requestData'] = request_data
        
        await self.ws.send(json.dumps(request))
        
        while True:
            response = json.loads(await self.ws.recv())
            if response.get('op') == 7 and response.get('d', {}).get('requestId') == str(self.message_id):
                return response['d']


def detect_gesture():
    """
    Simulated gesture detection.
    In real implementation, this would use MediaPipe to detect hand gestures.
    Returns True if "thumbs up" gesture detected.
    """
    # Simulate gesture detection
    print("🖐️  Simulating gesture detection...")
    time.sleep(0.5)
    print("👍 Thumbs up gesture detected!")
    return True


async def gesture_triggered_action(obs: OBSWebSocket, action: str):
    """Execute OBS action triggered by gesture"""
    if action == "toggle_recording":
        result = await obs.call('ToggleRecord')
        is_recording = result.get('responseData', {}).get('outputActive', False)
        return is_recording
    return None


async def main():
    print("=" * 50)
    print("🎮 Roxy Gesture Control Test")
    print("=" * 50)
    
    obs = OBSWebSocket()
    
    try:
        print("\n📡 Connecting to OBS WebSocket...")
        await obs.connect()
        print("✅ Connected to OBS")
        
        # Get initial status
        status = await obs.call('GetRecordStatus')
        initial_recording = status.get('responseData', {}).get('outputActive', False)
        print(f"\n📊 Initial recording status: {'🔴 Recording' if initial_recording else '⚪ Not Recording'}")
        
        # Simulate gesture detection
        print("\n" + "-" * 40)
        if detect_gesture():
            print("\n🚀 Triggering OBS action...")
            is_recording = await gesture_triggered_action(obs, "toggle_recording")
            print(f"\n📊 New recording status: {'🔴 Recording' if is_recording else '⚪ Not Recording'}")
            
            if initial_recording != is_recording:
                print("\n✅ SUCCESS! Gesture triggered recording state change!")
            else:
                print("\n⚠️ WARNING: Recording state didn't change as expected")
        
        # Optional: Toggle back to original state
        print("\n" + "-" * 40)
        print("🔄 Toggling back to original state...")
        await gesture_triggered_action(obs, "toggle_recording")
        
        final_status = await obs.call('GetRecordStatus')
        final_recording = final_status.get('responseData', {}).get('outputActive', False)
        print(f"📊 Final recording status: {'🔴 Recording' if final_recording else '⚪ Not Recording'}")
        
        if final_recording == initial_recording:
            print("✅ Returned to original state")
        
        print("\n" + "=" * 50)
        print("🎉 Gesture Control Test Complete!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await obs.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
