#!/usr/bin/env python3
"""
SKYBEAM STORY-006: Trend Detector Service
==========================================

PURPOSE: Fetch trends from RSS sources and produce structured JSON snapshots.

INPUTS: 3 RSS feeds (tech/AI focused)
OUTPUTS:
  - ~/.roxy/content-pipeline/trends/trends_latest.json
  - NATS publish to ghost.content.trends

USAGE:
  # One-shot mode (default)
  python3 trend_detector.py

  # Daemon mode (interval in seconds)
  python3 trend_detector.py --daemon --interval 3600

  # Test degraded mode (simulate offline)
  python3 trend_detector.py --test-degraded

PROOF REQUIREMENTS:
  - Schema validation passes
  - At least 1 successful snapshot file written
  - At least 1 NATS publish verified
"""

import asyncio
import json
import hashlib
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import feedparser
import nats

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
RSS_FEEDS = [
    {
        "name": "Hacker News",
        "url": "https://hnrss.org/frontpage",
        "category": "tech"
    },
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "category": "ai"
    },
    {
        "name": "MIT News AI",
        "url": "https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml",
        "category": "ai_research"
    }
]

OUTPUT_DIR = Path.home() / ".roxy" / "content-pipeline" / "trends"
OUTPUT_FILE = OUTPUT_DIR / "trends_latest.json"
NATS_URL = "nats://localhost:4222"
NATS_TOPIC = "ghost.content.trends"

# ─────────────────────────────────────────────────────────────────────────────
# Schema Definition
# ─────────────────────────────────────────────────────────────────────────────
SCHEMA = {
    "type": "object",
    "required": ["snapshot_id", "timestamp", "sources", "trends", "meta"],
    "properties": {
        "snapshot_id": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "sources": {"type": "array", "items": {"type": "object"}},
        "trends": {"type": "array", "items": {"type": "object"}},
        "meta": {"type": "object"}
    }
}


def validate_schema(data: dict) -> tuple[bool, Optional[str]]:
    """Simple schema validation without jsonschema dependency."""
    required = ["snapshot_id", "timestamp", "status", "sources", "trends", "meta"]
    for field in required:
        if field not in data:
            return False, f"Missing required field: {field}"

    if not isinstance(data["snapshot_id"], str):
        return False, "snapshot_id must be string"
    if not isinstance(data["timestamp"], str):
        return False, "timestamp must be string"
    if not isinstance(data["status"], str):
        return False, "status must be string"
    if data["status"] not in ["healthy", "partial", "degraded"]:
        return False, f"status must be healthy/partial/degraded, got: {data['status']}"
    if not isinstance(data["sources"], list):
        return False, "sources must be array"
    if not isinstance(data["trends"], list):
        return False, "trends must be array"
    if not isinstance(data["meta"], dict):
        return False, "meta must be object"

    return True, None


# ─────────────────────────────────────────────────────────────────────────────
# RSS Fetching
# ─────────────────────────────────────────────────────────────────────────────
def fetch_feed(feed_config: dict) -> dict:
    """Fetch and parse a single RSS feed."""
    name = feed_config["name"]
    url = feed_config["url"]
    category = feed_config["category"]

    print(f"  Fetching: {name}...")

    try:
        parsed = feedparser.parse(url)

        if parsed.bozo and not parsed.entries:
            return {
                "name": name,
                "url": url,
                "category": category,
                "status": "error",
                "error": str(parsed.bozo_exception) if parsed.bozo_exception else "Parse error",
                "items": []
            }

        items = []
        for entry in parsed.entries[:10]:  # Top 10 per feed
            item = {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", entry.get("updated", "")),
                "summary": entry.get("summary", "")[:500] if entry.get("summary") else ""
            }
            items.append(item)

        return {
            "name": name,
            "url": url,
            "category": category,
            "status": "success",
            "item_count": len(items),
            "items": items
        }

    except Exception as e:
        return {
            "name": name,
            "url": url,
            "category": category,
            "status": "error",
            "error": str(e),
            "items": []
        }


def extract_trends(sources: list[dict]) -> list[dict]:
    """Extract and score trends from fetched sources."""
    trends = []
    seen_titles = set()

    for source in sources:
        if source["status"] != "success":
            continue

        for item in source["items"]:
            title = item["title"].lower()

            # Simple deduplication by title similarity
            title_hash = hashlib.md5(title.encode()).hexdigest()[:8]
            if title_hash in seen_titles:
                continue
            seen_titles.add(title_hash)

            # Simple relevance scoring
            score = 50  # Base score
            keywords = ["ai", "artificial intelligence", "llm", "gpt", "claude",
                       "machine learning", "automation", "robot", "startup",
                       "tech", "software", "developer"]

            for kw in keywords:
                if kw in title:
                    score += 10

            # Boost recent items (basic heuristic)
            if source["category"] in ["ai", "ai_research"]:
                score += 15

            trends.append({
                "title": item["title"],
                "link": item["link"],
                "source": source["name"],
                "category": source["category"],
                "score": min(score, 100),
                "summary": item["summary"]
            })

    # Sort by score descending
    trends.sort(key=lambda x: x["score"], reverse=True)

    return trends[:20]  # Top 20 trends


