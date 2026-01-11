#!/usr/bin/env python3
"""
SKYBEAM Asset QA Gate (STORY-016)
==================================

Validates all asset artifacts before dispatch.

Input:  ~/.roxy/content-pipeline/assets/storyboards/storyboards_latest.json
Output: ~/.roxy/content-pipeline/assets/qa/asset_qa_latest.json
NATS:   ghost.asset.qa

Usage:
    python3 asset_qa_gate.py              # Normal run
    python3 asset_qa_gate.py --test-degraded  # Test degraded mode
"""

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import uuid

# Paths
STORYBOARDS_FILE = Path.home() / ".roxy/content-pipeline/assets/storyboards/storyboards_latest.json"
BRIEFS_FILE = Path.home() / ".roxy/content-pipeline/assets/briefs/asset_briefs_latest.json"
PACKS_FILE = Path.home() / ".roxy/content-pipeline/assets/prompts/prompt_packs_latest.json"
OUTPUT_DIR = Path.home() / ".roxy/content-pipeline/assets/qa"
OUTPUT_FILE = OUTPUT_DIR / "asset_qa_latest.json"

# NATS config
NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")
NATS_TOPIC = "ghost.asset.qa"

# Lint rules
DISALLOWED_WORDS = ["guaranteed", "100%", "proven", "best ever", "miracle"]
REQUIRED_ASSET_TYPES = ["thumbnail", "intro_card", "end_card"]
MIN_PROMPT_LENGTH = 20
MAX_PROMPT_LENGTH = 500


def load_json_file(path: Path) -> tuple[Optional[dict], Optional[str]]:
    """Load JSON from file."""
    if not path.exists():
        return None, f"File not found: {path}"
    try:
        with open(path) as f:
            data = json.load(f)
        return data, None
    except Exception as e:
        return None, f"Failed to load {path}: {e}"


def generate_check_id(script_id: str, check_num: int) -> str:
    """Generate check ID."""
    script_slug = script_id.replace("SCR_", "")[:8]
    return f"CHK_{script_slug}_{check_num:03d}"


def check_prompt_length(prompt: str) -> tuple[str, str]:
    """Check if prompt is within acceptable length."""
    length = len(prompt)
    if length < MIN_PROMPT_LENGTH:
        return "fail", f"Prompt too short ({length} chars, min {MIN_PROMPT_LENGTH})"
    elif length > MAX_PROMPT_LENGTH:
        return "warn", f"Prompt exceeds recommended length ({length} chars, max {MAX_PROMPT_LENGTH})"
    return "pass", f"Prompt length OK ({length} chars)"


def check_disallowed_words(text: str) -> tuple[str, str, list]:
    """Check for disallowed words."""
    found = []
    text_lower = text.lower()
    for word in DISALLOWED_WORDS:
        if word.lower() in text_lower:
            found.append(word)

    if found:
        return "fail", f"Contains disallowed words: {', '.join(found)}", found
    return "pass", "No disallowed words found", []


def check_asset_coverage(prompts: list) -> tuple[str, str, list]:
    """Check that required asset types are present."""
    present_types = set(p.get("asset_type") for p in prompts)
    missing = []
    for req in REQUIRED_ASSET_TYPES:
        if req not in present_types:
            missing.append(req)

    if missing:
        return "fail", f"Missing required asset types: {', '.join(missing)}", missing
    return "pass", "All required asset types present", []


def check_timecode_format(timecode: str) -> tuple[str, str]:
    """Check timecode format is valid."""
    pattern = r"^\d{2}:\d{2}:\d{2}:\d{2}$"
    if re.match(pattern, timecode):
        return "pass", f"Valid timecode format: {timecode}"
    return "fail", f"Invalid timecode format: {timecode}"


def check_frame_scene_mapping(frames: list) -> tuple[str, str]:
    """Check that frames have valid scene mappings."""
    missing_scenes = []
    for frame in frames:
        scene_id = frame.get("scene_id", "")
        if not scene_id or not scene_id.startswith("SCENE_"):
            missing_scenes.append(frame.get("frame_id", "unknown"))

    if missing_scenes:
        return "warn", f"Frames missing scene mapping: {len(missing_scenes)} frames"
    return "pass", f"All {len(frames)} frames have valid scene mappings"


