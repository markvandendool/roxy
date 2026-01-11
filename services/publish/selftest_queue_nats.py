#!/usr/bin/env python3
"""
SKYBEAM Publish Queue Builder Selftest (STORY-021)

Tests:
1. Schema validation
2. Idempotency (same hash not re-enqueued)
3. Degraded mode (gate not approved)
4. Entry structure validation
5. Known hashes tracking
"""

import json
import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

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
    schema_path = Path(__file__).parent / "schemas" / "publish_queue.json"
    try:
        with open(schema_path) as f:
            schema = json.load(f)
        if "$schema" in schema and "definitions" in schema:
            test_pass("schema_valid", "Schema loaded and has required fields")
        else:
            test_fail("schema_valid", "Schema missing required fields")
    except Exception as e:
        test_fail("schema_valid", str(e))


def test_entry_structure():
    """Test that queue entry has all required fields."""
    from publish_queue_builder import build_queue_entry

    mock_master = {
        "master_id": "MASTER_TEST_001",
        "script_id": "SCR_TEST",
        "title": "Test Video",
        "file_proof": {
            "sha256": "a" * 64,
            "path": "/tmp/test.mp4"
        }
    }
    mock_qa = {
        "qa_id": "QA_TEST_001"
    }

    entry = build_queue_entry(mock_master, mock_qa)

    required_fields = [
        "publish_id", "enqueue_timestamp", "master_id",
        "master_sha256", "source_qa_id", "script_id", "status"
    ]

    missing = [f for f in required_fields if f not in entry]
    if missing:
        test_fail("entry_structure", f"Missing fields: {missing}")
    else:
        test_pass("entry_structure", "All required fields present")


def test_id_format():
    """Test that generated IDs match expected format."""
    from publish_queue_builder import generate_id

    pub_id = generate_id("PUB")
    queue_id = generate_id("QUEUE")

    import re
    pub_pattern = r"^PUB_\d{8}_\d{6}_[a-f0-9]{8}$"
    queue_pattern = r"^QUEUE_\d{8}_\d{6}_[a-f0-9]{8}$"

    if re.match(pub_pattern, pub_id):
        test_pass("id_format_pub", f"PUB ID format correct: {pub_id}")
    else:
        test_fail("id_format_pub", f"Invalid format: {pub_id}")

    if re.match(queue_pattern, queue_id):
        test_pass("id_format_queue", f"QUEUE ID format correct: {queue_id}")
    else:
        test_fail("id_format_queue", f"Invalid format: {queue_id}")


def test_qa_gate_check():
    """Test QA gate approval check."""
    from publish_queue_builder import check_qa_gate

    approved_qa = {"gate_result": "approved"}
    rejected_qa = {"gate_result": "rejected"}
    empty_qa = {}

    ok, msg = check_qa_gate(approved_qa)
    if ok:
        test_pass("qa_gate_approved", "Approved gate passes")
    else:
        test_fail("qa_gate_approved", f"Should pass: {msg}")

    ok, msg = check_qa_gate(rejected_qa)
    if not ok:
        test_pass("qa_gate_rejected", "Rejected gate fails")
    else:
        test_fail("qa_gate_rejected", "Should fail")

    ok, msg = check_qa_gate(empty_qa)
    if not ok:
        test_pass("qa_gate_empty", "Empty gate fails")
    else:
        test_fail("qa_gate_empty", "Should fail")


def test_hash_loading():
    """Test loading known hashes from JSONL."""
    from publish_queue_builder import load_known_hashes, QUEUE_JSONL

    # Create temp JSONL with test data
    test_dir = tempfile.mkdtemp()
    test_jsonl = Path(test_dir) / "test_queue.jsonl"

    test_entries = [
        {"master_sha256": "hash1" + "0" * 59},
        {"master_sha256": "hash2" + "0" * 59},
        {"master_sha256": "hash1" + "0" * 59},  # Duplicate
    ]

    with open(test_jsonl, "w") as f:
        for entry in test_entries:
            f.write(json.dumps(entry) + "\n")

    # Temporarily override path
    import publish_queue_builder as pqb
    original_path = pqb.QUEUE_JSONL
    pqb.QUEUE_JSONL = test_jsonl

    try:
        hashes = load_known_hashes()
        if len(hashes) == 2:  # Deduped
            test_pass("hash_loading", f"Loaded {len(hashes)} unique hashes")
        else:
            test_fail("hash_loading", f"Expected 2 unique, got {len(hashes)}")
    finally:
        pqb.QUEUE_JSONL = original_path
        shutil.rmtree(test_dir)


def test_degraded_mode_fields():
    """Test that degraded snapshot has required fields."""
    from publish_queue_builder import write_snapshot

    # Create temp directory for test
    test_dir = tempfile.mkdtemp()
    test_snapshot = Path(test_dir) / "test_snapshot.json"

    import publish_queue_builder as pqb
    original_path = pqb.QUEUE_SNAPSHOT
    pqb.QUEUE_SNAPSHOT = test_snapshot

    try:
        snapshot = write_snapshot([], "degraded", "Test degraded reason")

        if snapshot.get("status") == "degraded" and snapshot.get("degraded_reason"):
            test_pass("degraded_mode_fields", "Degraded snapshot has status and reason")
        else:
            test_fail("degraded_mode_fields", "Missing degraded fields")
    finally:
        pqb.QUEUE_SNAPSHOT = original_path
        shutil.rmtree(test_dir)


def test_nats_topic():
    """Test NATS topic constant is set correctly."""
    from publish_queue_builder import NATS_TOPIC

    if NATS_TOPIC == "ghost.publish.queue":
        test_pass("nats_topic", f"Topic: {NATS_TOPIC}")
    else:
        test_fail("nats_topic", f"Wrong topic: {NATS_TOPIC}")


def main():
    print("=" * 60)
    print("SKYBEAM Publish Queue Builder Selftest (STORY-021)")
    print("=" * 60)

    test_schema_valid()
    test_entry_structure()
    test_id_format()
    test_qa_gate_check()
    test_hash_loading()
    test_degraded_mode_fields()
    test_nats_topic()

    print("=" * 60)
    print(f"Results: {TESTS_PASSED} passed, {TESTS_FAILED} failed")
    print("=" * 60)

    return 0 if TESTS_FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
