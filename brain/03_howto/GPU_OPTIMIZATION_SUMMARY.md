# 🚀 GPU Optimization Summary

**Date**: January 2, 2026  
**Issue**: RX 6900 XT hitting 100% GPU usage during roxy testing  
**Solution**: Hybrid CPU/GPU workload distribution

---

## ✅ What Was Done

### 1. Infrastructure Audit
- ✅ Analyzed current GPU/CPU hardware
- ✅ Identified VRAM overflow issue (15-17GB needed, only 16GB available)
- ✅ Documented all models and their resource usage

### 2. Code Updates
- ✅ Updated `voice/transcription/service.py` to support CPU offloading
- ✅ Updated `content-pipeline/transcriber.py` to use CPU by default
- ✅ Added environment variable `ROXY_WHISPER_DEVICE=cpu` support

### 3. Configuration
- ✅ Created optimization script: `scripts/optimize-gpu-resources.sh`
- ✅ Applied configuration: Whisper now uses CPU
- ✅ Backed up `.env` file

---

## 📊 Resource Distribution

### Before Optimization:
| Component | Device | VRAM | GPU Load |
|-----------|--------|------|----------|
| Whisper large-v3 | GPU | 3-4 GB | 60-80% |
| Ollama llama3:8b | GPU | 8-10 GB | 40-70% |
| TTS XTTS v2 | GPU | 2-3 GB | 30-50% |
| **Total** | **GPU** | **15-17 GB** | **100%** ⚠️ |

### After Optimization:
| Component | Device | VRAM | GPU Load |
|-----------|--------|------|----------|
| Whisper large-v3 | **CPU** | 0 GB | 0% |
| Ollama llama3:8b | GPU | 8-10 GB | 40-70% |
| TTS XTTS v2 | GPU | 2-3 GB | 30-50% |
| **Total** | **Hybrid** | **10-13 GB** | **60-70%** ✅ |

---

## 🎯 Expected Results

### GPU Usage:
- **Before**: 100% GPU, VRAM overflow risk
- **After**: 60-70% GPU, stable operation ✅

### Performance Impact:
- **Whisper**: 5-10x → 1-2x real-time (still fast enough)
- **Ollama**: No change (still on GPU)
- **TTS**: No change (still on GPU)

### System Stability:
- ✅ No VRAM overflow
- ✅ No GPU throttling
- ✅ Better thermal management
- ✅ More headroom for other tasks

---

## 🔧 Configuration

### Environment Variable:
```bash
ROXY_WHISPER_DEVICE=cpu  # Force CPU for Whisper
ROXY_GPU_ENABLED=true    # Keep GPU for LLM/TTS
```

### To Revert (if needed):
```bash
# Use GPU for Whisper (not recommended)
ROXY_WHISPER_DEVICE=cuda
```

---

## 📋 Next Steps

1. **Restart ROXY services** to apply changes:
   ```bash
   # If running as systemd service
   sudo systemctl restart roxy-voice
   
   # Or restart your ROXY processes manually
   ```

2. **Test GPU usage**:
   ```bash
   # Monitor GPU
   rocm-smi
   
   # Should see ~60-70% max instead of 100%
   ```

3. **Verify transcription quality**:
   - Test voice commands
   - Check transcription accuracy
   - CPU performance should be acceptable (1-2x real-time)

---

## 💡 Why This Works

### Your Hardware:
- **CPU**: Xeon W-3275 (28 cores, 56 threads) - Extremely powerful
- **GPU**: RX 6900 XT (16GB VRAM) - Excellent for AI
- **RAM**: 157GB - Plenty of headroom

### The Solution:
- **CPU is powerful enough** for Whisper transcription
- **GPU is reserved** for LLM and TTS (real-time critical)
- **Better resource balance** across the system
- **No hardware upgrade needed** - optimization is better than buying new GPU

---

## 🎓 Key Insights

