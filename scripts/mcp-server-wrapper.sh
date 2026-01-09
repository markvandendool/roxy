#!/bin/bash
# Wrapper script to load .env and run MCP servers
# Usage: mcp-server-wrapper.sh <server-name>

SERVER_NAME="$1"
ROXY_ROOT="/opt/roxy"
SERVER_SCRIPT="$ROXY_ROOT/mcp-servers/$SERVER_NAME/server.py"

# Load centralized .env file
if [ -f "$ROXY_ROOT/.env" ]; then
    set -a
    source "$ROXY_ROOT/.env"
    set +a
fi

# Set PYTHONPATH
export PYTHONPATH="$ROXY_ROOT:${PYTHONPATH:-}"

# Activate venv if it exists
if [ -f "$ROXY_ROOT/venv/bin/activate" ]; then
    source "$ROXY_ROOT/venv/bin/activate"
fi

# Run the MCP server
exec python3 "$SERVER_SCRIPT"

