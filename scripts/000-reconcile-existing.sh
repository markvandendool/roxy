#!/bin/bash
#===============================================================================
#  ██████╗ ███████╗ ██████╗ ██████╗ ███╗   ██╗ ██████╗██╗██╗     ███████╗
#  ██╔══██╗██╔════╝██╔════╝██╔═══██╗████╗  ██║██╔════╝██║██║     ██╔════╝
#  ██████╔╝█████╗  ██║     ██║   ██║██╔██╗ ██║██║     ██║██║     █████╗
#  ██╔══██╗██╔══╝  ██║     ██║   ██║██║╚██╗██║██║     ██║██║     ██╔══╝
#  ██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║╚██████╗██║███████╗███████╗
#  ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝╚═╝╚══════╝╚══════╝
#
#  LUNA-000 CITADEL - Pre-Deployment Reconciliation
#
#  PURPOSE: Detect existing ROXY-1 infrastructure and prepare for
#           ADDITIVE deployment without destroying working systems.
#
#  Run BEFORE FULL-SEND.sh
#===============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECONCILE_REPORT="/tmp/citadel-reconcile-$(date +%Y%m%d-%H%M%S).json"
OLD_ROXY_DIR="$HOME/.roxy"
NEW_ROXY_DIR="/opt/roxy"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[⚠]${NC} $1"; }
skip() { echo -e "${BLUE}[→]${NC} $1 (will skip install)"; }
need() { echo -e "${CYAN}[+]${NC} $1 (will install)"; }

echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║  CITADEL PRE-DEPLOYMENT RECONCILIATION                                    ║"
echo "║  Detecting existing ROXY-1 infrastructure...                            ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Initialize reconciliation state
declare -A EXISTING_SERVICES
declare -A SKIP_INSTALL
declare -A MIGRATION_NEEDED

#===============================================================================
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  PHASE 1: SERVICE DETECTION"
echo "═══════════════════════════════════════════════════════════════════════════"
#===============================================================================

# Docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
    skip "Docker $DOCKER_VERSION"
    SKIP_INSTALL[docker]=true
else
    need "Docker"
    SKIP_INSTALL[docker]=false
fi

# ROCm
if command -v rocm-smi &> /dev/null; then
    ROCM_VERSION=$(rocm-smi --version 2>/dev/null | head -1 || echo "installed")
    skip "ROCm: $ROCM_VERSION"
    SKIP_INSTALL[rocm]=true

    # Check GPU visibility
    if rocm-smi --showproductname &> /dev/null; then
        GPU_INFO=$(rocm-smi --showproductname 2>/dev/null | grep -i "card" | head -2)
        log "GPUs detected:"
        echo "$GPU_INFO" | sed 's/^/       /'
    fi
else
    need "ROCm"
    SKIP_INSTALL[rocm]=false
fi

