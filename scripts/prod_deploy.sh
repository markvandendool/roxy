#!/usr/bin/env bash
# prod_deploy.sh - Gate0 one-command production deploy
# Usage: ./prod_deploy.sh
#
# This script:
# 1. Pulls latest code (if git repo)
# 2. Restarts roxy-core service
# 3. Waits for /ready (no manual sleeps)
# 4. Runs proof bundle (gate2_smoke)
# 5. Prints PASS/FAIL

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROXY_DIR="${SCRIPT_DIR}/.."
BASE_URL="${ROXY_BASE_URL:-http://127.0.0.1:8766}"
READY_TIMEOUT="${READY_TIMEOUT:-30}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "ROXY Gate0 Production Deploy"
echo "========================================"
echo ""

# Step 1: Pull latest (if git repo)
echo "=== Step 1: Git pull ==="
cd "$ROXY_DIR"
if [ -d ".git" ]; then
    git pull --ff-only 2>&1 || echo "(git pull skipped or failed - continuing)"
else
    echo "(not a git repo - skipping pull)"
fi
echo ""

# Step 2: Restart roxy-core
echo "=== Step 2: Restart roxy-core ==="
systemctl --user restart roxy-core.service
echo "Service restarted"
echo ""

# Step 3: Wait for /ready
echo "=== Step 3: Wait for ready ==="
if ! "$SCRIPT_DIR/wait-for-ready.sh" "$READY_TIMEOUT" "$BASE_URL/ready"; then
    echo -e "${RED}FAIL: Service did not become ready${NC}"
    echo ""
    echo "=== Service status ==="
    systemctl --user status roxy-core.service --no-pager || true
    echo ""
    echo "=== Recent logs ==="
    journalctl --user -u roxy-core --no-pager -n 20 || true
    exit 1
fi
echo ""

# Step 4: Run proof bundle (gate2_smoke)
echo "=== Step 4: Gate2 smoke test ==="
if ! "$SCRIPT_DIR/gate2_smoke.sh"; then
    echo -e "${RED}FAIL: Gate2 smoke test failed${NC}"
    exit 1
fi
echo ""

# Step 5: Final status
echo "========================================"
echo -e "${GREEN}GATE0 PASS${NC}"
echo "========================================"
echo ""
echo "Deployment successful. Endpoints:"
echo "  /health: $BASE_URL/health"
echo "  /ready:  $BASE_URL/ready"
echo "  /info:   $BASE_URL/info"
echo ""

# Show ready response for confirmation
echo "=== /ready response ==="
curl -sS "$BASE_URL/ready" | python3 -m json.tool
