#!/bin/bash
# Agent Credential Setup - Centralized Credential Management
# Purpose: Store all ROXY-1 credentials in Infisical for agent access
# Created: 2025-12-29

set -e

ROXY_IP="10.0.0.69"
INFISICAL_URL="http://${ROXY_IP}:8080"

echo "=== Agent Credential Setup ==="
echo "Target: ROXY-1 (${ROXY_IP})"
echo ""

# Check if Infisical is running
if ! curl -s "${INFISICAL_URL}/api/v1/health" > /dev/null 2>&1; then
    echo "❌ Infisical not accessible at ${INFISICAL_URL}"
    echo "   Start it first: ssh roxy-1 'cd ${ROXY_ROOT:-$HOME/.roxy} && docker compose -f compose/docker-compose.infisical.yml up -d'"
    exit 1
fi

echo "✅ Infisical is running"
echo ""
echo "📝 Credentials to store in Infisical:"
echo ""
echo "   Project: mindsong-juke-hub"
echo "   Environment: production"
echo ""
echo "   Secrets to add:"
echo "   - ROXY_SSH_HOST: ${ROXY_IP}"
echo "   - ROXY_SSH_USER: mark"
echo "   - ROXY_SSH_KEY_PATH: ~/.ssh/id_ed25519"
echo "   - ROXY_INFISICAL_URL: ${INFISICAL_URL}"
echo ""
echo "   For agents to access:"
echo "   1. Install Infisical CLI: brew install infisical/get-cli/infisical"
echo "   2. Login: infisical login"
echo "   3. Use: infisical run --env=production -- <command>"
echo ""
echo "   Or via API:"
echo "   curl -H 'Authorization: Bearer <token>' ${INFISICAL_URL}/api/v1/secrets/..."
echo ""

