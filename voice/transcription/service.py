#!/usr/bin/env python3
"""
Roxy Speech-to-Text Service - faster-whisper
LUNA-031: Install faster-whisper with AMD GPU acceleration
"""

import sys
import argparse
from pathlib import Path
import time

try:
    from faster_whisper import WhisperModel
except ImportError:
    print("❌ Missing faster-whisper. Run: pip install faster-whisper")
    sys.exit(1)

class RoxyTranscription:
    """Speech-to-text using faster-whisper"""
    
    def __init__(self, model_size="large-v3", device="auto", compute_type="auto"):
        """
        Initialize Whisper model
        
        Args:
            model_size: Model size (tiny, base, small, medium, large-v2, large-v3)
            device: Device (cpu, cuda, auto)
            compute_type: Compute type (int8, int8_float16, float16, float32, auto)
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        
        print(f"🎤 Initializing Whisper transcription (model: {model_size})...")
        
        try:
            import os
            
            # Check for explicit CPU override (for GPU optimization)
            # This allows Whisper to use CPU while keeping LLM/TTS on GPU
            force_cpu = os.getenv("ROXY_WHISPER_DEVICE", "").lower() == "cpu"
            
            # Auto-detect device if needed
            if device == "auto":
                if force_cpu:
                    # Explicit CPU override for GPU optimization
                    device = "cpu"
                    if compute_type == "auto":
                        compute_type = "float32"
                    print(f"   🖥️  Using CPU (optimized for GPU resource management)")
                else:
                    try:
                        import torch
                        if torch.cuda.is_available():
                            device = "cuda"
                            # Use float16 for GPU (ROCm compatible)
                            if compute_type == "auto":
                                compute_type = "float16"
                            print(f"   GPU detected: {torch.cuda.get_device_name(0)}")
                        else:
                            device = "cpu"
                            if compute_type == "auto":
                                compute_type = "float32"
                    except Exception as e:
                        print(f"   ⚠️  Could not detect GPU: {e}, using CPU")
                        device = "cpu"
                        if compute_type == "auto":
                            compute_type = "float32"
            
            # Legacy: Check environment variable override (only if not forcing CPU)
            if not force_cpu and os.getenv("ROXY_GPU_ENABLED", "true").lower() == "true" and device == "cpu":
                try:
                    import torch
                    if torch.cuda.is_available():
                        device = "cuda"
                        if compute_type == "auto" or compute_type == "float32":
                            compute_type = "float16"
                except:
                    pass
            
            self.device = device
            self.compute_type = compute_type
            
            self.model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type
            )
            print(f"✅ Whisper model loaded: {model_size} on {device} (compute_type: {compute_type})")
        except Exception as e:
            print(f"❌ Failed to load Whisper model: {e}")
            raise
    
    def transcribe_file(self, audio_path, language="en", vad_filter=True):
        """
        Transcribe audio file
        
        Args:
            audio_path: Path to audio file
            language: Language code (en, es, fr, etc.) or None for auto-detect
            vad_filter: Use voice activity detection
        
        Returns:
            Transcription text and metadata
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        print(f"🎙️  Transcribing: {audio_path}")
        start_time = time.time()
        
        try:
            # Transcribe
            segments, info = self.model.transcribe(
                str(audio_path),
                language=language,
                vad_filter=vad_filter
            )
            
            # Collect segments
            text_segments = []
            for segment in segments:
                text_segments.append(segment.text.strip())
            
            transcription = " ".join(text_segments)
            elapsed = time.time() - start_time
            
            print(f"✅ Transcription complete ({elapsed:.2f}s)")
            print(f"   Language: {info.language} (probability: {info.language_probability:.2f})")
            print(f"   Text: {transcription[:100]}...")
            
            return {
                "text": transcription,
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": elapsed
            }
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            raise
    
    def transcribe_stream(self, audio_stream, language="en", vad_filter=True):
        """
        Transcribe audio stream (for real-time)
        
        Args:
            audio_stream: Audio stream (numpy array or file-like)
            language: Language code
            vad_filter: Use voice activity detection
        
        Returns:
            Transcription text
        """
        print("🎙️  Transcribing audio stream...")
        start_time = time.time()
        
        try:
            segments, info = self.model.transcribe(
                audio_stream,
                language=language,
                vad_filter=vad_filter
            )
            
            text_segments = []
            for segment in segments:
                text_segments.append(segment.text.strip())
            
            transcription = " ".join(text_segments)
            elapsed = time.time() - start_time
            
            print(f"✅ Transcription complete ({elapsed:.2f}s)")
            
            return {
                "text": transcription,
                "language": info.language,
                "duration": elapsed
            }
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            raise

def main():
    """CLI interface for transcription"""
    parser = argparse.ArgumentParser(description="Roxy Speech-to-Text Service")
    parser.add_argument("audio", help="Path to audio file")
    parser.add_argument("--model", "-m", default="large-v3", help="Model size (default: large-v3)")
    parser.add_argument("--language", "-l", help="Language code (auto-detect if not specified)")
    parser.add_argument("--device", "-d", default="auto", help="Device (cpu/cuda/auto)")
    parser.add_argument("--no-vad", action="store_true", help="Disable voice activity detection")
    
    args = parser.parse_args()
    
    # Initialize transcription
    try:
        transcriber = RoxyTranscription(
            model_size=args.model,
            device=args.device
        )
    except Exception as e:
        print(f"❌ Failed to initialize transcriber: {e}")
        sys.exit(1)
    
    # Transcribe
    try:
        result = transcriber.transcribe_file(
            args.audio,
            language=args.language,
            vad_filter=not args.no_vad
        )
        
        print(f"\n📝 Transcription:")
        print(f"   {result['text']}")
        print(f"\n📊 Metadata:")
        print(f"   Language: {result['language']} ({result['language_probability']:.2%})")
        print(f"   Duration: {result['duration']:.2f}s")
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()



