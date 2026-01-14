#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Test Friday distributed inference via NATS
echo '=== Testing Friday Worker Inference ==='

# Check NATS connectivity
echo '[1/3] Checking NATS connectivity to Friday...'
nc -zv 10.0.0.65 4222 2>&1 | grep -q succeeded && echo '    ✅ NATS reachable' || echo '    ❌ NATS not reachable'

# Check Friday health endpoint
echo '[2/3] Checking Friday health...'
HEALTH=$(curl -s http://10.0.0.65:8765/health 2>/dev/null | head -c 50)
if [ -n "$HEALTH" ]; then
    echo '    ✅ Friday health endpoint responding'
else
    echo '    ❌ Friday not responding'
fi

# Check Redis connectivity
echo '[3/3] Checking Redis connectivity...'
nc -zv 10.0.0.65 6379 2>&1 | grep -q succeeded && echo '    ✅ Redis reachable' || echo '    ⚠️  Redis on Friday not exposed (OK if using Roxy Redis)'

echo ''
echo '=== FRIDAY WORKER STATUS ==='
curl -s http://10.0.0.65:8765/health | python3 -m json.tool 2>/dev/null || echo 'Could not parse health response'