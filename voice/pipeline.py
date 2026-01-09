#!/usr/bin/env python3
"""
Roxy Voice Pipeline - Complete Voice Interface
LUNA-080: Create Roxy Voice Interface
Connects: wake word → transcription → LLM → TTS
"""

import asyncio
import sys
import json
import pyaudio
import numpy as np
import wave
import tempfile
import threading
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

ROXY_HOME = Path.home() / ".roxy"
ROXY_LEGACY = ROXY_HOME / "services.LEGACY.20260101_200448"

# Import components
try:
    from voice.wakeword.listener import RoxyWakeWordListener
    from voice.transcription.service import RoxyTranscription
    from voice.tts.service_edge import RoxyTTS
except ImportError as e:
    print(f"❌ Missing voice components: {e}")
    print("   Ensure all voice services are installed")
    import traceback
    traceback.print_exc()
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
        
        # Audio recording settings
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 4096
        self.audio = pyaudio.PyAudio()
        self.recording_stream = None
        self.recording_frames = []
        self.is_recording = False
        self.recording_thread = None
        
        # Silence detection
        self.silence_threshold = 500  # RMS threshold for silence
        self.silence_duration = 1.5  # seconds of silence before stopping
        self.max_recording_duration = 10.0  # maximum recording time in seconds
        
        self.listening = False
        self.conversation_active = False
    
    async def _default_llm(self, text):
        """Default LLM callback - integrates with ROXY LLM service"""
        try:
            # Try to import and use LLM service
            import sys
            if ROXY_LEGACY.exists():
                sys.path.insert(0, str(ROXY_LEGACY))
            
            try:
                from llm_service import get_llm_service
                llm_service = get_llm_service()
                
                if llm_service and llm_service.is_available():
                    response = await llm_service.generate_response(
                        user_input=text,
                        context={'source': 'voice_interface', 'session_id': 'roxy_voice'},
                        history=[],
                        facts=[]
                    )
                    if response and response.strip():
                        return response.strip()
            except ImportError:
                pass
            except Exception as e:
                print(f"   ⚠️  LLM service error: {e}")
        except:
            pass
        
        # Fallback: simple echo with context
        return f"I heard you say: {text}. How can I help you?"
    
    async def process_command(self, audio_path):
        """
        Process voice command: transcribe → LLM → TTS
        
        Args:
            audio_path: Path to audio file to transcribe
        """
        print("\n🎙️  Processing command...")
        
        try:
            # Step 1: Transcribe
            print("   📝 Transcribing...")
            result = self.transcriber.transcribe_file(audio_path)
            transcription = result['text']
            
            if not transcription.strip():
                print("   ⚠️  No speech detected")
                return
            
            print(f"   ✅ Heard: {transcription}")
            
            # Step 2: LLM processing
            print("   🤖 Processing with LLM...")
            if asyncio.iscoroutinefunction(self.llm_callback):
                response = await self.llm_callback(transcription)
            else:
                response = self.llm_callback(transcription)
            print(f"   ✅ Response: {response[:100]}...")
            
            # Step 3: TTS
            print("   🎤 Speaking response...")
            output = self.tts.speak(response)
            print(f"   ✅ Response spoken")
            
        except Exception as e:
            print(f"   ❌ Error processing command: {e}")
            import traceback
            traceback.print_exc()
    
    def on_wake_word_detected(self, wake_word):
        """Callback when wake word is detected"""
        if self.conversation_active:
            return  # Already processing
        
        print(f"\n🎯 Wake word detected: {wake_word}")
        print("   👂 Listening for command...")
        
        # Acknowledge wake word
        self.tts.speak("Yes, I'm listening!")
        
        # Start recording audio in a thread (since we're called from blocking thread)
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._record_and_process())
            finally:
                loop.close()
        
        recording_thread = threading.Thread(target=run_async, daemon=True)
        recording_thread.start()
    
    def _start_recording(self):
        """Begin audio capture after wake word"""
        if self.is_recording:
            return
        
        self.is_recording = True
        self.recording_frames = []
        
        try:
            self.recording_stream = self.audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )
            print("   🎙️  Recording started...")
        except Exception as e:
            print(f"   ❌ Failed to start recording: {e}")
            self.is_recording = False
            raise
    
    def _stop_recording(self):
        """Stop audio capture"""
        if not self.is_recording:
            return
        
        self.is_recording = False
        
        if self.recording_stream:
            try:
                self.recording_stream.stop_stream()
                self.recording_stream.close()
            except:
                pass
            self.recording_stream = None
        
        print("   🛑 Recording stopped")
    
    def _detect_silence(self, audio_data):
        """Detect if audio chunk is silence"""
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        rms = np.sqrt(np.mean(audio_array**2))
        return rms < self.silence_threshold
    
    async def _record_and_process(self):
        """Record audio until silence or timeout, then process"""
        if self.conversation_active:
            return
        
        self.conversation_active = True
        
        try:
            # Start recording
            self._start_recording()
            
            # Record until silence or timeout
            silence_start = None
            start_time = datetime.now()
            frames = []
            
            while self.is_recording:
                try:
                    # Read audio chunk
                    audio_data = self.recording_stream.read(
                        self.chunk, 
                        exception_on_overflow=False
                    )
                    frames.append(audio_data)
                    
                    # Check for silence
                    if self._detect_silence(audio_data):
                        if silence_start is None:
                            silence_start = datetime.now()
                    else:
                        silence_start = None  # Reset silence timer
                    
                    # Check timeout
                    elapsed = (datetime.now() - start_time).total_seconds()
                    if elapsed > self.max_recording_duration:
                        print(f"   ⏱️  Max recording duration reached ({self.max_recording_duration}s)")
                        break
                    
                    # Check if silence duration reached
                    if silence_start:
                        silence_elapsed = (datetime.now() - silence_start).total_seconds()
                        if silence_elapsed >= self.silence_duration:
                            print(f"   🔇 Silence detected ({self.silence_duration}s)")
                            break
                    
                    # Small delay to prevent CPU spinning
                    await asyncio.sleep(0.01)
                    
                except Exception as e:
                    print(f"   ⚠️  Recording error: {e}")
                    break
            
            # Stop recording
            self._stop_recording()
            
            if not frames:
                print("   ⚠️  No audio captured")
                self.conversation_active = False
                return
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            temp_path = temp_file.name
            temp_file.close()
            
            # Write WAV file
            with wave.open(temp_path, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.audio_format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(frames))
            
            print(f"   💾 Audio saved: {len(frames)} frames")
            
            # Process command
            await self.process_command(temp_path)
            
            # Clean up temp file
            try:
                Path(temp_path).unlink()
            except:
                pass
                
        except Exception as e:
            print(f"   ❌ Error in recording: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._stop_recording()
            self.conversation_active = False
    
    def start(self):
        """Start the voice pipeline"""
        print("\n🎤 Starting Roxy Voice Pipeline...")
        print("   Say 'Hey Roxy' to activate")
        print("   Press Ctrl+C to stop\n")
        
        try:
            # Run wake word listener in a thread since it's blocking
            def run_listener():
                self.wake_word_listener.start_listening(
                    callback=self.on_wake_word_detected
                )
            
            listener_thread = threading.Thread(target=run_listener, daemon=True)
            listener_thread.start()
            
            # Keep main thread alive and run async event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                while True:
                    loop.run_until_complete(asyncio.sleep(1))
            except KeyboardInterrupt:
                print("\n👋 Shutting down voice pipeline...")
            finally:
                loop.close()
                
        except KeyboardInterrupt:
            print("\n👋 Shutting down voice pipeline...")
        finally:
            self._stop_recording()
            self.wake_word_listener.stop()
            if self.audio:
                self.audio.terminate()
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
