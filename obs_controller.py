#!/usr/bin/env python3
"""
OBS WebSocket Controller for ROXY
Voice-controlled OBS Studio integration

Usage:
  python3 obs_controller.py start-stream
  python3 obs_controller.py stop-stream
  python3 obs_controller.py start-recording
  python3 obs_controller.py stop-recording
  python3 obs_controller.py scene <scene_name>
  python3 obs_controller.py status

Part of LUNA-000 CITADEL - Content Pipeline
"""

import sys
import json
import hashlib
import base64
import asyncio
from pathlib import Path

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    print("[WARN] websockets not installed. Run: pip install websockets")

# OBS WebSocket settings (OBS 28+ has built-in WebSocket)
OBS_HOST = "localhost"
OBS_PORT = 4455
OBS_PASSWORD = ""  # Set if you enable authentication in OBS

class OBSController:
    def __init__(self, host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD):
        self.host = host
        self.port = port
        self.password = password
        self.ws = None
        self.message_id = 0

    async def connect(self):
        """Connect to OBS WebSocket"""
        uri = f"ws://{self.host}:{self.port}"
        try:
            self.ws = await websockets.connect(uri)

            # Receive hello message
            hello = json.loads(await self.ws.recv())

            if hello.get("op") == 0:  # Hello
                # Identify ourselves
                identify_payload = {
                    "op": 1,  # Identify
                    "d": {
                        "rpcVersion": 1
                    }
                }

                # Add authentication if password set
                if self.password and hello["d"].get("authentication"):
                    auth = hello["d"]["authentication"]
                    secret = base64.b64encode(
                        hashlib.sha256(
                            (self.password + auth["salt"]).encode()
                        ).digest()
                    ).decode()
                    auth_string = base64.b64encode(
                        hashlib.sha256(
                            (secret + auth["challenge"]).encode()
                        ).digest()
                    ).decode()
                    identify_payload["d"]["authentication"] = auth_string

                await self.ws.send(json.dumps(identify_payload))

                # Wait for identified response
                identified = json.loads(await self.ws.recv())
                if identified.get("op") == 2:  # Identified
                    return True

            return False

        except Exception as e:
            print(f"[ERROR] Failed to connect to OBS: {e}")
            return False

    async def send_request(self, request_type, request_data=None):
        """Send a request to OBS"""
        self.message_id += 1

        message = {
            "op": 6,  # Request
            "d": {
                "requestType": request_type,
                "requestId": str(self.message_id)
            }
        }

        if request_data:
            message["d"]["requestData"] = request_data

        await self.ws.send(json.dumps(message))

        # Wait for response
        response = json.loads(await self.ws.recv())

        if response.get("op") == 7:  # RequestResponse
            return response["d"]

        return None

    async def disconnect(self):
        """Disconnect from OBS"""
        if self.ws:
            await self.ws.close()

    # === Control Methods ===

    async def start_streaming(self):
        """Start streaming"""
        result = await self.send_request("StartStream")
        return result

    async def stop_streaming(self):
        """Stop streaming"""
        result = await self.send_request("StopStream")
        return result

    async def start_recording(self):
        """Start recording"""
        result = await self.send_request("StartRecord")
        return result

    async def stop_recording(self):
        """Stop recording"""
        result = await self.send_request("StopRecord")
        return result

    async def set_scene(self, scene_name):
        """Switch to a scene"""
        result = await self.send_request("SetCurrentProgramScene", {
            "sceneName": scene_name
        })
        return result

    async def get_scene_list(self):
        """Get list of scenes"""
        result = await self.send_request("GetSceneList")
        return result

    async def get_stream_status(self):
        """Get streaming status"""
        result = await self.send_request("GetStreamStatus")
        return result

    async def get_record_status(self):
        """Get recording status"""
        result = await self.send_request("GetRecordStatus")
        return result

    async def get_stats(self):
        """Get OBS stats"""
        result = await self.send_request("GetStats")
        return result


async def main():
    if not HAS_WEBSOCKETS:
        print("Please install websockets: pip install websockets")
        return

    if len(sys.argv) < 2:
        print("Usage: obs_controller.py <command> [args]")
        print("Commands:")
        print("  start-stream    - Start streaming")
        print("  stop-stream     - Stop streaming")
        print("  start-recording - Start recording")
        print("  stop-recording  - Stop recording")
        print("  scene <name>    - Switch to scene")
        print("  scenes          - List all scenes")
        print("  status          - Get current status")
        return

    command = sys.argv[1].lower()

    obs = OBSController()

    if not await obs.connect():
        print("[ERROR] Could not connect to OBS. Is OBS running with WebSocket enabled?")
        print("  1. Open OBS")
        print("  2. Tools -> WebSocket Server Settings")
        print("  3. Enable WebSocket Server")
        return

    try:
        if command == "start-stream":
            result = await obs.start_streaming()
            print("[OBS] Streaming started" if result else "[OBS] Failed to start stream")

        elif command == "stop-stream":
            result = await obs.stop_streaming()
            print("[OBS] Streaming stopped" if result else "[OBS] Failed to stop stream")

        elif command == "start-recording":
            result = await obs.start_recording()
            print("[OBS] Recording started" if result else "[OBS] Failed to start recording")

        elif command == "stop-recording":
            result = await obs.stop_recording()
            print("[OBS] Recording stopped" if result else "[OBS] Failed to stop recording")

        elif command == "scene" and len(sys.argv) > 2:
            scene_name = " ".join(sys.argv[2:])
            result = await obs.set_scene(scene_name)
            print(f"[OBS] Switched to scene: {scene_name}" if result else f"[OBS] Failed to switch scene")

        elif command == "scenes":
            result = await obs.get_scene_list()
            if result and "responseData" in result:
                scenes = result["responseData"].get("scenes", [])
                current = result["responseData"].get("currentProgramSceneName", "")
                print("[OBS] Available scenes:")
                for scene in scenes:
                    marker = " *" if scene["sceneName"] == current else ""
                    print(f"  - {scene['sceneName']}{marker}")

        elif command == "status":
            stream = await obs.get_stream_status()
            record = await obs.get_record_status()
            stats = await obs.get_stats()

            print("[OBS] Status:")
            if stream and "responseData" in stream:
                s = stream["responseData"]
                print(f"  Streaming: {'LIVE' if s.get('outputActive') else 'OFF'}")
                if s.get('outputActive'):
                    print(f"    Duration: {s.get('outputTimecode', 'N/A')}")

            if record and "responseData" in record:
                r = record["responseData"]
                print(f"  Recording: {'RECORDING' if r.get('outputActive') else 'OFF'}")
                if r.get('outputActive'):
                    print(f"    Duration: {r.get('outputTimecode', 'N/A')}")

            if stats and "responseData" in stats:
                st = stats["responseData"]
                print(f"  CPU: {st.get('cpuUsage', 0):.1f}%")
                print(f"  FPS: {st.get('activeFps', 0):.1f}")
                print(f"  Memory: {st.get('memoryUsage', 0):.1f} MB")

        else:
            print(f"Unknown command: {command}")

    finally:
        await obs.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
