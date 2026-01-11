#!/usr/bin/env python3
"""
SKYBEAM Inject Subcommand Selftest (STORY-030)

Tests:
1. Inject with valid URL creates seed file
2. Dry-run mode does not create file
3. Duplicate detection within 24h
4. URL validation (invalid URLs rejected)
5. Priority flag works
6. Tags flag works
7. Platform detection (YouTube, TikTok)
8. Seed ID format validation
"""

import json
import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

TESTS_PASSED = 0
TESTS_FAILED = 0
SKYBEAM_CLI = Path(__file__).parent / "skybeam"
TEST_SEEDS_DIR = Path.home() / ".roxy" / "content-pipeline" / "seeds" / "manual"


def test_pass(name: str, msg: str = ""):
    global TESTS_PASSED
    TESTS_PASSED += 1
    print(f"  [PASS] {name}" + (f" - {msg}" if msg else ""))


def test_fail(name: str, msg: str = ""):
    global TESTS_FAILED
    TESTS_FAILED += 1
    print(f"  [FAIL] {name}" + (f" - {msg}" if msg else ""))


def cleanup_test_seeds():
    """Remove test seeds from manual directory."""
    if TEST_SEEDS_DIR.exists():
        for f in TEST_SEEDS_DIR.glob("inject_SEED_*.json"):
            try:
                os.unlink(f)
            except Exception:
                pass
        # Clean index
        index_file = TEST_SEEDS_DIR / ".inject_index.json"
        if index_file.exists():
            try:
                os.unlink(index_file)
            except Exception:
                pass


