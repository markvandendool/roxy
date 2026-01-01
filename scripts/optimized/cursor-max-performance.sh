#!/bin/bash
#
# Engineering-Grade Cursor Performance Optimization Script
# Based on Linux kernel documentation and systemd best practices
#
# This script forces Cursor to use all CPU cores with maximum priority
# while maintaining system stability and preventing resource starvation
#

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
ALL_CORES="0-55"
LOG_FILE="/var/log/cursor-performance.log"
MAX_ITERATIONS=1000  # Safety limit
ITERATION=0

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $*"
    exit 1
}

# Verify we're running as root (systemd runs as root)
if [ "$EUID" -ne 0 ]; then
    error_exit "This script must be run as root (via systemd)"
fi

log "Starting Cursor performance optimization service"

# Main optimization loop
while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    CURSOR_PIDS=$(pgrep -f cursor 2>/dev/null || true)
    
    if [ -z "$CURSOR_PIDS" ]; then
        # No Cursor processes running, wait longer
        sleep 5
        continue
    fi
    
    for pid in $CURSOR_PIDS; do
        # Verify process still exists
        if ! kill -0 "$pid" 2>/dev/null; then
            continue
        fi
        
        # Set CPU affinity to all cores
        if ! taskset -acp "$ALL_CORES" "$pid" >/dev/null 2>&1; then
            log "WARNING: Failed to set CPU affinity for PID $pid"
        fi
        
        # Set highest nice priority (SCHED_OTHER, priority -20)
        # Note: For true realtime, we'd use chrt -f, but that can starve system
        if ! renice -n -20 -p "$pid" >/dev/null 2>&1; then
            log "WARNING: Failed to set nice priority for PID $pid"
        fi
        
        # Set I/O priority: best-effort class, high priority (not realtime to avoid starvation)
        # Class 2 = best-effort, priority 4 = high (0-7, lower is higher priority)
        if ! ionice -c 2 -n 4 -p "$pid" >/dev/null 2>&1; then
            log "WARNING: Failed to set I/O priority for PID $pid"
        fi
        
        # Set CPU affinity and priority for all threads
        for tid in $(ps -T -p "$pid" -o tid= 2>/dev/null || true); do
            if [ -n "$tid" ] && kill -0 "$tid" 2>/dev/null; then
                taskset -acp "$ALL_CORES" "$tid" >/dev/null 2>&1 || true
                renice -n -20 -t "$tid" >/dev/null 2>&1 || true
            fi
        done
    done
    
    ITERATION=$((ITERATION + 1))
    # Increased sleep interval to reduce interruptions (30 seconds instead of 2)
    # This prevents constant process modifications that can cause crashes
    sleep 30
done

log "Maximum iterations reached, exiting"
exit 0










