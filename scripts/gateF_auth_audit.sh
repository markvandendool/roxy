#!/usr/bin/env bash
# gateF_auth_audit.sh - Auth consistency verification
# Verifies all mutating endpoints require auth and return proper status codes
set -euo pipefail

BASE_URL="${ROXY_BASE_URL:-http://127.0.0.1:8766}"
TOKEN=$(tr -d '\r\n' < "$HOME/.roxy/secret.token")
PROOF_DIR="$HOME/.roxy/proofs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PROOF_FILE="$PROOF_DIR/gateF_${TIMESTAMP}.log"

mkdir -p "$PROOF_DIR"

log() {
    echo "$1" | tee -a "$PROOF_FILE"
}

PASS=0
FAIL=0

test_endpoint() {
    local method="$1"
    local endpoint="$2"
    local body="${3:-}"
    local expect_unauth="${4:-403}"  # Expected status without auth

    # Test WITHOUT auth - should fail
    local status_no_auth
    if [ -n "$body" ]; then
        status_no_auth=$(curl -sS -o /dev/null -w '%{http_code}' -X "$method" "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" -d "$body" 2>/dev/null || echo "000")
    else
        status_no_auth=$(curl -sS -o /dev/null -w '%{http_code}' -X "$method" "$BASE_URL$endpoint" 2>/dev/null || echo "000")
    fi

    # Test WITH auth - should succeed (or at least not 401/403)
    local status_with_auth
    if [ -n "$body" ]; then
        status_with_auth=$(curl -sS -o /dev/null -w '%{http_code}' -X "$method" "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" -H "X-ROXY-Token: $TOKEN" -d "$body" 2>/dev/null || echo "000")
    else
        status_with_auth=$(curl -sS -o /dev/null -w '%{http_code}' -X "$method" "$BASE_URL$endpoint" \
            -H "X-ROXY-Token: $TOKEN" 2>/dev/null || echo "000")
    fi

    # Verify: without auth should be 401 or 403
    if [ "$status_no_auth" = "401" ] || [ "$status_no_auth" = "403" ]; then
        log "  [PASS] $method $endpoint - No auth: $status_no_auth, With auth: $status_with_auth"
        PASS=$((PASS + 1))
    else
        log "  [FAIL] $method $endpoint - No auth: $status_no_auth (expected 401/403)"
        FAIL=$((FAIL + 1))
    fi
}

log "========================================"
log "GATE F: Auth Consistency Audit"
log "Timestamp: $(date -Iseconds)"
log "========================================"
log ""

# Test mutating endpoints
log "=== Testing POST endpoints (should require auth) ==="

test_endpoint "POST" "/run" '{"command":"echo test"}'
test_endpoint "POST" "/batch" '{"commands":["echo test"]}'
test_endpoint "POST" "/benchmark" '{"query":"test"}'
test_endpoint "POST" "/raw" '{"prompt":"test"}'
test_endpoint "POST" "/feedback" '{"query":"test","response":"test","type":"neutral"}'
test_endpoint "POST" "/memory/recall" '{"query":"test"}'
test_endpoint "POST" "/expert" '{"query":"test"}'
test_endpoint "POST" "/warmup" '{}'
test_endpoint "POST" "/bench/run" '{"task":"gsm8k","model":"test","pool":"w5700x","dry_run":true}'
test_endpoint "POST" "/bench/cancel" '{}'

log ""
log "=== Testing GET endpoints that should NOT require auth ==="

# These should be accessible without auth
for endpoint in "/health" "/ready" "/info" "/version" "/metrics" "/bench/status"; do
    status=$(curl -sS -o /dev/null -w '%{http_code}' "$BASE_URL$endpoint" 2>/dev/null || echo "000")
    if [ "$status" = "200" ]; then
        log "  [PASS] GET $endpoint - Public access: $status"
        PASS=$((PASS + 1))
    else
        log "  [WARN] GET $endpoint - Status: $status (expected 200)"
    fi
done

log ""
log "========================================"
log "Summary: $PASS passed, $FAIL failed"
log "========================================"

if [ "$FAIL" -eq 0 ]; then
    log ""
    log "GATE F: PASS"
    log "All mutating endpoints require authentication."
    log "Proof file: $PROOF_FILE"
    exit 0
else
    log ""
    log "GATE F: FAIL"
    log "Some endpoints have auth inconsistencies."
    log "Proof file: $PROOF_FILE"
    exit 1
fi
