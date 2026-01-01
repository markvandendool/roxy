#!/bin/bash
#
# Setup PyTorch with ROCm Support
# Verifies installation and tests GPU operations
#

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🔧 PyTorch ROCm Setup                                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if PyTorch is already installed
echo "1. Checking PyTorch installation..."
python3 -c "
import torch
print(f'   PyTorch version: {torch.__version__}')
print(f'   CUDA available: {torch.cuda.is_available()}')
" 2>&1

if python3 -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
    echo "   ✅ PyTorch with ROCm is already installed and working"
else
    echo "   ⚠️  PyTorch ROCm not properly configured"
    echo ""
    echo "   To install PyTorch with ROCm 6.0:"
    echo "   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.0"
fi
echo ""

# Test GPU operations
echo "2. Testing GPU tensor operations..."
python3 << 'PYTHON_SCRIPT'
import torch
import sys

if not torch.cuda.is_available():
    print("   ❌ CUDA/ROCm not available")
    sys.exit(1)

try:
    # Create test tensors on GPU
    print("   Creating test tensors on GPU...")
    x = torch.randn(1000, 1000).cuda()
    y = torch.randn(1000, 1000).cuda()
    
    # Perform matrix multiplication
    print("   Performing matrix multiplication...")
    z = torch.matmul(x, y)
    
    # Check result
    print(f"   ✅ GPU operations successful")
    print(f"   Result shape: {z.shape}")
    print(f"   Result device: {z.device}")
    print(f"   GPU memory allocated: {torch.cuda.memory_allocated(0) / 1024**2:.2f} MB")
    
except Exception as e:
    print(f"   ❌ GPU operation failed: {e}")
    sys.exit(1)
PYTHON_SCRIPT

echo ""
echo "✅ PyTorch ROCm setup verification complete"










