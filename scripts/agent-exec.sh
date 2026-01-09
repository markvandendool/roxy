#!/bin/bash
# Agent Exec Helper - Execute command on ROXY-1 with error handling
# Usage: ./agent-exec.sh "command"

set -e

HOST="${ROXY_HOST:-roxy-1}"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <command>"
    exit 1
fi

echo "→ Executing on ROXY-1: $*"
ssh "$HOST" "$@" || {
    echo "❌ Command failed on ROXY-1"
    exit 1
}

