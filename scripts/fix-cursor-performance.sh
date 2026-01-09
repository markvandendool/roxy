#!/bin/bash

# Fix Cursor performance by setting maximum priority

echo "🔧 Fixing Cursor performance..."

# Find all Cursor processes
CURSOR_PIDS=$(pgrep -f cursor)

if [ -z "$CURSOR_PIDS" ]; then
    echo "⚠️  Cursor not running"
    exit 0
fi

for pid in $CURSOR_PIDS; do
    # Set highest CPU priority
    sudo renice -n -20 -p $pid 2>/dev/null
    
    # Set realtime I/O priority
    sudo ionice -c 1 -n 0 -p $pid 2>/dev/null
    
    # Set CPU affinity to performance cores (if available)
    # taskset -cp 0-27 $pid 2>/dev/null
    
    echo "✅ Optimized PID $pid"
done

echo "✅ Cursor performance fix applied"
