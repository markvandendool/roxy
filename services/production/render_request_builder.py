#!/usr/bin/env python3
"""
SKYBEAM Render Request Builder (STORY-017)
===========================================

Selects approved scripts and creates render requests.

Input:
  ~/.roxy/content-pipeline/scripts/scripts_reviewed.json
  ~/.roxy/content-pipeline/assets/storyboards/storyboards_latest.json
  ~/.roxy/content-pipeline/assets/qa/asset_qa_latest.json

Output:
  ~/.roxy/content-pipeline/production/requests/render_requests_latest.json

NATS:
  ghost.prod.render_request

Selection rule:
  Top 1 approved script by (score DESC, script_id ASC)
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import uuid

# Paths
REVIEWED_FILE = Path.home() / ".roxy/content-pipeline/scripts/scripts_reviewed.json"
STORYBOARDS_FILE = Path.home() / ".roxy/content-pipeline/assets/storyboards/storyboards_latest.json"
QA_FILE = Path.home() / ".roxy/content-pipeline/assets/qa/asset_qa_latest.json"
OUTPUT_DIR = Path.home() / ".roxy/content-pipeline/production/requests"
OUTPUT_FILE = OUTPUT_DIR / "render_requests_latest.json"

# NATS config
NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")
NATS_TOPIC = "ghost.prod.render_request"

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


def select_top_approved(reviewed_data: dict) -> list:
    """Select top 1 approved script by score DESC, script_id ASC."""
    if not reviewed_data:
        return []

    reviewed_scripts = reviewed_data.get("reviewed_scripts", [])
    approved = [s for s in reviewed_scripts if s.get("review_status") == "approved"]

    if not approved:
        return []

    # Sort by score DESC, then script_id ASC for tie-break
    approved.sort(key=lambda x: (-x.get("review_score", 0) or 0, x.get("script_id", "")))

    # Return top 1
    return approved[:1]


def build_render_request(script: dict, storyboards_data: Optional[dict]) -> dict:
    """Build a render request for a script."""
    script_id = script.get("script_id", "")

    # Find matching storyboard
    storyboard_id = None
    if storyboards_data:
        for sb in storyboards_data.get("storyboards", []):
            if sb.get("script_id") == script_id:
                storyboard_id = storyboards_data.get("storyboard_id")
                break

    return {
        "script_id": script_id,
        "title": script.get("trend_title", "Untitled"),
        "score": script.get("review_score", 0) or 0,
        "storyboard_id": storyboard_id,
        "render_spec": RENDER_SPEC.copy()
    }


def generate_render_requests(
    reviewed_data: Optional[dict],
    storyboards_data: Optional[dict],
    qa_data: Optional[dict],
    test_degraded: bool = False
) -> dict:
    """Generate render requests from reviewed scripts."""
    timestamp = datetime.now(timezone.utc).isoformat()
    short_id = uuid.uuid4().hex[:8]
    request_id = f"RENDER_REQ_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{short_id}"

    # Check QA gate
    qa_gate_approved = False
    if qa_data:
        summary = qa_data.get("summary", {})
        qa_gate_approved = summary.get("gate_result") == "approved"

    # Degraded mode
    if test_degraded or reviewed_data is None:
        return {
            "request_id": request_id,
            "timestamp": timestamp,
            "status": "degraded",
            "source_review": None,
            "source_storyboard": None,
            "source_qa": None,
            "requests": [],
            "meta": {
                "version": "1.0.0",
                "service": "render_request_builder",
                "story_id": "SKYBEAM-STORY-017",
                "request_count": 0,
                "degraded": True,
                "reason": "No reviewed scripts available" if not test_degraded else "Test degraded mode"
            }
        }

    # Check QA gate
    if not qa_gate_approved:
        return {
            "request_id": request_id,
            "timestamp": timestamp,
            "status": "degraded",
            "source_review": reviewed_data.get("review_id"),
            "source_storyboard": storyboards_data.get("storyboard_id") if storyboards_data else None,
            "source_qa": qa_data.get("qa_id") if qa_data else None,
            "requests": [],
            "meta": {
                "version": "1.0.0",
                "service": "render_request_builder",
                "story_id": "SKYBEAM-STORY-017",
                "request_count": 0,
                "degraded": True,
                "reason": "Asset QA gate not approved"
            }
        }

    # Select top approved script
    top_approved = select_top_approved(reviewed_data)
    requests = []

    for script in top_approved:
        req = build_render_request(script, storyboards_data)
        requests.append(req)

    # Determine status
    if not requests:
        status = "degraded"
        reason = "No approved scripts found"
    else:
        status = "healthy"
        reason = None

    result = {
        "request_id": request_id,
        "timestamp": timestamp,
        "status": status,
        "source_review": reviewed_data.get("review_id"),
        "source_storyboard": storyboards_data.get("storyboard_id") if storyboards_data else None,
        "source_qa": qa_data.get("qa_id") if qa_data else None,
        "requests": requests,
        "meta": {
            "version": "1.0.0",
            "service": "render_request_builder",
            "story_id": "SKYBEAM-STORY-017",
            "request_count": len(requests),
            "degraded": status == "degraded"
        }
    }

    if reason:
        result["meta"]["reason"] = reason

    return result


def validate_schema(data: dict) -> tuple[bool, Optional[str]]:
    """Validate render requests against schema."""
    required = ["request_id", "timestamp", "status", "source_review", "source_storyboard", "source_qa", "requests", "meta"]
    for field in required:
        if field not in data:
            return False, f"Missing required field: {field}"

    if data["status"] not in ["healthy", "partial", "degraded"]:
        return False, f"Invalid status: {data['status']}"

    return True, None


def write_requests(requests: dict) -> None:
    """Write requests to output file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(requests, f, indent=2)


