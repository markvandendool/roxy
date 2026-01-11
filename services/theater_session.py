#!/usr/bin/env python3
"""
Theater Session Utilities (THEATER-007)

Provides session manifest loading, validation, and file handoff utilities
for MindSong Theater integration.

This module is used by obs_director.py and can be imported by other services.
"""

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

ROXY_BASE = Path.home() / ".roxy"
THEATER_SESSIONS_DIR = ROXY_BASE / "theater-sessions"
SCHEMA_PATH = THEATER_SESSIONS_DIR / "session_manifest_schema.json"
PIPELINE_INPUT = ROXY_BASE / "content-pipeline" / "input"


def generate_session_id() -> str:
    """Generate a unique session ID with timestamp and hash."""
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d_%H%M%S")
    h = hashlib.sha256(f"{ts}{os.getpid()}{now.microsecond}".encode()).hexdigest()[:8]
    return f"SESSION_{ts}_{h}"


def generate_job_id(session_id: str = "") -> str:
    """Generate a unique job ID for SKYBEAM pipeline."""
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d_%H%M%S")
    seed = f"{session_id}{ts}{os.getpid()}"
    h = hashlib.sha256(seed.encode()).hexdigest()[:8]
    return f"JOB_{ts}_{h}"


def generate_handoff_id() -> str:
    """Generate a unique handoff ID."""
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d_%H%M%S")
    h = hashlib.sha256(f"{ts}{os.getpid()}{now.microsecond}".encode()).hexdigest()[:8]
    return f"HANDOFF_{ts}_{h}"


@dataclass
class ValidationResult:
    """Result of manifest validation."""
    valid: bool
    message: str
    errors: list = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def load_schema() -> Optional[dict]:
    """Load the session manifest JSON schema."""
    if not SCHEMA_PATH.exists():
        return None
    try:
        with open(SCHEMA_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def validate_manifest(manifest: dict) -> ValidationResult:
    """
    Validate a session manifest against the schema.

    Returns ValidationResult with valid=True if manifest is valid.
    """
    try:
        import jsonschema
    except ImportError:
        return ValidationResult(True, "Validation skipped (jsonschema not installed)")

    schema = load_schema()
    if schema is None:
        return ValidationResult(True, "Validation skipped (schema not found)")

    try:
        jsonschema.validate(manifest, schema)
        return ValidationResult(True, "Valid")
    except jsonschema.ValidationError as e:
        return ValidationResult(False, f"Validation error: {e.message}", [str(e)])


def load_manifest(path: Path) -> Tuple[Optional[dict], str]:
    """
    Load and validate a session manifest.

    Returns (manifest, error_message) tuple.
    """
    if not path.exists():
        return None, f"File not found: {path}"

    try:
        with open(path) as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {e}"

    result = validate_manifest(manifest)
    if not result.valid:
        return None, result.message

    return manifest, ""


def save_manifest(manifest: dict, path: Optional[Path] = None) -> Path:
    """
    Save a session manifest to disk.

    If path is None, generates path from session_id.
    """
    session_id = manifest.get("session_id")
    if not session_id:
        session_id = generate_session_id()
        manifest["session_id"] = session_id

    if path is None:
        THEATER_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        path = THEATER_SESSIONS_DIR / f"session_{session_id}.json"

    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)

    return path


def create_session_manifest(
    song_path: str,
    title: str = "",
    duration_seconds: float = 0,
    bpm: float = 120,
    preset: str = "performance",
    recording_mode: str = "dual",
    auto_ingest: bool = True
) -> dict:
    """
    Create a new session manifest with defaults.

    Args:
        song_path: Path to audio file
        title: Song title
        duration_seconds: Song duration
        bpm: Beats per minute
        preset: Theater preset (analysis, performance, teaching, minimal, composer)
        recording_mode: dual, landscape_only, or portrait_only
        auto_ingest: Whether to auto-ingest into SKYBEAM

    Returns:
        Complete session manifest dict
    """
    session_id = generate_session_id()
    now = datetime.now(timezone.utc)

    return {
        "session_id": session_id,
        "created_at": now.isoformat(),
        "song": {
            "file_path": song_path,
            "title": title or Path(song_path).stem,
            "duration_seconds": duration_seconds,
            "bpm": bpm,
            "time_signature": "4/4"
        },
        "recording": {
            "mode": recording_mode,
            "outputs": {
                "landscape": {
                    "resolution": "3840x2160",
                    "ndi_source": "MindSong Landscape 8K"
                },
                "portrait": {
                    "resolution": "1080x1920",
                    "ndi_source": "MindSong Portrait 4K"
                }
            },
            "pre_roll_seconds": 2,
            "post_roll_seconds": 2
        },
        "theater": {
            "preset": preset
        },
        "skybeam": {
            "auto_ingest": auto_ingest,
            "job_type": "shorts"
        },
        "status": "pending"
    }


