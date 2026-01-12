#!/usr/bin/env bash
#
# loop_time_fix.sh - ROXY Time Fix Iteration Loop
#
# Runs test matrix in a loop until 2 consecutive passes
# Captures logs on failure for debugging
#
# Usage: ./loop_time_fix.sh
#

set -euo pipefail

ROXY_DIR="${ROXY_DIR:-$HOME/.roxy}"
SCRIPTS_DIR="$ROXY_DIR/scripts"
LOG_FILE="$ROXY_DIR/logs/roxy-core.log"

MAX_ITERATIONS=10
CONSECUTIVE_PASS_NEEDED=2
consecutive_passes=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "$1"
}

capture_failure_logs() {
    log "${RED}=== FAILURE LOG CAPTURE ===${NC}"

    if [[ -f "$LOG_FILE" ]]; then
        log "Last 120 lines of roxy-core.log:"
        tail -120 "$LOG_FILE" 2>/dev/null || echo "(log file empty or inaccessible)"
    else
        log "(Log file not found: $LOG_FILE)"
    fi

    log ""
    log "Service status:"
    systemctl --user status roxy-core --no-pager 2>&1 | tail -80 || true
    log "${RED}=== END FAILURE LOG ===${NC}"
}

log ""
log "========================================"
log "   ROXY Time Fix Iteration Loop"
log "========================================"
log ""
log "Target: $CONSECUTIVE_PASS_NEEDED consecutive passes"
log "Max iterations: $MAX_ITERATIONS"
log ""

for i in $(seq 1 $MAX_ITERATIONS); do
    log "${YELLOW}=== Iteration $i ===${NC}"

    # Restart service to pick up any code changes
    log "Restarting roxy-core..."
    if ! systemctl --user restart roxy-core 2>/dev/null; then
        log "${RED}Failed to restart roxy-core${NC}"
        capture_failure_logs
        consecutive_passes=0
        continue
    fi

    # Wait for service to be ready
    log "Waiting for service (4s)..."
    sleep 4

    # Check health
    if ! curl -sf "http://127.0.0.1:8766/health" > /dev/null 2>&1; then
        log "${RED}roxy-core not healthy${NC}"
        capture_failure_logs
        consecutive_passes=0
        sleep 2
        continue
    fi

    # Run gateBRAIN first (basic sanity)
    log "Running gateBRAIN..."
    if ! bash "$SCRIPTS_DIR/gateBRAIN.sh" 2>/dev/null; then
        log "${RED}gateBRAIN failed${NC}"
        capture_failure_logs
        consecutive_passes=0
        continue
    fi

    # Run time matrix
    log "Running time test matrix..."
    if bash "$SCRIPTS_DIR/time_test_matrix.sh"; then
        ((consecutive_passes++))
        log "${GREEN}Time matrix PASSED (consecutive: $consecutive_passes)${NC}"
    else
        log "${RED}Time matrix FAILED${NC}"
        capture_failure_logs
        consecutive_passes=0
        continue
    fi

    # Check if we've reached target
    if [[ $consecutive_passes -ge $CONSECUTIVE_PASS_NEEDED ]]; then
        log ""
        log "${GREEN}========================================"
        log "   SUCCESS! $CONSECUTIVE_PASS_NEEDED consecutive passes"
        log "========================================${NC}"
        log ""
        exit 0
    fi
done

log ""
log "${RED}========================================"
log "   FAILED: Could not achieve $CONSECUTIVE_PASS_NEEDED"
log "   consecutive passes in $MAX_ITERATIONS iterations"
log "========================================${NC}"
log ""
capture_failure_logs
exit 1
