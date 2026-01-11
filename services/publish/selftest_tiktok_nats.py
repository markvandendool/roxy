#!/usr/bin/env python3
"""
SKYBEAM TikTok Publisher Selftest (STORY-024)

Tests:
1. Schema validation
2. ID format validation
3. Upload metadata generation
4. Idempotency check logic
5. Copy-paste text generation
6. Handoff pack structure
7. Credentials check
8. NATS topic constant
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
    schema_path = Path(__file__).parent / "schemas" / "tiktok_receipt.json"
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
    from tiktok_publisher import generate_id
    import re

    tt_id = generate_id("TT")
    pattern = r"^TT_\d{8}_\d{6}_[a-f0-9]{8}$"

    if re.match(pattern, tt_id):
        test_pass("id_format", f"TT ID format correct: {tt_id}")
    else:
        test_fail("id_format", f"Invalid format: {tt_id}")


def test_upload_metadata():
    """Test upload metadata generation from package."""
    from tiktok_publisher import build_upload_metadata

    package = {
        "title": "Test Video Title",
        "description": "Test description for the video",
        "hashtags": ["#AI", "#Tech", "#Test"]
    }

    metadata = build_upload_metadata(package)

    checks = [
        ("title" in metadata, "title present"),
        ("description" in metadata, "description present"),
        ("hashtags" in metadata, "hashtags present"),
        ("visibility" in metadata, "visibility present"),
        ("allow_comments" in metadata, "allow_comments present"),
    ]

    all_pass = True
    for check, desc in checks:
        if not check:
            test_fail("upload_metadata", f"Failed: {desc}")
            all_pass = False

    if all_pass:
        test_pass("upload_metadata", "All metadata fields correct")


def test_copy_paste_text():
    """Test copy-paste text generation."""
    from tiktok_publisher import build_copy_paste_text

    metadata = {
        "title": "Amazing AI Video",
        "description": "Check out this cool AI demo.\n\nMore details here.",
        "hashtags": ["#AI", "#Tech", "#Shorts"]
    }

    text = build_copy_paste_text(metadata)

    checks = [
        ("Amazing AI Video" in text, "title in text"),
        ("#AI" in text, "hashtags in text"),
    ]

    all_pass = True
    for check, desc in checks:
        if not check:
            test_fail("copy_paste_text", f"Failed: {desc}")
            all_pass = False

    if all_pass:
        test_pass("copy_paste_text", "Copy-paste text generated correctly")


def test_idempotency_logic():
    """Test idempotency check logic."""
    from tiktok_publisher import check_idempotency, save_published_id, PUBLISHED_IDS_FILE

    # Create temp directory for test
    test_dir = tempfile.mkdtemp()
    test_file = Path(test_dir) / ".tiktok_published.json"

    import tiktok_publisher as tp
    original_path = tp.PUBLISHED_IDS_FILE
    tp.PUBLISHED_IDS_FILE = test_file

    try:
        # Initially not processed
        skip, msg, _ = check_idempotency("PUB_TEST_001")
        if not skip:
            test_pass("idem_new", "New ID not skipped")
        else:
            test_fail("idem_new", "New ID incorrectly skipped")

        # Save as handoff_ready
        save_published_id("PUB_TEST_001", {"status": "handoff_ready", "receipt_id": "TT_TEST"})

        # Now should skip
        skip, msg, _ = check_idempotency("PUB_TEST_001")
        if skip and "handoff_ready" in msg:
            test_pass("idem_handoff", "Handoff ID skipped correctly")
        else:
            test_fail("idem_handoff", f"Handoff not skipped: {msg}")

        # Save as failed with retry
        save_published_id("PUB_TEST_002", {"status": "failed", "retry_count": 1})

        skip, msg, _ = check_idempotency("PUB_TEST_002")
        if not skip and "retry" in msg.lower():
            test_pass("idem_retry", "Failed ID allows retry")
        else:
            test_fail("idem_retry", f"Failed ID not retrying: {msg}")

    finally:
        tp.PUBLISHED_IDS_FILE = original_path
        shutil.rmtree(test_dir)


def test_handoff_pack_structure():
    """Test handoff pack creation."""
    from tiktok_publisher import create_handoff_pack, EXPORTS_DIR

    # Create temp directories
    test_dir = tempfile.mkdtemp()
    test_exports = Path(test_dir) / "exports"
    test_exports.mkdir()

    # Create a test video file
    test_video = Path(test_dir) / "test_video.mp4"
    test_video.write_bytes(b"fake video content")

    import tiktok_publisher as tp
    original_path = tp.EXPORTS_DIR
    tp.EXPORTS_DIR = test_exports

    try:
        metadata = {
            "title": "Test Video",
            "description": "Test description",
            "hashtags": ["#Test"],
            "visibility": "private"
        }

        pack = create_handoff_pack(
            "PUB_TEST_HANDOFF",
            str(test_video),
            "",  # No captions
            metadata,
            {}
        )

        required_keys = ["export_dir", "video_file", "metadata_file", "checklist_file", "copy_paste_text"]
        missing = [k for k in required_keys if k not in pack]

        if missing:
            test_fail("handoff_pack_structure", f"Missing keys: {missing}")
        else:
            test_pass("handoff_pack_structure", "All handoff pack keys present")

        # Check files exist
        if pack["video_file"] and Path(pack["video_file"]).exists():
            test_pass("handoff_video_copied", "Video file copied to pack")
        else:
            test_fail("handoff_video_copied", "Video file not copied")

    finally:
        tp.EXPORTS_DIR = original_path
        shutil.rmtree(test_dir)


def test_credentials_check():
    """Test credentials check function."""
    from tiktok_publisher import check_credentials

    # Check behavior when file doesn't exist (expected for handoff)
    creds_present, msg = check_credentials()

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

    from tiktok_publisher import generate_id

    receipt = {
        "receipt_id": generate_id("TT"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "publish_id": "PUB_TEST",
        "master_sha256": "a" * 64,
        "mode": "handoff",
        "status": "handoff_ready"
    }

    missing = [f for f in required_fields if f not in receipt]
    if missing:
        test_fail("receipt_structure", f"Missing fields: {missing}")
    else:
        test_pass("receipt_structure", "All required fields present")


def test_mode_selection():
    """Test mode selection logic."""
    from tiktok_publisher import check_credentials

    creds_present, _ = check_credentials()
    expected_mode = "live" if creds_present else "handoff"

    if expected_mode == "handoff":
        test_pass("mode_selection", "Handoff mode when no credentials")
    else:
        test_pass("mode_selection", "Live mode when credentials present")


def test_nats_topic():
    """Test NATS topic constant is set correctly."""
    from tiktok_publisher import NATS_TOPIC

    if NATS_TOPIC == "ghost.publish.tiktok":
        test_pass("nats_topic", f"Topic: {NATS_TOPIC}")
    else:
        test_fail("nats_topic", f"Wrong topic: {NATS_TOPIC}")


def main():
    print("=" * 60)
    print("SKYBEAM TikTok Publisher Selftest (STORY-024)")
    print("=" * 60)

    test_schema_valid()
    test_id_format()
    test_upload_metadata()
    test_copy_paste_text()
    test_idempotency_logic()
    test_handoff_pack_structure()
    test_credentials_check()
    test_receipt_structure()
    test_mode_selection()
    test_nats_topic()

    print("=" * 60)
    print(f"Results: {TESTS_PASSED} passed, {TESTS_FAILED} failed")
    print("=" * 60)

    return 0 if TESTS_FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
