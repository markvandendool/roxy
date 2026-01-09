#!/bin/bash
#===============================================================================
# LUNA-000 CITADEL - Directory Structure Setup
# Target: ROXY-1 (Ubuntu 24.04)
# Run as: sudo ./001-setup-directories.sh
#===============================================================================

set -euo pipefail

ROXY_ROOT="/opt/roxy"
ROXY_USER="${SUDO_USER:-$USER}"

echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║  CITADEL DIRECTORY STRUCTURE SETUP                                        ║"
echo "║  Target: $ROXY_ROOT                                                       ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"

# Create main directory structure
echo "[1/6] Creating directory structure..."

directories=(
    # Core
    "$ROXY_ROOT"
    "$ROXY_ROOT/logs"
    "$ROXY_ROOT/backups"
    "$ROXY_ROOT/data"

    # Agents
    "$ROXY_ROOT/agents/browser-agent"
    "$ROXY_ROOT/agents/desktop-agent"
    "$ROXY_ROOT/agents/obs-agent"
    "$ROXY_ROOT/agents/orchestrator/nodes"
    "$ROXY_ROOT/agents/orchestrator/tools"
    "$ROXY_ROOT/agents/orchestrator/commands"
    "$ROXY_ROOT/agents/memory"

    # Bots
    "$ROXY_ROOT/bots/discord"
    "$ROXY_ROOT/bots/telegram"

    # MCP Servers
    "$ROXY_ROOT/mcp-servers/desktop/tools"
    "$ROXY_ROOT/mcp-servers/browser"
    "$ROXY_ROOT/mcp-servers/obs"
    "$ROXY_ROOT/mcp-gateway"

    # Pipeline
    "$ROXY_ROOT/pipeline/transcription"
    "$ROXY_ROOT/pipeline/clips"
    "$ROXY_ROOT/pipeline/upscale"
    "$ROXY_ROOT/pipeline/thumbnails"
    "$ROXY_ROOT/pipeline/encode/presets"
    "$ROXY_ROOT/pipeline/queue"

    # Voice
    "$ROXY_ROOT/voice/wakeword/models"
    "$ROXY_ROOT/voice/transcription"
    "$ROXY_ROOT/voice/tts"
    "$ROXY_ROOT/voice/reference"

    # Integrations
    "$ROXY_ROOT/integrations/youtube"
    "$ROXY_ROOT/integrations/social"

    # Infrastructure
    "$ROXY_ROOT/compose"
    "$ROXY_ROOT/configs/caddy"
    "$ROXY_ROOT/configs/nats"
    "$ROXY_ROOT/configs/infisical"

    # Secrets (encrypted at rest)
    "$ROXY_ROOT/secrets/browser-sessions"
    "$ROXY_ROOT/secrets/keys"

    # ComfyUI workflows
    "$ROXY_ROOT/comfyui/workflows"
    "$ROXY_ROOT/comfyui/models"

    # Data stores
    "$ROXY_ROOT/data/chromadb"
    "$ROXY_ROOT/data/minio"
    "$ROXY_ROOT/data/postgres"
    "$ROXY_ROOT/data/redis"
    "$ROXY_ROOT/data/n8n"
    "$ROXY_ROOT/data/nats"

    # Tests
    "$ROXY_ROOT/tests/e2e"
    "$ROXY_ROOT/tests/unit"
)

for dir in "${directories[@]}"; do
    mkdir -p "$dir"
    echo "  ✓ $dir"
done

# Set ownership
echo ""
echo "[2/6] Setting ownership to $ROXY_USER..."
chown -R "$ROXY_USER:$ROXY_USER" "$ROXY_ROOT"

# Set permissions
echo "[3/6] Setting permissions..."
chmod 700 "$ROXY_ROOT/secrets"
chmod 700 "$ROXY_ROOT/secrets/browser-sessions"
chmod 700 "$ROXY_ROOT/secrets/keys"
chmod 755 "$ROXY_ROOT"

# Create .env template
echo "[4/6] Creating .env template..."
cat > "$ROXY_ROOT/.env.template" << 'EOF'
#===============================================================================
# ROXY CITADEL - Environment Configuration
# Copy to .env and fill in values
# Secrets should be stored in Infisical, not here
#===============================================================================

# Core
ROXY_ROOT=/opt/roxy
ROXY_DOMAIN=roxy.local
ROXY_ENV=production

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3:8b
HSA_OVERRIDE_GFX_VERSION=10.3.0

# n8n
N8N_HOST=n8n.roxy.local
N8N_PORT=5678
N8N_PROTOCOL=https

# PostgreSQL (shared)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=roxy
# POSTGRES_PASSWORD stored in Infisical

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# MinIO
MINIO_HOST=minio.roxy.local
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001
# MINIO_ROOT_USER stored in Infisical
# MINIO_ROOT_PASSWORD stored in Infisical

