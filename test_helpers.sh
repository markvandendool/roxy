#!/bin/bash
# PHASE 1: Request Encoding Fix
# Uses jq for JSON construction (eliminates manual escaping bugs)

ROXY_TOKEN=$(cat ~/.roxy/secret.token)
ROXY_URL="http://127.0.0.1:8766/run"

# Safe command sender (jq-based JSON, no manual escaping)
roxy_cmd() {
    local cmd="$1"
    jq -n --arg c "$cmd" '{command:$c}' | \
    curl -s -m 10 \
        -H "X-ROXY-Token: $ROXY_TOKEN" \
        -H "Content-Type: application/json" \
        -d @- "$ROXY_URL"
}

# Tool forcing helper (simple version)
roxy_tool() {
    local tool="$1"
    local json_args="$2"  # Must be valid JSON object
    echo "{\"tool\": \"$tool\", \"args\": $json_args}" | \
    curl -s -m 10 \
        -H "X-ROXY-Token: $ROXY_TOKEN" \
        -H "Content-Type: application/json" \
        -d @- "$ROXY_URL"
}

# Test cases
test_capabilities() {
    echo "TEST: Capabilities"
    roxy_cmd "what are your capabilities" | jq -r '.result' | head -10
}

test_tool_forcing() {
    echo "TEST: Tool Forcing - list_files"
    roxy_tool "list_files" '{"directory": "'$HOME'/.roxy"}' | jq -r '.result' | head -10
}

test_blocked_browser() {
    echo "TEST: Blocked Browser"
    roxy_cmd "open firefox to google.com" | jq -r '.result'
}

test_rag_query() {
    echo "TEST: RAG Query"
    roxy_cmd "What is the dual-stack problem?" | jq -r '.result' | head -15
}

# Export for use in other scripts
export -f roxy_cmd roxy_tool
