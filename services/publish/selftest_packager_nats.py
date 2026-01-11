#!/usr/bin/env python3
"""
SKYBEAM Publish Packager Selftest (STORY-022)

Tests:
1. Schema validation
2. Caption generation (normal + fallback)
3. SRT time formatting
4. Idempotency hash tracking
5. QA gate check
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
    schema_path = Path(__file__).parent / "schemas" / "publish_package.json"
    try:
        with open(schema_path) as f:
            schema = json.load(f)
        if "$schema" in schema and "definitions" in schema:
            test_pass("schema_valid", "Schema loaded with required fields")
        else:
            test_fail("schema_valid", "Schema missing required fields")
    except Exception as e:
        test_fail("schema_valid", str(e))


def test_srt_time_format():
    """Test SRT time formatting."""
    from publish_packager import format_srt_time

    tests = [
        (0.0, "00:00:00,000"),
        (1.5, "00:00:01,500"),
        (65.123, "00:01:05,123"),
        (3661.999, "01:01:01,999"),  # FP edge case - now handled correctly
    ]

    all_pass = True
    for seconds, expected in tests:
        result = format_srt_time(seconds)
        if result != expected:
            test_fail("srt_time_format", f"{seconds}s -> {result} (expected {expected})")
            all_pass = False

    if all_pass:
        test_pass("srt_time_format", "All time formats correct")


def test_caption_generation():
    """Test caption generation from text."""
    from publish_packager import generate_captions

    text = "This is the first sentence. Here is another one. And a third."
    duration = 10.0

    segments = generate_captions(text, duration)

    if len(segments) >= 2:
        test_pass("caption_generation", f"{len(segments)} segments from 3 sentences")
    else:
        test_fail("caption_generation", f"Only {len(segments)} segments")

    # Check segment structure
    if segments:
        seg = segments[0]
        required = ["index", "start_time", "end_time", "text"]
        missing = [f for f in required if f not in seg]
        if missing:
            test_fail("caption_structure", f"Missing fields: {missing}")
        else:
            test_pass("caption_structure", "All required fields present")


def test_fallback_captions():
    """Test fallback caption generation for empty text."""
    from publish_packager import generate_captions, generate_fallback_captions

    # Empty text should trigger fallback
    segments = generate_captions("", 10.0)

    if len(segments) >= 2:
        test_pass("fallback_captions", f"{len(segments)} fallback segments")
    else:
        test_fail("fallback_captions", f"Only {len(segments)} segments")

    # Direct fallback test
    fallback = generate_fallback_captions(10.0)
    if fallback and "SKYBEAM" in fallback[0].get("text", ""):
        test_pass("fallback_content", "Fallback contains SKYBEAM branding")
    else:
        test_fail("fallback_content", "Fallback missing branding")


def test_caption_duration_bounds():
    """Test that caption durations are within bounds."""
    from publish_packager import generate_captions, MIN_CAPTION_DURATION, MAX_CAPTION_DURATION

    text = "Short. " * 20  # Many short sentences
    duration = 60.0

    segments = generate_captions(text, duration)

    all_valid = True
    for seg in segments:
        # Parse times and check duration
        start = seg["start_time"]
        end = seg["end_time"]
        # Simple parse for testing
        start_parts = start.replace(",", ":").split(":")
        end_parts = end.replace(",", ":").split(":")
        start_sec = int(start_parts[0]) * 3600 + int(start_parts[1]) * 60 + int(start_parts[2]) + int(start_parts[3]) / 1000
        end_sec = int(end_parts[0]) * 3600 + int(end_parts[1]) * 60 + int(end_parts[2]) + int(end_parts[3]) / 1000
        seg_dur = end_sec - start_sec

        if seg_dur < MIN_CAPTION_DURATION - 0.1 or seg_dur > MAX_CAPTION_DURATION + 0.1:
            all_valid = False

    if all_valid:
        test_pass("caption_duration_bounds", f"All segments within {MIN_CAPTION_DURATION}-{MAX_CAPTION_DURATION}s")
    else:
        test_fail("caption_duration_bounds", "Some segments outside bounds")


def test_id_format():
    """Test that generated IDs match expected format."""
    from publish_packager import generate_id
    import re

    pkg_id = generate_id("PKG")
    pattern = r"^PKG_\d{8}_\d{6}_[a-f0-9]{8}$"

    if re.match(pattern, pkg_id):
        test_pass("id_format", f"PKG ID format correct: {pkg_id}")
    else:
        test_fail("id_format", f"Invalid format: {pkg_id}")


def test_qa_gate_check():
    """Test QA gate approval check."""
    from publish_packager import check_qa_gate

    approved_qa = {"gate_result": "approved"}
    rejected_qa = {"gate_result": "rejected"}

    ok, _ = check_qa_gate(approved_qa)
    if ok:
        test_pass("qa_gate_approved", "Approved gate passes")
    else:
        test_fail("qa_gate_approved", "Should pass")

    ok, _ = check_qa_gate(rejected_qa)
    if not ok:
        test_pass("qa_gate_rejected", "Rejected gate fails")
    else:
        test_fail("qa_gate_rejected", "Should fail")


def test_narration_extraction():
    """Test narration text extraction from script."""
    from publish_packager import extract_narration_text

    script = {
        "sections": [
            {"content": "[HOOK] This is the hook."},
            {"content": "[CONTEXT] Some context here."},
            {"content": "[CTA] Subscribe now!"}
        ]
    }

    text = extract_narration_text(script)

    if "[HOOK]" not in text and "This is the hook" in text:
        test_pass("narration_extraction", "Section markers stripped")
    else:
        test_fail("narration_extraction", "Section markers not stripped")


def test_nats_topic():
    """Test NATS topic constant is set correctly."""
    from publish_packager import NATS_TOPIC

    if NATS_TOPIC == "ghost.publish.package":
        test_pass("nats_topic", f"Topic: {NATS_TOPIC}")
    else:
        test_fail("nats_topic", f"Wrong topic: {NATS_TOPIC}")


def main():
    print("=" * 60)
    print("SKYBEAM Publish Packager Selftest (STORY-022)")
    print("=" * 60)

    test_schema_valid()
    test_srt_time_format()
    test_caption_generation()
    test_fallback_captions()
    test_caption_duration_bounds()
    test_id_format()
    test_qa_gate_check()
    test_narration_extraction()
    test_nats_topic()

    print("=" * 60)
    print(f"Results: {TESTS_PASSED} passed, {TESTS_FAILED} failed")
    print("=" * 60)

    return 0 if TESTS_FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
