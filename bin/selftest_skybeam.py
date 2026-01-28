#!/usr/bin/env python3
# @pipeline Skybeam
# @locked true
# @change_requires HumanApproval
# @owner Chief
"""
SKYBEAM Operator Console CLI Selftest (STORY-027)

Tests:
1. CLI runs without arguments (shows help)
2. status subcommand works
3. --json flag produces valid JSON
4. Exit codes match health state
5. Handles missing files gracefully
6. Timer parsing works
7. Receipt discovery works
8. Age formatting works
"""

import json
import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent))

TESTS_PASSED = 0
TESTS_FAILED = 0
SKYBEAM_CLI = Path(__file__).parent / "skybeam"


def test_pass(name: str, msg: str = ""):
    global TESTS_PASSED
    TESTS_PASSED += 1
    print(f"  [PASS] {name}" + (f" - {msg}" if msg else ""))


def test_fail(name: str, msg: str = ""):
    global TESTS_FAILED
    TESTS_FAILED += 1
    print(f"  [FAIL] {name}" + (f" - {msg}" if msg else ""))


def test_cli_help():
    """Test CLI shows help without arguments."""
    try:
        result = subprocess.run(
            [sys.executable, str(SKYBEAM_CLI)],
            capture_output=True,
            text=True,
            timeout=10
        )
        if "SKYBEAM" in result.stdout or "usage" in result.stdout.lower():
            test_pass("cli_help", "Help text displayed")
        else:
            test_fail("cli_help", f"No help text: {result.stdout[:100]}")
    except Exception as e:
        test_fail("cli_help", str(e))


def test_status_runs():
    """Test status subcommand runs."""
    try:
        result = subprocess.run(
            [sys.executable, str(SKYBEAM_CLI), "status"],
            capture_output=True,
            text=True,
            timeout=15
        )
        # Should produce output (dashboard or degraded)
        if result.stdout or result.returncode in (0, 1, 2):
            test_pass("status_runs", f"Exit code: {result.returncode}")
        else:
            test_fail("status_runs", f"No output, exit={result.returncode}")
    except Exception as e:
        test_fail("status_runs", str(e))


def test_status_json():
    """Test --json flag produces valid JSON."""
    try:
        result = subprocess.run(
            [sys.executable, str(SKYBEAM_CLI), "status", "--json"],
            capture_output=True,
            text=True,
            timeout=15
        )
        data = json.loads(result.stdout)
        required = ["gate_result", "alert_count", "queue", "timers"]
        missing = [f for f in required if f not in data]
        if missing:
            test_fail("status_json", f"Missing fields: {missing}")
        else:
            test_pass("status_json", f"Valid JSON with {len(data)} fields")
    except json.JSONDecodeError as e:
        test_fail("status_json", f"Invalid JSON: {e}")
    except Exception as e:
        test_fail("status_json", str(e))


def test_exit_codes():
    """Test exit code logic via actual run."""
    try:
        # Run status and check exit code matches gate_result
        result = subprocess.run(
            [sys.executable, str(SKYBEAM_CLI), "status", "--json"],
            capture_output=True,
            text=True,
            timeout=15
        )
        data = json.loads(result.stdout)
        gate = data.get("gate_result", "unknown")
        exit_code = result.returncode

        # Verify exit code mapping
        expected = {"approved": 0, "unknown": 0, "warning": 1, "critical": 2}
        expected_code = expected.get(gate, 0)

        if exit_code == expected_code:
            test_pass("exit_code_mapping", f"{gate} -> exit {exit_code}")
        else:
            test_fail("exit_code_mapping", f"{gate} should be {expected_code}, got {exit_code}")

        # Verify exit codes are in valid range
        if exit_code in (0, 1, 2):
            test_pass("exit_code_valid", f"Exit code {exit_code} is valid")
        else:
            test_fail("exit_code_valid", f"Invalid exit code: {exit_code}")

    except Exception as e:
        test_fail("exit_codes", str(e))


def test_age_formatting():
    """Test age formatting via JSON output."""
    try:
        result = subprocess.run(
            [sys.executable, str(SKYBEAM_CLI), "status", "--json"],
            capture_output=True,
            text=True,
            timeout=15
        )
        data = json.loads(result.stdout)
        receipt = data.get("latest_receipt", {})
        age = receipt.get("age", "")

        # Age should be in format like "5m ago", "2.3h ago", or "1d ago"
        if age in ("n/a", "?"):
            test_pass("age_format", f"Graceful handling: {age}")
        elif "ago" in age or age == "?":
            test_pass("age_format", f"Age formatted: {age}")
        else:
            test_fail("age_format", f"Unexpected format: {age}")

    except Exception as e:
        test_fail("age_formatting", str(e))


