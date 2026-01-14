#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
#
# Health Check for ROXY Services
# Checks service status and GPU utilization
#

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🔍 ROXY Services Health Check                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check ROXY service
echo "1. ROXY Service:"
if systemctl is-active --quiet roxy.service; then
    echo "   ✅ Active"
    systemctl status roxy.service --no-pager -l | grep -E "Active:|Main PID" | head -2
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
echo "   ROXY:"
pgrep -af roxy_core.py | head -2 || echo "      Not running"
echo "   Voice Pipeline:"
pgrep -af "voice/pipeline.py" | head -2 || echo "      Not running"
echo "   Ollama:"
pgrep -af ollama | head -2 || echo "      Not running"
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     📊 Health Check Complete                                ║"
echo "╚════════════════════════════════════════════════════════════╝"