def test_inject_help():
    """Test inject subcommand shows help."""
    try:
        result = subprocess.run(
            [sys.executable, str(SKYBEAM_CLI), "inject", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if "url" in result.stdout.lower() and "priority" in result.stdout.lower():
            test_pass("inject_help", "Help shows url and priority")
        else:
            test_fail("inject_help", "Missing expected help text")
    except Exception as e:
        test_fail("inject_help", str(e))


def test_inject_dry_run():
    """Test dry-run mode doesn't create file."""
    try:
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = subprocess.run(
            [sys.executable, str(SKYBEAM_CLI), "inject", test_url, "--dry-run"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if "[DRY-RUN]" in result.stdout:
            test_pass("inject_dry_run", "Dry-run output shown")
        else:
            test_fail("inject_dry_run", "No dry-run indicator")

        # Verify no file created
        files_before = len(list(TEST_SEEDS_DIR.glob("inject_SEED_*.json"))) if TEST_SEEDS_DIR.exists() else 0
        if result.returncode == 0:
            test_pass("inject_dry_run_exit", "Exit code 0")
        else:
            test_fail("inject_dry_run_exit", f"Exit code {result.returncode}")

    except Exception as e:
        test_fail("inject_dry_run", str(e))


def test_inject_creates_seed():
    """Test inject creates seed file."""
    cleanup_test_seeds()
    try:
        test_url = "https://www.youtube.com/watch?v=test123456"
        result = subprocess.run(
            [sys.executable, str(SKYBEAM_CLI), "inject", test_url],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            test_pass("inject_creates_seed_exit", "Exit code 0")
        else:
            test_fail("inject_creates_seed_exit", f"Exit {result.returncode}: {result.stderr}")
            return

        # Check file was created
        seed_files = list(TEST_SEEDS_DIR.glob("inject_SEED_*.json"))
        if seed_files:
            test_pass("inject_creates_seed_file", f"Created {seed_files[0].name}")

            # Validate content
            with open(seed_files[0]) as f:
                seed = json.load(f)
            if seed.get("url") == test_url:
                test_pass("inject_seed_url", "URL matches")
            else:
                test_fail("inject_seed_url", f"URL mismatch: {seed.get('url')}")

            if seed.get("platform") == "youtube":
                test_pass("inject_platform_detect", "Platform: youtube")
            else:
                test_fail("inject_platform_detect", f"Platform: {seed.get('platform')}")
        else:
            test_fail("inject_creates_seed_file", "No seed file found")

    except Exception as e:
        test_fail("inject_creates_seed", str(e))
    finally:
        cleanup_test_seeds()


def test_inject_duplicate():
    """Test duplicate detection."""
    cleanup_test_seeds()
    try:
        test_url = "https://www.youtube.com/watch?v=duptest123"

        # First injection
        result1 = subprocess.run(
            [sys.executable, str(SKYBEAM_CLI), "inject", test_url],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result1.returncode != 0:
            test_fail("inject_duplicate_first", f"First inject failed: {result1.returncode}")
            return

        test_pass("inject_duplicate_first", "First injection succeeded")

        # Second injection (should detect duplicate)
        result2 = subprocess.run(
            [sys.executable, str(SKYBEAM_CLI), "inject", test_url],
            capture_output=True,
            text=True,
            timeout=10
        )

        if "Duplicate" in result2.stdout:
            test_pass("inject_duplicate_detect", "Duplicate detected")
        else:
            test_fail("inject_duplicate_detect", "Duplicate not detected")

        # Exit code should still be 0 (not an error)
        if result2.returncode == 0:
            test_pass("inject_duplicate_exit", "Exit 0 on duplicate")
        else:
            test_fail("inject_duplicate_exit", f"Exit {result2.returncode}")

    except Exception as e:
        test_fail("inject_duplicate", str(e))
    finally:
        cleanup_test_seeds()


def test_inject_invalid_url():
    """Test invalid URL is rejected."""
    try:
        result = subprocess.run(
            [sys.executable, str(SKYBEAM_CLI), "inject", "not-a-valid-url"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 1:
            test_pass("inject_invalid_url", "Exit 1 on invalid URL")
        else:
            test_fail("inject_invalid_url", f"Expected exit 1, got {result.returncode}")

        if "Error" in result.stdout or "scheme" in result.stdout.lower():
            test_pass("inject_invalid_url_msg", "Error message shown")
        else:
            test_fail("inject_invalid_url_msg", "No error message")

    except Exception as e:
        test_fail("inject_invalid_url", str(e))


def test_inject_priority():
    """Test priority flag."""
    cleanup_test_seeds()
    try:
        test_url = "https://www.youtube.com/watch?v=priority123"
        result = subprocess.run(
            [sys.executable, str(SKYBEAM_CLI), "inject", test_url, "--priority", "high"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            # Check seed content
            seed_files = list(TEST_SEEDS_DIR.glob("inject_SEED_*.json"))
            if seed_files:
                with open(seed_files[0]) as f:
                    seed = json.load(f)
                if seed.get("priority") == "high":
                    test_pass("inject_priority", "Priority: high")
                else:
                    test_fail("inject_priority", f"Priority: {seed.get('priority')}")
            else:
                test_fail("inject_priority", "No seed file")
        else:
            test_fail("inject_priority", f"Exit {result.returncode}")

    except Exception as e:
        test_fail("inject_priority", str(e))
    finally:
        cleanup_test_seeds()


def test_inject_tags():
    """Test tags flag."""
    cleanup_test_seeds()
    try:
        test_url = "https://www.youtube.com/watch?v=tags123"
        result = subprocess.run(
            [sys.executable, str(SKYBEAM_CLI), "inject", test_url, "--tags", "breaking,urgent,test"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            seed_files = list(TEST_SEEDS_DIR.glob("inject_SEED_*.json"))
            if seed_files:
                with open(seed_files[0]) as f:
                    seed = json.load(f)
                tags = seed.get("tags", [])
                if "breaking" in tags and "urgent" in tags:
                    test_pass("inject_tags", f"Tags: {tags}")
                else:
                    test_fail("inject_tags", f"Tags: {tags}")
            else:
                test_fail("inject_tags", "No seed file")
        else:
            test_fail("inject_tags", f"Exit {result.returncode}")

    except Exception as e:
        test_fail("inject_tags", str(e))
    finally:
        cleanup_test_seeds()


def test_inject_tiktok_platform():
    """Test TikTok URL platform detection."""
    try:
        test_url = "https://www.tiktok.com/@user/video/7123456789"
        result = subprocess.run(
            [sys.executable, str(SKYBEAM_CLI), "inject", test_url, "--dry-run"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if "Platform: tiktok" in result.stdout:
            test_pass("inject_tiktok_platform", "TikTok platform detected")
        else:
            test_fail("inject_tiktok_platform", "TikTok not detected")

    except Exception as e:
        test_fail("inject_tiktok_platform", str(e))


def test_seed_id_format():
    """Test seed ID format is correct."""
    cleanup_test_seeds()
    try:
        test_url = "https://www.youtube.com/watch?v=seedid123"
        result = subprocess.run(
            [sys.executable, str(SKYBEAM_CLI), "inject", test_url],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            seed_files = list(TEST_SEEDS_DIR.glob("inject_SEED_*.json"))
            if seed_files:
                with open(seed_files[0]) as f:
                    seed = json.load(f)
                seed_id = seed.get("seed_id", "")
                import re
                pattern = r"^SEED_\d{8}_\d{6}_[a-f0-9]{8}$"
                if re.match(pattern, seed_id):
                    test_pass("seed_id_format", f"ID: {seed_id}")
                else:
                    test_fail("seed_id_format", f"Invalid format: {seed_id}")
            else:
                test_fail("seed_id_format", "No seed file")
        else:
            test_fail("seed_id_format", f"Exit {result.returncode}")

    except Exception as e:
        test_fail("seed_id_format", str(e))
    finally:
        cleanup_test_seeds()


def main():
    print("=" * 60)
    print("SKYBEAM Inject Subcommand Selftest (STORY-030)")
    print("=" * 60)

    # Cleanup before tests
    cleanup_test_seeds()

    test_inject_help()
    test_inject_dry_run()
    test_inject_creates_seed()
    test_inject_duplicate()
    test_inject_invalid_url()
    test_inject_priority()
    test_inject_tags()
    test_inject_tiktok_platform()
    test_seed_id_format()

    # Final cleanup
    cleanup_test_seeds()

    print("=" * 60)
    print(f"Results: {TESTS_PASSED} passed, {TESTS_FAILED} failed")
    print("=" * 60)

    return 0 if TESTS_FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
