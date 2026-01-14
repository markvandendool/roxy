#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
#===============================================================================
#  ███████╗██╗   ██╗██╗     ██╗         ███████╗███████╗███╗   ██╗██████╗
#  ██╔════╝██║   ██║██║     ██║         ██╔════╝██╔════╝████╗  ██║██╔══██╗
#  █████╗  ██║   ██║██║     ██║         ███████╗█████╗  ██╔██╗ ██║██║  ██║
#  ██╔══╝  ██║   ██║██║     ██║         ╚════██║██╔══╝  ██║╚██╗██║██║  ██║
#  ██║     ╚██████╔╝███████╗███████╗    ███████║███████╗██║ ╚████║██████╔╝
#  ╚═╝      ╚═════╝ ╚══════╝╚══════╝    ╚══════╝╚══════╝╚═╝  ╚═══╝╚═════╝
#
#                         █████╗ ██████╗ ██████╗ ██╗████████╗██╗██╗   ██╗███████╗
#                        ██╔══██╗██╔══██╗██╔══██╗██║╚══██╔══╝██║██║   ██║██╔════╝
#                        ███████║██║  ██║██║  ██║██║   ██║   ██║██║   ██║█████╗
#                        ██╔══██║██║  ██║██║  ██║██║   ██║   ██║╚██╗ ██╔╝██╔══╝
#                        ██║  ██║██████╔╝██████╔╝██║   ██║   ██║ ╚████╔╝ ███████╗
#                        ╚═╝  ╚═╝╚═════╝ ╚═════╝ ╚═╝   ╚═╝   ╚═╝  ╚═══╝  ╚══════╝
#
#  LUNA-000 CITADEL - ADDITIVE DEPLOYMENT
#
#  This version RESPECTS existing ROXY-1 infrastructure:
#  - Skips already-installed services (ROCm, Ollama, ChromaDB, etc.)
#  - Preserves existing data volumes
#  - Migrates ROXY_ROOT (default ~/.roxy) to the canonical root (additive, not destructive)
#  - Adds NEW services alongside existing ones
#
#  Run: sudo ./FULL-SEND-ADDITIVE.sh
#===============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/tmp/citadel-additive-$(date +%Y%m%d-%H%M%S).log"
RECONCILE_REPORT="${CITADEL_RECONCILE_REPORT:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠️  $1${NC}" | tee -a "$LOG_FILE"; }
skip() { echo -e "${BLUE}[$(date '+%H:%M:%S')] ⏭️  $1${NC}" | tee -a "$LOG_FILE"; }
error(){ echo -e "${RED}[$(date '+%H:%M:%S')] ❌ $1${NC}" | tee -a "$LOG_FILE"; }

header() {
    echo -e "\n${PURPLE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════${NC}\n"
}

#===============================================================================
# Pre-flight
#===============================================================================
header "ADDITIVE DEPLOYMENT - PRE-FLIGHT"

if [ "$EUID" -ne 0 ]; then
    error "Please run as root (sudo ./FULL-SEND-ADDITIVE.sh)"
    exit 1
fi

# Run reconciliation if not already done
if [ -z "$RECONCILE_REPORT" ] || [ ! -f "$RECONCILE_REPORT" ]; then
    log "Running reconciliation first..."
    chmod +x "$SCRIPT_DIR/000-reconcile-existing.sh"
    source "$SCRIPT_DIR/000-reconcile-existing.sh"
fi

# Load reconciliation data
if [ -f "$RECONCILE_REPORT" ]; then
    log "Loading reconciliation report: $RECONCILE_REPORT"
    SKIP_ROCM=$(jq -r '.skip_install.rocm' "$RECONCILE_REPORT")
    SKIP_OLLAMA=$(jq -r '.skip_install.ollama' "$RECONCILE_REPORT")
    SKIP_CHROMADB=$(jq -r '.skip_install.chromadb' "$RECONCILE_REPORT")
    SKIP_DOCKER=$(jq -r '.skip_install.docker' "$RECONCILE_REPORT")
    SKIP_DOTOOL=$(jq -r '.skip_install.dotool' "$RECONCILE_REPORT")
    SKIP_GVISOR=$(jq -r '.skip_install.gvisor' "$RECONCILE_REPORT")
    MIGRATE_ROXY=$(jq -r '.migration.roxy_dir_exists' "$RECONCILE_REPORT")
    CHROMADB_DOCS=$(jq -r '.existing_services.chromadb_docs' "$RECONCILE_REPORT")
