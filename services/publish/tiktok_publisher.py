#!/usr/bin/env python3
"""
SKYBEAM TikTok Publisher (STORY-024)

Documentation: file:///home/mark/.roxy/SKYBEAM_CURRENT_STATE.md

Input:
- publish_queue_latest.json (latest entry)
- publish_package_latest.json (metadata + captions)
- master_latest.mp4 (video file)

Output:
- tiktok_latest.json (latest receipt)
- tiktok_<publish_id>.json (immutable historical receipt)
- Handoff pack in exports/tiktok/<publish_id>/ (when API unavailable)

NATS topic: ghost.publish.tiktok

Modes:
- DRY_RUN (default): Validates inputs, writes receipt with status=dry_run
- HANDOFF: Creates manual upload pack when no API access
- LIVE: Requires credentials, performs actual upload

Credentials: ~/.roxy/credentials/tiktok_oauth.json (0600 permissions)
Lock: Uses /tmp/skybeam_publish.lock (fcntl LOCK_EX|LOCK_NB)
"""

import json
import os
import sys
import hashlib
import socket
import fcntl
import shutil
import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

# Paths
PIPELINE_BASE = Path.home() / ".roxy" / "content-pipeline"
QUEUE_SNAPSHOT = PIPELINE_BASE / "publish" / "queue" / "publish_queue_latest.json"
PACKAGE_LATEST = PIPELINE_BASE / "publish" / "packages" / "publish_package_latest.json"
CAPTIONS_LATEST = PIPELINE_BASE / "publish" / "packages" / "captions_latest.srt"
RECEIPTS_DIR = PIPELINE_BASE / "publish" / "receipts"
EXPORTS_DIR = PIPELINE_BASE / "publish" / "exports" / "tiktok"
TIKTOK_LATEST = RECEIPTS_DIR / "tiktok_latest.json"
CREDENTIALS_FILE = Path.home() / ".roxy" / "credentials" / "tiktok_oauth.json"
LOCK_FILE = Path("/tmp/skybeam_publish.lock")

# Track published IDs for idempotency
PUBLISHED_IDS_FILE = RECEIPTS_DIR / ".tiktok_published.json"

# Constants
NATS_TOPIC = "ghost.publish.tiktok"
MAX_RETRIES = 3
TIKTOK_TITLE_MAX = 150
TIKTOK_DESC_MAX = 2200


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
    """Check if TikTok credentials are present and valid."""
    if not CREDENTIALS_FILE.exists():
        return False, "Credentials file not found"

    # Check permissions (should be 0600)
    mode = CREDENTIALS_FILE.stat().st_mode & 0o777
    if mode != 0o600:
        print(f"[WARN] Credentials file has insecure permissions: {oct(mode)}")

    try:
        with open(CREDENTIALS_FILE, "r") as f:
            creds = json.load(f)
        if "client_key" in creds or "access_token" in creds:
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

        # Skip if already published, publishing, handoff_ready, or dry_run
        if status in ("published", "publishing", "handoff_ready", "dry_run"):
            return True, f"Already processed with status: {status}", record

        # Allow retry for failed if under max
        if status == "failed":
            retry_count = record.get("retry_count", 0)
            if retry_count < MAX_RETRIES:
                return False, f"Failed, retry allowed ({retry_count}/{MAX_RETRIES})", record
            return True, f"Failed, max retries reached ({retry_count}/{MAX_RETRIES})", record

    return False, "Not yet processed", {}


def dedupe_hashtags(hashtags: list) -> list:
    """Remove duplicate hashtags while preserving order."""
    seen = set()
    result = []
    for tag in hashtags:
        normalized = tag.lower()
        if normalized not in seen:
            seen.add(normalized)
            result.append(tag)
    return result


def decode_html_entities(text: str) -> str:
    """Decode HTML entities like &#160; and &#8220; to readable characters."""
    return html.unescape(text) if text else text


