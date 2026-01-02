#!/usr/bin/env python3
"""
Roxy TTS Service - Edge TTS (Workaround for Python 3.12)
LUNA-032: Install XTTS v2 (blocked by Python < 3.12 requirement)
Using Edge TTS as temporary solution
"""

import asyncio
import edge_tts
import edge_tts.exceptions
import os
import subprocess
from pathlib import Path

VOICE = "en-US-AriaNeural"  # A natural-sounding female voice
OUTPUT_DIR = Path("/tmp")

class RoxyTTS:
    """Text-to-speech using Edge TTS"""
    
    def __init__(self, voice=VOICE):
        """Initialize TTS service"""
        self.voice = voice
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(exist_ok=True)
    
    async def generate_speech(self, text: str, output_file: str = None):
        """Generate speech audio file"""
        if output_file is None:
            output_file = self.output_dir / "roxy_speech.mp3"
        
        try:
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(str(output_file))
            return str(output_file)
        except edge_tts.exceptions.NoAudioReceived as e:
            raise Exception(f"No audio received from Edge TTS: {e}")
        except Exception as e:
            raise Exception(f"TTS generation failed: {e}")
    
    def speak(self, text: str, output_file: str = None):
        """Generate and play speech (synchronous wrapper)"""
        audio_file = asyncio.run(self.generate_speech(text, output_file))
        
        # Play audio - try multiple players
        players = ["mpv", "paplay", "aplay"]
        played = False
        
        for player in players:
            try:
                # For paplay/aplay, we need WAV format
                if player in ["paplay", "aplay"] and audio_file.endswith('.mp3'):
                    # Try to use ffmpeg to convert, or just skip
                    try:
                        import tempfile
                        wav_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                        wav_path = wav_file.name
                        wav_file.close()
                        subprocess.run(
                            ["ffmpeg", "-i", audio_file, "-y", wav_path],
                            check=True,
                            capture_output=True,
                            timeout=10
                        )
                        subprocess.run([player, wav_path], check=True, capture_output=True)
                        Path(wav_path).unlink()
                        played = True
                        break
                    except (FileNotFoundError, subprocess.CalledProcessError):
                        continue
                else:
                    # Direct playback
                    subprocess.run([player, audio_file], check=True, capture_output=True)
                    played = True
                    break
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
        
        if not played:
            print(f"⚠️  No audio player found. Audio saved to: {audio_file}")
            print("   Install one of: mpv, paplay, or aplay")
        
        return audio_file

async def generate_and_play_speech(text: str, voice: str = VOICE, output_file: str = None):
    """Legacy function for backward compatibility"""
    if output_file is None:
        output_file = OUTPUT_DIR / "roxy_edge_test.mp3"
    
    print(f"🎤 Selected voice: {voice}")
    print(f"🎤 Initializing Roxy TTS (Edge TTS, voice: {voice})...")
    
    try:
        communicate = edge_tts.Communicate(text, voice)
        print(f"🎙️  Generating speech: '{text[:70]}...'")
        await communicate.save(str(output_file))
        print(f"✅ Speech saved: {output_file}")
        
        # Play the generated audio
        print("🔊 Playing audio...")
        subprocess.run(["mpv", str(output_file)], check=True)
        print("✅ Audio played")
        return True
    except edge_tts.exceptions.NoAudioReceived as e:
        print(f"❌ Error: No audio received from Edge TTS. {e}")
        return False
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        return False

async def main():
    text_to_speak = "Hello! I am Roxy, your omniscient control system. Audio is working perfectly! All systems are operational."
    await generate_and_play_speech(text_to_speak)

if __name__ == "__main__":
    asyncio.run(main())
