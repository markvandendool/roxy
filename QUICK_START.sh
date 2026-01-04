#!/bin/bash
# Quick Start Script - Roxy Workspace

echo "🚀 Roxy Workspace Quick Start"
echo "=============================="
echo ""
echo "1. Starting Mindsong Juke Hub..."
cd /opt/roxy/mindsong-juke-hub
pnpm dev > /tmp/mindsong-dev.log 2>&1 &
echo "   → Dev server starting on http://127.0.0.1:9135"
echo ""
echo "2. System Vitals Monitor..."
if ! pgrep -x conky > /dev/null; then
    conky -c ~/.config/conky/conky.conf > /dev/null 2>&1 &
    echo "   → Vitals overlay started (top-right corner)"
else
    echo "   → Vitals overlay already running"
fi
echo ""
echo "3. System Status:"
echo "   → MIDI Devices: $(aconnect -l 2>/dev/null | grep -c 'client' || echo '0')"
echo "   → Audio Sinks: $(wpctl status 2>/dev/null | grep -c 'Sink' || echo 'N/A')"
echo "   → Bluetooth: $(bluetoothctl show 2>&1 | grep -q 'Controller' && echo 'Ready' || echo 'No controller')"
echo ""
echo "✅ Quick Start Complete!"
echo "📊 Check top-right for system vitals"
echo "🌐 Open http://127.0.0.1:9135 for Mindsong app"
