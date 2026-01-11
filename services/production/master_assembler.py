#!/usr/bin/env python3
"""
SKYBEAM Master Assembler (STORY-019)
=====================================

Final packaging of rendered video into master output.

Input:
  ~/.roxy/content-pipeline/production/renders/render_result_latest.json
  ~/.roxy/content-pipeline/production/renders/<script_id>/render.mp4

Output:
  ~/.roxy/content-pipeline/production/master/master_latest.mp4
  ~/.roxy/content-pipeline/production/master/master_latest.json

NATS:
  ghost.prod.master

Notes:
  - Copies top successful render to master location
  - Can add watermark/captions here (future)
"""

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import uuid

# Paths
RENDER_RESULT_FILE = Path.home() / ".roxy/content-pipeline/production/renders/render_result_latest.json"
RENDERS_DIR = Path.home() / ".roxy/content-pipeline/production/renders"
REVIEWED_FILE = Path.home() / ".roxy/content-pipeline/scripts/scripts_reviewed.json"
STORYBOARDS_FILE = Path.home() / ".roxy/content-pipeline/assets/storyboards/storyboards_latest.json"
QA_FILE = Path.home() / ".roxy/content-pipeline/assets/qa/asset_qa_latest.json"
OUTPUT_DIR = Path.home() / ".roxy/content-pipeline/production/master"
OUTPUT_MP4 = OUTPUT_DIR / "master_latest.mp4"
OUTPUT_JSON = OUTPUT_DIR / "master_latest.json"

# NATS config
NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")
NATS_TOPIC = "ghost.prod.master"

# Render spec (locked)
RENDER_SPEC = {
    "format": "mp4",
    "aspect": "9:16",
    "resolution": "1080x1920",
    "fps": 30,
    "max_duration_seconds": 60,
    "audio": True
}


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


def get_ffprobe_summary(path: Path) -> Optional[dict]:
    """Get ffprobe summary of video file."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", str(path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        fmt = data.get("format", {})
        streams = data.get("streams", [])

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        fps_str = video_stream.get("r_frame_rate", "30/1")
        fps = 30.0
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) > 0 else 30.0

        return {
            "duration": float(fmt.get("duration", 0)),
            "width": video_stream.get("width", 0),
            "height": video_stream.get("height", 0),
            "video_codec": video_stream.get("codec_name", "unknown"),
            "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
            "fps": round(fps, 2)
        }
    except Exception:
        return None


def assemble_master(
    render_result: Optional[dict],
    test_degraded: bool = False
) -> dict:
    """Assemble master from render result."""
    timestamp = datetime.now(timezone.utc).isoformat()
    short_id = uuid.uuid4().hex[:8]
    master_id = f"MASTER_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{short_id}"

    # Load source references
    reviewed_data, _ = load_json_file(REVIEWED_FILE)
    storyboards_data, _ = load_json_file(STORYBOARDS_FILE)
    qa_data, _ = load_json_file(QA_FILE)

    base_result = {
        "master_id": master_id,
        "timestamp": timestamp,
        "source_review": reviewed_data.get("review_id") if reviewed_data else None,
        "source_storyboard": storyboards_data.get("storyboard_id") if storyboards_data else None,
        "source_qa": qa_data.get("qa_id") if qa_data else None,
        "source_render": None,
        "script_id": None,
        "title": None,
        "render_spec": RENDER_SPEC,
        "file_proof": None,
        "meta": {
            "version": "1.0.0",
            "service": "master_assembler",
            "story_id": "SKYBEAM-STORY-019",
            "pipeline_version": "1.0.0",
            "host": socket.gethostname()
        }
    }

    # Degraded mode
    if test_degraded or render_result is None:
        base_result["status"] = "degraded"
        base_result["meta"]["degraded"] = True
        base_result["meta"]["reason"] = "No render result available" if not test_degraded else "Test degraded mode"
        return base_result

    # Check render status
    if render_result.get("status") in ["degraded", "failed"]:
        base_result["status"] = "degraded"
        base_result["source_render"] = render_result.get("result_id")
        base_result["meta"]["degraded"] = True
        base_result["meta"]["reason"] = f"Source render {render_result.get('status')}"
        return base_result

    # Get successful render
    renders = render_result.get("renders", [])
    successful = [r for r in renders if r.get("render_status") == "success"]

    if not successful:
        base_result["status"] = "degraded"
        base_result["source_render"] = render_result.get("result_id")
        base_result["meta"]["degraded"] = True
        base_result["meta"]["reason"] = "No successful renders found"
        return base_result

    # Take top successful render
    top_render = successful[0]
    source_path = Path(top_render.get("render_path", ""))

    if not source_path.exists():
        base_result["status"] = "failed"
        base_result["source_render"] = render_result.get("result_id")
        base_result["meta"]["degraded"] = True
        base_result["meta"]["reason"] = f"Render file not found: {source_path}"
        return base_result

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Copy to master location
    try:
        shutil.copy2(source_path, OUTPUT_MP4)
    except Exception as e:
        base_result["status"] = "failed"
        base_result["source_render"] = render_result.get("result_id")
        base_result["meta"]["degraded"] = True
        base_result["meta"]["reason"] = f"Copy failed: {e}"
        return base_result

    # Generate file proof
    file_bytes = OUTPUT_MP4.stat().st_size
    sha256 = calculate_sha256(OUTPUT_MP4)
    ffprobe_summary = get_ffprobe_summary(OUTPUT_MP4)

    base_result["status"] = "healthy"
    base_result["source_render"] = render_result.get("result_id")
    base_result["script_id"] = top_render.get("script_id")
    base_result["title"] = top_render.get("title")
    base_result["file_proof"] = {
        "path": str(OUTPUT_MP4),
        "bytes": file_bytes,
        "sha256": sha256,
        "ffprobe_summary": ffprobe_summary
    }
    base_result["meta"]["degraded"] = False

    return base_result


def validate_schema(data: dict) -> tuple[bool, Optional[str]]:
    """Validate master output against schema."""
    required = ["master_id", "timestamp", "status", "render_spec", "meta"]
    for field in required:
        if field not in data:
            return False, f"Missing required field: {field}"

    if data["status"] not in ["healthy", "partial", "degraded", "failed"]:
        return False, f"Invalid status: {data['status']}"

    return True, None


def write_master(master: dict) -> None:
    """Write master manifest to output file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(master, f, indent=2)


