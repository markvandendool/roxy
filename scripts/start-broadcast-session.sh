#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Start a complete broadcasting session

set -e

echo "=== Starting Broadcasting Session ==="
echo ""

# 1. Start performance monitoring
echo "[1/4] Starting performance monitoring..."
if ! pgrep -f "conky.*conky-topbar" > /dev/null; then
    conky -c ~/.config/conky/conky-topbar.conf > /dev/null 2>&1 &
    echo "✅ Conky started"
else
    echo "✅ Conky already running"
fi

# 2. Verify OBS connection
echo ""
echo "[2/4] Verifying OBS WebSocket..."
cd ${ROXY_ROOT:-$HOME/.roxy} && source venv/bin/activate
if python scripts/obs_automation.py status > /dev/null 2>&1; then
    echo "✅ OBS WebSocket connected"
else
    echo "⚠️  OBS WebSocket not connected"
    echo "   Start OBS: obs"
    echo "   Enable WebSocket: Tools → WebSocket Server Settings"
fi

# 3. Check n8n
echo ""
echo "[3/4] Checking n8n..."
if curl -s http://localhost:5678/healthz > /dev/null 2>&1; then
    echo "✅ n8n running"
else
    echo "⚠️  n8n not running"
    echo "   Start: docker compose -f ${ROXY_ROOT:-$HOME/.roxy}/compose/docker-compose.foundation.yml up -d roxy-n8n"
fi

# 4. Check content pipeline
echo ""
echo "[4/4] Checking content pipeline..."
if [ -d ${ROXY_ROOT:-$HOME/.roxy}/content-pipeline ]; then
    echo "✅ Content pipeline ready"
    echo "   Scripts: $(ls -1 ${ROXY_ROOT:-$HOME/.roxy}/content-pipeline/*.py 2>/dev/null | wc -l) found"
else
    echo "❌ Content pipeline not found"
fi

echo ""
echo "=== Broadcasting Session Ready ==="
echo ""
echo "Quick Commands:"
echo "  Start recording: python scripts/obs_automation.py start"
echo "  Stop recording:  python scripts/obs_automation.py stop"
echo "  View monitor:    btop"
echo "  n8n:             http://localhost:5678"
echo ""
