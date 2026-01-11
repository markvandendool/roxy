#!/usr/bin/env python3
"""
SKYBEAM Competitor Analyzer Service (STORY-008)
================================================

Analyzes current trends against competitor coverage to find differentiation angles.

Input:  ~/.roxy/content-pipeline/trends/trends_latest.json
Output: ~/.roxy/content-pipeline/competitors/competitors_latest.json
NATS:   ghost.content.competitors

Usage:
    python3 competitor_analyzer.py              # Normal run
    python3 competitor_analyzer.py --test-degraded  # Test degraded mode
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
TRENDS_FILE = Path.home() / ".roxy/content-pipeline/trends/trends_latest.json"
OUTPUT_DIR = Path.home() / ".roxy/content-pipeline/competitors"
OUTPUT_FILE = OUTPUT_DIR / "competitors_latest.json"
COMPETITORS_FILE = SCRIPT_DIR / "competitors_list.json"
SCHEMA_FILE = SCRIPT_DIR / "schemas/competitor_analysis.json"

# NATS config
NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")
NATS_TOPIC = "ghost.content.competitors"


def load_trends(path: Path) -> tuple[Optional[dict], Optional[str]]:
    """Load trends from file."""
    if not path.exists():
        return None, f"Trends file not found: {path}"
    try:
        with open(path) as f:
            data = json.load(f)
        return data, None
    except Exception as e:
        return None, f"Failed to load trends: {e}"


def load_competitors(path: Path) -> tuple[Optional[list], Optional[str]]:
    """Load competitor list from file."""
    if not path.exists():
        return None, f"Competitors file not found: {path}"
    try:
        with open(path) as f:
            data = json.load(f)
        return data.get("competitors", []), None
    except Exception as e:
        return None, f"Failed to load competitors: {e}"


def match_competitors_to_trend(trend: dict, competitors: list) -> list:
    """Find relevant competitors for a trend based on category matching."""
    trend_title = trend.get("title", "").lower()
    trend_category = trend.get("category", "")
    trend_source = trend.get("source", "").lower()

    relevant = []

    # Category mapping
    category_map = {
        "ai": ["ai_deep_dive", "ai_tools", "ai_research", "ai_developer", "ai_interviews"],
        "ai_research": ["ai_research", "ai_deep_dive", "developer"],
        "tech": ["tech_review", "tech_news", "developer"],
    }

    matched_categories = category_map.get(trend_category, ["tech_news"])

    for comp in competitors:
        comp_category = comp.get("category", "")
        comp_focus = [f.lower() for f in comp.get("focus", [])]

        # Check category match
        if comp_category in matched_categories:
            likelihood = "high"
        elif any(kw in trend_title for kw in comp_focus):
            likelihood = "medium"
        else:
            likelihood = "low"
            continue  # Skip low likelihood for brevity

        # Generate angle based on competitor focus
        angle = generate_angle(comp, trend)

        relevant.append({
            "name": comp.get("name"),
            "category": comp_category,
            "likelihood": likelihood,
            "angle": angle
        })

    # Sort by likelihood (high first) and limit to top 5
    likelihood_order = {"high": 0, "medium": 1, "low": 2}
    relevant.sort(key=lambda x: likelihood_order.get(x["likelihood"], 2))
    return relevant[:5]


def generate_angle(competitor: dict, trend: dict) -> str:
    """Generate predicted angle a competitor would take."""
    name = competitor.get("name", "")
    category = competitor.get("category", "")
    focus = competitor.get("focus", [])

    angles = {
        "tech_review": f"Hands-on demo and first impressions",
        "developer": f"Code tutorial and implementation walkthrough",
        "ai_deep_dive": f"Technical deep dive into architecture and implications",
        "ai_tools": f"Practical how-to guide for using related tools",
        "ai_research": f"Paper review and research context",
        "ai_interviews": f"Interview with key figures involved",
        "tech_news": f"News coverage and industry analysis",
        "ai_developer": f"Building a project using this technology",
    }

    return angles.get(category, "General coverage and commentary")


def generate_differentiation(trend: dict, competitors: list) -> list:
    """Generate differentiation strategies for SKYBEAM."""
    strategies = []

    # Find gaps based on competitor categories
    competitor_categories = {c.get("category") for c in competitors}

    if "ai_deep_dive" not in competitor_categories:
        strategies.append("Deep technical analysis that most creators skip")

    if "developer" not in competitor_categories:
        strategies.append("Code-first implementation walkthrough")

    # Always add unique SKYBEAM angles
    strategies.extend([
        "Multi-modal presentation combining code, visuals, and narration",
        "Unique perspective from AI-powered content pipeline",
        "Real-time data integration and live demonstrations",
    ])

    return strategies[:4]


def generate_coverage_angle(trend: dict) -> str:
    """Generate SKYBEAM's unique coverage angle."""
    category = trend.get("category", "")

    angles = {
        "ai": "Technical breakdown with practical applications and code examples",
        "ai_research": "Research paper analysis with visual explanations and implementation insights",
        "tech": "Industry analysis with AI-powered insights and trend forecasting",
    }

    return angles.get(category, "Comprehensive coverage with unique AI-assisted perspective")


