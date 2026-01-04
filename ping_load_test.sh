#!/bin/bash
# PHASE B: PING LOAD TEST WITH CONTROLLED CONCURRENCY
# Goal: Disambiguate client timeout vs server bug

set -o pipefail

ROXY_TOKEN=$(cat ~/.roxy/secret.token)
ROXY_URL="http://127.0.0.1:8766/run"
TIMEOUT=30  # Generous 30s timeout

# Test matrix: concurrency levels
CONCURRENCY_LEVELS=(1 5 10 25 50)
REQUESTS_PER_LEVEL=200

RESULTS_FILE="$1"
if [ -z "$RESULTS_FILE" ]; then
    echo "Usage: $0 <results_output_file>"
    exit 1
fi

echo "=== PING LOAD TEST ===" | tee "$RESULTS_FILE"
echo "Timeout: ${TIMEOUT}s per request" | tee -a "$RESULTS_FILE"
echo "Requests per concurrency level: $REQUESTS_PER_LEVEL" | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"

# Function to send single ping request
send_ping() {
    local start_ms=$(date +%s%3N)
    local response=$(jq -n '{command:"ping"}' | \
        curl -s -m $TIMEOUT \
            -H "X-ROXY-Token: $ROXY_TOKEN" \
            -H "Content-Type: application/json" \
            -d @- "$ROXY_URL" 2>&1)
    local end_ms=$(date +%s%3N)
    local latency=$((end_ms - start_ms))
    
    # Check if successful
    if echo "$response" | jq -e '.status == "success"' &>/dev/null; then
        echo "OK $latency"
    else
        echo "FAIL $latency"
    fi
}

# Test each concurrency level
for C in "${CONCURRENCY_LEVELS[@]}"; do
    echo "Testing C=$C (concurrency=$C, requests=$REQUESTS_PER_LEVEL)..." | tee -a "$RESULTS_FILE"
    
    SUCCESSES=0
    FAILURES=0
    LATENCIES=()
    
    # Start timestamp for error correlation
    START_TS=$(date --iso-8601=seconds)
    
    # Send requests in batches of C parallel requests
    BATCHES=$(( REQUESTS_PER_LEVEL / C ))
    for batch in $(seq 1 $BATCHES); do
        # Launch C parallel requests
        pids=()
        for i in $(seq 1 $C); do
            send_ping > /tmp/ping_result_${batch}_${i}.txt &
            pids+=($!)
        done
        
        # Wait for all to complete
        for pid in "${pids[@]}"; do
            wait $pid
        done
        
        # Collect results
        for i in $(seq 1 $C); do
            result=$(cat /tmp/ping_result_${batch}_${i}.txt)
            status=$(echo "$result" | awk '{print $1}')
            latency=$(echo "$result" | awk '{print $2}')
            
            if [ "$status" = "OK" ]; then
                ((SUCCESSES++))
                LATENCIES+=($latency)
            else
                ((FAILURES++))
            fi
        done
    done
    
    # Calculate statistics
    TOTAL=$((SUCCESSES + FAILURES))
    SUCCESS_RATE=$(( SUCCESSES * 100 / TOTAL ))
    
    # Sort latencies for percentiles
    if [ ${#LATENCIES[@]} -gt 0 ]; then
        SORTED_LATENCIES=($(printf '%s\n' "${LATENCIES[@]}" | sort -n))
        P50_IDX=$(( ${#SORTED_LATENCIES[@]} * 50 / 100 ))
        P95_IDX=$(( ${#SORTED_LATENCIES[@]} * 95 / 100 ))
        P99_IDX=$(( ${#SORTED_LATENCIES[@]} * 99 / 100 ))
        
        P50=${SORTED_LATENCIES[$P50_IDX]}
        P95=${SORTED_LATENCIES[$P95_IDX]}
        P99=${SORTED_LATENCIES[$P99_IDX]}
    else
        P50=0
        P95=0
        P99=0
    fi
    
    # Count broken pipe errors in this window
    BROKEN_PIPES=$(journalctl --user -u roxy-core --since "$START_TS" --no-pager 2>/dev/null | grep -c "Broken pipe" || echo "0")
    
    # Output results
    echo "  Successes: $SUCCESSES/$TOTAL ($SUCCESS_RATE%)" | tee -a "$RESULTS_FILE"
    echo "  Failures: $FAILURES/$TOTAL" | tee -a "$RESULTS_FILE"
    echo "  Latency P50: ${P50}ms" | tee -a "$RESULTS_FILE"
    echo "  Latency P95: ${P95}ms" | tee -a "$RESULTS_FILE"
    echo "  Latency P99: ${P99}ms" | tee -a "$RESULTS_FILE"
    echo "  Broken pipe errors: $BROKEN_PIPES" | tee -a "$RESULTS_FILE"
    echo "" | tee -a "$RESULTS_FILE"
    
    # Cleanup temp files
    rm -f /tmp/ping_result_*.txt
done

echo "=== SUMMARY ===" | tee -a "$RESULTS_FILE"
echo "Test complete. Results saved to: $RESULTS_FILE" | tee -a "$RESULTS_FILE"
