#!/usr/bin/env python3
"""
SKYBEAM Prompt Pack Generator (STORY-014)
==========================================

Turns asset briefs into generation-ready prompt packs.

Input:  ~/.roxy/content-pipeline/assets/briefs/asset_briefs_latest.json
Output: ~/.roxy/content-pipeline/assets/prompts/prompt_packs_latest.json
NATS:   ghost.asset.prompts

Usage:
    python3 prompt_pack_generator.py              # Normal run
    python3 prompt_pack_generator.py --test-degraded  # Test degraded mode
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
BRIEFS_FILE = Path.home() / ".roxy/content-pipeline/assets/briefs/asset_briefs_latest.json"
OUTPUT_DIR = Path.home() / ".roxy/content-pipeline/assets/prompts"
OUTPUT_FILE = OUTPUT_DIR / "prompt_packs_latest.json"

# NATS config
NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")
NATS_TOPIC = "ghost.asset.prompts"

# Asset specs by type
ASSET_SPECS = {
    "thumbnail": {"width": 1280, "height": 720, "aspect": "16:9"},
    "intro_card": {"width": 1920, "height": 1080, "aspect": "16:9"},
    "lower_third": {"width": 1920, "height": 200, "aspect": "wide"},
    "broll": {"width": 1920, "height": 1080, "aspect": "16:9", "fps": 30, "duration": 5.0},
    "title_card": {"width": 1920, "height": 1080, "aspect": "16:9"},
    "end_card": {"width": 1920, "height": 1080, "aspect": "16:9"}
}

# Style tokens by mood
STYLE_TOKENS = {
    "energetic": ["vibrant colors", "dynamic lighting", "motion blur", "high saturation", "glitch effects"],
    "professional": ["clean lines", "corporate aesthetic", "soft shadows", "neutral tones", "minimal design"],
    "authoritative": ["cinematic lighting", "deep shadows", "rich colors", "film grain", "dramatic composition"],
    "conversational": ["warm tones", "natural lighting", "friendly atmosphere", "soft focus", "inviting"]
}

# Base prompts by asset type
BASE_PROMPTS = {
    "thumbnail": "YouTube video thumbnail, {title}, {mood} style, professional quality, eye-catching, high contrast text area, {style}",
    "intro_card": "Video intro title card, {title}, {mood} motion graphics style, sleek animation ready, {style}",
    "lower_third": "Lower third graphic, {text}, {mood} style, semi-transparent background, modern typography, {style}",
    "broll": "B-roll footage, {intent}, {mood} cinematography, professional grade, 4K quality, {style}",
    "title_card": "Section title card, {text}, {mood} design, minimal clean layout, {style}",
    "end_card": "YouTube end screen, subscribe CTA, {mood} style, engaging call to action, {style}"
}

NEGATIVE_PROMPT = "blurry, low quality, distorted text, amateur, watermark, logo, cluttered, noisy, oversaturated, underexposed"


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


def generate_asset_id(script_id: str, asset_type: str, variant: int) -> str:
    """Generate asset ID."""
    script_slug = script_id.replace("SCR_", "")[:8]
    short_id = uuid.uuid4().hex[:8]
    return f"ASSET_{script_slug}_{asset_type}_{variant:02d}_{short_id}"


def generate_prompt(asset_type: str, brief: dict, scene: Optional[dict] = None, variant: int = 0) -> dict:
    """Generate a single prompt for an asset."""
    title = brief.get("title", "")
    visual_style = brief.get("visual_style", {})
    mood = visual_style.get("mood", "professional")
    style_list = STYLE_TOKENS.get(mood, STYLE_TOKENS["professional"])

    # Build prompt
    base = BASE_PROMPTS.get(asset_type, BASE_PROMPTS["broll"])
    style_str = ", ".join(style_list[:3])

    # Fill template
    prompt = base.format(
        title=title[:50],
        mood=mood,
        style=style_str,
        text=scene.get("on_screen_text", title) if scene else title,
        intent=scene.get("broll_intent", "tech visuals") if scene else "tech visuals"
    )

    # Get specs
    specs = ASSET_SPECS.get(asset_type, ASSET_SPECS["broll"]).copy()

    # Safe text overlays
    safe_texts = [title[:30]]
    if scene:
        safe_texts.append(scene.get("on_screen_text", "")[:30])

    return {
        "asset_id": generate_asset_id(brief.get("script_id", ""), asset_type, variant),
        "asset_type": asset_type,
        "prompt": prompt,
        "negative_prompt": NEGATIVE_PROMPT,
        "target_specs": specs,
        "style_tokens": style_list,
        "safe_text_overlays": [t for t in safe_texts if t]
    }


def generate_prompts_for_brief(brief: dict) -> list:
    """Generate all prompts for a single brief."""
    prompts = []
    script_id = brief.get("script_id", "")
    required_assets = brief.get("required_assets", [])
    scene_map = brief.get("scene_map", [])

    for asset_req in required_assets:
        asset_type = asset_req.get("asset_type")
        count = asset_req.get("count", 1)

        for i in range(count):
            # For broll and lower_thirds, use scene map if available
            scene = None
            if asset_type in ["broll", "lower_third", "title_card"] and i < len(scene_map):
                scene = scene_map[i]

            prompt = generate_prompt(asset_type, brief, scene, i)
            prompts.append(prompt)

    return prompts


def generate_packs(
    briefs_data: Optional[dict],
    test_degraded: bool = False
) -> dict:
    """Generate prompt packs from briefs."""
    timestamp = datetime.now(timezone.utc).isoformat()
    short_id = uuid.uuid4().hex[:8]
    pack_id = f"PACK_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{short_id}"

    # Degraded mode
    if test_degraded or briefs_data is None:
        return {
            "pack_id": pack_id,
            "timestamp": timestamp,
            "status": "degraded",
            "source_briefs": None,
            "packs": [],
            "meta": {
                "version": "1.0.0",
                "service": "prompt_pack_generator",
                "story_id": "SKYBEAM-STORY-014",
                "pack_count": 0,
                "prompt_count": 0,
                "degraded": True
            }
        }

    briefs = briefs_data.get("briefs", [])
    packs = []
    total_prompts = 0

    for brief in briefs:
        prompts = generate_prompts_for_brief(brief)
        packs.append({
            "script_id": brief.get("script_id"),
            "prompts": prompts
        })
        total_prompts += len(prompts)

    # Determine status
    if not packs:
        status = "degraded"
    elif total_prompts == 0:
        status = "partial"
    else:
        status = "healthy"

    return {
        "pack_id": pack_id,
        "timestamp": timestamp,
        "status": status,
        "source_briefs": briefs_data.get("brief_id"),
        "packs": packs,
        "meta": {
            "version": "1.0.0",
            "service": "prompt_pack_generator",
            "story_id": "SKYBEAM-STORY-014",
            "pack_count": len(packs),
            "prompt_count": total_prompts,
            "degraded": status == "degraded"
        }
    }


def validate_schema(data: dict) -> tuple[bool, Optional[str]]:
    """Validate packs against schema."""
    required = ["pack_id", "timestamp", "status", "source_briefs", "packs", "meta"]
    for field in required:
        if field not in data:
            return False, f"Missing required field: {field}"

    if data["status"] not in ["healthy", "partial", "degraded"]:
        return False, f"Invalid status: {data['status']}"

    return True, None


def write_packs(packs: dict) -> None:
    """Write packs to output file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(packs, f, indent=2)


