#!/bin/bash
# Ensure iStats-like monitor is running on top bar

# Kill existing conky
pkill -9 conky 2>/dev/null

# Start Conky iStats
nohup conky -c ~/.config/conky/conky-topbar-istats.conf > /tmp/conky.log 2>&1 &

sleep 1

if pgrep -f 'conky.*conky-topbar-istats' > /dev/null; then
    echo '✅ iStats monitor started'
    echo '   Shows: CPU, RAM, GPU, Temperature, Network'
    echo '   Location: Top right of central screen'
else
    echo '⚠️  Conky failed to start, check /tmp/conky.log'
fi
