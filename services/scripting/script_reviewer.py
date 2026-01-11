#!/usr/bin/env python3
"""
SKYBEAM Script Reviewer Service (STORY-012)
============================================

Reviews generated scripts and provides quality scores and recommendations.

Input:
  ~/.roxy/content-pipeline/scripts/scripts_latest.json

Output:
  ~/.roxy/content-pipeline/scripts/scripts_reviewed.json

NATS:
  ghost.script.reviewed

Usage:
    python3 script_reviewer.py              # Normal run
    python3 script_reviewer.py --test-degraded  # Test degraded mode
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
SCRIPTS_FILE = Path.home() / ".roxy/content-pipeline/scripts/scripts_latest.json"
OUTPUT_DIR = Path.home() / ".roxy/content-pipeline/scripts"
OUTPUT_FILE = OUTPUT_DIR / "scripts_reviewed.json"

# NATS config
NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")
NATS_TOPIC = "ghost.script.reviewed"

# Review thresholds
APPROVAL_THRESHOLD = 7  # Minimum overall score for approval
REJECTION_THRESHOLD = 4  # Below this is rejected


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


def score_hook(script: dict) -> tuple[int, list]:
    """Score the hook strength (1-10)."""
    hook = script.get("hook", "")
    recommendations = []

    score = 5  # Base score

    # Check hook length (20-80 chars is ideal)
    if 20 <= len(hook) <= 80:
        score += 2
    elif len(hook) < 10:
        score -= 2
        recommendations.append("Hook is too short - add more intrigue")
    elif len(hook) > 100:
        score -= 1
        recommendations.append("Hook is too long - trim for impact")

    # Check for engagement patterns
    if any(word in hook.lower() for word in ["why", "how", "what", "this"]):
        score += 1

    # Check for curiosity gap
    if "?" in hook or "..." in hook:
        score += 1

    # Check for power words
    power_words = ["breaking", "just", "secret", "revealed", "honest", "truth", "everything"]
    if any(word in hook.lower() for word in power_words):
        score += 1

    return min(10, max(1, score)), recommendations


def score_content_depth(script: dict) -> tuple[int, list]:
    """Score content depth (1-10)."""
    sections = script.get("sections", [])
    recommendations = []

    score = 5  # Base score

    # Check section count
    if len(sections) >= 4:
        score += 2
    elif len(sections) < 3:
        score -= 2
        recommendations.append("Add more sections for depth")

    # Check for substantive content markers
    all_content = " ".join(s.get("content", "") for s in sections)

    if "[DETAILS]" in all_content or "[ANALYSIS]" in all_content:
        score += 1

    if "[CONTEXT]" in all_content:
        score += 1

    # Check estimated duration (longer = more depth potential)
    duration = script.get("estimated_duration", 0)
    if duration >= 120:
        score += 1
    elif duration < 45:
        recommendations.append("Consider expanding for more depth")

    return min(10, max(1, score)), recommendations


def score_structure_flow(script: dict) -> tuple[int, list]:
    """Score structure and flow (1-10)."""
    sections = script.get("sections", [])
    recommendations = []

    score = 6  # Base score

    # Check for required sections
    section_names = [s.get("section", "").lower() for s in sections]

    if "hook" in section_names:
        score += 1
    else:
        recommendations.append("Missing hook section")

    if "cta" in section_names:
        score += 1
    else:
        recommendations.append("Missing call-to-action section")

    # Check section ordering (hook should be first, cta should be last)
    if section_names and section_names[0] == "hook":
        score += 1
    else:
        recommendations.append("Hook should be the first section")

    if section_names and section_names[-1] == "cta":
        score += 1
    else:
        recommendations.append("CTA should be the last section")

    return min(10, max(1, score)), recommendations


def score_differentiation(script: dict) -> tuple[int, list]:
    """Score differentiation from competitors (1-10)."""
    differentiation = script.get("differentiation", [])
    recommendations = []

    score = 5  # Base score

    # More differentiation points = higher score
    diff_count = len(differentiation)
    if diff_count >= 3:
        score += 3
    elif diff_count >= 2:
        score += 2
    elif diff_count >= 1:
        score += 1
    else:
        score -= 2
        recommendations.append("Add unique angles to differentiate from competitors")

    # Check for actionable differentiation
    if any("code" in d.lower() or "implementation" in d.lower() for d in differentiation):
        score += 1

    return min(10, max(1, score)), recommendations


def review_script(script: dict) -> dict:
    """Review a single script and generate scores/recommendations."""
    # Score each dimension
    hook_score, hook_recs = score_hook(script)
    depth_score, depth_recs = score_content_depth(script)
    flow_score, flow_recs = score_structure_flow(script)
    diff_score, diff_recs = score_differentiation(script)

    # Calculate overall score
    overall = (hook_score + depth_score + flow_score + diff_score) // 4

    # Combine recommendations
    all_recommendations = hook_recs + depth_recs + flow_recs + diff_recs

    # Determine review status
    if overall >= APPROVAL_THRESHOLD:
        review_status = "approved"
    elif overall <= REJECTION_THRESHOLD:
        review_status = "rejected"
    else:
        review_status = "needs_revision"

    # Identify sections needing revision
    revision_needed = []
    sections = script.get("sections", [])
    for section in sections:
        content = section.get("content", "")
        # Flag sections that are just placeholders
        if content.startswith("[") and "]" in content and len(content.split("]")[1].strip()) < 20:
            revision_needed.append({
                "section": section.get("section"),
                "issue": "Content is placeholder-only",
                "suggestion": "Expand with specific details from the trend data"
            })

    # Approved sections are those not in revision_needed
    approved_sections = [
        s.get("section") for s in sections
        if s.get("section") not in [r["section"] for r in revision_needed]
    ]

    return {
        "script_id": script.get("id"),
        "trend_title": script.get("trend_title"),
        "template_id": script.get("template_id"),
        "review_status": review_status,
        "scores": {
            "hook_strength": hook_score,
            "content_depth": depth_score,
            "structure_flow": flow_score,
            "differentiation": diff_score,
            "overall": overall
        },
        "recommendations": all_recommendations[:5],  # Top 5 recommendations
        "approved_sections": approved_sections,
        "revision_needed": revision_needed[:3],  # Top 3 revision items
        "production_ready": review_status == "approved" and len(revision_needed) == 0
    }


def generate_review(
    scripts_data: Optional[dict],
    test_degraded: bool = False
) -> dict:
    """Generate review for all scripts."""
    timestamp = datetime.now(timezone.utc).isoformat()
    short_id = uuid.uuid4().hex[:8]
    review_id = f"REVIEW_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{short_id}"

    # Degraded mode
    if test_degraded or scripts_data is None:
        return {
            "review_id": review_id,
            "timestamp": timestamp,
            "status": "degraded",
            "source_scripts": None,
            "reviewed_scripts": [],
            "summary": {
                "total_reviewed": 0,
                "approved": 0,
                "needs_revision": 0,
                "rejected": 0,
                "average_score": 0
            },
            "meta": {
                "version": "1.0.0",
                "service": "script_reviewer",
                "story_id": "SKYBEAM-STORY-012",
                "review_count": 0,
                "degraded": True
            }
        }

    scripts = scripts_data.get("scripts", [])
    if not scripts:
        return {
            "review_id": review_id,
            "timestamp": timestamp,
            "status": "degraded",
            "source_scripts": scripts_data.get("script_id"),
            "reviewed_scripts": [],
            "summary": {
                "total_reviewed": 0,
                "approved": 0,
                "needs_revision": 0,
                "rejected": 0,
                "average_score": 0
            },
            "meta": {
                "version": "1.0.0",
                "service": "script_reviewer",
                "story_id": "SKYBEAM-STORY-012",
                "review_count": 0,
                "degraded": True
            }
        }

    # Review each script
    reviewed_scripts = []
    for script in scripts:
        review = review_script(script)
        reviewed_scripts.append(review)

    # Calculate summary
    total = len(reviewed_scripts)
    approved = sum(1 for r in reviewed_scripts if r["review_status"] == "approved")
    needs_revision = sum(1 for r in reviewed_scripts if r["review_status"] == "needs_revision")
    rejected = sum(1 for r in reviewed_scripts if r["review_status"] == "rejected")
    avg_score = sum(r["scores"]["overall"] for r in reviewed_scripts) / total if total > 0 else 0

    # Determine status
    if approved == total:
        status = "healthy"
    elif rejected == total:
        status = "degraded"
    else:
        status = "partial"

    return {
        "review_id": review_id,
        "timestamp": timestamp,
        "status": status,
        "source_scripts": scripts_data.get("script_id"),
        "reviewed_scripts": reviewed_scripts,
        "summary": {
            "total_reviewed": total,
            "approved": approved,
            "needs_revision": needs_revision,
            "rejected": rejected,
            "average_score": round(avg_score, 1)
        },
        "meta": {
            "version": "1.0.0",
            "service": "script_reviewer",
            "story_id": "SKYBEAM-STORY-012",
            "review_count": total,
            "degraded": status == "degraded"
        }
    }


def validate_schema(data: dict) -> tuple[bool, Optional[str]]:
    """Validate review against schema (basic validation)."""
    required = ["review_id", "timestamp", "status", "source_scripts", "reviewed_scripts", "meta"]
    for field in required:
        if field not in data:
            return False, f"Missing required field: {field}"

    if data["status"] not in ["healthy", "partial", "degraded"]:
        return False, f"Invalid status: {data['status']}"

    if not isinstance(data["reviewed_scripts"], list):
        return False, "reviewed_scripts must be a list"

    meta_required = ["version", "service", "story_id", "review_count"]
    for field in meta_required:
        if field not in data.get("meta", {}):
            return False, f"Missing meta field: {field}"

    return True, None


def write_review(review: dict) -> None:
    """Write review to output file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(review, f, indent=2)


