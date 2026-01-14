#!/usr/bin/env python3
"""
ROXY OBS MCP Server
Control OBS Studio via WebSocket (v5 protocol)
Requires: OBS 28+ with obs-websocket plugin enabled
"""
import asyncio
import json
import base64
import hashlib
import logging
from typing import Optional
import websockets
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP('roxy-obs')

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


# Global OBS client
obs = OBSWebSocket()


@mcp.tool()
async def obs_get_status() -> str:
    """Get OBS connection and recording/streaming status."""
    try:
        result = await obs.call('GetRecordStatus')
        stream = await obs.call('GetStreamStatus')
        return json.dumps({
            'connected': True,
            'recording': result.get('responseData', {}).get('outputActive', False),
            'recordingPaused': result.get('responseData', {}).get('outputPaused', False),
            'recordingTime': result.get('responseData', {}).get('outputTimecode', '00:00:00'),
            'streaming': stream.get('responseData', {}).get('outputActive', False)
        }, indent=2)
    except Exception as e:
        return json.dumps({'connected': False, 'error': str(e)})


@mcp.tool()
async def obs_start_recording() -> str:
    """Start OBS recording."""
    try:
        result = await obs.call('StartRecord')
        return 'Recording started' if result.get('requestStatus', {}).get('result') else f'Failed: {result}'
    except Exception as e:
        return f'Error: {str(e)}'


@mcp.tool()
async def obs_stop_recording() -> str:
    """Stop OBS recording and return output file path."""
    try:
        result = await obs.call('StopRecord')
        output_path = result.get('responseData', {}).get('outputPath', 'Unknown')
        return f'Recording stopped. File: {output_path}'
    except Exception as e:
        return f'Error: {str(e)}'


@mcp.tool()
async def obs_pause_recording() -> str:
    """Pause OBS recording."""
    try:
        await obs.call('PauseRecord')
        return 'Recording paused'
    except Exception as e:
        return f'Error: {str(e)}'


@mcp.tool()
async def obs_resume_recording() -> str:
    """Resume paused OBS recording."""
    try:
        await obs.call('ResumeRecord')
        return 'Recording resumed'
    except Exception as e:
        return f'Error: {str(e)}'


@mcp.tool()
async def obs_get_scenes() -> str:
    """Get list of available OBS scenes."""
    try:
        result = await obs.call('GetSceneList')
        scenes = result.get('responseData', {}).get('scenes', [])
        current = result.get('responseData', {}).get('currentProgramSceneName', '')
        return json.dumps({
            'currentScene': current,
            'scenes': [s.get('sceneName') for s in scenes]
        }, indent=2)
    except Exception as e:
        return f'Error: {str(e)}'


@mcp.tool()
async def obs_switch_scene(scene_name: str) -> str:
    """Switch to a specific OBS scene.
    
    Args:
        scene_name: Name of the scene to switch to
    """
    try:
        await obs.call('SetCurrentProgramScene', {'sceneName': scene_name})
        return f'Switched to scene: {scene_name}'
    except Exception as e:
        return f'Error: {str(e)}'


@mcp.tool()
async def obs_get_record_directory() -> str:
    """Get OBS recording output directory."""
    try:
        result = await obs.call('GetRecordDirectory')
        return result.get('responseData', {}).get('recordDirectory', 'Unknown')
    except Exception as e:
        return f'Error: {str(e)}'


@mcp.tool()
async def obs_set_record_directory(directory: str) -> str:
    """Set OBS recording output directory.
    
    Args:
        directory: Path to the output directory
    """
    try:
        await obs.call('SetRecordDirectory', {'recordDirectory': directory})
        return f'Recording directory set to: {directory}'
    except Exception as e:
        return f'Error: {str(e)}'


@mcp.tool()
async def obs_take_screenshot(source_name: str = None, file_path: str = None) -> str:
    """Take a screenshot of OBS output or specific source.
    
    Args:
        source_name: Optional source name (defaults to current scene)
        file_path: Optional path to save screenshot (defaults to temp file)
    """
    try:
        import tempfile
        if not file_path:
            file_path = tempfile.mktemp(suffix='.png')
        
        request_data = {
            'imageFormat': 'png',
            'imageFilePath': file_path
        }
        if source_name:
            request_data['sourceName'] = source_name
        else:
            # Get current scene
            scenes = await obs.call('GetSceneList')
            current = scenes.get('responseData', {}).get('currentProgramSceneName')
            request_data['sourceName'] = current
        
        await obs.call('SaveSourceScreenshot', request_data)
        return f'Screenshot saved: {file_path}'
    except Exception as e:
        return f'Error: {str(e)}'


if __name__ == '__main__':
    mcp.run()