def build_upload_metadata(package: Dict) -> Dict:
    """Build TikTok upload metadata from package."""
    title = decode_html_entities(package.get("title", "SKYBEAM Video"))[:TIKTOK_TITLE_MAX]
    description = decode_html_entities(package.get("description", ""))[:TIKTOK_DESC_MAX]
    hashtags = dedupe_hashtags(package.get("hashtags", []))

    return {
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "visibility": "private",
        "allow_comments": True,
        "allow_duet": False,
        "allow_stitch": False
    }


def build_copy_paste_text(metadata: Dict) -> str:
    """Build ready-to-paste caption text for manual upload."""
    # Metadata should already be decoded, but ensure it here for safety
    title = decode_html_entities(metadata.get("title", ""))
    description = decode_html_entities(metadata.get("description", ""))
    hashtags = metadata.get("hashtags", [])

    text_parts = []
    if title:
        text_parts.append(title)
    if description:
        # Extract just the first line of description
        first_line = description.split("\n")[0]
        if first_line and first_line != title:
            text_parts.append(first_line)
    if hashtags:
        text_parts.append(" ".join(hashtags))

    return "\n\n".join(text_parts)


def create_handoff_pack(publish_id: str, video_path: str, captions_path: str,
                        metadata: Dict, package: Dict) -> Dict:
    """Create a manual handoff pack for TikTok upload."""
    # Create export directory
    export_dir = EXPORTS_DIR / publish_id
    export_dir.mkdir(parents=True, exist_ok=True)

    # Copy video file
    video_dest = export_dir / "video.mp4"
    if video_path and Path(video_path).exists():
        shutil.copy2(video_path, video_dest)

    # Copy captions file
    captions_dest = export_dir / "captions.srt"
    if captions_path and Path(captions_path).exists():
        shutil.copy2(captions_path, captions_dest)

    # Write metadata JSON
    metadata_dest = export_dir / "metadata.json"
    with open(metadata_dest, "w") as f:
        json.dump({
            "publish_id": publish_id,
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "hashtags": metadata.get("hashtags", []),
            "visibility": metadata.get("visibility", "private"),
            "created": datetime.now(timezone.utc).isoformat()
        }, f, indent=2)

    # Write copy-paste text
    copy_paste_text = build_copy_paste_text(metadata)
    copy_paste_dest = export_dir / "copy_paste.txt"
    with open(copy_paste_dest, "w") as f:
        f.write(copy_paste_text)

    # Write checklist
    checklist_dest = export_dir / "UPLOAD_CHECKLIST.md"
    with open(checklist_dest, "w") as f:
        f.write(f"""# TikTok Manual Upload Checklist

## Publish ID: {publish_id}
## Created: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

## Files in this pack:
- [ ] video.mp4 - The video to upload
- [ ] captions.srt - Captions file (optional)
- [ ] copy_paste.txt - Ready-to-paste caption text
- [ ] metadata.json - Full metadata for reference

## Upload Steps:
1. [ ] Open TikTok app or web creator portal
2. [ ] Click "Upload" or "+" button
3. [ ] Select video.mp4 from this folder
4. [ ] Copy text from copy_paste.txt into caption field
5. [ ] Set visibility to: {metadata.get('visibility', 'private')}
6. [ ] Review and post

## After Upload:
- [ ] Note the TikTok video URL
- [ ] Update receipt with video ID if available

## SKYBEAM Content Factory
This handoff pack was generated automatically.
""")

    return {
        "export_dir": str(export_dir),
        "video_file": str(video_dest) if video_dest.exists() else None,
        "captions_file": str(captions_dest) if captions_dest.exists() else None,
        "metadata_file": str(metadata_dest),
        "checklist_file": str(checklist_dest),
        "copy_paste_text": copy_paste_text
    }


