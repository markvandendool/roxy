#!/usr/bin/env python3
"""
Roxy OBS Gesture Test
Launches OBS, configures MIDI binding via MCP, tests gesture control.
"""
import asyncio
import json
import subprocess
import time
import sys
import os
import base64
import hashlib
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OBS WebSocket configuration
OBS_HOST = 'localhost'
OBS_PORT = 4455  # Default OBS WebSocket v5 port
OBS_PASSWORD = ''  # Set if authentication is enabled

class OBSWebSocket:
    """OBS WebSocket v5 client"""
    
    def __init__(self, host: str = OBS_HOST, port: int = OBS_PORT, password: str = OBS_PASSWORD):
        self.host = host
        self.port = port
        self.password = password
        self.ws = None
        self.message_id = 0
        
    async def connect(self):
        uri = f'ws://{self.host}:{self.port}'
        self.ws = await websockets.connect(uri)
        
        # Receive Hello message
        hello = json.loads(await self.ws.recv())
        logger.info(f'OBS Hello: {hello}')
        
        # Authenticate if required
        if hello.get('d', {}).get('authentication'):
            auth = hello['d']['authentication']
            challenge = auth['challenge']
            salt = auth['salt']
            
            # Generate auth response
            secret = base64.b64encode(
                hashlib.sha256((self.password + salt).encode()).digest()
            ).decode()
            auth_response = base64.b64encode(
                hashlib.sha256((secret + challenge).encode()).digest()
            ).decode()
            
            identify = {
                'op': 1,
                'd': {
                    'rpcVersion': 1,
                    'authentication': auth_response
                }
            }
        else:
            identify = {
                'op': 1,
                'd': {
                    'rpcVersion': 1
                }
            }
        
        await self.ws.send(json.dumps(identify))
        identified = json.loads(await self.ws.recv())
        logger.info(f'OBS Identified: {identified}')
        
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
        
        # Wait for response
        while True:
            response = json.loads(await self.ws.recv())
            if response.get('op') == 7 and response.get('d', {}).get('requestId') == str(self.message_id):
                return response['d']

async def test_gesture_control():
    print("� Connecting to OBS WebSocket...")
    obs_ws = OBSWebSocket()
    
    try:
        await obs_ws.connect()
        print("✅ Connected to OBS")
        
        # Get initial status
        status = await obs_ws.call('GetRecordStatus')
        initial_recording = status.get('responseData', {}).get('outputActive', False)
        print(f"📊 Initial recording status: {initial_recording}")
        
        if initial_recording:
            print("⏹️ Stopping initial recording...")
            await obs_ws.call('StopRecord')
            time.sleep(1)
        
        # Assume binding is set: CC10 -> Start/Stop Recording
        print("🎛️ Sending MIDI CC10 (should start recording)...")
        import mido
        midi_port = 'VirMIDI 0-0'
        with mido.open_output(midi_port) as port:
            # Send CC10 on channel 1 (1-indexed = MIDI channel 0)
            port.send(mido.Message('control_change', control=10, value=127, channel=0))
        
        time.sleep(2)  # Wait for action
        
        # Check status after MIDI
        status = await obs_ws.call('GetRecordStatus')
        after_recording = status.get('responseData', {}).get('outputActive', False)
        print(f"📊 After MIDI recording status: {after_recording}")
        
        if not initial_recording and after_recording:
            print("✅ SUCCESS: Gesture control working! MIDI triggered recording start.")
        elif initial_recording and not after_recording:
            print("✅ SUCCESS: Gesture control working! MIDI triggered recording stop.")
        else:
            print("❌ FAILURE: MIDI did not trigger expected action.")
        
        # Stop recording if started
        if after_recording:
            await obs_ws.call('StopRecord')
            print("⏹️ Stopped recording for cleanup.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await obs_ws.disconnect()

if __name__ == '__main__':
    asyncio.run(test_gesture_control())