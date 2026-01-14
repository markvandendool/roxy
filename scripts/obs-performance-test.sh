#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# OBS Performance Test Suite
# Tests GPU, CPU, canvas performance, encoding, etc.

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           OBS Performance Test Suite                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 1. GPU Information
echo "[1/6] GPU Information..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
lspci | grep -i vga
echo ""
lspci | grep -i "3d\|display\|vga" | head -3
echo ""

# 2. GPU Performance (AMD)
echo "[2/6] GPU Performance (AMD)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if command -v radeontop > /dev/null 2>&1; then
    echo "Running radeontop for 3 seconds..."
    timeout 3 radeontop -l 1 -d - 2>/dev/null | tail -5 || echo "radeontop output"
else
    echo "⚠️  radeontop not installed"
fi
echo ""

# 3. CPU Performance
echo "[3/6] CPU Performance..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CPU Cores: $(nproc)"
echo "CPU Model: $(lscpu | grep 'Model name' | cut -d: -f2 | xargs)"
echo "CPU Frequency: $(lscpu | grep 'CPU max MHz' | cut -d: -f2 | xargs) MHz"
echo "Load Average: $(uptime | awk -F'load average:' '{print $2}')"
echo ""

# 4. Memory Performance
echo "[4/6] Memory Performance..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
free -h
echo ""

# 5. OBS Canvas/Encoding Test
echo "[5/6] OBS Canvas/Encoding Capabilities..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if command -v obs > /dev/null 2>&1; then
    echo "OBS Version: $(obs --version 2>&1 | head -1)"
    echo ""
    echo "Available encoders:"
    obs --help 2>&1 | grep -i encoder || echo "Check OBS settings for encoder options"
    echo ""
    echo "Display resolution:"
    xrandr 2>/dev/null | grep -E 'connected.*[0-9]+x[0-9]+' | head -3 || echo "Check display config"
else
    echo "⚠️  OBS not found"
fi
echo ""

# 6. FFmpeg Performance Test
echo "[6/6] FFmpeg/Encoding Performance..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if command -v ffmpeg > /dev/null 2>&1; then
    echo "FFmpeg version:"
    ffmpeg -version 2>&1 | head -1
    echo ""
    echo "Available encoders:"
    ffmpeg -encoders 2>&1 | grep -E 'h264|hevc|av1|amd|radeon' | head -10 || echo "Check encoders"
    echo ""
    echo "Hardware acceleration:"
    ffmpeg -hwaccels 2>&1 | grep -v 'Hardware' | head -5
else
    echo "⚠️  FFmpeg not installed"
fi
echo ""

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Test Complete                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Next: Run OBS and test actual recording performance"