1. **GPU bottleneck was VRAM, not compute power**
   - RX 6900 XT has plenty of compute
   - 16GB VRAM was the limiting factor

2. **CPU is underutilized**
   - 56 threads can easily handle Whisper
   - Better to use CPU for transcription

3. **Hybrid approach is optimal**
   - GPU for what needs it (LLM, TTS)
   - CPU for what can tolerate it (transcription)

4. **No hardware upgrade needed**
   - Save $1000+ on new GPU
   - Get better results through optimization

---

## 📚 Documentation

- **Full Audit**: `INFRASTRUCTURE_AUDIT_GPU_OPTIMIZATION.md`
- **Optimization Script**: `scripts/optimize-gpu-resources.sh`
- **GPU Setup Guide**: `GPU_SETUP_GUIDE.md`

---

## ✅ Conclusion

Your RX 6900 XT is sufficient. The issue was resource management, not hardware capability. Moving Whisper to CPU solves the 100% GPU usage problem while maintaining excellent performance.

**Status**: ✅ Optimized and ready to test!








---

## 🎬 OBS Streaming/Recording GPU Assignment

**Updated**: January 10, 2026

### Hardware Mapping (VERIFIED)

| GPU | DRM Device | PCI Slot | Connectors | Display Status |
|-----|------------|----------|------------|----------------|
| **RX 6900 XT** (Navi 21) | card0 / renderD128 | 0000:14:00.0 | DP-7, DP-8, DP-9, HDMI-A-1 | **NO DISPLAYS** |
| **W5700X** (Navi 10) | card1 / renderD129 | 0000:09:00.0 | DP-1 through DP-6 | **DP-3, DP-5, DP-6 connected** |

### Role Assignment

| GPU | Role | Reason |
|-----|------|--------|
| **W5700X** (renderD129) | Desktop / Display | Has monitors connected - runs the UI |
| **RX 6900 XT** (renderD128) | VAAPI Encoding | No displays - 100% free for encoding |

### OBS VAAPI Configuration

The RX 6900 XT supports hardware encoding via VAAPI:

**Supported Encoding Profiles:**
- H.264 (Main, High, Constrained Baseline) - EncSlice
- HEVC/H.265 (Main, Main10) - EncSlice ✅ Best for recording
- JPEG Baseline

**Decode Support (bonus):**
- H.264, HEVC, VP9, AV1, MPEG2, VC1, JPEG

### OBS Profile: Linux_VAAPI_Optimal

**Location**: `~/.config/obs-studio/basic/profiles/Linux_VAAPI_Optimal/`

**Settings:**
- **Streaming Encoder**: VAAPI H.264 on renderD128
- **Recording Encoder**: VAAPI HEVC on renderD128
- **Resolution**: 3840x2160 @ 60fps
- **Recording Format**: MKV (remux to MP4 after)
- **Replay Buffer**: 120 seconds, 4GB
- **Audio**: 320kbps AAC

### Scene Collection: Linux_VAAPI_Optimal

**Location**: `~/.config/obs-studio/basic/scenes/Linux_VAAPI_Optimal.json`

Clean Linux-native scene collection with:
- PulseAudio sources (not CoreAudio)
- PipeWire display capture
- No macOS legacy sources

### VAAPI Device Selection

To force OBS to use the RX 6900 XT:

```bash
# In OBS Settings > Output > Streaming/Recording
# VAAPI Device: /dev/dri/renderD128

# Or launch OBS with:
LIBVA_DRM_DEVICE=/dev/dri/renderD128 obs
```

### Known Issues Fixed

1. **Harry_Elgato_LINUX.json**: 9.9MB corrupted scene collection
   - Contains 347,791 lines
   - Has macOS CoreAudio sources
   - **Causes OBS to crash on load**
   - Solution: Use Linux_VAAPI_Optimal.json instead

2. **Default profile uses x264**: CPU encoding wastes resources
   - Solution: Switch to Linux_VAAPI_Optimal profile