# ─────────────────────────────────────────────────────────────────────────────
# Snapshot Generation
# ─────────────────────────────────────────────────────────────────────────────
def generate_snapshot(test_degraded: bool = False) -> dict:
    """Generate a complete trend snapshot.

    Args:
        test_degraded: If True, simulate offline mode (all feeds fail)
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    snapshot_id = f"TREND_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(timestamp.encode()).hexdigest()[:8]}"

    print(f"\n[TREND DETECTOR] Generating snapshot: {snapshot_id}")
    print(f"  Timestamp: {timestamp}")
    print(f"  Sources: {len(RSS_FEEDS)}")
    if test_degraded:
        print("  Mode: DEGRADED (test/offline simulation)")

    # Fetch all feeds (or simulate failure in degraded mode)
    sources = []
    if test_degraded:
        # Simulate all feeds failing
        for feed in RSS_FEEDS:
            sources.append({
                "name": feed["name"],
                "url": feed["url"],
                "category": feed["category"],
                "status": "error",
                "error": "Simulated offline mode (--test-degraded)",
                "items": []
            })
    else:
        for feed in RSS_FEEDS:
            source = fetch_feed(feed)
            sources.append(source)

    # Extract trends (will be empty if all sources failed)
    trends = extract_trends(sources)

    # Calculate success count
    success_count = sum(1 for s in sources if s["status"] == "success")

    # Determine status
    if success_count == 0:
        status = "degraded"
    elif success_count < len(sources):
        status = "partial"
    else:
        status = "healthy"

    # Build snapshot
    snapshot = {
        "snapshot_id": snapshot_id,
        "timestamp": timestamp,
        "status": status,
        "sources": [
            {
                "name": s["name"],
                "url": s["url"],
                "category": s["category"],
                "status": s["status"],
                "item_count": s.get("item_count", 0)
            }
            for s in sources
        ],
        "trends": trends,
        "meta": {
            "version": "1.0.0",
            "service": "trend_detector",
            "story_id": "SKYBEAM-STORY-006",
            "source_count": len(sources),
            "trend_count": len(trends),
            "success_count": success_count,
            "degraded": status == "degraded"
        }
    }

    return snapshot


# ─────────────────────────────────────────────────────────────────────────────
# File Output
# ─────────────────────────────────────────────────────────────────────────────
def write_snapshot(snapshot: dict) -> Path:
    """Write snapshot to file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(snapshot, f, indent=2)

    print(f"  Written: {OUTPUT_FILE}")
    return OUTPUT_FILE


# ─────────────────────────────────────────────────────────────────────────────
# NATS Publishing
# ─────────────────────────────────────────────────────────────────────────────
async def publish_to_nats(snapshot: dict) -> bool:
    """Publish snapshot to NATS topic."""
    try:
        nc = await nats.connect(NATS_URL)

        payload = json.dumps({
            "snapshot_id": snapshot["snapshot_id"],
            "timestamp": snapshot["timestamp"],
            "status": snapshot["status"],
            "degraded": snapshot["meta"]["degraded"],
            "trend_count": snapshot["meta"]["trend_count"],
            "top_trends": snapshot["trends"][:5]  # Top 5 for NATS message
        }).encode()

        await nc.publish(NATS_TOPIC, payload)
        await nc.flush()
        await nc.close()

        print(f"  Published to NATS: {NATS_TOPIC} (status={snapshot['status']})")
        return True

    except Exception as e:
        print(f"  NATS error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
async def run_once(test_degraded: bool = False) -> dict:
    """Run a single trend detection cycle."""
    snapshot = generate_snapshot(test_degraded=test_degraded)

    # Validate schema
    valid, error = validate_schema(snapshot)
    if not valid:
        print(f"  Schema validation FAILED: {error}")
        return {"success": False, "error": error}

    print("  Schema validation: PASSED")

    # Write to file
    output_path = write_snapshot(snapshot)

    # Publish to NATS
    nats_ok = await publish_to_nats(snapshot)

    print(f"\n[TREND DETECTOR] Cycle complete")
    print(f"  Snapshot ID: {snapshot['snapshot_id']}")
    print(f"  Status: {snapshot['status']}")
    print(f"  Trends found: {snapshot['meta']['trend_count']}")
    print(f"  Sources OK: {snapshot['meta']['success_count']}/{snapshot['meta']['source_count']}")
    print(f"  File written: {output_path}")
    print(f"  NATS published: {nats_ok}")

    return {
        "success": True,
        "snapshot_id": snapshot["snapshot_id"],
        "status": snapshot["status"],
        "degraded": snapshot["meta"]["degraded"],
        "file": str(output_path),
        "nats_published": nats_ok
    }


async def daemon_loop(interval: int):
    """Run in daemon mode with interval."""
    print(f"[TREND DETECTOR] Starting daemon mode (interval: {interval}s)")

    while True:
        await run_once()
        print(f"\n[TREND DETECTOR] Sleeping for {interval} seconds...")
        await asyncio.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="SKYBEAM Trend Detector Service")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode")
    parser.add_argument("--interval", type=int, default=3600, help="Interval in seconds (daemon mode)")
    parser.add_argument("--test-degraded", action="store_true", help="Simulate offline/degraded mode")
    args = parser.parse_args()

    print("=" * 70)
    print("  SKYBEAM STORY-006: Trend Detector Service")
    print("=" * 70)

    if args.daemon:
        asyncio.run(daemon_loop(args.interval))
    else:
        result = asyncio.run(run_once(test_degraded=args.test_degraded))
        if result["success"]:
            print("\n" + "=" * 70)
            print("  PROOF ARTIFACTS:")
            print(f"  - File: {result['file']}")
            print(f"  - Snapshot: {result['snapshot_id']}")
            print(f"  - Status: {result.get('status', 'unknown')}")
            print(f"  - NATS: {result['nats_published']}")
            print("=" * 70)


if __name__ == "__main__":
    main()
