#!/usr/bin/env python3
"""
ROXY v1.0 - Digital Chief of Staff
Voice Assistant for JARVIS-1 Workstation

Usage: python3 ~/.roxy/roxy_assistant.py
Wake word: "Hey Jarvis" (train "Hey Roxy" later)
"""

import os
import sys
import time
import queue
import subprocess
import numpy as np
import sounddevice as sd
import requests

# Set path
os.environ['PATH'] = f"{os.path.expanduser('~/.local/bin')}:{os.environ.get('PATH', '')}"

import whisper
from openwakeword.model import Model as WakeModel

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

CONFIG = {
    'whisper_model': 'base.en',
    'ollama_model': 'llama3:8b',
    'ollama_url': 'http://localhost:11434',
    'voice_model': os.path.expanduser('~/.roxy/voices/en_US-lessac-medium.onnx'),
    'sample_rate': 16000,
    'channels': 1,
    'command_duration': 5,
    'wake_threshold': 0.5,
}

ROXY_PROMPT = """You are Roxy, Mark's digital Chief of Staff.

PERSONALITY:
- Direct and efficient, occasional dry humor
- Never sycophantic ("Got it" not "Certainly! I'd be happy to...")
- Professional but warm

KNOWLEDGE:
- MindSong architecture (Quantum Rails, LUNO, EventSpine)
- SKOREQ governance system
- Linux administration

Keep responses concise (1-3 sentences). Offer follow-up actions when relevant."""

# ═══════════════════════════════════════════════════════════════════════════
# ROXY CLASS
# ═══════════════════════════════════════════════════════════════════════════

class Roxy:
    def __init__(self):
        print("🚀 Initializing Roxy...")
        
        # Whisper STT (CPU for compatibility)
        print("   Loading Whisper...")
        self.whisper = whisper.load_model(CONFIG['whisper_model'], device='cpu')
        
        # Wake word detection
        print("   Loading OpenWakeWord...")
        self.wake_model = WakeModel()
        
        # Audio queue
        self.audio_queue = queue.Queue()
        
        print("✅ Roxy online!")
    
    def listen_for_wake_word(self):
        """Listen for wake word."""
        def callback(indata, frames, time_info, status):
            self.audio_queue.put(indata.copy())
        
        with sd.InputStream(
            samplerate=CONFIG['sample_rate'],
            channels=CONFIG['channels'],
            callback=callback,
            blocksize=1280
        ):
            print("\n👂 Listening for 'Hey Jarvis'...")
            while True:
                try:
                    audio = self.audio_queue.get(timeout=0.1)
                    prediction = self.wake_model.predict(audio.flatten())
                    
                    score = prediction.get('hey_jarvis', 0)
                    if score > CONFIG['wake_threshold']:
                        print("🎤 Wake word detected!")
                        # Clear queue
                        while not self.audio_queue.empty():
                            try:
                                self.audio_queue.get_nowait()
                            except:
                                break
                        return True
                except queue.Empty:
                    continue
    
    def record_command(self):
        """Record user's voice command."""
        duration = CONFIG['command_duration']
        print(f"🎙️  Listening for {duration}s...")
        
        audio = sd.rec(
            int(duration * CONFIG['sample_rate']),
            samplerate=CONFIG['sample_rate'],
            channels=CONFIG['channels'],
            dtype='float32'
        )
        sd.wait()
        return audio.flatten()
    
    def transcribe(self, audio):
        """Convert speech to text."""
        result = self.whisper.transcribe(audio, fp16=False, language='en')
        return result['text'].strip()
    
    def query_ollama(self, text):
        """Send query to Ollama."""
        try:
            response = requests.post(
                f"{CONFIG['ollama_url']}/api/generate",
                json={
                    'model': CONFIG['ollama_model'],
                    'prompt': f"{ROXY_PROMPT}\n\nUser: {text}\nRoxy:",
                    'stream': False,
                    'options': {'temperature': 0.7, 'num_predict': 150}
                },
                timeout=30
            )
            return response.json().get('response', '').strip()
        except Exception as e:
            return f"Sorry, couldn't reach my brain: {e}"
    
    def speak(self, text):
        """Text-to-speech using Piper."""
        print(f"🔊 Roxy: {text}")
        
        try:
            # Generate speech with Piper
            process = subprocess.Popen(
                ['piper', '--model', CONFIG['voice_model'], '--output_file', '/tmp/roxy.wav'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            process.communicate(input=text.encode())
            
            # Play audio
            subprocess.run(['aplay', '-q', '/tmp/roxy.wav'], check=True)
        except Exception as e:
            print(f"   TTS error: {e}")
    
    def run(self):
        """Main voice assistant loop."""
        self.speak("Roxy online. Ready when you are.")
        
        while True:
            try:
                # Wait for wake word
                self.listen_for_wake_word()
                
                # Record command
                audio = self.record_command()
                
                # Transcribe
                text = self.transcribe(audio)
                print(f"📝 You said: {text}")
                
                if not text or len(text) < 3:
                    self.speak("Didn't catch that.")
                    continue
                
                # Exit commands
                if any(x in text.lower() for x in ['goodbye', 'shut down', 'exit']):
                    self.speak("Shutting down. Later, Mark.")
                    break
                
                # Generate response
                response = self.query_ollama(text)
                
                # Speak response
                self.speak(response)
                
            except KeyboardInterrupt:
                print("\n👋 Roxy shutting down...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(1)

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    roxy = Roxy()
    roxy.run()
