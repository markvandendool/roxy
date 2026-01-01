#!/bin/bash
# Agent SSH Helper - Seamless JARVIS-1 Access
# Usage: ./agent-ssh.sh "command" or ./agent-ssh.sh (interactive)

set -e

HOST="${JARVIS_HOST:-jarvis-1}"
SSH_KEY="${JARVIS_SSH_KEY:-~/.ssh/id_ed25519}"

if [ $# -eq 0 ]; then
    # Interactive mode
    exec ssh "$HOST"
else
    # Command mode
    ssh "$HOST" "$@"
fi