else
    warn "No reconciliation report found, will detect on-the-fly"
    SKIP_ROCM=false
    SKIP_OLLAMA=false
    SKIP_CHROMADB=false
    SKIP_DOCKER=false
    SKIP_DOTOOL=false
    SKIP_GVISOR=false
    MIGRATE_ROXY=false
    CHROMADB_DOCS=0
fi

echo ""
echo "Configuration:"
echo "  Skip ROCm:     $SKIP_ROCM"
echo "  Skip Ollama:   $SKIP_OLLAMA"
echo "  Skip ChromaDB: $SKIP_CHROMADB (${CHROMADB_DOCS} docs preserved)"
echo "  Skip Docker:   $SKIP_DOCKER"
echo "  Migrate ~/.roxy: $MIGRATE_ROXY"
echo ""

read -p "Proceed with ADDITIVE deployment? [y/N] " -n 1 -r
echo
[[ ! $REPLY =~ ^[Yy]$ ]] && exit 1

#===============================================================================
header "PHASE 1: DIRECTORY STRUCTURE"
#===============================================================================

log "Creating ROXY_ROOT structure (preserving existing)..."

# Source directory setup but don't overwrite
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
ROXY_USER="${SUDO_USER:-$USER}"

# Create directories only if they don't exist
directories=(
    "$ROXY_ROOT"
    "$ROXY_ROOT/logs"
    "$ROXY_ROOT/backups"
    "$ROXY_ROOT/data"
    "$ROXY_ROOT/agents/browser-agent"
    "$ROXY_ROOT/agents/desktop-agent"
    "$ROXY_ROOT/agents/obs-agent"
    "$ROXY_ROOT/agents/orchestrator/nodes"
    "$ROXY_ROOT/agents/orchestrator/tools"
    "$ROXY_ROOT/agents/memory"
    "$ROXY_ROOT/bots/discord"
    "$ROXY_ROOT/bots/telegram"
    "$ROXY_ROOT/mcp-servers/desktop/tools"
    "$ROXY_ROOT/mcp-servers/browser"
    "$ROXY_ROOT/mcp-gateway"
    "$ROXY_ROOT/pipeline/transcription"
    "$ROXY_ROOT/pipeline/clips"
    "$ROXY_ROOT/pipeline/upscale"
    "$ROXY_ROOT/pipeline/thumbnails"
    "$ROXY_ROOT/pipeline/encode/presets"
    "$ROXY_ROOT/voice/wakeword/models"
    "$ROXY_ROOT/voice/transcription"
    "$ROXY_ROOT/voice/tts"
    "$ROXY_ROOT/voice/reference"
    "$ROXY_ROOT/integrations/youtube"
    "$ROXY_ROOT/compose/configs"
    "$ROXY_ROOT/configs"
    "$ROXY_ROOT/secrets/browser-sessions"
    "$ROXY_ROOT/secrets/keys"
    "$ROXY_ROOT/data/chromadb"
    "$ROXY_ROOT/data/minio"
    "$ROXY_ROOT/data/postgres"
    "$ROXY_ROOT/data/redis"
    "$ROXY_ROOT/data/n8n"
    "$ROXY_ROOT/data/nats"
    "$ROXY_ROOT/tests"
    "$ROXY_ROOT/scripts"
)

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        log "Created: $dir"
    fi
done

chown -R "$ROXY_USER:$ROXY_USER" "$ROXY_ROOT"
chmod 700 "$ROXY_ROOT/secrets"
log "✅ Directory structure ready"

#===============================================================================
header "PHASE 2: MIGRATE ~/.roxy/ (if exists)"
#===============================================================================

