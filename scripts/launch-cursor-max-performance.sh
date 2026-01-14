#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"

# Launch Cursor with maximum performance settings

echo "🚀 Launching Cursor with ALL 56 cores + maximum priority..."

# Launch Cursor
/opt/cursor.AppImage "$@" &

# Wait for it to start
sleep 2

# Force all cores and max priority
ALL_CORES=$(seq -s, 0 55)
for pid in $(pgrep -f cursor 2>/dev/null); do
    taskset -acp $ALL_CORES $pid 2>/dev/null
    renice -n -20 -p $pid 2>/dev/null
    ionice -c 1 -n 0 -p $pid 2>/dev/null
    echo "✅ Optimized PID $pid"
done

echo "✅ Cursor launched with maximum performance"