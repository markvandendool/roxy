#!/usr/bin/env python3
"""
Interactive Voice Chat with ROXY
Complete voice interface: Record → Transcribe → LLM → TTS
"""

import os
import sys
import pyaudio
import wave
import tempfile
import subprocess
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set Whisper to use CPU
os.environ['ROXY_WHISPER_DEVICE'] = 'cpu'

def find_audio_device():
    """Find a working audio input device"""
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        try:
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                rate = int(info['defaultSampleRate'])
                try:
                    test_stream = p.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=rate,
                        input=True,
                        input_device_index=i,
                        frames_per_buffer=4096
                    )
                    test_stream.close()
                    p.terminate()
                    return i, rate
                except:
                    continue
        except:
            continue
    p.terminate()
    return None, None

def record_audio(duration=5, device_index=None, sample_rate=16000):
    """Record audio from microphone"""
    CHUNK = 4096
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    
    p = pyaudio.PyAudio()
    
    if device_index is None:
        device_index, sample_rate = find_audio_device()
        if device_index is None:
            print("❌ No working audio device found")
            return None
    
    print(f"🎙️  Recording {duration} seconds...")
    print("   (Speak now!)")
    
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=sample_rate,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=CHUNK
    )
    
    frames = []
    for i in range(0, int(sample_rate / CHUNK * duration)):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    temp_path = temp_file.name
    temp_file.close()
    
    wf = wave.open(temp_path, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(sample_rate)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    print("✅ Recording complete")
    return temp_path

def transcribe_audio(audio_path):
    """Transcribe audio using Whisper (CPU)"""
    print("📝 Transcribing...")
    from voice.transcription.service import RoxyTranscription
    
    transcriber = RoxyTranscription(model_size='base', device='auto')
    result = transcriber.transcribe_file(audio_path)
    
    return result['text']

def get_llm_response(text):
    """Get response from Ollama LLM"""
    print("🤖 Getting LLM response...")
    import requests
    
    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'llama3:8b',
                'prompt': text,
                'stream': False
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json()['response']
        else:
            return f"I'm having trouble connecting to the LLM. (Status: {response.status_code})"
    except Exception as e:
        return f"I'm having trouble getting a response. ({str(e)})"

def speak_text(text):
    """Speak text using TTS (GPU)"""
    print("🎤 Speaking response...")
    from voice.tts.service_edge import RoxyTTS
    
    tts = RoxyTTS()
    tts.speak(text)

def main():
    """Main interactive loop"""
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     🎤 ROXY Interactive Voice Chat                        ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print("")
    print("This will:")
    print("  1. Record your voice (5 seconds)")
    print("  2. Transcribe it (CPU)")
    print("  3. Get LLM response (GPU)")
    print("  4. Speak the response (GPU)")
    print("")
    print("Press Ctrl+C to exit")
    print("")
    
    # Find audio device
    device_index, sample_rate = find_audio_device()
    if device_index is None:
        print("❌ No working audio device found")
        print("   Please check your microphone connection")
        return
    
    print(f"✅ Using audio device {device_index} at {sample_rate}Hz")
    print("")
    
    try:
        while True:
            input("Press Enter to start recording (or Ctrl+C to exit)...")
            print("")
            
            # Record
            audio_path = record_audio(duration=5, device_index=device_index, sample_rate=sample_rate)
            if audio_path is None:
                continue
            
            try:
                # Transcribe
                transcription = transcribe_audio(audio_path)
                print(f"✅ You said: {transcription}")
                print("")
                
                if not transcription.strip():
                    print("⚠️  No speech detected, try again")
                    continue
                
                # Get LLM response
                response = get_llm_response(transcription)
                print(f"✅ ROXY: {response[:100]}...")
                print("")
                
                # Speak
                speak_text(response)
                print("✅ Response spoken")
                print("")
                
            finally:
                # Cleanup
                try:
                    os.unlink(audio_path)
                except:
                    pass
            
            print("-" * 60)
            print("")
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()