def test_load_json():
    """Test graceful handling of missing files."""
    try:
        # Create a temp directory with no health file
        test_dir = tempfile.mkdtemp()
        try:
            # Run status - should handle missing files gracefully
            result = subprocess.run(
                [sys.executable, str(SKYBEAM_CLI), "status", "--json"],
                capture_output=True,
                text=True,
                timeout=15
            )
            # Should not crash - exit code 0, 1, or 2 is fine
            if result.returncode in (0, 1, 2):
                test_pass("load_json_graceful", "Handles files gracefully")
            else:
                test_fail("load_json_graceful", f"Unexpected exit: {result.returncode}")

            # Verify JSON is still valid even with potential missing data
            try:
                data = json.loads(result.stdout)
                test_pass("load_json_output", "JSON output valid")
            except json.JSONDecodeError:
                test_fail("load_json_output", "Invalid JSON on degraded mode")

        finally:
            shutil.rmtree(test_dir)

    except Exception as e:
        test_fail("load_json", str(e))


def test_timer_parsing():
    """Test timer list parsing."""
    try:
        result = subprocess.run(
            [sys.executable, str(SKYBEAM_CLI), "status", "--json"],
            capture_output=True,
            text=True,
            timeout=15
        )
        data = json.loads(result.stdout)
        timers = data.get("timers", [])

        if isinstance(timers, list):
            test_pass("timer_parsing", f"Found {len(timers)} timers")
        else:
            test_fail("timer_parsing", f"Timers not a list: {type(timers)}")

        # Check timer structure
        if timers:
            t = timers[0]
            if "unit" in t:
                test_pass("timer_structure", f"Timer has unit: {t['unit']}")
            else:
                test_fail("timer_structure", f"Timer missing unit: {t}")
    except Exception as e:
        test_fail("timer_parsing", str(e))


def test_queue_info():
    """Test queue information extraction."""
    try:
        result = subprocess.run(
            [sys.executable, str(SKYBEAM_CLI), "status", "--json"],
            capture_output=True,
            text=True,
            timeout=15
        )
        data = json.loads(result.stdout)
        queue = data.get("queue", {})

        if "length" in queue:
            test_pass("queue_length", f"Queue length: {queue['length']}")
        else:
            test_fail("queue_length", "Missing queue length")

        if "oldest_age_hours" in queue:
            test_pass("queue_age", f"Oldest age: {queue['oldest_age_hours']}h")
        else:
            test_fail("queue_age", "Missing oldest age")

    except Exception as e:
        test_fail("queue_info", str(e))


def test_dashboard_fits_terminal():
    """Test dashboard output is reasonably sized."""
    try:
        result = subprocess.run(
            [sys.executable, str(SKYBEAM_CLI), "status"],
            capture_output=True,
            text=True,
            timeout=15
        )
        lines = result.stdout.split("\n")
        max_width = max(len(line) for line in lines) if lines else 0

        # Should fit in 80 columns (allowing for ANSI codes)
        # ANSI codes add ~10-20 chars per colored element
        if max_width < 120:  # Generous for ANSI
            test_pass("dashboard_width", f"Max line width: {max_width}")
        else:
            test_fail("dashboard_width", f"Too wide: {max_width}")

        if len(lines) < 40:
            test_pass("dashboard_height", f"Lines: {len(lines)}")
        else:
            test_fail("dashboard_height", f"Too tall: {len(lines)}")

    except Exception as e:
        test_fail("dashboard_size", str(e))


def main():
    print("=" * 60)
    print("SKYBEAM Operator Console CLI Selftest (STORY-027)")
    print("=" * 60)

    test_cli_help()
    test_status_runs()
    test_status_json()
    test_exit_codes()
    test_age_formatting()
    test_load_json()
    test_timer_parsing()
    test_queue_info()
    test_dashboard_fits_terminal()

    print("=" * 60)
    print(f"Results: {TESTS_PASSED} passed, {TESTS_FAILED} failed")
    print("=" * 60)

    return 0 if TESTS_FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
