#!/bin/bash
#
# Monitor GPU Usage by ROXY Services
# Shows which services are using GPU
#

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     📊 GPU Usage by ROXY Services                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Get GPU utilization
if command -v rocm-smi &> /dev/null; then
    echo "Current GPU Status:"
    rocm-smi 2>&1 | head -10
    echo ""
else
    echo "⚠️  rocm-smi not available"
    echo ""
fi

# Check which processes are using GPU
echo "Processes using GPU devices:"
for pid in $(lsof /dev/dri/card* 2>/dev/null | awk 'NR>1 {print $2}' | sort -u); do
    if ps -p $pid > /dev/null 2>&1; then
        CMD=$(ps -p $pid -o cmd= | head -1 | cut -c1-80)
        echo "   PID $pid: $CMD"
    fi
done
echo ""

# Check service-specific GPU usage
echo "Service GPU Usage:"
echo "   ROXY (LLM inference):"
ROXY_PID=$(pgrep -f roxy_core.py | head -1)
if [ -n "$ROXY_PID" ]; then
    if lsof -p $ROXY_PID 2>/dev/null | grep -q "/dev/dri"; then
        echo "      ✅ Using GPU"
    else
        echo "      ⚠️  Not using GPU"
    fi
else
    echo "      Not running"
fi

echo "   Voice Pipeline (Transcription):"
VOICE_PID=$(pgrep -f "voice/pipeline.py" | head -1)
if [ -n "$VOICE_PID" ]; then
    if lsof -p $VOICE_PID 2>/dev/null | grep -q "/dev/dri"; then
        echo "      ✅ Using GPU"
    else
        echo "      ⚠️  Not using GPU"
    fi
else
    echo "      Not running"
fi

echo "   Ollama (LLM):"
OLLAMA_PID=$(pgrep -f ollama | head -1)
if [ -n "$OLLAMA_PID" ]; then
    if lsof -p $OLLAMA_PID 2>/dev/null | grep -q "/dev/dri"; then
        echo "      ✅ Using GPU"
    else
        echo "      ⚠️  Not using GPU"
    fi
else
    echo "      Not running"
fi
echo ""

echo "💡 To monitor continuously: watch -n 2 $0"