def run_qa_checks(storyboard: dict, packs_data: Optional[dict]) -> dict:
    """Run all QA checks on a storyboard."""
    script_id = storyboard.get("script_id", "")
    frames = storyboard.get("frames", [])
    shotlist = storyboard.get("shotlist", [])

    # Get corresponding prompts from pack
    prompts = []
    if packs_data:
        for pack in packs_data.get("packs", []):
            if pack.get("script_id") == script_id:
                prompts = pack.get("prompts", [])
                break

    checks = []
    check_num = 0

    # Check 1: Asset coverage
    check_num += 1
    result, message, missing = check_asset_coverage(prompts)
    checks.append({
        "check_id": generate_check_id(script_id, check_num),
        "check_type": "asset_coverage",
        "target": script_id,
        "result": result,
        "message": message,
        "details": {"missing_types": missing} if missing else {}
    })

    # Check 2: Frame-scene mapping
    check_num += 1
    result, message = check_frame_scene_mapping(frames)
    checks.append({
        "check_id": generate_check_id(script_id, check_num),
        "check_type": "scene_mapping",
        "target": script_id,
        "result": result,
        "message": message,
        "details": {"frame_count": len(frames)}
    })

    # Check 3-N: Prompt quality checks
    for prompt in prompts[:5]:  # Spot check first 5 prompts
        prompt_text = prompt.get("prompt", "")
        asset_id = prompt.get("asset_id", "")

        # Length check
        check_num += 1
        result, message = check_prompt_length(prompt_text)
        checks.append({
            "check_id": generate_check_id(script_id, check_num),
            "check_type": "prompt_length",
            "target": asset_id,
            "result": result,
            "message": message,
            "details": {"length": len(prompt_text)}
        })

        # Disallowed words check
        check_num += 1
        result, message, found = check_disallowed_words(prompt_text)
        checks.append({
            "check_id": generate_check_id(script_id, check_num),
            "check_type": "content_policy",
            "target": asset_id,
            "result": result,
            "message": message,
            "details": {"found_words": found} if found else {}
        })

    # Check timecodes
    for frame in frames[:3]:  # Spot check first 3 frames
        check_num += 1
        timecode = frame.get("timecode", "")
        result, message = check_timecode_format(timecode)
        checks.append({
            "check_id": generate_check_id(script_id, check_num),
            "check_type": "timecode_format",
            "target": frame.get("frame_id", ""),
            "result": result,
            "message": message,
            "details": {}
        })

    # Calculate totals
    passed = sum(1 for c in checks if c["result"] == "pass")
    failed = sum(1 for c in checks if c["result"] == "fail")
    warnings = sum(1 for c in checks if c["result"] == "warn")

    # Determine gate status
    if failed > 0:
        gate_status = "blocked"
    elif warnings > 2:
        gate_status = "review_required"
    else:
        gate_status = "approved"

    return {
        "script_id": script_id,
        "checks": checks,
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
        "gate_status": gate_status
    }


def generate_qa_report(
    storyboards_data: Optional[dict],
    test_degraded: bool = False
) -> dict:
    """Generate QA report from storyboards."""
    timestamp = datetime.now(timezone.utc).isoformat()
    short_id = uuid.uuid4().hex[:8]
    qa_id = f"QA_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{short_id}"

    # Degraded mode
    if test_degraded or storyboards_data is None:
        return {
            "qa_id": qa_id,
            "timestamp": timestamp,
            "status": "degraded",
            "source_storyboard": None,
            "qa_reports": [],
            "summary": {
                "total_checks": 0,
                "total_passed": 0,
                "total_failed": 0,
                "total_warnings": 0,
                "gate_result": "blocked"
            },
            "meta": {
                "version": "1.0.0",
                "service": "asset_qa_gate",
                "story_id": "SKYBEAM-STORY-016",
                "report_count": 0,
                "degraded": True
            }
        }

    # Load packs for cross-referencing
    packs_data, _ = load_json_file(PACKS_FILE)

    storyboards = storyboards_data.get("storyboards", [])
    qa_reports = []
    total_checks = 0
    total_passed = 0
    total_failed = 0
    total_warnings = 0

    for storyboard in storyboards:
        report = run_qa_checks(storyboard, packs_data)
        qa_reports.append(report)
        total_checks += len(report["checks"])
        total_passed += report["passed"]
        total_failed += report["failed"]
        total_warnings += report["warnings"]

    # Determine overall gate result
    if total_failed > 0:
        gate_result = "blocked"
    elif total_warnings > 5:
        gate_result = "review_required"
    else:
        gate_result = "approved"

    # Determine status
    if not qa_reports:
        status = "degraded"
    elif total_failed > 0:
        status = "partial"
    else:
        status = "healthy"

    return {
        "qa_id": qa_id,
        "timestamp": timestamp,
        "status": status,
        "source_storyboard": storyboards_data.get("storyboard_id"),
        "qa_reports": qa_reports,
        "summary": {
            "total_checks": total_checks,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_warnings": total_warnings,
            "gate_result": gate_result
        },
        "meta": {
            "version": "1.0.0",
            "service": "asset_qa_gate",
            "story_id": "SKYBEAM-STORY-016",
            "report_count": len(qa_reports),
            "degraded": status == "degraded"
        }
    }


