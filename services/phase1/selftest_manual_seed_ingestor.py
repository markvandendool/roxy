#!/usr/bin/env python3
"""
SKYBEAM Manual Seed Ingestor Selftest (STORY-031b)

Tests:
1. Schema validation (valid/invalid seeds)
2. Seed scanning from manual directory
3. Merge into seeds_merged_latest.json
4. Processed seeds moved to processed/
5. Duplicate detection (already merged)
6. Priority ordering
7. Receipt generation
8. Idempotent re-runs
"""

import json
import os
import sys
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

from manual_seed_ingestor import (
    validate_seed,
    scan_manual_seeds,
    load_json,
    save_json,
    generate_ingest_id,
    SEEDS_DIR,
    MANUAL_DIR,
    PROCESSED_DIR,
    MERGED_OUTPUT,
    INGEST_RECEIPT
)

TESTS_PASSED = 0
TESTS_FAILED = 0


def test_pass(name: str, msg: str = ""):
    global TESTS_PASSED
    TESTS_PASSED += 1
    print(f"  [PASS] {name}" + (f" - {msg}" if msg else ""))


def test_fail(name: str, msg: str = ""):
    global TESTS_FAILED
    TESTS_FAILED += 1
    print(f"  [FAIL] {name}" + (f" - {msg}" if msg else ""))


def cleanup():
    """Clean up test artifacts."""
    # Remove test seeds from manual/
    for f in MANUAL_DIR.glob("inject_SEED_TEST_*.json"):
        try:
            os.unlink(f)
        except Exception:
            pass
    # Remove from processed/
    if PROCESSED_DIR.exists():
        for f in PROCESSED_DIR.glob("*SEED_TEST_*.json"):
            try:
                os.unlink(f)
            except Exception:
                pass


def create_test_seed(seed_id: str, priority: str = "normal", valid: bool = True) -> Path:
    """Create a test seed file."""
    MANUAL_DIR.mkdir(parents=True, exist_ok=True)

    seed = {
        "seed_id": seed_id,
        "created": datetime.now(timezone.utc).isoformat(),
        "type": "manual_inject",
        "priority": priority,
        "source": "test",
        "url": "https://youtube.com/watch?v=TEST123" if valid else "invalid-url",
        "platform": "youtube",
        "tags": ["test"],
        "request": {"manual_injection": True},
        "meta": {"version": "1.0.0"}
    }

    path = MANUAL_DIR / f"inject_{seed_id}.json"
    save_json(path, seed)
    return path


def test_validate_seed_valid():
    """Test validation passes for valid seed."""
    seed = {
        "seed_id": "SEED_20260111_000000_test1234",
        "created": "2026-01-11T00:00:00Z",
        "type": "manual_inject",
        "url": "https://youtube.com/watch?v=abc123"
    }
    is_valid, error = validate_seed(seed)
    if is_valid:
        test_pass("validate_seed_valid", "Valid seed passes")
    else:
        test_fail("validate_seed_valid", error)


def test_validate_seed_missing_field():
    """Test validation fails for missing field."""
    seed = {
        "seed_id": "SEED_20260111_000000_test1234",
        "type": "manual_inject"
        # missing created, url
    }
    is_valid, error = validate_seed(seed)
    if not is_valid and "Missing" in error:
        test_pass("validate_seed_missing", f"Detects missing field: {error}")
    else:
        test_fail("validate_seed_missing", f"Should fail: {is_valid}, {error}")


def test_validate_seed_bad_id():
    """Test validation fails for bad seed_id format."""
    seed = {
        "seed_id": "BAD_FORMAT",
        "created": "2026-01-11T00:00:00Z",
        "type": "manual_inject",
        "url": "https://youtube.com/watch?v=abc123"
    }
    is_valid, error = validate_seed(seed)
    if not is_valid and "seed_id" in error.lower():
        test_pass("validate_seed_bad_id", "Detects bad ID format")
    else:
        test_fail("validate_seed_bad_id", f"Should fail: {is_valid}, {error}")


def test_validate_seed_bad_url():
    """Test validation fails for bad URL."""
    seed = {
        "seed_id": "SEED_20260111_000000_test1234",
        "created": "2026-01-11T00:00:00Z",
        "type": "manual_inject",
        "url": "not-a-url"
    }
    is_valid, error = validate_seed(seed)
    if not is_valid and "URL" in error:
        test_pass("validate_seed_bad_url", "Detects bad URL")
    else:
        test_fail("validate_seed_bad_url", f"Should fail: {is_valid}, {error}")


def test_scan_manual_seeds():
    """Test scanning manual directory."""
    cleanup()
    try:
        # Create test seeds
        create_test_seed("SEED_TEST_001_aaaaaaaa", "normal")
        create_test_seed("SEED_TEST_002_bbbbbbbb", "high")

        seeds = scan_manual_seeds()
        test_ids = [s[1]["seed_id"] for s in seeds if "TEST" in s[1]["seed_id"]]

        if len(test_ids) >= 2:
            test_pass("scan_manual_seeds", f"Found {len(test_ids)} test seeds")
        else:
            test_fail("scan_manual_seeds", f"Expected 2, found {len(test_ids)}")

    finally:
        cleanup()