# ChromaDB
CHROMADB_HOST=localhost
CHROMADB_PORT=8000

# NATS
NATS_HOST=localhost
NATS_PORT=4222
NATS_MONITOR_PORT=8222

# Infisical
INFISICAL_HOST=secrets.roxy.local
INFISICAL_API_URL=https://secrets.roxy.local/api

# OBS
OBS_WEBSOCKET_HOST=localhost
OBS_WEBSOCKET_PORT=4455
# OBS_WEBSOCKET_PASSWORD stored in Infisical

# Voice
WAKEWORD_MODEL=hey_roxy
WAKEWORD_THRESHOLD=0.5
TTS_MODEL=xtts_v2
TTS_VOICE_REF=/opt/roxy/voice/reference/roxy_voice.wav

# Content Pipeline
RECORDINGS_DIR=/opt/roxy/data/recordings
CLIPS_DIR=/opt/roxy/data/clips
THUMBNAILS_DIR=/opt/roxy/data/thumbnails
EXPORTS_DIR=/opt/roxy/data/exports

# GPU (AMD)
GPU_DEVICE=/dev/dri/renderD128
VAAPI_DEVICE=/dev/dri/renderD128
EOF

# Create README
echo "[5/6] Creating README..."
cat > "$ROXY_ROOT/README.md" << 'EOF'
# ROXY CITADEL - /opt/roxy

## Directory Structure

```
/opt/roxy/
├── agents/          # AI agent code
│   ├── browser-agent/
│   ├── desktop-agent/
│   ├── obs-agent/
│   └── orchestrator/
├── bots/            # Discord/Telegram bots
├── compose/         # Docker compose files
├── configs/         # Service configs (Caddy, NATS, etc)
├── data/            # Persistent data stores
├── integrations/    # External API integrations
├── mcp-servers/     # MCP protocol servers
├── mcp-gateway/     # Unified MCP gateway
├── pipeline/        # Content processing pipeline
├── secrets/         # Encrypted secrets (SOPS)
├── tests/           # Test suites
└── voice/           # Wake word, TTS, transcription
```

## Quick Commands

```bash
# Start all services
docker compose -f compose/docker-compose.yml up -d

# Check health
curl http://localhost:8080/health

# View logs
docker compose -f compose/docker-compose.yml logs -f

# Stop all
docker compose -f compose/docker-compose.yml down
```

## Security

- Secrets stored in Infisical (secrets.roxy.local)
- Browser sessions encrypted with SOPS + Age
- gVisor sandbox for browser automation
- All sensitive dirs are chmod 700
EOF

# Create health check script
echo "[6/6] Creating health check script..."
cat > "$ROXY_ROOT/scripts/health-check.sh" << 'EOF'
#!/bin/bash
# ROXY Health Check - Run to verify all services

echo "═══════════════════════════════════════════════════════════"
echo "  ROXY CITADEL HEALTH CHECK"
echo "═══════════════════════════════════════════════════════════"

check_service() {
    local name=$1
    local url=$2
    local expected=$3

    if curl -sf "$url" > /dev/null 2>&1; then
        echo "✅ $name"
    else
        echo "❌ $name ($url)"
    fi
}

echo ""
echo "Infrastructure:"
check_service "Ollama" "http://localhost:11434/api/tags"
check_service "PostgreSQL" "localhost:5432"
check_service "Redis" "localhost:6379"
check_service "ChromaDB" "http://localhost:8000/api/v1/heartbeat"
check_service "MinIO" "http://localhost:9000/minio/health/live"
check_service "NATS" "http://localhost:8222/healthz"
check_service "n8n" "http://localhost:5678/healthz"

echo ""
echo "Voice:"
if pgrep -f "openwakeword" > /dev/null; then
    echo "✅ Wake Word Listener"
else
    echo "❌ Wake Word Listener"
fi

echo ""
echo "GPU:"
if command -v rocm-smi &> /dev/null; then
    rocm-smi --showuse | head -5
else
    echo "⚠️  ROCm not installed"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
EOF

chmod +x "$ROXY_ROOT/scripts/health-check.sh"
mkdir -p "$ROXY_ROOT/scripts"
mv "$ROXY_ROOT/scripts/health-check.sh" "$ROXY_ROOT/scripts/" 2>/dev/null || true

echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║  SETUP COMPLETE                                                           ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Next steps:                                                              ║"
echo "║  1. cp $ROXY_ROOT/.env.template $ROXY_ROOT/.env                          ║"
echo "║  2. Edit .env with your values                                            ║"
echo "║  3. Run ./002-install-dependencies.sh                                     ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
