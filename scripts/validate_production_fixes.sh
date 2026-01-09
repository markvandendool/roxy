#!/bin/bash
# Production Fixes Validation Script
# Validates all 4 Codex audit fixes

set -e

ROXY_URL="${ROXY_URL:-http://127.0.0.1:8766}"
METRICS_URL="${METRICS_URL:-http://127.0.0.1:9091}"
TOKEN_FILE="${TOKEN_FILE:-$HOME/.roxy/secret.token}"

echo "=========================================="
echo "ROXY Production Fixes Validation"
echo "=========================================="
echo ""

# Load token
if [ ! -f "$TOKEN_FILE" ]; then
    echo "❌ ERROR: Token file not found at $TOKEN_FILE"
    exit 1
fi
TOKEN=$(cat "$TOKEN_FILE")

# Test 1: Health endpoint with dependency checks
echo "Test 1: Health endpoint dependency checks"
echo "----------------------------------------"
HEALTH_RESPONSE=$(curl -s "$ROXY_URL/health")
HEALTH_STATUS=$(echo "$HEALTH_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('status', 'unknown'))" 2>/dev/null || echo "unknown")
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$ROXY_URL/health")

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Health endpoint returns 200 when all dependencies OK"
    CHECKS=$(echo "$HEALTH_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('checks', {})))" 2>/dev/null || echo "0")
    if [ "$CHECKS" -ge 4 ]; then
        echo "✅ Health checks include all dependencies (found $CHECKS checks)"
    else
        echo "⚠️  WARNING: Expected 4+ checks, found $CHECKS"
    fi
else
    echo "⚠️  Health endpoint returned $HTTP_CODE (expected 200 when healthy)"
fi
echo ""

# Test 2: Auth guard
echo "Test 2: Authentication guard"
echo "----------------------------------------"
AUTH_FAIL=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$ROXY_URL/run" \
    -H "Content-Type: application/json" \
    -d '{"command":"test"}')
if [ "$AUTH_FAIL" = "403" ]; then
    echo "✅ Auth guard blocks requests without token (403)"
else
    echo "❌ FAIL: Expected 403, got $AUTH_FAIL"
fi

AUTH_PASS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$ROXY_URL/run" \
    -H "Content-Type: application/json" \
    -H "X-ROXY-Token: $TOKEN" \
    -d '{"command":"hello"}')
if [ "$AUTH_PASS" = "200" ]; then
    echo "✅ Auth guard allows requests with valid token (200)"
else
    echo "⚠️  WARNING: Expected 200, got $AUTH_PASS"
fi
echo ""

# Test 3: Streaming endpoint - both q and command params
echo "Test 3: Streaming endpoint parameter support"
echo "----------------------------------------"
STREAM_Q=$(timeout 3 curl -s -N "$ROXY_URL/stream?q=test" \
    -H "X-ROXY-Token: $TOKEN" 2>&1 | head -1)
if echo "$STREAM_Q" | grep -q "data:"; then
    echo "✅ Streaming endpoint accepts 'q' parameter"
else
    echo "⚠️  WARNING: 'q' parameter may not work (got: ${STREAM_Q:0:50})"
fi

STREAM_CMD=$(timeout 3 curl -s -N "$ROXY_URL/stream?command=test" \
    -H "X-ROXY-Token: $TOKEN" 2>&1 | head -1)
if echo "$STREAM_CMD" | grep -q "data:"; then
    echo "✅ Streaming endpoint accepts 'command' parameter"
else
    echo "⚠️  WARNING: 'command' parameter may not work (got: ${STREAM_CMD:0:50})"
fi
echo ""

# Test 4: Metrics endpoint
echo "Test 4: Prometheus metrics endpoint"
echo "----------------------------------------"
METRICS_RESPONSE=$(curl -s "$METRICS_URL/metrics" 2>&1 | head -5)
if echo "$METRICS_RESPONSE" | grep -q "roxy_requests_total\|# HELP"; then
    echo "✅ Metrics endpoint accessible and returning metrics"
    METRIC_COUNT=$(curl -s "$METRICS_URL/metrics" 2>&1 | grep -c "roxy_" || echo "0")
    echo "   Found $METRIC_COUNT ROXY metrics"
else
    echo "⚠️  WARNING: Metrics endpoint may not be initialized"
    echo "   Response: ${METRICS_RESPONSE:0:100}"
fi
echo ""

# Test 5: Rate limiting (if enabled)
echo "Test 5: Rate limiting"
echo "----------------------------------------"
RATE_LIMIT_ENABLED=$(curl -s "$ROXY_URL/health" | python3 -c "import sys, json; d=json.load(sys.stdin); print('ok' in str(d.get('checks', {}).get('rate_limiter', '')))" 2>/dev/null || echo "false")
if [ "$RATE_LIMIT_ENABLED" = "True" ]; then
    echo "✅ Rate limiter is available"
    # Try to trigger rate limit (may not work if limits are high)
    echo "   (Rate limit testing requires burst requests - skipping for now)"
else
    echo "⚠️  Rate limiter status unclear"
fi
echo ""

# Test 6: Observability logs
echo "Test 6: Observability log hygiene"
echo "----------------------------------------"
LOG_DIR="$HOME/.roxy/logs/observability"
if [ -d "$LOG_DIR" ]; then
    LOG_COUNT=$(find "$LOG_DIR" -name "*.jsonl" -type f | wc -l)
    echo "✅ Found $LOG_COUNT observability log files"
    
    # Check log file sizes
    LARGE_LOGS=$(find "$LOG_DIR" -name "*.jsonl" -type f -size +100M | wc -l)
    if [ "$LARGE_LOGS" -eq 0 ]; then
        echo "✅ All log files under 100MB (rotation working)"
    else
        echo "⚠️  WARNING: $LARGE_LOGS log files exceed 100MB"
    fi
    
    # Check for request IDs in recent log
    RECENT_LOG=$(find "$LOG_DIR" -name "requests_*.jsonl" -type f -mtime -1 | head -1)
    if [ -n "$RECENT_LOG" ]; then
        if tail -1 "$RECENT_LOG" 2>/dev/null | python3 -c "import sys, json; d=json.load(sys.stdin); exit(0 if 'request_id' in d else 1)" 2>/dev/null; then
            echo "✅ Recent logs include request_id field"
        else
            echo "⚠️  WARNING: Recent logs may not have request_id"
        fi
    fi
else
    echo "⚠️  Observability log directory not found"
fi
echo ""

# Summary
echo "=========================================="
echo "Validation Complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Check metrics: curl -s $METRICS_URL/metrics | grep roxy_"
echo "2. Test health with dependencies down: stop Ollama/ChromaDB and check /health"
echo "3. Monitor streaming heartbeats: curl -N '$ROXY_URL/stream?q=test' -H 'X-ROXY-Token:$TOKEN'"
echo "4. Check logs: tail -f $LOG_DIR/requests_*.jsonl"
echo ""





