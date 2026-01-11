#!/usr/bin/env python3
"""
SKYBEAM STORY-007: Deep Research Agent
=======================================

PURPOSE: Transform trend snapshots into structured research briefs.

INPUT:
  - ~/.roxy/content-pipeline/trends/trends_latest.json (or explicit path)

OUTPUT:
  - ~/.roxy/content-pipeline/research/research_latest.json
  - NATS publish to ghost.content.research

USAGE:
  # One-shot mode (default)
  python3 deep_research_agent.py

  # Custom input file
  python3 deep_research_agent.py --input /path/to/trends.json

  # Test degraded mode (empty/missing input)
  python3 deep_research_agent.py --test-degraded

  # Custom number of trends to process
  python3 deep_research_agent.py --top-n 10

PROOF REQUIREMENTS:
  - Schema validation passes
  - research_latest.json written
  - NATS pub/sub verified
  - Degraded mode tested
"""

import asyncio
import json
import hashlib
import argparse
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import nats

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
TRENDS_DIR = Path.home() / ".roxy" / "content-pipeline" / "trends"
TRENDS_FILE = TRENDS_DIR / "trends_latest.json"
OUTPUT_DIR = Path.home() / ".roxy" / "content-pipeline" / "research"
OUTPUT_FILE = OUTPUT_DIR / "research_latest.json"
SCHEMA_FILE = Path.home() / ".roxy" / "services" / "research" / "schemas" / "research_brief.json"
NATS_URL = "nats://localhost:4222"
NATS_TOPIC = "ghost.content.research"

DEFAULT_TOP_N = 5

# ─────────────────────────────────────────────────────────────────────────────
# Schema Validation
# ─────────────────────────────────────────────────────────────────────────────
def validate_schema(data: dict) -> tuple[bool, Optional[str]]:
    """Simple schema validation without jsonschema dependency."""
    required = ["brief_id", "timestamp", "status", "source_snapshot", "briefs", "meta"]
    for field in required:
        if field not in data:
            return False, f"Missing required field: {field}"

    if not isinstance(data["brief_id"], str):
        return False, "brief_id must be string"
    if not isinstance(data["timestamp"], str):
        return False, "timestamp must be string"
    if not isinstance(data["status"], str):
        return False, "status must be string"
    if data["status"] not in ["healthy", "partial", "degraded"]:
        return False, f"status must be healthy/partial/degraded, got: {data['status']}"
    if not isinstance(data["source_snapshot"], str):
        return False, "source_snapshot must be string"
    if not isinstance(data["briefs"], list):
        return False, "briefs must be array"
    if not isinstance(data["meta"], dict):
        return False, "meta must be object"

    # Validate briefs structure
    for i, brief in enumerate(data["briefs"]):
        if not isinstance(brief.get("title"), str):
            return False, f"briefs[{i}].title must be string"
        if not isinstance(brief.get("claims"), list):
            return False, f"briefs[{i}].claims must be array"
        if not isinstance(brief.get("followups"), list):
            return False, f"briefs[{i}].followups must be array"

    return True, None


# ─────────────────────────────────────────────────────────────────────────────
# Trend Loading
# ─────────────────────────────────────────────────────────────────────────────
def load_trends(input_path: Path) -> tuple[Optional[dict], Optional[str]]:
    """Load trends from JSON file."""
    if not input_path.exists():
        return None, f"Trends file not found: {input_path}"

    try:
        with open(input_path) as f:
            data = json.load(f)
        return data, None
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"
    except Exception as e:
        return None, f"Load error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Claim Extraction (Heuristic-based)
