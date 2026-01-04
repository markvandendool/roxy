#!/usr/bin/env python3
"""
MCP OBS Server - OBS Studio control for AI assistants
Part of LUNA-000 CITADEL P6: MCP Architecture

Exposes:
- obs_status: Get streaming/recording status
- obs_start_stream: Start streaming
- obs_stop_stream: Stop streaming
- obs_start_recording: Start recording
- obs_stop_recording: Stop recording
- obs_set_scene: Switch to scene
- obs_get_scenes: List available scenes
"""

import json
import asyncio

try:
    import obsws_python as obs
except ImportError:
    obs = None

TOOLS = {
    "obs_status": {
        "description": "Get OBS streaming and recording status",
        "parameters": {}
    },
    "obs_start_stream": {
        "description": "Start streaming",
        "parameters": {}
    },
    "obs_stop_stream": {
        "description": "Stop streaming",
        "parameters": {}
    },
    "obs_start_recording": {
        "description": "Start recording",
        "parameters": {}
    },
    "obs_stop_recording": {
        "description": "Stop recording",
        "parameters": {}
    },
    "obs_set_scene": {
        "description": "Switch to a scene",
        "parameters": {"scene": {"type": "string", "required": True}}
    },
    "obs_get_scenes": {
        "description": "List available scenes",
        "parameters": {}
    }
}

def get_client():
    """Get OBS WebSocket client"""
    if not obs:
        return None
    try:
        return obs.ReqClient(host="localhost", port=4455, timeout=5)
    except:
        return None

def handle_tool(name, params={}):
    """Handle MCP tool call"""
    client = get_client()
    if not client:
        return {"error": "Cannot connect to OBS. Is it running?"}
    
    try:
        if name == "obs_status":
            stream = client.get_stream_status()
            record = client.get_record_status()
            return {
                "streaming": stream.output_active,
                "recording": record.output_active,
                "stream_duration": getattr(stream, "output_duration", 0),
                "record_duration": getattr(record, "output_duration", 0)
            }
        
        elif name == "obs_start_stream":
            client.start_stream()
            return {"success": True, "message": "Streaming started"}
        
        elif name == "obs_stop_stream":
            client.stop_stream()
            return {"success": True, "message": "Streaming stopped"}
        
        elif name == "obs_start_recording":
            client.start_record()
            return {"success": True, "message": "Recording started"}
        
        elif name == "obs_stop_recording":
            client.stop_record()
            return {"success": True, "message": "Recording stopped"}
        
        elif name == "obs_set_scene":
            scene = params.get("scene")
            client.set_current_program_scene(scene)
            return {"success": True, "message": f"Switched to {scene}"}
        
        elif name == "obs_get_scenes":
            scenes = client.get_scene_list()
            return {"scenes": [s["sceneName"] for s in scenes.scenes]}
        
    except Exception as e:
        return {"error": str(e)}
    
    return {"error": f"Unknown tool: {name}"}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        tool = sys.argv[1]
        params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        result = handle_tool(tool, params)
        print(json.dumps(result, indent=2))
    else:
        print("MCP OBS Server")
        print("Tools:", list(TOOLS.keys()))
