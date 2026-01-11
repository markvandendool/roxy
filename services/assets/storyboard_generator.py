#!/usr/bin/env python3
"""
SKYBEAM Storyboard Generator (STORY-015)
=========================================

Converts prompt packs into storyboards with shotlists.

Input:  ~/.roxy/content-pipeline/assets/prompts/prompt_packs_latest.json
Output: ~/.roxy/content-pipeline/assets/storyboards/storyboards_latest.json
NATS:   ghost.asset.storyboards

Usage:
    python3 storyboard_generator.py              # Normal run
    python3 storyboard_generator.py --test-degraded  # Test degraded mode
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
PACKS_FILE = Path.home() / ".roxy/content-pipeline/assets/prompts/prompt_packs_latest.json"
OUTPUT_DIR = Path.home() / ".roxy/content-pipeline/assets/storyboards"
OUTPUT_FILE = OUTPUT_DIR / "storyboards_latest.json"

# NATS config
NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")
NATS_TOPIC = "ghost.asset.storyboards"

# Camera angles by asset type
CAMERA_ANGLES = {
    "thumbnail": "straight-on, eye-level",
    "intro_card": "wide establishing shot",
    "lower_third": "rule of thirds, lower frame",
    "broll": "dynamic movement, dolly",
    "title_card": "centered frame",
    "end_card": "centered with space for overlays"
}

# Composition by asset type
COMPOSITIONS = {
    "thumbnail": "hero subject center-left, text space right",
    "intro_card": "cinematic letterbox, title centered",
    "lower_third": "clean lower 20%, transparent overlay",
    "broll": "dynamic framing, motion-safe margins",
    "title_card": "centered text, decorative borders",
    "end_card": "subscribe button zones, card slots"
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


def generate_frame_id(script_id: str, frame_num: int) -> str:
    """Generate frame ID."""
    script_slug = script_id.replace("SCR_", "")[:8]
    return f"FRAME_{script_slug}_{frame_num:03d}"


def generate_shot_id(script_id: str, shot_num: int) -> str:
    """Generate shot ID."""
    script_slug = script_id.replace("SCR_", "")[:8]
    return f"SHOT_{script_slug}_{shot_num:03d}"


def format_timecode(seconds: float) -> str:
    """Format seconds as timecode HH:MM:SS:FF."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    frames = int((seconds % 1) * 30)  # 30fps
    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"


def generate_frames(script_id: str, prompts: list) -> list:
    """Generate storyboard frames from prompts."""
    frames = []
    current_time = 0.0

    for i, prompt in enumerate(prompts):
        asset_type = prompt.get("asset_type", "broll")
        specs = prompt.get("target_specs", {})

        # Estimate duration based on asset type
        if asset_type == "broll":
            duration = specs.get("duration", 5.0)
        elif asset_type in ["thumbnail", "intro_card", "end_card"]:
            duration = 3.0
        elif asset_type in ["lower_third", "title_card"]:
            duration = 2.0
        else:
            duration = 3.0

        frame = {
            "frame_id": generate_frame_id(script_id, i + 1),
            "scene_id": f"SCENE_{(i // 3) + 1:02d}",  # Approx scene mapping
            "asset_id": prompt.get("asset_id", ""),
            "timecode": format_timecode(current_time),
            "description": prompt.get("prompt", "")[:100],
            "camera": CAMERA_ANGLES.get(asset_type, "standard"),
            "composition": COMPOSITIONS.get(asset_type, "centered"),
            "notes": f"Style: {', '.join(prompt.get('style_tokens', [])[:2])}"
        }
        frames.append(frame)
        current_time += duration

    return frames


def generate_shotlist(script_id: str, prompts: list) -> list:
    """Generate shotlist from prompts."""
    shots = []

    # Priority by asset type
    priorities = {
        "thumbnail": "critical",
        "intro_card": "high",
        "end_card": "high",
        "broll": "medium",
        "lower_third": "medium",
        "title_card": "medium"
    }

    for i, prompt in enumerate(prompts):
        asset_type = prompt.get("asset_type", "broll")
        specs = prompt.get("target_specs", {})

        # Duration
        if asset_type == "broll":
            duration = specs.get("duration", 5.0)
        elif asset_type in ["thumbnail", "intro_card", "end_card"]:
            duration = 3.0
        else:
            duration = 2.0

        shot = {
            "shot_id": generate_shot_id(script_id, i + 1),
            "asset_type": asset_type,
            "duration": duration,
            "description": prompt.get("prompt", "")[:80],
            "priority": priorities.get(asset_type, "low")
        }
        shots.append(shot)

    return shots


def generate_storyboard(pack: dict) -> dict:
    """Generate storyboard for a single pack."""
    script_id = pack.get("script_id", "")
    prompts = pack.get("prompts", [])

    return {
        "script_id": script_id,
        "frames": generate_frames(script_id, prompts),
        "shotlist": generate_shotlist(script_id, prompts)
    }


