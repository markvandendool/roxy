#!/bin/bash
# Security scanning script for ROXY
# Scans dependencies and containers for vulnerabilities

set -e

ROXY_DIR="/opt/roxy"
LOG_FILE="$ROXY_DIR/logs/security_scan.log"
SCAN_DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting security scan..."

# Python dependency scanning with safety
if command -v safety &> /dev/null; then
    log "Scanning Python dependencies with safety..."
    cd "$ROXY_DIR"
    if [ -f "requirements.txt" ]; then
        safety check --file requirements.txt 2>&1 | tee -a "$LOG_FILE" || true
    else
        log "requirements.txt not found, skipping safety check"
    fi
else
    log "safety not installed, skipping Python dependency scan"
    log "Install with: pip install safety"
fi

# Container scanning with Trivy
if command -v trivy &> /dev/null; then
    log "Scanning Docker containers with Trivy..."
    
    # Scan ROXY containers
    CONTAINERS=("roxy-postgres" "roxy-redis" "roxy-chromadb" "roxy-n8n")
    
    for container in "${CONTAINERS[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
            log "Scanning container: $container"
            trivy container "$container" 2>&1 | tee -a "$LOG_FILE" || true
        else
            log "Container $container not running, skipping"
        fi
    done
else
    log "trivy not installed, skipping container scan"
    log "Install with: https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
fi

# Check for exposed secrets
log "Scanning for exposed secrets..."
if command -v gitleaks &> /dev/null; then
    cd "$ROXY_DIR"
    gitleaks detect --source . --no-banner 2>&1 | tee -a "$LOG_FILE" || true
else
    log "gitleaks not installed, skipping secret scan"
    log "Install with: https://github.com/gitleaks/gitleaks"
fi

# Check file permissions
log "Checking file permissions..."
find "$ROXY_DIR" -name "*.token" -o -name "*.key" -o -name "*.pem" | while read -r file; do
    perms=$(stat -c "%a" "$file" 2>/dev/null || stat -f "%OLp" "$file" 2>/dev/null)
    if [ "$perms" != "600" ] && [ "$perms" != "400" ]; then
        log "WARNING: $file has insecure permissions: $perms"
    fi
done

log "Security scan complete. Results logged to: $LOG_FILE"






