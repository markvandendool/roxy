#!/bin/bash
# Quick test script for new ROXY features

echo "=== ROXY Feature Test ==="
echo ""

# Test 1: Health check
echo "1. Testing health endpoint..."
curl -s http://127.0.0.1:8766/health | python3 -m json.tool
echo ""

# Test 2: Cache test (run same command twice)
echo "2. Testing semantic cache (first request)..."
TOKEN=$(cat ~/.roxy/secret.token 2>/dev/null || echo "")
if [ -n "$TOKEN" ]; then
    curl -s -X POST http://127.0.0.1:8766/run \
        -H "Content-Type: application/json" \
        -H "X-ROXY-Token: $TOKEN" \
        -d '{"command":"what is ROXY?"}' | python3 -m json.tool | head -5
    echo ""
    echo "3. Testing cache hit (second request - should be faster)..."
    curl -s -X POST http://127.0.0.1:8766/run \
        -H "Content-Type: application/json" \
        -H "X-ROXY-Token: $TOKEN" \
        -d '{"command":"what is ROXY?"}' | python3 -m json.tool | head -5
else
    echo "   (Skipping - no auth token found)"
fi
echo ""

# Test 3: Rate limiting (rapid requests)
echo "4. Testing rate limiting (5 rapid requests)..."
for i in {1..5}; do
    echo -n "  Request $i: "
    if [ -n "$TOKEN" ]; then
        curl -s -X POST http://127.0.0.1:8766/run \
            -H "Content-Type: application/json" \
            -H "X-ROXY-Token: $TOKEN" \
            -d '{"command":"test"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('status', 'error'))"
    else
        echo "skipped (no token)"
    fi
done
echo ""

# Test 4: Check metrics
echo "5. Checking metrics collection..."
if [ -d ~/.roxy/logs/metrics ]; then
    echo "   Metrics directory exists"
    ls -lh ~/.roxy/logs/metrics/ | tail -3
else
    echo "   Metrics directory not found (will be created on first query)"
fi
echo ""

# Test 5: Check observability
echo "6. Checking observability logs..."
if [ -d ~/.roxy/logs/observability ]; then
    echo "   Observability directory exists"
    ls -lh ~/.roxy/logs/observability/ | tail -3
else
    echo "   Observability directory not found (will be created on first request)"
fi
echo ""

# Test 6: Streaming endpoint
echo "7. Testing streaming endpoint..."
if [ -n "$TOKEN" ]; then
    echo "   (Streaming test - should show progressive output)"
    timeout 5 curl -N -s "http://127.0.0.1:8766/stream?command=help" \
        -H "X-ROXY-Token: $TOKEN" 2>&1 | head -10 || echo "   Streaming endpoint responded"
else
    echo "   (Skipping - no auth token found)"
fi
echo ""

echo "=== Test Complete ==="
echo ""
echo "Check service status: systemctl --user status roxy-core"
echo "View logs: journalctl --user -u roxy-core -n 50"













