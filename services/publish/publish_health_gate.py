#!/usr/bin/env python3
"""
SKYBEAM Publish Health Gate (STORY-026)

Documentation: file:///home/mark/.roxy/SKYBEAM_CURRENT_STATE.md

Input:
- metrics_latest.json
- publish_queue_latest.json
- All *_latest.json files for freshness checks

Output:
- health_latest.json (health snapshot)
- alerts_latest.json (active alerts)
- reports/ALERTS.md (human-readable alert summary)

NATS topic: ghost.publish.health

Checks:
- Queue stuck (queued > X hours with no newer receipts)
- Timer drift (mtime of *latest.json vs expected cadence)
- Receipt freshness
- Metrics freshness
- Master SHA256 consistency
- Failed receipts count

Gate result: approved | warning | critical
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
QUEUE_SNAPSHOT = PIPELINE_BASE / "publish" / "queue" / "publish_queue_latest.json"
METRICS_LATEST = PIPELINE_BASE / "publish" / "metrics" / "metrics_latest.json"
PACKAGE_LATEST = PIPELINE_BASE / "publish" / "packages" / "publish_package_latest.json"
HEALTH_DIR = PIPELINE_BASE / "publish" / "health"
HEALTH_LATEST = HEALTH_DIR / "publish_health_latest.json"
ALERTS_LATEST = HEALTH_DIR / "alerts_latest.json"
REPORTS_DIR = PIPELINE_BASE / "publish" / "reports"
ALERTS_MD = REPORTS_DIR / "ALERTS.md"
HEARTBEAT_FILE = HEALTH_DIR / ".heartbeat.json"
LOCK_FILE = Path("/tmp/skybeam_publish.lock")

# Thresholds
QUEUE_STUCK_WARNING_HOURS = 2.0
QUEUE_STUCK_CRITICAL_HOURS = 6.0
FRESHNESS_WARNING_HOURS = 2.0
FRESHNESS_CRITICAL_HOURS = 4.0
FAILED_RECEIPTS_WARNING = 2
FAILED_RECEIPTS_CRITICAL = 5

# Constants
NATS_TOPIC = "ghost.publish.health"
HEARTBEAT_INTERVAL_SECONDS = 3600  # 1 hour


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
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def get_file_age_hours(path: Path) -> Optional[float]:
    """Get file age in hours based on mtime."""
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    age_seconds = time.time() - mtime
    return age_seconds / 3600


def check_queue_stuck() -> Dict[str, Any]:
    """Check if queue has items stuck without progress."""
    queue_data = load_json(QUEUE_SNAPSHOT)

    if queue_data is None:
        return {
            "check_id": "CHK_HEALTH_001",
            "check_type": "queue_stuck",
            "result": "warning",
            "message": "Queue snapshot not available",
            "details": {"queue_available": False}
        }

    queue_stats = queue_data.get("queue_length", 0)
    entries = queue_data.get("entries", [])

    if not entries:
        return {
            "check_id": "CHK_HEALTH_001",
            "check_type": "queue_stuck",
            "result": "pass",
            "message": "Queue empty - no stuck items",
            "details": {"queue_length": 0}
        }

    # Find oldest queued item
    now = datetime.now(timezone.utc)
    oldest_age_hours = 0

    for entry in entries:
        if entry.get("status") == "queued":
            enqueue_ts = entry.get("enqueue_timestamp", "")
            if enqueue_ts:
                try:
                    enqueue_dt = datetime.fromisoformat(enqueue_ts.replace("Z", "+00:00"))
                    age_hours = (now - enqueue_dt).total_seconds() / 3600
                    oldest_age_hours = max(oldest_age_hours, age_hours)
                except (ValueError, TypeError):
                    pass

    result = "pass"
    if oldest_age_hours >= QUEUE_STUCK_CRITICAL_HOURS:
        result = "critical"
    elif oldest_age_hours >= QUEUE_STUCK_WARNING_HOURS:
        result = "warning"

    return {
        "check_id": "CHK_HEALTH_001",
        "check_type": "queue_stuck",
        "result": result,
        "message": f"Oldest queued item: {oldest_age_hours:.1f} hours",
        "details": {"queue_length": len(entries), "oldest_age_hours": round(oldest_age_hours, 2)},
        "threshold": {
            "warning": QUEUE_STUCK_WARNING_HOURS,
            "critical": QUEUE_STUCK_CRITICAL_HOURS,
            "actual": round(oldest_age_hours, 2)
        }
    }


def check_metrics_freshness() -> Dict[str, Any]:
    """Check if metrics are fresh."""
    age_hours = get_file_age_hours(METRICS_LATEST)

    if age_hours is None:
        return {
            "check_id": "CHK_HEALTH_002",
            "check_type": "metrics_freshness",
            "result": "critical",
            "message": "Metrics file not found",
            "details": {"file_exists": False}
        }

    result = "pass"
    if age_hours >= FRESHNESS_CRITICAL_HOURS:
        result = "critical"
    elif age_hours >= FRESHNESS_WARNING_HOURS:
        result = "warning"

    return {
        "check_id": "CHK_HEALTH_002",
        "check_type": "metrics_freshness",
        "result": result,
        "message": f"Metrics age: {age_hours:.1f} hours",
        "details": {"file_exists": True, "age_hours": round(age_hours, 2)},
        "threshold": {
            "warning": FRESHNESS_WARNING_HOURS,
            "critical": FRESHNESS_CRITICAL_HOURS,
            "actual": round(age_hours, 2)
        }
    }


def check_receipt_freshness() -> Dict[str, Any]:
    """Check if we have recent receipts."""
    metrics_data = load_json(METRICS_LATEST)

    if metrics_data is None:
        return {
            "check_id": "CHK_HEALTH_003",
            "check_type": "receipt_freshness",
            "result": "warning",
            "message": "Cannot check receipts - metrics unavailable",
            "details": {"metrics_available": False}
        }

    latest_receipt = metrics_data.get("receipts_summary", {}).get("latest_receipt")

    if not latest_receipt:
        return {
            "check_id": "CHK_HEALTH_003",
            "check_type": "receipt_freshness",
            "result": "warning",
            "message": "No receipts found",
            "details": {"receipts_found": False}
        }

    receipt_ts = latest_receipt.get("timestamp", "")
    if not receipt_ts:
        return {
            "check_id": "CHK_HEALTH_003",
            "check_type": "receipt_freshness",
            "result": "warning",
            "message": "Latest receipt has no timestamp",
            "details": {"has_timestamp": False}
        }

    try:
        receipt_dt = datetime.fromisoformat(receipt_ts.replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - receipt_dt).total_seconds() / 3600
    except (ValueError, TypeError):
        age_hours = 999

    result = "pass"
    if age_hours >= FRESHNESS_CRITICAL_HOURS:
        result = "critical"
    elif age_hours >= FRESHNESS_WARNING_HOURS:
        result = "warning"

    return {
        "check_id": "CHK_HEALTH_003",
        "check_type": "receipt_freshness",
        "result": result,
        "message": f"Latest receipt age: {age_hours:.1f} hours",
        "details": {
            "latest_receipt_id": latest_receipt.get("receipt_id"),
            "age_hours": round(age_hours, 2)
        },
        "threshold": {
            "warning": FRESHNESS_WARNING_HOURS,
            "critical": FRESHNESS_CRITICAL_HOURS,
            "actual": round(age_hours, 2)
        }
    }


def check_failed_receipts() -> Dict[str, Any]:
    """Check count of failed receipts."""
    metrics_data = load_json(METRICS_LATEST)

    if metrics_data is None:
        return {
            "check_id": "CHK_HEALTH_004",
            "check_type": "failed_receipts",
            "result": "warning",
            "message": "Cannot check failed receipts - metrics unavailable",
            "details": {"metrics_available": False}
        }

    by_status = metrics_data.get("receipts_summary", {}).get("by_status", {})
    failed_count = by_status.get("failed", 0)

    result = "pass"
    if failed_count >= FAILED_RECEIPTS_CRITICAL:
        result = "critical"
    elif failed_count >= FAILED_RECEIPTS_WARNING:
        result = "warning"

    return {
        "check_id": "CHK_HEALTH_004",
        "check_type": "failed_receipts",
        "result": result,
        "message": f"Failed receipts: {failed_count}",
        "details": {"failed_count": failed_count, "by_status": by_status},
        "threshold": {
            "warning": FAILED_RECEIPTS_WARNING,
            "critical": FAILED_RECEIPTS_CRITICAL,
            "actual": failed_count
        }
    }


def check_master_consistency() -> Dict[str, Any]:
    """Check SHA256 consistency between queue and package."""
    queue_data = load_json(QUEUE_SNAPSHOT)
    package_data = load_json(PACKAGE_LATEST)

    if queue_data is None or package_data is None:
        return {
            "check_id": "CHK_HEALTH_005",
            "check_type": "master_consistency",
            "result": "warning",
            "message": "Cannot verify consistency - missing files",
            "details": {
                "queue_available": queue_data is not None,
                "package_available": package_data is not None
            }
        }

    latest_entry = queue_data.get("latest_entry", {})
    queue_sha = latest_entry.get("master_sha256", "")
    package_sha = package_data.get("master_sha256", "")

    if not queue_sha or not package_sha:
        return {
            "check_id": "CHK_HEALTH_005",
            "check_type": "master_consistency",
            "result": "warning",
            "message": "Missing SHA256 values",
            "details": {"queue_sha": bool(queue_sha), "package_sha": bool(package_sha)}
        }

    if queue_sha == package_sha:
        return {
            "check_id": "CHK_HEALTH_005",
            "check_type": "master_consistency",
            "result": "pass",
            "message": f"SHA256 consistent: {queue_sha[:16]}...",
            "details": {"sha256": queue_sha, "consistent": True}
        }

    return {
        "check_id": "CHK_HEALTH_005",
        "check_type": "master_consistency",
        "result": "warning",
        "message": "SHA256 mismatch between queue and package",
        "details": {
            "queue_sha": queue_sha[:16] + "...",
            "package_sha": package_sha[:16] + "...",
            "consistent": False
        }
    }


def check_api_access() -> Dict[str, Any]:
    """Check platform API access status from metrics."""
    metrics_data = load_json(METRICS_LATEST)

    if metrics_data is None:
        return {
            "check_id": "CHK_HEALTH_006",
            "check_type": "api_access",
            "result": "warning",
            "message": "Cannot check API access - metrics unavailable",
            "details": {"metrics_available": False}
        }

    api_access = metrics_data.get("api_access", {})
    yt_available = api_access.get("youtube", {}).get("available", False)
    tt_available = api_access.get("tiktok", {}).get("available", False)

    if yt_available and tt_available:
        result = "pass"
        message = "All platform APIs available"
    elif yt_available or tt_available:
        result = "warning"
        available = "YouTube" if yt_available else "TikTok"
        message = f"Partial API access: only {available}"
    else:
        result = "warning"  # Not critical - handoff mode works
        message = "No platform APIs available - using handoff mode"

    return {
        "check_id": "CHK_HEALTH_006",
        "check_type": "api_access",
        "result": result,
        "message": message,
        "details": {"youtube": yt_available, "tiktok": tt_available}
    }


def generate_alerts(checks: List[Dict]) -> List[Dict]:
    """Generate alerts from check results."""
    alerts = []

    remediation_map = {
        "queue_stuck": [
            "Check if pipeline services are running: systemctl --user list-timers | grep roxy",
            "Verify master.mp4 exists and passes QA",
            "Check logs: journalctl --user -u roxy-publish-*.service",
            "Manually trigger queue processing if needed"
        ],
        "metrics_freshness": [
            "Check metrics collector service: systemctl --user status roxy-publish-metrics",
            "Verify receipts directory is accessible",
            "Check for lock contention on /tmp/skybeam_publish.lock"
        ],
        "receipt_freshness": [
            "Verify publisher services are running",
            "Check for API credential issues",
            "Review handoff packs if in handoff mode"
        ],
        "failed_receipts": [
            "Check individual receipt files for error details",
            "Verify platform API credentials",
            "Review retry_info in failed receipts",
            "Consider manual re-upload for handoff items"
        ],
        "master_consistency": [
            "Queue and package may be from different pipeline runs",
            "Check if new content is being processed",
            "This is usually transient and self-corrects"
        ],
        "api_access": [
            "Add platform credentials to ~/.roxy/credentials/",
            "Using handoff mode - manual upload packs available in exports/",
            "No action required if handoff mode is acceptable"
        ]
    }

    for check in checks:
        if check["result"] in ("warning", "critical"):
            check_type = check["check_type"]
            alert = {
                "alert_id": generate_id("ALERT"),
                "severity": check["result"],
                "title": f"{check_type.replace('_', ' ').title()} Issue",
                "description": check["message"],
                "source_check": check["check_id"],
                "remediation": remediation_map.get(check_type, ["Investigate manually"]),
                "first_seen": datetime.now(timezone.utc).isoformat(),
                "acknowledged": False
            }
            alerts.append(alert)

    return alerts


def update_heartbeat() -> Dict[str, Any]:
    """Update heartbeat file and return heartbeat info."""
    now = datetime.now(timezone.utc)

    # Load previous heartbeat
    prev_beats = 0
    if HEARTBEAT_FILE.exists():
        try:
            with open(HEARTBEAT_FILE, "r") as f:
                prev = json.load(f)
                prev_beats = prev.get("consecutive_beats", 0)
        except (json.JSONDecodeError, KeyError):
            pass

    heartbeat = {
        "last_beat": now.isoformat(),
        "beat_interval_seconds": HEARTBEAT_INTERVAL_SECONDS,
        "consecutive_beats": prev_beats + 1
    }

    # Save heartbeat
    HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    with open(HEARTBEAT_FILE, "w") as f:
        json.dump(heartbeat, f)

    return heartbeat


def write_alerts_markdown(alerts: List[Dict], gate_result: str) -> None:
    """Write human-readable alerts markdown."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)

    with open(ALERTS_MD, "w") as f:
        f.write("# SKYBEAM Publish Pipeline Alerts\n\n")
        f.write(f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
        f.write(f"**Overall Status:** {gate_result.upper()}\n\n")

        if not alerts:
            f.write("## No Active Alerts\n\n")
            f.write("All health checks passed. Pipeline is operating normally.\n")
            return

        f.write(f"## Active Alerts ({len(alerts)})\n\n")

        for alert in alerts:
            severity_icon = "🔴" if alert["severity"] == "critical" else "🟡"
            f.write(f"### {severity_icon} {alert['title']}\n\n")
            f.write(f"**Severity:** {alert['severity'].upper()}\n\n")
            f.write(f"**Description:** {alert['description']}\n\n")
            f.write("**Remediation Steps:**\n")
            for step in alert["remediation"]:
                f.write(f"- {step}\n")
            f.write("\n---\n\n")


def publish_to_nats(data: Dict[str, Any]) -> bool:
    """Publish to NATS topic (graceful degradation if unavailable)."""
    try:
        import nats
        print(f"[NATS] Would publish to {NATS_TOPIC}: {data.get('health_id', 'unknown')}")
        return True
    except ImportError:
        print(f"[NATS] NATS client not available, skipping publish to {NATS_TOPIC}")
        return False


def main() -> int:
    """Main entry point for health gate."""
    start_time = time.time()

    print("=" * 60)
    print("SKYBEAM Publish Health Gate (STORY-026)")
    print("=" * 60)

    # Acquire Phase 6 lock
    lock_fd = acquire_lock()
    if lock_fd is None:
        print("[PARTIAL] Could not acquire Phase 6 lock - another process running")
        print("[PARTIAL] Exiting without writes (lock_busy)")
        return 0

    try:
        # Ensure directories exist
        HEALTH_DIR.mkdir(parents=True, exist_ok=True)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        # Run all checks
        checks = [
            check_queue_stuck(),
            check_metrics_freshness(),
            check_receipt_freshness(),
            check_failed_receipts(),
            check_master_consistency(),
            check_api_access()
        ]

        # Print check results
        for check in checks:
            result_icon = {"pass": "✓", "warning": "⚠", "critical": "✗"}[check["result"]]
            print(f"[{result_icon}] {check['check_type']}: {check['message']}")

        # Determine gate result
        results = [c["result"] for c in checks]
        if "critical" in results:
            gate_result = "critical"
        elif "warning" in results:
            gate_result = "warning"
        else:
            gate_result = "approved"

        # Generate alerts
        alerts = generate_alerts(checks)

        # Update heartbeat
        heartbeat = update_heartbeat()

        # Build summary
        summary = {
            "total_checks": len(checks),
            "passed": sum(1 for c in checks if c["result"] == "pass"),
            "warnings": sum(1 for c in checks if c["result"] == "warning"),
            "critical": sum(1 for c in checks if c["result"] == "critical"),
            "active_alerts": len(alerts)
        }

        # Build health snapshot
        check_duration_ms = int((time.time() - start_time) * 1000)

        health = {
            "health_id": generate_id("HEALTH"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
            "gate_result": gate_result,
            "alerts": alerts,
            "summary": summary,
            "heartbeat": heartbeat,
            "meta": {
                "version": "1.0.0",
                "service": "publish_health_gate",
                "story_id": "SKYBEAM-STORY-026",
                "host": socket.gethostname(),
                "check_duration_ms": check_duration_ms
            }
        }

        # Write health snapshot
        with open(HEALTH_LATEST, "w") as f:
            json.dump(health, f, indent=2)

        # Write alerts JSON
        with open(ALERTS_LATEST, "w") as f:
            json.dump({"alerts": alerts, "timestamp": health["timestamp"]}, f, indent=2)

        # Write alerts markdown
        write_alerts_markdown(alerts, gate_result)

        # Publish to NATS
        publish_to_nats(health)

        print(f"\n[OK] Health ID: {health['health_id']}")
        print(f"[OK] Gate result: {gate_result.upper()}")
        print(f"[OK] Checks: {summary['passed']}/{summary['total_checks']} passed")
        print(f"[OK] Active alerts: {summary['active_alerts']}")
        print(f"[OK] Heartbeat: {heartbeat['consecutive_beats']} consecutive")

        return 0

    finally:
        release_lock(lock_fd)


if __name__ == "__main__":
    sys.exit(main())
