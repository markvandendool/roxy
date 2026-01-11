#!/usr/bin/env python3
"""
SKYBEAM Manual Seed Ingestor (STORY-031b)

Scans ~/.roxy/content-pipeline/seeds/manual/ for injected seeds,
validates schema, merges into seeds_merged_latest.json, and marks processed.

Input:
  ~/.roxy/content-pipeline/seeds/manual/inject_SEED_*.json

Output:
  ~/.roxy/content-pipeline/seeds/seeds_merged_latest.json
  ~/.roxy/content-pipeline/seeds/manual/processed/ (moved files)

Timer: :02 (every hour at minute 02)
"""

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import hashlib

# Paths
SEEDS_DIR = Path.home() / ".roxy" / "content-pipeline" / "seeds"
MANUAL_DIR = SEEDS_DIR / "manual"
PROCESSED_DIR = MANUAL_DIR / "processed"
MERGED_OUTPUT = SEEDS_DIR / "seeds_merged_latest.json"
INGEST_RECEIPT = SEEDS_DIR / ".ingest_receipt.json"

# Schema validation
REQUIRED_FIELDS = ["seed_id", "created", "type", "url"]


def validate_seed(seed: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate seed schema. Returns (is_valid, error_message)."""
    for field in REQUIRED_FIELDS:
        if field not in seed:
            return False, f"Missing required field: {field}"

    seed_id = seed.get("seed_id", "")
    if not seed_id.startswith("SEED_"):
        return False, f"Invalid seed_id format: {seed_id}"

    url = seed.get("url", "")
    if not url.startswith("http"):
        return False, f"Invalid URL: {url}"

    return True, ""


def load_json(path: Path) -> Optional[Dict[str, Any]]:
    """Load JSON file, return None if missing or invalid."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_json(path: Path, data: Dict[str, Any]) -> None:
    """Save JSON to file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def generate_ingest_id() -> str:
    """Generate a timestamped ingest ID."""
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d_%H%M%S")
    h = hashlib.sha256(f"{ts}{now.microsecond}".encode()).hexdigest()[:8]
    return f"INGEST_{ts}_{h}"


def scan_manual_seeds() -> List[Tuple[Path, Dict[str, Any]]]:
    """Scan manual directory for unprocessed seeds."""
    seeds = []
    if not MANUAL_DIR.exists():
        return seeds

    for path in MANUAL_DIR.glob("inject_SEED_*.json"):
        data = load_json(path)
        if data:
            seeds.append((path, data))

    # Sort by priority (high > normal > low) then by created time
    priority_order = {"high": 0, "normal": 1, "low": 2}
    seeds.sort(key=lambda x: (
        priority_order.get(x[1].get("priority", "normal"), 1),
        x[1].get("created", "")
    ))

    return seeds


def load_existing_merged() -> Dict[str, Any]:
    """Load existing merged seeds file or create empty structure."""
    existing = load_json(MERGED_OUTPUT)
    if existing:
        return existing
    return {
        "merged_id": generate_ingest_id(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seeds": [],
        "known_ids": [],
        "meta": {
            "version": "1.0.0",
            "service": "manual_seed_ingestor",
            "story_id": "SKYBEAM-STORY-031b"
        }
    }


def run_ingest() -> int:
    """Run the ingestion process."""
    print("=" * 60)
    print("SKYBEAM Manual Seed Ingestor (STORY-031b)")
    print("=" * 60)

    # Ensure directories exist
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Scan for new seeds
    manual_seeds = scan_manual_seeds()
    print(f"Found {len(manual_seeds)} manual seed(s) to process")

    if not manual_seeds:
        print("No new seeds to ingest")
        # Update receipt even with no work
        receipt = {
            "ingest_id": generate_ingest_id(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "seeds_processed": 0,
            "seeds_valid": 0,
            "seeds_invalid": 0,
            "status": "no_work"
        }
        save_json(INGEST_RECEIPT, receipt)
        return 0

    # Load existing merged data
    merged = load_existing_merged()
    known_ids = set(merged.get("known_ids", []))

    valid_count = 0
    invalid_count = 0
    skipped_count = 0

    for path, seed in manual_seeds:
        seed_id = seed.get("seed_id", "unknown")

        # Check if already processed
        if seed_id in known_ids:
            print(f"  [SKIP] {seed_id} (already merged)")
            skipped_count += 1
            # Move to processed anyway
            dest = PROCESSED_DIR / path.name
            shutil.move(str(path), str(dest))
            continue

        # Validate
        is_valid, error = validate_seed(seed)
        if not is_valid:
            print(f"  [FAIL] {seed_id}: {error}")
            invalid_count += 1
            # Move to processed with error marker
            seed["_ingest_error"] = error
            dest = PROCESSED_DIR / f"invalid_{path.name}"
            save_json(dest, seed)
            os.unlink(path)
            continue

        # Add to merged
        seed["_ingested_at"] = datetime.now(timezone.utc).isoformat()
        merged["seeds"].append(seed)
        known_ids.add(seed_id)
        valid_count += 1
        print(f"  [OK] {seed_id} ({seed.get('priority', 'normal')} priority)")

        # Move to processed
        dest = PROCESSED_DIR / path.name
        shutil.move(str(path), str(dest))

    # Update merged output
    merged["merged_id"] = generate_ingest_id()
    merged["timestamp"] = datetime.now(timezone.utc).isoformat()
    merged["known_ids"] = list(known_ids)
    merged["meta"]["last_ingest"] = datetime.now(timezone.utc).isoformat()
    merged["meta"]["seed_count"] = len(merged["seeds"])

    save_json(MERGED_OUTPUT, merged)

    # Write receipt
    receipt = {
        "ingest_id": merged["merged_id"],
        "timestamp": merged["timestamp"],
        "seeds_processed": valid_count + invalid_count + skipped_count,
        "seeds_valid": valid_count,
        "seeds_invalid": invalid_count,
        "seeds_skipped": skipped_count,
        "total_merged": len(merged["seeds"]),
        "status": "complete",
        "output_file": str(MERGED_OUTPUT)
    }
    save_json(INGEST_RECEIPT, receipt)

    print()
    print(f"Ingested: {valid_count} valid, {invalid_count} invalid, {skipped_count} skipped")
    print(f"Total merged seeds: {len(merged['seeds'])}")
    print(f"Output: {MERGED_OUTPUT}")
    print("=" * 60)

    return 0


def main():
    return run_ingest()


if __name__ == "__main__":
    sys.exit(main())