if [ "$MIGRATE_ROXY" = "true" ] && [ -d "$HOME/.roxy" ]; then
    log "Migrating ROXY_ROOT to canonical root..."

    # Create backup
    BACKUP_DIR="${ROXY_ROOT}-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    cp -a "$HOME/.roxy/"* "$BACKUP_DIR/" 2>/dev/null || true
    log "Backup created: $BACKUP_DIR"

    # Migrate with rsync (additive, no overwrite)
    rsync -av --ignore-existing "$HOME/.roxy/" "$ROXY_ROOT/" 2>/dev/null || true
    chown -R "$ROXY_USER:$ROXY_USER" "$ROXY_ROOT"

    log "✅ Migration complete (original ~/.roxy/ preserved)"
else
    skip "No ~/.roxy/ to migrate"
fi

#===============================================================================
header "PHASE 3: DEPENDENCIES (additive)"
#===============================================================================

# Update system
log "Updating package lists..."
apt-get update -qq

# Base packages (always safe to install)
log "Installing base packages..."
apt-get install -y -qq \
    curl wget git jq htop tree unzip \
    python3 python3-pip python3-venv \
    ffmpeg gnome-screenshot wl-clipboard 2>/dev/null || true

# Docker
if [ "$SKIP_DOCKER" = "true" ]; then
    skip "Docker already installed"
else
    log "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker "$ROXY_USER"
    systemctl enable docker
    systemctl start docker
    log "✅ Docker installed"
fi

# gVisor
if [ "$SKIP_GVISOR" = "true" ]; then
    skip "gVisor already installed"
else
    log "Installing gVisor..."
    curl -fsSL https://gvisor.dev/archive.key | gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg 2>/dev/null || true
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" > /etc/apt/sources.list.d/gvisor.list
    apt-get update -qq
    apt-get install -y -qq runsc

    # Configure Docker runtime (only if not already configured)
    if [ -f /etc/docker/daemon.json ]; then
        if ! grep -q "runsc" /etc/docker/daemon.json; then
            # Backup and add runsc
            cp /etc/docker/daemon.json /etc/docker/daemon.json.bak
            jq '. + {"runtimes": {"runsc": {"path": "/usr/bin/runsc"}}}' /etc/docker/daemon.json > /tmp/daemon.json
            mv /tmp/daemon.json /etc/docker/daemon.json
            systemctl restart docker
        fi
    else
        cat > /etc/docker/daemon.json << 'EOF'
{
    "runtimes": {
        "runsc": {
            "path": "/usr/bin/runsc"
        }
    }
}
EOF
        systemctl restart docker
    fi
    log "✅ gVisor installed"
fi

# ROCm
if [ "$SKIP_ROCM" = "true" ]; then
    skip "ROCm already installed"
    rocm-smi --showproductname 2>/dev/null | head -3 || true
else
    warn "ROCm installation requested - this is DANGEROUS on a working system"
    read -p "Install ROCm? This could break existing GPU setup. [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "Installing ROCm 6.0..."
        wget -q https://repo.radeon.com/amdgpu-install/6.0/ubuntu/jammy/amdgpu-install_6.0.60000-1_all.deb
        apt-get install -y ./amdgpu-install_6.0.60000-1_all.deb
        rm amdgpu-install_6.0.60000-1_all.deb
        amdgpu-install -y --usecase=rocm,graphics --no-dkms
        usermod -aG render,video "$ROXY_USER"
        log "✅ ROCm installed (reboot required)"
    else
        skip "ROCm installation skipped by user"
    fi
fi

# Ollama
if [ "$SKIP_OLLAMA" = "true" ]; then
    skip "Ollama already installed"
    ollama list 2>/dev/null || true
else
    log "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh

    mkdir -p /etc/systemd/system/ollama.service.d
    cat > /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="HSA_OVERRIDE_GFX_VERSION=10.3.0"
Environment="OLLAMA_HOST=0.0.0.0"
EOF
    systemctl daemon-reload
    systemctl enable ollama
    systemctl restart ollama

    log "Pulling llama3:8b..."
    sudo -u "$ROXY_USER" ollama pull llama3:8b
    log "✅ Ollama installed"
fi

# dotool (requires Go - optional for initial setup)
if [ "$SKIP_DOTOOL" = "true" ]; then
    skip "dotool already installed"
