#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
#
# Direct Voice Test - Test ROXY voice without wake word
# This lets you test transcription and TTS directly
#

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🎤 ROXY Direct Voice Test                               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

cd ${ROXY_ROOT:-$HOME/.roxy}
source venv/bin/activate

echo "📋 Options:"
echo "   1. Test transcription (record audio, transcribe)"
echo "   2. Test TTS (text to speech)"
echo "   3. Test full pipeline (record → transcribe → LLM → TTS)"
echo "   4. Check audio devices"
echo ""
read -p "Choose option (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🎙️  Testing Transcription..."
        echo "   Recording 5 seconds of audio..."
        echo "   (Speak into your microphone)"
        echo ""
        
        # Record audio
        RECORDING=$(mktemp /tmp/roxy_test_XXXXXX.wav)
        arecord -d 5 -f cd -t wav "$RECORDING" 2>/dev/null || \
        rec -r 16000 -c 1 -t wav "$RECORDING" trim 0 5 2>/dev/null || {
            echo "❌ Could not record audio. Trying Python recording..."
            python3 << 'PYEOF'
import pyaudio
import wave
import sys

CHUNK = 4096
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 5

p = pyaudio.PyAudio()

# Try to find a working device
device_index = None
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxInputChannels'] > 0:
        try:
            # Try to open with this device
            stream = p.open(format=FORMAT,
                          channels=CHANNELS,
                          rate=int(info['defaultSampleRate']),
                          input=True,
                          input_device_index=i,
                          frames_per_buffer=CHUNK)
            device_index = i
            RATE = int(info['defaultSampleRate'])
            stream.close()
            break
        except:
            continue

if device_index is None:
    print("❌ No working audio input device found")
    sys.exit(1)

print(f"✅ Using device {device_index} at {RATE}Hz")
print("   Recording 5 seconds... (speak now!)")

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK)

frames = []
for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    data = stream.read(CHUNK, exception_on_overflow=False)
    frames.append(data)

stream.stop_stream()
stream.close()
p.terminate()

WAV_OUTPUT = "/tmp/roxy_test_recording.wav"
wf = wave.open(WAV_OUTPUT, 'wb')
wf.setnchannels(CHANNELS)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(RATE)
wf.writeframes(b''.join(frames))
wf.close()

print(f"✅ Recording saved: {WAV_OUTPUT}")
PYEOF
        }
        
        if [ -f "$RECORDING" ] || [ -f "/tmp/roxy_test_recording.wav" ]; then
            AUDIO_FILE="${RECORDING:-/tmp/roxy_test_recording.wav}"
            echo ""
            echo "📝 Transcribing..."
            python3 << PYEOF
import os
import sys
os.environ['ROXY_WHISPER_DEVICE'] = 'cpu'
sys.path.insert(0, '${ROXY_ROOT:-$HOME/.roxy}')
from voice.transcription.service import RoxyTranscription

transcriber = RoxyTranscription(model_size='base', device='auto')
result = transcriber.transcribe_file('$AUDIO_FILE')
print(f"\n✅ Transcription:")
print(f"   {result['text']}")
PYEOF
            rm -f "$RECORDING" /tmp/roxy_test_recording.wav
        fi
        ;;
        
    2)
        echo ""
        echo "🎤 Testing TTS..."
        read -p "Enter text to speak: " text
        python3 << PYEOF
import sys
sys.path.insert(0, '${ROXY_ROOT:-$HOME/.roxy}')
from voice.tts.service_edge import RoxyTTS

tts = RoxyTTS()
print(f"Speaking: {text}")
tts.speak("$text")
PYEOF
        ;;
        
    3)
        echo ""
        echo "🔄 Testing Full Pipeline..."
        echo "   This will: Record → Transcribe → LLM → TTS"
        echo ""
        echo "   Recording 5 seconds..."
        # Similar to option 1 but with full pipeline
        echo "   (Full pipeline test - coming soon)"
        ;;
        
    4)
        echo ""
        echo "🔍 Available Audio Devices:"
        python3 << 'PYEOF'
import pyaudio
p = pyaudio.PyAudio()
print("\nInput Devices:")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxInputChannels'] > 0:
        print(f"  {i}: {info['name']}")
        print(f"     Sample Rate: {info['defaultSampleRate']}Hz")
        print(f"     Channels: {info['maxInputChannels']}")
        print()
p.terminate()
PYEOF
        ;;
        
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "✅ Test complete!"











