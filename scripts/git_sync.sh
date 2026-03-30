#!/bin/bash
# ROXY Git Sync Script
# Part of ROXY-GIT-ORCHESTRATION-V1
#
# Safe sync: fetch main without destroying roxy/* branches
# Run via cron every 30 minutes

set -e

REPO_DIR="$HOME/work/mindsong_gh_https_1769765834/mindsong-juke-hub"
LOG_DIR="$HOME/.roxy/data"
LOG_FILE="$LOG_DIR/git_sync.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

log() {
    echo "[$(date -Iseconds)] $1" >> "$LOG_FILE"
}

# Check if repo exists
if [ ! -d "$REPO_DIR/.git" ]; then
    log "ERROR: Repository not found at $REPO_DIR"
    exit 1
fi

cd "$REPO_DIR" || exit 1

log "Starting sync"

# Fetch all updates from origin
if git fetch origin >> "$LOG_FILE" 2>&1; then
    log "Fetch successful"
else
    log "ERROR: Fetch failed"
    exit 1
fi

# Get current branch
current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
log "Current branch: $current_branch"

# Only reset main if we're on main AND there are no uncommitted changes
if [ "$current_branch" = "main" ]; then
    # Check for uncommitted changes
    if git diff-index --quiet HEAD -- 2>/dev/null; then
        git reset --hard origin/main >> "$LOG_FILE" 2>&1
        log "Reset main to origin/main"
    else
        log "WARN: Uncommitted changes on main, skipping reset"
    fi
else
    log "On branch $current_branch, skipping main reset"
fi

# Prune deleted remote branches
git remote prune origin >> "$LOG_FILE" 2>&1
log "Pruned stale remote tracking branches"

# Clean up old merged roxy/* branches (local only)
# Only delete branches that have been merged to origin/main
merged_branches=$(git branch --merged origin/main 2>/dev/null | grep 'roxy/' | tr -d ' ' || true)
if [ -n "$merged_branches" ]; then
    for branch in $merged_branches; do
        git branch -d "$branch" >> "$LOG_FILE" 2>&1 || true
        log "Deleted merged branch: $branch"
    done
fi

log "Sync complete"
