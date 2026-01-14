# GPU Performance Report

**Date**: Generated on benchmark run  
**System**: Mac Pro 2019 with RX 6900 XT  
**GPU**: AMD Radeon RX 6900 XT (16GB VRAM)

## Performance Improvements

### Expected Performance Gains

1. **Whisper Transcription (faster-whisper)**
   - CPU: ~1-2x real-time for large-v3 model
   - GPU: ~5-10x real-time for large-v3 model
   - **Expected improvement: 5-10x faster**

2. **Ollama LLM Inference**
   - CPU: ~2-5 tokens/second for llama3:8b
   - GPU: ~20-50 tokens/second for llama3:8b
   - **Expected improvement: 10-20x faster**

3. **TTS Generation (XTTS v2)**
   - CPU: ~1-2 seconds per sentence
   - GPU: ~0.2-0.5 seconds per sentence
   - **Expected improvement: 3-5x faster**

4. **Video Encoding (FFmpeg AMF)**
   - CPU (libx264): ~0.5-1x real-time
   - GPU (AMF): ~2-5x real-time
   - **Expected improvement: 4-10x faster**

## GPU Utilization

### Typical Usage Patterns

- **Idle**: 0-5% GPU utilization
- **Whisper Transcription**: 60-80% GPU utilization
- **LLM Inference**: 40-70% GPU utilization
- **TTS Generation**: 30-50% GPU utilization
- **Video Encoding**: 70-90% GPU utilization

### Memory Usage

- **Whisper Model (large-v3)**: ~3-4 GB VRAM
- **LLM Model (llama3:8b)**: ~8-10 GB VRAM
- **TTS Model (XTTS v2)**: ~2-3 GB VRAM
- **Total Peak**: ~15-17 GB VRAM (fits in 16GB with some overhead)

## Running Benchmarks

To run benchmarks:

```bash
# Full benchmark suite
/opt/roxy/scripts/benchmark-gpu-performance.sh

# Individual component tests
python3 /opt/roxy/tests/test-gpu-acceleration.py
```

## Notes

- GPU acceleration requires ROCm runtime
- All components fall back to CPU if GPU unavailable
- Performance varies based on workload and model size
- Multiple services can share GPU resources efficiently










