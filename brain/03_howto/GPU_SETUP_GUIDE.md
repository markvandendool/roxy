# ROXY GPU Setup Guide

Complete guide for setting up GPU acceleration with ROXY on AMD RX 6900 XT.

## Prerequisites

- AMD RX 6900 XT GPU
- Ubuntu/Linux system
- ROCm runtime (for AMD GPU support)
- PyTorch with ROCm backend

## Installation

### 1. ROCm Runtime

ROCm should already be installed if PyTorch with ROCm is working. Verify:

```bash
rocm-smi
python3 -c "import torch; print(torch.cuda.is_available())"
```

### 2. PyTorch with ROCm

PyTorch with ROCm is already installed. Verify:

```bash
python3 -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

### 3. GPU Configuration

GPU configuration is in `/opt/roxy/.env`:

```bash
ROXY_GPU_ENABLED=true
ROXY_GPU_DEVICE=cuda
ROXY_GPU_COMPUTE_TYPE=float16
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3:8b
CUDA_VISIBLE_DEVICES=0
```

## Component Configuration

### Whisper Transcription

Whisper automatically detects and uses GPU when available. The service uses:
- Device: `cuda` (auto-detected)
- Compute type: `float16` for GPU, `float32` for CPU

### Ollama LLM

Ollama automatically detects and uses GPU. No additional configuration needed.

### TTS Service

TTS automatically detects GPU. Uses CUDA when available.

### Video Encoding

FFmpeg AMF encoding is configured but requires FFmpeg built with AMF support. Currently falls back to software encoding.

## Verification

Run the verification script:

```bash
/opt/roxy/scripts/verify-gpu-setup.sh
```

Run GPU tests:

```bash
python3 /opt/roxy/tests/test-gpu-acceleration.py
```

## Troubleshooting

### GPU Not Detected

1. Check ROCm installation: `rocm-smi`
2. Verify PyTorch: `python3 -c "import torch; print(torch.cuda.is_available())"`
3. Check device permissions: `ls -l /dev/dri/card*`

### Services Not Using GPU

1. Check environment variables: `grep ROXY_GPU /opt/roxy/.env`
2. Verify service is loading .env: Check systemd service `EnvironmentFile`
3. Check service logs: `sudo journalctl -u jarvis -f`

### Performance Issues

1. Check GPU utilization: `rocm-smi`
2. Monitor GPU memory: `watch -n 1 rocm-smi`
3. Verify compute type: Should be `float16` for GPU

## Performance Expectations

- **Whisper**: 5-10x faster on GPU
- **LLM Inference**: 10-20x faster on GPU
- **TTS**: 3-5x faster on GPU
- **Video Encoding**: 4-10x faster on GPU (when AMF available)

## Service Management

See [SERVICE_MANAGEMENT.md](SERVICE_MANAGEMENT.md) for details on managing ROXY services.










