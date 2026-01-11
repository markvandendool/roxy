#!/usr/bin/env python3
"""
SKYBEAM Research Bundle Writer (STORY-009)
============================================

Combines outputs from trend_detector, deep_research_agent, and competitor_analyzer
into a single research bundle.

Input:
  ~/.roxy/content-pipeline/trends/trends_latest.json
  ~/.roxy/content-pipeline/research/research_latest.json
  ~/.roxy/content-pipeline/competitors/competitors_latest.json

Output:
  ~/.roxy/content-pipeline/bundles/research_bundle_latest.json

NATS:
  ghost.content.bundle

Usage:
    python3 bundle_writer.py              # Normal run
    python3 bundle_writer.py --test-degraded  # Test degraded mode
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
TRENDS_FILE = Path.home() / ".roxy/content-pipeline/trends/trends_latest.json"
RESEARCH_FILE = Path.home() / ".roxy/content-pipeline/research/research_latest.json"
COMPETITORS_FILE = Path.home() / ".roxy/content-pipeline/competitors/competitors_latest.json"
OUTPUT_DIR = Path.home() / ".roxy/content-pipeline/bundles"
OUTPUT_FILE = OUTPUT_DIR / "research_bundle_latest.json"

# NATS config
NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")
NATS_TOPIC = "ghost.content.bundle"


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


def determine_bundle_status(
    trends: Optional[dict],
    research: Optional[dict],
    competitors: Optional[dict]
) -> str:
    """
    Determine bundle status based on component statuses.
    healthy = all three healthy
    partial = some healthy, some degraded/missing
    degraded = all missing or all degraded
    """
    statuses = []

    for data in [trends, research, competitors]:
        if data is None:
            statuses.append("missing")
        else:
            statuses.append(data.get("status", "unknown"))

    # All healthy = healthy
    if all(s == "healthy" for s in statuses):
        return "healthy"

    # All missing/degraded = degraded
    if all(s in ["missing", "degraded"] for s in statuses):
        return "degraded"

    # Mixed = partial
    return "partial"


def generate_bundle(
    trends: Optional[dict],
    research: Optional[dict],
    competitors: Optional[dict],
    test_degraded: bool = False
) -> dict:
    """Generate the combined research bundle."""
    timestamp = datetime.now(timezone.utc).isoformat()
    short_id = uuid.uuid4().hex[:8]
    bundle_id = f"BUNDLE_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{short_id}"

    # Degraded mode
    if test_degraded:
        return {
            "bundle_id": bundle_id,
            "timestamp": timestamp,
            "status": "degraded",
            "components": {
                "trends": None,
                "research": None,
                "competitors": None
            },
            "summary": {
                "trend_count": 0,
                "brief_count": 0,
                "analysis_count": 0,
                "top_trend": None,
                "top_competitors": []
            },
            "meta": {
                "version": "1.0.0",
                "service": "bundle_writer",
                "story_id": "SKYBEAM-STORY-009",
                "degraded": True
            }
        }

    # Determine status
    status = determine_bundle_status(trends, research, competitors)

    # Extract counts
    trend_count = len(trends.get("trends", [])) if trends else 0
    brief_count = research.get("meta", {}).get("brief_count", 0) if research else 0
    analysis_count = competitors.get("meta", {}).get("analysis_count", 0) if competitors else 0

    # Top trend
    top_trend = None
    if trends and trends.get("trends"):
        top = trends["trends"][0]
        top_trend = {
            "title": top.get("title"),
            "source": top.get("source"),
            "score": top.get("score")
        }

    # Top competitors from first analysis
    top_competitors = []
    if competitors and competitors.get("analyses"):
        first_analysis = competitors["analyses"][0]
        for comp in first_analysis.get("relevant_competitors", [])[:3]:
            top_competitors.append({
                "name": comp.get("name"),
                "likelihood": comp.get("likelihood")
            })

    return {
        "bundle_id": bundle_id,
        "timestamp": timestamp,
        "status": status,
        "components": {
            "trends": {
                "snapshot_id": trends.get("snapshot_id") if trends else None,
                "status": trends.get("status") if trends else "missing",
                "count": trend_count
            },
            "research": {
                "brief_id": research.get("brief_id") if research else None,
                "status": research.get("status") if research else "missing",
                "count": brief_count
            },
            "competitors": {
                "analysis_id": competitors.get("analysis_id") if competitors else None,
                "status": competitors.get("status") if competitors else "missing",
                "count": analysis_count
            }
        },
        "summary": {
            "trend_count": trend_count,
            "brief_count": brief_count,
            "analysis_count": analysis_count,
            "top_trend": top_trend,
            "top_competitors": top_competitors
        },
        "meta": {
            "version": "1.0.0",
            "service": "bundle_writer",
            "story_id": "SKYBEAM-STORY-009",
            "degraded": status == "degraded"
        }
    }


def validate_schema(data: dict) -> tuple[bool, Optional[str]]:
    """Validate bundle against schema (basic validation)."""
    required = ["bundle_id", "timestamp", "status", "components", "summary", "meta"]
    for field in required:
        if field not in data:
            return False, f"Missing required field: {field}"

    if data["status"] not in ["healthy", "partial", "degraded"]:
        return False, f"Invalid status: {data['status']}"

    components_required = ["trends", "research", "competitors"]
    for comp in components_required:
        if comp not in data.get("components", {}):
            return False, f"Missing component: {comp}"

    meta_required = ["version", "service", "story_id"]
    for field in meta_required:
        if field not in data.get("meta", {}):
            return False, f"Missing meta field: {field}"

    return True, None


def write_bundle(bundle: dict) -> None:
    """Write bundle to output file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(bundle, f, indent=2)


