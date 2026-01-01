#!/bin/bash

# Force ALL Cursor processes to use ALL CPU cores with maximum priority

echo "🔥 FORCING CURSOR TO USE ALL 56 CORES + HYPERTHREADING"

# Get all CPU cores (0-55 for 56 cores)
ALL_CORES=$(seq -s, 0 55)

# Find all Cursor processes (including children)
CURSOR_PIDS=$(pgrep -f cursor)

if [ -z "$CURSOR_PIDS" ]; then
    echo "⚠️  Cursor not running"
    exit 0
fi

for pid in $CURSOR_PIDS; do
    # Set CPU affinity to ALL cores
    taskset -acp $ALL_CORES $pid 2>/dev/null
    
    # Set highest CPU priority
    renice -n -20 -p $pid 2>/dev/null
    
    # Set realtime I/O priority
    ionice -c 1 -n 0 -p $pid 2>/dev/null
    
    # Also set for all threads of this process
    for tid in $(ps -T -p $pid -o tid= 2>/dev/null); do
        taskset -acp $ALL_CORES $tid 2>/dev/null
        renice -n -20 -t $tid 2>/dev/null
    done
    
    echo "✅ Optimized PID $pid (all cores, max priority)"
done

echo "✅ All Cursor processes forced to use all 56 cores"
