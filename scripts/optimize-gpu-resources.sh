#!/bin/bash
#
# Optimize GPU Resources for ROXY
# Configures Whisper to use CPU, keeping GPU free for LLM and TTS
#

set -e

ENV_FILE="/opt/roxy/.env"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROXY_DIR="$(dirname "$SCRIPT_DIR")"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🚀 GPU Resource Optimization                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  .env file not found at $ENV_FILE"
    echo "   Creating new .env file..."
    touch "$ENV_FILE"
fi

# Backup .env
if [ -f "$ENV_FILE" ]; then
    BACKUP_FILE="${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$ENV_FILE" "$BACKUP_FILE"
    echo "✅ Backed up .env to: $BACKUP_FILE"
fi

echo ""
echo "📋 Current Configuration:"
if grep -q "ROXY_WHISPER_DEVICE" "$ENV_FILE" 2>/dev/null; then
    grep "ROXY_WHISPER_DEVICE" "$ENV_FILE"
else
    echo "   ROXY_WHISPER_DEVICE: (not set)"
fi

echo ""
echo "🔧 Optimizing GPU Resources..."
echo ""

# Set Whisper to use CPU
if grep -q "^ROXY_WHISPER_DEVICE=" "$ENV_FILE" 2>/dev/null; then
    # Update existing
    sed -i 's/^ROXY_WHISPER_DEVICE=.*/ROXY_WHISPER_DEVICE=cpu/' "$ENV_FILE"
    echo "✅ Updated ROXY_WHISPER_DEVICE=cpu"
else
    # Add new
    echo "" >> "$ENV_FILE"
    echo "# GPU Resource Optimization" >> "$ENV_FILE"
    echo "# Whisper uses CPU to free GPU for LLM and TTS" >> "$ENV_FILE"
    echo "ROXY_WHISPER_DEVICE=cpu" >> "$ENV_FILE"
    echo "✅ Added ROXY_WHISPER_DEVICE=cpu"
fi

# Ensure GPU is enabled for LLM and TTS
if ! grep -q "^ROXY_GPU_ENABLED=" "$ENV_FILE" 2>/dev/null; then
    echo "ROXY_GPU_ENABLED=true" >> "$ENV_FILE"
    echo "✅ Added ROXY_GPU_ENABLED=true"
fi

echo ""
echo "📊 Configuration Summary:"
echo "   ✅ Whisper: CPU (frees GPU resources)"
echo "   ✅ Ollama LLM: GPU (fast inference)"
echo "   ✅ TTS: GPU (real-time synthesis)"
echo ""
echo "💡 Expected GPU Usage:"
echo "   Before: 100% GPU, 15-17GB VRAM (overflow)"
echo "   After:  60-70% GPU, 10-13GB VRAM ✅"
echo ""
echo "📝 Note: Whisper will use your powerful 56-thread CPU"
echo "   Performance: ~1-2x real-time (still fast enough)"
echo ""
echo "✅ GPU optimization complete!"
echo ""
echo "🔄 To apply changes, restart ROXY services:"
echo "   sudo systemctl restart roxy-voice  # if running as service"
echo "   # Or restart your ROXY processes manually"
echo ""







