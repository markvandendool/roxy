#!/bin/bash
# =============================================================================
# OBS WebSocket Wait Script
# =============================================================================
#
# Purpose: Waits for OBS WebSocket server to become available on port 4455.
#          Used after obs_launch_clean.sh to ensure OBS is ready for commands.
#
# Usage:
#   ./obs_wait_ws.sh [--timeout SECONDS] [--port PORT]
#
# Defaults:
#   --timeout 30
#   --port 4455
#
# Exit codes:
#   0 - WebSocket port is listening and owned by OBS
#   1 - Timeout reached, port not available
#   2 - Port listening but not owned by OBS
# =============================================================================

set -e

TIMEOUT=30
PORT=4455
CHECK_INTERVAL=1

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

echo "[$(date -Iseconds)] Waiting for OBS WebSocket on port $PORT (timeout: ${TIMEOUT}s)..."

ELAPSED=0

while [[ $ELAPSED -lt $TIMEOUT ]]; do
    # Check if port is listening
    if ss -tlnp 2>/dev/null | grep -q ":${PORT}\b"; then
        # Verify it's owned by OBS
        OWNER=$(ss -tlnp 2>/dev/null | grep ":${PORT}\b" | grep -o 'users:(("[^"]*"' | head -1 | cut -d'"' -f2)

        if [[ "$OWNER" == "obs" ]]; then
            echo "[$(date -Iseconds)] OBS WebSocket ready on port $PORT"
            echo "SUCCESS: OBS WebSocket listening on port $PORT (owner: $OWNER)"
            exit 0
        else
            echo "[$(date -Iseconds)] Port $PORT is listening but owner is '$OWNER' (expected 'obs')"
        fi
    fi

    sleep "$CHECK_INTERVAL"
    ELAPSED=$((ELAPSED + CHECK_INTERVAL))

    # Progress indicator every 5 seconds
    if [[ $((ELAPSED % 5)) -eq 0 ]]; then
        echo "[$(date -Iseconds)] Still waiting... (${ELAPSED}s / ${TIMEOUT}s)"
    fi
done

echo "[$(date -Iseconds)] TIMEOUT: OBS WebSocket not available after ${TIMEOUT}s"
echo "ERROR: OBS WebSocket not available on port $PORT after ${TIMEOUT}s" >&2

# Diagnostics
echo "" >&2
echo "=== DIAGNOSTICS ===" >&2
echo "OBS process:" >&2
pgrep -a obs 2>/dev/null || echo "  (no OBS process found)" >&2

echo "" >&2
echo "Port $PORT status:" >&2
ss -tlnp 2>/dev/null | grep ":${PORT}\b" || echo "  (port not listening)" >&2

echo "" >&2
echo "OBS WebSocket config:" >&2
if [[ -f /home/mark/.config/obs-studio/plugin_config/obs-websocket/config.json ]]; then
    cat /home/mark/.config/obs-studio/plugin_config/obs-websocket/config.json 2>/dev/null | head -15 >&2
else
    echo "  (config file not found)" >&2
fi

exit 1
