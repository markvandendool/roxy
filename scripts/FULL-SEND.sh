#!/bin/bash
#===============================================================================
#  ███████╗██╗   ██╗██╗     ██╗         ███████╗███████╗███╗   ██╗██████╗
#  ██╔════╝██║   ██║██║     ██║         ██╔════╝██╔════╝████╗  ██║██╔══██╗
#  █████╗  ██║   ██║██║     ██║         ███████╗█████╗  ██╔██╗ ██║██║  ██║
#  ██╔══╝  ██║   ██║██║     ██║         ╚════██║██╔══╝  ██║╚██╗██║██║  ██║
#  ██║     ╚██████╔╝███████╗███████╗    ███████║███████╗██║ ╚████║██████╔╝
#  ╚═╝      ╚═════╝ ╚══════╝╚══════╝    ╚══════╝╚══════╝╚═╝  ╚═══╝╚═════╝
#
#  LUNA-000 CITADEL - ROXY OMNISCIENT CONTROL SYSTEM
#  Target: ROXY-1 (Mac Pro 2019, Ubuntu 24.04, AMD W5700X + RX 6900 XT)
#
#  Run as: sudo ./FULL-SEND.sh
#===============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/tmp/citadel-deploy-$(date +%Y%m%d-%H%M%S).log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ❌ $1${NC}" | tee -a "$LOG_FILE"
}

header() {
    echo -e "\n${PURPLE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════${NC}\n"
}

#===============================================================================
# Pre-flight checks
#===============================================================================
header "PRE-FLIGHT CHECKS"

# Check root
if [ "$EUID" -ne 0 ]; then
    error "Please run as root (sudo ./FULL-SEND.sh)"
    exit 1
fi

# Check Ubuntu
if ! grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
    warn "This script is designed for Ubuntu. Proceed with caution."
fi

# Check AMD GPU
if lspci | grep -i "AMD" | grep -i "VGA\|Display" > /dev/null 2>&1; then
    log "✅ AMD GPU detected"
    lspci | grep -i "AMD" | grep -i "VGA\|Display" | head -2
else
    warn "No AMD GPU detected. Some features may not work."
fi

# Disk space check
AVAILABLE_GB=$(df -BG / | awk 'NR==2 {print $4}' | tr -d 'G')
if [ "$AVAILABLE_GB" -lt 50 ]; then
    error "Less than 50GB available. Need more space."
    exit 1
fi
log "✅ Disk space: ${AVAILABLE_GB}GB available"

# RAM check
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
log "✅ RAM: ${TOTAL_RAM}GB"

echo ""
read -p "Ready to deploy CITADEL? This will install Docker, ROCm, Ollama, and more. [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

#===============================================================================
# Phase 1: Directory Structure
#===============================================================================
header "PHASE 1: DIRECTORY STRUCTURE"
log "Running 001-setup-directories.sh..."
chmod +x "$SCRIPT_DIR/001-setup-directories.sh"
"$SCRIPT_DIR/001-setup-directories.sh" 2>&1 | tee -a "$LOG_FILE"

#===============================================================================
# Phase 2: Dependencies
#===============================================================================
header "PHASE 2: DEPENDENCIES"
log "Running 002-install-dependencies.sh..."
chmod +x "$SCRIPT_DIR/002-install-dependencies.sh"
"$SCRIPT_DIR/002-install-dependencies.sh" 2>&1 | tee -a "$LOG_FILE"

#===============================================================================
# Phase 3: Environment Configuration
#===============================================================================
header "PHASE 3: ENVIRONMENT CONFIGURATION"

if [ ! -f /opt/roxy/.env ]; then
    log "Creating .env from template..."
    cp /opt/roxy/.env.template /opt/roxy/.env

    # Generate secure passwords
    POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)
    MINIO_ROOT_USER="roxy-admin"
    MINIO_ROOT_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)

    # Update .env
    sed -i "s/# POSTGRES_PASSWORD stored in Infisical/POSTGRES_PASSWORD=$POSTGRES_PASSWORD/" /opt/roxy/.env
    sed -i "s/# MINIO_ROOT_USER stored in Infisical/MINIO_ROOT_USER=$MINIO_ROOT_USER/" /opt/roxy/.env
    sed -i "s/# MINIO_ROOT_PASSWORD stored in Infisical/MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD/" /opt/roxy/.env

    log "✅ Generated secure credentials"
    warn "SAVE THESE CREDENTIALS:"
    echo "  POSTGRES_PASSWORD: $POSTGRES_PASSWORD"
    echo "  MINIO_ROOT_USER: $MINIO_ROOT_USER"
    echo "  MINIO_ROOT_PASSWORD: $MINIO_ROOT_PASSWORD"