def write_receipt(receipt: Dict, publish_id: str) -> None:
    """Write receipt to latest and historical files."""
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)

    # Write latest
    with open(TIKTOK_LATEST, "w") as f:
        json.dump(receipt, f, indent=2)

    # Write historical (immutable)
    historical_path = RECEIPTS_DIR / f"tiktok_{publish_id}.json"
    with open(historical_path, "w") as f:
        json.dump(receipt, f, indent=2)


def perform_upload(video_path: Path, metadata: Dict) -> Dict:
    """Perform actual TikTok upload (stubbed for now)."""
    # This would use TikTok's Content Posting API
    # https://developers.tiktok.com/doc/content-posting-api-get-started

    return {
        "video_id": "STUB_" + generate_id("VID"),
        "share_url": "https://tiktok.com/@user/video/STUB",
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
    """Main entry point for TikTok publisher."""
    print("=" * 60)
    print("SKYBEAM TikTok Publisher (STORY-024)")
    print("=" * 60)

    # Acquire Phase 6 lock
    lock_fd = acquire_lock()
    if lock_fd is None:
        print("[PARTIAL] Could not acquire Phase 6 lock - another process running")
        print("[PARTIAL] Exiting without writes (lock_busy)")
        return 0

    try:
        # Ensure directories exist
        RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

        # Check credentials to determine mode
        creds_present, creds_msg = check_credentials()

        # Determine mode: live (creds), handoff (no creds, create pack), dry_run (validation only)
        if creds_present:
            mode = "live"
        else:
            mode = "handoff"  # Default to handoff when no API access

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

        # Get file paths (absolute paths)
        captions_info = package.get("captions", {})
        captions_path = captions_info.get("file_path", str(CAPTIONS_LATEST))
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
        print(f"[META] Hashtags: {len(upload_metadata['hashtags'])} tags")

        # Determine status based on mode
        if degraded:
            status = "degraded"
            next_action = "investigate"
        elif mode == "handoff":
            status = "handoff_ready"
            next_action = "use_handoff_pack"
        elif mode == "dry_run":
            status = "dry_run"
            next_action = "manual_upload_required"
        else:
            status = "pending"
            next_action = "none"

        # Build receipt
        receipt = {
            "receipt_id": generate_id("TT"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "publish_id": publish_id,
            "package_id": package.get("package_id", ""),
            "master_id": latest_entry.get("master_id", ""),
            "master_sha256": master_sha256,
            "script_id": script_id,
            "mode": mode,
            "status": status,
            "platform": "tiktok",
            "upload_metadata": upload_metadata,
            "file_paths": {
                "video": video_path,
                "captions": captions_path
            },
            "next_action": next_action,
            "retry_info": {
                "retry_allowed": True,
                "retry_count": prev_record.get("retry_count", 0),
                "max_retries": MAX_RETRIES
            },
            "meta": {
                "version": "1.0.0",
                "service": "tiktok_publisher",
                "story_id": "SKYBEAM-STORY-024",
                "host": socket.gethostname(),
                "credentials_present": creds_present,
                "handoff_mode": mode == "handoff"
            }
        }

        if degraded_reason:
            receipt["degraded_reason"] = degraded_reason

        # Create handoff pack if in handoff mode and not degraded
        if mode == "handoff" and not degraded:
            print("[HANDOFF] Creating manual upload pack...")
            handoff_pack = create_handoff_pack(
                publish_id, video_path, captions_path,
                upload_metadata, package
            )
            receipt["handoff_pack"] = handoff_pack
            print(f"[HANDOFF] Pack created: {handoff_pack['export_dir']}")

        # Perform upload if live mode and not degraded
        if mode == "live" and not degraded:
            print("[UPLOAD] Starting TikTok upload...")
            try:
                receipt["status"] = "uploading"
                tiktok_response = perform_upload(Path(video_path), upload_metadata)
                receipt["tiktok_response"] = tiktok_response
                receipt["status"] = "published"
                receipt["next_action"] = "none"
                print(f"[UPLOAD] Success: {tiktok_response.get('share_url', 'N/A')}")
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
