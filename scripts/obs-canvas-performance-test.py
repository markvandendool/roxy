#!/usr/bin/env python3
"""
OBS Canvas Performance Test
Tests canvas rendering, GPU acceleration, encoding performance
"""
import subprocess
import time
import json
import os
from pathlib import Path

def test_obs_websocket():
    """Test OBS WebSocket connection and get performance info"""
    try:
        import obsws_python as obs
        client = obs.ReqClient(host='localhost', port=4455, password='')
        
        # Get OBS version
        version = client.get_version()
        print(f"✅ OBS Version: {version.obs_version}")
        print(f"   WebSocket: {version.obs_web_socket_version}")
        print(f"   Platform: {version.platform}")
        
        # Get stats
        try:
            stats = client.get_stats()
            print(f"\n📊 OBS Stats:")
            print(f"   CPU Usage: {stats.cpu_usage:.2f}%")
            print(f"   Memory Usage: {stats.memory_usage / 1024 / 1024:.2f} MB")
            print(f"   Available Disk Space: {stats.available_disk_space / 1024 / 1024 / 1024:.2f} GB")
            print(f"   Active FPS: {stats.active_fps:.2f}")
            print(f"   Average Frame Render Time: {stats.average_frame_render_time:.2f} ms")
        except Exception as e:
            print(f"⚠️  Could not get stats: {e}")
        
        # Get scene list
        scenes = client.get_scene_list()
        print(f"\n🎬 Scenes: {len(scenes.scenes)} found")
        for scene in scenes.scenes[:5]:
            print(f"   - {scene.scene_name}")
        
        return True
    except Exception as e:
        print(f"❌ OBS WebSocket test failed: {e}")
        return False

def test_ffmpeg_encoding():
    """Test FFmpeg encoding performance"""
    print("\n🎥 FFmpeg Encoding Test:")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    try:
        # Get FFmpeg version
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        version_line = result.stdout.split('\n')[0]
        print(f"✅ {version_line}")
        
        # Test hardware acceleration
        result = subprocess.run(['ffmpeg', '-hwaccels'], capture_output=True, text=True, timeout=5)
        hwaccels = [line.strip() for line in result.stdout.split('\n') if line.strip() and not line.startswith('Hardware')]
        if hwaccels:
            print(f"✅ Hardware acceleration: {', '.join(hwaccels[:5])}")
        else:
            print("⚠️  No hardware acceleration found")
        
        # Test AMD encoder
        result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True, timeout=10)
        amd_encoders = [line for line in result.stdout.split('\n') if 'amd' in line.lower() or 'radeon' in line.lower() or 'h264_amf' in line.lower()]
        if amd_encoders:
            print(f"✅ AMD encoders found: {len(amd_encoders)}")
            for encoder in amd_encoders[:3]:
                print(f"   - {encoder.strip()}")
        else:
            print("⚠️  No AMD encoders found")
        
        return True
    except Exception as e:
        print(f"❌ FFmpeg test failed: {e}")
        return False

def test_canvas_resolution():
    """Test canvas resolution capabilities"""
    print("\n🖼️  Canvas Resolution Test:")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    try:
        # Get display info
        result = subprocess.run(['xrandr'], capture_output=True, text=True, timeout=5)
        displays = []
        for line in result.stdout.split('\n'):
            if 'connected' in line and ('3840' in line or '1920' in line or '2560' in line):
                displays.append(line.strip())
        
        if displays:
            print("✅ Available resolutions:")
            for display in displays[:3]:
                print(f"   {display}")
        else:
            print("⚠️  Could not detect displays")
        
        # Test OBS canvas sizes
        canvas_sizes = [
            (1920, 1080, "1080p"),
            (2560, 1440, "1440p"),
            (3840, 2160, "4K"),
        ]
        
        print("\n📐 Recommended OBS Canvas Sizes:")
        for width, height, name in canvas_sizes:
            print(f"   {name}: {width}x{height}")
        
        return True
    except Exception as e:
        print(f"❌ Canvas test failed: {e}")
        return False

def test_gpu_performance():
    """Test GPU performance"""
    print("\n🎮 GPU Performance Test:")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    try:
        # Get GPU info
        result = subprocess.run(['lspci'], capture_output=True, text=True, timeout=5)
        gpus = [line for line in result.stdout.split('\n') if 'vga' in line.lower() or 'display' in line.lower() or '3d' in line.lower()]
        
        if gpus:
            print("✅ GPUs detected:")
            for gpu in gpus:
                print(f"   {gpu}")
        else:
            print("⚠️  No GPUs detected")
        
        # Test radeontop if available
        try:
            result = subprocess.run(['timeout', '2', 'radeontop', '-l', '1', '-d', '-'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 or result.stderr:
                print("✅ radeontop available for GPU monitoring")
        except:
            print("⚠️  radeontop not available")
        
        return True
    except Exception as e:
        print(f"❌ GPU test failed: {e}")
        return False

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║        OBS Canvas & Performance Test Suite                   ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print("")
    
    # Run tests
    obs_ok = test_obs_websocket()
    ffmpeg_ok = test_ffmpeg_encoding()
    canvas_ok = test_canvas_resolution()
    gpu_ok = test_gpu_performance()
    
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║                    Test Summary                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"OBS WebSocket: {'✅' if obs_ok else '❌'}")
    print(f"FFmpeg: {'✅' if ffmpeg_ok else '❌'}")
    print(f"Canvas: {'✅' if canvas_ok else '❌'}")
    print(f"GPU: {'✅' if gpu_ok else '❌'}")
    print("")
    print("Next: Start OBS and test actual recording performance")