async def publish_to_nats(review: dict) -> bool:
    """Publish review to NATS."""
    try:
        import nats
        nc = await nats.connect(NATS_URL)
        payload = json.dumps(review).encode()
        await nc.publish(NATS_TOPIC, payload)
        await nc.flush()
        await nc.close()
        return True
    except Exception as e:
        print(f"NATS publish error: {e}", file=sys.stderr)
        return False


async def run_once(test_degraded: bool = False) -> dict:
    """Run a single review cycle."""
    print("=" * 70)
    print("  SKYBEAM Script Reviewer Service (STORY-012)")
    print("=" * 70)

    # Load scripts
    print("\n[1] Loading scripts...")
    scripts_data, error = load_json_file(SCRIPTS_FILE)
    if error:
        print(f"  Warning: {error}")
    else:
        print(f"  Loaded: {scripts_data.get('script_id')} ({scripts_data.get('meta', {}).get('script_count')} scripts)")

    # Generate review
    print("[2] Reviewing scripts...")
    review = generate_review(scripts_data, test_degraded=test_degraded)
    print(f"  Review ID: {review['review_id']}")
    print(f"  Status: {review['status']}")

    # Validate
    print("[3] Validating schema...")
    valid, error = validate_schema(review)
    if not valid:
        print(f"  FAIL: {error}")
        return review
    print(f"  Schema: VALID")

    # Write
    print("[4] Writing output...")
    write_review(review)
    print(f"  File written: {OUTPUT_FILE}")

    # Publish
    print("[5] Publishing to NATS...")
    nats_ok = await publish_to_nats(review)
    print(f"  NATS published: {nats_ok}")

    # Summary
    summary = review.get("summary", {})
    print("=" * 70)
    print("  PROOF ARTIFACTS:")
    print(f"  - File: {OUTPUT_FILE}")
    print(f"  - Review ID: {review['review_id']}")
    print(f"  - Status: {review['status']}")
    print(f"  - Total: {summary.get('total_reviewed')}")
    print(f"  - Approved: {summary.get('approved')}")
    print(f"  - Needs Revision: {summary.get('needs_revision')}")
    print(f"  - Rejected: {summary.get('rejected')}")
    print(f"  - Avg Score: {summary.get('average_score')}")
    print(f"  - NATS: {nats_ok}")
    print("=" * 70)

    return review


def main():
    parser = argparse.ArgumentParser(description="SKYBEAM Script Reviewer Service")
    parser.add_argument("--test-degraded", action="store_true", help="Test degraded mode")
    args = parser.parse_args()

    asyncio.run(run_once(test_degraded=args.test_degraded))


if __name__ == "__main__":
    main()
