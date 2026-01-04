# 🎤 How to Voice Chat with ROXY

## Quick Start

### Option 1: Direct Voice Test (Easiest - Recommended)

Test voice features without wake word:

```bash
cd /opt/roxy
bash scripts/test-voice-direct.sh
```

This gives you options to:
1. **Test Transcription** - Record audio and see it transcribed
2. **Test TTS** - Type text and hear ROXY speak
3. **Test Full Pipeline** - Complete voice interaction
4. **Check Audio Devices** - See available microphones

### Option 2: Use Wake Word Service

The voice service listens for "Hey Roxy" wake word:

```bash
# Check service status
sudo systemctl status roxy-voice

# View logs (to see if it's working)
sudo journalctl -u roxy-voice -f
```

**Note**: The service may need audio device configuration. Use Option 1 for immediate testing.

---

## Current Status

### ✅ What's Working:
- **Whisper Transcription** - CPU-optimized, ready to use
- **TTS (Text-to-Speech)** - GPU-accelerated, ready to use
- **LLM Integration** - Ollama running, ready for responses

### ⚠️ What Needs Setup:
- **Wake Word Detection** - Audio device sample rate needs configuration
- **Audio Input** - May need device selection

---

## Step-by-Step: Test Voice Features

### 1. Test Transcription (CPU-Optimized)

```bash
cd /opt/roxy
source venv/bin/activate

# Record audio (5 seconds)
python3 << 'EOF'
import pyaudio
import wave
import sys

CHUNK = 4096
FORMAT = pyaudio.paInt16
CHANNELS = 1
RECORD_SECONDS = 5

p = pyaudio.PyAudio()

# Find working device
device_index = None
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxInputChannels'] > 0:
        try:
            rate = int(info['defaultSampleRate'])
            stream = p.open(format=FORMAT, channels=CHANNELS, rate=rate,
                          input=True, input_device_index=i, frames_per_buffer=CHUNK)
            device_index = i
            RATE = rate
            stream.close()
            print(f"Using device {i}: {info['name']} at {rate}Hz")
            break
        except:
            continue

if device_index is None:
    print("No working audio device")
    sys.exit(1)

print("Recording 5 seconds... (speak now!)")
stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                input=True, input_device_index=device_index, frames_per_buffer=CHUNK)

frames = []
for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    data = stream.read(CHUNK)
    frames.append(data)

stream.stop_stream()
stream.close()
p.terminate()

wf = wave.open('/tmp/test_audio.wav', 'wb')
wf.setnchannels(CHANNELS)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(RATE)
wf.writeframes(b''.join(frames))
wf.close()

print("Saved to /tmp/test_audio.wav")
EOF

# Transcribe
python3 << 'EOF'
import os
os.environ['ROXY_WHISPER_DEVICE'] = 'cpu'
import sys
sys.path.insert(0, '/opt/roxy')
from voice.transcription.service import RoxyTranscription

transcriber = RoxyTranscription(model_size='base', device='auto')
result = transcriber.transcribe_file('/tmp/test_audio.wav')
print(f"\n✅ You said: {result['text']}")
EOF
```

### 2. Test TTS (Text-to-Speech)

```bash
cd /opt/roxy
source venv/bin/activate

python3 << 'EOF'
import sys
sys.path.insert(0, '/opt/roxy')
from voice.tts.service_edge import RoxyTTS

tts = RoxyTTS()
tts.speak("Hello! This is ROXY speaking. The GPU optimization is working perfectly!")
EOF
```

### 3. Test Full Pipeline (Manual)

```bash
cd /opt/roxy
source venv/bin/activate

# Record your question
# (use the recording script from step 1, save to /tmp/question.wav)

# Then run:
python3 << 'EOF'
import os
import sys
os.environ['ROXY_WHISPER_DEVICE'] = 'cpu'
sys.path.insert(0, '/opt/roxy')

# Transcribe
from voice.transcription.service import RoxyTranscription
transcriber = RoxyTranscription(model_size='base', device='auto')
result = transcriber.transcribe_file('/tmp/question.wav')
question = result['text']
print(f"🎤 You asked: {question}")

# Get LLM response (using Ollama)
import requests
response = requests.post('http://localhost:11434/api/generate', json={
    'model': 'llama3:8b',
    'prompt': question,
    'stream': False
})
answer = response.json()['response']
print(f"🤖 ROXY: {answer}")

# Speak response
from voice.tts.service_edge import RoxyTTS
tts = RoxyTTS()
tts.speak(answer)
EOF
```

---

## Troubleshooting

### Audio Device Issues

**Problem**: "Invalid sample rate" error

**Solution**: The wake word listener has been updated to auto-detect sample rates. If you still have issues:

1. Check available devices:
```bash
bash scripts/test-voice-direct.sh
# Choose option 4
```

2. The code now auto-detects and uses the correct sample rate

### Service Not Starting

**Check logs**:
```bash
sudo journalctl -u roxy-voice -n 50
```

**Restart service**:
```bash
sudo systemctl restart roxy-voice
```

### GPU Usage Monitoring

While testing, monitor GPU:
```bash
# In another terminal
watch -n 1 rocm-smi
```

**Expected**:
- Whisper: 0% GPU (uses CPU) ✅
- LLM: 40-70% GPU ✅
- TTS: 30-50% GPU ✅
- Total: 60-70% GPU (not 100%) ✅

---

## Next Steps

1. **Test transcription** - Verify CPU usage works
2. **Test TTS** - Verify GPU usage for speech
3. **Test full pipeline** - End-to-end voice interaction
4. **Fix wake word** - Once basic features work, configure wake word detection

---

## Summary

**Easiest way to test right now**:
```bash
cd /opt/roxy
bash scripts/test-voice-direct.sh
```

This lets you test each component individually without worrying about wake word configuration!







