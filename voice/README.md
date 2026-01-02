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
The Voice MCP server (`/opt/roxy/mcp-servers/voice/server.py`) exposes TTS capabilities:
- `speak(text, voice='aria')` - Speak text using Edge TTS
- `synthesize_audio(text, output_path, voice='aria')` - Generate audio file
- `list_voices()` - List available voices
- `test_voice(voice, sample_text)` - Test a voice

### With Voice Pipeline
Complete end-to-end pipeline:
1. **Wake Word Detection** (openWakeWord) - Listens for "Hey Roxy"
2. **Real-time Audio Capture** - Records after wake word until silence/timeout
3. **Speech-to-Text** (faster-whisper) - Transcribes audio
4. **LLM Processing** - Generates intelligent response
5. **Text-to-Speech** (Edge TTS) - Speaks response through speakers

### Usage

**Run Pipeline:**
```bash
cd /opt/roxy
source venv/bin/activate
python voice/pipeline.py
```

**Install Systemd Service:**
```bash
sudo cp /opt/roxy/voice/roxy-voice.service /etc/systemd/user/
systemctl --user daemon-reload
systemctl --user enable roxy-voice.service
systemctl --user start roxy-voice.service
```

**Check Status:**
```bash
systemctl --user status roxy-voice.service
journalctl --user -u roxy-voice.service -f
```

---

## Current Status

✅ **Installed & Integrated**:
- Edge TTS (working with Python 3.12)
- openWakeWord (wake word detection)
- faster-whisper (speech-to-text)
- Complete voice pipeline with real-time audio capture
- LLM integration
- MCP server updated for Edge TTS
- Systemd service created

⏳ **Optional Enhancements**:
- Reference voice recording (for voice cloning when XTTS v2 supports Python 3.12)
- Custom "Hey Roxy" wake word training
- GPU acceleration for faster-whisper (ROCm)

---

## Files

- `/opt/roxy/voice/tts/service.py` - TTS service
- `/opt/roxy/voice/reference/roxy_voice.wav` - Reference voice (to be recorded)
- `/opt/roxy/voice/README.md` - This file

---

**Next Steps**: Record Roxy's reference voice and test cloning!












