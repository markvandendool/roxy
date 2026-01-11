#!/usr/bin/env python3
"""
SKYBEAM Publish Queue Builder (STORY-021)

Documentation: file:///home/mark/.roxy/SKYBEAM_CURRENT_STATE.md

Input:
- production_qa_latest.json (must be approved)
- master_latest.json (must exist)

Output:
- publish_queue.jsonl (append-only, only if new master hash not seen)
- publish_queue_latest.json (materialized snapshot)

NATS topic: ghost.publish.queue

Idempotency: Uses master_sha256 as dedup key. Re-runs with same hash do NOT enqueue.
Degraded mode: If QA gate not approved, status=degraded, no enqueue.
Lock: Uses /tmp/skybeam_publish.lock (fcntl LOCK_EX|LOCK_NB). If busy, status=partial, exit 0.
"""

import json
import os
import sys
import hashlib
import socket
import fcntl
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# Paths
PIPELINE_BASE = Path.home() / ".roxy" / "content-pipeline"
PRODUCTION_QA = PIPELINE_BASE / "production" / "qa" / "production_qa_latest.json"
MASTER_MANIFEST = PIPELINE_BASE / "production" / "master" / "master_latest.json"
QUEUE_DIR = PIPELINE_BASE / "publish" / "queue"
QUEUE_JSONL = QUEUE_DIR / "publish_queue.jsonl"
QUEUE_SNAPSHOT = QUEUE_DIR / "publish_queue_latest.json"
LOCK_FILE = Path("/tmp/skybeam_publish.lock")

# Constants
NATS_TOPIC = "ghost.publish.queue"
DEFAULT_PLATFORMS = ["youtube_shorts", "tiktok"]


def acquire_lock() -> Optional[int]:
    """Acquire exclusive lock for Phase 6 operations."""
    try:
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except (OSError, IOError):
        return None


def release_lock(fd: int) -> None:
    """Release the Phase 6 lock."""
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    except (OSError, IOError):
        pass


def generate_id(prefix: str) -> str:
    """Generate a timestamped unique ID."""
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d_%H%M%S")
    h = hashlib.sha256(f"{ts}{os.getpid()}{now.microsecond}".encode()).hexdigest()[:8]
    return f"{prefix}_{ts}_{h}"


def load_json(path: Path) -> Optional[Dict[str, Any]]:
    """Load JSON file, return None if missing or invalid."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[WARN] Cannot load {path}: {e}")
        return None


def load_known_hashes() -> set:
    """Load all master_sha256 values from existing queue."""
    hashes = set()
    if QUEUE_JSONL.exists():
        with open(QUEUE_JSONL, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        if "master_sha256" in entry:
                            hashes.add(entry["master_sha256"])
                    except json.JSONDecodeError:
                        continue
    return hashes


def load_all_entries() -> List[Dict[str, Any]]:
    """Load all entries from queue JSONL."""
    entries = []
    if QUEUE_JSONL.exists():
        with open(QUEUE_JSONL, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return entries


def check_qa_gate(qa_data: Dict[str, Any]) -> Tuple[bool, str]:
    """Check if QA gate is approved."""
    gate_result = qa_data.get("gate_result", "")
    if gate_result == "approved":
        return True, "QA gate approved"
    return False, f"QA gate not approved: {gate_result}"


def build_queue_entry(master_data: Dict[str, Any], qa_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build a new queue entry from master manifest."""
    file_proof = master_data.get("file_proof", {})

    return {
        "publish_id": generate_id("PUB"),
        "enqueue_timestamp": datetime.now(timezone.utc).isoformat(),
        "master_id": master_data.get("master_id", ""),
        "master_sha256": file_proof.get("sha256", ""),
        "master_path": file_proof.get("path", ""),
        "source_qa_id": qa_data.get("qa_id", ""),
        "script_id": master_data.get("script_id", ""),
        "title": master_data.get("title", ""),
        "status": "queued",
        "platforms": DEFAULT_PLATFORMS,
        "meta": {
            "version": "1.0.0",
            "service": "publish_queue_builder",
            "story_id": "SKYBEAM-STORY-021",
            "host": socket.gethostname()
        }
    }


