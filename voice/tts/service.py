#!/usr/bin/env python3
"""
Roxy TTS Service - XTTS v2 Voice Cloning
LUNA-032: Install XTTS v2 Voice Cloning
"""

import os
import sys
import argparse
from pathlib import Path
import tempfile

try:
    from TTS.api import TTS
    import torch
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("   Run: pip install TTS torch")
    sys.exit(1)

# Paths
VOICE_DIR = Path(__file__).parent.parent
REFERENCE_DIR = VOICE_DIR / "reference"
MODELS_DIR = VOICE_DIR / "tts" / "models"

class RoxyTTS:
    """XTTS v2 TTS service for Roxy's voice"""
    
    def __init__(self, model_name="tts_models/multilingual/multi-dataset/xtts_v2", device=None):
        """
        Initialize XTTS v2 model
        
        Args:
            model_name: TTS model name (default: XTTS v2)
            device: Device to use (cuda/cpu, auto-detected if None)
        """
        if device is None:
            # Check environment variable first
            gpu_enabled = os.getenv('ROXY_GPU_ENABLED', 'true').lower() == 'true'
            
            if gpu_enabled and torch.cuda.is_available():
                device = "cuda"
                print(f"   GPU detected: {torch.cuda.get_device_name(0)}")
            else:
                device = "cpu"
                if not torch.cuda.is_available():
                    print(f"   No GPU available, using CPU")
                else:
                    print(f"   GPU disabled via environment, using CPU")
        
        self.device = device
        self.model_name = model_name
        
        print(f"🎤 Initializing Roxy TTS (device: {device})...")
        try:
            self.tts = TTS(model_name=model_name, progress_bar=True).to(device)
            print(f"✅ TTS model loaded: {model_name} on {device}")
            
            # Log GPU memory if using GPU
            if device == "cuda":
                try:
                    memory_allocated = torch.cuda.memory_allocated(0) / 1024**2
                    memory_reserved = torch.cuda.memory_reserved(0) / 1024**2
                    print(f"   GPU memory: {memory_allocated:.1f} MB allocated, {memory_reserved:.1f} MB reserved")
                except:
                    pass
        except Exception as e:
            print(f"❌ Failed to load TTS model: {e}")
            raise
    
    def speak(self, text, speaker_wav=None, language="en", output_path=None, output_format="wav"):
        """
        Generate speech from text
        
        Args:
            text: Text to speak
            speaker_wav: Path to reference audio for voice cloning (optional)
            language: Language code (en, es, fr, de, etc.)
            output_path: Output file path (if None, returns audio data)
            output_format: Output format (wav, mp3, etc.)
        
        Returns:
            Path to output file or audio data
        """
        if speaker_wav and not Path(speaker_wav).exists():
            print(f"⚠️  Reference audio not found: {speaker_wav}")
            print("   Using default voice...")
            speaker_wav = None
        
        # If no output path, use temp file
        if output_path is None:
            output_path = tempfile.mktemp(suffix=f".{output_format}")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            print(f"🎙️  Generating speech: '{text[:50]}...'")
            
            if speaker_wav:
                # Voice cloning mode
                self.tts.tts_to_file(
                    text=text,
                    speaker_wav=speaker_wav,
                    language=language,
                    file_path=str(output_path)
                )
                print(f"✅ Voice cloned speech saved: {output_path}")
            else:
                # Default voice mode
                self.tts.tts_to_file(
                    text=text,
                    language=language,
                    file_path=str(output_path)
                )
                print(f"✅ Speech saved: {output_path}")
            
            return output_path
        except Exception as e:
            print(f"❌ TTS generation failed: {e}")
            raise
    
    def speak_to_audio(self, text, speaker_wav=None, language="en"):
        """
        Generate speech and return audio data (for streaming)
        
        Args:
            text: Text to speak
            speaker_wav: Path to reference audio for voice cloning
            language: Language code
        
        Returns:
            Audio data (numpy array)
        """
        if speaker_wav and not Path(speaker_wav).exists():
            speaker_wav = None
        
        try:
            if speaker_wav:
                wav = self.tts.tts(
                    text=text,
                    speaker_wav=speaker_wav,
                    language=language
                )
            else:
                wav = self.tts.tts(text=text, language=language)
            
            return wav
        except Exception as e:
            print(f"❌ TTS generation failed: {e}")
            raise

def main():
    """CLI interface for Roxy TTS"""
    parser = argparse.ArgumentParser(description="Roxy TTS Service - XTTS v2")
    parser.add_argument("text", help="Text to speak")
    parser.add_argument("--voice", "-v", help="Path to reference voice audio (.wav)")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--language", "-l", default="en", help="Language code (default: en)")
    parser.add_argument("--device", "-d", help="Device (cuda/cpu, auto-detected if not specified)")
    
    args = parser.parse_args()
    
    # Initialize TTS
    try:
        tts = RoxyTTS(device=args.device)
    except Exception as e:
        print(f"❌ Failed to initialize TTS: {e}")
        sys.exit(1)
    
    # Check for Roxy's reference voice
    roxy_voice = REFERENCE_DIR / "roxy_voice.wav"
    if roxy_voice.exists() and not args.voice:
        print(f"🎤 Using Roxy's cloned voice: {roxy_voice}")
        args.voice = str(roxy_voice)
    elif args.voice:
        args.voice = Path(args.voice).expanduser()
        if not args.voice.exists():
            print(f"⚠️  Voice file not found: {args.voice}")
            args.voice = None
    else:
        print("ℹ️  No reference voice found, using default XTTS voice")
        print(f"   To clone Roxy's voice, place reference audio at: {roxy_voice}")
    
    # Generate speech
    try:
        output = tts.speak(
            text=args.text,
            speaker_wav=args.voice,
            language=args.language,
            output_path=args.output
        )
        print(f"\n✅ Speech generated: {output}")
        
        # Play audio if paplay is available
        if not args.output or Path(args.output).exists():
            import subprocess
            try:
                play_cmd = ["paplay", str(output)] if not args.output else ["paplay", str(output)]
                subprocess.run(play_cmd, check=True)
                print("🔊 Audio played")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print(f"💡 Play audio with: paplay {output}")
    except Exception as e:
        print(f"❌ Failed to generate speech: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
