#!/usr/bin/env python3
"""
SKYBEAM Production QA Gate (STORY-020)
=======================================

Final acceptance gate for master output.

Input:
  ~/.roxy/content-pipeline/production/master/master_latest.mp4
  ~/.roxy/content-pipeline/production/master/master_latest.json

Output:
  ~/.roxy/content-pipeline/production/qa/production_qa_latest.json

NATS:
  ghost.prod.qa

Checks:
  - File exists + bytes > 0
  - ffprobe succeeds
  - Resolution EXACT (1080x1920)
  - Duration <= 60.5s
  - Audio stream present
  - Manifest sha256 matches mp4
"""

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import uuid

# Paths
MASTER_MP4 = Path.home() / ".roxy/content-pipeline/production/master/master_latest.mp4"
MASTER_JSON = Path.home() / ".roxy/content-pipeline/production/master/master_latest.json"
OUTPUT_DIR = Path.home() / ".roxy/content-pipeline/production/qa"
OUTPUT_FILE = OUTPUT_DIR / "production_qa_latest.json"

# NATS config
NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")
NATS_TOPIC = "ghost.prod.qa"

# QA requirements
REQUIRED_WIDTH = 1080
REQUIRED_HEIGHT = 1920
MAX_DURATION = 60.5


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


def calculate_sha256(path: Path) -> str:
    """Calculate SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_ffprobe_data(path: Path) -> Optional[dict]:
    """Get ffprobe data from video file."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", str(path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except Exception:
        return None


def run_checks(master_data: Optional[dict]) -> list:
    """Run all QA checks on master output."""
    checks = []
    check_num = 0

    # Check 1: File exists
    check_num += 1
    if MASTER_MP4.exists():
        checks.append({
            "check_id": f"CHK_PROD_{check_num:03d}",
            "check_type": "file_exists",
            "result": "pass",
            "message": f"Master file exists: {MASTER_MP4}"
        })
    else:
        checks.append({
            "check_id": f"CHK_PROD_{check_num:03d}",
            "check_type": "file_exists",
            "result": "fail",
            "message": f"Master file not found: {MASTER_MP4}"
        })
        return checks  # Early exit

    # Check 2: File size > 0
    check_num += 1
    file_size = MASTER_MP4.stat().st_size
    if file_size > 0:
        checks.append({
            "check_id": f"CHK_PROD_{check_num:03d}",
            "check_type": "file_size",
            "result": "pass",
            "message": f"File size: {file_size} bytes",
            "actual": file_size
        })
    else:
        checks.append({
            "check_id": f"CHK_PROD_{check_num:03d}",
            "check_type": "file_size",
            "result": "fail",
            "message": "File is empty (0 bytes)",
            "actual": 0
        })

    # Check 3: ffprobe succeeds
    check_num += 1
    ffprobe_data = get_ffprobe_data(MASTER_MP4)
    if ffprobe_data:
        checks.append({
            "check_id": f"CHK_PROD_{check_num:03d}",
            "check_type": "ffprobe",
            "result": "pass",
            "message": "ffprobe succeeded"
        })
    else:
        checks.append({
            "check_id": f"CHK_PROD_{check_num:03d}",
            "check_type": "ffprobe",
            "result": "fail",
            "message": "ffprobe failed - invalid video file"
        })
        return checks  # Early exit

    # Extract stream info
    streams = ffprobe_data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = ffprobe_data.get("format", {})

    # Check 4: Resolution EXACT (1080x1920)
    check_num += 1
    actual_width = video_stream.get("width", 0)
    actual_height = video_stream.get("height", 0)
    if actual_width == REQUIRED_WIDTH and actual_height == REQUIRED_HEIGHT:
        checks.append({
            "check_id": f"CHK_PROD_{check_num:03d}",
            "check_type": "resolution",
            "result": "pass",
            "message": f"Resolution: {actual_width}x{actual_height}",
            "expected": f"{REQUIRED_WIDTH}x{REQUIRED_HEIGHT}",
            "actual": f"{actual_width}x{actual_height}"
        })
    else:
        checks.append({
            "check_id": f"CHK_PROD_{check_num:03d}",
            "check_type": "resolution",
            "result": "fail",
            "message": f"Resolution mismatch: expected {REQUIRED_WIDTH}x{REQUIRED_HEIGHT}, got {actual_width}x{actual_height}",
            "expected": f"{REQUIRED_WIDTH}x{REQUIRED_HEIGHT}",
            "actual": f"{actual_width}x{actual_height}"
        })

    # Check 5: Duration <= 60.5s
    check_num += 1
    actual_duration = float(fmt.get("duration", 0))
    if actual_duration <= MAX_DURATION:
        checks.append({
            "check_id": f"CHK_PROD_{check_num:03d}",
            "check_type": "duration",
            "result": "pass",
            "message": f"Duration: {actual_duration:.1f}s (max {MAX_DURATION}s)",
            "expected": MAX_DURATION,
            "actual": actual_duration
        })
    else:
        checks.append({
            "check_id": f"CHK_PROD_{check_num:03d}",
            "check_type": "duration",
            "result": "fail",
            "message": f"Duration exceeds limit: {actual_duration:.1f}s > {MAX_DURATION}s",
            "expected": MAX_DURATION,
            "actual": actual_duration
        })

    # Check 6: Audio stream present
    check_num += 1
    if audio_stream:
        checks.append({
            "check_id": f"CHK_PROD_{check_num:03d}",
            "check_type": "audio",
            "result": "pass",
            "message": f"Audio stream present: {audio_stream.get('codec_name', 'unknown')}"
        })
    else:
        checks.append({
            "check_id": f"CHK_PROD_{check_num:03d}",
            "check_type": "audio",
            "result": "fail",
            "message": "No audio stream found"
        })

    # Check 7: SHA256 matches manifest
    check_num += 1
    if master_data and master_data.get("file_proof"):
        manifest_sha = master_data["file_proof"].get("sha256", "")
        actual_sha = calculate_sha256(MASTER_MP4)
        if manifest_sha == actual_sha:
            checks.append({
                "check_id": f"CHK_PROD_{check_num:03d}",
                "check_type": "sha256",
                "result": "pass",
                "message": f"SHA256 matches manifest: {actual_sha[:16]}..."
            })
        else:
            checks.append({
                "check_id": f"CHK_PROD_{check_num:03d}",
                "check_type": "sha256",
                "result": "fail",
                "message": f"SHA256 mismatch: manifest={manifest_sha[:16]}..., actual={actual_sha[:16]}..."
            })
    else:
        checks.append({
            "check_id": f"CHK_PROD_{check_num:03d}",
            "check_type": "sha256",
            "result": "warn",
            "message": "No manifest file_proof to verify SHA256"
        })

    return checks


def generate_qa_report(
    master_data: Optional[dict],
    test_degraded: bool = False
) -> dict:
    """Generate production QA report."""
    timestamp = datetime.now(timezone.utc).isoformat()
    short_id = uuid.uuid4().hex[:8]
    qa_id = f"PROD_QA_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{short_id}"

    # Degraded mode
    if test_degraded:
        return {
            "qa_id": qa_id,
            "timestamp": timestamp,
            "status": "degraded",
            "source_master": None,
            "checks": [],
            "gate_result": "rejected",
            "meta": {
                "version": "1.0.0",
                "service": "production_qa_gate",
                "story_id": "SKYBEAM-STORY-020",
                "check_count": 0,
                "passed": 0,
                "failed": 0,
                "degraded": True,
                "reason": "Test degraded mode"
            }
        }

    # Run checks
    checks = run_checks(master_data)

    # Calculate results
    passed = sum(1 for c in checks if c["result"] == "pass")
    failed = sum(1 for c in checks if c["result"] == "fail")

    # Gate result
    gate_result = "approved" if failed == 0 else "rejected"

    # Status
    if not checks:
        status = "degraded"
    elif failed > 0:
        status = "partial"
    else:
        status = "healthy"

    return {
        "qa_id": qa_id,
        "timestamp": timestamp,
        "status": status,
        "source_master": master_data.get("master_id") if master_data else None,
        "checks": checks,
        "gate_result": gate_result,
        "meta": {
            "version": "1.0.0",
            "service": "production_qa_gate",
            "story_id": "SKYBEAM-STORY-020",
            "check_count": len(checks),
            "passed": passed,
            "failed": failed,
            "degraded": status == "degraded"
        }
    }


def validate_schema(data: dict) -> tuple[bool, Optional[str]]:
    """Validate QA report against schema."""
    required = ["qa_id", "timestamp", "status", "source_master", "checks", "gate_result", "meta"]
    for field in required:
        if field not in data:
            return False, f"Missing required field: {field}"

    if data["status"] not in ["healthy", "partial", "degraded"]:
        return False, f"Invalid status: {data['status']}"

    if data["gate_result"] not in ["approved", "rejected"]:
        return False, f"Invalid gate_result: {data['gate_result']}"

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
    print("  SKYBEAM Production QA Gate (STORY-020)")
    print("=" * 70)

    # Load master manifest
    print("\n[1] Loading master manifest...")
    master_data, error = load_json_file(MASTER_JSON)
    if error:
        print(f"  Warning: {error}")
    else:
        print(f"  Loaded: {master_data.get('master_id')}")

    # Generate QA report
    print("[2] Running QA checks...")
    report = generate_qa_report(master_data, test_degraded=test_degraded)
    print(f"  QA ID: {report['qa_id']}")
    print(f"  Status: {report['status']}")
    print(f"  Checks: {report['meta']['check_count']}")
    print(f"  Passed: {report['meta']['passed']}")
    print(f"  Failed: {report['meta']['failed']}")
    print(f"  Gate: {report['gate_result']}")

    # Show check details
    for check in report.get("checks", []):
        icon = "OK" if check["result"] == "pass" else ("!!" if check["result"] == "fail" else "??")
        print(f"  [{icon}] {check['check_type']}: {check['message'][:50]}")

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
    print(f"  - Gate: {report['gate_result']}")
    print(f"  - Checks: {report['meta']['passed']}/{report['meta']['check_count']} passed")
    print(f"  - NATS: {nats_ok}")
    print("=" * 70)

    return report


def main():
    parser = argparse.ArgumentParser(description="SKYBEAM Production QA Gate")
    parser.add_argument("--test-degraded", action="store_true", help="Test degraded mode")
    args = parser.parse_args()

    asyncio.run(run_once(test_degraded=args.test_degraded))


if __name__ == "__main__":
    main()
