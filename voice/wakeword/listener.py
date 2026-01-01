#!/usr/bin/env python3
"""
Roxy Wake Word Listener - openWakeWord
LUNA-030: Install openWakeWord for "Hey Roxy" detection
"""

import pyaudio
import numpy as np
import time
import sys
from pathlib import Path

try:
    from openwakeword import Model
except ImportError:
    print("❌ Missing openwakeword. Run: pip install openwakeword")
    sys.exit(1)

class RoxyWakeWordListener:
    """Wake word detection using openWakeWord"""
    
    def __init__(self, wake_word="hey roxy", model_path=None):
        """
        Initialize wake word listener
        
        Args:
            wake_word: Wake word phrase (default: "hey roxy")
            model_path: Path to custom model (optional)
        """
        self.wake_word = wake_word.lower()
        self.model_path = model_path
        
        print(f"👂 Initializing wake word listener: '{wake_word}'...")
        
        # Initialize openWakeWord
        try:
            if model_path and Path(model_path).exists():
                self.owwModel = Model(wakeword_models=[model_path])
                print(f"✅ Loaded custom model: {model_path}")
            else:
                # Use default models
                self.owwModel = Model()
                print("✅ Loaded default openWakeWord models")
        except Exception as e:
            print(f"❌ Failed to load wake word model: {e}")
            raise
        
        # Audio settings
        self.chunk = 4096
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
        print("✅ Wake word listener ready")
    
    def start_listening(self, callback=None):
        """
        Start listening for wake word
        
        Args:
            callback: Function to call when wake word detected (receives wake word name)
        """
        print(f"👂 Listening for '{self.wake_word}'...")
        print("   (Press Ctrl+C to stop)")
        
        try:
            # Open audio stream
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )
            
            while True:
                # Read audio chunk
                audio_data = self.stream.read(self.chunk, exception_on_overflow=False)
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # Predict wake words
                prediction = self.owwModel.predict(audio_array)
                
                # Check for wake word detections
                for mdl in self.owwModel.models.keys():
                    if prediction[mdl] > 0.5:  # Threshold
                        wake_word_detected = mdl.replace('_', ' ').lower()
                        print(f"\n🎯 WAKE WORD DETECTED: '{wake_word_detected}' (confidence: {prediction[mdl]:.2f})")
                        
                        if callback:
                            callback(wake_word_detected)
                        else:
                            # Default: just print
                            print("   → Ready for command...")
                
                time.sleep(0.01)  # Small delay
                
        except KeyboardInterrupt:
            print("\n👂 Stopping wake word listener...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop listening"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()
        print("✅ Wake word listener stopped")

def main():
    """CLI interface for wake word listener"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Roxy Wake Word Listener")
    parser.add_argument("--wake-word", "-w", default="hey roxy", help="Wake word phrase")
    parser.add_argument("--model", "-m", help="Path to custom wake word model")
    
    args = parser.parse_args()
    
    # Initialize listener
    try:
        listener = RoxyWakeWordListener(
            wake_word=args.wake_word,
            model_path=args.model
        )
    except Exception as e:
        print(f"❌ Failed to initialize listener: {e}")
        sys.exit(1)
    
    # Start listening
    listener.start_listening()

if __name__ == "__main__":
    main()











