#!/bin/bash
#
# SKYBEAM Theater Integration - Proof Pack Runner
# PHASE8_THEATER_PROOFS
#
# Runs all selftests, collects outputs into proof directory,
# prints summary, exits 0 only on full pass.
#

set -e

echo "============================================================"
echo "SKYBEAM THEATER PROOF PACK RUNNER"
echo "============================================================"
echo ""

# Find or create proof directory
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PROOF_BASE="/home/mark/.roxy/proofs"
EXISTING_DIR=$(ls -d ${PROOF_BASE}/PHASE8_THEATER_PROOFS_* 2>/dev/null | tail -1 || echo "")

if [ -n "$EXISTING_DIR" ]; then
    PROOF_DIR="$EXISTING_DIR"
    echo "[INFO] Using existing proof directory: $PROOF_DIR"
else
    PROOF_DIR="${PROOF_BASE}/PHASE8_THEATER_PROOFS_${TIMESTAMP}"
    mkdir -p "$PROOF_DIR"
    echo "[INFO] Created proof directory: $PROOF_DIR"
fi

cd /home/mark/.roxy

PASSED=0
FAILED=0
TOTAL=0

# Function to run a test and track results
run_test() {
    local name="$1"
    local script="$2"

    echo ""
    echo "------------------------------------------------------------"
    echo "Running: $name"
    echo "------------------------------------------------------------"

    TOTAL=$((TOTAL + 1))

    if python3 "$script"; then
        PASSED=$((PASSED + 1))
        echo "[PASS] $name"
    else
        FAILED=$((FAILED + 1))
        echo "[FAIL] $name"
    fi
}

# ============================================================
# Step 1: File Metrics
# ============================================================
echo ""
echo "------------------------------------------------------------"
echo "Collecting File Metrics"
echo "------------------------------------------------------------"

{
    echo "=== FILE METRICS ==="
    echo "Generated: $(date -Iseconds)"
    echo ""
    echo "=== Line Counts ==="
    wc -l services/obs_director.py services/theater_session.py \
        services/selftest_theater_session.py \
        services/selftest_theater_handoff.py \
        services/selftest_obs_director_dryrun.py
    echo ""
    echo "=== Python Syntax Check ==="
    python3 -m py_compile services/obs_director.py && echo "obs_director.py: SYNTAX OK" || echo "obs_director.py: SYNTAX FAIL"
    python3 -m py_compile services/theater_session.py && echo "theater_session.py: SYNTAX OK" || echo "theater_session.py: SYNTAX FAIL"
    python3 -m py_compile services/selftest_theater_session.py && echo "selftest_theater_session.py: SYNTAX OK" || echo "selftest_theater_session.py: SYNTAX FAIL"
    python3 -m py_compile services/selftest_theater_handoff.py && echo "selftest_theater_handoff.py: SYNTAX OK" || echo "selftest_theater_handoff.py: SYNTAX FAIL"
    python3 -m py_compile services/selftest_obs_director_dryrun.py && echo "selftest_obs_director_dryrun.py: SYNTAX OK" || echo "selftest_obs_director_dryrun.py: SYNTAX FAIL"
} > "$PROOF_DIR/file_metrics.txt" 2>&1

echo "[INFO] File metrics written to: $PROOF_DIR/file_metrics.txt"

# ============================================================
# Step 2: SHA256 Manifest
# ============================================================
echo ""
echo "------------------------------------------------------------"
echo "Generating SHA256 Manifest"
echo "------------------------------------------------------------"

{
    echo "=== SHA256 MANIFEST ==="
    echo "Generated: $(date -Iseconds)"
    echo ""
    echo "=== Service Files ==="
    sha256sum services/obs_director.py services/theater_session.py 2>/dev/null || true
    echo ""
    echo "=== Schema/Config Files ==="
    sha256sum theater-sessions/session_manifest_schema.json \
        theater-sessions/session_manifest_example.json \
        config/theater_obs_mapping.json 2>/dev/null || true
    echo ""
    echo "=== Selftest Files ==="
    sha256sum services/selftest_theater_session.py \
        services/selftest_theater_handoff.py \
        services/selftest_obs_director_dryrun.py \
        services/run_theater_proofs.sh 2>/dev/null || true
} > "$PROOF_DIR/sha256_manifest.txt" 2>&1

echo "[INFO] SHA256 manifest written to: $PROOF_DIR/sha256_manifest.txt"

# ============================================================
# Step 3: Directory Tree
# ============================================================
echo ""
echo "------------------------------------------------------------"
echo "Generating Directory Tree"
echo "------------------------------------------------------------"

{
    echo "=== PROOF DIRECTORY TREE ==="
    echo "Generated: $(date -Iseconds)"
    echo ""
    tree "$PROOF_DIR" 2>/dev/null || ls -la "$PROOF_DIR"
} > "$PROOF_DIR/tree.txt" 2>&1

echo "[INFO] Directory tree written to: $PROOF_DIR/tree.txt"

# ============================================================
# Step 4: Run Selftests
# ============================================================

run_test "Theater Session + Schema Validation" "services/selftest_theater_session.py"
run_test "Theater Handoff Protocol" "services/selftest_theater_handoff.py"
run_test "OBS Director Dry-Run (Mocked)" "services/selftest_obs_director_dryrun.py"

# ============================================================
# Step 5: Update Tree (post-tests)
# ============================================================
{
    echo "=== PROOF DIRECTORY TREE (FINAL) ==="
    echo "Generated: $(date -Iseconds)"
    echo ""
    tree "$PROOF_DIR" 2>/dev/null || ls -la "$PROOF_DIR"
} > "$PROOF_DIR/tree.txt" 2>&1

# ============================================================
# Final Summary
# ============================================================
echo ""
echo "============================================================"
echo "PROOF PACK SUMMARY"
echo "============================================================"
echo ""
echo "Proof Directory: $PROOF_DIR"
echo ""
echo "Test Results:"
echo "  Total:  $TOTAL"
echo "  Passed: $PASSED"
echo "  Failed: $FAILED"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo "============================================================"
    echo "OVERALL RESULT: PASS"
    echo "============================================================"
    echo ""
    echo "All selftests passed. Proof pack complete."
    echo ""
    echo "Files in proof pack:"
    ls -la "$PROOF_DIR"
    exit 0
else
    echo "============================================================"
    echo "OVERALL RESULT: FAIL"
    echo "============================================================"
    echo ""
    echo "$FAILED test(s) failed. Review results in proof directory."
    exit 1
fi
