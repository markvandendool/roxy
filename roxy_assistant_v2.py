#!/usr/bin/env python3
"""
ROXY Voice Assistant v2.0
Enhanced with OpenWakeWord, Whisper STT, ChromaDB RAG, Ollama LLM, Piper TTS

Part of LUNA-000 CITADEL -> NEXUS
The Left Brain of the Unified Mind (Operations/Business)
"""

import os
import sys
import json
import time
import wave
import struct
import subprocess
import tempfile
import threading
import queue
from pathlib import Path
from datetime import datetime

# Audio
import numpy as np
import sounddevice as sd

# Wake word detection
from openwakeword import Model as OWWModel

# Optional imports with fallbacks
try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    print("[WARN] ChromaDB not available - RAG disabled")

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("[WARN] requests not available - LLM disabled")

# Configuration
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION = 0.08  # 80ms chunks for wake word
WAKE_THRESHOLD = 0.5
SILENCE_THRESHOLD = 500
SILENCE_DURATION = 1.5  # seconds of silence to stop recording
MAX_RECORD_DURATION = 30  # max seconds to record

WHISPER_MODEL = "base.en"
PIPER_VOICE = "/home/mark/.roxy/piper-voices/en_US-lessac-medium.onnx"
OLLAMA_MODEL = "llama3:8b"
OLLAMA_URL = "http://localhost:11434/api/generate"

ROXY_SYSTEM_PROMPT = """You are ROXY, the AI assistant for MindSong and Mark's personal operations.

PERSONALITY:
- Warm, witty, and efficient like JARVIS
- Left-brain focused: operations, business, scheduling, systems
- Proactive and anticipatory
- Occasionally playful but always professional

CAPABILITIES:
- Voice interaction via wake word "Hey Roxy"
- Access to MindSong codebase documentation
- Schedule management and reminders
- System status monitoring
- Home automation coordination

CONTEXT:
- Running on JARVIS-1 (Mac Pro 2019, 28-core Xeon, 157GB RAM)
- Part of LUNA-000 CITADEL project
- Working alongside Rocky (the music education AI - right brain)
- Together you form the Unified Mind for MindSong

Keep responses concise for voice output (2-3 sentences max unless asked for detail).
Current time: {time}
"""

