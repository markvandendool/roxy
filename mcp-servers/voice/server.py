#!/usr/bin/env python3
"""
ROXY Voice MCP Server
Exposes TTS and voice control capabilities
"""
from mcp.server.fastmcp import FastMCP
import subprocess
import sys
sys.path.insert(0, '/opt/roxy/voice')

from tts.service import RoxyTTS, VOICES

mcp = FastMCP('roxy-voice')
tts = RoxyTTS('roxy')

@mcp.tool()
async def speak(text: str, voice: str = 'roxy', speaker: int = 0) -> str:
    """Speak text using Roxy's TTS voice.
    
    Args:
        text: The text to speak
        voice: Voice profile to use (roxy, amy, kusal)
        speaker: Speaker ID for multi-speaker models (0-903 for roxy)
    """
    try:
        if voice != tts.voice_config.get('name', 'roxy'):
            tts.set_voice(voice)
        tts.speak(text, speaker=speaker)
        return f'Spoke: "{text}" (voice: {voice}, speaker: {speaker})'
    except Exception as e:
        return f'Error: {str(e)}'

@mcp.tool()
async def synthesize_audio(text: str, output_path: str, voice: str = 'roxy', speaker: int = 0) -> str:
    """Synthesize text to audio file."""
    try:
        if voice != tts.voice_config.get('name', 'roxy'):
            tts.set_voice(voice)
        wav_path = tts.synthesize(text, output_path, speaker=speaker)
        return f'Audio saved to: {wav_path}'
    except Exception as e:
        return f'Error: {str(e)}'

@mcp.tool()
async def list_voices() -> str:
    """List available voice profiles."""
    result = []
    for name, config in VOICES.items():
        result.append(f"- {name}: {config['description']}")
    return '\n'.join(result)

@mcp.tool()
async def test_speaker(speaker_id: int, sample_text: str = 'Hello, this is a voice test.') -> str:
    """Test a specific speaker ID (0-903 for roxy voice)."""
    try:
        tts.set_voice('roxy')
        tts.speak(sample_text, speaker=speaker_id)
        return f'Tested speaker {speaker_id}'
    except Exception as e:
        return f'Error: {str(e)}'

if __name__ == '__main__':
    mcp.run()