# ─────────────────────────────────────────────────────────────────────────────
def extract_claims(trend: dict) -> list[str]:
    """Extract claims/insights from trend data.

    Uses heuristics since we're not doing web fetching:
    1. Parse summary for key sentences
    2. Generate claims from title and category
    """
    claims = []
    title = trend.get("title", "")
    summary = trend.get("summary", "")
    source = trend.get("source", "")
    category = trend.get("category", "tech")

    # Claim 1: Main topic from title
    if title:
        claims.append(f"This trend focuses on: {title[:100]}")

    # Claim 2: Extract key phrase from summary
    if summary:
        # Take first sentence
        sentences = re.split(r'[.!?]', summary)
        if sentences and sentences[0].strip():
            claims.append(f"Key insight: {sentences[0].strip()[:150]}")

    # Claim 3: Source credibility
    claims.append(f"Source: {source} (category: {category})")

    # Claim 4: Category-specific insight
    if category == "ai":
        claims.append("This relates to commercial AI applications and industry developments")
    elif category == "ai_research":
        claims.append("This relates to academic AI research and new discoveries")
    else:
        claims.append("This relates to general technology and software developments")

    # Claim 5: Actionability
    if any(word in title.lower() for word in ["new", "launch", "release", "announce"]):
        claims.append("This appears to be a new announcement or product launch")
    elif any(word in title.lower() for word in ["research", "study", "paper"]):
        claims.append("This appears to be research-oriented content")
    else:
        claims.append("This is general technology news coverage")

    return claims[:5]  # Max 5 claims


def generate_followups(trend: dict) -> list[str]:
    """Generate follow-up research questions."""
    title = trend.get("title", "")
    category = trend.get("category", "tech")

    followups = []

    # Generic followups based on content
    followups.append(f"What are the key players/companies mentioned?")
    followups.append(f"What is the timeline for this development?")
    followups.append(f"What are the potential implications for the industry?")

    if category in ["ai", "ai_research"]:
        followups.append("What AI models or techniques are involved?")
        followups.append("How does this compare to existing solutions?")
    else:
        followups.append("What technologies are enabling this?")
        followups.append("What are the business model implications?")

    return followups[:5]  # Max 5 followups


# ─────────────────────────────────────────────────────────────────────────────
# Brief Generation
# ─────────────────────────────────────────────────────────────────────────────
def generate_brief(trend: dict) -> dict:
    """Generate a research brief for a single trend."""
    return {
        "title": trend.get("title", "Unknown"),
        "source": trend.get("source", "Unknown"),
        "category": trend.get("category", "unknown"),
        "link": trend.get("link", ""),
        "summary": trend.get("summary", "")[:200],
        "claims": extract_claims(trend),
        "followups": generate_followups(trend)
    }


