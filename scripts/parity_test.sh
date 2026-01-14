#!/usr/bin/env bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
#
# parity_test.sh - ROXY /run vs /stream Parity Test
# Compares truth query answers between endpoints
#
set -euo pipefail

ROXY_DIR="${ROXY_DIR:-$HOME/.roxy}"
ROXY_CORE_URL="${ROXY_CORE_URL:-http://127.0.0.1:8766}"
TOKEN=$(cat "$ROXY_DIR/secret.token")

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

PASS=0
FAIL=0

check_parity() {
    local prompt="$1"
    local check_field="$2"  # year, branch, etc.

    echo -n "Parity: '$prompt' ... "

    # Get /run result
    local run_response run_result
    run_response=$(curl -sf -X POST "$ROXY_CORE_URL/run" \
        -H "X-ROXY-Token: $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"command\": \"$prompt\"}" \
        --max-time 30 2>/dev/null) || run_response='{"error":"failed"}'
    run_result=$(echo "$run_response" | jq -r '.result // ""' 2>/dev/null)

    # Get /stream result (collect tokens)
    local encoded stream_response stream_tokens
    encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$prompt'))")
    stream_response=$(timeout 15 curl -sN "$ROXY_CORE_URL/stream?command=$encoded" \
        -H "X-ROXY-Token: $TOKEN" 2>/dev/null | head -c 5000) || stream_response=""

    # Extract tokens from stream
    stream_tokens=$(echo "$stream_response" | grep "event: token" -A1 | grep "^data:" | \
        sed 's/^data: //' | jq -r '.token // ""' 2>/dev/null | tr -d '\n')

    # Check parity based on field
    local run_has stream_has
    case "$check_field" in
        year)
            local current_year
            current_year=$(date +%Y)
            run_has=$(echo "$run_result" | grep -c "$current_year" || echo "0")
            stream_has=$(echo "$stream_tokens" | grep -c "$current_year" || echo "0")
            ;;
        branch)
            run_has=$(echo "$run_result" | grep -c "main\|master" || echo "0")
            stream_has=$(echo "$stream_tokens" | grep -c "main\|master" || echo "0")
            ;;
        *)
            run_has="1"
            stream_has="1"
            ;;
    esac

    if [[ "$run_has" -gt 0 ]] && [[ "$stream_has" -gt 0 ]]; then
        echo -e "${GREEN}PASS${NC} (both contain $check_field)"
        ((PASS++))
    elif [[ "$run_has" -gt 0 ]] && [[ "$stream_has" -eq 0 ]]; then
        echo -e "${RED}FAIL${NC} (/run has $check_field, /stream missing)"
        ((FAIL++))
    elif [[ "$run_has" -eq 0 ]] && [[ "$stream_has" -gt 0 ]]; then
        echo -e "${RED}FAIL${NC} (/stream has $check_field, /run missing)"
        ((FAIL++))
    else
        echo -e "${RED}FAIL${NC} (both missing $check_field)"
        ((FAIL++))
    fi
}

echo ""
echo "========================================"
echo "   ROXY Parity Test (/run vs /stream)"
echo "========================================"
echo ""

# Verify service
if ! curl -sf "$ROXY_CORE_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}ERROR: roxy-core not responding${NC}"
    exit 1
fi

# Time parity tests
check_parity "what time is it" "year"
check_parity "current date" "year"
check_parity "what day is today" "year"

# Repo parity tests (if applicable)
# check_parity "what branch am I on" "branch"

echo ""
echo "========================================"
echo "   Results: ${GREEN}$PASS PASS${NC}, ${RED}$FAIL FAIL${NC}"
echo "========================================"

exit $FAIL