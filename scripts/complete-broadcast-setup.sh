#!/bin/bash
# Complete Broadcasting Pipeline Setup
# Runs all setup scripts in order

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     Broadcasting Pipeline - Complete Setup                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

SCRIPTS_DIR="/opt/roxy/scripts"

# 1. Audio routing
echo "[1/5] Audio Routing..."
bash "$SCRIPTS_DIR/setup-audio-routing.sh" 2>&1 | grep -E "✅|⚠️|❌" || true

# 2. OBS scenes
echo ""
echo "[2/5] OBS Scenes..."
bash "$SCRIPTS_DIR/create-obs-scenes.sh" 2>&1 | grep -E "✅|⚠️|❌" || true

# 3. OBS WebSocket (if plugin installed)
echo ""
echo "[3/5] OBS WebSocket..."
if [ -f ~/.config/obs-studio/plugin_config/obs-websocket/config.json ]; then
    echo "✅ OBS WebSocket configured"
    PASSWORD=$(cat ~/.config/obs-studio/plugin_config/obs-websocket/config.json | grep -o '"password": "[^"]*' | cut -d'"' -f4)
    echo "   Password saved to /opt/roxy/.env"
else
    echo "⚠️  OBS WebSocket plugin not installed"
    echo "   Run: cd /tmp/obs-websocket/build && sudo make install"
fi

# 4. Content pipeline test
echo ""
echo "[4/5] Content Pipeline..."
cd /opt/roxy
source venv/bin/activate
python3 -c "
import sys
from pathlib import Path
scripts = [
    'content-pipeline/whisperx_transcriber.py',
    'content-pipeline/clip_extractor.py',
    'content-pipeline/encoding_presets.py',
    'content-pipeline/viral_detector.py'
]
all_ok = True
for script in scripts:
    if Path(script).exists():
        print(f'✅ {script}')
    else:
        print(f'❌ {script} missing')
        all_ok = False
sys.exit(0 if all_ok else 1)
" 2>&1

# 5. n8n workflows
echo ""
echo "[5/5] n8n Workflows..."
if [ -d /opt/roxy/n8n-workflows ]; then
    echo "✅ Workflow templates created"
    echo "   Import from: /opt/roxy/n8n-workflows"
else
    echo "⚠️  Workflow templates not found"
    echo "   Run: bash $SCRIPTS_DIR/create-n8n-broadcast-workflows.sh"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Setup Complete                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Quick Start:"
echo "  1. Start OBS: obs"
echo "  2. Test recording: python scripts/obs_automation.py start"
echo "  3. Import n8n workflows: http://localhost:5678"
echo "  4. Test content pipeline with sample video"
echo ""