def generate_research(trends_data: Optional[dict], top_n: int = DEFAULT_TOP_N, test_degraded: bool = False) -> dict:
    """Generate complete research briefs from trends."""
    timestamp = datetime.now(timezone.utc).isoformat()
    brief_id = f"BRIEF_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(timestamp.encode()).hexdigest()[:8]}"

    print(f"\n[DEEP RESEARCH] Generating brief: {brief_id}")
    print(f"  Timestamp: {timestamp}")
    print(f"  Top N: {top_n}")

    # Handle degraded mode
    if test_degraded or trends_data is None:
        print("  Mode: DEGRADED (no valid trend data)")
        return {
            "brief_id": brief_id,
            "timestamp": timestamp,
            "status": "degraded",
            "source_snapshot": "none",
            "briefs": [],
            "meta": {
                "version": "1.0.0",
                "service": "deep_research_agent",
                "story_id": "SKYBEAM-STORY-007",
                "brief_count": 0,
                "degraded": True
            }
        }

    # Extract trends from snapshot
    trends = trends_data.get("trends", [])
    source_snapshot = trends_data.get("snapshot_id", "unknown")
    source_status = trends_data.get("status", "unknown")

    print(f"  Source snapshot: {source_snapshot}")
    print(f"  Source status: {source_status}")
    print(f"  Trends available: {len(trends)}")

    # Generate briefs for top N trends
    briefs = []
    for trend in trends[:top_n]:
        brief = generate_brief(trend)
        briefs.append(brief)
        print(f"    - {brief['title'][:60]}...")

    # Determine status
    if len(briefs) == 0:
        status = "degraded"
    elif len(briefs) < top_n:
        status = "partial"
    else:
        status = "healthy"

    return {
        "brief_id": brief_id,
        "timestamp": timestamp,
        "status": status,
        "source_snapshot": source_snapshot,
        "briefs": briefs,
        "meta": {
            "version": "1.0.0",
            "service": "deep_research_agent",
            "story_id": "SKYBEAM-STORY-007",
            "brief_count": len(briefs),
            "degraded": status == "degraded"
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# File Output
# ─────────────────────────────────────────────────────────────────────────────
def write_research(research: dict) -> Path:
    """Write research to file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(research, f, indent=2)

    print(f"  Written: {OUTPUT_FILE}")
    return OUTPUT_FILE


# ─────────────────────────────────────────────────────────────────────────────
# NATS Publishing
# ─────────────────────────────────────────────────────────────────────────────
async def publish_to_nats(research: dict) -> bool:
    """Publish research to NATS topic."""
    try:
        nc = await nats.connect(NATS_URL)

        payload = json.dumps({
            "brief_id": research["brief_id"],
            "timestamp": research["timestamp"],
            "status": research["status"],
            "degraded": research["meta"]["degraded"],
            "brief_count": research["meta"]["brief_count"],
            "source_snapshot": research["source_snapshot"],
            "briefs_summary": [
                {"title": b["title"][:60], "claims_count": len(b["claims"])}
                for b in research["briefs"][:3]  # Top 3 for NATS message
            ]
        }).encode()

        await nc.publish(NATS_TOPIC, payload)
        await nc.flush()
        await nc.close()

        print(f"  Published to NATS: {NATS_TOPIC} (status={research['status']})")
        return True

    except Exception as e:
        print(f"  NATS error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
async def run_once(input_path: Path = TRENDS_FILE, top_n: int = DEFAULT_TOP_N, test_degraded: bool = False) -> dict:
    """Run a single research cycle."""

    # Load trends (or skip if testing degraded)
    trends_data = None
    if not test_degraded:
        print(f"  Loading trends from: {input_path}")
        trends_data, error = load_trends(input_path)
        if error:
            print(f"  Warning: {error}")

    # Generate research
    research = generate_research(trends_data, top_n=top_n, test_degraded=test_degraded)

    # Validate schema
    valid, error = validate_schema(research)
    if not valid:
        print(f"  Schema validation FAILED: {error}")
        return {"success": False, "error": error}

    print("  Schema validation: PASSED")

    # Write to file
    output_path = write_research(research)

    # Publish to NATS
    nats_ok = await publish_to_nats(research)

    print(f"\n[DEEP RESEARCH] Cycle complete")
    print(f"  Brief ID: {research['brief_id']}")
    print(f"  Status: {research['status']}")
    print(f"  Briefs generated: {research['meta']['brief_count']}")
    print(f"  File written: {output_path}")
    print(f"  NATS published: {nats_ok}")

    return {
        "success": True,
        "brief_id": research["brief_id"],
        "status": research["status"],
        "degraded": research["meta"]["degraded"],
        "brief_count": research["meta"]["brief_count"],
        "file": str(output_path),
        "nats_published": nats_ok
    }


def main():
    parser = argparse.ArgumentParser(description="SKYBEAM Deep Research Agent")
    parser.add_argument("--input", type=str, default=str(TRENDS_FILE), help="Input trends file")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N, help="Number of trends to process")
    parser.add_argument("--test-degraded", action="store_true", help="Simulate degraded mode")
    args = parser.parse_args()

    print("=" * 70)
    print("  SKYBEAM STORY-007: Deep Research Agent")
    print("=" * 70)

    result = asyncio.run(run_once(
        input_path=Path(args.input),
        top_n=args.top_n,
        test_degraded=args.test_degraded
    ))

    if result["success"]:
        print("\n" + "=" * 70)
        print("  PROOF ARTIFACTS:")
        print(f"  - File: {result['file']}")
        print(f"  - Brief: {result['brief_id']}")
        print(f"  - Status: {result['status']}")
        print(f"  - Briefs: {result['brief_count']}")
        print(f"  - NATS: {result['nats_published']}")
        print("=" * 70)


if __name__ == "__main__":
    main()