async def publish_to_nats(requests: dict) -> bool:
    """Publish requests to NATS."""
    try:
        import nats
        nc = await nats.connect(NATS_URL)
        payload = json.dumps(requests).encode()
        await nc.publish(NATS_TOPIC, payload)
        await nc.flush()
        await nc.close()
        return True
    except Exception as e:
        print(f"NATS publish error: {e}", file=sys.stderr)
        return False


async def run_once(test_degraded: bool = False) -> dict:
    """Run a single render request generation cycle."""
    print("=" * 70)
    print("  SKYBEAM Render Request Builder (STORY-017)")
    print("=" * 70)

    # Load inputs
    print("\n[1] Loading reviewed scripts...")
    reviewed_data, error = load_json_file(REVIEWED_FILE)
    if error:
        print(f"  Warning: {error}")
    else:
        print(f"  Loaded: {reviewed_data.get('review_id')}")

    print("[2] Loading storyboards...")
    storyboards_data, error = load_json_file(STORYBOARDS_FILE)
    if error:
        print(f"  Warning: {error}")
    else:
        print(f"  Loaded: {storyboards_data.get('storyboard_id')}")

    print("[3] Loading asset QA...")
    qa_data, error = load_json_file(QA_FILE)
    if error:
        print(f"  Warning: {error}")
    else:
        gate = qa_data.get("summary", {}).get("gate_result", "unknown")
        print(f"  Loaded: {qa_data.get('qa_id')} (gate: {gate})")

    # Generate requests
    print("[4] Generating render requests...")
    requests = generate_render_requests(reviewed_data, storyboards_data, qa_data, test_degraded=test_degraded)
    print(f"  Request ID: {requests['request_id']}")
    print(f"  Status: {requests['status']}")
    print(f"  Requests: {requests['meta']['request_count']}")
    if requests['meta'].get('reason'):
        print(f"  Reason: {requests['meta']['reason']}")

    # Show selected script
    if requests['requests']:
        top = requests['requests'][0]
        print(f"  Selected: {top['title'][:50]}... (score: {top['score']})")

    # Validate
    print("[5] Validating schema...")
    valid, error = validate_schema(requests)
    if not valid:
        print(f"  FAIL: {error}")
        return requests
    print(f"  Schema: VALID")

    # Write
    print("[6] Writing output...")
    write_requests(requests)
    print(f"  File written: {OUTPUT_FILE}")

    # Publish
    print("[7] Publishing to NATS...")
    nats_ok = await publish_to_nats(requests)
    print(f"  NATS published: {nats_ok}")

    # Summary
    print("=" * 70)
    print("  PROOF ARTIFACTS:")
    print(f"  - File: {OUTPUT_FILE}")
    print(f"  - Request ID: {requests['request_id']}")
    print(f"  - Status: {requests['status']}")
    print(f"  - Requests: {requests['meta']['request_count']}")
    print(f"  - NATS: {nats_ok}")
    print("=" * 70)

    return requests


def main():
    parser = argparse.ArgumentParser(description="SKYBEAM Render Request Builder")
    parser.add_argument("--test-degraded", action="store_true", help="Test degraded mode")
    args = parser.parse_args()

    asyncio.run(run_once(test_degraded=args.test_degraded))


if __name__ == "__main__":
    main()
