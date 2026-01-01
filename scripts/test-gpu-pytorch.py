#!/usr/bin/env python3
"""
Test GPU PyTorch Operations
Verifies ROCm/CUDA functionality
"""

import torch
import sys

def test_gpu():
    """Test GPU availability and operations"""
    print("🔍 Testing GPU PyTorch Operations...")
    print("")
    
    # Check CUDA availability
    if not torch.cuda.is_available():
        print("❌ CUDA/ROCm not available")
        return False
    
    print(f"✅ CUDA available")
    print(f"   Device count: {torch.cuda.device_count()}")
    print(f"   Current device: {torch.cuda.current_device()}")
    print(f"   Device name: {torch.cuda.get_device_name(0)}")
    print("")
    
    # Get device properties
    props = torch.cuda.get_device_properties(0)
    print(f"📊 Device Properties:")
    print(f"   Total memory: {props.total_memory / 1024**3:.2f} GB")
    print(f"   Multiprocessors: {props.multi_processor_count}")
    print("")
    
    # Test tensor operations
    print("🧪 Testing tensor operations...")
    try:
        # Create tensors on GPU
        x = torch.randn(1000, 1000, device='cuda')
        y = torch.randn(1000, 1000, device='cuda')
        
        # Matrix multiplication
        z = torch.matmul(x, y)
        
        print(f"   ✅ Matrix multiplication successful")
        print(f"   Result shape: {z.shape}")
        print(f"   Result device: {z.device}")
        print(f"   Memory allocated: {torch.cuda.memory_allocated(0) / 1024**2:.2f} MB")
        print(f"   Memory reserved: {torch.cuda.memory_reserved(0) / 1024**2:.2f} MB")
        print("")
        
        # Test more operations
        print("🧪 Testing additional operations...")
        a = torch.randn(5000, 5000, device='cuda')
        b = a * 2.0
        c = torch.sum(b)
        
        print(f"   ✅ Additional operations successful")
        print(f"   Sum result: {c.item():.2f}")
        print("")
        
        return True
        
    except Exception as e:
        print(f"   ❌ GPU operation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_gpu()
    sys.exit(0 if success else 1)










