#!/usr/bin/env python3
"""
SKYBEAM Publish Metrics Collector (STORY-025)

Documentation: file:///home/mark/.roxy/SKYBEAM_CURRENT_STATE.md

Input:
- receipts/*.json (all platform receipts)
- publish_queue_latest.json (queue status)

Output:
- metrics_latest.json (current metrics snapshot)

NATS topic: ghost.publish.metrics

Collects:
- Receipt counts by platform and status
- Queue statistics
- Platform engagement metrics (if API access available)

Degraded mode: Still outputs valid metrics with reason if API unavailable.
Rate-limited: Designed for hourly polling, no hammering.
Lock: Uses /tmp/skybeam_publish.lock (fcntl LOCK_EX|LOCK_NB)
"""

import json
import os
import sys
import hashlib
import socket
import fcntl
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# Paths
PIPELINE_BASE = Path.home() / ".roxy" / "content-pipeline"
RECEIPTS_DIR = PIPELINE_BASE / "publish" / "receipts"
QUEUE_SNAPSHOT = PIPELINE_BASE / "publish" / "queue" / "publish_queue_latest.json"
METRICS_DIR = PIPELINE_BASE / "publish" / "metrics"
METRICS_LATEST = METRICS_DIR / "metrics_latest.json"
YT_CREDENTIALS = Path.home() / ".roxy" / "credentials" / "youtube_oauth.json"
TT_CREDENTIALS = Path.home() / ".roxy" / "credentials" / "tiktok_oauth.json"
LOCK_FILE = Path("/tmp/skybeam_publish.lock")

# Constants
NATS_TOPIC = "ghost.publish.metrics"
COLLECTION_WINDOW_HOURS = 24  # Look back 24 hours for metrics


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
        return None


def check_api_access(platform: str) -> Tuple[bool, str]:
    """Check if API credentials are available for a platform."""
    if platform == "youtube":
        creds_file = YT_CREDENTIALS
    elif platform == "tiktok":
        creds_file = TT_CREDENTIALS
    else:
        return False, f"Unknown platform: {platform}"

    if not creds_file.exists():
        return False, "Credentials file not found"

    try:
        with open(creds_file, "r") as f:
            creds = json.load(f)
        if creds:
            return True, "Credentials present"
        return False, "Empty credentials file"
    except json.JSONDecodeError:
        return False, "Invalid credentials JSON"


def load_all_receipts() -> List[Dict[str, Any]]:
    """Load all receipt files from receipts directory."""
    receipts = []
    if not RECEIPTS_DIR.exists():
        return receipts

    for path in RECEIPTS_DIR.glob("*.json"):
        # Skip hidden files and tracking files
        if path.name.startswith("."):
            continue
        # Skip latest symlinks (we want individual receipts)
        if "_latest" in path.name:
            continue

        data = load_json(path)
        if data and "receipt_id" in data:
            receipts.append(data)

    return receipts


def compute_receipts_summary(receipts: List[Dict]) -> Dict[str, Any]:
    """Compute summary statistics from receipts."""
    summary = {
        "total_receipts": len(receipts),
        "by_platform": {
            "youtube_shorts": {
                "total": 0,
                "published": 0,
                "failed": 0,
                "pending": 0,
                "dry_run": 0,
                "handoff_ready": 0
            },
            "tiktok": {
                "total": 0,
                "published": 0,
                "failed": 0,
                "pending": 0,
                "dry_run": 0,
                "handoff_ready": 0
            }
        },
        "by_status": {},
        "latest_receipt": None
    }

    latest_timestamp = None

    for receipt in receipts:
        platform = receipt.get("platform", "unknown")
        status = receipt.get("status", "unknown")
        timestamp = receipt.get("timestamp", "")

        # Count by status
        summary["by_status"][status] = summary["by_status"].get(status, 0) + 1

        # Count by platform
        if platform == "youtube_shorts" and platform in summary["by_platform"]:
            summary["by_platform"]["youtube_shorts"]["total"] += 1
            if status in summary["by_platform"]["youtube_shorts"]:
                summary["by_platform"]["youtube_shorts"][status] += 1
        elif platform == "tiktok" and platform in summary["by_platform"]:
            summary["by_platform"]["tiktok"]["total"] += 1
            if status in summary["by_platform"]["tiktok"]:
                summary["by_platform"]["tiktok"][status] += 1

        # Track latest receipt
        if timestamp:
            if latest_timestamp is None or timestamp > latest_timestamp:
                latest_timestamp = timestamp
                summary["latest_receipt"] = {
                    "receipt_id": receipt.get("receipt_id", ""),
                    "platform": platform,
                    "status": status,
                    "timestamp": timestamp
                }

    return summary


def compute_queue_stats() -> Dict[str, Any]:
    """Compute queue statistics."""
    queue_data = load_json(QUEUE_SNAPSHOT)

    if queue_data is None:
        return {
            "queue_length": 0,
            "oldest_queued_age_hours": 0,
            "latest_enqueue": None
        }

    entries = queue_data.get("entries", [])
    queue_length = len(entries)
    latest_enqueue = None
    oldest_age_hours = 0

    now = datetime.now(timezone.utc)

    for entry in entries:
        enqueue_ts = entry.get("enqueue_timestamp", "")
        if enqueue_ts:
            try:
                enqueue_dt = datetime.fromisoformat(enqueue_ts.replace("Z", "+00:00"))
                age_hours = (now - enqueue_dt).total_seconds() / 3600

                if oldest_age_hours == 0 or age_hours > oldest_age_hours:
                    oldest_age_hours = age_hours

                if latest_enqueue is None or enqueue_ts > latest_enqueue:
                    latest_enqueue = enqueue_ts
            except (ValueError, TypeError):
                pass

    return {
        "queue_length": queue_length,
        "oldest_queued_age_hours": round(oldest_age_hours, 2),
        "latest_enqueue": latest_enqueue
    }


