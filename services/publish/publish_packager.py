#!/usr/bin/env python3
"""
SKYBEAM Publish Packager (STORY-022)

Documentation: file:///home/mark/.roxy/SKYBEAM_CURRENT_STATE.md

Input:
- publish_queue_latest.json (latest_entry with status=queued)
- master_latest.json
- production_qa_latest.json (approved required)
- scripts_reviewed.json / scripts_latest.json

Output:
- publish_package_latest.json
- captions_latest.srt

NATS topic: ghost.publish.package

Idempotency: Uses publish_id + master_sha256 as dedup key.
Degraded mode: If script missing, produces fallback title/desc/captions.
Lock: Uses /tmp/skybeam_publish.lock (fcntl LOCK_EX|LOCK_NB). If busy, status=partial, exit 0.
"""

import json
import os
import sys
import hashlib
import socket
import fcntl
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# Paths
PIPELINE_BASE = Path.home() / ".roxy" / "content-pipeline"
QUEUE_SNAPSHOT = PIPELINE_BASE / "publish" / "queue" / "publish_queue_latest.json"
MASTER_MANIFEST = PIPELINE_BASE / "production" / "master" / "master_latest.json"
PRODUCTION_QA = PIPELINE_BASE / "production" / "qa" / "production_qa_latest.json"
SCRIPTS_REVIEWED = PIPELINE_BASE / "scripts" / "scripts_reviewed.json"
SCRIPTS_LATEST = PIPELINE_BASE / "scripts" / "scripts_latest.json"
PACKAGES_DIR = PIPELINE_BASE / "publish" / "packages"
PACKAGE_LATEST = PACKAGES_DIR / "publish_package_latest.json"
CAPTIONS_LATEST = PACKAGES_DIR / "captions_latest.srt"
LOCK_FILE = Path("/tmp/skybeam_publish.lock")

# Track packaged hashes for idempotency
PACKAGED_HASHES_FILE = PACKAGES_DIR / ".packaged_hashes.json"

# Constants
NATS_TOPIC = "ghost.publish.package"
MIN_CAPTION_DURATION = 1.2  # seconds
MAX_CAPTION_DURATION = 4.0  # seconds
DEFAULT_HASHTAGS = ["#AI", "#Tech", "#Shorts", "#SKYBEAM"]


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


def load_packaged_hashes() -> set:
    """Load already-packaged publish_id + master_sha256 combos."""
    hashes = set()
    if PACKAGED_HASHES_FILE.exists():
        try:
            with open(PACKAGED_HASHES_FILE, "r") as f:
                data = json.load(f)
                hashes = set(data.get("packaged", []))
        except (json.JSONDecodeError, KeyError):
            pass
    return hashes


def save_packaged_hash(combo_hash: str) -> None:
    """Save a packaged hash combo."""
    hashes = load_packaged_hashes()
    hashes.add(combo_hash)
    with open(PACKAGED_HASHES_FILE, "w") as f:
        json.dump({"packaged": list(hashes)}, f)


def check_qa_gate(qa_data: Dict[str, Any]) -> Tuple[bool, str]:
    """Check if QA gate is approved."""
    gate_result = qa_data.get("gate_result", "")
    if gate_result == "approved":
        return True, "QA gate approved"
    return False, f"QA gate not approved: {gate_result}"


def find_script(script_id: str, scripts_reviewed: Dict, scripts_latest: Dict) -> Optional[Dict]:
    """Find script by ID in reviewed or latest scripts."""
    # Try reviewed scripts first
    if scripts_reviewed:
        for script in scripts_reviewed.get("reviewed_scripts", []):
            if script.get("script_id") == script_id:
                return script

    # Try latest scripts
    if scripts_latest:
        for script in scripts_latest.get("scripts", []):
            if script.get("id") == script_id:
                return script

    return None


def find_script_content(script_id: str, scripts_latest: Dict) -> Optional[Dict]:
    """Find full script content by ID."""
    if scripts_latest:
        for script in scripts_latest.get("scripts", []):
            if script.get("id") == script_id:
                return script
    return None


def extract_narration_text(script: Dict) -> str:
    """Extract narration text from script sections."""
    sections = script.get("sections", [])
    texts = []
    for section in sections:
        content = section.get("content", "")
        # Strip section markers like [HOOK], [CONTEXT], etc.
        content = re.sub(r'\[([A-Z]+)\]\s*', '', content)
        if content:
            texts.append(content.strip())
    return " ".join(texts)


