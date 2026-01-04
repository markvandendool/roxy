#!/bin/bash
# STRESS TEST V3: CHIEF-GRADE VALIDATION
# - Log cursor markers for clean-run verification
# - Error whitelisting for expected failures
# - Structured JSON validation (not text grepping)
# - Load testing to characterize intermittents

set -o pipefail

ROXY_TOKEN=$(cat ~/.roxy/secret.token)
ROXY_URL="http://127.0.0.1:8766/run"
PASS=0
FAIL=0

# Capture start timestamp for log delta
START_TS=$(date --iso-8601=seconds)
echo "=== CHIEF-GRADE STRESS TEST V3 ==="
echo "Start time: $START_TS"
echo ""

# Whitelisted error signatures (expected failures)
WHITELIST_ERRORS=(
    "Expecting value: line 1 column 1"  # Invalid JSON test
)

# Test runner with structured validation
run_test() {
    local name="$1"
    local command="$2"
    shift 2  # Remove first two args
    local validator_and_args=("$@")  # Remaining args are validator + its args
    
    echo -n "TEST: $name ... "
    
    local response=$(jq -n --arg c "$command" '{command:$c}' | \
        curl -s -m 10 \
            -H "X-ROXY-Token: $ROXY_TOKEN" \
            -H "Content-Type: application/json" \
            -d @- "$ROXY_URL" 2>&1)
    
    # Call validator with response as first arg, plus any additional args
    # Debug: echo "DEBUG: Calling ${validator_and_args[@]} with response" >> /tmp/test_debug.log
    if "${validator_and_args[0]}" "$response" "${validator_and_args[@]:1}" 2>/tmp/validator_error.txt; then
        echo "✅ PASS"
        ((PASS++))
        return 0
    else
        echo "❌ FAIL"
        if [ -s /tmp/validator_error.txt ]; then
            echo "  Validator error: $(cat /tmp/validator_error.txt | head -1)"
        fi
        echo "  Response: ${response:0:300}"
        ((FAIL++))
        return 1
    fi
}

# Validators (structured JSON checks)
validate_success() {
    echo "$1" | jq -e '.status == "success"' &>/dev/null
}

validate_has_result() {
    echo "$1" | jq -e '.result' &>/dev/null
}

validate_contains() {
    local response="$1"
    local pattern="$2"
    # Simple string containment check (avoid regex issues)
    echo "$response" | jq -r '.result' 2>/dev/null | grep -qF "$pattern"
}

validate_tool_executed() {
    local response="$1"
    local tool_name="$2"
    # Check if result contains tool routing evidence
    echo "$response" | jq -r '.result' 2>/dev/null | grep -qE "Routing to: (tool_direct|$tool_name)"
}

validate_error_403() {
    echo "$1" | grep -qE "403|Forbidden|Invalid"
}

validate_error_graceful() {
    echo "$1" | jq -e '.status == "error"' &>/dev/null || echo "$1" | grep -qE "error|Error|500"
}

# === BASIC FUNCTIONALITY TESTS ===
echo "=== PHASE 1: BASIC FUNCTIONALITY ==="

run_test "Health endpoint" \
    "ping" \
    validate_success

run_test "Capabilities query" \
    "what are your capabilities" \
    validate_has_result

# === TOOL FORCING TESTS ===
echo ""
echo "=== PHASE 2: TOOL FORCING ==="

run_test "Tool Direct: list_files" \
    '{"tool": "list_files", "args": {"path": "/home/mark/.roxy"}}' \
    validate_contains "roxy_core.py"

run_test "Tool Direct: read_file" \
    '{"tool": "read_file", "args": {"file_path": "/home/mark/.roxy/config.json", "max_lines": 5}}' \
    validate_contains "repo_roots"

run_test "RUN_TOOL syntax" \
    'RUN_TOOL list_files {"path": "/home/mark/.roxy"}' \
    validate_contains "config.json"