else
    log ".env already exists, skipping"
fi

#===============================================================================
# Phase 4: Copy Compose Files
#===============================================================================
header "PHASE 4: COMPOSE FILES"

COMPOSE_SRC="$(dirname "$SCRIPT_DIR")/compose"
COMPOSE_DST="/opt/roxy/compose"

log "Copying compose files..."
cp -r "$COMPOSE_SRC"/* "$COMPOSE_DST/"
chown -R ${SUDO_USER:-$USER}:${SUDO_USER:-$USER} "$COMPOSE_DST"
log "✅ Compose files installed"

#===============================================================================
# Phase 5: Deploy Foundation
#===============================================================================
header "PHASE 5: FOUNDATION SERVICES"
log "Running 003-deploy-foundation.sh..."
chmod +x "$SCRIPT_DIR/003-deploy-foundation.sh"

# Run as non-root user for docker
sudo -u ${SUDO_USER:-$USER} "$SCRIPT_DIR/003-deploy-foundation.sh" 2>&1 | tee -a "$LOG_FILE"

#===============================================================================
# Phase 6: Deploy Infisical
#===============================================================================
header "PHASE 6: SECRETS MANAGER"
log "Running 004-deploy-infisical.sh..."
chmod +x "$SCRIPT_DIR/004-deploy-infisical.sh"
sudo -u ${SUDO_USER:-$USER} "$SCRIPT_DIR/004-deploy-infisical.sh" 2>&1 | tee -a "$LOG_FILE"

#===============================================================================
# Phase 7: Verify Deployment
#===============================================================================
header "PHASE 7: VERIFICATION"

log "Waiting 30 seconds for services to stabilize..."
sleep 30

log "Running health check..."
/opt/roxy/scripts/health-check.sh 2>&1 | tee -a "$LOG_FILE"

#===============================================================================
# Summary
#===============================================================================
echo ""
echo -e "${GREEN}"
cat << 'EOF'
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ██████╗██╗████████╗ █████╗ ██████╗ ███████╗██╗                             ║
║  ██╔════╝██║╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║                             ║
║  ██║     ██║   ██║   ███████║██║  ██║█████╗  ██║                             ║
║  ██║     ██║   ██║   ██╔══██║██║  ██║██╔══╝  ██║                             ║
║  ╚██████╗██║   ██║   ██║  ██║██████╔╝███████╗███████╗                        ║
║   ╚═════╝╚═╝   ╚═╝   ╚═╝  ╚═╝╚═════╝ ╚══════╝╚══════╝                        ║
║                                                                               ║
║                    FOUNDATION DEPLOYMENT COMPLETE                             ║
║                                                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  SERVICES RUNNING:                                                            ║
║  ├─ PostgreSQL .......... localhost:5432                                      ║
║  ├─ Redis ............... localhost:6379                                      ║
║  ├─ n8n ................. https://n8n.roxy.local                            ║
║  ├─ MinIO ............... https://minio.roxy.local                          ║
║  ├─ ChromaDB ............ localhost:8000                                      ║
║  ├─ NATS ................ localhost:4222                                      ║
║  ├─ Infisical ........... https://secrets.roxy.local                        ║
║  └─ Ollama .............. localhost:11434                                     ║
║                                                                               ║
║  NEXT STEPS:                                                                  ║
║  1. REBOOT (required for ROCm + group changes)                                ║
║  2. Verify: ollama run llama3:8b "Hello Roxy"                                 ║
║  3. Setup Infisical admin account                                             ║
║  4. Test: echo 'type hello' | dotool                                          ║
║  5. Continue with LUNA-S2 (Browser Automation)                                ║
║                                                                               ║
║  LOG FILE: /tmp/citadel-deploy-*.log                                          ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

log "Deployment complete. Log saved to: $LOG_FILE"
warn "REBOOT REQUIRED for ROCm and group membership changes!"
echo ""
read -p "Reboot now? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    reboot
fi
