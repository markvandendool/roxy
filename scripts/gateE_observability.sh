#!/usr/bin/env bash
# gateE_observability.sh - Observability verification test
# Verifies all critical metrics are exported and stable
set -euo pipefail

BASE_URL="${ROXY_BASE_URL:-http://127.0.0.1:8766}"
PROOF_DIR="$HOME/.roxy/proofs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PROOF_FILE="$PROOF_DIR/gateE_${TIMESTAMP}.log"

mkdir -p "$PROOF_DIR"

echo "========================================" | tee "$PROOF_FILE"
echo "GATE E: Observability Verification" | tee -a "$PROOF_FILE"
echo "Timestamp: $(date -Iseconds)" | tee -a "$PROOF_FILE"
echo "========================================" | tee -a "$PROOF_FILE"
echo "" | tee -a "$PROOF_FILE"

# Step 1: Verify /metrics returns Prometheus format
echo "=== Step 1: Metrics endpoint availability ===" | tee -a "$PROOF_FILE"
HTTP_CODE=$(curl -sS -o /tmp/metrics.txt -w '%{http_code}' "$BASE_URL/metrics")
echo "HTTP Code: $HTTP_CODE" | tee -a "$PROOF_FILE"

if [ "$HTTP_CODE" != "200" ]; then
    echo "FAIL: /metrics returned $HTTP_CODE" | tee -a "$PROOF_FILE"
    exit 1
fi
echo "Metrics endpoint: PASS" | tee -a "$PROOF_FILE"
echo "" | tee -a "$PROOF_FILE"

# Step 2: Verify required metrics exist
echo "=== Step 2: Required metrics presence ===" | tee -a "$PROOF_FILE"
REQUIRED_METRICS=(
    "roxy_requests_total"
    "roxy_request_duration_seconds"
    "roxy_pool_reachable"
    "roxy_pool_latency_ms"
    "roxy_ready_checks_total"
    "roxy_active_requests"
)

MISSING=0
for metric in "${REQUIRED_METRICS[@]}"; do
    if grep -q "$metric" /tmp/metrics.txt; then
        echo "  $metric: PRESENT" | tee -a "$PROOF_FILE"
    else
        echo "  $metric: MISSING" | tee -a "$PROOF_FILE"
        MISSING=$((MISSING + 1))
    fi
done

if [ "$MISSING" -gt 0 ]; then
    echo "FAIL: $MISSING required metrics missing" | tee -a "$PROOF_FILE"
    exit 1
fi
echo "Required metrics: PASS" | tee -a "$PROOF_FILE"
echo "" | tee -a "$PROOF_FILE"

# Step 3: Verify pool metrics have correct values
echo "=== Step 3: Pool metrics values ===" | tee -a "$PROOF_FILE"
W5700X=$(grep 'roxy_pool_reachable{pool="w5700x"}' /tmp/metrics.txt | awk '{print $2}')
XT6900=$(grep 'roxy_pool_reachable{pool="6900xt"}' /tmp/metrics.txt | awk '{print $2}')

echo "w5700x reachable: $W5700X" | tee -a "$PROOF_FILE"
echo "6900xt reachable: $XT6900" | tee -a "$PROOF_FILE"

if [ "$W5700X" != "1.0" ] || [ "$XT6900" != "1.0" ]; then
    echo "FAIL: Pool reachability metrics incorrect" | tee -a "$PROOF_FILE"
    exit 1
fi
echo "Pool metrics: PASS" | tee -a "$PROOF_FILE"
echo "" | tee -a "$PROOF_FILE"

# Step 4: Scrape stability test
echo "=== Step 4: Scrape stability (5 consecutive scrapes) ===" | tee -a "$PROOF_FILE"
SUCCESS=0
for i in $(seq 1 5); do
    CODE=$(curl -sS -o /dev/null -w '%{http_code}' "$BASE_URL/metrics")
    if [ "$CODE" = "200" ]; then
        SUCCESS=$((SUCCESS + 1))
        echo "  Scrape $i: OK" | tee -a "$PROOF_FILE"
    else
        echo "  Scrape $i: FAIL ($CODE)" | tee -a "$PROOF_FILE"
    fi
    sleep 0.2
done

if [ "$SUCCESS" -lt 5 ]; then
    echo "FAIL: Scrape stability failed ($SUCCESS/5)" | tee -a "$PROOF_FILE"
    exit 1
fi
echo "Scrape stability: PASS" | tee -a "$PROOF_FILE"
echo "" | tee -a "$PROOF_FILE"

# Step 5: Verify /version endpoint
echo "=== Step 5: Version endpoint ===" | tee -a "$PROOF_FILE"
VERSION=$(curl -sS "$BASE_URL/version")
echo "$VERSION" | python3 -m json.tool | tee -a "$PROOF_FILE"

GIT_SHA=$(echo "$VERSION" | python3 -c "import sys,json; print(json.load(sys.stdin).get('git_sha', 'none'))")
if [ "$GIT_SHA" = "none" ] || [ "$GIT_SHA" = "unknown" ]; then
    echo "WARNING: git_sha not available" | tee -a "$PROOF_FILE"
else
    echo "Git SHA: $GIT_SHA" | tee -a "$PROOF_FILE"
fi
echo "Version endpoint: PASS" | tee -a "$PROOF_FILE"
echo "" | tee -a "$PROOF_FILE"

# Step 6: Summary of all metrics
echo "=== Step 6: Metrics summary ===" | tee -a "$PROOF_FILE"
METRIC_COUNT=$(grep -c "^roxy_" /tmp/metrics.txt || echo 0)
echo "Total ROXY metrics exported: $METRIC_COUNT" | tee -a "$PROOF_FILE"
echo "" | tee -a "$PROOF_FILE"

# List all roxy metrics
grep "^# HELP roxy_" /tmp/metrics.txt | tee -a "$PROOF_FILE"
echo "" | tee -a "$PROOF_FILE"

echo "========================================" | tee -a "$PROOF_FILE"
echo "GATE E: PASS" | tee -a "$PROOF_FILE"
echo "Proof file: $PROOF_FILE" | tee -a "$PROOF_FILE"
echo "========================================" | tee -a "$PROOF_FILE"
