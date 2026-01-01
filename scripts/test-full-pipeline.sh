#!/bin/bash
# Test broadcasting pipeline end-to-end

set -e

echo "=== Broadcasting Pipeline Test ==="
echo ""

# 1. Test OBS connection
echo "[1/4] Testing OBS WebSocket..."
cd /opt/roxy && source venv/bin/activate
python scripts/obs_automation.py status && echo "✅ OBS connected" || echo "❌ OBS not connected"

# 2. Test content pipeline scripts
echo ""
echo "[2/4] Testing content pipeline..."
for script in content-pipeline/*.py; do
    if [ -f "" ]; then
        echo "✅ "
    fi
done

# 3. Test n8n
echo ""
echo "[3/4] Testing n8n..."
curl -s http://localhost:5678/healthz > /dev/null && echo "✅ n8n running" || echo "❌ n8n not running"

# 4. Test performance monitoring
echo ""
echo "[4/4] Testing performance monitoring..."
command -v btop > /dev/null && echo "✅ btop installed" || echo "❌ btop not found"
command -v conky > /dev/null && echo "✅ conky installed" || echo "❌ conky not found"

echo ""
echo "=== Test Complete ==="
