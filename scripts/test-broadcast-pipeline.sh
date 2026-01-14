#!/bin/bash
# Test broadcasting pipeline end-to-end

set -e

echo "=== Broadcasting Pipeline Test ==="
echo ""

# 1. Test audio routing
echo "[1/6] Testing audio routing..."
if pactl get-default-source > /dev/null 2>&1; then
    echo "✅ Default input: $(pactl get-default-source)"
else
    echo "❌ No default input set"
fi

if pactl get-default-sink > /dev/null 2>&1; then
    echo "✅ Default output: $(pactl get-default-sink)"
else
    echo "❌ No default output set"
fi

# 2. Test OBS
echo ""
echo "[2/6] Testing OBS..."
if command -v obs > /dev/null; then
    echo "✅ OBS installed: $(obs --version)"
else
    echo "❌ OBS not found"
fi

# Check OBS WebSocket plugin
if [ -f ~/.config/obs-studio/plugin_config/obs-websocket/config.json ]; then
    echo "✅ OBS WebSocket config exists"
else
    echo "⚠️  OBS WebSocket config not found"
fi

# 3. Test Ardour
echo ""
echo "[3/6] Testing DAW..."
if command -v ardour > /dev/null 2>&1; then
    echo "✅ Ardour installed: "
else
    echo "❌ Ardour not found"
fi

# 4. Test content pipeline scripts
echo ""
echo "[4/6] Testing content pipeline scripts..."
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
cd "$ROXY_ROOT"
source venv/bin/activate

SCRIPTS=(
    "content-pipeline/whisperx_transcriber.py"
    "content-pipeline/clip_extractor.py"
    "content-pipeline/encoding_presets.py"
    "content-pipeline/viral_detector.py"
)

for script in "${SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        echo "✅ $script"
    else
        echo "❌ $script missing"
    fi
done

# 5. Test Python dependencies
echo ""
echo "[5/6] Testing Python dependencies..."
python3 -c "import obsws_python; print('✅ obsws-python')" 2>/dev/null || echo "❌ obsws-python"
python3 -c "import faster_whisper; print('✅ faster-whisper')" 2>/dev/null || echo "❌ faster-whisper"
python3 -c "import ollama; print('✅ ollama')" 2>/dev/null || echo "❌ ollama"

# 6. Test n8n
echo ""
echo "[6/6] Testing n8n..."
if curl -s http://localhost:5678/healthz > /dev/null 2>&1; then
    echo "✅ n8n is running"
else
    echo "⚠️  n8n not accessible (may need to start)"
fi

echo ""
echo "=== Test Complete ==="
echo ""
echo "Next steps:"
echo "1. Start OBS: obs"
echo "2. Configure OBS scenes"
echo "3. Test recording: python scripts/obs_automation.py start"
echo "4. Import n8n workflows"
echo "5. Test content pipeline with sample video"
