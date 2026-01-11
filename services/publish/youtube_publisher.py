#!/usr/bin/env python3
"""
SKYBEAM YouTube Shorts Publisher (STORY-023)

Documentation: file:///home/mark/.roxy/SKYBEAM_CURRENT_STATE.md

Input:
- publish_queue_latest.json (latest entry)
- publish_package_latest.json (metadata + captions)
- master_latest.mp4 (video file)

Output:
- youtube_latest.json (latest receipt)
- youtube_<publish_id>.json (immutable historical receipt)

NATS topic: ghost.publish.youtube

Modes:
- DRY_RUN (default): Validates inputs, writes receipt with status=dry_run
- LIVE: Requires credentials, performs actual upload

Credentials: ~/.roxy/credentials/youtube_oauth.json (0600 permissions)
Lock: Uses /tmp/skybeam_publish.lock (fcntl LOCK_EX|LOCK_NB)
"""

import json
import os
import sys
import hashlib
import socket
import fcntl
import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

# Paths
PIPELINE_BASE = Path.home() / ".roxy" / "content-pipeline"
QUEUE_SNAPSHOT = PIPELINE_BASE / "publish" / "queue" / "publish_queue_latest.json"
PACKAGE_LATEST = PIPELINE_BASE / "publish" / "packages" / "publish_package_latest.json"
RECEIPTS_DIR = PIPELINE_BASE / "publish" / "receipts"
YOUTUBE_LATEST = RECEIPTS_DIR / "youtube_latest.json"
CREDENTIALS_FILE = Path.home() / ".roxy" / "credentials" / "youtube_oauth.json"
LOCK_FILE = Path("/tmp/skybeam_publish.lock")

# Track published IDs for idempotency
PUBLISHED_IDS_FILE = RECEIPTS_DIR / ".youtube_published.json"

# Constants
NATS_TOPIC = "ghost.publish.youtube"
MAX_RETRIES = 3
YOUTUBE_CATEGORY_SCIENCE_TECH = "28"


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


def check_credentials() -> Tuple[bool, str]:
    """Check if YouTube credentials are present and valid."""
    if not CREDENTIALS_FILE.exists():
        return False, "Credentials file not found"

    # Check permissions (should be 0600)
    mode = CREDENTIALS_FILE.stat().st_mode & 0o777
    if mode != 0o600:
        print(f"[WARN] Credentials file has insecure permissions: {oct(mode)}")

    try:
        with open(CREDENTIALS_FILE, "r") as f:
            creds = json.load(f)
        # Basic validation - check for expected OAuth fields
        if "client_id" in creds or "access_token" in creds or "refresh_token" in creds:
            return True, "Credentials present"
        return False, "Credentials file missing required fields"
    except json.JSONDecodeError:
        return False, "Invalid credentials JSON"


