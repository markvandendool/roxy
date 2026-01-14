# 🎤 CITADEL Phase 4 - Voice Control Deployment

**Date**: January 1, 2026  
**Status**: 🚧 IN PROGRESS (Edge TTS workaround active)

## ⚠️ Python Version Limitation

**Issue**: Coqui TTS (XTTS v2) requires Python < 3.12, but system has Python 3.12.3

**Workaround**: Using Edge TTS (Microsoft Edge TTS API) as temporary solution
- ✅ Works with Python 3.12
- ✅ Natural-sounding voices (including female voices)
- ✅ No model download needed
- ✅ Free and unlimited
- ⚠️ Requires internet connection
- ⚠️ Not voice cloning (uses pre-trained voices)

**Future**: When TTS supports Python 3.12, migrate to XTTS v2 for voice cloning

---

## Components

### 1. ✅ Edge TTS (Temporary - until XTTS v2 supports Python 3.12)
- **Tool**: Edge TTS (Microsoft Edge TTS API)
- **Location**: `/opt/roxy/voice/tts/service_edge.py`
- **Status**: Installed and working
- **Voice**: Auto-selected natural female voice (AriaNeural)
- **Note**: XTTS v2 service.py created but requires Python < 3.12

### 2. ⏳ Reference Voice Recording
- **Location**: `/opt/roxy/voice/reference/roxy_voice.wav`
- **Status**: Pending (needs 30+ seconds of reference audio)
- **Requirement**: Clean, natural speech, varied intonation

### 3. ⏳ openWakeWord
- **Purpose**: Wake word detection ("Hey Roxy")
- **Status**: Not installed yet
- **Story**: LUNA-030

### 4. ⏳ faster-whisper
- **Purpose**: Speech-to-text (AMD GPU accelerated)
- **Status**: Not installed yet
- **Story**: LUNA-031

---

## Installation Details

### XTTS v2 Installation
```bash
cd /opt/roxy
source venv/bin/activate
pip install TTS
```

### Directory Structure
```
/opt/roxy/voice/
├── tts/
│   ├── service.py          # TTS service (XTTS v2)
│   └── models/             # Model cache
├── reference/
│   └── roxy_voice.wav      # Reference voice (to be recorded)
├── wakeword/
│   └── models/             # Wake word models
└── transcription/
    └── models/             # Whisper models
```

---

## Usage

### Test TTS (Default Voice)
```bash
cd /opt/roxy
source venv/bin/activate
python voice/tts/service.py "Hello! I am Roxy!" --output /tmp/test.wav
paplay /tmp/test.wav
```

### Voice Cloning (After Reference Recording)
```bash
python voice/tts/service.py "Hello! This is my cloned voice!" \
  --voice voice/reference/roxy_voice.wav \
  --output /tmp/roxy_cloned.wav
paplay /tmp/roxy_cloned.wav
```

### Python API
```python
from voice.tts.service import RoxyTTS

tts = RoxyTTS()
tts.speak("Hello! I am Roxy!", speaker_wav="voice/reference/roxy_voice.wav")
```

---

## Voice Cloning Process

### Step 1: Record Reference Audio
- **Duration**: 30+ seconds (60+ recommended)
- **Quality**: Clean, no background noise
- **Format**: WAV, 16kHz or higher
- **Content**: Natural speech, varied intonation

### Step 2: Place Reference File
```bash
cp your_recording.wav /opt/roxy/voice/reference/roxy_voice.wav
```

### Step 3: Test Cloning
```bash
python voice/tts/service.py "Test message" --voice voice/reference/roxy_voice.wav
```

---

## Acceptance Criteria (from Epic)

### XTTS v2 (LUNA-032)
- ✅ TTS installed
- ⏳ Voice sounds natural and recognizable (pending reference recording)
- ⏳ Synthesis latency < 500ms for first word (to be tested)
- ⏳ Streaming audio output working (to be tested)
- ⏳ Emotion/tone control working (to be tested)

### Voice Pipeline (LUNA-080)
- ⏳ "Hey Roxy" activates listening (openWakeWord pending)
- ⏳ Natural conversation flow (pending)
- ⏳ TTS response in Roxy's voice (pending reference recording)
- ⏳ Runs continuously as service (pending)
- ⏳ End-to-end latency < 2 seconds (pending)

---

## Next Steps

1. **Record Reference Voice** (30+ seconds)
   - Save to `/opt/roxy/voice/reference/roxy_voice.wav`
   - Test voice cloning

2. **Install openWakeWord** (LUNA-030)
   - Train "Hey Roxy" wake word
   - Create always-listening service

3. **Install faster-whisper** (LUNA-031)
   - Set up AMD GPU acceleration (CTranslate2-rocm)
   - Configure transcription service

4. **Create Voice Pipeline** (LUNA-080)
   - Connect wake word → transcription → LLM → TTS
   - Implement conversation state management

---

## Troubleshooting

### TTS Model Download
The first run will download the XTTS v2 model (~1.5GB). This may take time.

### GPU Acceleration
XTTS v2 supports CUDA. Check GPU availability:
```python
import torch
print(torch.cuda.is_available())
```

### Reference Voice Quality
- Use high-quality microphone
- Record in quiet environment
- Speak naturally with varied intonation
- Minimum 30 seconds, 60+ recommended

---

**Deployment Started**: January 1, 2026  
**Epic**: LUNA-000 CITADEL  
**Phase**: PHASE-4 Voice Control  
**Status**: 🚧 IN PROGRESS