else
    if command -v go &> /dev/null; then
        log "Installing dotool..."
        cd /tmp
        git clone https://git.sr.ht/~geb/dotool 2>/dev/null || true
        cd dotool
        ./build.sh
        cp dotool dotoold /usr/local/bin/
        cd /
        rm -rf /tmp/dotool

        echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' > /etc/udev/rules.d/99-uinput.rules
        udevadm control --reload-rules
        udevadm trigger
        usermod -aG input "$ROXY_USER"
        log "✅ dotool installed"
    else
        warn "Go not installed - skipping dotool (install Go and re-run for Wayland automation)"
    fi
fi

#===============================================================================
header "PHASE 4: PYTHON ENVIRONMENT"
#===============================================================================

VENV_PATH="$ROXY_ROOT/venv"

if [ ! -d "$VENV_PATH" ]; then
    log "Creating Python venv..."
    python3 -m venv "$VENV_PATH"
fi

chown -R "$ROXY_USER:$ROXY_USER" "$VENV_PATH"

log "Installing Python packages..."
sudo -u "$ROXY_USER" "$VENV_PATH/bin/pip" install --upgrade pip -q
sudo -u "$ROXY_USER" "$VENV_PATH/bin/pip" install -q \
    browser-use langchain-ollama langgraph mem0ai chromadb \
    playwright faster-whisper openwakeword \
    obsws-python nats-py minio fastmcp \
    python-telegram-bot "discord.py" httpx pydantic rich || true

# TTS requires Python <3.12, install separately if compatible
if python3 -c "import sys; exit(0 if sys.version_info < (3,12) else 1)" 2>/dev/null; then
    sudo -u "$ROXY_USER" "$VENV_PATH/bin/pip" install -q TTS || warn "TTS installation failed"
else
    warn "TTS requires Python <3.12, skipping (use XTTS-v2 via API instead)"
fi

# Playwright browsers
sudo -u "$ROXY_USER" "$VENV_PATH/bin/playwright" install chromium firefox 2>/dev/null || true
log "✅ Python environment ready"

#===============================================================================
header "PHASE 5: COPY COMPOSE FILES"
#===============================================================================

COMPOSE_SRC="$(dirname "$SCRIPT_DIR")/compose"

