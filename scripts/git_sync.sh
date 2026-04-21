#!/bin/bash
# ROXY Git Sync Script
# Safe sync: fetch main without destroying roxy/* branches

set -e

REPO_DIR="$HOME/mindsong-juke-hub"
LOG_FILE="$HOME/.roxy/data/git_sync.log"

cd "$REPO_DIR" || exit 1

git fetch origin 2>> "$LOG_FILE"
git reset --hard origin/main 2>> "$LOG_FILE"
git remote prune origin 2>> "$LOG_FILE"

echo "[$(date -Iseconds)] Sync complete" >> "$LOG_FILE"