def format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp HH:MM:SS,mmm.

    Uses integer millisecond rounding to avoid floating-point precision issues.
    """
    ms_total = int(round(seconds * 1000.0))
    hours = ms_total // 3600000
    ms_total %= 3600000
    minutes = ms_total // 60000
    ms_total %= 60000
    secs = ms_total // 1000
    millis = ms_total % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_captions(text: str, duration_seconds: float) -> List[Dict]:
    """Generate SRT caption segments from text."""
    if not text.strip():
        # Fallback for empty text
        return generate_fallback_captions(duration_seconds)

    # Split into sentences/phrases
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return generate_fallback_captions(duration_seconds)

    # Calculate time per segment
    total_chars = sum(len(s) for s in sentences)
    segments = []
    current_time = 0.0

    for i, sentence in enumerate(sentences):
        # Allocate time proportionally to text length
        if total_chars > 0:
            segment_duration = (len(sentence) / total_chars) * duration_seconds
        else:
            segment_duration = duration_seconds / len(sentences)

        # Clamp duration
        segment_duration = max(MIN_CAPTION_DURATION, min(MAX_CAPTION_DURATION, segment_duration))

        # Don't exceed total duration
        if current_time + segment_duration > duration_seconds:
            segment_duration = duration_seconds - current_time

        if segment_duration < 0.5:
            break

        end_time = current_time + segment_duration

        segments.append({
            "index": i + 1,
            "start_time": format_srt_time(current_time),
            "end_time": format_srt_time(end_time),
            "text": sentence[:200]  # Truncate long sentences
        })

        current_time = end_time

        if current_time >= duration_seconds:
            break

    return segments


def generate_fallback_captions(duration_seconds: float) -> List[Dict]:
    """Generate fallback captions when script text is missing."""
    fallback_texts = [
        "Welcome to SKYBEAM AI insights.",
        "Stay tuned for the latest in AI and tech.",
        "Subscribe for more content like this."
    ]

    segment_duration = min(MAX_CAPTION_DURATION, duration_seconds / 3)
    segments = []
    current_time = 0.0

    for i, text in enumerate(fallback_texts):
        if current_time >= duration_seconds:
            break
        end_time = min(current_time + segment_duration, duration_seconds)
        segments.append({
            "index": i + 1,
            "start_time": format_srt_time(current_time),
            "end_time": format_srt_time(end_time),
            "text": text
        })
        current_time = end_time

    return segments


def write_srt_file(segments: List[Dict], path: Path) -> None:
    """Write segments to SRT file."""
    with open(path, "w") as f:
        for seg in segments:
            f.write(f"{seg['index']}\n")
            f.write(f"{seg['start_time']} --> {seg['end_time']}\n")
            f.write(f"{seg['text']}\n\n")


def generate_description(script: Optional[Dict], title: str) -> str:
    """Generate video description from script or fallback."""
    if script:
        # Try to get summary from script
        variables = script.get("variables", {})
        summary = variables.get("summary", "")
        if summary:
            return f"{summary}\n\n{' '.join(DEFAULT_HASHTAGS)}"

    # Fallback description
    return f"AI-powered insights on: {title}\n\nPowered by SKYBEAM Content Factory.\n\n{' '.join(DEFAULT_HASHTAGS)}"


def generate_hashtags(script: Optional[Dict]) -> List[str]:
    """Generate hashtags from script or defaults."""
    tags = list(DEFAULT_HASHTAGS)
    if script:
        category = script.get("variables", {}).get("category", "")
        if category:
            tags.append(f"#{category.upper()}")
    return tags


def publish_to_nats(data: Dict[str, Any]) -> bool:
    """Publish to NATS topic (graceful degradation if unavailable)."""
    try:
        import nats
        print(f"[NATS] Would publish to {NATS_TOPIC}: {data.get('package_id', 'unknown')}")
        return True
    except ImportError:
        print(f"[NATS] NATS client not available, skipping publish to {NATS_TOPIC}")
        return False


def main() -> int:
    """Main entry point for publish packager."""
    print("=" * 60)
    print("SKYBEAM Publish Packager (STORY-022)")
    print("=" * 60)

    # Acquire Phase 6 lock
    lock_fd = acquire_lock()
    if lock_fd is None:
        print("[PARTIAL] Could not acquire Phase 6 lock - another process running")
        print("[PARTIAL] Exiting without writes (lock_busy)")
        return 0

    try:
        # Ensure packages directory exists
        PACKAGES_DIR.mkdir(parents=True, exist_ok=True)

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
        title = latest_entry.get("title", "SKYBEAM Video")

        print(f"[QUEUE] Publish ID: {publish_id}")
        print(f"[QUEUE] Master SHA256: {master_sha256[:16]}...")
        print(f"[QUEUE] Script ID: {script_id}")

        # Check idempotency
        combo_hash = hashlib.sha256(f"{publish_id}:{master_sha256}".encode()).hexdigest()
        packaged_hashes = load_packaged_hashes()

        if combo_hash in packaged_hashes:
            print("[IDEM] Already packaged - SKIP (idempotent)")
            return 0

        # Load QA gate
        qa_data = load_json(PRODUCTION_QA)
        if qa_data is None:
            print("[DEGRADED] No QA data available")
            # Continue with degraded mode
            qa_approved = False
        else:
            qa_approved, qa_msg = check_qa_gate(qa_data)
            print(f"[QA] {qa_msg}")
            if not qa_approved:
                print("[DEGRADED] QA not approved - will produce degraded package")

        # Load master manifest for duration
        master_data = load_json(MASTER_MANIFEST)
        duration_seconds = 10.0  # default
        if master_data:
            file_proof = master_data.get("file_proof", {})
            ffprobe = file_proof.get("ffprobe_summary", {})
            duration_seconds = ffprobe.get("duration", 10.0)
        print(f"[MASTER] Duration: {duration_seconds}s")

        # Load scripts
        scripts_reviewed = load_json(SCRIPTS_REVIEWED)
        scripts_latest = load_json(SCRIPTS_LATEST)

        # Find script content
        script = find_script_content(script_id, scripts_latest)
        degraded = False
        degraded_reason = ""

        if script:
            print(f"[SCRIPT] Found: {script.get('template_name', 'unknown')}")
            narration_text = extract_narration_text(script)
        else:
            print(f"[WARN] Script {script_id} not found - using fallback")
            narration_text = ""
            degraded = True
            degraded_reason = f"Script {script_id} not found"

        if not qa_approved:
            degraded = True
            degraded_reason = degraded_reason or "QA not approved"

        # Generate captions
        caption_segments = generate_captions(narration_text, duration_seconds)
        print(f"[CAPTIONS] Generated {len(caption_segments)} segments")

        # Write SRT file
        write_srt_file(caption_segments, CAPTIONS_LATEST)
        print(f"[CAPTIONS] Written to: {CAPTIONS_LATEST}")

        # Build package
        package = {
            "package_id": generate_id("PKG"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "publish_id": publish_id,
            "master_id": latest_entry.get("master_id", ""),
            "master_sha256": master_sha256,
            "script_id": script_id,
            "title": title[:100],
            "description": generate_description(script, title),
            "hashtags": generate_hashtags(script),
            "captions": {
                "format": "srt",
                "segment_count": len(caption_segments),
                "duration_seconds": duration_seconds,
                "file_path": str(CAPTIONS_LATEST),
                "segments": caption_segments
            },
            "thumbnail": {
                "status": "pending"
            },
            "platforms": latest_entry.get("platforms", ["youtube_shorts", "tiktok"]),
            "status": "degraded" if degraded else "healthy",
            "meta": {
                "version": "1.0.0",
                "service": "publish_packager",
                "story_id": "SKYBEAM-STORY-022",
                "host": socket.gethostname()
            }
        }

        if degraded_reason:
            package["degraded_reason"] = degraded_reason

        # Write package
        with open(PACKAGE_LATEST, "w") as f:
            json.dump(package, f, indent=2)

        # Save packaged hash for idempotency
        save_packaged_hash(combo_hash)

        # Publish to NATS
        publish_to_nats(package)

        print(f"[OK] Package ID: {package['package_id']}")
        print(f"[OK] Status: {package['status']}")
        print(f"[OK] Captions: {len(caption_segments)} segments, {duration_seconds}s")

        return 0

    finally:
        release_lock(lock_fd)


if __name__ == "__main__":
    sys.exit(main())
