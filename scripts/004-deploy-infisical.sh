#!/bin/bash
#===============================================================================
# LUNA-002: Deploy Infisical Secrets Manager
# Target: ROXY-1 (Ubuntu 24.04)
# Run as: ./004-deploy-infisical.sh
#===============================================================================

set -euo pipefail

ROXY_ROOT="/opt/roxy"
COMPOSE_DIR="$ROXY_ROOT/compose"

echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║  LUNA-002: INFISICAL SECRETS MANAGER DEPLOYMENT                           ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"

# Load environment
set -a
source "$ROXY_ROOT/.env"
set +a

#===============================================================================
echo ""
echo "[1/4] Generating Infisical secrets (if not set)..."
#===============================================================================

# Generate secrets if not already set
if [ -z "${INFISICAL_ENCRYPTION_KEY:-}" ]; then
    INFISICAL_ENCRYPTION_KEY=$(openssl rand -hex 32)
    echo "INFISICAL_ENCRYPTION_KEY=$INFISICAL_ENCRYPTION_KEY" >> "$ROXY_ROOT/.env"
    echo "Generated INFISICAL_ENCRYPTION_KEY"
fi

if [ -z "${INFISICAL_JWT_SECRET:-}" ]; then
    INFISICAL_JWT_SECRET=$(openssl rand -hex 32)
    echo "INFISICAL_JWT_SECRET=$INFISICAL_JWT_SECRET" >> "$ROXY_ROOT/.env"
    echo "Generated INFISICAL_JWT_SECRET"
fi

if [ -z "${INFISICAL_JWT_REFRESH:-}" ]; then
    INFISICAL_JWT_REFRESH=$(openssl rand -hex 32)
    echo "INFISICAL_JWT_REFRESH=$INFISICAL_JWT_REFRESH" >> "$ROXY_ROOT/.env"
    echo "Generated INFISICAL_JWT_REFRESH"
fi

if [ -z "${INFISICAL_JWT_AUTH:-}" ]; then
    INFISICAL_JWT_AUTH=$(openssl rand -hex 32)
    echo "INFISICAL_JWT_AUTH=$INFISICAL_JWT_AUTH" >> "$ROXY_ROOT/.env"
    echo "Generated INFISICAL_JWT_AUTH"
fi

# Reload environment
set -a
source "$ROXY_ROOT/.env"
set +a

echo "✅ Secrets configured"

#===============================================================================
echo ""
echo "[2/4] Pulling Infisical images..."
#===============================================================================
cd "$COMPOSE_DIR"
docker compose -f docker-compose.infisical.yml pull
echo "✅ Images pulled"

#===============================================================================
echo ""
echo "[3/4] Starting Infisical..."
#===============================================================================
docker compose -f docker-compose.infisical.yml up -d

echo "Waiting for Infisical to become ready..."
until curl -sf http://localhost:8080/api/status > /dev/null 2>&1; do
    echo "  Waiting..."
    sleep 5
done
echo "✅ Infisical running"

#===============================================================================
echo ""
echo "[4/4] Creating initial project structure..."
#===============================================================================
cat << 'EOF'

╔═══════════════════════════════════════════════════════════════════════════╗
║  INFISICAL DEPLOYMENT COMPLETE                                            ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  Access: https://secrets.roxy.local                                     ║
║                                                                           ║
║  MANUAL SETUP REQUIRED:                                                   ║
║                                                                           ║
║  1. Open https://secrets.roxy.local                                     ║
║  2. Create admin account                                                  ║
║  3. Create project: "roxy-citadel"                                        ║
║  4. Create environments: dev, staging, prod                               ║
║  5. Add secrets:                                                          ║
║     • POSTGRES_PASSWORD                                                   ║
║     • MINIO_ROOT_USER                                                     ║
║     • MINIO_ROOT_PASSWORD                                                 ║
║     • OBS_WEBSOCKET_PASSWORD                                              ║
║     • YOUTUBE_API_KEY                                                     ║
║     • DISCORD_BOT_TOKEN                                                   ║
║     • TELEGRAM_BOT_TOKEN                                                  ║
║  6. Create service account for CLI access                                 ║
║  7. Run: infisical login                                                  ║
║                                                                           ║
║  CLI Usage:                                                               ║
║  • infisical secrets --env=prod                                           ║
║  • infisical run -- ./my-script.sh                                        ║
║                                                                           ║
║  Next: ./005-deploy-voice.sh                                              ║
╚═══════════════════════════════════════════════════════════════════════════╝

EOF
