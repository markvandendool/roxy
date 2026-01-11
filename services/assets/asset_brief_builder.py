#!/usr/bin/env python3
"""
SKYBEAM Asset Brief Builder (STORY-013)
========================================

Converts reviewed scripts into per-script asset requirements.

Input:  ~/.roxy/content-pipeline/scripts/scripts_reviewed.json
Output: ~/.roxy/content-pipeline/assets/briefs/asset_briefs_latest.json
NATS:   ghost.asset.briefs

Usage:
    python3 asset_brief_builder.py              # Normal run
    python3 asset_brief_builder.py --test-degraded  # Test degraded mode
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
SCRIPT_DIR = Path(__file__).parent
REVIEW_FILE = Path.home() / ".roxy/content-pipeline/scripts/scripts_reviewed.json"
OUTPUT_DIR = Path.home() / ".roxy/content-pipeline/assets/briefs"
OUTPUT_FILE = OUTPUT_DIR / "asset_briefs_latest.json"

# NATS config
NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")
NATS_TOPIC = "ghost.asset.briefs"

# Default visual styles by format
VISUAL_STYLES = {
    "short": {
        "primary_color": "#00D4FF",
        "secondary_color": "#1A1A2E",
        "font_family": "Inter Bold",
        "mood": "energetic",
        "lighting": "high-contrast"
    },
    "standard": {
        "primary_color": "#6366F1",
        "secondary_color": "#0F0F23",
        "font_family": "Inter Medium",
        "mood": "professional",
        "lighting": "balanced"
    },
    "long": {
        "primary_color": "#8B5CF6",
        "secondary_color": "#1E1E3F",
        "font_family": "Inter Regular",
        "mood": "authoritative",
        "lighting": "cinematic"
    }
}

# Required assets by format
REQUIRED_ASSETS = {
    "short": [
        {"asset_type": "thumbnail", "purpose": "Video thumbnail for platforms", "count": 1},
        {"asset_type": "intro_card", "purpose": "Opening title card", "count": 1},
        {"asset_type": "lower_third", "purpose": "Name/topic lower third", "count": 1},
        {"asset_type": "end_card", "purpose": "Subscribe CTA end card", "count": 1}
    ],
    "standard": [
        {"asset_type": "thumbnail", "purpose": "Video thumbnail for platforms", "count": 1},
        {"asset_type": "intro_card", "purpose": "Opening title card", "count": 1},
        {"asset_type": "lower_third", "purpose": "Name/topic lower thirds", "count": 3},
        {"asset_type": "broll", "purpose": "B-roll footage pack", "count": 5},
        {"asset_type": "title_card", "purpose": "Section title cards", "count": 3},
        {"asset_type": "end_card", "purpose": "Subscribe CTA end card", "count": 1}
    ],
    "long": [
        {"asset_type": "thumbnail", "purpose": "Video thumbnail for platforms", "count": 1},
        {"asset_type": "intro_card", "purpose": "Opening title card", "count": 1},
        {"asset_type": "lower_third", "purpose": "Name/topic lower thirds", "count": 5},
        {"asset_type": "broll", "purpose": "B-roll footage pack", "count": 10},
        {"asset_type": "title_card", "purpose": "Section title cards", "count": 5},
        {"asset_type": "end_card", "purpose": "Subscribe CTA end card", "count": 1}
    ]
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


def generate_scene_map(script: dict) -> list:
    """Generate scene map from script sections."""
    scenes = []
    sections = script.get("sections", [])
    current_time = 0.0

    for i, section in enumerate(sections):
        duration = section.get("duration_seconds", 10)
        scene_id = f"SCENE_{i+1:02d}"

        scene = {
            "scene_id": scene_id,
            "t_start": current_time,
            "t_end": current_time + duration,
            "section": section.get("section", ""),
            "on_screen_text": extract_on_screen_text(section),
            "broll_intent": generate_broll_intent(section),
            "vo_summary": section.get("content", "")[:100]
        }
        scenes.append(scene)
        current_time += duration

    return scenes


def extract_on_screen_text(section: dict) -> str:
    """Extract text suitable for on-screen display."""
    content = section.get("content", "")
    section_name = section.get("section", "")

    # Extract bracketed content type
    if content.startswith("[") and "]" in content:
        bracket_end = content.index("]")
        text_type = content[1:bracket_end]
        return f"{text_type}: {section_name.replace('_', ' ').title()}"

    return section_name.replace("_", " ").title()


def generate_broll_intent(section: dict) -> str:
    """Generate B-roll intent based on section type."""
    section_name = section.get("section", "").lower()

    intents = {
        "hook": "Attention-grabbing tech visuals, glitch effects",
        "intro": "Professional tech environment, screens with code",
        "context": "Historical footage, timeline graphics",
        "details": "Product shots, UI demos, data visualizations",
        "analysis": "Charts, graphs, expert-style talking head frame",
        "demo": "Screen recording, hands-on footage",
        "step": "Tutorial-style screen capture, step indicators",
        "pros_cons": "Split screen comparison, checkmarks/X marks",
        "verdict": "Rating graphics, recommendation badge",
        "cta": "Subscribe button animation, social handles",
        "takeaway": "Key point graphics, summary card"
    }

    for key, intent in intents.items():
        if key in section_name:
            return intent

    return "General tech visuals, abstract backgrounds"


def generate_compliance(script: dict) -> dict:
    """Generate compliance flags for a script."""
    title = script.get("trend_title", "").lower()

    # Check for potential trademark risks
    trademark_risks = []
    risky_terms = ["nvidia", "amd", "apple", "google", "microsoft", "openai", "anthropic", "meta"]
    for term in risky_terms:
        if term in title:
            trademark_risks.append(f"{term.title()} trademark")

    return {
        "disallowed_words": ["guaranteed", "100%", "proven"],
        "music_policy": "royalty_free_only",
        "trademark_risks": trademark_risks
    }


def build_brief(reviewed_script: dict, script_data: dict) -> dict:
    """Build asset brief for a single script."""
    script_id = reviewed_script.get("script_id", "")
    format_type = reviewed_script.get("template_id", "standard").split("-")[-1]
    if format_type not in ["short", "standard", "long"]:
        format_type = "standard"

    # Get duration from script data
    duration = 120  # default
    if script_data:
        duration = script_data.get("estimated_duration", 120)

    return {
        "script_id": script_id,
        "title": reviewed_script.get("trend_title", "Untitled"),
        "format": format_type,
        "duration_target": duration,
        "visual_style": VISUAL_STYLES.get(format_type, VISUAL_STYLES["standard"]),
        "required_assets": REQUIRED_ASSETS.get(format_type, REQUIRED_ASSETS["standard"]),
        "scene_map": generate_scene_map(script_data) if script_data else [],
        "compliance": generate_compliance(reviewed_script)
    }


def generate_briefs(
    review_data: Optional[dict],
    test_degraded: bool = False
) -> dict:
    """Generate asset briefs from reviewed scripts."""
    timestamp = datetime.now(timezone.utc).isoformat()
    short_id = uuid.uuid4().hex[:8]
    brief_id = f"BRIEF_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{short_id}"

    # Degraded mode
    if test_degraded or review_data is None:
        return {
            "brief_id": brief_id,
            "timestamp": timestamp,
            "status": "degraded",
            "source_review": None,
            "briefs": [],
            "meta": {
                "version": "1.0.0",
                "service": "asset_brief_builder",
                "story_id": "SKYBEAM-STORY-013",
                "brief_count": 0,
                "degraded": True
            }
        }

    # Load scripts data for full script info
    scripts_file = Path.home() / ".roxy/content-pipeline/scripts/scripts_latest.json"
    scripts_data, _ = load_json_file(scripts_file)
    scripts_map = {}
    if scripts_data:
        for script in scripts_data.get("scripts", []):
            scripts_map[script.get("id")] = script

    # Only process approved scripts
    reviewed_scripts = review_data.get("reviewed_scripts", [])
    approved = [s for s in reviewed_scripts if s.get("review_status") == "approved"]

    briefs = []
    for reviewed in approved:
        script_id = reviewed.get("script_id")
        script_data = scripts_map.get(script_id, {})
        brief = build_brief(reviewed, script_data)
        briefs.append(brief)

    # Determine status
    if not briefs:
        status = "degraded"
    elif len(briefs) < len(approved):
        status = "partial"
    else:
        status = "healthy"

    return {
        "brief_id": brief_id,
        "timestamp": timestamp,
        "status": status,
        "source_review": review_data.get("review_id"),
        "briefs": briefs,
        "meta": {
            "version": "1.0.0",
            "service": "asset_brief_builder",
            "story_id": "SKYBEAM-STORY-013",
            "brief_count": len(briefs),
            "degraded": status == "degraded"
        }
    }


def validate_schema(data: dict) -> tuple[bool, Optional[str]]:
    """Validate briefs against schema."""
    required = ["brief_id", "timestamp", "status", "source_review", "briefs", "meta"]
    for field in required:
        if field not in data:
            return False, f"Missing required field: {field}"

    if data["status"] not in ["healthy", "partial", "degraded"]:
        return False, f"Invalid status: {data['status']}"

    return True, None


def write_briefs(briefs: dict) -> None:
    """Write briefs to output file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(briefs, f, indent=2)