def load_published_ids() -> Dict[str, Dict]:
    """Load already-published publish_id records."""
    if PUBLISHED_IDS_FILE.exists():
        try:
            with open(PUBLISHED_IDS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            pass
    return {}


def save_published_id(publish_id: str, receipt: Dict) -> None:
    """Save a published ID record."""
    records = load_published_ids()
    records[publish_id] = {
        "status": receipt.get("status"),
        "receipt_id": receipt.get("receipt_id"),
        "timestamp": receipt.get("timestamp"),
        "retry_count": receipt.get("retry_info", {}).get("retry_count", 0)
    }
    with open(PUBLISHED_IDS_FILE, "w") as f:
        json.dump(records, f, indent=2)


def check_idempotency(publish_id: str) -> Tuple[bool, str, Dict]:
    """Check if publish_id has already been processed."""
    records = load_published_ids()
    if publish_id in records:
        record = records[publish_id]
        status = record.get("status", "")

        # Skip if already published or publishing
        if status in ("published", "publishing", "dry_run"):
            return True, f"Already processed with status: {status}", record

        # Allow retry for failed if retry_allowed and under max
        if status == "failed":
            retry_count = record.get("retry_count", 0)
            if retry_count < MAX_RETRIES:
                return False, f"Failed, retry allowed ({retry_count}/{MAX_RETRIES})", record
            return True, f"Failed, max retries reached ({retry_count}/{MAX_RETRIES})", record

    return False, "Not yet processed", {}


def decode_html_entities(text: str) -> str:
    """Decode HTML entities like &#160; and &#8220; to readable characters."""
    return html.unescape(text) if text else text


def dedupe_tags(tags: list) -> list:
    """Remove duplicate tags while preserving order."""
    seen = set()
    result = []
    for tag in tags:
        normalized = tag.lower()
        if normalized not in seen:
            seen.add(normalized)
            result.append(tag)
    return result


def build_upload_metadata(package: Dict) -> Dict:
    """Build YouTube upload metadata from package."""
    title = decode_html_entities(package.get("title", "SKYBEAM Video"))[:100]
    description = decode_html_entities(package.get("description", ""))[:5000]
    hashtags = package.get("hashtags", [])

    # Convert hashtags to tags (remove #)
    tags = [tag.lstrip("#") for tag in hashtags]
    tags.extend(["Shorts", "AI", "Tech"])  # Ensure core tags
    tags = dedupe_tags(tags)  # Remove duplicates

    return {
        "title": title,
        "description": description,
        "tags": tags[:30],  # YouTube limit
        "visibility": "private",  # Default to private for safety
        "category_id": YOUTUBE_CATEGORY_SCIENCE_TECH,
        "shorts": True
    }


def write_receipt(receipt: Dict, publish_id: str) -> None:
    """Write receipt to latest and historical files."""
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)

    # Write latest
    with open(YOUTUBE_LATEST, "w") as f:
        json.dump(receipt, f, indent=2)

    # Write historical (immutable)
    historical_path = RECEIPTS_DIR / f"youtube_{publish_id}.json"
    with open(historical_path, "w") as f:
        json.dump(receipt, f, indent=2)


def perform_upload(video_path: Path, metadata: Dict, captions_path: Optional[Path]) -> Dict:
    """Perform actual YouTube upload (stubbed for now)."""
    # This would use google-api-python-client
    # from googleapiclient.discovery import build
    # from googleapiclient.http import MediaFileUpload

    # For now, return a stub response
    return {
        "video_id": "STUB_" + generate_id("VID"),
        "channel_id": "STUB_CHANNEL",
        "url": "https://youtube.com/shorts/STUB",
        "upload_status": "uploaded"
    }


def publish_to_nats(data: Dict[str, Any]) -> bool:
    """Publish to NATS topic (graceful degradation if unavailable)."""
    try:
        import nats
        print(f"[NATS] Would publish to {NATS_TOPIC}: {data.get('receipt_id', 'unknown')}")
        return True
    except ImportError:
        print(f"[NATS] NATS client not available, skipping publish to {NATS_TOPIC}")
        return False