class RoxyAssistant:
    def __init__(self):
        self.audio_queue = queue.Queue()
        self.is_listening = False
        self.is_recording = False
        self.wake_detected = False

        # Initialize wake word model
        print("[ROXY] Loading wake word model...")
        self.oww = OWWModel()
        self.wake_models = list(self.oww.models.keys())
        print(f"[ROXY] Available wake words: {self.wake_models}")

        # Use hey_jarvis as placeholder until custom hey_roxy is trained
        self.wake_word = "hey_jarvis"
        if self.wake_word not in self.wake_models:
            print(f"[WARN] {self.wake_word} not found, using first available")
            self.wake_word = self.wake_models[0] if self.wake_models else None

        # Initialize RAG if available
        self.chroma_client = None
        self.collection = None
        if HAS_CHROMADB:
            try:
                chroma_path = Path.home() / ".roxy" / "chroma_db"
                if chroma_path.exists():
                    self.chroma_client = chromadb.PersistentClient(path=str(chroma_path))
                    self.collection = self.chroma_client.get_collection("mindsong_docs")
                    print(f"[ROXY] RAG loaded: {self.collection.count()} chunks")
            except Exception as e:
                print(f"[WARN] RAG init failed: {e}")

        print("[ROXY] Initialization complete")

    def audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream - adds chunks to queue"""
        if status:
            print(f"[AUDIO] {status}")
        self.audio_queue.put(indata.copy())

    def detect_wake_word(self, audio_chunk):
        """Check if wake word is detected in audio chunk"""
        if self.wake_word is None:
            return False

        # Ensure correct shape for OpenWakeWord
        if len(audio_chunk.shape) > 1:
            audio_chunk = audio_chunk.flatten()

        # Predict
        prediction = self.oww.predict(audio_chunk)

        # Check threshold
        if self.wake_word in prediction:
            score = prediction[self.wake_word]
            if score > WAKE_THRESHOLD:
                return True

        return False

    def record_speech(self):
        """Record speech until silence detected"""
        print("[ROXY] Listening...")

        frames = []
        silence_frames = 0
        silence_threshold_frames = int(SILENCE_DURATION * SAMPLE_RATE / int(CHUNK_DURATION * SAMPLE_RATE))
        max_frames = int(MAX_RECORD_DURATION * SAMPLE_RATE / int(CHUNK_DURATION * SAMPLE_RATE))

        # Clear queue
        while not self.audio_queue.empty():
            self.audio_queue.get()

        frame_count = 0
        while frame_count < max_frames:
            try:
                chunk = self.audio_queue.get(timeout=1.0)
                frames.append(chunk)
                frame_count += 1

                # Check for silence
                amplitude = np.abs(chunk).mean() * 32768
                if amplitude < SILENCE_THRESHOLD:
                    silence_frames += 1
                else:
                    silence_frames = 0

                if silence_frames > silence_threshold_frames and len(frames) > 10:
                    break

            except queue.Empty:
                break

        if not frames:
            return None

        # Concatenate all frames
        audio_data = np.concatenate(frames)
        return audio_data

    def transcribe_audio(self, audio_data):
        """Transcribe audio using Whisper"""
        print("[ROXY] Transcribing...")

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

            # Write WAV
            with wave.open(temp_path, 'wb') as wav:
                wav.setnchannels(CHANNELS)
                wav.setsampwidth(2)
                wav.setframerate(SAMPLE_RATE)

                # Convert float32 to int16
                audio_int16 = (audio_data * 32767).astype(np.int16)
                wav.writeframes(audio_int16.tobytes())

        try:
            # Run whisper
            result = subprocess.run(
                ["whisper", temp_path, "--model", WHISPER_MODEL, "--output_format", "txt", "--output_dir", "/tmp"],
                capture_output=True,
                text=True,
                timeout=60
            )

            # Read transcription
            txt_path = temp_path.replace(".wav", ".txt")
            if os.path.exists(txt_path):
                with open(txt_path, 'r') as f:
                    text = f.read().strip()
                os.unlink(txt_path)
                return text

            return None

        except Exception as e:
            print(f"[ERROR] Transcription failed: {e}")
            return None
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def query_rag(self, query, n_results=3):
        """Query ChromaDB for relevant context"""
        if not self.collection:
            return ""

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )

            if results and results['documents']:
                context = "\n\n".join(results['documents'][0])
                return context[:2000]  # Limit context size

        except Exception as e:
            print(f"[WARN] RAG query failed: {e}")

        return ""

    def get_llm_response(self, user_input, context=""):
        """Get response from Ollama"""
        if not HAS_REQUESTS:
            return "I apologize, but my language model is currently unavailable."

        system_prompt = ROXY_SYSTEM_PROMPT.format(
            time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        if context:
            system_prompt += f"\n\nRELEVANT CONTEXT:\n{context}"

        prompt = f"{system_prompt}\n\nUser: {user_input}\n\nRoxy:"

        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 256
                    }
                },
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip()

        except Exception as e:
            print(f"[ERROR] LLM request failed: {e}")

        return "I'm having trouble connecting to my language model right now."

    def speak(self, text):
        """Speak text using Piper TTS"""
        print(f"[ROXY] Speaking: {text[:100]}...")

        try:
            # Use piper for TTS
            process = subprocess.Popen(
                ["piper", "--model", PIPER_VOICE, "--output-raw"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            audio_data, _ = process.communicate(input=text.encode(), timeout=30)

            if audio_data:
                # Play audio
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                sd.play(audio_array, samplerate=22050, blocking=True)

        except FileNotFoundError:
            print("[WARN] Piper not found, falling back to espeak")
            subprocess.run(["espeak", "-s", "150", text], capture_output=True)
        except Exception as e:
            print(f"[ERROR] TTS failed: {e}")

    def process_command(self, text):
        """Process user command and generate response"""
        if not text:
            self.speak("I didn't catch that. Could you repeat?")
            return

        print(f"[ROXY] Heard: {text}")

        # Check for special commands
        text_lower = text.lower()

        if any(word in text_lower for word in ["goodbye", "bye", "exit", "quit", "stop"]):
            self.speak("Goodbye! Call me anytime.")
            self.is_listening = False
            return

        if "status" in text_lower and "system" in text_lower:
            self.speak("JARVIS-1 is operational. All systems nominal. 28 cores active, 157 gigabytes RAM available.")
            return

        if "time" in text_lower:
            now = datetime.now().strftime("%I:%M %p")
            self.speak(f"It's currently {now}")
            return

        # Query RAG for context
        context = self.query_rag(text)

        # Get LLM response
        response = self.get_llm_response(text, context)

        # Speak response
        self.speak(response)

    def run(self):
        """Main voice assistant loop"""
        print("\n" + "=" * 60)
        print("  ROXY Voice Assistant v2.0")
        print("  Say 'Hey Jarvis' to activate (placeholder for 'Hey Roxy')")
        print("  Press Ctrl+C to exit")
        print("=" * 60 + "\n")

        self.is_listening = True
        chunk_size = int(CHUNK_DURATION * SAMPLE_RATE)

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype='float32',
            blocksize=chunk_size,
            callback=self.audio_callback
        ):
            self.speak("Roxy online. How can I help?")

            while self.is_listening:
                try:
                    # Get audio chunk
                    chunk = self.audio_queue.get(timeout=1.0)

                    # Check for wake word
                    if self.detect_wake_word(chunk):
                        print("[ROXY] Wake word detected!")
                        self.speak("Yes?")

                        # Record speech
                        audio = self.record_speech()

                        if audio is not None:
                            # Transcribe
                            text = self.transcribe_audio(audio)

                            # Process
                            self.process_command(text)

                        # Reset wake word model
                        self.oww.reset()

                except queue.Empty:
                    continue
                except KeyboardInterrupt:
                    print("\n[ROXY] Shutting down...")
                    break

def main():
    """Entry point"""
    try:
        roxy = RoxyAssistant()
        roxy.run()
    except KeyboardInterrupt:
        print("\n[ROXY] Interrupted")
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