async def publish_to_nats(briefs: dict) -> bool:
    """Publish briefs to NATS."""
    try:
        import nats
        nc = await nats.connect(NATS_URL)
        payload = json.dumps(briefs).encode()
        await nc.publish(NATS_TOPIC, payload)
        await nc.flush()
        await nc.close()
        return True
    except Exception as e:
        print(f"NATS publish error: {e}", file=sys.stderr)
        return False


async def run_once(test_degraded: bool = False) -> dict:
    """Run a single brief generation cycle."""
    print("=" * 70)
    print("  SKYBEAM Asset Brief Builder (STORY-013)")
    print("=" * 70)

    # Load review
    print("\n[1] Loading reviewed scripts...")
    review_data, error = load_json_file(REVIEW_FILE)
    if error:
        print(f"  Warning: {error}")
    else:
        print(f"  Loaded: {review_data.get('review_id')}")

    # Generate briefs
    print("[2] Generating asset briefs...")
    briefs = generate_briefs(review_data, test_degraded=test_degraded)
    print(f"  Brief ID: {briefs['brief_id']}")
    print(f"  Status: {briefs['status']}")
    print(f"  Briefs: {briefs['meta']['brief_count']}")

    # Validate
    print("[3] Validating schema...")
    valid, error = validate_schema(briefs)
    if not valid:
        print(f"  FAIL: {error}")
        return briefs
    print(f"  Schema: VALID")

    # Write
    print("[4] Writing output...")
    write_briefs(briefs)
    print(f"  File written: {OUTPUT_FILE}")

    # Publish
    print("[5] Publishing to NATS...")
    nats_ok = await publish_to_nats(briefs)
    print(f"  NATS published: {nats_ok}")

    # Summary
    print("=" * 70)
    print("  PROOF ARTIFACTS:")
    print(f"  - File: {OUTPUT_FILE}")
    print(f"  - Brief ID: {briefs['brief_id']}")
    print(f"  - Status: {briefs['status']}")
    print(f"  - Briefs: {briefs['meta']['brief_count']}")
    print(f"  - NATS: {nats_ok}")
    print("=" * 70)

    return briefs


def main():
    parser = argparse.ArgumentParser(description="SKYBEAM Asset Brief Builder")
    parser.add_argument("--test-degraded", action="store_true", help="Test degraded mode")
    args = parser.parse_args()

    asyncio.run(run_once(test_degraded=args.test_degraded))


if __name__ == "__main__":
    main()
