#!/bin/bash
#
# Verify GPU Optimization - Check that Whisper uses CPU
#

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🔍 GPU Optimization Verification                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check .env configuration
echo "📋 Configuration Check:"
if [ -f "/opt/roxy/.env" ]; then
    if grep -q "ROXY_WHISPER_DEVICE=cpu" /opt/roxy/.env; then
        echo "   ✅ ROXY_WHISPER_DEVICE=cpu (Whisper will use CPU)"
    else
        echo "   ⚠️  ROXY_WHISPER_DEVICE not set to cpu"
    fi
    
    if grep -q "ROXY_GPU_ENABLED=true" /opt/roxy/.env; then
        echo "   ✅ ROXY_GPU_ENABLED=true (LLM/TTS will use GPU)"
    else
        echo "   ⚠️  ROXY_GPU_ENABLED not set"
    fi
else
    echo "   ❌ .env file not found"
fi

echo ""
echo "🖥️  System Resources:"
echo "   CPU: $(nproc) threads available"
echo "   RAM: $(free -h | awk '/^Mem:/ {print $2}') total, $(free -h | awk '/^Mem:/ {print $7}') available"

echo ""
echo "🎮 GPU Status:"
if command -v rocm-smi &> /dev/null; then
    rocm-smi 2>&1 | head -10
else
    echo "   ⚠️  rocm-smi not available"
    echo "   Checking GPU via lspci..."
    lspci | grep -i vga
fi

echo ""
echo "📊 Expected Behavior:"
echo "   ✅ Whisper transcription: CPU (frees GPU)"
echo "   ✅ Ollama LLM: GPU (fast inference)"
echo "   ✅ TTS: GPU (real-time synthesis)"
echo "   ✅ GPU Usage: 60-70% (instead of 100%)"
echo ""

echo "🧪 To Test:"
echo "   1. Start ROXY voice service: sudo systemctl start roxy-voice"
echo "   2. Monitor GPU: watch -n 1 rocm-smi"
echo "   3. Test voice command and watch GPU usage"
echo "   4. GPU should stay under 80% during transcription"
echo ""












