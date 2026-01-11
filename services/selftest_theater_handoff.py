#!/usr/bin/env python3
"""
SELFTEST: Theater Handoff Protocol (THEATER-012)

Deterministic tests for:
1. Dummy recording files created correctly
2. handoff_recording copies files to destination
3. File sizes match
4. SHA256 hashes match calculated values
5. Handoff manifest exists with correct references

Writes: handoff_selftest_results.json, handoff_manifest.json
Exit: 0 on all expected outcomes, 1 on unexpected failure
"""

import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Add services to path
sys.path.insert(0, str(Path(__file__).parent))

from theater_session import (
    create_session_manifest,
    handoff_recording,
    file_sha256,
    generate_job_id,
    generate_handoff_id,
)

RESULTS = []


def log_result(test_name: str, expected: str, actual: str, passed: bool, details: str = ""):
    """Log a test result."""
    result = {
        "test": test_name,
        "expected": expected,
        "actual": actual,
        "passed": passed,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    RESULTS.append(result)
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {test_name}: expected={expected}, actual={actual}")
    if details:
        print(f"       Details: {details[:100]}...")


def create_dummy_recording(path: Path, size_bytes: int = 1024) -> str:
    """Create a dummy recording file with random bytes, return SHA256."""
    # Use deterministic "random" bytes based on path for reproducibility
    seed = hashlib.sha256(str(path).encode()).digest()
    content = (seed * (size_bytes // len(seed) + 1))[:size_bytes]

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)

    return hashlib.sha256(content).hexdigest()


def test_dummy_file_creation():
    """Test 1: Dummy recording files can be created with correct hash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dummy_path = Path(tmpdir) / "test_recording.mp4"
        expected_size = 2048

        sha = create_dummy_recording(dummy_path, expected_size)

        exists = dummy_path.exists()
        actual_size = dummy_path.stat().st_size if exists else 0
        size_match = actual_size == expected_size

        # Verify hash
        actual_sha = file_sha256(dummy_path) if exists else ""
        hash_match = sha == actual_sha

        passed = exists and size_match and hash_match

        log_result(
            "test_dummy_file_creation",
            "EXISTS+SIZE_MATCH+HASH_MATCH",
            f"exists={exists}, size={size_match}, hash={hash_match}",
            passed,
            f"Size: {actual_size}, SHA256: {sha[:16]}..."
        )
        return passed


def test_handoff_copies_files():
    """Test 2: handoff_recording copies files to destination."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set up temporary pipeline input
        tmp_pipeline = Path(tmpdir) / "pipeline" / "input"
        tmp_pipeline.mkdir(parents=True)

        # Temporarily override PIPELINE_INPUT
        import theater_session
        original_pipeline = theater_session.PIPELINE_INPUT
        theater_session.PIPELINE_INPUT = tmp_pipeline

        try:
            # Create dummy recordings
            landscape_path = Path(tmpdir) / "source" / "landscape.mp4"
            portrait_path = Path(tmpdir) / "source" / "portrait.mp4"

            landscape_sha = create_dummy_recording(landscape_path, 4096)
            portrait_sha = create_dummy_recording(portrait_path, 2048)

            # Create session manifest
            manifest = create_session_manifest(
                song_path="/tmp/test.mp3",
                title="Handoff Test",
                duration_seconds=60,
                bpm=120
            )

            # Perform handoff
            job_id, handoff_path = handoff_recording(
                manifest,
                landscape_path=landscape_path,
                portrait_path=portrait_path
            )

            # Verify job directory created
            job_dir = tmp_pipeline / job_id
            job_exists = job_dir.exists()

            # Verify files copied
            dest_landscape = job_dir / "landscape.mp4"
            dest_portrait = job_dir / "portrait.mp4"
            landscape_copied = dest_landscape.exists()
            portrait_copied = dest_portrait.exists()

            passed = job_exists and landscape_copied and portrait_copied

            log_result(
                "test_handoff_copies_files",
                "JOB_DIR+FILES_COPIED",
                f"job={job_exists}, land={landscape_copied}, port={portrait_copied}",
                passed,
                f"Job ID: {job_id}"
            )
            return passed

        finally:
            theater_session.PIPELINE_INPUT = original_pipeline


def test_handoff_file_sizes_match():
    """Test 3: Copied files have matching sizes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_pipeline = Path(tmpdir) / "pipeline" / "input"
        tmp_pipeline.mkdir(parents=True)

        import theater_session
        original_pipeline = theater_session.PIPELINE_INPUT
        theater_session.PIPELINE_INPUT = tmp_pipeline

        try:
            landscape_path = Path(tmpdir) / "source" / "landscape.mp4"
            landscape_size = 8192
            create_dummy_recording(landscape_path, landscape_size)

            manifest = create_session_manifest(
                song_path="/tmp/test.mp3",
                title="Size Test",
                duration_seconds=30,
                bpm=100
            )

            job_id, _ = handoff_recording(manifest, landscape_path=landscape_path)

            dest_path = tmp_pipeline / job_id / "landscape.mp4"
            dest_size = dest_path.stat().st_size if dest_path.exists() else 0

            size_match = dest_size == landscape_size

            log_result(
                "test_handoff_file_sizes_match",
                f"SIZE={landscape_size}",
                f"SIZE={dest_size}",
                size_match,
                f"Source: {landscape_size}, Dest: {dest_size}"
            )
            return size_match

        finally:
            theater_session.PIPELINE_INPUT = original_pipeline


def test_handoff_sha256_matches():
    """Test 4: Copied files have matching SHA256 hashes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_pipeline = Path(tmpdir) / "pipeline" / "input"
        tmp_pipeline.mkdir(parents=True)

        import theater_session
        original_pipeline = theater_session.PIPELINE_INPUT
        theater_session.PIPELINE_INPUT = tmp_pipeline

        try:
            portrait_path = Path(tmpdir) / "source" / "portrait.mp4"
            expected_sha = create_dummy_recording(portrait_path, 4096)

            manifest = create_session_manifest(
                song_path="/tmp/test.mp3",
                title="Hash Test",
                duration_seconds=45,
                bpm=110
            )

            job_id, _ = handoff_recording(manifest, portrait_path=portrait_path)

            dest_path = tmp_pipeline / job_id / "portrait.mp4"
            actual_sha = file_sha256(dest_path) if dest_path.exists() else ""

            hash_match = expected_sha == actual_sha

            log_result(
                "test_handoff_sha256_matches",
                f"SHA={expected_sha[:16]}...",
                f"SHA={actual_sha[:16]}...",
                hash_match,
                f"Full match: {hash_match}"
            )
            return hash_match

        finally:
            theater_session.PIPELINE_INPUT = original_pipeline


def test_handoff_manifest_exists():
    """Test 5: Handoff manifest is created with correct structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_pipeline = Path(tmpdir) / "pipeline" / "input"
        tmp_pipeline.mkdir(parents=True)

        import theater_session
        original_pipeline = theater_session.PIPELINE_INPUT
        theater_session.PIPELINE_INPUT = tmp_pipeline

        try:
            landscape_path = Path(tmpdir) / "source" / "landscape.mp4"
            create_dummy_recording(landscape_path, 2048)

            manifest = create_session_manifest(
                song_path="/tmp/test.mp3",
                title="Manifest Test",
                duration_seconds=60,
                bpm=120,
                preset="performance"
            )

            job_id, handoff_path = handoff_recording(manifest, landscape_path=landscape_path)

            # Verify handoff manifest exists
            manifest_exists = handoff_path.exists()

            # Verify structure
            if manifest_exists:
                with open(handoff_path) as f:
                    handoff = json.load(f)

                has_handoff_id = "handoff_id" in handoff
                has_session_id = "session_id" in handoff
                has_job_id = "job_id" in handoff
                has_files = "files" in handoff
                has_metadata = "metadata" in handoff

                structure_ok = all([has_handoff_id, has_session_id, has_job_id, has_files, has_metadata])
            else:
                structure_ok = False

            passed = manifest_exists and structure_ok

            log_result(
                "test_handoff_manifest_exists",
                "MANIFEST_OK+STRUCTURE_OK",
                f"exists={manifest_exists}, structure={structure_ok}",
                passed,
                f"Path: {handoff_path}"
            )

            # Copy handoff manifest to proof directory
            if manifest_exists:
                proof_dirs = sorted(Path("/home/mark/.roxy/proofs").glob("PHASE8_THEATER_PROOFS_*"))
                if proof_dirs:
                    import shutil
                    shutil.copy(handoff_path, proof_dirs[-1] / "handoff_manifest.json")

            return passed

        finally:
            theater_session.PIPELINE_INPUT = original_pipeline


def test_job_id_generation():
    """Test 6: Job ID generation follows correct pattern."""
    import re

    job_id = generate_job_id("SESSION_TEST")
    pattern = r"^JOB_[0-9]{8}_[0-9]{6}_[a-f0-9]{8}$"

    matches = bool(re.match(pattern, job_id))

    log_result(
        "test_job_id_generation",
        "PATTERN_MATCH",
        "PATTERN_MATCH" if matches else "PATTERN_MISMATCH",
        matches,
        f"Generated: {job_id}"
    )
    return matches


def main() -> int:
    """Run all tests and write results."""
    print("=" * 60)
    print("SELFTEST: Theater Handoff Protocol")
    print("=" * 60)
    print()

    tests = [
        test_dummy_file_creation,
        test_handoff_copies_files,
        test_handoff_file_sizes_match,
        test_handoff_sha256_matches,
        test_handoff_manifest_exists,
        test_job_id_generation,
    ]

    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            if test_fn():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            log_result(
                test_fn.__name__,
                "NO_EXCEPTION",
                "EXCEPTION",
                False,
                str(e)
            )
            failed += 1

    print()
    print("=" * 60)
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print("=" * 60)

    # Write results
    output = {
        "suite": "theater_handoff_selftest",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": len(tests),
            "passed": passed,
            "failed": failed,
            "success_rate": f"{100*passed/len(tests):.1f}%"
        },
        "results": RESULTS
    }

    proof_dirs = sorted(Path("/home/mark/.roxy/proofs").glob("PHASE8_THEATER_PROOFS_*"))
    if proof_dirs:
        output_path = proof_dirs[-1] / "handoff_selftest_results.json"
    else:
        output_path = Path("handoff_selftest_results.json")

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults written to: {output_path}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
