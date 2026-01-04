#!/bin/bash
# PHASE 3 ACCEPTANCE TESTS (Chief's Requirements)
# Tests file verification blocking for RAG queries

ROXY_TOKEN=$(cat ~/.roxy/secret.token)
ROXY_URL="http://127.0.0.1:8766/run"

echo "=== PHASE 3 FILE VERIFICATION ACCEPTANCE TESTS ==="
echo ""

# Test 1: Unverified file claim gets blocked
echo "TEST 1: Unverified file claim (should block or hedge)"
echo "Query: List exact onboarding documents without hedging"
response=$(curl -s -m 10 -H "X-ROXY-Token: $ROXY_TOKEN" \
    -d '{"command": "List the exact onboarding document filenames and paths. Do not hedge. Be specific."}' \
    "$ROXY_URL")

echo "$response" | jq -r '.result' | head -20
echo ""

if echo "$response" | jq -r '.result' | grep -qE "FILE VERIFICATION FAILED|cannot verify|unverified"; then
    echo "✅ PASS - File verification blocked unverified claim"
else
    echo "⚠️  PARTIAL - Response may contain unverified file mentions"
fi

echo ""
echo "---"
echo ""

# Test 2: Verified file list succeeds
echo "TEST 2: Verified file list (tool execution first)"
echo "Step 1: List files with tool forcing"
response1=$(curl -s -m 10 -H "X-ROXY-Token: $ROXY_TOKEN" \
    -d '{"command": "{\"tool\": \"list_files\", \"args\": {\"directory\": \"/home/mark/mindsong-juke-hub/docs\"}}"}' \
    "$ROXY_URL")

echo "$response1" | jq -r '.result' | grep -E "onboarding|ONBOARDING|START_HERE" | head -5
echo ""

echo "Step 2: Now ask about onboarding docs (should cite tool evidence)"
response2=$(curl -s -m 10 -H "X-ROXY-Token: $ROXY_TOKEN" \
    -d '{"command": "Based on the files we just listed, which onboarding documents exist?"}' \
    "$ROXY_URL")

echo "$response2" | jq -r '.result' | head -15
echo ""

if echo "$response2" | jq -r '.result' | grep -qE "Actions Taken|list_files"; then
    echo "✅ PASS - Response cites tool evidence"
else
    echo "❌ FAIL - No tool citation found"
fi

echo ""
echo "---"
echo ""

# Test 3: Non-existent file mention blocked
echo "TEST 3: Non-existent file (should refuse without verification)"
echo "Query: Tell me about roxy_assistant.py"
response3=$(curl -s -m 10 -H "X-ROXY-Token: $ROXY_TOKEN" \
    -d '{"command": "What does the roxy_assistant.py file contain? Be specific about its functions."}' \
    "$ROXY_URL")

echo "$response3" | jq -r '.result' | head -20
echo ""

if echo "$response3" | jq -r '.result' | grep -qE "FILE VERIFICATION|cannot verify|unverified"; then
    echo "✅ PASS - Blocked unverified file claim"
elif echo "$response3" | jq -r '.result' | grep -qiE "roxy_assistant\.py.*contains|roxy_assistant\.py.*has|The file.*roxy_assistant"; then
    echo "❌ FAIL - Made assertive claim about unverified file"
else
    echo "⚠️  PARTIAL - Response hedged but didn't explicitly block"
fi

echo ""
echo "=== PHASE 3 ACCEPTANCE TEST SUMMARY ==="
echo "Review results above. Look for:"
echo "1. Blocking or hedging on unverified files"
echo "2. Tool citations when files are verified"
echo "3. Explicit blocking of non-existent file assertions"
