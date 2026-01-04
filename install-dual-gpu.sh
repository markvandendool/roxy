#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 INSTALL DUAL-GPU OLLAMA CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
# This script applies engineering-grade optimizations for:
#   GPU[0]: AMD Radeon Pro W5700X (16GB)
#   GPU[1]: AMD Radeon RX 6900 XT (16GB)
# ═══════════════════════════════════════════════════════════════════════════════

set -e

echo "🔬 DUAL-GPU OLLAMA OPTIMIZER"
echo "═══════════════════════════════════════════════════════════════"

# Check if running as root for systemd changes
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  This script needs sudo for systemd changes"
    echo "   Re-running with sudo..."
    exec sudo "$0" "$@"
fi

CONFIG_SRC="$HOME/.roxy/ollama-dual-gpu.conf"
if [ ! -f "$CONFIG_SRC" ]; then
    CONFIG_SRC="/home/mark/.roxy/ollama-dual-gpu.conf"
fi

CONFIG_DIR="/etc/systemd/system/ollama.service.d"
CONFIG_DST="$CONFIG_DIR/dual-gpu.conf"

echo ""
echo "📊 Current GPU Status:"
rocm-smi --showuse 2>/dev/null | grep -E "GPU\[" | head -4

echo ""
echo "📋 Current Ollama Config:"
systemctl show ollama --property=Environment | tr ' ' '\n' | grep -E "OLLAMA|HIP|ROCR" | head -10

echo ""
echo "🔧 Installing new configuration..."

# Backup old configs
if [ -f "$CONFIG_DIR/gpu-stability.conf" ]; then
    echo "   📦 Backing up gpu-stability.conf"
    mv "$CONFIG_DIR/gpu-stability.conf" "$CONFIG_DIR/gpu-stability.conf.bak"
fi

# Install new config
echo "   📄 Installing dual-gpu.conf"
cp "$CONFIG_SRC" "$CONFIG_DST"

# Reload systemd
echo "   🔄 Reloading systemd daemon"
systemctl daemon-reload

# Restart Ollama
echo "   🔄 Restarting Ollama service"
systemctl restart ollama

# Wait for startup
sleep 3

echo ""
echo "✅ Installation Complete!"
echo ""
echo "📊 New GPU Status:"
rocm-smi --showuse 2>/dev/null | grep -E "GPU\[" | head -4

echo ""
echo "📋 New Ollama Config:"
systemctl show ollama --property=Environment | tr ' ' '\n' | grep -E "OLLAMA|HIP|ROCR|SCHED"

echo ""
echo "🧪 To verify both GPUs are used:"
echo "   watch -n 1 'rocm-smi --showuse'"
echo ""
echo "   Then run parallel requests:"
echo "   for i in {1..8}; do curl -s localhost:11434/api/generate -d '{\"model\":\"tinyllama\",\"prompt\":\"Hi\"}' & done"