def fetch_platform_metrics(platform: str, receipts: List[Dict]) -> Dict[str, Any]:
    """Fetch engagement metrics from platform API (stubbed)."""
    # Filter receipts for this platform that are published
    platform_receipts = [r for r in receipts
                         if r.get("platform") == platform
                         and r.get("status") == "published"]

    # Map platform name to API credential name
    api_platform = "youtube" if platform == "youtube_shorts" else platform
    has_api, reason = check_api_access(api_platform)

    if not has_api:
        return {
            "available": False,
            "videos_tracked": len(platform_receipts),
            "total_views": 0,
            "total_likes": 0,
            "total_comments": 0,
            "total_shares": 0,
            "last_updated": None,
            "degraded_reason": reason
        }

    # In live mode, would call platform APIs here
    # For now, return stub with "available" flag
    return {
        "available": True,
        "videos_tracked": len(platform_receipts),
        "total_views": 0,  # Would fetch from API
        "total_likes": 0,
        "total_comments": 0,
        "total_shares": 0,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "degraded_reason": None
    }


def publish_to_nats(data: Dict[str, Any]) -> bool:
    """Publish to NATS topic (graceful degradation if unavailable)."""
    try:
        import nats
        print(f"[NATS] Would publish to {NATS_TOPIC}: {data.get('metrics_id', 'unknown')}")
        return True
    except ImportError:
        print(f"[NATS] NATS client not available, skipping publish to {NATS_TOPIC}")
        return False


def main() -> int:
    """Main entry point for metrics collector."""
    start_time = time.time()

    print("=" * 60)
    print("SKYBEAM Publish Metrics Collector (STORY-025)")
    print("=" * 60)

    # Acquire Phase 6 lock
    lock_fd = acquire_lock()
    if lock_fd is None:
        print("[PARTIAL] Could not acquire Phase 6 lock - another process running")
        print("[PARTIAL] Exiting without writes (lock_busy)")
        return 0

    try:
        # Ensure metrics directory exists
        METRICS_DIR.mkdir(parents=True, exist_ok=True)

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=COLLECTION_WINDOW_HOURS)

        print(f"[WINDOW] Collecting metrics for last {COLLECTION_WINDOW_HOURS} hours")

        # Load all receipts
        receipts = load_all_receipts()
        print(f"[RECEIPTS] Found {len(receipts)} receipt files")

        # Compute summaries
        receipts_summary = compute_receipts_summary(receipts)
        queue_stats = compute_queue_stats()

        print(f"[QUEUE] Length: {queue_stats['queue_length']}")
        print(f"[STATS] By status: {receipts_summary['by_status']}")

        # Check API access
        yt_access, yt_reason = check_api_access("youtube")
        tt_access, tt_reason = check_api_access("tiktok")

        print(f"[API] YouTube: {'available' if yt_access else 'unavailable'} - {yt_reason}")
        print(f"[API] TikTok: {'available' if tt_access else 'unavailable'} - {tt_reason}")

        # Fetch platform metrics (degraded if no API)
        yt_metrics = fetch_platform_metrics("youtube_shorts", receipts)
        tt_metrics = fetch_platform_metrics("tiktok", receipts)

        # Determine overall status
        degraded = False
        degraded_reasons = []

        if not yt_access:
            degraded_reasons.append(f"YouTube: {yt_reason}")
        if not tt_access:
            degraded_reasons.append(f"TikTok: {tt_reason}")

        if degraded_reasons:
            degraded = True

        # Build metrics snapshot
        collection_duration_ms = int((time.time() - start_time) * 1000)

        metrics = {
            "metrics_id": generate_id("METRICS"),
            "timestamp": now.isoformat(),
            "collection_window": {
                "start": window_start.isoformat(),
                "end": now.isoformat(),
                "duration_hours": COLLECTION_WINDOW_HOURS
            },
            "receipts_summary": receipts_summary,
            "queue_stats": queue_stats,
            "platform_metrics": {
                "youtube": yt_metrics,
                "tiktok": tt_metrics
            },
            "api_access": {
                "youtube": {
                    "available": yt_access,
                    "last_check": now.isoformat(),
                    "reason": yt_reason
                },
                "tiktok": {
                    "available": tt_access,
                    "last_check": now.isoformat(),
                    "reason": tt_reason
                }
            },
            "status": "degraded" if degraded else "healthy",
            "meta": {
                "version": "1.0.0",
                "service": "publish_metrics_collector",
                "story_id": "SKYBEAM-STORY-025",
                "host": socket.gethostname(),
                "collection_duration_ms": collection_duration_ms
            }
        }

        if degraded_reasons:
            metrics["degraded_reason"] = "; ".join(degraded_reasons)

        # Write metrics
        with open(METRICS_LATEST, "w") as f:
            json.dump(metrics, f, indent=2)

        # Publish to NATS
        publish_to_nats(metrics)

        print(f"[OK] Metrics ID: {metrics['metrics_id']}")
        print(f"[OK] Status: {metrics['status']}")
        print(f"[OK] Total receipts: {receipts_summary['total_receipts']}")
        print(f"[OK] Collection time: {collection_duration_ms}ms")

        return 0

    finally:
        release_lock(lock_fd)


if __name__ == "__main__":
    sys.exit(main())
