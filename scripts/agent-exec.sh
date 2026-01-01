#!/bin/bash
# Agent Exec Helper - Execute command on JARVIS-1 with error handling
# Usage: ./agent-exec.sh "command"

set -e

HOST="${JARVIS_HOST:-jarvis-1}"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <command>"
    exit 1
fi

echo "→ Executing on JARVIS-1: $*"
ssh "$HOST" "$@" || {
    echo "❌ Command failed on JARVIS-1"
    exit 1
}