def generate_storyboards(
    packs_data: Optional[dict],
    test_degraded: bool = False
) -> dict:
    """Generate storyboards from prompt packs."""
    timestamp = datetime.now(timezone.utc).isoformat()
    short_id = uuid.uuid4().hex[:8]
    storyboard_id = f"STORYBOARD_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{short_id}"

    # Degraded mode
    if test_degraded or packs_data is None:
        return {
            "storyboard_id": storyboard_id,
            "timestamp": timestamp,
            "status": "degraded",
            "source_pack": None,
            "storyboards": [],
            "meta": {
                "version": "1.0.0",
                "service": "storyboard_generator",
                "story_id": "SKYBEAM-STORY-015",
                "storyboard_count": 0,
                "total_frames": 0,
                "total_shots": 0,
                "degraded": True
            }
        }

    packs = packs_data.get("packs", [])
    storyboards = []
    total_frames = 0
    total_shots = 0

    for pack in packs:
        storyboard = generate_storyboard(pack)
        storyboards.append(storyboard)
        total_frames += len(storyboard["frames"])
        total_shots += len(storyboard["shotlist"])

    # Determine status
    if not storyboards:
        status = "degraded"
    elif total_frames == 0:
        status = "partial"
    else:
        status = "healthy"

    return {
        "storyboard_id": storyboard_id,
        "timestamp": timestamp,
        "status": status,
        "source_pack": packs_data.get("pack_id"),
        "storyboards": storyboards,
        "meta": {
            "version": "1.0.0",
            "service": "storyboard_generator",
            "story_id": "SKYBEAM-STORY-015",
            "storyboard_count": len(storyboards),
            "total_frames": total_frames,
            "total_shots": total_shots,
            "degraded": status == "degraded"
        }
    }


def validate_schema(data: dict) -> tuple[bool, Optional[str]]:
    """Validate storyboards against schema."""
    required = ["storyboard_id", "timestamp", "status", "source_pack", "storyboards", "meta"]
    for field in required:
        if field not in data:
            return False, f"Missing required field: {field}"

    if data["status"] not in ["healthy", "partial", "degraded"]:
        return False, f"Invalid status: {data['status']}"

    return True, None


def write_storyboards(storyboards: dict) -> None:
    """Write storyboards to output file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(storyboards, f, indent=2)


async def publish_to_nats(storyboards: dict) -> bool:
    """Publish storyboards to NATS."""
    try:
        import nats
        nc = await nats.connect(NATS_URL)
        payload = json.dumps(storyboards).encode()
        await nc.publish(NATS_TOPIC, payload)
        await nc.flush()
        await nc.close()
        return True
    except Exception as e:
        print(f"NATS publish error: {e}", file=sys.stderr)
        return False


async def run_once(test_degraded: bool = False) -> dict:
    """Run a single storyboard generation cycle."""
    print("=" * 70)
    print("  SKYBEAM Storyboard Generator (STORY-015)")
    print("=" * 70)

    # Load packs
    print("\n[1] Loading prompt packs...")
    packs_data, error = load_json_file(PACKS_FILE)
    if error:
        print(f"  Warning: {error}")
    else:
        print(f"  Loaded: {packs_data.get('pack_id')}")

    # Generate storyboards
    print("[2] Generating storyboards...")
    storyboards = generate_storyboards(packs_data, test_degraded=test_degraded)
    print(f"  Storyboard ID: {storyboards['storyboard_id']}")
    print(f"  Status: {storyboards['status']}")
    print(f"  Storyboards: {storyboards['meta']['storyboard_count']}")
    print(f"  Frames: {storyboards['meta']['total_frames']}")
    print(f"  Shots: {storyboards['meta']['total_shots']}")

    # Validate
    print("[3] Validating schema...")
    valid, error = validate_schema(storyboards)
    if not valid:
        print(f"  FAIL: {error}")
        return storyboards
    print(f"  Schema: VALID")

    # Write
    print("[4] Writing output...")
    write_storyboards(storyboards)
    print(f"  File written: {OUTPUT_FILE}")

    # Publish
    print("[5] Publishing to NATS...")
    nats_ok = await publish_to_nats(storyboards)
    print(f"  NATS published: {nats_ok}")

    # Summary
    print("=" * 70)
    print("  PROOF ARTIFACTS:")
    print(f"  - File: {OUTPUT_FILE}")
    print(f"  - Storyboard ID: {storyboards['storyboard_id']}")
    print(f"  - Status: {storyboards['status']}")
    print(f"  - Storyboards: {storyboards['meta']['storyboard_count']}")
    print(f"  - Frames: {storyboards['meta']['total_frames']}")
    print(f"  - Shots: {storyboards['meta']['total_shots']}")
    print(f"  - NATS: {nats_ok}")
    print("=" * 70)

    return storyboards


def main():
    parser = argparse.ArgumentParser(description="SKYBEAM Storyboard Generator")
    parser.add_argument("--test-degraded", action="store_true", help="Test degraded mode")
    args = parser.parse_args()

    asyncio.run(run_once(test_degraded=args.test_degraded))


if __name__ == "__main__":
    main()
