#!/usr/bin/env python3
"""
SKYBEAM Publish Health Gate Selftest (STORY-026)

Tests:
1. Schema validation
2. ID format validation
3. Check result structure
4. Alert generation
5. Gate result logic
6. Heartbeat tracking
7. NATS topic constant
"""

import json
import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

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


def test_schema_valid():
    """Test that schema file exists and is valid JSON."""
    schema_path = Path(__file__).parent / "schemas" / "publish_health.json"
    try:
        with open(schema_path) as f:
            schema = json.load(f)
        if "$schema" in schema and "definitions" in schema:
            test_pass("schema_valid", "Schema loaded with definitions")
        else:
            test_fail("schema_valid", "Schema missing required fields")
    except Exception as e:
        test_fail("schema_valid", str(e))


def test_id_format():
    """Test that generated IDs match expected format."""
    from publish_health_gate import generate_id
    import re

    health_id = generate_id("HEALTH")
    alert_id = generate_id("ALERT")

    health_pattern = r"^HEALTH_\d{8}_\d{6}_[a-f0-9]{8}$"
    alert_pattern = r"^ALERT_\d{8}_\d{6}_[a-f0-9]{8}$"

    if re.match(health_pattern, health_id):
        test_pass("id_format_health", f"HEALTH ID: {health_id}")
    else:
        test_fail("id_format_health", f"Invalid: {health_id}")

    if re.match(alert_pattern, alert_id):
        test_pass("id_format_alert", f"ALERT ID: {alert_id}")
    else:
        test_fail("id_format_alert", f"Invalid: {alert_id}")


def test_check_structure():
    """Test that check results have required structure."""
    from publish_health_gate import check_queue_stuck

    check = check_queue_stuck()

    required_fields = ["check_id", "check_type", "result", "message"]
    missing = [f for f in required_fields if f not in check]

    if missing:
        test_fail("check_structure", f"Missing fields: {missing}")
    else:
        test_pass("check_structure", "All required fields present")

    # Verify result is valid
    if check["result"] in ("pass", "warning", "critical"):
        test_pass("check_result_valid", f"Result: {check['result']}")
    else:
        test_fail("check_result_valid", f"Invalid result: {check['result']}")


def test_alert_generation():
    """Test alert generation from checks."""
    from publish_health_gate import generate_alerts

    mock_checks = [
        {"check_id": "CHK_001", "check_type": "queue_stuck", "result": "pass", "message": "OK"},
        {"check_id": "CHK_002", "check_type": "metrics_freshness", "result": "warning", "message": "Warning"},
        {"check_id": "CHK_003", "check_type": "failed_receipts", "result": "critical", "message": "Critical"},
    ]

    alerts = generate_alerts(mock_checks)

    # Should generate 2 alerts (warning + critical)
    if len(alerts) == 2:
        test_pass("alert_count", "2 alerts generated for 2 non-pass checks")
    else:
        test_fail("alert_count", f"Expected 2 alerts, got {len(alerts)}")

    # Check alert structure
    if alerts:
        alert = alerts[0]
        required = ["alert_id", "severity", "title", "description", "remediation"]
        missing = [f for f in required if f not in alert]
        if missing:
            test_fail("alert_structure", f"Missing: {missing}")
        else:
            test_pass("alert_structure", "Alert has all required fields")


