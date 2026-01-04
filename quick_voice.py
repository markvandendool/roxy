#!/usr/bin/env python3
"""
ROXY Quick Voice Chat
Simple push-to-talk voice chat using speech_recognition

Usage:
    python quick_voice.py
    
Press SPACE to talk, release to process.
"""

import sys
import time
import queue
import threading
from pathlib import Path

# Audio
import speech_recognition as sr

# TTS - try multiple backends
TTS_ENGINE = None

def init_tts():
    global TTS_ENGINE
    
    # Try pyttsx3 first (local, fast)
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 180)  # Slightly fast
        TTS_ENGINE = ('pyttsx3', engine)
        return
    except:
        pass
    
    # Try edge-tts (requires async)
    try:
        import edge_tts
        TTS_ENGINE = ('edge', None)
        return
    except:
        pass
    
    print("⚠️ No TTS engine available. Responses will be text-only.")
    TTS_ENGINE = ('none', None)


def speak(text: str):
    """Speak text using available TTS"""
    
    if TTS_ENGINE[0] == 'pyttsx3':
        TTS_ENGINE[1].say(text)
        TTS_ENGINE[1].runAndWait()
        
    elif TTS_ENGINE[0] == 'edge':
        import asyncio
        import edge_tts
        import io
        import sounddevice as sd
        from pydub import AudioSegment
        
        async def speak_async():
            communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            
            # Play audio
            audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
            samples = audio.get_array_of_samples()
            import numpy as np
            sd.play(np.array(samples), samplerate=audio.frame_rate)
            sd.wait()
        
        asyncio.run(speak_async())
    
    else:
        print(f"🔊 {text}")


def query_roxy(text: str) -> str:
    """Query ROXY for response"""
    
    import requests
    
    token_file = Path.home() / ".roxy" / "secret.token"
    token = token_file.read_text().strip() if token_file.exists() else ""
    
    try:
        response = requests.post(
            "http://127.0.0.1:8766/run",
            headers={
                "X-ROXY-Token": token,
                "Content-Type": "application/json"
            },
            json={"command": text},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("response", data.get("result", str(data)))
        else:
            return f"Error: HTTP {response.status_code}"
            
    except Exception as e:
        return f"Error: {e}"


def main():
    """Main voice chat loop"""
    
    print("\n" + "="*60)
    print("🎤 ROXY Quick Voice Chat")
    print("="*60)
    print("Speak after the beep. I'll respond when you pause.")
    print("Say 'exit' or 'quit' to stop.")
    print("="*60 + "\n")
    
    # Initialize
    init_tts()
    recognizer = sr.Recognizer()
    
    # Adjust for ambient noise
    print("🔧 Calibrating microphone...")
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
    print("✓ Ready!\n")
    
    speak("Hello! I'm ROXY. How can I help you?")
    
    while True:
        try:
            # Listen
            print("🎤 Listening... (speak now)")
            
            with sr.Microphone() as source:
                audio = recognizer.listen(
                    source,
                    timeout=10,
                    phrase_time_limit=15
                )
            
            # Transcribe
            print("🔄 Processing...")
            
            try:
                # Try Whisper first (local, accurate)
                text = recognizer.recognize_whisper(
                    audio,
                    model="tiny",
                    language="english"
                )
            except:
                # Fallback to Google (requires internet)
                text = recognizer.recognize_google(audio)
            
            if not text:
                continue
            
            print(f"👤 You: {text}")
            
            # Check for exit commands
            if text.lower().strip() in ['exit', 'quit', 'goodbye', 'bye']:
                speak("Goodbye!")
                break
            
            # Query ROXY
            response = query_roxy(text)
            print(f"🤖 ROXY: {response}")
            
            # Speak response
            speak(response)
            
        except sr.WaitTimeoutError:
            print("⏰ No speech detected, listening again...")
            continue
            
        except sr.UnknownValueError:
            print("❓ Could not understand audio, try again...")
            continue
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
            
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
    
    print("\n" + "="*60)
    print("Session ended. Thank you for chatting!")
    print("="*60)


if __name__ == "__main__":
    main()
