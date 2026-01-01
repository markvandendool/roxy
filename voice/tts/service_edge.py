#!/usr/bin/env python3
"""
Roxy TTS Service - Edge TTS (Temporary until XTTS v2 supports Python 3.12)
Uses Microsoft Edge TTS API (free, no installation needed)
"""

import asyncio
import sys
import argparse
from pathlib import Path

try:
    import edge_tts
except ImportError:
    print("❌ Missing edge-tts. Run: pip install edge-tts")
    sys.exit(1)

class RoxyTTS:
    """Edge TTS service (temporary until XTTS v2 supports Python 3.12)"""
    
    def __init__(self, voice="en-US-AriaNeural"):
        """
        Initialize Edge TTS
        
        Args:
            voice: Voice name (default: AriaNeural - natural female voice)
        """
        self.voice = voice
        print(f"🎤 Initializing Roxy TTS (Edge TTS, voice: {voice})...")
    
    async def list_voices(self):
        """List available voices"""
        voices = await edge_tts.list_voices()
        return voices
    
    async def speak_async(self, text, output_path=None, voice=None):
        """
        Generate speech from text (async)
        
        Args:
            text: Text to speak
            output_path: Output file path (if None, returns audio data)
            voice: Voice name (uses default if None)
        
        Returns:
            Path to output file
        """
        voice = voice or self.voice
        
        if output_path is None:
            output_path = "/tmp/roxy_tts_output.mp3"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            print(f"🎙️  Generating speech: '{text[:50]}...'")
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(output_path))
            print(f"✅ Speech saved: {output_path}")
            return output_path
        except Exception as e:
            print(f"❌ TTS generation failed: {e}")
            raise
    
    def speak(self, text, output_path=None, voice=None):
        """Synchronous wrapper for speak_async"""
        return asyncio.run(self.speak_async(text, output_path, voice))

async def find_female_voice():
    """Find a natural-sounding female voice"""
    voices = await edge_tts.list_voices()
    
    # Prefer natural-sounding female voices
    preferred = [
        "en-US-AriaNeural",      # Natural, warm
        "en-US-JennyNeural",      # Friendly
        "en-US-MichelleNeural",   # Professional
        "en-GB-SoniaNeural",     # British
    ]
    
    for pref in preferred:
        for voice in voices:
            if voice["ShortName"] == pref:
                return pref
    
    # Fallback: any English female voice
    for voice in voices:
        if "en" in voice["Locale"] and "Female" in voice.get("Gender", ""):
            return voice["ShortName"]
    
    return "en-US-AriaNeural"  # Default

def main():
    """CLI interface for Roxy TTS"""
    parser = argparse.ArgumentParser(description="Roxy TTS Service - Edge TTS")
    parser.add_argument("text", help="Text to speak")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--voice", "-v", help="Voice name (default: auto-select female)")
    parser.add_argument("--list-voices", action="store_true", help="List available voices")
    
    args = parser.parse_args()
    
    if args.list_voices:
        async def list():
            voices = await edge_tts.list_voices()
            print("\n🎤 Available Voices:")
            for v in voices[:20]:  # Show first 20
                print(f"  {v['ShortName']}: {v.get('Gender', 'N/A')} - {v.get('Locale', 'N/A')}")
        asyncio.run(list())
        return
    
    # Initialize TTS
    if args.voice:
        tts = RoxyTTS(voice=args.voice)
    else:
        # Auto-select natural female voice
        voice = asyncio.run(find_female_voice())
        print(f"🎤 Selected voice: {voice}")
        tts = RoxyTTS(voice=voice)
    
    # Generate speech
    try:
        output = tts.speak(
            text=args.text,
            output_path=args.output
        )
        print(f"\n✅ Speech generated: {output}")
        
        # Play audio if paplay is available
        import subprocess
        try:
            subprocess.run(["paplay", str(output)], check=True)
            print("🔊 Audio played")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"💡 Play audio with: paplay {output}")
    except Exception as e:
        print(f"❌ Failed to generate speech: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()



