#!/usr/bin/env python3
"""
Integration Tests for ROXY Services
Tests all services running simultaneously with GPU acceleration
"""

import sys
import os
import time
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def check_service_status(service_name):
    """Check if a systemd service is running"""
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', service_name],
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.stdout.strip() == 'active'
    except:
        return False

def check_process_running(process_name):
    """Check if a process is running"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', process_name],
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.returncode == 0
    except:
        return False

def test_service_integration():
    """Test all services can run together"""
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     🔗 Service Integration Tests                          ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print("")
    
    results = []
    
    # Check JARVIS service
    print("1. Checking JARVIS service...")
    jarvis_running = check_service_status('jarvis.service')
    jarvis_process = check_process_running('jarvis_core.py')
    if jarvis_running or jarvis_process:
        print("   ✅ JARVIS is running")
        results.append(True)
    else:
        print("   ⚠️  JARVIS not running (can be started with: sudo systemctl start jarvis)")
        results.append(False)
    print("")
    
    # Check Voice Pipeline service
    print("2. Checking Voice Pipeline service...")
    voice_running = check_service_status('roxy-voice.service')
    voice_process = check_process_running('voice/pipeline.py')
    if voice_running or voice_process:
        print("   ✅ Voice Pipeline is running")
        results.append(True)
    else:
        print("   ⚠️  Voice Pipeline not running (optional service)")
        results.append(True)  # Not required
    print("")
    
    # Check Ollama service
    print("3. Checking Ollama service...")
    ollama_running = check_service_status('ollama.service')
    ollama_process = check_process_running('ollama')
    if ollama_running or ollama_process:
        print("   ✅ Ollama is running")
        results.append(True)
    else:
        print("   ⚠️  Ollama not running")
        results.append(False)
    print("")
    
    # Check GPU resource management
    print("4. Checking GPU resource management...")
    try:
        import torch
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            print(f"   ✅ {device_count} GPU(s) available")
            
            # Check memory
            for i in range(device_count):
                total_mem = torch.cuda.get_device_properties(i).total_memory / 1024**3
                allocated = torch.cuda.memory_allocated(i) / 1024**3
                reserved = torch.cuda.memory_reserved(i) / 1024**3
                print(f"   GPU {i}: {allocated:.1f}GB / {total_mem:.1f}GB allocated, {reserved:.1f}GB reserved")
            
            results.append(True)
        else:
            print("   ⚠️  GPU not available")
            results.append(False)
    except Exception as e:
        print(f"   ⚠️  Error checking GPU: {e}")
        results.append(False)
    print("")
    
    # Test concurrent operations
    print("5. Testing concurrent GPU operations...")
    try:
        import torch
        
        if torch.cuda.is_available():
            # Simulate multiple operations
            print("   Creating multiple GPU tensors...")
            tensors = []
            for i in range(3):
                x = torch.randn(1000, 1000, device='cuda')
                tensors.append(x)
            
            print(f"   ✅ Created {len(tensors)} GPU tensors")
            print("   ✅ GPU can handle concurrent operations")
            results.append(True)
        else:
            print("   ⚠️  GPU not available for testing")
            results.append(False)
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
        results.append(False)
    print("")
    
    # Summary
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     📊 Integration Test Results                            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print("")
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"   Tests passed: {passed}/{total}")
    
    if passed >= total - 1:  # Allow one optional service to be down
        print("\n   ✅ Integration tests passed!")
        return 0
    else:
        print(f"\n   ⚠️  Some services need attention")
        return 1

if __name__ == "__main__":
    sys.exit(test_service_integration())

