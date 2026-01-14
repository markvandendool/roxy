#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Token rotation script for ROXY
# Generates new secure token and restarts service

set -e

ROXY_DIR="/home/mark/.roxy"
TOKEN_FILE="$ROXY_DIR/secret.token"
BACKUP_DIR="$ROXY_DIR/backups"
LOG_FILE="$ROXY_DIR/logs/token_rotation.log"

# Create directories if needed
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting token rotation..."

# Backup current token
if [ -f "$TOKEN_FILE" ]; then
    BACKUP_FILE="$BACKUP_DIR/secret_token_backup_$(date +%Y%m%d_%H%M%S)"
    cp "$TOKEN_FILE" "$BACKUP_FILE"
    log "Backed up current token to: $BACKUP_FILE"
fi

# Generate new token
NEW_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
log "Generated new token"

# Write new token
echo "$NEW_TOKEN" > "$TOKEN_FILE"
chmod 600 "$TOKEN_FILE"
log "New token written to: $TOKEN_FILE"

# Restart ROXY core service
if systemctl --user is-active --quiet roxy-core 2>/dev/null; then
    log "Restarting ROXY core service..."
    systemctl --user restart roxy-core
    sleep 2
    
    if systemctl --user is-active --quiet roxy-core 2>/dev/null; then
        log "✓ ROXY core service restarted successfully"
    else
        log "✗ ROXY core service failed to start"
        log "Restoring previous token..."
        if [ -f "$BACKUP_FILE" ]; then
            cp "$BACKUP_FILE" "$TOKEN_FILE"
            chmod 600 "$TOKEN_FILE"
            systemctl --user restart roxy-core
        fi
        exit 1
    fi
else
    log "ROXY core service not running, skipping restart"
fi

log "Token rotation complete"
log "New token: $NEW_TOKEN"
log "IMPORTANT: Update all clients with the new token!"





