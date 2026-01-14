#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Agent SSH Helper - Seamless ROXY-1 Access
# Usage: ./agent-ssh.sh "command" or ./agent-ssh.sh (interactive)

set -e

HOST="${ROXY_HOST:-roxy-1}"
SSH_KEY="${ROXY_SSH_KEY:-~/.ssh/id_ed25519}"

if [ $# -eq 0 ]; then
    # Interactive mode
    exec ssh "$HOST"
else
    # Command mode
    ssh "$HOST" "$@"
fi
