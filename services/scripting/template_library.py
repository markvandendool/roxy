#!/usr/bin/env python3
"""
SKYBEAM Template Library Service (STORY-011)
=============================================

Manages the script template library for content generation.

Input:  templates/templates.json
Output: ~/.roxy/content-pipeline/scripts/templates_latest.json
NATS:   ghost.script.templates

Usage:
    python3 template_library.py              # Normal run
    python3 template_library.py --test-degraded  # Test degraded mode
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
TEMPLATES_FILE = SCRIPT_DIR / "templates/templates.json"
OUTPUT_DIR = Path.home() / ".roxy/content-pipeline/scripts"
OUTPUT_FILE = OUTPUT_DIR / "templates_latest.json"
SCHEMA_FILE = SCRIPT_DIR / "schemas/template_library.json"

# NATS config
NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")
NATS_TOPIC = "ghost.script.templates"


def load_templates(path: Path) -> tuple[Optional[list], Optional[str]]:
    """Load templates from file."""
    if not path.exists():
        return None, f"Templates file not found: {path}"
    try:
        with open(path) as f:
            data = json.load(f)
        return data.get("templates", []), None
    except Exception as e:
        return None, f"Failed to load templates: {e}"


def validate_template(template: dict) -> tuple[bool, Optional[str]]:
    """Validate a single template has required fields."""
    required = ["id", "name", "category", "format", "duration_range", "structure", "variables"]
    for field in required:
        if field not in template:
            return False, f"Template missing field: {field}"

    # Validate structure percentages sum to 100
    structure = template.get("structure", [])
    total_pct = sum(s.get("duration_pct", 0) for s in structure)
    if abs(total_pct - 100) > 1:  # Allow 1% tolerance
        return False, f"Template {template['id']} structure percentages sum to {total_pct}, not 100"

    return True, None


def generate_library(
    templates: Optional[list],
    test_degraded: bool = False
) -> dict:
    """Generate the template library output."""
    timestamp = datetime.now(timezone.utc).isoformat()
    short_id = uuid.uuid4().hex[:8]
    library_id = f"TMPL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{short_id}"

    # Degraded mode
    if test_degraded or templates is None:
        return {
            "library_id": library_id,
            "timestamp": timestamp,
            "status": "degraded",
            "templates": [],
            "meta": {
                "version": "1.0.0",
                "service": "template_library",
                "story_id": "SKYBEAM-STORY-011",
                "template_count": 0,
                "degraded": True
            }
        }

    # Validate templates
    valid_templates = []
    invalid_count = 0
    for template in templates:
        valid, error = validate_template(template)
        if valid:
            valid_templates.append(template)
        else:
            print(f"  Warning: {error}")
            invalid_count += 1

    # Determine status
    if not valid_templates:
        status = "degraded"
    elif invalid_count > 0:
        status = "partial"
    else:
        status = "healthy"

    return {
        "library_id": library_id,
        "timestamp": timestamp,
        "status": status,
        "templates": valid_templates,
        "meta": {
            "version": "1.0.0",
            "service": "template_library",
            "story_id": "SKYBEAM-STORY-011",
            "template_count": len(valid_templates),
            "categories": list(set(t.get("category") for t in valid_templates)),
            "formats": list(set(t.get("format") for t in valid_templates)),
            "degraded": status == "degraded"
        }
    }


def validate_schema(data: dict) -> tuple[bool, Optional[str]]:
    """Validate library against schema (basic validation)."""
    required = ["library_id", "timestamp", "status", "templates", "meta"]
    for field in required:
        if field not in data:
            return False, f"Missing required field: {field}"

    if data["status"] not in ["healthy", "partial", "degraded"]:
        return False, f"Invalid status: {data['status']}"

    if not isinstance(data["templates"], list):
        return False, "templates must be a list"

    meta_required = ["version", "service", "story_id", "template_count"]
    for field in meta_required:
        if field not in data.get("meta", {}):
            return False, f"Missing meta field: {field}"

    return True, None


def write_library(library: dict) -> None:
    """Write library to output file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(library, f, indent=2)


async def publish_to_nats(library: dict) -> bool:
    """Publish library to NATS."""
    try:
        import nats
        nc = await nats.connect(NATS_URL)
        payload = json.dumps(library).encode()
        await nc.publish(NATS_TOPIC, payload)
        await nc.flush()
        await nc.close()
        return True
    except Exception as e:
        print(f"NATS publish error: {e}", file=sys.stderr)
        return False


async def run_once(test_degraded: bool = False) -> dict:
    """Run a single library generation cycle."""
    print("=" * 70)
    print("  SKYBEAM Template Library Service (STORY-011)")
    print("=" * 70)

    # Load templates
    print("\n[1] Loading templates...")
    templates, error = load_templates(TEMPLATES_FILE)
    if error:
        print(f"  Warning: {error}")
    else:
        print(f"  Loaded: {len(templates)} templates")

    # Generate library
    print("[2] Generating library...")
    library = generate_library(templates, test_degraded=test_degraded)
    print(f"  Library ID: {library['library_id']}")
    print(f"  Status: {library['status']}")
    print(f"  Templates: {library['meta']['template_count']}")

    # Validate
    print("[3] Validating schema...")
    valid, error = validate_schema(library)
    if not valid:
        print(f"  FAIL: {error}")
        return library
    print(f"  Schema: VALID")

    # Write
    print("[4] Writing output...")
    write_library(library)
    print(f"  File written: {OUTPUT_FILE}")

    # Publish
    print("[5] Publishing to NATS...")
    nats_ok = await publish_to_nats(library)
    print(f"  NATS published: {nats_ok}")

    # Summary
    print("=" * 70)
    print("  PROOF ARTIFACTS:")
    print(f"  - File: {OUTPUT_FILE}")
    print(f"  - Library: {library['library_id']}")
    print(f"  - Status: {library['status']}")
    print(f"  - Templates: {library['meta']['template_count']}")
    if library['meta'].get('categories'):
        print(f"  - Categories: {', '.join(library['meta']['categories'])}")
    if library['meta'].get('formats'):
        print(f"  - Formats: {', '.join(library['meta']['formats'])}")
    print(f"  - NATS: {nats_ok}")
    print("=" * 70)

    return library


def main():
    parser = argparse.ArgumentParser(description="SKYBEAM Template Library Service")
    parser.add_argument("--test-degraded", action="store_true", help="Test degraded mode")
    args = parser.parse_args()

    asyncio.run(run_once(test_degraded=args.test_degraded))


if __name__ == "__main__":
    main()