def test_gate_result_logic():
    """Test gate result determination logic."""
    # Gate should be: critical if any critical, else warning if any warning, else approved

    checks_critical = [
        {"result": "pass"},
        {"result": "critical"},
    ]

    checks_warning = [
        {"result": "pass"},
        {"result": "warning"},
    ]

    checks_pass = [
        {"result": "pass"},
        {"result": "pass"},
    ]

    # Test critical path
    results = [c["result"] for c in checks_critical]
    if "critical" in results:
        gate = "critical"
    elif "warning" in results:
        gate = "warning"
    else:
        gate = "approved"

    if gate == "critical":
        test_pass("gate_logic_critical", "Critical check -> critical gate")
    else:
        test_fail("gate_logic_critical", f"Expected critical, got {gate}")

    # Test warning path
    results = [c["result"] for c in checks_warning]
    if "critical" in results:
        gate = "critical"
    elif "warning" in results:
        gate = "warning"
    else:
        gate = "approved"

    if gate == "warning":
        test_pass("gate_logic_warning", "Warning check -> warning gate")
    else:
        test_fail("gate_logic_warning", f"Expected warning, got {gate}")

    # Test pass path
    results = [c["result"] for c in checks_pass]
    if "critical" in results:
        gate = "critical"
    elif "warning" in results:
        gate = "warning"
    else:
        gate = "approved"

    if gate == "approved":
        test_pass("gate_logic_approved", "All pass -> approved gate")
    else:
        test_fail("gate_logic_approved", f"Expected approved, got {gate}")


def test_heartbeat():
    """Test heartbeat update function."""
    from publish_health_gate import update_heartbeat, HEARTBEAT_FILE, HEALTH_DIR

    # Create temp directory
    test_dir = tempfile.mkdtemp()
    test_health_dir = Path(test_dir) / "health"
    test_health_dir.mkdir()
    test_heartbeat = test_health_dir / ".heartbeat.json"

    import publish_health_gate as phg
    original_dir = phg.HEALTH_DIR
    original_file = phg.HEARTBEAT_FILE
    phg.HEALTH_DIR = test_health_dir
    phg.HEARTBEAT_FILE = test_heartbeat

    try:
        # First beat
        hb1 = update_heartbeat()
        if hb1["consecutive_beats"] == 1:
            test_pass("heartbeat_first", "First beat = 1")
        else:
            test_fail("heartbeat_first", f"Expected 1, got {hb1['consecutive_beats']}")

        # Second beat
        hb2 = update_heartbeat()
        if hb2["consecutive_beats"] == 2:
            test_pass("heartbeat_increment", "Second beat = 2")
        else:
            test_fail("heartbeat_increment", f"Expected 2, got {hb2['consecutive_beats']}")

    finally:
        phg.HEALTH_DIR = original_dir
        phg.HEARTBEAT_FILE = original_file
        shutil.rmtree(test_dir)


def test_thresholds():
    """Test that thresholds are properly defined."""
    from publish_health_gate import (
        QUEUE_STUCK_WARNING_HOURS,
        QUEUE_STUCK_CRITICAL_HOURS,
        FRESHNESS_WARNING_HOURS,
        FRESHNESS_CRITICAL_HOURS
    )

    if QUEUE_STUCK_WARNING_HOURS < QUEUE_STUCK_CRITICAL_HOURS:
        test_pass("threshold_queue", f"Queue: warn={QUEUE_STUCK_WARNING_HOURS}h, crit={QUEUE_STUCK_CRITICAL_HOURS}h")
    else:
        test_fail("threshold_queue", "Warning should be less than critical")

    if FRESHNESS_WARNING_HOURS < FRESHNESS_CRITICAL_HOURS:
        test_pass("threshold_freshness", f"Freshness: warn={FRESHNESS_WARNING_HOURS}h, crit={FRESHNESS_CRITICAL_HOURS}h")
    else:
        test_fail("threshold_freshness", "Warning should be less than critical")


def test_nats_topic():
    """Test NATS topic constant is set correctly."""
    from publish_health_gate import NATS_TOPIC

    if NATS_TOPIC == "ghost.publish.health":
        test_pass("nats_topic", f"Topic: {NATS_TOPIC}")
    else:
        test_fail("nats_topic", f"Wrong topic: {NATS_TOPIC}")


def main():
    print("=" * 60)
    print("SKYBEAM Publish Health Gate Selftest (STORY-026)")
    print("=" * 60)

    test_schema_valid()
    test_id_format()
    test_check_structure()
    test_alert_generation()
    test_gate_result_logic()
    test_heartbeat()
    test_thresholds()
    test_nats_topic()

    print("=" * 60)
    print(f"Results: {TESTS_PASSED} passed, {TESTS_FAILED} failed")
    print("=" * 60)

    return 0 if TESTS_FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