def create_handoff_manifest(
    session_id: str,
    job_id: str,
    files: dict,
    metadata: dict = None
) -> dict:
    """
    Create a handoff manifest for SKYBEAM pipeline.

    Args:
        session_id: Source session ID
        job_id: Target SKYBEAM job ID
        files: Dict with landscape/portrait file info
        metadata: Additional metadata

    Returns:
        Handoff manifest dict
    """
    now = datetime.now(timezone.utc)

    return {
        "handoff_id": generate_handoff_id(),
        "session_id": session_id,
        "job_id": job_id,
        "timestamp": now.isoformat(),
        "files": files,
        "metadata": metadata or {}
    }


def file_sha256(path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def handoff_recording(
    session_manifest: dict,
    landscape_path: Optional[Path] = None,
    portrait_path: Optional[Path] = None
) -> Tuple[str, Path]:
    """
    Hand off recording files to SKYBEAM pipeline.

    Creates job directory, copies files, and writes handoff manifest.

    Args:
        session_manifest: The session manifest dict
        landscape_path: Path to landscape recording (optional)
        portrait_path: Path to portrait recording (optional)

    Returns:
        (job_id, handoff_manifest_path) tuple
    """
    session_id = session_manifest.get("session_id", "unknown")
    job_id = generate_job_id(session_id)

    # Create job directory
    job_dir = PIPELINE_INPUT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    files = {}

    # Copy landscape file
    if landscape_path and landscape_path.exists():
        dest = job_dir / "landscape.mp4"
        shutil.copy2(landscape_path, dest)
        files["landscape"] = {
            "source": str(landscape_path),
            "destination": str(dest),
            "sha256": file_sha256(dest),
            "resolution": session_manifest.get("recording", {}).get("outputs", {}).get("landscape", {}).get("resolution", "3840x2160")
        }

    # Copy portrait file
    if portrait_path and portrait_path.exists():
        dest = job_dir / "portrait.mp4"
        shutil.copy2(portrait_path, dest)
        files["portrait"] = {
            "source": str(portrait_path),
            "destination": str(dest),
            "sha256": file_sha256(dest),
            "resolution": session_manifest.get("recording", {}).get("outputs", {}).get("portrait", {}).get("resolution", "1080x1920")
        }

    # Build metadata from session
    metadata = {
        "song_title": session_manifest.get("song", {}).get("title", "Unknown"),
        "theater_preset": session_manifest.get("theater", {}).get("preset", "performance"),
        "auto_process": session_manifest.get("skybeam", {}).get("auto_ingest", True)
    }

    # Create handoff manifest
    handoff = create_handoff_manifest(session_id, job_id, files, metadata)

    # Write handoff manifest
    handoff_path = job_dir / "handoff_manifest.json"
    with open(handoff_path, "w") as f:
        json.dump(handoff, f, indent=2)

    return job_id, handoff_path


# CLI for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: theater_session.py <command>")
        print("Commands:")
        print("  create <song_path> [title] [bpm]  - Create session manifest")
        print("  validate <manifest.json>          - Validate manifest")
        print("  generate-id                       - Generate session ID")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "create" and len(sys.argv) > 2:
        song_path = sys.argv[2]
        title = sys.argv[3] if len(sys.argv) > 3 else ""
        bpm = float(sys.argv[4]) if len(sys.argv) > 4 else 120

        manifest = create_session_manifest(song_path, title=title, bpm=bpm)
        path = save_manifest(manifest)
        print(f"Created: {path}")
        print(json.dumps(manifest, indent=2))

    elif cmd == "validate" and len(sys.argv) > 2:
        manifest, error = load_manifest(Path(sys.argv[2]))
        if error:
            print(f"Error: {error}")
            sys.exit(1)
        print("Valid manifest")
        print(f"Session ID: {manifest.get('session_id')}")

    elif cmd == "generate-id":
        print(generate_session_id())

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