def test_priority_ordering():
    """Test seeds are ordered by priority."""
    cleanup()
    try:
        create_test_seed("SEED_TEST_LOW_aaaaaaaa", "low")
        create_test_seed("SEED_TEST_HIGH_bbbbbbbb", "high")
        create_test_seed("SEED_TEST_NORM_cccccccc", "normal")

        seeds = scan_manual_seeds()
        test_seeds = [s for s in seeds if "TEST" in s[1]["seed_id"]]

        if len(test_seeds) >= 3:
            priorities = [s[1]["priority"] for s in test_seeds]
            # High should come before normal, normal before low
            if priorities.index("high") < priorities.index("normal") < priorities.index("low"):
                test_pass("priority_ordering", f"Order: {priorities}")
            else:
                test_fail("priority_ordering", f"Wrong order: {priorities}")
        else:
            test_fail("priority_ordering", f"Not enough seeds: {len(test_seeds)}")

    finally:
        cleanup()


def test_ingest_id_format():
    """Test ingest ID format."""
    import re
    ingest_id = generate_ingest_id()
    pattern = r"^INGEST_\d{8}_\d{6}_[a-f0-9]{8}$"
    if re.match(pattern, ingest_id):
        test_pass("ingest_id_format", ingest_id)
    else:
        test_fail("ingest_id_format", f"Bad format: {ingest_id}")


def test_full_ingest_cycle():
    """Test full ingest cycle with actual run."""
    cleanup()
    try:
        # Create a test seed
        create_test_seed("SEED_TEST_FULL_12345678", "normal")

        # Run the ingestor
        import subprocess
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "manual_seed_ingestor.py")],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            test_pass("full_ingest_exit", "Exit code 0")
        else:
            test_fail("full_ingest_exit", f"Exit {result.returncode}: {result.stderr}")
            return

        # Check merged output exists
        if MERGED_OUTPUT.exists():
            merged = load_json(MERGED_OUTPUT)
            if merged:
                test_pass("full_ingest_merged", f"Merged file created")
            else:
                test_fail("full_ingest_merged", "Merged file empty/invalid")
        else:
            test_fail("full_ingest_merged", "Merged file not created")

        # Check receipt exists
        if INGEST_RECEIPT.exists():
            receipt = load_json(INGEST_RECEIPT)
            if receipt and "ingest_id" in receipt:
                test_pass("full_ingest_receipt", f"Receipt: {receipt['ingest_id']}")
            else:
                test_fail("full_ingest_receipt", "Receipt invalid")
        else:
            test_fail("full_ingest_receipt", "Receipt not created")

        # Check seed was moved to processed
        processed_files = list(PROCESSED_DIR.glob("*SEED_TEST_FULL*.json"))
        if processed_files:
            test_pass("full_ingest_moved", f"Moved to: {processed_files[0].name}")
        else:
            test_fail("full_ingest_moved", "Seed not moved to processed/")

    finally:
        cleanup()


def test_idempotent_rerun():
    """Test re-running doesn't duplicate seeds."""
    cleanup()
    try:
        create_test_seed("SEED_TEST_IDEM_12345678", "normal")

        import subprocess

        # First run
        result1 = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "manual_seed_ingestor.py")],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result1.returncode != 0:
            test_fail("idempotent_first", f"First run failed: {result1.returncode}")
            return

        # Get seed count after first run
        merged1 = load_json(MERGED_OUTPUT)
        count1 = len([s for s in merged1.get("seeds", []) if "TEST_IDEM" in s.get("seed_id", "")])

        # Second run (should be no-op)
        result2 = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "manual_seed_ingestor.py")],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result2.returncode != 0:
            test_fail("idempotent_second", f"Second run failed: {result2.returncode}")
            return

        # Get seed count after second run
        merged2 = load_json(MERGED_OUTPUT)
        count2 = len([s for s in merged2.get("seeds", []) if "TEST_IDEM" in s.get("seed_id", "")])

        if count1 == count2:
            test_pass("idempotent_rerun", f"Seed count unchanged: {count1}")
        else:
            test_fail("idempotent_rerun", f"Count changed: {count1} -> {count2}")

    finally:
        cleanup()


def main():
    print("=" * 60)
    print("SKYBEAM Manual Seed Ingestor Selftest (STORY-031b)")
    print("=" * 60)

    test_validate_seed_valid()
    test_validate_seed_missing_field()
    test_validate_seed_bad_id()
    test_validate_seed_bad_url()
    test_scan_manual_seeds()
    test_priority_ordering()
    test_ingest_id_format()
    test_full_ingest_cycle()
    test_idempotent_rerun()

    print("=" * 60)
    print(f"Results: {TESTS_PASSED} passed, {TESTS_FAILED} failed")
    print("=" * 60)

    return 0 if TESTS_FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
