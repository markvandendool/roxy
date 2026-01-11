#!/usr/bin/env python3
"""
THEATER-010: Scene Switching Selftest

Tests the OBS Director's ability to switch scenes based on preset changes.
Uses mock OBS client to verify scene switching logic without real OBS.

Run: python3 selftest_scene_switching.py
"""

import asyncio
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# =============================================================================
# Mock Classes
# =============================================================================

@dataclass
class MockOBSClient:
    """Mock OBS client for testing scene switching."""
    connected: bool = True
    current_scene: str = ""
    switch_calls: list = field(default_factory=list)
    should_fail: bool = False

    async def switch_scene(self, scene_name: str) -> dict:
        """Mock scene switch."""
        self.switch_calls.append(scene_name)
        if self.should_fail:
            return {"success": False, "error": "Mock failure"}
        self.current_scene = scene_name
        return {"success": True, "scene": scene_name}

    async def disconnect(self):
        """Mock disconnect."""
        self.connected = False


# =============================================================================
# Test OBS Director with Scene Switching
# =============================================================================

class TestableDirector:
    """Minimal director with scene switching for testing."""

    def __init__(self, preset_mapping: dict, obs_client: MockOBSClient):
        self._preset_mapping = preset_mapping
        self._obs_client = obs_client
        self._current_preset: Optional[str] = None
        self._events_published: list = []

    async def switch_scene_for_preset(
        self,
        preset: str,
        orientation: str = "landscape"
    ) -> bool:
        """Switch OBS scene based on theater preset."""
        if not self._obs_client or not self._obs_client.connected:
            return False

        preset_config = self._preset_mapping.get(preset)
        if not preset_config:
            return False

        scene_key = f"obs_scene_{orientation}"
        scene_name = preset_config.get(scene_key)
        if not scene_name:
            return False

        if self._current_preset == preset:
            return True

        try:
            result = await self._obs_client.switch_scene(scene_name)
            if result.get("success"):
                self._current_preset = preset
                self._events_published.append({
                    "type": "scene_switched",
                    "preset": preset,
                    "scene": scene_name,
                    "orientation": orientation
                })
                return True
            return False
        except Exception:
            return False


# =============================================================================
# Test Cases
# =============================================================================

PRESET_MAPPING = {
    "analysis": {
        "obs_scene_landscape": "MindSong Analysis 8K",
        "obs_scene_portrait": "MindSong Analysis Portrait"
    },
    "performance": {
        "obs_scene_landscape": "MindSong Performance 8K",
        "obs_scene_portrait": "MindSong Performance Portrait"
    },
    "teaching": {
        "obs_scene_landscape": "MindSong Teaching 8K",
        "obs_scene_portrait": "MindSong Teaching Portrait"
    },
    "minimal": {
        "obs_scene_landscape": "MindSong Minimal 8K",
        "obs_scene_portrait": "MindSong Minimal Portrait"
    },
    "composer": {
        "obs_scene_landscape": "MindSong Composer 8K",
        "obs_scene_portrait": "MindSong Composer Portrait"
    }
}


async def test_switch_landscape_scene() -> tuple[str, str, str]:
    """Test switching to landscape scene."""
    obs = MockOBSClient()
    director = TestableDirector(PRESET_MAPPING, obs)

    result = await director.switch_scene_for_preset("performance", "landscape")

    expected = "SCENE_SWITCHED"
    if result and obs.current_scene == "MindSong Performance 8K":
        actual = "SCENE_SWITCHED"
    else:
        actual = f"FAILED: {obs.current_scene}"

    return ("test_switch_landscape_scene", expected, actual)


async def test_switch_portrait_scene() -> tuple[str, str, str]:
    """Test switching to portrait scene."""
    obs = MockOBSClient()
    director = TestableDirector(PRESET_MAPPING, obs)

    result = await director.switch_scene_for_preset("analysis", "portrait")

    expected = "SCENE_SWITCHED"
    if result and obs.current_scene == "MindSong Analysis Portrait":
        actual = "SCENE_SWITCHED"
    else:
        actual = f"FAILED: {obs.current_scene}"

    return ("test_switch_portrait_scene", expected, actual)


async def test_all_presets_landscape() -> tuple[str, str, str]:
    """Test that all presets have valid landscape mappings."""
    obs = MockOBSClient()
    director = TestableDirector(PRESET_MAPPING, obs)

    presets = ["analysis", "performance", "teaching", "minimal", "composer"]
    failed = []

    for preset in presets:
        director._current_preset = None  # Reset
        result = await director.switch_scene_for_preset(preset, "landscape")
        if not result:
            failed.append(preset)

    expected = "ALL_PRESETS_VALID"
    if not failed:
        actual = "ALL_PRESETS_VALID"
    else:
        actual = f"FAILED: {failed}"

    return ("test_all_presets_landscape", expected, actual)