# === SAFETY TESTS ===
echo ""
echo "=== PHASE 3: SAFETY ENVELOPE ==="

run_test "Block browser (no tool)" \
    "open firefox to google.com" \
    validate_contains "BROWSER CONTROL NOT AVAILABLE"

run_test "Block shell (disabled)" \
    "run command: ls -la" \
    validate_contains "disabled"

# === EDGE CASES ===
echo ""
echo "=== PHASE 4: EDGE CASES ==="

run_test "Special chars (quotes/brackets)" \
    'echo "hello world" with <brackets> and $symbols' \
    validate_success

run_test "Long command (200 chars)" \
    "This is a very long command intended to test the handling of large inputs with many words and characters to ensure the JSON encoding properly escapes everything without breaking the parser or causing timeouts in the system" \
    validate_success

# === ERROR HANDLING ===
echo ""
echo "=== PHASE 5: ERROR HANDLING ==="

echo -n "TEST: Invalid JSON (graceful error) ... "
response=$(echo 'not valid json' | curl -s -m 5 -H "X-ROXY-Token: $ROXY_TOKEN" -d @- "$ROXY_URL" 2>&1)
if validate_error_graceful "$response"; then
    echo "✅ PASS"
    ((PASS++))
else
    echo "❌ FAIL"
    ((FAIL++))
fi

echo -n "TEST: Missing token (403 denied) ... "
response=$(jq -n '{command:"ping"}' | curl -s -m 5 -d @- "$ROXY_URL" 2>&1)
if validate_error_403 "$response"; then
    echo "✅ PASS"
    ((PASS++))
else
    echo "❌ FAIL"
    ((FAIL++))
fi

# === LOAD TESTS (characterize intermittents) ===
echo ""
echo "=== PHASE 6: LOAD CHARACTERIZATION ==="

# Concurrent requests
echo -n "LOAD TEST: 3 parallel requests ... "
(jq -n '{command:"ping"}' | curl -s -m 10 -H "X-ROXY-Token: $ROXY_TOKEN" -d @- "$ROXY_URL" > /tmp/roxy_load_1.txt 2>&1) &
(jq -n '{command:"what are your capabilities"}' | curl -s -m 10 -H "X-ROXY-Token: $ROXY_TOKEN" -d @- "$ROXY_URL" > /tmp/roxy_load_2.txt 2>&1) &
(jq -n --arg c '{"tool": "list_files", "args": {"path": "/home/mark/.roxy"}}' '{command:$c}' | curl -s -m 10 -H "X-ROXY-Token: $ROXY_TOKEN" -d @- "$ROXY_URL" > /tmp/roxy_load_3.txt 2>&1) &
wait

if grep -q "success" /tmp/roxy_load_1.txt && \
   grep -q "AVAILABLE\|success" /tmp/roxy_load_2.txt && \
   grep -q "roxy_core\|success" /tmp/roxy_load_3.txt; then
    echo "✅ PASS"
    ((PASS++))
else
    echo "❌ FAIL"
    ((FAIL++))
    echo "  Load 1: $(head -100 /tmp/roxy_load_1.txt)"
    echo "  Load 2: $(head -100 /tmp/roxy_load_2.txt)"
    echo "  Load 3: $(head -100 /tmp/roxy_load_3.txt)"
fi

# Rapid fire (50 tool_direct calls to characterize blocking)
echo -n "LOAD TEST: 50 tool_direct calls (back-to-back) ... "
RAPID_FAIL=0
RAPID_START=$(date +%s)
for i in {1..50}; do
    response=$(jq -n '{command:"ping"}' | curl -s -m 5 -H "X-ROXY-Token: $ROXY_TOKEN" -d @- "$ROXY_URL" 2>&1)
    if ! echo "$response" | grep -q "success"; then
        ((RAPID_FAIL++))
    fi