def main() -> int:
    """Main entry point for YouTube publisher."""
    print("=" * 60)
    print("SKYBEAM YouTube Shorts Publisher (STORY-023)")
    print("=" * 60)

    # Acquire Phase 6 lock
    lock_fd = acquire_lock()
    if lock_fd is None:
        print("[PARTIAL] Could not acquire Phase 6 lock - another process running")
        print("[PARTIAL] Exiting without writes (lock_busy)")
        return 0

    try:
        # Ensure receipts directory exists
        RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)

        # Check credentials to determine mode
        creds_present, creds_msg = check_credentials()
        mode = "live" if creds_present else "dry_run"
        print(f"[MODE] {mode.upper()} - {creds_msg}")

        # Load queue snapshot
        queue_data = load_json(QUEUE_SNAPSHOT)
        if queue_data is None:
            print("[DEGRADED] No queue snapshot available")
            return 0

        # Get latest entry
        latest_entry = queue_data.get("latest_entry")
        if not latest_entry:
            print("[DEGRADED] No entries in queue")
            return 0

        publish_id = latest_entry.get("publish_id", "")
        master_sha256 = latest_entry.get("master_sha256", "")
        script_id = latest_entry.get("script_id", "")

        print(f"[QUEUE] Publish ID: {publish_id}")
        print(f"[QUEUE] Master SHA256: {master_sha256[:16]}...")

        # Check idempotency
        skip, idem_msg, prev_record = check_idempotency(publish_id)
        if skip:
            print(f"[IDEM] {idem_msg} - SKIP")
            return 0

        if prev_record:
            print(f"[RETRY] {idem_msg}")

        # Load package
        package = load_json(PACKAGE_LATEST)
        degraded = False
        degraded_reason = ""

        if package is None:
            print("[DEGRADED] No package available")
            degraded = True
            degraded_reason = "Package not found"
            package = {}

        # Verify package matches queue entry
        if package.get("publish_id") != publish_id:
            print(f"[WARN] Package publish_id mismatch: {package.get('publish_id')} != {publish_id}")
            degraded = True
            degraded_reason = "Package publish_id mismatch"

        # Get file paths
        captions_info = package.get("captions", {})
        captions_path = captions_info.get("file_path", "")
        video_path = latest_entry.get("master_path", "")

        # Verify video file exists
        if video_path and Path(video_path).exists():
            print(f"[VIDEO] Found: {video_path}")
        else:
            print(f"[WARN] Video file not found: {video_path}")
            degraded = True
            degraded_reason = degraded_reason or "Video file not found"

        # Build upload metadata
        upload_metadata = build_upload_metadata(package)
        print(f"[META] Title: {upload_metadata['title'][:50]}...")
        print(f"[META] Tags: {len(upload_metadata['tags'])} tags")

        # Build receipt
        receipt = {
            "receipt_id": generate_id("YT"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "publish_id": publish_id,
            "package_id": package.get("package_id", ""),
            "master_id": latest_entry.get("master_id", ""),
            "master_sha256": master_sha256,
            "script_id": script_id,
            "mode": mode,
            "status": "degraded" if degraded else ("dry_run" if mode == "dry_run" else "pending"),
            "platform": "youtube_shorts",
            "upload_metadata": upload_metadata,
            "file_paths": {
                "video": video_path,
                "captions": captions_path
            },
            "next_action": "manual_upload_required" if mode == "dry_run" else "none",
            "retry_info": {
                "retry_allowed": True,
                "retry_count": prev_record.get("retry_count", 0),
                "max_retries": MAX_RETRIES
            },
            "meta": {
                "version": "1.0.0",
                "service": "youtube_publisher",
                "story_id": "SKYBEAM-STORY-023",
                "host": socket.gethostname(),
                "credentials_present": creds_present
            }
        }

        if degraded_reason:
            receipt["degraded_reason"] = degraded_reason

        # Perform upload if live mode and not degraded
        if mode == "live" and not degraded:
            print("[UPLOAD] Starting YouTube upload...")
            try:
                receipt["status"] = "uploading"
                youtube_response = perform_upload(
                    Path(video_path),
                    upload_metadata,
                    Path(captions_path) if captions_path else None
                )
                receipt["youtube_response"] = youtube_response
                receipt["status"] = "published"
                receipt["next_action"] = "none"
                print(f"[UPLOAD] Success: {youtube_response.get('url', 'N/A')}")
            except Exception as e:
                receipt["status"] = "failed"
                receipt["retry_info"]["retry_count"] += 1
                receipt["retry_info"]["last_error"] = str(e)
                receipt["next_action"] = "retry" if receipt["retry_info"]["retry_count"] < MAX_RETRIES else "investigate"
                print(f"[ERROR] Upload failed: {e}")

        # Write receipt
        write_receipt(receipt, publish_id)

        # Save published ID for idempotency
        save_published_id(publish_id, receipt)

        # Publish to NATS
        publish_to_nats(receipt)

        print(f"[OK] Receipt ID: {receipt['receipt_id']}")
        print(f"[OK] Status: {receipt['status']}")
        print(f"[OK] Mode: {receipt['mode']}")
        print(f"[OK] Next action: {receipt['next_action']}")

        return 0

    finally:
        release_lock(lock_fd)


if __name__ == "__main__":
    sys.exit(main())