# Ollama
if command -v ollama &> /dev/null; then
    skip "Ollama"
    SKIP_INSTALL[ollama]=true

    # Check running models
    if curl -sf http://localhost:11434/api/tags &> /dev/null; then
        MODELS=$(curl -sf http://localhost:11434/api/tags | jq -r '.models[].name' 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
        log "Models loaded: $MODELS"
        EXISTING_SERVICES[ollama_models]="$MODELS"
    fi
else
    need "Ollama + llama3:8b"
    SKIP_INSTALL[ollama]=false
fi

# ChromaDB
if curl -sf http://localhost:8000/api/v1/heartbeat &> /dev/null; then
    skip "ChromaDB (running)"
    SKIP_INSTALL[chromadb]=true

    # Check collections
    COLLECTIONS=$(curl -sf http://localhost:8000/api/v1/collections 2>/dev/null | jq -r '.[].name' 2>/dev/null | wc -l)
    TOTAL_DOCS=$(curl -sf http://localhost:8000/api/v1/collections 2>/dev/null | jq '[.[].count // 0] | add' 2>/dev/null || echo "unknown")
    log "ChromaDB: $COLLECTIONS collections, ~$TOTAL_DOCS documents"
    EXISTING_SERVICES[chromadb_docs]="$TOTAL_DOCS"

    warn "CRITICAL: Existing ChromaDB data will be PRESERVED"
else
    need "ChromaDB"
    SKIP_INSTALL[chromadb]=false
fi

# PostgreSQL
if command -v psql &> /dev/null || docker ps 2>/dev/null | grep -q postgres; then
    skip "PostgreSQL"
    SKIP_INSTALL[postgres]=true
else
    need "PostgreSQL"
    SKIP_INSTALL[postgres]=false
fi

# Redis
if command -v redis-cli &> /dev/null || docker ps 2>/dev/null | grep -q redis; then
    if redis-cli ping &> /dev/null 2>&1; then
        skip "Redis (running)"
        SKIP_INSTALL[redis]=true
    else
        need "Redis"
        SKIP_INSTALL[redis]=false
    fi
else
    need "Redis"
    SKIP_INSTALL[redis]=false
fi

# Home Assistant
if curl -sf http://localhost:8123 &> /dev/null; then
    skip "Home Assistant (:8123)"
    EXISTING_SERVICES[homeassistant]="running"
    log "Home Assistant will NOT be touched"
fi

# Grafana
if curl -sf http://localhost:3000 &> /dev/null; then
    skip "Grafana (:3000)"
    EXISTING_SERVICES[grafana]="running"
fi

# Prometheus
if curl -sf http://localhost:9090 &> /dev/null; then
    skip "Prometheus (:9090)"
    EXISTING_SERVICES[prometheus]="running"
fi

# dotool
if command -v dotool &> /dev/null; then
    skip "dotool"
    SKIP_INSTALL[dotool]=true
else
    need "dotool"
    SKIP_INSTALL[dotool]=false
fi

# gVisor
if command -v runsc &> /dev/null; then
    skip "gVisor (runsc)"
    SKIP_INSTALL[gvisor]=true
else
    need "gVisor"
    SKIP_INSTALL[gvisor]=false
fi

#===============================================================================
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  PHASE 2: DIRECTORY STRUCTURE ANALYSIS"
echo "═══════════════════════════════════════════════════════════════════════════"
#===============================================================================

# Check existing ~/.roxy
if [ -d "$OLD_ROXY_DIR" ]; then
    warn "Existing ~/.roxy/ detected"

    # Count files
    FILE_COUNT=$(find "$OLD_ROXY_DIR" -type f 2>/dev/null | wc -l)
    DIR_SIZE=$(du -sh "$OLD_ROXY_DIR" 2>/dev/null | cut -f1)
    log "  Files: $FILE_COUNT, Size: $DIR_SIZE"

    # Critical files to preserve
    echo ""
    echo "  Critical files detected:"

    CRITICAL_FILES=(
        "roxy_assistant_v2.py"
        "obs_skill.py"
        "clip_extractor.py"
        "voice/reference/*.wav"
        "chromadb/*"
        "models/*"
        "config/*.json"
        "cron/*"
    )

    for pattern in "${CRITICAL_FILES[@]}"; do
        FOUND=$(find "$OLD_ROXY_DIR" -path "*$pattern" 2>/dev/null | head -3)
        if [ -n "$FOUND" ]; then
            echo "    ✓ $pattern"
            while IFS= read -r file; do
                SIZE=$(du -h "$file" 2>/dev/null | cut -f1)
                echo "      → $file ($SIZE)"
            done <<< "$FOUND"
        fi
    done

    MIGRATION_NEEDED[roxy_dir]=true
else
    log "No existing ~/.roxy/ directory"
    MIGRATION_NEEDED[roxy_dir]=false
fi

# Check if /opt/roxy exists
if [ -d "$NEW_ROXY_DIR" ]; then
    warn "Existing /opt/roxy/ detected"
    NEW_FILE_COUNT=$(find "$NEW_ROXY_DIR" -type f 2>/dev/null | wc -l)
    NEW_DIR_SIZE=$(du -sh "$NEW_ROXY_DIR" 2>/dev/null | cut -f1)
    log "  Files: $NEW_FILE_COUNT, Size: $NEW_DIR_SIZE"
fi

#===============================================================================
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  PHASE 3: DOCKER CONTAINER AUDIT"
echo "═══════════════════════════════════════════════════════════════════════════"
#===============================================================================

if command -v docker &> /dev/null; then
    RUNNING_CONTAINERS=$(docker ps --format "{{.Names}}" 2>/dev/null | tr '\n' ' ')
    if [ -n "$RUNNING_CONTAINERS" ]; then
        log "Running containers: $RUNNING_CONTAINERS"

        # Check for naming conflicts
        CITADEL_NAMES=("roxy-postgres" "roxy-redis" "roxy-n8n" "roxy-minio" "roxy-chromadb" "roxy-nats" "roxy-caddy" "roxy-infisical")

        for name in "${CITADEL_NAMES[@]}"; do
            if echo "$RUNNING_CONTAINERS" | grep -q "$name"; then
                warn "Container $name already exists - will need --force-recreate"
            fi
        done
    fi

    # Check existing volumes
    EXISTING_VOLUMES=$(docker volume ls --format "{{.Name}}" 2>/dev/null | grep -E "roxy|chromadb|postgres|redis|minio" | tr '\n' ' ' || true)
    if [ -n "$EXISTING_VOLUMES" ]; then
        warn "Existing volumes with data: $EXISTING_VOLUMES"
        log "  These will be PRESERVED (not recreated)"
    fi
fi

#===============================================================================
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  PHASE 4: PORT CONFLICT CHECK"
echo "═══════════════════════════════════════════════════════════════════════════"
#===============================================================================

check_port() {
    local port=$1
    local service=$2
    if ss -tuln 2>/dev/null | grep -q ":$port "; then
        CURRENT=$(ss -tuln 2>/dev/null | grep ":$port " | head -1)
        warn "Port $port ($service) IN USE: $CURRENT"
        return 1
    else
        log "Port $port ($service) available"
        return 0
    fi
}

PORTS_OK=true
check_port 5432 "PostgreSQL" || PORTS_OK=false
check_port 6379 "Redis" || PORTS_OK=false
check_port 5678 "n8n" || PORTS_OK=false
check_port 9000 "MinIO API" || PORTS_OK=false
check_port 9001 "MinIO Console" || PORTS_OK=false
check_port 8000 "ChromaDB" || PORTS_OK=false
check_port 4222 "NATS" || PORTS_OK=false
check_port 8222 "NATS Monitor" || PORTS_OK=false
check_port 80 "Caddy HTTP" || PORTS_OK=false
check_port 443 "Caddy HTTPS" || PORTS_OK=false
check_port 8080 "Infisical" || PORTS_OK=false

#===============================================================================
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  PHASE 5: GENERATE RECONCILIATION PLAN"
echo "═══════════════════════════════════════════════════════════════════════════"
#===============================================================================

# Generate JSON report
cat > "$RECONCILE_REPORT" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "hostname": "$(hostname)",
  "skip_install": {
    "docker": ${SKIP_INSTALL[docker]:-false},
    "rocm": ${SKIP_INSTALL[rocm]:-false},
    "ollama": ${SKIP_INSTALL[ollama]:-false},
    "chromadb": ${SKIP_INSTALL[chromadb]:-false},
    "postgres": ${SKIP_INSTALL[postgres]:-false},
    "redis": ${SKIP_INSTALL[redis]:-false},
    "dotool": ${SKIP_INSTALL[dotool]:-false},
    "gvisor": ${SKIP_INSTALL[gvisor]:-false}
  },
  "existing_services": {
    "ollama_models": "${EXISTING_SERVICES[ollama_models]:-}",
    "chromadb_docs": "${EXISTING_SERVICES[chromadb_docs]:-0}",
    "homeassistant": "${EXISTING_SERVICES[homeassistant]:-not_running}",
    "grafana": "${EXISTING_SERVICES[grafana]:-not_running}",
    "prometheus": "${EXISTING_SERVICES[prometheus]:-not_running}"
  },
  "migration": {
    "roxy_dir_exists": ${MIGRATION_NEEDED[roxy_dir]:-false},
    "old_path": "$OLD_ROXY_DIR",
    "new_path": "$NEW_ROXY_DIR"
  },
  "ports_clear": $PORTS_OK
}
EOF

log "Reconciliation report saved: $RECONCILE_REPORT"

#===============================================================================
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  PHASE 6: MIGRATION SCRIPT GENERATION"
echo "═══════════════════════════════════════════════════════════════════════════"
#===============================================================================

MIGRATION_SCRIPT="$SCRIPT_DIR/000a-migrate-roxy-dir.sh"

cat > "$MIGRATION_SCRIPT" << 'MIGRATE_EOF'
#!/bin/bash
#===============================================================================
# Migrate ~/.roxy/ to /opt/roxy/
# Generated by 000-reconcile-existing.sh
#===============================================================================

set -euo pipefail

OLD_ROXY="$HOME/.roxy"
NEW_ROXY="/opt/roxy"
BACKUP_DIR="/opt/roxy-backup-$(date +%Y%m%d-%H%M%S)"

if [ ! -d "$OLD_ROXY" ]; then
    echo "No ~/.roxy/ to migrate"
    exit 0
fi

echo "Migrating ~/.roxy/ to /opt/roxy/..."

# Create backup
echo "[1/4] Backing up to $BACKUP_DIR..."
sudo mkdir -p "$BACKUP_DIR"
sudo cp -a "$OLD_ROXY"/* "$BACKUP_DIR/"

# Create new structure if needed
echo "[2/4] Ensuring /opt/roxy/ structure..."
sudo mkdir -p "$NEW_ROXY"/{agents,bots,configs,data,mcp-servers,pipeline,secrets,voice,logs}

# Migrate with rsync (preserves permissions, handles existing files)
echo "[3/4] Migrating files..."
sudo rsync -av --ignore-existing "$OLD_ROXY/" "$NEW_ROXY/"

# Set ownership
echo "[4/4] Setting permissions..."
sudo chown -R $USER:$USER "$NEW_ROXY"

echo ""
echo "✅ Migration complete"
echo "   Backup: $BACKUP_DIR"
echo "   New location: $NEW_ROXY"
echo ""
echo "   Old ~/.roxy/ preserved (remove manually when ready)"
MIGRATE_EOF

chmod +x "$MIGRATION_SCRIPT"
log "Migration script generated: $MIGRATION_SCRIPT"

#===============================================================================
echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║  RECONCILIATION COMPLETE                                                  ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║                                                                           ║"

# Summary
SKIP_COUNT=0
INSTALL_COUNT=0
for key in "${!SKIP_INSTALL[@]}"; do
    if [ "${SKIP_INSTALL[$key]}" = "true" ]; then
        ((SKIP_COUNT++)) || true
    else
        ((INSTALL_COUNT++)) || true
    fi
done

echo "║  WILL SKIP (already installed):    $SKIP_COUNT services                       ║"
echo "║  WILL INSTALL (new):               $INSTALL_COUNT services                       ║"
echo "║                                                                           ║"

if [ "${MIGRATION_NEEDED[roxy_dir]:-false}" = "true" ]; then
echo "║  ⚠️  ~/.roxy/ migration needed                                             ║"
echo "║     Run: ./000a-migrate-roxy-dir.sh                                       ║"
fi

if [ "$PORTS_OK" = "false" ]; then
echo "║  ⚠️  Port conflicts detected - review above                               ║"
fi

echo "║                                                                           ║"
echo "║  NEXT STEPS:                                                              ║"
echo "║  1. Review this report                                                    ║"
echo "║  2. Run ./000a-migrate-roxy-dir.sh (if ~/.roxy exists)                    ║"
echo "║  3. Run ./FULL-SEND-ADDITIVE.sh (not FULL-SEND.sh)                        ║"
echo "║                                                                           ║"
echo "║  Report: $RECONCILE_REPORT                                                ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"

# Export for FULL-SEND to consume
export CITADEL_RECONCILE_REPORT="$RECONCILE_REPORT"
