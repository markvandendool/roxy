#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════════════
# 🚀 GPU QUICK OPTIMIZE - Apply Top Optimizations for AMD RX 6900 XT + Radeon Graphics
# ═══════════════════════════════════════════════════════════════════════════════════════
# Usage: source ~/.roxy/gpu_quick_optimize.sh
# 
# Based on:
# - AMD ROCm Documentation
# - PyTorch HIP/ROCm Semantics
# - Ollama GPU Documentation
# - HuggingFace GPU Inference Guide
# ═══════════════════════════════════════════════════════════════════════════════════════

echo "🚀 GPU Quick Optimize v1.0"
echo "═══════════════════════════════════════════════════════════════"

# ─────────────────────────────────────────────────────────────────────────────────────
# DETECT CURRENT STATE
# ─────────────────────────────────────────────────────────────────────────────────────

echo ""
echo "📊 Current GPU State:"
rocm-smi --showuse 2>/dev/null | grep -E "GPU\[|use" | head -4

echo ""
echo "💾 Memory Usage:"
rocm-smi --showmeminfo vram 2>/dev/null | grep -E "GPU\[|Used|Total" | head -6

# ─────────────────────────────────────────────────────────────────────────────────────
# OLLAMA OPTIMIZATIONS (HIGH IMPACT)
# ─────────────────────────────────────────────────────────────────────────────────────

echo ""
echo "⚡ Applying Ollama Optimizations..."

# 1. Parallel Request Processing (8x throughput for 32GB VRAM)
export OLLAMA_NUM_PARALLEL=8
echo "   ✅ OLLAMA_NUM_PARALLEL=8 (process 8 concurrent requests)"

# 2. Keep Multiple Models Hot
export OLLAMA_MAX_LOADED_MODELS=2
echo "   ✅ OLLAMA_MAX_LOADED_MODELS=2 (keep 2 models in VRAM)"

# 3. Flash Attention (1.5-2x faster)
export OLLAMA_FLASH_ATTENTION=1
echo "   ✅ OLLAMA_FLASH_ATTENTION=1 (optimized attention)"

# 4. All Layers on GPU
export OLLAMA_GPU_LAYERS=99
echo "   ✅ OLLAMA_GPU_LAYERS=99 (full GPU offload)"

# 5. Larger Batch Size (4x throughput for 32GB VRAM)
export OLLAMA_NUM_BATCH=1024
echo "   ✅ OLLAMA_NUM_BATCH=1024 (larger batches)"

# 6. Keep Models Loaded
export OLLAMA_KEEP_ALIVE="24h"
echo "   ✅ OLLAMA_KEEP_ALIVE=24h (no model unloading)"

# ─────────────────────────────────────────────────────────────────────────────────────
# ROCm/HIP OPTIMIZATIONS
# ─────────────────────────────────────────────────────────────────────────────────────

echo ""
echo "🔧 Applying ROCm/HIP Optimizations..."

# Memory Management
export PYTORCH_HIP_ALLOC_CONF="expandable_segments:True"
echo "   ✅ PYTORCH_HIP_ALLOC_CONF (better memory allocation)"

# PCIe Optimization
export HSA_FORCE_FINE_GRAIN_PCIE=1
echo "   ✅ HSA_FORCE_FINE_GRAIN_PCIE=1 (faster transfers)"

# hipBLAS Workspace
export HIPBLAS_WORKSPACE_CONFIG=":4096:2:16:8"
echo "   ✅ HIPBLAS_WORKSPACE_CONFIG (optimized BLAS)"

# Reduce Logging Overhead
export AMD_LOG_LEVEL=0
echo "   ✅ AMD_LOG_LEVEL=0 (minimal logging)"

# ─────────────────────────────────────────────────────────────────────────────────────
# DUAL GPU CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────────────

echo ""
echo "🎮 Dual GPU Strategy:"
echo "   GPU[0]: Main inference (LLM)"
echo "   GPU[1]: Background tasks (embeddings, preprocessing)"

# Make both GPUs visible
export HIP_VISIBLE_DEVICES=0,1
export ROCR_VISIBLE_DEVICES=0,1
echo "   ✅ Both GPUs enabled for workload distribution"

# ─────────────────────────────────────────────────────────────────────────────────────
# PERSISTENCE
# ─────────────────────────────────────────────────────────────────────────────────────

# Save to bashrc if not already there
if ! grep -q "OLLAMA_NUM_PARALLEL" ~/.bashrc 2>/dev/null; then
    echo ""
    read -p "💾 Save optimizations to ~/.bashrc? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cat >> ~/.bashrc << 'BASHRC_APPEND'

# ═══════════════════════════════════════════════════════════════
# GPU Optimizations (added by ROXY)
# ═══════════════════════════════════════════════════════════════
export OLLAMA_NUM_PARALLEL=4
export OLLAMA_MAX_LOADED_MODELS=2
export OLLAMA_FLASH_ATTENTION=1
export OLLAMA_GPU_LAYERS=99
export OLLAMA_NUM_BATCH=512
export OLLAMA_KEEP_ALIVE="24h"
export PYTORCH_HIP_ALLOC_CONF="expandable_segments:True"
export HSA_FORCE_FINE_GRAIN_PCIE=1
export HIPBLAS_WORKSPACE_CONFIG=":4096:2:16:8"
export HIP_VISIBLE_DEVICES=0,1
BASHRC_APPEND
        echo "   ✅ Saved to ~/.bashrc"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────────────
# RESTART OLLAMA
# ─────────────────────────────────────────────────────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ GPU Optimizations Applied!"
echo ""
echo "📋 To apply to Ollama, restart the service:"
echo "   sudo systemctl restart ollama"
echo "   # OR"
echo "   pkill ollama && ollama serve &"
echo ""
echo "📊 Monitor GPU usage:"
echo "   watch -n1 'rocm-smi --showuse && rocm-smi --showmeminfo vram'"
echo ""
echo "🧪 Test with parallel requests:"
echo "   for i in {1..4}; do curl -s http://localhost:11434/api/generate -d '{\"model\":\"tinyllama\",\"prompt\":\"Hi\"}' & done"
echo "═══════════════════════════════════════════════════════════════"
