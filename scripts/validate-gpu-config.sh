#!/bin/bash
#
# Validate GPU Configuration
# Checks that all GPU settings are properly configured
#

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🔍 GPU Configuration Validation                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

ERRORS=0
WARNINGS=0

# Check .env file exists
if [ ! -f /opt/roxy/.env ]; then
    echo "❌ /opt/roxy/.env not found"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ .env file exists"
fi
echo ""

# Check GPU environment variables
echo "1. Checking GPU environment variables..."
if grep -q "ROXY_GPU_ENABLED=true" /opt/roxy/.env 2>/dev/null; then
    echo "   ✅ ROXY_GPU_ENABLED=true"
else
    echo "   ⚠️  ROXY_GPU_ENABLED not set or not true"
    WARNINGS=$((WARNINGS + 1))
fi

if grep -q "ROXY_GPU_DEVICE=cuda" /opt/roxy/.env 2>/dev/null; then
    echo "   ✅ ROXY_GPU_DEVICE=cuda"
else
    echo "   ⚠️  ROXY_GPU_DEVICE not set to cuda"
    WARNINGS=$((WARNINGS + 1))
fi

if grep -q "ROXY_GPU_COMPUTE_TYPE=float16" /opt/roxy/.env 2>/dev/null; then
    echo "   ✅ ROXY_GPU_COMPUTE_TYPE=float16"
else
    echo "   ⚠️  ROXY_GPU_COMPUTE_TYPE not set to float16"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# Check Ollama configuration
echo "2. Checking Ollama configuration..."
if grep -q "OLLAMA_HOST=" /opt/roxy/.env 2>/dev/null; then
    OLLAMA_HOST=$(grep "OLLAMA_HOST=" /opt/roxy/.env | cut -d= -f2)
    echo "   ✅ OLLAMA_HOST=$OLLAMA_HOST"
else
    echo "   ⚠️  OLLAMA_HOST not set"
    WARNINGS=$((WARNINGS + 1))
fi

if grep -q "OLLAMA_MODEL=" /opt/roxy/.env 2>/dev/null; then
    OLLAMA_MODEL=$(grep "OLLAMA_MODEL=" /opt/roxy/.env | cut -d= -f2)
    echo "   ✅ OLLAMA_MODEL=$OLLAMA_MODEL"
else
    echo "   ⚠️  OLLAMA_MODEL not set"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# Check CUDA device
echo "3. Checking CUDA device configuration..."
if grep -q "CUDA_VISIBLE_DEVICES=" /opt/roxy/.env 2>/dev/null; then
    CUDA_DEVICE=$(grep "CUDA_VISIBLE_DEVICES=" /opt/roxy/.env | cut -d= -f2)
    echo "   ✅ CUDA_VISIBLE_DEVICES=$CUDA_DEVICE"
else
    echo "   ⚠️  CUDA_VISIBLE_DEVICES not set (will use default)"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# Test GPU availability
echo "4. Testing GPU availability..."
python3 << 'PYTHON_SCRIPT'
import torch
import sys

if torch.cuda.is_available():
    print(f"   ✅ CUDA available")
    print(f"   Device count: {torch.cuda.device_count()}")
    for i in range(torch.cuda.device_count()):
        print(f"   Device {i}: {torch.cuda.get_device_name(i)}")
else:
    print("   ❌ CUDA not available")
    sys.exit(1)
PYTHON_SCRIPT

if [ $? -eq 0 ]; then
    echo "   ✅ GPU test passed"
else
    echo "   ❌ GPU test failed"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Summary
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     📊 Validation Summary                                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo "✅ All checks passed!"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo "⚠️  Configuration valid with $WARNINGS warning(s)"
    exit 0
else
    echo "❌ Configuration has $ERRORS error(s) and $WARNINGS warning(s)"
    exit 1
fi

