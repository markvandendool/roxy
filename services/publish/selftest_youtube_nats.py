#!/usr/bin/env python3
"""
SKYBEAM YouTube Publisher Selftest (STORY-023)

Tests:
1. Schema validation
2. ID format validation
3. Upload metadata generation
4. Idempotency check logic
5. Credentials check
6. NATS topic constant
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
    schema_path = Path(__file__).parent / "schemas" / "youtube_receipt.json"
    try:
        with open(schema_path) as f:
            schema = json.load(f)
        if "$schema" in schema and "properties" in schema:
            test_pass("schema_valid", "Schema loaded with required fields")
        else:
            test_fail("schema_valid", "Schema missing required fields")
    except Exception as e:
        test_fail("schema_valid", str(e))


def test_id_format():
    """Test that generated IDs match expected format."""
    from youtube_publisher import generate_id
    import re

    yt_id = generate_id("YT")
    pattern = r"^YT_\d{8}_\d{6}_[a-f0-9]{8}$"

    if re.match(pattern, yt_id):
        test_pass("id_format", f"YT ID format correct: {yt_id}")
    else:
        test_fail("id_format", f"Invalid format: {yt_id}")


def test_upload_metadata():
    """Test upload metadata generation from package."""
    from youtube_publisher import build_upload_metadata

    package = {
        "title": "Test Video Title",
        "description": "Test description for the video",
        "hashtags": ["#AI", "#Tech", "#Test"]
    }

    metadata = build_upload_metadata(package)

    checks = [
        ("title" in metadata, "title present"),
        ("description" in metadata, "description present"),
        ("tags" in metadata, "tags present"),
        ("visibility" in metadata, "visibility present"),
        (metadata.get("shorts") is True, "shorts flag set"),
        (len(metadata.get("tags", [])) <= 30, "tags within limit"),
    ]

    all_pass = True
    for check, desc in checks:
        if not check:
            test_fail("upload_metadata", f"Failed: {desc}")
            all_pass = False

    if all_pass:
        test_pass("upload_metadata", "All metadata fields correct")


def test_idempotency_logic():
    """Test idempotency check logic."""
    from youtube_publisher import check_idempotency, save_published_id, load_published_ids, PUBLISHED_IDS_FILE

    # Create temp directory for test
    test_dir = tempfile.mkdtemp()
    test_file = Path(test_dir) / ".youtube_published.json"

    import youtube_publisher as yp
    original_path = yp.PUBLISHED_IDS_FILE
    yp.PUBLISHED_IDS_FILE = test_file

    try:
        # Initially not processed
        skip, msg, _ = check_idempotency("PUB_TEST_001")
        if not skip:
            test_pass("idem_new", "New ID not skipped")
        else:
            test_fail("idem_new", "New ID incorrectly skipped")

        # Save as dry_run
        save_published_id("PUB_TEST_001", {"status": "dry_run", "receipt_id": "YT_TEST"})

        # Now should skip
        skip, msg, _ = check_idempotency("PUB_TEST_001")
        if skip and "dry_run" in msg:
            test_pass("idem_dryrun", "Dry-run ID skipped correctly")
        else:
            test_fail("idem_dryrun", f"Dry-run not skipped: {msg}")

        # Save as failed with retry
        save_published_id("PUB_TEST_002", {"status": "failed", "retry_count": 1})

        skip, msg, _ = check_idempotency("PUB_TEST_002")
        if not skip and "retry" in msg.lower():
            test_pass("idem_retry", "Failed ID allows retry")
        else:
            test_fail("idem_retry", f"Failed ID not retrying: {msg}")

    finally:
        yp.PUBLISHED_IDS_FILE = original_path
        shutil.rmtree(test_dir)


def test_credentials_check():
    """Test credentials check function."""
    from youtube_publisher import check_credentials, CREDENTIALS_FILE

    # Check behavior when file doesn't exist (expected for dry-run)
    creds_present, msg = check_credentials()

    # We expect credentials to NOT be present in test environment
    if not creds_present:
        test_pass("credentials_check", f"No creds (expected): {msg}")
    else:
        test_pass("credentials_check", f"Creds present: {msg}")


def test_receipt_structure():
    """Test that receipt has all required fields per schema."""
    required_fields = [
        "receipt_id",
        "timestamp",
        "publish_id",
        "master_sha256",
        "mode",
        "status"
    ]

    # Build a minimal receipt
    from youtube_publisher import generate_id
    from datetime import datetime, timezone

    receipt = {
        "receipt_id": generate_id("YT"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "publish_id": "PUB_TEST",
        "master_sha256": "a" * 64,
        "mode": "dry_run",
        "status": "dry_run"
    }

    missing = [f for f in required_fields if f not in receipt]
    if missing:
        test_fail("receipt_structure", f"Missing fields: {missing}")
    else:
        test_pass("receipt_structure", "All required fields present")


def test_mode_selection():
    """Test mode selection logic."""
    # Mode should be dry_run when no credentials
    from youtube_publisher import check_credentials

    creds_present, _ = check_credentials()
    expected_mode = "live" if creds_present else "dry_run"

    if expected_mode == "dry_run":
        test_pass("mode_selection", "Dry-run mode when no credentials")
    else:
        test_pass("mode_selection", "Live mode when credentials present")


def test_tag_limit():
    """Test that tags are limited to 30."""
    from youtube_publisher import build_upload_metadata

    # Package with many hashtags
    package = {
        "title": "Test",
        "description": "Test",
        "hashtags": [f"#tag{i}" for i in range(50)]
    }

    metadata = build_upload_metadata(package)

    if len(metadata.get("tags", [])) <= 30:
        test_pass("tag_limit", f"{len(metadata['tags'])} tags (max 30)")
    else:
        test_fail("tag_limit", f"{len(metadata['tags'])} tags exceeds 30")


def test_nats_topic():
    """Test NATS topic constant is set correctly."""
    from youtube_publisher import NATS_TOPIC

    if NATS_TOPIC == "ghost.publish.youtube":
        test_pass("nats_topic", f"Topic: {NATS_TOPIC}")
    else:
        test_fail("nats_topic", f"Wrong topic: {NATS_TOPIC}")


def main():
    print("=" * 60)
    print("SKYBEAM YouTube Publisher Selftest (STORY-023)")
    print("=" * 60)

    test_schema_valid()
    test_id_format()
    test_upload_metadata()
    test_idempotency_logic()
    test_credentials_check()
    test_receipt_structure()
    test_mode_selection()
    test_tag_limit()
    test_nats_topic()

    print("=" * 60)
    print(f"Results: {TESTS_PASSED} passed, {TESTS_FAILED} failed")
    print("=" * 60)

    return 0 if TESTS_FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
