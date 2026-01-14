# 🎤 ROXY Voice Chat - Ready to Use!

**Status**: ✅ **FULLY FUNCTIONAL**

---

## 🚀 Quick Start

### Option 1: Interactive Voice Chat (Recommended)

Complete voice interaction - Record → Transcribe → LLM → TTS:

```bash
cd /opt/roxy
source venv/bin/activate
python3 scripts/voice-chat-interactive.py
```

**What it does**:
1. Records 5 seconds of audio from your microphone
2. Transcribes it using Whisper (CPU-optimized)
3. Gets response from Ollama LLM (GPU)
4. Speaks the response using TTS (GPU)

**Usage**:
- Press Enter to start recording
- Speak your question/command
- Wait for ROXY to respond
- Press Ctrl+C to exit

### Option 2: Test Individual Components

```bash
cd /opt/roxy
bash scripts/test-voice-direct.sh
```

Choose from menu:
- **Option 1**: Test transcription only
- **Option 2**: Test TTS only
- **Option 3**: Test full pipeline
- **Option 4**: Check audio devices

---

## 📊 GPU Usage Verification

While using voice chat, monitor GPU in another terminal:

```bash
watch -n 1 rocm-smi
```

**Expected GPU Usage**:
- **Whisper Transcription**: 0% GPU (uses CPU) ✅
- **Ollama LLM**: 40-70% GPU ✅
- **TTS**: 30-50% GPU ✅
- **Total**: 60-70% GPU (not 100%) ✅

---

## ✅ What's Working

### Components:
- ✅ **Whisper Transcription** - CPU-optimized, working
- ✅ **Ollama LLM** - GPU-accelerated, working
- ✅ **TTS (Text-to-Speech)** - GPU-accelerated, working
- ✅ **Audio Recording** - Auto-detects devices
- ✅ **Full Pipeline** - End-to-end voice interaction

### Optimizations:
- ✅ **GPU Resource Management** - Whisper uses CPU
- ✅ **Audio Device Detection** - Auto-finds working devices
- ✅ **Sample Rate Handling** - Auto-detects and handles

---

## 🎯 Usage Examples

### Example 1: Simple Question

```bash
python3 scripts/voice-chat-interactive.py
# Press Enter
# Say: "What is the weather like?"
# ROXY responds with LLM answer
# ROXY speaks the answer
```

### Example 2: Command

```bash
python3 scripts/voice-chat-interactive.py
# Press Enter
# Say: "Tell me a joke"
# ROXY responds and speaks
```

### Example 3: Conversation

```bash
python3 scripts/voice-chat-interactive.py
# Press Enter, ask question
# Press Enter again, ask follow-up
# Continue conversation...
```

---

## 🔧 Troubleshooting

### Audio Device Not Found

**Problem**: "No working audio device found"

**Solution**:
1. Check microphone is connected
2. Check audio permissions:
   ```bash
   # Add user to audio group
   sudo usermod -a -G audio $USER
   # Log out and back in
   ```

3. Test audio device:
   ```bash
   bash scripts/test-voice-direct.sh
   # Choose option 4
   ```

### GPU Still at 100%

**Problem**: GPU usage still high during transcription

**Solution**:
1. Verify configuration:
   ```bash
   cat /opt/roxy/.env | grep ROXY_WHISPER_DEVICE
   # Should show: ROXY_WHISPER_DEVICE=cpu
   ```

2. Check transcription is using CPU:
   ```bash
   # During transcription, check:
   lsof /dev/dri/card* | grep python
   # Should be empty (no GPU usage)
   ```

### LLM Not Responding

**Problem**: "Having trouble connecting to LLM"

**Solution**:
1. Check Ollama is running:
   ```bash
   systemctl status ollama
   ```

2. Test Ollama directly:
   ```bash
   curl http://localhost:11434/api/tags
   ```

3. Restart Ollama if needed:
   ```bash
   sudo systemctl restart ollama
   ```

---

## 📝 Configuration

### Environment Variables

Current settings in `/opt/roxy/.env`:
```bash
ROXY_WHISPER_DEVICE=cpu      # Whisper uses CPU
ROXY_GPU_ENABLED=true        # GPU enabled for LLM/TTS
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3:8b
```

### Audio Settings

- **Sample Rate**: Auto-detected from device
- **Channels**: Mono (1 channel)
- **Format**: 16-bit PCM
- **Device**: Auto-detected

---

## 🎓 How It Works

### 1. Recording
- Uses PyAudio to capture audio
- Auto-detects working audio device
- Records 5 seconds (configurable)

### 2. Transcription
- Uses faster-whisper with "base" model
- Runs on CPU (optimized)
- Returns text transcription

### 3. LLM Processing
- Sends transcription to Ollama
- Uses llama3:8b model
- Runs on GPU (fast inference)

### 4. TTS
- Uses XTTS v2 for voice synthesis
- Runs on GPU (real-time)
- Speaks the response

---

## 📈 Performance

### Expected Performance:
- **Recording**: Real-time
- **Transcription**: 1-2x real-time (CPU)
- **LLM Response**: 20-50 tokens/second (GPU)
- **TTS**: 0.2-0.5 seconds per sentence (GPU)

### Total Latency:
- **Typical**: 5-10 seconds for full cycle
- **Breakdown**:
  - Recording: 5 seconds
  - Transcription: 2-3 seconds (CPU)
  - LLM: 1-3 seconds (GPU)
  - TTS: 1-2 seconds (GPU)

---

## 🚀 Next Steps

1. **Test the system**:
   ```bash
   python3 scripts/voice-chat-interactive.py
   ```

2. **Monitor GPU**:
   ```bash
   watch -n 1 rocm-smi
   ```

3. **Verify optimization**:
   - GPU should stay under 80%
   - Whisper should use CPU
   - LLM and TTS should use GPU

4. **Customize** (optional):
   - Change recording duration
   - Use different Whisper model size
   - Adjust LLM model

---

## ✅ Status Summary

- ✅ **GPU Optimization**: Complete and tested
- ✅ **Voice Components**: All working
- ✅ **Audio Detection**: Auto-configured
- ✅ **End-to-End**: Fully functional
- ✅ **Documentation**: Complete

**You're ready to voice chat with ROXY!** 🎉

---

**Quick Command**:
```bash
cd /opt/roxy && source venv/bin/activate && python3 scripts/voice-chat-interactive.py
```