async def publish_to_nats(bundle: dict) -> bool:
    """Publish bundle to NATS."""
    try:
        import nats
        nc = await nats.connect(NATS_URL)
        payload = json.dumps(bundle).encode()
        await nc.publish(NATS_TOPIC, payload)
        await nc.flush()
        await nc.close()
        return True
    except Exception as e:
        print(f"NATS publish error: {e}", file=sys.stderr)
        return False


async def run_once(test_degraded: bool = False) -> dict:
    """Run a single bundle generation cycle."""
    print("=" * 70)
    print("  SKYBEAM Research Bundle Writer (STORY-009)")
    print("=" * 70)

    # Load components
    print("\n[1] Loading trends...")
    trends, error = load_json_file(TRENDS_FILE)
    if error:
        print(f"  Warning: {error}")
    else:
        print(f"  Loaded: {trends.get('snapshot_id')}")

    print("[2] Loading research...")
    research, error = load_json_file(RESEARCH_FILE)
    if error:
        print(f"  Warning: {error}")
    else:
        print(f"  Loaded: {research.get('brief_id')}")

    print("[3] Loading competitors...")
    competitors, error = load_json_file(COMPETITORS_FILE)
    if error:
        print(f"  Warning: {error}")
    else:
        print(f"  Loaded: {competitors.get('analysis_id')}")

    # Generate bundle
    print("[4] Generating bundle...")
    bundle = generate_bundle(trends, research, competitors, test_degraded=test_degraded)
    print(f"  Bundle ID: {bundle['bundle_id']}")
    print(f"  Status: {bundle['status']}")

    # Validate
    print("[5] Validating schema...")
    valid, error = validate_schema(bundle)
    if not valid:
        print(f"  FAIL: {error}")
        return bundle
    print(f"  Schema: VALID")

    # Write
    print("[6] Writing output...")
    write_bundle(bundle)
    print(f"  File written: {OUTPUT_FILE}")

    # Publish
    print("[7] Publishing to NATS...")
    nats_ok = await publish_to_nats(bundle)
    print(f"  NATS published: {nats_ok}")

    # Summary
    print("=" * 70)
    print("  PROOF ARTIFACTS:")
    print(f"  - File: {OUTPUT_FILE}")
    print(f"  - Bundle: {bundle['bundle_id']}")
    print(f"  - Status: {bundle['status']}")
    print(f"  - Trends: {bundle['summary']['trend_count']}")
    print(f"  - Briefs: {bundle['summary']['brief_count']}")
    print(f"  - Analyses: {bundle['summary']['analysis_count']}")
    print(f"  - NATS: {nats_ok}")
    print("=" * 70)

    return bundle


def main():
    parser = argparse.ArgumentParser(description="SKYBEAM Research Bundle Writer")
    parser.add_argument("--test-degraded", action="store_true", help="Test degraded mode")
    args = parser.parse_args()

    asyncio.run(run_once(test_degraded=args.test_degraded))


if __name__ == "__main__":
    main()
