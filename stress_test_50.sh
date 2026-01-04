#!/bin/bash
# ROXY Stress Test - 50 Questions
# Tests greeting fastpath, casual chat, RAG, tools, edge cases

ROXY_URL="http://127.0.0.1:8766/run"
TOKEN=$(cat ~/.roxy/secret.token 2>/dev/null || echo "test-token")
PASS=0
FAIL=0
TIMEOUT=0

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         ROXY STRESS TEST - 50 QUESTIONS                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

send_command() {
    local cmd="$1"
    local test_name="$2"
    local timeout_sec="${3:-15}"
    
    echo -n "[$((PASS + FAIL + TIMEOUT + 1))/50] $test_name... "
    
    response=$(timeout $timeout_sec curl -s -X POST "$ROXY_URL" \
        -H "Content-Type: application/json" \
        -H "X-ROXY-Token: $TOKEN" \
        -d "{\"command\": \"$cmd\"}" 2>&1)
    
    exit_code=$?
    
    if [ $exit_code -eq 124 ]; then
        echo -e "${YELLOW}TIMEOUT${NC}"
        ((TIMEOUT++))
    elif [ $exit_code -ne 0 ] || [ -z "$response" ]; then
        echo -e "${RED}FAIL${NC} (no response)"
        ((FAIL++))
    elif echo "$response" | grep -qi "error\|exception\|traceback"; then
        echo -e "${RED}FAIL${NC} (error in response)"
        ((FAIL++))
    else
        echo -e "${GREEN}PASS${NC}"
        ((PASS++))
    fi
    
    sleep 0.5  # Brief pause between requests
}

# CATEGORY 1: Greeting Fastpath (should be instant)
echo "━━━ CATEGORY 1: Greeting Fastpath ━━━"
send_command "hi" "Greeting: hi" 5
send_command "hello" "Greeting: hello" 5
send_command "hey roxy" "Greeting: hey roxy" 5
send_command "hi roxy" "Greeting: hi roxy" 5
send_command "good morning" "Greeting: good morning" 5
send_command "hello roxy" "Greeting: hello roxy" 5
send_command "sup" "Greeting: sup" 5
send_command "howdy" "Greeting: howdy" 5

# CATEGORY 2: Casual Chat (bypass action validation)
echo ""
echo "━━━ CATEGORY 2: Casual Chat ━━━"
send_command "how are you feeling today?" "Casual: how are you" 10
send_command "tell me a joke" "Casual: joke request" 10
send_command "what do you think about ai?" "Casual: opinion question" 10
send_command "are you ok?" "Casual: wellness check" 10
send_command "tell me something interesting" "Casual: tell me something" 10

# CATEGORY 3: RAG Queries (knowledge retrieval)
echo ""
echo "━━━ CATEGORY 3: RAG Queries ━━━"
send_command "what is the LUNO epoch?" "RAG: LUNO epoch" 15
send_command "tell me about the citadel epic" "RAG: citadel epic" 15
send_command "what is moonshot?" "RAG: moonshot" 15
send_command "what are the current priorities?" "RAG: priorities" 15
send_command "what is the omega system?" "RAG: omega system" 15
send_command "whats been done today on the project?" "RAG: daily progress" 15
send_command "what is the truth gate?" "RAG: truth gate" 15
send_command "explain the context manager" "RAG: context manager" 15
send_command "what is the agent onboarding process?" "RAG: onboarding" 15
send_command "what are the P0 priorities?" "RAG: P0 priorities" 15

# CATEGORY 4: File Operations
echo ""
echo "━━━ CATEGORY 4: File Operations ━━━"
send_command "list files in ~/.roxy" "File: list roxy dir" 10
send_command "show me roxy_core.py" "File: show roxy_core" 10
send_command "read ~/.roxy/config.json" "File: read config" 10
send_command "what files are in the workspace?" "File: workspace files" 10

# CATEGORY 5: Tool Commands
echo ""
echo "━━━ CATEGORY 5: Tool Commands ━━━"
send_command "check if obs is running" "Tool: obs status" 10
send_command "get system info" "Tool: system info" 10
send_command "check disk space" "Tool: disk space" 10

# CATEGORY 6: Multi-turn Context
echo ""
echo "━━━ CATEGORY 6: Context Awareness ━━━"
send_command "what is 2 plus 2?" "Context: simple math" 10
send_command "multiply that by 3" "Context: follow-up math" 10
send_command "tell me about python" "Context: new topic" 10
send_command "give me an example" "Context: follow-up request" 10

# CATEGORY 7: Edge Cases
echo ""
echo "━━━ CATEGORY 7: Edge Cases ━━━"
send_command "" "Edge: empty string" 10
send_command "?" "Edge: single question mark" 10
send_command "asdfjkl;qwer" "Edge: random gibberish" 10
send_command "help" "Edge: help command" 10
send_command "what can you do?" "Edge: capabilities query" 10
send_command "exit" "Edge: exit command" 10

# CATEGORY 8: Complex Queries
echo ""
echo "━━━ CATEGORY 8: Complex Queries ━━━"
send_command "summarize the last week of work" "Complex: weekly summary" 15
send_command "what are all the active epics and their status?" "Complex: epic status" 15
send_command "compare citadel and moonshot priorities" "Complex: comparison" 15
send_command "what needs to be done next?" "Complex: next actions" 15
send_command "who is chief and what did he fix recently?" "Complex: contributor info" 15

# Results Summary
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    TEST RESULTS                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${GREEN}PASSED:${NC}  $PASS"
echo -e "${RED}FAILED:${NC}  $FAIL"
echo -e "${YELLOW}TIMEOUT:${NC} $TIMEOUT"
echo -e "TOTAL:   50"
echo ""

SUCCESS_RATE=$((PASS * 100 / 50))
echo "Success Rate: ${SUCCESS_RATE}%"

if [ $SUCCESS_RATE -ge 90 ]; then
    echo -e "${GREEN}✓ EXCELLENT${NC} - ROXY is performing well!"
elif [ $SUCCESS_RATE -ge 70 ]; then
    echo -e "${YELLOW}⚠ GOOD${NC} - Some issues detected"
else
    echo -e "${RED}✗ NEEDS ATTENTION${NC} - Multiple failures"
fi

exit 0