async def test_skip_duplicate_switch() -> tuple[str, str, str]:
    """Test that switching to same preset is skipped."""
    obs = MockOBSClient()
    director = TestableDirector(PRESET_MAPPING, obs)

    # First switch
    await director.switch_scene_for_preset("performance", "landscape")
    call_count_after_first = len(obs.switch_calls)

    # Second switch to same preset (should be skipped)
    await director.switch_scene_for_preset("performance", "landscape")
    call_count_after_second = len(obs.switch_calls)

    expected = "DUPLICATE_SKIPPED"
    if call_count_after_first == 1 and call_count_after_second == 1:
        actual = "DUPLICATE_SKIPPED"
    else:
        actual = f"CALLS: {call_count_after_first} then {call_count_after_second}"

    return ("test_skip_duplicate_switch", expected, actual)


async def test_invalid_preset() -> tuple[str, str, str]:
    """Test handling of invalid preset name."""
    obs = MockOBSClient()
    director = TestableDirector(PRESET_MAPPING, obs)

    result = await director.switch_scene_for_preset("nonexistent_preset", "landscape")

    expected = "GRACEFUL_FAILURE"
    if not result and len(obs.switch_calls) == 0:
        actual = "GRACEFUL_FAILURE"
    else:
        actual = f"UNEXPECTED: result={result}, calls={len(obs.switch_calls)}"

    return ("test_invalid_preset", expected, actual)


async def test_obs_disconnected() -> tuple[str, str, str]:
    """Test handling when OBS is disconnected."""
    obs = MockOBSClient(connected=False)
    director = TestableDirector(PRESET_MAPPING, obs)

    result = await director.switch_scene_for_preset("performance", "landscape")

    expected = "GRACEFUL_FAILURE"
    if not result:
        actual = "GRACEFUL_FAILURE"
    else:
        actual = "UNEXPECTED_SUCCESS"

    return ("test_obs_disconnected", expected, actual)


async def test_obs_switch_failure() -> tuple[str, str, str]:
    """Test handling when OBS switch fails."""
    obs = MockOBSClient(should_fail=True)
    director = TestableDirector(PRESET_MAPPING, obs)

    result = await director.switch_scene_for_preset("performance", "landscape")

    expected = "FAILURE_HANDLED"
    if not result and director._current_preset is None:
        actual = "FAILURE_HANDLED"
    else:
        actual = f"UNEXPECTED: result={result}, preset={director._current_preset}"

    return ("test_obs_switch_failure", expected, actual)


async def test_event_published() -> tuple[str, str, str]:
    """Test that scene switch publishes event."""
    obs = MockOBSClient()
    director = TestableDirector(PRESET_MAPPING, obs)

    await director.switch_scene_for_preset("teaching", "landscape")

    expected = "EVENT_PUBLISHED"
    if len(director._events_published) == 1:
        event = director._events_published[0]
        if (event["type"] == "scene_switched" and
            event["preset"] == "teaching" and
            event["scene"] == "MindSong Teaching 8K"):
            actual = "EVENT_PUBLISHED"
        else:
            actual = f"WRONG_EVENT: {event}"
    else:
        actual = f"NO_EVENT: {director._events_published}"

    return ("test_event_published", expected, actual)


# =============================================================================
# Main
# =============================================================================

async def main():
    """Run all tests."""
    print("=" * 60)
    print("SELFTEST: Scene Switching (THEATER-010)")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)
    print()

    tests = [
        test_switch_landscape_scene,
        test_switch_portrait_scene,
        test_all_presets_landscape,
        test_skip_duplicate_switch,
        test_invalid_preset,
        test_obs_disconnected,
        test_obs_switch_failure,
        test_event_published,
    ]

    results = []
    passed = 0
    failed = 0

    for test in tests:
        name, expected, actual = await test()
        status = "PASS" if expected == actual else "FAIL"
        results.append({
            "name": name,
            "status": status,
            "expected": expected,
            "actual": actual
        })

        if status == "PASS":
            passed += 1
            print(f"[PASS] {name}: expected={expected}, actual={actual}")
        else:
            failed += 1
            print(f"[FAIL] {name}: expected={expected}, actual={actual}")

    print()
    print("=" * 60)
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print("=" * 60)

    # Write results
    output = {
        "test_name": "scene_switching_selftest",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "results": results
    }

    output_path = Path(__file__).parent / "selftest_scene_switching_results.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print()
    print(f"Results written to: {output_path}")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
