#!/bin/bash
#===============================================================================
# LUNA-S1: Deploy Foundation Infrastructure
# Target: ROXY-1 (Ubuntu 24.04)
# Run as: ./003-deploy-foundation.sh
#===============================================================================

set -euo pipefail

ROXY_ROOT="/opt/roxy"
COMPOSE_DIR="$ROXY_ROOT/compose"

echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║  LUNA-S1: FOUNDATION INFRASTRUCTURE DEPLOYMENT                            ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"

# Check .env exists
if [ ! -f "$ROXY_ROOT/.env" ]; then
    echo "❌ ERROR: $ROXY_ROOT/.env not found"
    echo "   Copy .env.template to .env and fill in values"
    exit 1
fi

# Load environment
set -a
source "$ROXY_ROOT/.env"
set +a

# Check required variables
required_vars=(
    "POSTGRES_PASSWORD"
    "MINIO_ROOT_USER"
    "MINIO_ROOT_PASSWORD"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var:-}" ]; then
        echo "❌ ERROR: $var not set in .env"
        exit 1
    fi
done

#===============================================================================
echo ""
echo "[1/7] Creating PostgreSQL init scripts..."
#===============================================================================
mkdir -p "$COMPOSE_DIR/init-scripts/postgres"
cat > "$COMPOSE_DIR/init-scripts/postgres/01-init-databases.sql" << 'EOF'
-- Create databases for each service
CREATE DATABASE n8n;
CREATE DATABASE infisical;
CREATE DATABASE plane;
CREATE DATABASE twenty;
CREATE DATABASE chatwoot;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE n8n TO roxy;
GRANT ALL PRIVILEGES ON DATABASE infisical TO roxy;
GRANT ALL PRIVILEGES ON DATABASE plane TO roxy;
GRANT ALL PRIVILEGES ON DATABASE twenty TO roxy;
GRANT ALL PRIVILEGES ON DATABASE chatwoot TO roxy;
EOF
echo "✅ Init scripts created"

#===============================================================================
echo ""
echo "[2/7] Creating NATS streams configuration..."
#===============================================================================
cat > "$COMPOSE_DIR/configs/nats-streams.json" << 'EOF'
{
  "streams": [
    {
      "name": "SYSTEM",
      "subjects": ["system.>"],
      "retention": "limits",
      "max_msgs": 100000,
      "max_bytes": 104857600,
      "max_age": 604800000000000,
      "storage": "file"
    },
    {
      "name": "AGENTS",
      "subjects": ["agents.>"],
      "retention": "limits",
      "max_msgs": 100000,
      "max_bytes": 104857600,
      "max_age": 604800000000000,
      "storage": "file"
    },
    {
      "name": "PIPELINE",
      "subjects": ["pipeline.>"],
      "retention": "limits",
      "max_msgs": 50000,
      "max_bytes": 52428800,
      "max_age": 2592000000000000,
      "storage": "file"
    },
    {
      "name": "ALERTS",
      "subjects": ["alerts.>"],
      "retention": "limits",
      "max_msgs": 10000,
      "max_bytes": 10485760,
      "max_age": 2592000000000000,
      "storage": "file"
    }
  ]
}
EOF
echo "✅ NATS streams configured"

#===============================================================================
echo ""
echo "[3/7] Creating MinIO bucket initialization script..."
#===============================================================================
cat > "$COMPOSE_DIR/init-scripts/minio-init.sh" << 'EOF'
#!/bin/bash
# Wait for MinIO to be ready
sleep 10

# Configure mc alias
mc alias set roxy http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"

# Create buckets
mc mb roxy/recordings --ignore-existing
mc mb roxy/clips --ignore-existing
mc mb roxy/thumbnails --ignore-existing
mc mb roxy/exports --ignore-existing
mc mb roxy/transcripts --ignore-existing
mc mb roxy/models --ignore-existing

# Set lifecycle policies (cleanup after 90 days for recordings)
mc ilm rule add roxy/recordings --expire-days 90

echo "MinIO buckets created"
EOF
chmod +x "$COMPOSE_DIR/init-scripts/minio-init.sh"
echo "✅ MinIO init script created"