def write_snapshot(entries: List[Dict[str, Any]], status: str, degraded_reason: str = "") -> Dict[str, Any]:
    """Write queue snapshot to latest.json."""
    known_hashes = list(set(e.get("master_sha256", "") for e in entries if e.get("master_sha256")))

    snapshot = {
        "snapshot_id": generate_id("QUEUE"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "queue_length": len(entries),
        "known_hashes": known_hashes,
        "entries": entries,
        "latest_entry": entries[-1] if entries else None,
        "status": status,
        "meta": {
            "version": "1.0.0",
            "service": "publish_queue_builder",
            "story_id": "SKYBEAM-STORY-021",
            "host": socket.gethostname(),
            "last_run": datetime.now(timezone.utc).isoformat()
        }
    }

    if degraded_reason:
        snapshot["degraded_reason"] = degraded_reason

    with open(QUEUE_SNAPSHOT, "w") as f:
        json.dump(snapshot, f, indent=2)

    return snapshot


def publish_to_nats(data: Dict[str, Any]) -> bool:
    """Publish to NATS topic (graceful degradation if unavailable)."""
    try:
        import nats
        # Would use async NATS client here
        # For now, just log intention
        print(f"[NATS] Would publish to {NATS_TOPIC}: {data.get('snapshot_id', 'unknown')}")
        return True
    except ImportError:
        print(f"[NATS] NATS client not available, skipping publish to {NATS_TOPIC}")
        return False


def main() -> int:
    """Main entry point for publish queue builder."""
    print("=" * 60)
    print("SKYBEAM Publish Queue Builder (STORY-021)")
    print("=" * 60)

    # Acquire Phase 6 lock
    lock_fd = acquire_lock()
    if lock_fd is None:
        print("[PARTIAL] Could not acquire Phase 6 lock - another process running")
        print("[PARTIAL] Exiting without writes (lock_busy)")
        # Write partial status snapshot if possible
        try:
            entries = load_all_entries()
            write_snapshot(entries, "partial", "lock_busy")
        except Exception:
            pass
        return 0

    try:
        # Ensure queue directory exists
        QUEUE_DIR.mkdir(parents=True, exist_ok=True)

        # Load QA gate status
        qa_data = load_json(PRODUCTION_QA)
        if qa_data is None:
            print("[DEGRADED] No QA data available")
            entries = load_all_entries()
            write_snapshot(entries, "degraded", "QA data not found")
            return 0

        # Check QA gate
        gate_ok, gate_msg = check_qa_gate(qa_data)
        print(f"[QA] {gate_msg}")

        if not gate_ok:
            print("[DEGRADED] QA gate not approved - no enqueue")
            entries = load_all_entries()
            write_snapshot(entries, "degraded", gate_msg)
            return 0

        # Load master manifest
        master_data = load_json(MASTER_MANIFEST)
        if master_data is None:
            print("[DEGRADED] No master manifest available")
            entries = load_all_entries()
            write_snapshot(entries, "degraded", "Master manifest not found")
            return 0

        # Get master SHA256 for idempotency check
        file_proof = master_data.get("file_proof", {})
        master_sha256 = file_proof.get("sha256", "")

        if not master_sha256:
            print("[DEGRADED] Master manifest missing sha256")
            entries = load_all_entries()
            write_snapshot(entries, "degraded", "Master sha256 missing")
            return 0

        # Load known hashes for idempotency
        known_hashes = load_known_hashes()
        print(f"[IDEM] Known hashes in queue: {len(known_hashes)}")
        print(f"[IDEM] Current master sha256: {master_sha256[:16]}...")

        # Check idempotency
        if master_sha256 in known_hashes:
            print("[IDEM] Master already in queue - SKIP (idempotent)")
            entries = load_all_entries()
            snapshot = write_snapshot(entries, "healthy")
            publish_to_nats(snapshot)
            print(f"[OK] Queue unchanged. Length: {len(entries)}")
            return 0

        # Build new entry
        new_entry = build_queue_entry(master_data, qa_data)
        print(f"[NEW] Creating queue entry: {new_entry['publish_id']}")

        # Append to JSONL (atomic append)
        with open(QUEUE_JSONL, "a") as f:
            f.write(json.dumps(new_entry) + "\n")

        # Reload and write snapshot
        entries = load_all_entries()
        snapshot = write_snapshot(entries, "healthy")

        # Publish to NATS
        publish_to_nats(snapshot)

        print(f"[OK] Enqueued. Queue length: {len(entries)}")
        print(f"[OK] Publish ID: {new_entry['publish_id']}")
        print(f"[OK] Master: {new_entry['master_id']}")

        return 0

    finally:
        release_lock(lock_fd)


if __name__ == "__main__":
    sys.exit(main())
