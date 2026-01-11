#!/usr/bin/env bash
# gateALL.sh - Single-command full verification
# Runs all gates and produces consolidated proof log
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROOF_DIR="$HOME/.roxy/proofs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PROOF_FILE="$PROOF_DIR/gateALL_${TIMESTAMP}.log"

mkdir -p "$PROOF_DIR"

# Colors for terminal (not in log)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo "$1" | tee -a "$PROOF_FILE"
}

log_color() {
    echo -e "$1" # Color to terminal
    echo "$2" >> "$PROOF_FILE" # Plain to file
}

# Header
log "========================================================"
log "GATE ALL: Complete Production Verification"
log "========================================================"
log "Timestamp: $(date -Iseconds)"
log "Host: $(hostname)"
log "User: $(whoami)"
log ""

# Capture version info
log "=== System Information ==="
log "Version endpoint:"
if VERSION=$(curl -sS http://127.0.0.1:8766/version 2>/dev/null); then
    echo "$VERSION" | python3 -m json.tool >> "$PROOF_FILE"
    echo "$VERSION" | python3 -m json.tool
else
    log "ERROR: Could not reach /version - is service running?"
    log "Run: ~/.roxy/scripts/prod_deploy.sh first"
    exit 1
fi
log ""

# Track results
GATES_PASSED=0
GATES_FAILED=0
GATE_RESULTS=""

run_gate() {
    local gate_name="$1"
    local gate_script="$2"

    log "=== Running $gate_name ==="
    log "Script: $gate_script"
    log ""

    if [ ! -x "$gate_script" ]; then
        log "ERROR: Gate script not found or not executable: $gate_script"
        GATES_FAILED=$((GATES_FAILED + 1))
        GATE_RESULTS="$GATE_RESULTS\n  $gate_name: FAIL (script not found)"
        return 1
    fi

    # Run gate and capture output
    local gate_output
    local gate_exit
    gate_output=$("$gate_script" 2>&1) && gate_exit=0 || gate_exit=$?

    # Append gate output to proof
    echo "$gate_output" >> "$PROOF_FILE"

    # Check result
    if [ $gate_exit -eq 0 ] && echo "$gate_output" | grep -q "PASS"; then
        log_color "${GREEN}$gate_name: PASS${NC}" "$gate_name: PASS"
        GATES_PASSED=$((GATES_PASSED + 1))
        GATE_RESULTS="$GATE_RESULTS\n  $gate_name: PASS"

        # Extract proof file path
        local proof_path
        proof_path=$(echo "$gate_output" | grep "Proof file:" | tail -1 | awk '{print $NF}')
        if [ -n "$proof_path" ]; then
            log "  Proof: $proof_path"
        fi
    else
        log_color "${RED}$gate_name: FAIL${NC}" "$gate_name: FAIL"
        GATES_FAILED=$((GATES_FAILED + 1))
        GATE_RESULTS="$GATE_RESULTS\n  $gate_name: FAIL"

        # Show failure details
        echo "$gate_output" | grep -E "(FAIL|ERROR)" | head -5
    fi
    log ""
}

# Run all gates
log "========================================================"
log "Running Gates..."
log "========================================================"
log ""

run_gate "Gate A (Resilience)" "$SCRIPT_DIR/gateA_resilience.sh"
run_gate "Gate B (Overload)" "$SCRIPT_DIR/gateB_overload.sh"
run_gate "Gate E (Observability)" "$SCRIPT_DIR/gateE_observability.sh"
run_gate "Gate F (Auth)" "$SCRIPT_DIR/gateF_auth_audit.sh"

# Summary
log "========================================================"
log "SUMMARY"
log "========================================================"
log ""
log "Gates Passed: $GATES_PASSED"
log "Gates Failed: $GATES_FAILED"
log ""
log "Results:"
echo -e "$GATE_RESULTS" | tee -a "$PROOF_FILE"
log ""

# Final verdict
if [ $GATES_FAILED -eq 0 ]; then
    log "========================================================"
    log_color "${GREEN}GATE ALL: PASS${NC}" "GATE ALL: PASS"
    log "========================================================"
    log ""
    log "All gates passed. System is production-ready."
    log ""
    log "Proof file: $PROOF_FILE"
    log "To promote to v1.0.0:"
    log "  git tag -a v1.0.0 -m 'v1.0.0 - Production release'"
    log "  git push origin v1.0.0"
    exit 0
else
    log "========================================================"
    log_color "${RED}GATE ALL: FAIL${NC}" "GATE ALL: FAIL"
    log "========================================================"
    log ""
    log "One or more gates failed. Review proof file for details."
    log ""
    log "Proof file: $PROOF_FILE"
    log "See: docs/RUNBOOK.md for remediation steps"
    exit 1
fi
