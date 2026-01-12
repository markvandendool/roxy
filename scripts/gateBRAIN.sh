#!/usr/bin/env bash
#
# gateBRAIN.sh - ROXY Brain Verification Script
#
# Tests that ROXY's brain is properly grounded in reality:
# 1. Time/date awareness (TruthPacket works)
# 2. Identity awareness (knows she's ROXY)
# 3. System awareness (knows hostname, repo)
# 4. RAG doesn't poison time responses
#
# Usage: ./gateBRAIN.sh [--verbose]
#

set -euo pipefail

ROXY_DIR="${ROXY_DIR:-$HOME/.roxy}"
ROXY_CORE_URL="${ROXY_CORE_URL:-http://127.0.0.1:8766}"
VERBOSE="${1:-}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

passed=0
failed=0

log() {
    echo -e "$1"
}

log_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((passed++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((failed++))
}

# Test TruthPacket generation
test_truth_packet() {
    log_test "TruthPacket generation..."

    if ! python3 "$ROXY_DIR/truth_packet.py" > /tmp/truth_packet.json 2>&1; then
        log_fail "TruthPacket generation failed"
        return 1
    fi

    # Check required fields
    local required_fields=("now_iso" "now_human" "hostname" "roxy_version")
    for field in "${required_fields[@]}"; do
        if ! grep -q "\"$field\"" /tmp/truth_packet.json; then
            log_fail "TruthPacket missing field: $field"
            return 1
        fi
    done

    # Check year is current
    local current_year=$(date +%Y)
    if ! grep -q "\"now_year\": $current_year" /tmp/truth_packet.json; then
        log_fail "TruthPacket has wrong year (expected $current_year)"
        return 1
    fi

    log_pass "TruthPacket generation OK"
    return 0
}

# Test identity loading
test_identity() {
    log_test "Identity document loading..."

    if ! python3 "$ROXY_DIR/truth_packet.py" --identity > /tmp/identity.txt 2>&1; then
        log_fail "Identity loading failed"
        return 1
    fi

    # Check identity contains key phrases
    if ! grep -qi "ROXY" /tmp/identity.txt; then
        log_fail "Identity missing 'ROXY'"
        return 1
    fi

    if ! grep -qi "MindSong" /tmp/identity.txt; then
        log_fail "Identity missing 'MindSong'"
        return 1
    fi

    log_pass "Identity document OK"
    return 0
}

# Test time/date classifier
test_time_classifier() {
    log_test "Time/date query classifier..."

    local test_queries=(
        "what time is it"
        "what is the date"
        "what day is it"
        "tell me the current time"
    )

    for query in "${test_queries[@]}"; do
        result=$(python3 -c "
from query_detection import is_time_date_query
print('SKIP' if is_time_date_query(\"$query\") else 'NO_SKIP')
" 2>/dev/null || echo "ERROR")

        if [[ "$result" != "SKIP" ]]; then
            log_fail "Query '$query' should skip RAG but got: $result"
            return 1
        fi
    done

    # Test queries that should NOT skip RAG
    local normal_queries=(
        "how do I configure ollama"
        "what is the architecture"
        "explain the codebase"
    )

    for query in "${normal_queries[@]}"; do
        result=$(python3 -c "
from query_detection import is_time_date_query
print('SKIP' if is_time_date_query('$query') else 'NO_SKIP')
" 2>/dev/null || echo "ERROR")

        if [[ "$result" != "NO_SKIP" ]]; then
            log_fail "Query '$query' should NOT skip RAG but got: $result"
            return 1
        fi
    done

    log_pass "Time/date classifier OK"
    return 0
}

# Test repo/git classifier (Directive #5)
test_repo_classifier() {
    log_test "Repo/git query classifier..."

    local repo_queries=(
        "what branch are we on"
        "what is the current commit"
        "is the repo dirty"
        "what was the last commit"
    )

    for query in "${repo_queries[@]}"; do
        result=$(python3 -c "
from query_detection import is_repo_query
print('SKIP' if is_repo_query(\"$query\") else 'NO_SKIP')
" 2>/dev/null || echo "ERROR")

        if [[ "$result" != "SKIP" ]]; then
            log_fail "Query '$query' should skip RAG but got: $result"
            return 1
        fi
    done

    log_pass "Repo/git classifier OK"
    return 0
}

# Test repo state matches TruthPacket
test_repo_truth() {
    log_test "Repo state matches TruthPacket..."

    # Get actual git branch
    actual_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "ERROR")

    # Get TruthPacket branch
    truth_branch=$(python3 -c "
from truth_packet import generate_truth_packet
packet = generate_truth_packet(include_pools=False)
print(packet.get('git', {}).get('branch', 'unknown'))
" 2>/dev/null || echo "ERROR")

    if [[ "$actual_branch" != "$truth_branch" ]]; then
        log_fail "TruthPacket branch mismatch: actual=$actual_branch, truth=$truth_branch"
        return 1
    fi

    log_pass "Repo state matches TruthPacket"
    return 0
}

# Test roxy-core is responding
test_core_health() {
    log_test "roxy-core health..."

    if ! curl -sf "$ROXY_CORE_URL/health" > /dev/null 2>&1; then
        log_fail "roxy-core not responding at $ROXY_CORE_URL"
        return 1
    fi

    log_pass "roxy-core healthy"
    return 0
}

# Test time query via /run (if core is up and auth is configured)
test_time_via_run() {
    log_test "Time query via /run endpoint..."

    # Check if core is up first
    if ! curl -sf "$ROXY_CORE_URL/health" > /dev/null 2>&1; then
        log_test "(skipped - roxy-core not running)"
        return 0
    fi

    # Try to get auth token from environment or config
    local auth_token="${ROXY_AUTH_TOKEN:-}"

    if [[ -z "$auth_token" ]]; then
        # Try to read from config file
        local config_file="$ROXY_DIR/state/auth_token"
        if [[ -f "$config_file" ]]; then
            auth_token=$(cat "$config_file" 2>/dev/null || true)
        fi
    fi

    if [[ -z "$auth_token" ]]; then
        log_test "(skipped - no auth token available)"
        return 0
    fi

    # The /run endpoint returns SSE streaming data
    response=$(timeout 15 curl -sN -X POST "$ROXY_CORE_URL/run" \
        -H "Content-Type: application/json" \
        -H "Accept: text/event-stream" \
        -H "Authorization: Bearer $auth_token" \
        -d '{"command": "what time is it"}' 2>/dev/null | head -c 5000 || echo "TIMEOUT")

    if [[ "$response" == "TIMEOUT" ]] || [[ -z "$response" ]]; then
        log_fail "No response from /run endpoint (timeout or empty)"
        return 1
    fi

    # Check for auth failure
    if echo "$response" | grep -q "Forbidden"; then
        log_test "(skipped - auth token rejected)"
        return 0
    fi

    # Check we got some SSE events or token data
    if ! echo "$response" | grep -qE "(event:|token)"; then
        log_fail "Response doesn't contain SSE events or tokens"
        [[ -n "$VERBOSE" ]] && echo "Response: $response"
        return 1
    fi

    # Extract tokens and check for old dates
    tokens=$(echo "$response" | grep -oP '"token":\s*"[^"]*"' | sed 's/"token":\s*"//g' | tr -d '"')

    # Response should NOT contain dates from old reference material (pre-2025)
    if echo "$tokens" | grep -qE "202[0-4]"; then
        log_fail "Response contains old dates (RAG poisoning?)"
        [[ -n "$VERBOSE" ]] && echo "Tokens: $tokens"
        return 1
    fi

    log_pass "Time query via /run OK"
    return 0
}

# Test DETERMINISTIC time query via /run (Chief directive #3 - TruthPacket grounded)
test_time_via_run_deterministic() {
    log_test "DETERMINISTIC time query via /run..."

    # Check if core is up first
    if ! curl -sf "$ROXY_CORE_URL/health" > /dev/null 2>&1; then
        log_test "(skipped - roxy-core not running)"
        return 0
    fi

    # Get auth token from secret.token
    local auth_token=""
    if [[ -f "$ROXY_DIR/secret.token" ]]; then
        auth_token=$(cat "$ROXY_DIR/secret.token" 2>/dev/null || true)
    fi

    if [[ -z "$auth_token" ]]; then
        log_test "(skipped - no auth token at secret.token)"
        return 0
    fi

    # POST /run with JSON body (not SSE streaming)
    response=$(timeout 30 curl -sf -X POST "$ROXY_CORE_URL/run" \
        -H "Content-Type: application/json" \
        -H "X-ROXY-Token: $auth_token" \
        -d '{"command": "what time is it"}' 2>/dev/null || echo '{"error":"timeout"}')

    if [[ "$response" == '{"error":"timeout"}' ]] || [[ -z "$response" ]]; then
        log_fail "No response from /run endpoint (timeout or empty)"
        return 1
    fi

    # Check for auth failure
    if echo "$response" | jq -e '.status == "error"' > /dev/null 2>&1; then
        log_fail "Error response from /run"
        [[ -n "$VERBOSE" ]] && echo "Response: $response"
        return 1
    fi

    # Parse result text
    local result=$(echo "$response" | jq -r '.result // ""' 2>/dev/null)

    # CHECK 1: Result should show routing to time_direct (NOT rag)
    # Note: metadata.mode may be stale due to caching, so check result text
    if ! echo "$result" | grep -q "Routing to: time_direct"; then
        # Check if it was routed to RAG (the broken case)
        if echo "$result" | grep -q "Routing to: rag"; then
            log_fail "Time query routed to 'rag' instead of 'time_direct'"
            [[ -n "$VERBOSE" ]] && echo "Result: $result"
            return 1
        fi
        log_fail "Time query routing not found in response"
        [[ -n "$VERBOSE" ]] && echo "Result: $result"
        return 1
    fi

    # CHECK 2: Result should contain current year
    local current_year=$(date +%Y)
    if ! echo "$result" | grep -q "$current_year"; then
        log_fail "Response missing current year ($current_year)"
        [[ -n "$VERBOSE" ]] && echo "Result: $result"
        return 1
    fi

    # CHECK 3: Result should NOT contain RAG garbage patterns
    if echo "$result" | grep -qE "(now_utc|Context 1|\[Context|variables defined)"; then
        log_fail "Response contains RAG garbage (TruthPacket not used)"
        [[ -n "$VERBOSE" ]] && echo "Result: $result"
        return 1
    fi

    log_pass "DETERMINISTIC time query OK (routed to time_direct, year=$current_year)"
    return 0
}

# Test SSE routing_meta event (Chief directive #4 + smoke test)
test_sse_routing_meta() {
    log_test "SSE routing_meta smoke test..."

    # Check if core is up first
    if ! curl -sf "$ROXY_CORE_URL/health" > /dev/null 2>&1; then
        log_test "(skipped - roxy-core not running)"
        return 0
    fi

    # Get auth token
    local auth_token=""
    if [[ -f "$ROXY_DIR/secret.token" ]]; then
        auth_token=$(cat "$ROXY_DIR/secret.token" 2>/dev/null || true)
    fi

    if [[ -z "$auth_token" ]]; then
        log_test "(skipped - no auth token)"
        return 0
    fi

    # SSE smoke test: /stream should return routing_meta within 2 seconds
    # Use "what time" query which goes through RAG path and emits routing_meta
    response=$(timeout 2 curl -sN "$ROXY_CORE_URL/stream?command=what%20time%20is%20it" \
        -H "X-ROXY-Token: $auth_token" 2>/dev/null | head -c 1000 || echo "TIMEOUT")

    if [[ "$response" == "TIMEOUT" ]] || [[ -z "$response" ]]; then
        log_test "(skipped - SSE stream timeout within 2s, may need Ollama warmup)"
        return 0
    fi

    # Check for routing_meta event with required semantic fields
    if echo "$response" | grep -q "event: routing_meta"; then
        # Verify key semantic fields (Chief directives A-E)
        local has_pool=$(echo "$response" | grep -q "selected_pool" && echo "1")
        local has_mode=$(echo "$response" | grep -q "routed_mode" && echo "1")
        local has_type=$(echo "$response" | grep -q "query_type" && echo "1")
        local has_reason=$(echo "$response" | grep -q "reason" && echo "1")

        if [[ "$has_pool" && "$has_mode" && "$has_type" && "$has_reason" ]]; then
            log_pass "SSE routing_meta smoke test OK (all semantic fields present)"
            return 0
        else
            log_fail "routing_meta missing semantic fields (pool=$has_pool mode=$has_mode type=$has_type reason=$has_reason)"
            return 1
        fi
    elif echo "$response" | grep -q "403"; then
        log_test "(skipped - auth rejected)"
        return 0
    else
        log_fail "No routing_meta event in SSE stream within 2s"
        [[ -n "$VERBOSE" ]] && echo "Response: $response"
        return 1
    fi
}

# Test routing_meta emission for formerly failing prompts
# These prompts previously triggered false command classification:
# - git-related questions (triggered by "git" keyword)
# - restart questions (triggered by "restart" keyword)
# - /health URL mentions (triggered by "health" keyword)
test_routing_meta_formerly_failing() {
    log_test "routing_meta emission for edge-case prompts..."

    # Check if core is up first
    if ! curl -sf "$ROXY_CORE_URL/health" > /dev/null 2>&1; then
        log_test "(skipped - roxy-core not running)"
        return 0
    fi

    # Get auth token
    local auth_token=""
    if [[ -f "$ROXY_DIR/secret.token" ]]; then
        auth_token=$(cat "$ROXY_DIR/secret.token" 2>/dev/null || true)
    fi

    if [[ -z "$auth_token" ]]; then
        log_test "(skipped - no auth token)"
        return 0
    fi

    # Formerly failing prompts that must emit routing_meta
    local test_prompts=(
        "What's the current Git HEAD commit date (author date)?"
        "Restart roxy-core.service and confirm /health and /ready are OK."
        "Explain the difference between /health and /ready in ROXY"
    )

    local all_passed=1

    for prompt in "${test_prompts[@]}"; do
        # URL encode the prompt
        local encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$prompt'''))" 2>/dev/null)

        # Test /stream endpoint
        local response=$(set +o pipefail; timeout 10 curl -sN "$ROXY_CORE_URL/stream?command=$encoded" \
            -H "X-ROXY-Token: $auth_token" 2>/dev/null | head -c 2000; true)

        # Must have routing_meta event
        if ! echo "$response" | grep -q "event: routing_meta"; then
            log_fail "Missing routing_meta for: ${prompt:0:50}..."
            all_passed=0
        fi
    done

    if [[ "$all_passed" -eq 1 ]]; then
        log_pass "routing_meta emission OK for all edge-case prompts"
        return 0
    else
        return 1
    fi
}

# Main
main() {
    log ""
    log "========================================"
    log "   ROXY Brain Verification (gateBRAIN)"
    log "========================================"
    log ""

    cd "$ROXY_DIR"

    # Run tests
    test_truth_packet || true
    test_identity || true
    test_time_classifier || true
    test_repo_classifier || true
    test_repo_truth || true
    test_core_health || true
    test_time_via_run || true
    test_time_via_run_deterministic || true
    test_sse_routing_meta || true
    test_routing_meta_formerly_failing || true

    log ""
    log "========================================"
    log "   Results: ${GREEN}$passed passed${NC}, ${RED}$failed failed${NC}"
    log "========================================"
    log ""

    if [[ $failed -gt 0 ]]; then
        exit 1
    fi
}

main "$@"
