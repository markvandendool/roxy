#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
#
# Verify GPU Setup for ROXY
# Checks ROCm, PyTorch, and GPU availability
#

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🔍 ROXY GPU Setup Verification                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check ROCm
echo "1. Checking ROCm installation..."
if command -v rocm-smi &> /dev/null; then
    echo "   ✅ rocm-smi found"
    rocm-smi 2>&1 | head -10
else
    echo "   ⚠️  rocm-smi not found (optional for monitoring)"
    echo "   Install: sudo apt install rocm-smi"
fi
echo ""

# Check PyTorch
echo "2. Checking PyTorch with ROCm..."
python3 -c "
import torch
print(f'   PyTorch version: {torch.__version__}')
print(f'   CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'   Device count: {torch.cuda.device_count()}')
    for i in range(torch.cuda.device_count()):
        print(f'   Device {i}: {torch.cuda.get_device_name(i)}')
        props = torch.cuda.get_device_properties(i)
        print(f'      Memory: {props.total_memory / 1024**3:.1f} GB')
else:
    print('   ❌ CUDA/ROCm not available')
" 2>&1
echo ""

# Check faster-whisper
echo "3. Checking faster-whisper..."
python3 -c "
try:
    from faster_whisper import WhisperModel
    print('   ✅ faster-whisper installed')
except ImportError:
    print('   ❌ faster-whisper not installed')
    print('   Install: pip install faster-whisper')
" 2>&1
echo ""

# Check Ollama
echo "4. Checking Ollama..."
if command -v ollama &> /dev/null; then
    echo "   ✅ Ollama installed"
    ollama list 2>&1 | head -5 || echo "   ⚠️  Ollama not running or no models"
else
    echo "   ❌ Ollama not installed"
fi
echo ""

# Check GPU device files
echo "5. Checking GPU device files..."
if [ -e /dev/dri/card2 ]; then
    echo "   ✅ RX 6900 XT device found: /dev/dri/card2"
    ls -l /dev/dri/card2
else
    echo "   ⚠️  GPU device not found at /dev/dri/card2"
fi
echo ""

# Test GPU tensor operation
echo "6. Testing GPU tensor operation..."
python3 -c "
import torch
if torch.cuda.is_available():
    try:
        x = torch.randn(1000, 1000).cuda()
        y = torch.randn(1000, 1000).cuda()
        z = torch.matmul(x, y)
        print('   ✅ GPU tensor operations working')
        print(f'   Result shape: {z.shape}')
    except Exception as e:
        print(f'   ❌ GPU tensor operation failed: {e}')
else:
    print('   ⚠️  CUDA not available for testing')
" 2>&1
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     📊 Verification Complete                                ║"
echo "╚════════════════════════════════════════════════════════════╝"