async def publish_to_nats(master: dict) -> bool:
    """Publish master to NATS."""
    try:
        import nats
        nc = await nats.connect(NATS_URL)
        payload = json.dumps(master).encode()
        await nc.publish(NATS_TOPIC, payload)
        await nc.flush()
        await nc.close()
        return True
    except Exception as e:
        print(f"NATS publish error: {e}", file=sys.stderr)
        return False


async def run_once(test_degraded: bool = False) -> dict:
    """Run a single master assembly cycle."""
    print("=" * 70)
    print("  SKYBEAM Master Assembler (STORY-019)")
    print("=" * 70)

    # Load render result
    print("\n[1] Loading render result...")
    render_result, error = load_json_file(RENDER_RESULT_FILE)
    if error:
        print(f"  Warning: {error}")
    else:
        print(f"  Loaded: {render_result.get('result_id')}")
        print(f"  Status: {render_result.get('status')}")

    # Assemble master
    print("[2] Assembling master...")
    master = assemble_master(render_result, test_degraded=test_degraded)
    print(f"  Master ID: {master['master_id']}")
    print(f"  Status: {master['status']}")
    if master.get("title"):
        print(f"  Title: {master['title'][:50]}...")
    if master.get("file_proof"):
        proof = master["file_proof"]
        summary = proof.get("ffprobe_summary", {})
        print(f"  File: {proof['bytes']} bytes")
        print(f"  Resolution: {summary.get('width')}x{summary.get('height')}")
        print(f"  Duration: {summary.get('duration'):.1f}s")
        print(f"  SHA256: {proof['sha256'][:16]}...")

    # Validate
    print("[3] Validating schema...")
    valid, error = validate_schema(master)
    if not valid:
        print(f"  FAIL: {error}")
        return master
    print(f"  Schema: VALID")

    # Write
    print("[4] Writing manifest...")
    write_master(master)
    print(f"  Manifest: {OUTPUT_JSON}")
    if master.get("file_proof"):
        print(f"  Master: {OUTPUT_MP4}")

    # Publish
    print("[5] Publishing to NATS...")
    nats_ok = await publish_to_nats(master)
    print(f"  NATS published: {nats_ok}")

    # Summary
    print("=" * 70)
    print("  PROOF ARTIFACTS:")
    print(f"  - Manifest: {OUTPUT_JSON}")
    if master.get("file_proof"):
        print(f"  - Master MP4: {OUTPUT_MP4}")
        print(f"  - Bytes: {master['file_proof']['bytes']}")
        print(f"  - SHA256: {master['file_proof']['sha256']}")
    print(f"  - Master ID: {master['master_id']}")
    print(f"  - Status: {master['status']}")
    print(f"  - NATS: {nats_ok}")
    print("=" * 70)

    return master


def main():
    parser = argparse.ArgumentParser(description="SKYBEAM Master Assembler")
    parser.add_argument("--test-degraded", action="store_true", help="Test degraded mode")
    args = parser.parse_args()

    asyncio.run(run_once(test_degraded=args.test_degraded))


if __name__ == "__main__":
    main()