def analyze_trend(trend: dict, competitors: list) -> dict:
    """Generate competitor analysis for a single trend."""
    relevant_competitors = match_competitors_to_trend(trend, competitors)

    return {
        "trend_title": trend.get("title", "Unknown"),
        "relevant_competitors": relevant_competitors,
        "coverage_angle": generate_coverage_angle(trend),
        "differentiation": generate_differentiation(trend, relevant_competitors)
    }


def generate_analysis(
    trends_data: Optional[dict],
    competitors: list,
    top_n: int = 5,
    test_degraded: bool = False
) -> dict:
    """Generate competitor analysis from trends."""
    timestamp = datetime.now(timezone.utc).isoformat()
    short_id = uuid.uuid4().hex[:8]
    analysis_id = f"COMP_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{short_id}"

    # Degraded mode
    if test_degraded or trends_data is None or not competitors:
        return {
            "analysis_id": analysis_id,
            "timestamp": timestamp,
            "status": "degraded",
            "source_trends": None,
            "analyses": [],
            "meta": {
                "version": "1.0.0",
                "service": "competitor_analyzer",
                "story_id": "SKYBEAM-STORY-008",
                "analysis_count": 0,
                "degraded": True
            }
        }

    # Get top trends
    trends = trends_data.get("trends", [])[:top_n]
    source_snapshot = trends_data.get("snapshot_id")

    # Analyze each trend
    analyses = []
    for trend in trends:
        analysis = analyze_trend(trend, competitors)
        analyses.append(analysis)

    return {
        "analysis_id": analysis_id,
        "timestamp": timestamp,
        "status": "healthy",
        "source_trends": source_snapshot,
        "analyses": analyses,
        "meta": {
            "version": "1.0.0",
            "service": "competitor_analyzer",
            "story_id": "SKYBEAM-STORY-008",
            "analysis_count": len(analyses),
            "degraded": False
        }
    }


def validate_schema(data: dict) -> tuple[bool, Optional[str]]:
    """Validate analysis against schema (basic validation without jsonschema)."""
    required = ["analysis_id", "timestamp", "status", "source_trends", "analyses", "meta"]
    for field in required:
        if field not in data:
            return False, f"Missing required field: {field}"

    if data["status"] not in ["healthy", "partial", "degraded"]:
        return False, f"Invalid status: {data['status']}"

    if not isinstance(data["analyses"], list):
        return False, "analyses must be a list"

    meta_required = ["version", "service", "story_id", "analysis_count"]
    for field in meta_required:
        if field not in data.get("meta", {}):
            return False, f"Missing meta field: {field}"

    return True, None


def write_analysis(analysis: dict) -> None:
    """Write analysis to output file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(analysis, f, indent=2)


async def publish_to_nats(analysis: dict) -> bool:
    """Publish analysis to NATS."""
    try:
        import nats
        nc = await nats.connect(NATS_URL)
        payload = json.dumps(analysis).encode()
        await nc.publish(NATS_TOPIC, payload)
        await nc.flush()
        await nc.close()
        return True
    except Exception as e:
        print(f"NATS publish error: {e}", file=sys.stderr)
        return False


async def run_once(test_degraded: bool = False) -> dict:
    """Run a single analysis cycle."""
    print("=" * 70)
    print("  SKYBEAM Competitor Analyzer (STORY-008)")
    print("=" * 70)

    # Load trends
    print("\n[1] Loading trends...")
    trends_data, error = load_trends(TRENDS_FILE)
    if error:
        print(f"  Warning: {error}")
    else:
        print(f"  Loaded: {len(trends_data.get('trends', []))} trends")

    # Load competitors
    print("[2] Loading competitors...")
    competitors, error = load_competitors(COMPETITORS_FILE)
    if error:
        print(f"  Warning: {error}")
        competitors = []
    else:
        print(f"  Loaded: {len(competitors)} competitors")

    # Generate analysis
    print("[3] Generating analysis...")
    analysis = generate_analysis(trends_data, competitors, top_n=5, test_degraded=test_degraded)
    print(f"  Analysis ID: {analysis['analysis_id']}")
    print(f"  Status: {analysis['status']}")
    print(f"  Analyses: {analysis['meta']['analysis_count']}")

    # Validate
    print("[4] Validating schema...")
    valid, error = validate_schema(analysis)
    if not valid:
        print(f"  FAIL: {error}")
        return analysis
    print(f"  Schema: VALID")

    # Write
    print("[5] Writing output...")
    write_analysis(analysis)
    print(f"  File written: {OUTPUT_FILE}")

    # Publish
    print("[6] Publishing to NATS...")
    nats_ok = await publish_to_nats(analysis)
    print(f"  NATS published: {nats_ok}")

    # Summary
    print("=" * 70)
    print("  PROOF ARTIFACTS:")
    print(f"  - File: {OUTPUT_FILE}")
    print(f"  - Analysis: {analysis['analysis_id']}")
    print(f"  - Status: {analysis['status']}")
    print(f"  - Analyses: {analysis['meta']['analysis_count']}")
    print(f"  - NATS: {nats_ok}")
    print("=" * 70)

    return analysis


def main():
    parser = argparse.ArgumentParser(description="SKYBEAM Competitor Analyzer")
    parser.add_argument("--test-degraded", action="store_true", help="Test degraded mode")
    args = parser.parse_args()

    asyncio.run(run_once(test_degraded=args.test_degraded))


if __name__ == "__main__":
    main()
