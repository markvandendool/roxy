#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Pin Cursor threads to specific CPU cores for optimal hyperthreading

LOG_FILE="/var/log/cursor-cpu-pinning.log"

while true; do
    for pid in $(pgrep -f cursor 2>/dev/null); do
        if ! ps -p "$pid" > /dev/null 2>&1; then
            continue
        fi
        
        # Get all threads for this process
        threads=($(ps -T -p "$pid" -o tid= 2>/dev/null))
        
        if [ ${#threads[@]} -eq 0 ]; then
            continue
        fi
        
        # Distribute threads across all 56 cores (28 physical + 28 HT)
        thread_idx=0
        for tid in "${threads[@]}"; do
            if [ -n "$tid" ] && kill -0 "$tid" 2>/dev/null 2>&1; then
                # Pin to specific core (round-robin across all 56)
                core=$((thread_idx % 56))
                taskset -cp "$core" "$tid" >/dev/null 2>&1
                thread_idx=$((thread_idx + 1))
            fi
        done
    done
    sleep 5
done