#!/usr/bin/env python3
"""
SKYBEAM Script Generator Service (STORY-010)
=============================================

Generates script outlines by matching trends to templates.

Input:
  ~/.roxy/content-pipeline/bundles/research_bundle_latest.json
  ~/.roxy/content-pipeline/scripts/templates_latest.json

Output:
  ~/.roxy/content-pipeline/scripts/scripts_latest.json

NATS:
  ghost.script.generated

Usage:
    python3 script_generator.py              # Normal run
    python3 script_generator.py --test-degraded  # Test degraded mode
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
import random

# Paths
SCRIPT_DIR = Path(__file__).parent
BUNDLE_FILE = Path.home() / ".roxy/content-pipeline/bundles/research_bundle_latest.json"
TEMPLATES_FILE = Path.home() / ".roxy/content-pipeline/scripts/templates_latest.json"
OUTPUT_DIR = Path.home() / ".roxy/content-pipeline/scripts"
OUTPUT_FILE = OUTPUT_DIR / "scripts_latest.json"

# NATS config
NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")
NATS_TOPIC = "ghost.script.generated"


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


def select_template(trend: dict, templates: list) -> Optional[dict]:
    """Select best template for a trend based on category and content."""
    trend_source = trend.get("source", "").lower()
    trend_title = trend.get("title", "").lower()

    # Scoring based on content type hints
    scores = {}
    for template in templates:
        score = 0
        template_id = template.get("id", "")
        category = template.get("category", "")

        # News templates for breaking/current events
        if any(kw in trend_title for kw in ["breaking", "announces", "launches", "releases", "just"]):
            if category in ["news", "quick_hit"]:
                score += 10

        # Tutorial templates for "how to" content
        if any(kw in trend_title for kw in ["how to", "guide", "tutorial", "learn"]):
            if category == "tutorial":
                score += 10

        # Comparison templates for "vs" content
        if " vs " in trend_title or "versus" in trend_title:
            if category == "comparison":
                score += 10

        # Review templates for product mentions
        if any(kw in trend_title for kw in ["review", "tested", "hands-on"]):
            if category == "review":
                score += 10

        # Deep dive for research/technical content
        if any(kw in trend_source for kw in ["mit", "research", "paper"]):
            if category in ["deep_dive", "explainer"]:
                score += 8

        # Default: news-standard is safe fallback
        if template_id == "news-standard":
            score += 3

        scores[template_id] = (score, template)

    # Return highest scoring template
    if scores:
        best_id = max(scores, key=lambda k: scores[k][0])
        return scores[best_id][1]

    # Fallback to first template
    return templates[0] if templates else None


def generate_hook(template: dict, trend: dict) -> str:
    """Generate hook line from template patterns."""
    hooks = template.get("hooks", [])
    if not hooks:
        return trend.get("title", "")

    # Pick a random hook pattern
    pattern = random.choice(hooks)

    # Simple variable substitution
    result = pattern
    result = result.replace("{headline}", trend.get("title", "Breaking news"))
    result = result.replace("{source}", trend.get("source", "sources"))
    result = result.replace("{topic}", trend.get("title", "this topic").split(":")[0])
    result = result.replace("{tool_name}", trend.get("title", "the tool").split()[-1])
    result = result.replace("{option_a}", "Option A")
    result = result.replace("{option_b}", "Option B")

    return result


def generate_section_content(section: dict, trend: dict, template: dict) -> str:
    """Generate placeholder content for a script section."""
    section_name = section.get("section", "")
    purpose = section.get("purpose", "")

    # Generate contextual content based on section type
    if section_name == "hook":
        return f"[HOOK] {generate_hook(template, trend)}"

    elif section_name in ["what", "details", "overview"]:
        summary = trend.get("summary", "")[:200]
        return f"[DETAILS] {summary}..."

    elif section_name in ["why_matters", "analysis", "implications"]:
        return f"[ANALYSIS] Here's why this matters: {purpose}"

    elif section_name in ["context", "background", "intro"]:
        return f"[CONTEXT] Background on this development..."

    elif section_name in ["cta"]:
        return "[CTA] Subscribe for more AI insights. Drop a comment with your thoughts."

    elif section_name in ["takeaway", "summary", "verdict"]:
        return f"[TAKEAWAY] The key point to remember..."

    elif "step" in section_name:
        return f"[{section_name.upper()}] Walk through this step..."

    elif section_name in ["demo", "example"]:
        return f"[DEMO] Let me show you how this works..."

    elif section_name == "pros_cons":
        return "[PROS/CONS] Let's break down the advantages and disadvantages..."

    elif section_name == "tips":
        return "[TIPS] Pro tips to get the most out of this..."

    else:
        return f"[{section_name.upper()}] {purpose}"


def generate_script(trend: dict, template: dict, competitor_data: Optional[dict] = None) -> dict:
    """Generate a single script from trend and template."""
    script_id = f"SCR_{uuid.uuid4().hex[:12]}"

    # Get duration range
    duration_range = template.get("duration_range", {"min_seconds": 60, "max_seconds": 120})
    target_duration = (duration_range["min_seconds"] + duration_range["max_seconds"]) // 2

    # Generate sections
    sections = []
    structure = template.get("structure", [])
    for section_def in structure:
        duration_pct = section_def.get("duration_pct", 10)
        section_duration = int(target_duration * duration_pct / 100)

        sections.append({
            "section": section_def.get("section"),
            "content": generate_section_content(section_def, trend, template),
            "duration_seconds": section_duration,
            "notes": section_def.get("purpose", "")
        })

    # Fill variables
    variables = {
        "headline": trend.get("title", ""),
        "source": trend.get("source", ""),
        "summary": trend.get("summary", ""),
        "category": trend.get("category", "")
    }

    # Get differentiation from competitor analysis if available
    differentiation = []
    if competitor_data:
        for analysis in competitor_data.get("analyses", []):
            if analysis.get("trend_title") == trend.get("title"):
                differentiation = analysis.get("differentiation", [])
                break

    return {
        "id": script_id,
        "trend_title": trend.get("title", ""),
        "template_id": template.get("id"),
        "template_name": template.get("name"),
        "format": template.get("format"),
        "estimated_duration": target_duration,
        "hook": generate_hook(template, trend),
        "sections": sections,
        "variables": variables,
        "differentiation": differentiation
    }


def generate_scripts(
    bundle: Optional[dict],
    templates_data: Optional[dict],
    top_n: int = 3,
    test_degraded: bool = False
) -> dict:
    """Generate scripts from bundle and templates."""
    timestamp = datetime.now(timezone.utc).isoformat()
    short_id = uuid.uuid4().hex[:8]
    script_id = f"SCRIPT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{short_id}"

    # Degraded mode
    if test_degraded or bundle is None or templates_data is None:
        return {
            "script_id": script_id,
            "timestamp": timestamp,
            "status": "degraded",
            "source_bundle": None,
            "source_templates": None,
            "scripts": [],
            "meta": {
                "version": "1.0.0",
                "service": "script_generator",
                "story_id": "SKYBEAM-STORY-010",
                "script_count": 0,
                "degraded": True
            }
        }

    templates = templates_data.get("templates", [])
    if not templates:
        return {
            "script_id": script_id,
            "timestamp": timestamp,
            "status": "degraded",
            "source_bundle": bundle.get("bundle_id"),
            "source_templates": templates_data.get("library_id"),
            "scripts": [],
            "meta": {
                "version": "1.0.0",
                "service": "script_generator",
                "story_id": "SKYBEAM-STORY-010",
                "script_count": 0,
                "degraded": True
            }
        }

    # Get top trend from bundle
    top_trend = bundle.get("summary", {}).get("top_trend")
    trend_count = bundle.get("summary", {}).get("trend_count", 0)

    # Load full trends from trends file for more data
    trends_file = Path.home() / ".roxy/content-pipeline/trends/trends_latest.json"
    trends_data, _ = load_json_file(trends_file)
    trends = trends_data.get("trends", [])[:top_n] if trends_data else []

    # Load competitor data for differentiation
    competitors_file = Path.home() / ".roxy/content-pipeline/competitors/competitors_latest.json"
    competitor_data, _ = load_json_file(competitors_file)

    # Generate scripts for top trends
    scripts = []
    for trend in trends:
        template = select_template(trend, templates)
        if template:
            script = generate_script(trend, template, competitor_data)
            scripts.append(script)

    # Determine status
    if not scripts:
        status = "degraded"
    elif len(scripts) < top_n:
        status = "partial"
    else:
        status = "healthy"

    return {
        "script_id": script_id,
        "timestamp": timestamp,
        "status": status,
        "source_bundle": bundle.get("bundle_id"),
        "source_templates": templates_data.get("library_id"),
        "scripts": scripts,
        "meta": {
            "version": "1.0.0",
            "service": "script_generator",
            "story_id": "SKYBEAM-STORY-010",
            "script_count": len(scripts),
            "templates_used": list(set(s.get("template_id") for s in scripts)),
            "degraded": status == "degraded"
        }
    }


def validate_schema(data: dict) -> tuple[bool, Optional[str]]:
    """Validate scripts against schema (basic validation)."""
    required = ["script_id", "timestamp", "status", "source_bundle", "source_templates", "scripts", "meta"]
    for field in required:
        if field not in data:
            return False, f"Missing required field: {field}"

    if data["status"] not in ["healthy", "partial", "degraded"]:
        return False, f"Invalid status: {data['status']}"

    if not isinstance(data["scripts"], list):
        return False, "scripts must be a list"

    meta_required = ["version", "service", "story_id", "script_count"]
    for field in meta_required:
        if field not in data.get("meta", {}):
            return False, f"Missing meta field: {field}"

    return True, None


def write_scripts(scripts: dict) -> None:
    """Write scripts to output file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(scripts, f, indent=2)


