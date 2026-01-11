#!/usr/bin/env python3
"""
SELFTEST: Theater Session + Manifest Schema Validation (THEATER-007)

Deterministic tests for:
1. PASS: Valid manifest validates
2. FAIL: Missing required field detected
3. FAIL: Invalid enum value detected
4. FAIL: Invalid session_id pattern detected

Writes: theater_session_selftest_results.json
Exit: 0 on all expected outcomes, 1 on unexpected failure
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Add services to path
sys.path.insert(0, str(Path(__file__).parent))

from theater_session import (
    validate_manifest,
    create_session_manifest,
    generate_session_id,
    load_manifest,
    save_manifest,
    ValidationResult
)

RESULTS = []


def log_result(test_name: str, expected: str, actual: str, passed: bool, details: str = ""):
    """Log a test result."""
    result = {
        "test": test_name,
        "expected": expected,
        "actual": actual,
        "passed": passed,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    RESULTS.append(result)
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {test_name}: expected={expected}, actual={actual}")
    if details:
        print(f"       Details: {details}")


def test_valid_manifest():
    """Test 1: Valid manifest should PASS validation."""
    manifest = create_session_manifest(
        song_path="/tmp/test_song.mp3",
        title="Test Song",
        duration_seconds=180.0,
        bpm=120,
        preset="performance"
    )

    result = validate_manifest(manifest)

    # Expected: validation passes
    expected = "PASS"
    actual = "PASS" if result.valid else "FAIL"
    passed = result.valid

    log_result(
        "test_valid_manifest",
        expected,
        actual,
        passed,
        result.message
    )
    return passed


def test_missing_required_field():
    """Test 2: Manifest missing required field should FAIL validation."""
    manifest = {
        "session_id": generate_session_id(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        # Missing: "song", "recording", "theater" (all required)
    }

    result = validate_manifest(manifest)

    # Expected: validation fails
    expected = "FAIL"
    actual = "FAIL" if not result.valid else "PASS"
    passed = not result.valid  # We expect it to fail

    log_result(
        "test_missing_required_field",
        expected,
        actual,
        passed,
        result.message if not result.valid else "Unexpectedly passed validation"
    )
    return passed


def test_invalid_enum_value():
    """Test 3: Invalid enum value should FAIL validation."""
    manifest = create_session_manifest(
        song_path="/tmp/test.mp3",
        title="Test",
        duration_seconds=60,
        bpm=100,
        preset="invalid_preset_name"  # Not in enum
    )

    result = validate_manifest(manifest)

    # Expected: validation fails due to invalid enum
    expected = "FAIL"
    actual = "FAIL" if not result.valid else "PASS"
    passed = not result.valid

    log_result(
        "test_invalid_enum_value",
        expected,
        actual,
        passed,
        result.message if not result.valid else "Unexpectedly passed validation"
    )
    return passed


def test_invalid_session_id_pattern():
    """Test 4: Invalid session_id pattern should FAIL validation."""
    manifest = create_session_manifest(
        song_path="/tmp/test.mp3",
        title="Test",
        duration_seconds=60,
        bpm=100
    )

    # Corrupt the session_id to invalid pattern
    manifest["session_id"] = "INVALID_ID_FORMAT"

    result = validate_manifest(manifest)

    # Expected: validation fails due to pattern mismatch
    expected = "FAIL"
    actual = "FAIL" if not result.valid else "PASS"
    passed = not result.valid

    log_result(
        "test_invalid_session_id_pattern",
        expected,
        actual,
        passed,
        result.message if not result.valid else "Unexpectedly passed validation"
    )
    return passed


def test_session_id_generation():
    """Test 5: Session ID generation follows correct pattern."""
    import re

    session_id = generate_session_id()
    pattern = r"^SESSION_[0-9]{8}_[0-9]{6}_[a-f0-9]{8}$"

    matches = bool(re.match(pattern, session_id))

    log_result(
        "test_session_id_generation",
        "PATTERN_MATCH",
        "PATTERN_MATCH" if matches else "PATTERN_MISMATCH",
        matches,
        f"Generated: {session_id}"
    )
    return matches


def test_manifest_save_load_roundtrip():
    """Test 6: Manifest can be saved and loaded without data loss."""
    manifest = create_session_manifest(
        song_path="/tmp/roundtrip_test.mp3",
        title="Roundtrip Test",
        duration_seconds=120,
        bpm=140,
        preset="teaching"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test_manifest.json"

        # Save
        with open(path, "w") as f:
            json.dump(manifest, f)

        # Load
        loaded, error = load_manifest(path)

        if error:
            log_result(
                "test_manifest_save_load_roundtrip",
                "ROUNDTRIP_OK",
                "LOAD_ERROR",
                False,
                error
            )
            return False

        # Compare key fields
        match = (
            loaded["session_id"] == manifest["session_id"] and
            loaded["song"]["title"] == manifest["song"]["title"] and
            loaded["theater"]["preset"] == manifest["theater"]["preset"]
        )

        log_result(
            "test_manifest_save_load_roundtrip",
            "ROUNDTRIP_OK",
            "ROUNDTRIP_OK" if match else "DATA_MISMATCH",
            match,
            f"session_id match: {loaded['session_id'] == manifest['session_id']}"
        )
        return match


def main() -> int:
    """Run all tests and write results."""
    print("=" * 60)
    print("SELFTEST: Theater Session + Manifest Schema")
    print("=" * 60)
    print()

    # Check if jsonschema is available
    try:
        import jsonschema
        print("[INFO] jsonschema available - full validation enabled")
    except ImportError:
        print("[WARN] jsonschema not installed - validation tests will be limited")

    print()

    # Run tests
    tests = [
        test_valid_manifest,
        test_missing_required_field,
        test_invalid_enum_value,
        test_invalid_session_id_pattern,
        test_session_id_generation,
        test_manifest_save_load_roundtrip,
    ]

    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            if test_fn():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            log_result(
                test_fn.__name__,
                "NO_EXCEPTION",
                "EXCEPTION",
                False,
                str(e)
            )
            failed += 1

    print()
    print("=" * 60)
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print("=" * 60)

    # Write results to JSON
    output = {
        "suite": "theater_session_selftest",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": len(tests),
            "passed": passed,
            "failed": failed,
            "success_rate": f"{100*passed/len(tests):.1f}%"
        },
        "results": RESULTS
    }

    # Write to proof directory if it exists, else current directory
    proof_dirs = sorted(Path("/home/mark/.roxy/proofs").glob("PHASE8_THEATER_PROOFS_*"))
    if proof_dirs:
        output_path = proof_dirs[-1] / "theater_session_selftest_results.json"
    else:
        output_path = Path("theater_session_selftest_results.json")

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults written to: {output_path}")

    # Return 0 only if all expected outcomes matched
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
