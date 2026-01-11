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
from streaming import is_time_date_query
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
from streaming import is_time_date_query
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
    test_core_health || true
    test_time_via_run || true

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
