#!/usr/bin/env python3
"""
ROXY Voice MCP Server
Exposes TTS and voice control capabilities using Edge TTS
"""
from mcp.server.fastmcp import FastMCP
import sys
import os
from pathlib import Path

# Add ROXY_ROOT to path
ROXY_ROOT = Path(os.environ.get('ROXY_ROOT', str(Path.home() / '.roxy')))
sys.path.insert(0, str(ROXY_ROOT))

# Import Edge TTS service
from voice.tts.service_edge import RoxyTTS

mcp = FastMCP('roxy-voice')
tts = RoxyTTS()

# Available Edge TTS voices (common ones)
EDGE_VOICES = {
    'aria': 'en-US-AriaNeural',
    'jenny': 'en-US-JennyNeural',
    'guy': 'en-US-GuyNeural',
    'jane': 'en-US-JaneNeural',
    'aria': 'en-US-AriaNeural',
}

@mcp.tool()
async def speak(text: str, voice: str = 'aria') -> str:
    """Speak text using Edge TTS.
    
    Args:
        text: The text to speak
        voice: Voice name (aria, jenny, guy, jane) - defaults to aria
    """
    try:
        voice_id = EDGE_VOICES.get(voice.lower(), EDGE_VOICES['aria'])
        tts.voice = voice_id
        tts.speak(text)
        return f'Spoke: "{text}" (voice: {voice})'
    except Exception as e:
        return f'Error: {str(e)}'

@mcp.tool()
async def synthesize_audio(text: str, output_path: str, voice: str = 'aria') -> str:
    """Synthesize text to audio file using Edge TTS.
    
    Args:
        text: The text to synthesize
        output_path: Path to save the audio file
        voice: Voice name (aria, jenny, guy, jane)
    """
    try:
        voice_id = EDGE_VOICES.get(voice.lower(), EDGE_VOICES['aria'])
        tts.voice = voice_id
        audio_file = await tts.generate_speech(text, output_path)
        return f'Audio saved to: {audio_file}'
    except Exception as e:
        return f'Error: {str(e)}'

@mcp.tool()
async def list_voices() -> str:
    """List available Edge TTS voice profiles."""
    result = ["Available voices:"]
    for name, voice_id in EDGE_VOICES.items():
        result.append(f"- {name}: {voice_id}")
    return '\n'.join(result)

@mcp.tool()
async def test_voice(voice: str = 'aria', sample_text: str = 'Hello, this is a voice test.') -> str:
    """Test a specific voice with sample text.
    
    Args:
        voice: Voice name to test (aria, jenny, guy, jane)
        sample_text: Text to speak for testing
    """
    try:
        voice_id = EDGE_VOICES.get(voice.lower(), EDGE_VOICES['aria'])
        tts.voice = voice_id
        tts.speak(sample_text)
        return f'Tested voice: {voice} ({voice_id})'
    except Exception as e:
        return f'Error: {str(e)}'

if __name__ == '__main__':
    mcp.run()