async def publish_to_nats(scripts: dict) -> bool:
    """Publish scripts to NATS."""
    try:
        import nats
        nc = await nats.connect(NATS_URL)
        payload = json.dumps(scripts).encode()
        await nc.publish(NATS_TOPIC, payload)
        await nc.flush()
        await nc.close()
        return True
    except Exception as e:
        print(f"NATS publish error: {e}", file=sys.stderr)
        return False


async def run_once(test_degraded: bool = False) -> dict:
    """Run a single script generation cycle."""
    print("=" * 70)
    print("  SKYBEAM Script Generator Service (STORY-010)")
    print("=" * 70)

    # Load bundle
    print("\n[1] Loading research bundle...")
    bundle, error = load_json_file(BUNDLE_FILE)
    if error:
        print(f"  Warning: {error}")
    else:
        print(f"  Loaded: {bundle.get('bundle_id')}")

    # Load templates
    print("[2] Loading template library...")
    templates_data, error = load_json_file(TEMPLATES_FILE)
    if error:
        print(f"  Warning: {error}")
    else:
        print(f"  Loaded: {templates_data.get('library_id')} ({templates_data.get('meta', {}).get('template_count')} templates)")

    # Generate scripts
    print("[3] Generating scripts...")
    scripts = generate_scripts(bundle, templates_data, top_n=3, test_degraded=test_degraded)
    print(f"  Script ID: {scripts['script_id']}")
    print(f"  Status: {scripts['status']}")
    print(f"  Scripts: {scripts['meta']['script_count']}")

    # Validate
    print("[4] Validating schema...")
    valid, error = validate_schema(scripts)
    if not valid:
        print(f"  FAIL: {error}")
        return scripts
    print(f"  Schema: VALID")

    # Write
    print("[5] Writing output...")
    write_scripts(scripts)
    print(f"  File written: {OUTPUT_FILE}")

    # Publish
    print("[6] Publishing to NATS...")
    nats_ok = await publish_to_nats(scripts)
    print(f"  NATS published: {nats_ok}")

    # Summary
    print("=" * 70)
    print("  PROOF ARTIFACTS:")
    print(f"  - File: {OUTPUT_FILE}")
    print(f"  - Script ID: {scripts['script_id']}")
    print(f"  - Status: {scripts['status']}")
    print(f"  - Scripts: {scripts['meta']['script_count']}")
    if scripts['meta'].get('templates_used'):
        print(f"  - Templates: {', '.join(scripts['meta']['templates_used'])}")
    print(f"  - NATS: {nats_ok}")
    print("=" * 70)

    return scripts


def main():
    parser = argparse.ArgumentParser(description="SKYBEAM Script Generator Service")
    parser.add_argument("--test-degraded", action="store_true", help="Test degraded mode")
    args = parser.parse_args()

    asyncio.run(run_once(test_degraded=args.test_degraded))


if __name__ == "__main__":
    main()
