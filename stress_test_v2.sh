#!/bin/bash
# STRESS TEST V2: Comprehensive validation using jq-based JSON (Phase 1)
# Success criteria: 100% pass rate, zero timeouts, zero JSON errors

set -o pipefail  # Only exit on pipe failures, not test failures

ROXY_TOKEN=$(cat ~/.roxy/secret.token)
ROXY_URL="http://127.0.0.1:8766/run"
PASS=0
FAIL=0

# Test runner
run_test() {
    local name="$1"
    local command="$2"
    local expected_pattern="$3"
    
    echo -n "TEST: $name ... "
    
    local response=$(jq -n --arg c "$command" '{command:$c}' | \
        curl -s -m 10 \
            -H "X-ROXY-Token: $ROXY_TOKEN" \
            -H "Content-Type: application/json" \
            -d @- "$ROXY_URL" 2>&1)
    
    if echo "$response" | grep -qP "$expected_pattern"; then
        echo "✅ PASS"
        ((PASS++))
        return 0
    else
        echo "❌ FAIL"
        echo "  Response: ${response:0:200}"
        ((FAIL++))
        return 1
    fi
}

# Tool forcing test
run_tool_test() {
    local name="$1"
    local tool="$2"
    local args_json="$3"
    local expected_pattern="$4"
    
    echo -n "TOOL TEST: $name ... "
    
    local tool_command="{\"tool\": \"$tool\", \"args\": $args_json}"
    local response=$(jq -n --arg c "$tool_command" '{command:$c}' | \
        curl -s -m 10 \
            -H "X-ROXY-Token: $ROXY_TOKEN" \
            -H "Content-Type: application/json" \
            -d @- "$ROXY_URL" 2>&1)
    
    if echo "$response" | grep -qP "$expected_pattern"; then
        echo "✅ PASS"
        ((PASS++))
        return 0
    else
        echo "❌ FAIL"
        echo "  Response: ${response:0:200}"
        ((FAIL++))
        return 1
    fi
}

echo "=== ROXY STRESS TEST V2 ==="
echo "Phase 1: Request Encoding (jq-based JSON)"
echo ""

# 1. Health check
run_test "Health endpoint" \
    "ping" \
    "pong|ok|success"

# 2. Capabilities
run_test "Capabilities query" \
    "what are your capabilities" \
    "AVAILABLE|llama3|Tools"

# 3. Tool forcing - list_files
run_tool_test "Tool Direct: list_files" \
    "list_files" \
    '{"directory": "/home/mark/.roxy"}' \
    "roxy_core.py|config.json"

# 4. Tool forcing - read_file (first 5 lines)
run_tool_test "Tool Direct: read_file" \
    "read_file" \
    '{"file_path": "/home/mark/.roxy/config.json", "max_lines": 5}' \
    "repo_roots|default_model|allowed_tools"

# 5. Blocked browser
run_test "Block browser (no tool)" \
    "open firefox to google.com" \
    "BROWSER CONTROL NOT AVAILABLE|NO TOOL"

# 6. Blocked shell
run_test "Block shell (disabled)" \
    "run command: ls -la" \
    "Security policy|disabled by default"

# 7. RAG query
run_test "RAG query" \
    "What is ROXY's architecture?" \
    "Processing|Routing|success|result"

# 8. Special characters in command
run_test "Special chars (quotes)" \
    'echo "hello world" with <brackets> and $symbols' \
    "success|result"

# 9. Long command
run_test "Long command (200 chars)" \
    "This is a very long command intended to test the handling of large inputs with many words and characters to ensure the JSON encoding properly escapes everything without breaking the parser or causing timeouts in the system" \
    "success|result"