done
RAPID_END=$(date +%s)
RAPID_DURATION=$((RAPID_END - RAPID_START))

if [ $RAPID_FAIL -eq 0 ]; then
    echo "✅ PASS (50/50 in ${RAPID_DURATION}s)"
    ((PASS++))
else
    echo "❌ FAIL ($((50-RAPID_FAIL))/50 succeeded in ${RAPID_DURATION}s)"
    ((FAIL++))
fi

# === RESULTS ===
echo ""
echo "=== RESULTS ==="
TOTAL=$((PASS + FAIL))
echo "PASS: $PASS/$TOTAL"
echo "FAIL: $FAIL/$TOTAL"
if [ $TOTAL -gt 0 ]; then
    echo "SUCCESS RATE: $(( PASS * 100 / TOTAL ))%"
fi

# === LOG DELTA ANALYSIS ===
echo ""
echo "=== SERVICE HEALTH (CLEAN-RUN VERIFICATION) ==="

# Get errors since test start
ERROR_LINES=$(journalctl --user -u roxy-core --since "$START_TS" --no-pager | grep ERROR || echo "")

# Filter out whitelisted errors
UNEXPECTED_ERRORS=""
while IFS= read -r line; do
    is_whitelisted=false
    for pattern in "${WHITELIST_ERRORS[@]}"; do
        if echo "$line" | grep -qF "$pattern"; then
            is_whitelisted=true
            break
        fi
    done
    if [ "$is_whitelisted" = false ] && [ -n "$line" ]; then
        UNEXPECTED_ERRORS="${UNEXPECTED_ERRORS}${line}\n"
    fi
done <<< "$ERROR_LINES"

if [ -z "$UNEXPECTED_ERRORS" ]; then
    UNEXPECTED_COUNT=0
else
    UNEXPECTED_COUNT=$(echo -e "$UNEXPECTED_ERRORS" | grep -c "ERROR")
fi

echo "Errors since $START_TS: $(echo "$ERROR_LINES" | wc -l)"
echo "Whitelisted (expected): $(( $(echo "$ERROR_LINES" | wc -l) - UNEXPECTED_COUNT ))"
echo "Unexpected errors: $UNEXPECTED_COUNT"

if [ $UNEXPECTED_COUNT -gt 0 ]; then
    echo ""
    echo "⚠️  UNEXPECTED ERRORS DETECTED:"
    echo -e "$UNEXPECTED_ERRORS"
fi

# === SINGLE-STACK PROOF ===
echo ""
echo "=== SINGLE-STACK PROOF ==="
echo "Port 8766 listeners (ss):"
ss -H -lptn 'sport = :8766' | tee /tmp/roxy_ss_check.txt
LISTENER_COUNT=$(wc -l < /tmp/roxy_ss_check.txt)
echo "Listener count: $LISTENER_COUNT (must be 1)"

echo ""
echo "Port 8766 listeners (lsof):"
lsof -nP -iTCP:8766 -sTCP:LISTEN 2>/dev/null | tee /tmp/roxy_lsof_check.txt || echo "lsof unavailable"

# === FINAL VERDICT ===
echo ""
if [ $FAIL -eq 0 ] && [ $UNEXPECTED_COUNT -eq 0 ] && [ $LISTENER_COUNT -eq 1 ]; then
    echo "🎉 CHIEF-GRADE VALIDATION PASSED"
    echo "   - All tests passed"
    echo "   - Zero unexpected errors"
    echo "   - Single listener verified"
    exit 0
else
    echo "⚠️  VALIDATION FAILED"
    [ $FAIL -gt 0 ] && echo "   - $FAIL test failures"
    [ $UNEXPECTED_COUNT -gt 0 ] && echo "   - $UNEXPECTED_COUNT unexpected errors"
    [ $LISTENER_COUNT -ne 1 ] && echo "   - Multiple listeners detected ($LISTENER_COUNT)"
    exit 1
fi
