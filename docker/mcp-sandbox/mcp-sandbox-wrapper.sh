#!/bin/sh
# MCP Sandbox Wrapper
# Wraps MCP server execution with bubblewrap isolation
#
# Usage: mcp-sandbox-wrapper <mcp-server-package> [args...]
# Example: mcp-sandbox-wrapper @modelcontextprotocol/server-github

set -e

MCP_SERVER="$1"
shift

# Configuration
MEMORY_LIMIT_MB="${MCP_MEMORY_LIMIT:-512}"
TIME_LIMIT_SECS="${MCP_TIME_LIMIT:-300}"
ALLOWED_PATHS="${MCP_ALLOWED_PATHS:-}"
NETWORK_MODE="${MCP_NETWORK:-none}"

# Logging
LOG_FILE="/sandbox/logs/mcp-$(date +%s).log"
log() {
    echo "[$(date -Iseconds)] $*" >> "$LOG_FILE"
}

log "Starting MCP server: $MCP_SERVER"
log "Memory limit: ${MEMORY_LIMIT_MB}MB"
log "Time limit: ${TIME_LIMIT_SECS}s"
log "Network: $NETWORK_MODE"

# Build bubblewrap command
BWRAP_ARGS="
    --unshare-all
    --share-net
    --die-with-parent
    --proc /proc
    --dev /dev
    --tmpfs /tmp
"

# Add read-only system binds
for dir in /usr /bin /lib /lib64 /etc/ssl; do
    if [ -d "$dir" ]; then
        BWRAP_ARGS="$BWRAP_ARGS --ro-bind $dir $dir"
    fi
done

# Add allowed paths (read-only by default)
if [ -n "$ALLOWED_PATHS" ]; then
    IFS=','
    for path in $ALLOWED_PATHS; do
        if [ -d "$path" ]; then
            BWRAP_ARGS="$BWRAP_ARGS --ro-bind $path $path"
            log "Allowed path (ro): $path"
        fi
    done
fi

# Writable work directory
BWRAP_ARGS="$BWRAP_ARGS --bind /sandbox/work /sandbox/work --chdir /sandbox/work"

# Set resource limits
ulimit -v $((MEMORY_LIMIT_MB * 1024))
ulimit -t $TIME_LIMIT_SECS

# Execute with timeout
timeout $TIME_LIMIT_SECS bwrap $BWRAP_ARGS npx -y "$MCP_SERVER" "$@" 2>>"$LOG_FILE" || {
    EXIT_CODE=$?
    log "MCP server exited with code: $EXIT_CODE"
    exit $EXIT_CODE
}
