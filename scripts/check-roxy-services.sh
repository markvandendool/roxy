#!/bin/bash
#
# Health Check for ROXY Services
# Checks service status and GPU utilization
#

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🔍 ROXY Services Health Check                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check JARVIS service
echo "1. JARVIS Service:"
if systemctl is-active --quiet jarvis.service; then
    echo "   ✅ Active"
    systemctl status jarvis.service --no-pager -l | grep -E "Active:|Main PID" | head -2
else
    echo "   ❌ Inactive"
fi
echo ""

# Check Voice Pipeline service
echo "2. ROXY Voice Pipeline Service:"
if systemctl is-active --quiet roxy-voice.service; then
    echo "   ✅ Active"
    systemctl status roxy-voice.service --no-pager -l | grep -E "Active:|Main PID" | head -2
else
    echo "   ⚠️  Inactive (optional service)"
fi
echo ""

# Check Ollama service
echo "3. Ollama Service:"
if systemctl is-active --quiet ollama.service; then
    echo "   ✅ Active"
    systemctl status ollama.service --no-pager -l | grep -E "Active:|Main PID" | head -2
else
    echo "   ⚠️  Inactive"
fi
echo ""

# Check GPU utilization
echo "4. GPU Utilization:"
if command -v rocm-smi &> /dev/null; then
    rocm-smi --showuse 2>&1 | head -10
else
    echo "   ⚠️  rocm-smi not available"
fi
echo ""

# Check service processes
echo "5. Running Processes:"
echo "   JARVIS:"
pgrep -af jarvis_core.py | head -2 || echo "      Not running"
echo "   Voice Pipeline:"
pgrep -af "voice/pipeline.py" | head -2 || echo "      Not running"
echo "   Ollama:"
pgrep -af ollama | head -2 || echo "      Not running"
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     📊 Health Check Complete                                ║"
echo "╚════════════════════════════════════════════════════════════╝"










