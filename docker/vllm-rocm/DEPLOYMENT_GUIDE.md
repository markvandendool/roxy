# vLLM ROCm Deployment Guide for CITADEL
## AMD GPU (6900XT + W5700X) Production Inference Stack

### Prerequisites

1. **ROCm Installed** (5.7+)
```bash
rocm-smi  # Verify both GPUs visible
```

2. **Models Downloaded** in AWQ format (better than GGUF for GPU)
```bash
# Convert or download AWQ quantized models
mkdir -p /home/mark/models
# Qwen 2.5 Coder 14B AWQ ~9GB
# Qwen 2.5 Coder 7B AWQ ~5GB
```

3. **Docker with ROCm support**
```bash
# Add user to render/video groups
sudo usermod -a -G render,video $USER
```

### Deployment Steps

```bash
cd ~/.roxy/docker/vllm-rocm

# 1. Build custom image (if needed) or use prebuilt
# docker build -t vllm-rocm:custom .

# 2. Start services
docker-compose up -d

# 3. Verify health
curl http://localhost:11435/health
curl http://localhost:11434/health

# 4. Test inference
curl http://localhost:11430/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder-14b-awq",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Migration from Ollama

| Ollama Endpoint | vLLM Endpoint | Notes |
|-----------------|---------------|-------|
| 11434 (W5700X) | 11434 | Direct port mapping |
| 11435 (6900XT) | 11435 | Direct port mapping |
| - | 11430 | New unified router |

### Performance Expectations

| GPU | Model | Quant | Tokens/sec (vLLM) | Tokens/sec (Ollama) | Speedup |
|-----|-------|-------|-------------------|---------------------|---------|
| 6900XT | Qwen 14B | AWQ | 80-120 | 20-30 | **4x** |
| W5700X | Qwen 7B | AWQ | 60-80 | 15-25 | **3.5x** |

Key optimizations:
- **PagedAttention**: 20x throughput vs naive
- **Continuous Batching**: No request queuing
- **Prefix Caching**: Reuse KV cache for common prefixes

### Troubleshooting

**Issue**: `HIP out of memory`
- Solution: Reduce `--max-model-len` or `--gpu-memory-utilization`

**Issue**: `Unsupported architecture`
- Solution: Set `VLLM_ALLOW_DEPRECATED_ARCH=1`

**Issue**: Flash Attention errors
- Solution: Set `VLLM_USE_TRITON_FLASH_ATTENTION=0`

### Next Steps

1. **Speculative Decoding** (2x speedup)
   - Deploy draft model (Qwen 1.5B) on W5700X
   - Target model (Qwen 14B) on 6900XT
   
2. **Tensor Parallelism** (70B+ models)
   - Shard single model across both GPUs
   - Requires identical GPUs (won't work 6900XT+W5700X)

3. **Mac Studio Integration**
   - Add M2 Max as vLLM node
   - Requires ARM64 vLLM build
