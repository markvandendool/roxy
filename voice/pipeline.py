#!/usr/bin/env python3
"""
Roxy Voice Pipeline - Complete Voice Interface
LUNA-080: Create Roxy Voice Interface
Connects: wake word → transcription → LLM → TTS
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Import components
try:
    from voice.wakeword.listener import RoxyWakeWordListener
    from voice.transcription.service import RoxyTranscription
    from voice.tts.service_edge import RoxyTTS
except ImportError as e:
    print(f"❌ Missing voice components: {e}")
    print("   Ensure all voice services are installed")
    sys.exit(1)

class RoxyVoicePipeline:
    """Complete voice interface pipeline"""
    
    def __init__(self, llm_callback=None):
        """
        Initialize voice pipeline
        
        Args:
            llm_callback: Function to call with transcribed text, returns response text
        """
        self.llm_callback = llm_callback or self._default_llm
        
        # Initialize components
        print("🎤 Initializing Roxy Voice Pipeline...")
        
        try:
            self.wake_word_listener = RoxyWakeWordListener(wake_word="hey roxy")
            self.transcriber = RoxyTranscription(model_size="base")  # Use base for speed
            self.tts = RoxyTTS()
            print("✅ Voice pipeline initialized")
        except Exception as e:
            print(f"❌ Failed to initialize pipeline: {e}")
            raise
        
        self.listening = False
        self.conversation_active = False
    
    def _default_llm(self, text):
        """Default LLM callback (echo for testing)"""
        return f"I heard you say: {text}"
    
    async def process_command(self, audio_data):
        """
        Process voice command: transcribe → LLM → TTS
        
        Args:
            audio_data: Audio data to transcribe
        """
        if self.conversation_active:
            return  # Already processing
        
        self.conversation_active = True
        print("\n🎙️  Processing command...")
        
        try:
            # Step 1: Transcribe
            print("   📝 Transcribing...")
            result = self.transcriber.transcribe_stream(audio_data)
            transcription = result['text']
            
            if not transcription.strip():
                print("   ⚠️  No speech detected")
                self.conversation_active = False
                return
            
            print(f"   ✅ Heard: {transcription}")
            
            # Step 2: LLM processing
            print("   🤖 Processing with LLM...")
            response = self.llm_callback(transcription)
            print(f"   ✅ Response: {response[:100]}...")
            
            # Step 3: TTS
            print("   🎤 Speaking response...")
            output = self.tts.speak(response)
            print(f"   ✅ Response spoken: {output}")
            
        except Exception as e:
            print(f"   ❌ Error processing command: {e}")
        finally:
            self.conversation_active = False
    
    def on_wake_word_detected(self, wake_word):
        """Callback when wake word is detected"""
        print(f"\n🎯 Wake word detected: {wake_word}")
        print("   👂 Listening for command...")
        
        # Start recording (simplified - would need actual audio capture)
        # For now, just acknowledge
        self.tts.speak("Yes, I'm listening!")
        
        # In full implementation, would:
        # 1. Start recording audio
        # 2. Wait for silence or timeout
        # 3. Process command
    
    def start(self):
        """Start the voice pipeline"""
        print("\n🎤 Starting Roxy Voice Pipeline...")
        print("   Say 'Hey Roxy' to activate")
        print("   Press Ctrl+C to stop\n")
        
        try:
            self.wake_word_listener.start_listening(
                callback=self.on_wake_word_detected
            )
        except KeyboardInterrupt:
            print("\n👋 Shutting down voice pipeline...")
        finally:
            self.wake_word_listener.stop()
            print("✅ Voice pipeline stopped")

def main():
    """CLI interface for voice pipeline"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Roxy Voice Pipeline")
    parser.add_argument("--llm-url", help="LLM API URL (for future integration)")
    parser.add_argument("--test", action="store_true", help="Test mode")
    
    args = parser.parse_args()
    
    # Initialize pipeline
    try:
        pipeline = RoxyVoicePipeline()
    except Exception as e:
        print(f"❌ Failed to initialize pipeline: {e}")
        sys.exit(1)
    
    # Start pipeline
    pipeline.start()

if __name__ == "__main__":
    main()
