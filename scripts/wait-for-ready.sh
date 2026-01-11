#!/usr/bin/env bash
# wait-for-ready.sh - Wait for roxy-core /ready endpoint to return 200
# Usage: ./wait-for-ready.sh [timeout_seconds] [url]
# Exit 0 on success, 1 on timeout/failure

set -euo pipefail

TIMEOUT="${1:-30}"
URL="${2:-http://127.0.0.1:8766/ready}"

echo "Waiting for $URL to become ready (timeout: ${TIMEOUT}s)..."

START=$(date +%s)
while true; do
    NOW=$(date +%s)
    ELAPSED=$((NOW - START))

    if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
        echo "TIMEOUT: /ready did not return 200 within ${TIMEOUT}s"
        # Show last response for debugging
        curl -sS "$URL" 2>&1 || true
        exit 1
    fi

    HTTP_CODE=$(curl -sS -o /dev/null -w '%{http_code}' "$URL" 2>/dev/null || echo "000")

    if [ "$HTTP_CODE" = "200" ]; then
        echo "READY: $URL returned 200 after ${ELAPSED}s"
        exit 0
    fi

    # Show progress every 5 seconds
    if [ $((ELAPSED % 5)) -eq 0 ] && [ "$ELAPSED" -gt 0 ]; then
        echo "  still waiting... (${ELAPSED}s, last HTTP $HTTP_CODE)"
    fi

    sleep 1
done