#===============================================================================
echo ""
echo "[4/7] Pulling Docker images..."
#===============================================================================
cd "$COMPOSE_DIR"
docker compose -f docker-compose.foundation.yml pull
echo "✅ Images pulled"

#===============================================================================
echo ""
echo "[5/7] Starting foundation services..."
#===============================================================================
docker compose -f docker-compose.foundation.yml up -d

# Wait for services to be healthy
echo "Waiting for services to become healthy..."
sleep 10

#===============================================================================
echo ""
echo "[6/7] Creating NATS JetStream streams..."
#===============================================================================
# Wait for NATS
until curl -sf http://localhost:8222/healthz > /dev/null 2>&1; do
    echo "Waiting for NATS..."
    sleep 2
done

# Create streams via NATS CLI (if available) or API
if command -v nats &> /dev/null; then
    nats stream add SYSTEM --subjects "system.>" --retention limits --max-msgs 100000 --max-bytes 100MB --max-age 7d --storage file --replicas 1 --discard old --dupe-window 2m -f
    nats stream add AGENTS --subjects "agents.>" --retention limits --max-msgs 100000 --max-bytes 100MB --max-age 7d --storage file --replicas 1 --discard old --dupe-window 2m -f
    nats stream add PIPELINE --subjects "pipeline.>" --retention limits --max-msgs 50000 --max-bytes 50MB --max-age 30d --storage file --replicas 1 --discard old --dupe-window 2m -f
    nats stream add ALERTS --subjects "alerts.>" --retention limits --max-msgs 10000 --max-bytes 10MB --max-age 30d --storage file --replicas 1 --discard old --dupe-window 2m -f
    echo "✅ NATS streams created"
else
    echo "⚠️  NATS CLI not installed, streams need manual creation"
    echo "   Install with: curl -sf https://binaries.nats.dev/nats-io/natscli/nats@latest | sh"
fi

#===============================================================================
echo ""
echo "[7/7] Initializing MinIO buckets..."
#===============================================================================
# Run MinIO init in a temporary container
docker run --rm --network roxy-network \
    -e MINIO_ROOT_USER="$MINIO_ROOT_USER" \
    -e MINIO_ROOT_PASSWORD="$MINIO_ROOT_PASSWORD" \
    minio/mc sh -c '
        mc alias set roxy http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
        mc mb roxy/recordings --ignore-existing
        mc mb roxy/clips --ignore-existing
        mc mb roxy/thumbnails --ignore-existing
        mc mb roxy/exports --ignore-existing
        mc mb roxy/transcripts --ignore-existing
        mc mb roxy/models --ignore-existing
        echo "Buckets created"
    '
echo "✅ MinIO buckets created"

#===============================================================================
echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║  FOUNDATION DEPLOYMENT COMPLETE                                           ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Services running:                                                        ║"
echo "║  • PostgreSQL    → localhost:5432                                         ║"
echo "║  • Redis         → localhost:6379                                         ║"
echo "║  • n8n           → https://n8n.roxy.local (port 5678)                   ║"
echo "║  • MinIO         → https://minio.roxy.local (ports 9000/9001)           ║"
echo "║  • ChromaDB      → localhost:8000                                         ║"
echo "║  • NATS          → localhost:4222 (monitor: 8222)                         ║"
echo "║  • Caddy         → ports 80/443 (reverse proxy)                           ║"
echo "║                                                                           ║"
echo "║  Health check: $ROXY_ROOT/scripts/health-check.sh                         ║"
echo "║  Logs: docker compose -f docker-compose.foundation.yml logs -f            ║"
echo "║                                                                           ║"
echo "║  Next: ./004-deploy-infisical.sh                                          ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"

# Quick health check
echo ""
echo "Running quick health check..."
sleep 5

services=("postgres:5432" "redis:6379" "n8n:5678" "minio:9000" "chromadb:8000" "nats:4222")
for svc in "${services[@]}"; do
    name="${svc%%:*}"
    port="${svc##*:}"
    if docker compose -f docker-compose.foundation.yml exec -T "$name" true 2>/dev/null; then
        echo "✅ $name"
    else
        echo "⚠️  $name (may still be starting)"
    fi
done
