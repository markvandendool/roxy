#!/bin/sh
# Sandboxed Filesystem MCP Server Wrapper
# Restricts filesystem access to explicitly allowed paths only

set -e

# Parse allowed paths from environment
ALLOWED_PATHS="${MCP_READONLY_PATHS:-/sandbox/work}"
MEMORY_LIMIT="${MCP_MEMORY_LIMIT:-256}"
TIME_LIMIT="${MCP_TIME_LIMIT:-60}"

# Build bubblewrap command with filesystem restrictions
BWRAP="bwrap
    --unshare-all
    --share-net
    --die-with-parent
    --proc /proc
    --dev /dev
    --tmpfs /tmp
    --ro-bind /usr /usr
    --ro-bind /bin /bin
    --ro-bind /lib /lib
"

# Add lib64 if exists
if [ -d /lib64 ]; then
    BWRAP="$BWRAP --ro-bind /lib64 /lib64"
fi

# Add allowed paths as read-only
for path in $(echo "$ALLOWED_PATHS" | tr ',' '\n'); do
    if [ -d "$path" ]; then
        # Create mount point and bind read-only
        BWRAP="$BWRAP --ro-bind $path $path"
    fi
done

# Writable work directory (for temp files)
BWRAP="$BWRAP --bind /sandbox/work /sandbox/work --chdir /sandbox/work"

# Set resource limits (512MB memory, 60s CPU)
ulimit -v $((MEMORY_LIMIT * 1024))
ulimit -t $TIME_LIMIT

# Log execution
echo "[MCP-FILESYSTEM] Starting with paths: $ALLOWED_PATHS"
echo "[MCP-FILESYSTEM] Memory limit: ${MEMORY_LIMIT}MB"
echo "[MCP-FILESYSTEM] Time limit: ${TIME_LIMIT}s"

# Execute filesystem MCP server with all allowed paths as arguments
exec $BWRAP /usr/local/bin/mcp-server-filesystem $ALLOWED_PATHS