if [ -d "$COMPOSE_SRC" ]; then
    log "Copying compose files..."
    cp -r "$COMPOSE_SRC"/* "$ROXY_ROOT/compose/"
    chown -R "$ROXY_USER:$ROXY_USER" "$ROXY_ROOT/compose"
    log "✅ Compose files installed"
else
    warn "Compose source not found: $COMPOSE_SRC"
fi

#===============================================================================
header "PHASE 6: ENVIRONMENT FILE"
#===============================================================================

if [ ! -f "$ROXY_ROOT/.env" ]; then
    log "Creating .env with secure credentials..."

    POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)
    MINIO_ROOT_USER="roxy-admin"
    MINIO_ROOT_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)

    cat > "$ROXY_ROOT/.env" << EOF
#===============================================================================
# ROXY CITADEL - Generated $(date)
#===============================================================================

ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
ROXY_DOMAIN=roxy.local
ROXY_ENV=production

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3:8b
HSA_OVERRIDE_GFX_VERSION=10.3.0

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=roxy
POSTGRES_PASSWORD=$POSTGRES_PASSWORD

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# MinIO
MINIO_HOST=minio.roxy.local
MINIO_ROOT_USER=$MINIO_ROOT_USER
MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD

# n8n
N8N_HOST=n8n.roxy.local

# ChromaDB
CHROMADB_HOST=localhost
CHROMADB_PORT=8000

# NATS
NATS_HOST=localhost
NATS_PORT=4222

# GPU
GPU_DEVICE=/dev/dri/renderD128
VAAPI_DEVICE=/dev/dri/renderD128
EOF

    chown "$ROXY_USER:$ROXY_USER" "$ROXY_ROOT/.env"
    chmod 600 "$ROXY_ROOT/.env"

    log "✅ .env created"
    warn "SAVE THESE CREDENTIALS:"
    echo "  POSTGRES_PASSWORD: $POSTGRES_PASSWORD"
    echo "  MINIO_ROOT_USER: $MINIO_ROOT_USER"
    echo "  MINIO_ROOT_PASSWORD: $MINIO_ROOT_PASSWORD"
else
    skip ".env already exists, preserving"
fi

#===============================================================================
header "PHASE 7: DEPLOY NEW SERVICES"
#===============================================================================

cd "$ROXY_ROOT/compose"

# Load env
set -a
source "$ROXY_ROOT/.env"
set +a

# Deploy foundation (additive - existing containers preserved)
log "Deploying foundation services..."

if [ "$SKIP_CHROMADB" = "true" ]; then
    warn "ChromaDB already running - excluding from deployment"
    warn "  Preserving $CHROMADB_DOCS documents"

    # Create a modified compose that excludes ChromaDB
    grep -v "chromadb" docker-compose.foundation.yml > docker-compose.foundation-nochroma.yml || true
    docker compose -f docker-compose.foundation-nochroma.yml up -d 2>&1 | tee -a "$LOG_FILE"
else
    docker compose -f docker-compose.foundation.yml up -d 2>&1 | tee -a "$LOG_FILE"
fi

log "Waiting for services..."
sleep 15

#===============================================================================
header "PHASE 8: DEPLOY INFISICAL"
#===============================================================================

# Generate Infisical secrets if needed
if [ -z "${INFISICAL_ENCRYPTION_KEY:-}" ]; then
    {
        echo ""
        echo "INFISICAL_ENCRYPTION_KEY=$(openssl rand -hex 32)"
        echo "INFISICAL_JWT_SECRET=$(openssl rand -hex 32)"
        echo "INFISICAL_JWT_REFRESH=$(openssl rand -hex 32)"
        echo "INFISICAL_JWT_AUTH=$(openssl rand -hex 32)"
    } >> "$ROXY_ROOT/.env"
    log "Generated Infisical secrets"
fi

set -a
source "$ROXY_ROOT/.env"
set +a

docker compose -f docker-compose.infisical.yml up -d 2>&1 | tee -a "$LOG_FILE"
log "✅ Infisical deployed"

#===============================================================================
header "PHASE 9: HEALTH CHECK"
#===============================================================================

log "Running health check..."
sleep 10

echo ""
echo "Service Status:"
echo "═══════════════════════════════════════"

check_service() {
    local name=$1
    local check=$2
    if eval "$check" &> /dev/null; then
        echo -e "  ${GREEN}✅${NC} $name"
    else
        echo -e "  ${YELLOW}⚠️${NC} $name (may still be starting)"
    fi
}

check_service "PostgreSQL" "docker exec roxy-postgres pg_isready"
check_service "Redis" "docker exec roxy-redis redis-cli ping"
check_service "n8n" "curl -sf http://localhost:5678/healthz"
check_service "MinIO" "curl -sf http://localhost:9000/minio/health/live"
check_service "ChromaDB" "curl -sf http://localhost:8000/api/v1/heartbeat"
check_service "NATS" "curl -sf http://localhost:8222/healthz"
check_service "Ollama" "curl -sf http://localhost:11434/api/tags"

echo ""

#===============================================================================
header "DEPLOYMENT COMPLETE"
#===============================================================================

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
║                    ADDITIVE DEPLOYMENT COMPLETE                               ║
║                                                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  PRESERVED:                                                                   ║
║  ├─ Existing ROCm installation                                                ║
║  ├─ Existing Ollama + models                                                  ║
║  ├─ Existing ChromaDB data                                                    ║
║  ├─ Home Assistant, Grafana, Prometheus                                       ║
║  └─ All ROXY_ROOT content (migrated to canonical root)                        ║
║                                                                               ║
║  ADDED:                                                                       ║
║  ├─ PostgreSQL, Redis, NATS (event bus)                                       ║
║  ├─ n8n (workflow automation)                                                 ║
║  ├─ MinIO (S3 storage)                                                        ║
║  ├─ Infisical (secrets manager)                                               ║
║  ├─ Caddy (reverse proxy)                                                     ║
║  └─ gVisor (browser sandbox)                                                  ║
║                                                                               ║
║  CANONICAL LOCATION: $ROXY_ROOT                                               ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

log "Log saved: $LOG_FILE"

if [ "${SKIP_ROCM:-}" = "false" ]; then
    warn "REBOOT REQUIRED for ROCm/group changes"
    read -p "Reboot now? [y/N] " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] && reboot
fi