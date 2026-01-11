#!/bin/bash
# =============================================================================
# OBS Clean Launcher - Escapes VSCode Snap Environment Pollution
# =============================================================================
#
# Purpose: Launches OBS Studio with sanitized environment variables.
#          VSCode snap pollutes GTK/QT paths with /snap/core20 libraries
#          which causes symbol lookup errors in /usr/bin/obs.
#
# Usage:
#   ./obs_launch_clean.sh [--collection NAME] [--profile NAME]
#
# Outputs:
#   /tmp/obs_clean_startup.log - Startup log (truncated to last 200 lines)
#   /tmp/obs.pid - PID of running OBS process
#
# Exit codes:
#   0 - OBS started successfully and is still running after 8 seconds
#   1 - OBS failed to start or died within 8 seconds
# =============================================================================

set -e

LOG_FILE="/tmp/obs_clean_startup.log"
PID_FILE="/tmp/obs.pid"
STARTUP_WAIT=15  # Increased - OBS plugins take time to load
OBS_BIN="/usr/bin/obs"

# Parse arguments
COLLECTION=""
PROFILE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --collection)
            COLLECTION="$2"
            shift 2
            ;;
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

# =============================================================================
# Environment Sanitization
# =============================================================================

echo "[$(date -Iseconds)] Starting OBS clean launch..." > "$LOG_FILE"
echo "[$(date -Iseconds)] Sanitizing environment..." >> "$LOG_FILE"

# CRITICAL: Only unset GTK_PATH which points to snap libraries
# Do NOT unset GSETTINGS_SCHEMA_DIR or other schema directories
# as this breaks GNOME settings lookups
unset GTK_PATH

# Clear QT snap paths
unset QT_PLUGIN_PATH

# Clear library preload/path that might pull in snap libs
unset LD_LIBRARY_PATH
unset LD_PRELOAD

# Clear all *_VSCODE_SNAP_ORIG variables (these are backup copies)
for var in $(env | grep '_VSCODE_SNAP_ORIG' | cut -d= -f1); do
    unset "$var"
done

# Set required variables
export HOME=/home/mark
export DISPLAY=:0
export XDG_RUNTIME_DIR=/run/user/1000
export PATH=/usr/bin:/bin:/usr/sbin:/sbin

# Restore standard XDG_CONFIG_DIRS if polluted with snap
if [[ "$XDG_CONFIG_DIRS" == *"/snap/"* ]]; then
    export XDG_CONFIG_DIRS="/etc/xdg/xdg-ubuntu:/etc/xdg"
fi

echo "[$(date -Iseconds)] Environment sanitized" >> "$LOG_FILE"
echo "[$(date -Iseconds)] HOME=$HOME" >> "$LOG_FILE"
echo "[$(date -Iseconds)] DISPLAY=$DISPLAY" >> "$LOG_FILE"
echo "[$(date -Iseconds)] XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR" >> "$LOG_FILE"

# =============================================================================
# Clear crash state (prevents "unclean shutdown" dialog)
# =============================================================================

SENTINEL_DIR="/home/mark/.config/obs-studio/.sentinel"
if [[ -d "$SENTINEL_DIR" ]]; then
    rm -rf "$SENTINEL_DIR"
    echo "[$(date -Iseconds)] Cleared crash sentinel directory" >> "$LOG_FILE"
fi

# =============================================================================
# Check for existing OBS process
# =============================================================================

if pgrep -x obs > /dev/null 2>&1; then
    EXISTING_PID=$(pgrep -x obs | head -1)
    echo "[$(date -Iseconds)] OBS already running (PID: $EXISTING_PID)" >> "$LOG_FILE"
    echo "$EXISTING_PID" > "$PID_FILE"
    echo "OBS already running (PID: $EXISTING_PID)"
    exit 0
fi

# =============================================================================
# Build OBS command
# =============================================================================

# --disable-shutdown-check: Skip shutdown check dialog
# --disable-missing-files-check: Skip missing files dialog
# --disable-updater: Don't check for updates
OBS_CMD="$OBS_BIN --minimize-to-tray --disable-shutdown-check --disable-missing-files-check --disable-updater"

if [[ -n "$COLLECTION" ]]; then
    OBS_CMD="$OBS_CMD --collection \"$COLLECTION\""
fi

if [[ -n "$PROFILE" ]]; then
    OBS_CMD="$OBS_CMD --profile \"$PROFILE\""
fi

echo "[$(date -Iseconds)] Launching: $OBS_CMD" >> "$LOG_FILE"

# =============================================================================
# Launch OBS
# =============================================================================

nohup $OBS_CMD >> "$LOG_FILE" 2>&1 &
OBS_PID=$!

echo "[$(date -Iseconds)] OBS launched with PID: $OBS_PID" >> "$LOG_FILE"
echo "$OBS_PID" > "$PID_FILE"

# =============================================================================
# Wait and verify
# =============================================================================

echo "[$(date -Iseconds)] Waiting ${STARTUP_WAIT}s for OBS to stabilize..." >> "$LOG_FILE"
sleep "$STARTUP_WAIT"

if kill -0 "$OBS_PID" 2>/dev/null; then
    echo "[$(date -Iseconds)] OBS running successfully (PID: $OBS_PID)" >> "$LOG_FILE"
    echo "OBS started successfully (PID: $OBS_PID)"

    # Truncate log to last 200 lines
    tail -200 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"

    exit 0
else
    echo "[$(date -Iseconds)] ERROR: OBS died within ${STARTUP_WAIT}s" >> "$LOG_FILE"
    echo "ERROR: OBS failed to start or died within ${STARTUP_WAIT}s" >&2
    echo "Check $LOG_FILE for details" >&2

    # Show last 20 lines of log
    tail -20 "$LOG_FILE" >&2

    exit 1
fi