async def publish_to_nats(packs: dict) -> bool:
    """Publish packs to NATS."""
    try:
        import nats
        nc = await nats.connect(NATS_URL)
        payload = json.dumps(packs).encode()
        await nc.publish(NATS_TOPIC, payload)
        await nc.flush()
        await nc.close()
        return True
    except Exception as e:
        print(f"NATS publish error: {e}", file=sys.stderr)
        return False


async def run_once(test_degraded: bool = False) -> dict:
    """Run a single pack generation cycle."""
    print("=" * 70)
    print("  SKYBEAM Prompt Pack Generator (STORY-014)")
    print("=" * 70)

    # Load briefs
    print("\n[1] Loading asset briefs...")
    briefs_data, error = load_json_file(BRIEFS_FILE)
    if error:
        print(f"  Warning: {error}")
    else:
        print(f"  Loaded: {briefs_data.get('brief_id')}")

    # Generate packs
    print("[2] Generating prompt packs...")
    packs = generate_packs(briefs_data, test_degraded=test_degraded)
    print(f"  Pack ID: {packs['pack_id']}")
    print(f"  Status: {packs['status']}")
    print(f"  Packs: {packs['meta']['pack_count']}")
    print(f"  Prompts: {packs['meta']['prompt_count']}")

    # Validate
    print("[3] Validating schema...")
    valid, error = validate_schema(packs)
    if not valid:
        print(f"  FAIL: {error}")
        return packs
    print(f"  Schema: VALID")

    # Write
    print("[4] Writing output...")
    write_packs(packs)
    print(f"  File written: {OUTPUT_FILE}")

    # Publish
    print("[5] Publishing to NATS...")
    nats_ok = await publish_to_nats(packs)
    print(f"  NATS published: {nats_ok}")

    # Summary
    print("=" * 70)
    print("  PROOF ARTIFACTS:")
    print(f"  - File: {OUTPUT_FILE}")
    print(f"  - Pack ID: {packs['pack_id']}")
    print(f"  - Status: {packs['status']}")
    print(f"  - Packs: {packs['meta']['pack_count']}")
    print(f"  - Prompts: {packs['meta']['prompt_count']}")
    print(f"  - NATS: {nats_ok}")
    print("=" * 70)

    return packs


def main():
    parser = argparse.ArgumentParser(description="SKYBEAM Prompt Pack Generator")
    parser.add_argument("--test-degraded", action="store_true", help="Test degraded mode")
    args = parser.parse_args()

    asyncio.run(run_once(test_degraded=args.test_degraded))


if __name__ == "__main__":
    main()