def validate_schema(data: dict) -> tuple[bool, Optional[str]]:
    """Validate QA report against schema."""
    required = ["qa_id", "timestamp", "status", "source_storyboard", "qa_reports", "summary", "meta"]
    for field in required:
        if field not in data:
            return False, f"Missing required field: {field}"

    if data["status"] not in ["healthy", "partial", "degraded"]:
        return False, f"Invalid status: {data['status']}"

    return True, None


def write_qa_report(report: dict) -> None:
    """Write QA report to output file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(report, f, indent=2)


async def publish_to_nats(report: dict) -> bool:
    """Publish QA report to NATS."""
    try:
        import nats
        nc = await nats.connect(NATS_URL)
        payload = json.dumps(report).encode()
        await nc.publish(NATS_TOPIC, payload)
        await nc.flush()
        await nc.close()
        return True
    except Exception as e:
        print(f"NATS publish error: {e}", file=sys.stderr)
        return False


async def run_once(test_degraded: bool = False) -> dict:
    """Run a single QA cycle."""
    print("=" * 70)
    print("  SKYBEAM Asset QA Gate (STORY-016)")
    print("=" * 70)

    # Load storyboards
    print("\n[1] Loading storyboards...")
    storyboards_data, error = load_json_file(STORYBOARDS_FILE)
    if error:
        print(f"  Warning: {error}")
    else:
        print(f"  Loaded: {storyboards_data.get('storyboard_id')}")

    # Generate QA report
    print("[2] Running QA checks...")
    report = generate_qa_report(storyboards_data, test_degraded=test_degraded)
    print(f"  QA ID: {report['qa_id']}")
    print(f"  Status: {report['status']}")
    print(f"  Reports: {report['meta']['report_count']}")
    print(f"  Checks: {report['summary']['total_checks']}")
    print(f"  Passed: {report['summary']['total_passed']}")
    print(f"  Failed: {report['summary']['total_failed']}")
    print(f"  Warnings: {report['summary']['total_warnings']}")
    print(f"  Gate: {report['summary']['gate_result']}")

    # Validate
    print("[3] Validating schema...")
    valid, error = validate_schema(report)
    if not valid:
        print(f"  FAIL: {error}")
        return report
    print(f"  Schema: VALID")

    # Write
    print("[4] Writing output...")
    write_qa_report(report)
    print(f"  File written: {OUTPUT_FILE}")

    # Publish
    print("[5] Publishing to NATS...")
    nats_ok = await publish_to_nats(report)
    print(f"  NATS published: {nats_ok}")

    # Summary
    print("=" * 70)
    print("  PROOF ARTIFACTS:")
    print(f"  - File: {OUTPUT_FILE}")
    print(f"  - QA ID: {report['qa_id']}")
    print(f"  - Status: {report['status']}")
    print(f"  - Gate Result: {report['summary']['gate_result']}")
    print(f"  - Checks: {report['summary']['total_passed']}/{report['summary']['total_checks']} passed")
    print(f"  - NATS: {nats_ok}")
    print("=" * 70)

    return report


def main():
    parser = argparse.ArgumentParser(description="SKYBEAM Asset QA Gate")
    parser.add_argument("--test-degraded", action="store_true", help="Test degraded mode")
    args = parser.parse_args()

    asyncio.run(run_once(test_degraded=args.test_degraded))


if __name__ == "__main__":
    main()
