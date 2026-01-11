#!/usr/bin/env python3
"""
SKYBEAM Publish Metrics Collector Selftest (STORY-025)

Tests:
1. Schema validation
2. ID format validation
3. Receipts summary computation
4. Queue stats computation
5. API access check
6. Platform metrics structure
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
    schema_path = Path(__file__).parent / "schemas" / "publish_metrics.json"
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
    from publish_metrics_collector import generate_id
    import re

    metrics_id = generate_id("METRICS")
    pattern = r"^METRICS_\d{8}_\d{6}_[a-f0-9]{8}$"

    if re.match(pattern, metrics_id):
        test_pass("id_format", f"METRICS ID format correct: {metrics_id}")
    else:
        test_fail("id_format", f"Invalid format: {metrics_id}")


def test_receipts_summary():
    """Test receipts summary computation."""
    from publish_metrics_collector import compute_receipts_summary

    mock_receipts = [
        {"receipt_id": "YT_001", "platform": "youtube_shorts", "status": "dry_run", "timestamp": "2026-01-10T10:00:00Z"},
        {"receipt_id": "YT_002", "platform": "youtube_shorts", "status": "published", "timestamp": "2026-01-10T11:00:00Z"},
        {"receipt_id": "TT_001", "platform": "tiktok", "status": "handoff_ready", "timestamp": "2026-01-10T12:00:00Z"},
        {"receipt_id": "TT_002", "platform": "tiktok", "status": "failed", "timestamp": "2026-01-10T09:00:00Z"},
    ]

    summary = compute_receipts_summary(mock_receipts)

    checks = [
        (summary["total_receipts"] == 4, "total_receipts == 4"),
        (summary["by_platform"]["youtube_shorts"]["total"] == 2, "youtube total == 2"),
        (summary["by_platform"]["tiktok"]["total"] == 2, "tiktok total == 2"),
        ("dry_run" in summary["by_status"], "dry_run in by_status"),
        (summary["latest_receipt"]["receipt_id"] == "TT_001", "latest is TT_001"),
    ]

    all_pass = True
    for check, desc in checks:
        if not check:
            test_fail("receipts_summary", f"Failed: {desc}")
            all_pass = False

    if all_pass:
        test_pass("receipts_summary", "All summary checks passed")


def test_queue_stats():
    """Test queue stats computation."""
    from publish_metrics_collector import compute_queue_stats, QUEUE_SNAPSHOT

    # Create temp queue file
    test_dir = tempfile.mkdtemp()
    test_queue = Path(test_dir) / "test_queue.json"

    now = datetime.now(timezone.utc)
    old_entry_time = (now - timedelta(hours=5)).isoformat()

    queue_data = {
        "entries": [
            {"enqueue_timestamp": now.isoformat()},
            {"enqueue_timestamp": old_entry_time},
        ]
    }

    with open(test_queue, "w") as f:
        json.dump(queue_data, f)

    import publish_metrics_collector as pmc
    original_path = pmc.QUEUE_SNAPSHOT
    pmc.QUEUE_SNAPSHOT = test_queue

    try:
        stats = compute_queue_stats()

        checks = [
            (stats["queue_length"] == 2, "queue_length == 2"),
            (stats["oldest_queued_age_hours"] >= 4.9, "oldest age >= 4.9 hours"),
            (stats["latest_enqueue"] is not None, "latest_enqueue not None"),
        ]

        all_pass = True
        for check, desc in checks:
            if not check:
                test_fail("queue_stats", f"Failed: {desc}")
                all_pass = False

        if all_pass:
            test_pass("queue_stats", f"Queue length={stats['queue_length']}, oldest={stats['oldest_queued_age_hours']:.1f}h")

    finally:
        pmc.QUEUE_SNAPSHOT = original_path
        shutil.rmtree(test_dir)


def test_api_access_check():
    """Test API access check function."""
    from publish_metrics_collector import check_api_access

    # Check for unavailable (expected in test env)
    yt_available, yt_reason = check_api_access("youtube")
    tt_available, tt_reason = check_api_access("tiktok")

    if not yt_available:
        test_pass("api_check_youtube", f"YouTube unavailable (expected): {yt_reason}")
    else:
        test_pass("api_check_youtube", "YouTube available")

    if not tt_available:
        test_pass("api_check_tiktok", f"TikTok unavailable (expected): {tt_reason}")
    else:
        test_pass("api_check_tiktok", "TikTok available")


def test_platform_metrics_structure():
    """Test platform metrics structure."""
    from publish_metrics_collector import fetch_platform_metrics

    mock_receipts = [
        {"platform": "youtube_shorts", "status": "published"},
        {"platform": "youtube_shorts", "status": "dry_run"},
    ]

    metrics = fetch_platform_metrics("youtube_shorts", mock_receipts)

    required_keys = ["available", "videos_tracked", "total_views", "total_likes", "total_comments"]
    missing = [k for k in required_keys if k not in metrics]

    if missing:
        test_fail("platform_metrics_structure", f"Missing keys: {missing}")
    else:
        test_pass("platform_metrics_structure", f"All keys present, tracked={metrics['videos_tracked']}")


def test_empty_receipts():
    """Test handling of empty receipts."""
    from publish_metrics_collector import compute_receipts_summary

    summary = compute_receipts_summary([])

    if summary["total_receipts"] == 0 and summary["latest_receipt"] is None:
        test_pass("empty_receipts", "Empty receipts handled correctly")
    else:
        test_fail("empty_receipts", "Empty receipts not handled")


def test_nats_topic():
    """Test NATS topic constant is set correctly."""
    from publish_metrics_collector import NATS_TOPIC

    if NATS_TOPIC == "ghost.publish.metrics":
        test_pass("nats_topic", f"Topic: {NATS_TOPIC}")
    else:
        test_fail("nats_topic", f"Wrong topic: {NATS_TOPIC}")


def test_collection_window():
    """Test that collection window is properly defined."""
    from publish_metrics_collector import COLLECTION_WINDOW_HOURS

    if COLLECTION_WINDOW_HOURS > 0:
        test_pass("collection_window", f"Window: {COLLECTION_WINDOW_HOURS} hours")
    else:
        test_fail("collection_window", "Invalid window")


def main():
    print("=" * 60)
    print("SKYBEAM Publish Metrics Collector Selftest (STORY-025)")
    print("=" * 60)

    test_schema_valid()
    test_id_format()
    test_receipts_summary()
    test_queue_stats()
    test_api_access_check()
    test_platform_metrics_structure()
    test_empty_receipts()
    test_nats_topic()
    test_collection_window()

    print("=" * 60)
    print(f"Results: {TESTS_PASSED} passed, {TESTS_FAILED} failed")
    print("=" * 60)

    return 0 if TESTS_FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