# 10. Concurrent requests (3 parallel)
echo -n "CONCURRENT TEST: 3 parallel requests ... "
(jq -n '{command:"ping"}' | curl -s -m 10 -H "X-ROXY-Token: $ROXY_TOKEN" -d @- "$ROXY_URL" > /tmp/roxy_concurrent_1.txt 2>&1) &
(jq -n '{command:"what are your capabilities"}' | curl -s -m 10 -H "X-ROXY-Token: $ROXY_TOKEN" -d @- "$ROXY_URL" > /tmp/roxy_concurrent_2.txt 2>&1) &
(jq -n --arg c '{"tool": "list_files", "args": {"directory": "/home/mark/.roxy"}}' '{command:$c}' | curl -s -m 10 -H "X-ROXY-Token: $ROXY_TOKEN" -d @- "$ROXY_URL" > /tmp/roxy_concurrent_3.txt 2>&1) &
wait

if grep -q "success" /tmp/roxy_concurrent_1.txt && \
   grep -q "AVAILABLE" /tmp/roxy_concurrent_2.txt && \
   grep -q "roxy_core" /tmp/roxy_concurrent_3.txt; then
    echo "✅ PASS"
    ((PASS++))
else
    echo "❌ FAIL"
    ((FAIL++))
fi

# 11. Rapid fire (10 requests back-to-back)
echo -n "RAPID FIRE TEST: 10 sequential requests ... "
RAPID_FAIL=0
for i in {1..10}; do
    response=$(jq -n '{command:"ping"}' | curl -s -m 5 -H "X-ROXY-Token: $ROXY_TOKEN" -d @- "$ROXY_URL" 2>&1)
    if ! echo "$response" | grep -q "success"; then
        ((RAPID_FAIL++))
    fi
done
if [ $RAPID_FAIL -eq 0 ]; then
    echo "✅ PASS (10/10)"
    ((PASS++))
else
    echo "❌ FAIL ($((10-RAPID_FAIL))/10 succeeded)"
    ((FAIL++))
fi

# 12. Invalid JSON (should fail gracefully)
echo -n "ERROR HANDLING TEST: Invalid JSON ... "
response=$(echo 'not valid json' | curl -s -m 5 -H "X-ROXY-Token: $ROXY_TOKEN" -d @- "$ROXY_URL" 2>&1)
if echo "$response" | grep -qE "error|Error|500"; then
    echo "✅ PASS (graceful error)"
    ((PASS++))
else
    echo "❌ FAIL (should return error)"
    ((FAIL++))
fi

# 13. Missing token (should deny)
echo -n "AUTH TEST: Missing token ... "
response=$(jq -n '{command:"ping"}' | curl -s -m 5 -d @- "$ROXY_URL" 2>&1)
if echo "$response" | grep -qE "403|Forbidden|Invalid"; then
    echo "✅ PASS (denied)"
    ((PASS++))
else
    echo "❌ FAIL (should deny)"
    ((FAIL++))
fi

# 14. RUN_TOOL syntax (alternative to JSON)
run_test "RUN_TOOL syntax" \
    'RUN_TOOL list_files {"directory": "/home/mark/.roxy"}' \
    "roxy_core.py|config.json"

echo ""
echo "=== RESULTS ==="
echo "PASS: $PASS/14"
echo "FAIL: $FAIL/14"
echo "SUCCESS RATE: $(( PASS * 100 / 14 ))%"

# Check service logs for errors
echo ""
echo "=== SERVICE HEALTH ==="
ERROR_COUNT=$(journalctl --user -u roxy-core --since "5 minutes ago" --no-pager | grep ERROR | grep -v "Invalid JSON test" | wc -l || echo "0")
echo "Unexpected errors in last 5 min: $ERROR_COUNT"

if [ $FAIL -eq 0 ] && [ $ERROR_COUNT -eq 0 ]; then
    echo ""
    echo "🎉 ALL TESTS PASSED - Phase 1 SUCCESS"
    exit 0
else
    echo ""
    echo "⚠️ SOME TESTS FAILED - Review output above"
    exit 1
fi
