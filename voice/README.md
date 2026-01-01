# 🎤 Roxy Voice System

**Status**: Phase 4 - Voice Control (In Progress)  
**Epic**: LUNA-000 CITADEL

---

## Components

### 1. XTTS v2 Voice Cloning ✅
- **Location**: `/opt/roxy/voice/tts/service.py`
- **Model**: Coqui XTTS v2
- **Status**: Installed and ready
- **Usage**: See below

### 2. Reference Voice (Pending)
- **Location**: `/opt/roxy/voice/reference/roxy_voice.wav`
- **Status**: Not recorded yet
- **Requirement**: 30+ seconds of clean reference audio

### 3. Wake Word Detection (Pending)
- **Tool**: openWakeWord
- **Wake Word**: "Hey Roxy"
- **Status**: Not installed yet

### 4. Speech-to-Text (Pending)
- **Tool**: faster-whisper (with CTranslate2-rocm for AMD GPU)
- **Status**: Not installed yet

---

## Quick Start

### Test TTS (Default Voice)
```bash
cd /opt/roxy
source venv/bin/activate
python voice/tts/service.py "Hello! I am Roxy!" --output /tmp/test.wav
paplay /tmp/test.wav
```

### Clone Roxy's Voice

1. **Record Reference Audio** (30+ seconds):
   ```bash
   # Record using your preferred method
   # Save to: /opt/roxy/voice/reference/roxy_voice.wav
   ```

2. **Test Voice Cloning**:
   ```bash
   python voice/tts/service.py "Hello! This is my cloned voice!" \
     --voice voice/reference/roxy_voice.wav \
     --output /tmp/roxy_cloned.wav
   paplay /tmp/roxy_cloned.wav
   ```

---

## Voice Cloning Process

### Step 1: Record Reference Audio
- **Duration**: Minimum 30 seconds (60+ seconds recommended)
- **Quality**: Clean, no background noise
- **Format**: WAV, 16kHz or higher
- **Content**: Natural speech, varied intonation

### Step 2: Place Reference File
```bash
cp your_recording.wav /opt/roxy/voice/reference/roxy_voice.wav
```

### Step 3: Test Cloning
```bash
cd /opt/roxy
source venv/bin/activate
python voice/tts/service.py "Test message" --voice voice/reference/roxy_voice.wav
```

---

## Integration

### With MCP Server
The TTS service can be integrated into the Voice MCP server for Claude to use.

### With Voice Pipeline
- Wake word → Transcription → LLM → TTS (Roxy's voice)

---

## Current Status

✅ **Installed**:
- Coqui TTS (XTTS v2)
- TTS service script

⏳ **Pending**:
- Reference voice recording
- Voice cloning test
- Wake word detection (openWakeWord)
- Speech-to-text (faster-whisper)

---

## Files

- `/opt/roxy/voice/tts/service.py` - TTS service
- `/opt/roxy/voice/reference/roxy_voice.wav` - Reference voice (to be recorded)
- `/opt/roxy/voice/README.md` - This file

---

**Next Steps**: Record Roxy's reference voice and test cloning!



