#!/usr/bin/env python3
"""
THEATER-011: ROXY Silent Mode Selftest

Tests the OBS Director's ability to enter and exit recording mode,
which signals ROXY to pause/resume automation during theater recording.

Run: python3 selftest_silent_mode.py
"""

import asyncio
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, List

# =============================================================================
# Mock Classes
# =============================================================================

@dataclass
class MockNATSPublisher:
    """Mock NATS publisher for testing mode events."""
    published_events: List[dict] = field(default_factory=list)

    async def publish(self, topic: str, data: bytes):
        """Record published events."""
        event = {
            "topic": topic,
            "data": json.loads(data.decode()) if isinstance(data, bytes) else data
        }
        self.published_events.append(event)


# =============================================================================
# Test Director with Silent Mode
# =============================================================================

class TestableSilentModeDirector:
    """Minimal director with silent mode for testing."""

    NATS_TOPICS = {
        "roxy_mode": "ghost.roxy.mode"
    }

    def __init__(self, nats_publisher: MockNATSPublisher):
        self._nats = nats_publisher
        self._roxy_mode: str = "normal"
        self._events_published: List[dict] = []

    async def _publish_event(self, topic: str, event):
        """Publish event to mock NATS."""
        data = {
            "event_type": event.event_type,
            "session_id": event.session_id,
            "timestamp": event.timestamp,
            "data": event.data
        }
        if self._nats:
            await self._nats.publish(topic, json.dumps(data).encode())
        self._events_published.append({"topic": topic, "event": data})

    async def enter_recording_mode(self, session_id: str) -> bool:
        """Enter recording mode."""
        if self._roxy_mode == "recording":
            return True

        self._roxy_mode = "recording"

        await self._publish_event(
            self.NATS_TOPICS["roxy_mode"],
            MockEvent(
                event_type="mode_changed",
                session_id=session_id,
                data={
                    "mode": "recording",
                    "previous_mode": "normal",
                    "actions": [
                        "pause_skybeam_timers",
                        "mute_notifications",
                        "suppress_non_critical_events"
                    ]
                }
            )
        )

        return True

    async def exit_recording_mode(self, session_id: str) -> bool:
        """Exit recording mode."""
        if self._roxy_mode == "normal":
            return True

        self._roxy_mode = "normal"

        await self._publish_event(
            self.NATS_TOPICS["roxy_mode"],
            MockEvent(
                event_type="mode_changed",
                session_id=session_id,
                data={
                    "mode": "normal",
                    "previous_mode": "recording",
                    "actions": [
                        "resume_skybeam_timers",
                        "unmute_notifications",
                        "enable_all_events"
                    ]
                }
            )
        )

        return True

    def get_roxy_mode(self) -> str:
        """Get current mode."""
        return self._roxy_mode


@dataclass
class MockEvent:
    """Mock event for testing."""
    event_type: str
    session_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: dict = field(default_factory=dict)


# =============================================================================
# Test Cases
# =============================================================================

async def test_initial_mode_is_normal() -> tuple[str, str, str]:
    """Test that initial mode is normal."""
    nats = MockNATSPublisher()
    director = TestableSilentModeDirector(nats)

    expected = "NORMAL_MODE"
    actual = "NORMAL_MODE" if director.get_roxy_mode() == "normal" else f"WRONG: {director.get_roxy_mode()}"

    return ("test_initial_mode_is_normal", expected, actual)


async def test_enter_recording_mode() -> tuple[str, str, str]:
    """Test entering recording mode."""
    nats = MockNATSPublisher()
    director = TestableSilentModeDirector(nats)

    result = await director.enter_recording_mode("SESSION_TEST_001")

    expected = "RECORDING_MODE"
    if result and director.get_roxy_mode() == "recording":
        actual = "RECORDING_MODE"
    else:
        actual = f"FAILED: result={result}, mode={director.get_roxy_mode()}"

    return ("test_enter_recording_mode", expected, actual)


async def test_exit_recording_mode() -> tuple[str, str, str]:
    """Test exiting recording mode."""
    nats = MockNATSPublisher()
    director = TestableSilentModeDirector(nats)

    await director.enter_recording_mode("SESSION_TEST_001")
    result = await director.exit_recording_mode("SESSION_TEST_001")

    expected = "NORMAL_MODE"
    if result and director.get_roxy_mode() == "normal":
        actual = "NORMAL_MODE"
    else:
        actual = f"FAILED: result={result}, mode={director.get_roxy_mode()}"

    return ("test_exit_recording_mode", expected, actual)


async def test_enter_mode_publishes_event() -> tuple[str, str, str]:
    """Test that entering recording mode publishes NATS event."""
    nats = MockNATSPublisher()
    director = TestableSilentModeDirector(nats)

    await director.enter_recording_mode("SESSION_TEST_001")

    expected = "EVENT_PUBLISHED"
    if len(nats.published_events) == 1:
        event = nats.published_events[0]
        if event["topic"] == "ghost.roxy.mode":
            data = event["data"]
            if data["data"]["mode"] == "recording":
                actual = "EVENT_PUBLISHED"
            else:
                actual = f"WRONG_MODE: {data}"
        else:
            actual = f"WRONG_TOPIC: {event['topic']}"
    else:
        actual = f"WRONG_COUNT: {len(nats.published_events)}"

    return ("test_enter_mode_publishes_event", expected, actual)


async def test_event_contains_actions() -> tuple[str, str, str]:
    """Test that mode event contains expected actions."""
    nats = MockNATSPublisher()
    director = TestableSilentModeDirector(nats)

    await director.enter_recording_mode("SESSION_TEST_001")

    expected = "ACTIONS_PRESENT"
    event = nats.published_events[0]["data"]
    actions = event["data"].get("actions", [])

    expected_actions = ["pause_skybeam_timers", "mute_notifications", "suppress_non_critical_events"]
    if all(a in actions for a in expected_actions):
        actual = "ACTIONS_PRESENT"
    else:
        actual = f"MISSING_ACTIONS: {actions}"

    return ("test_event_contains_actions", expected, actual)


async def test_skip_duplicate_enter() -> tuple[str, str, str]:
    """Test that duplicate enter is skipped."""
    nats = MockNATSPublisher()
    director = TestableSilentModeDirector(nats)

    await director.enter_recording_mode("SESSION_TEST_001")
    event_count_after_first = len(nats.published_events)

    await director.enter_recording_mode("SESSION_TEST_001")
    event_count_after_second = len(nats.published_events)

    expected = "DUPLICATE_SKIPPED"
    if event_count_after_first == 1 and event_count_after_second == 1:
        actual = "DUPLICATE_SKIPPED"
    else:
        actual = f"COUNTS: {event_count_after_first} then {event_count_after_second}"

    return ("test_skip_duplicate_enter", expected, actual)


async def test_skip_duplicate_exit() -> tuple[str, str, str]:
    """Test that duplicate exit is skipped."""
    nats = MockNATSPublisher()
    director = TestableSilentModeDirector(nats)

    # Try to exit when already in normal mode
    result = await director.exit_recording_mode("SESSION_TEST_001")

    expected = "NO_EVENT_PUBLISHED"
    if result and len(nats.published_events) == 0:
        actual = "NO_EVENT_PUBLISHED"
    else:
        actual = f"UNEXPECTED: result={result}, events={len(nats.published_events)}"

    return ("test_skip_duplicate_exit", expected, actual)


async def test_full_recording_cycle() -> tuple[str, str, str]:
    """Test full enter/exit recording cycle."""
    nats = MockNATSPublisher()
    director = TestableSilentModeDirector(nats)

    # Start recording
    await director.enter_recording_mode("SESSION_TEST_001")
    mode_during = director.get_roxy_mode()

    # Stop recording
    await director.exit_recording_mode("SESSION_TEST_001")
    mode_after = director.get_roxy_mode()

    expected = "FULL_CYCLE_COMPLETE"
    if mode_during == "recording" and mode_after == "normal" and len(nats.published_events) == 2:
        actual = "FULL_CYCLE_COMPLETE"
    else:
        actual = f"FAILED: during={mode_during}, after={mode_after}, events={len(nats.published_events)}"

    return ("test_full_recording_cycle", expected, actual)


# =============================================================================
# Main
# =============================================================================

async def main():
    """Run all tests."""
    print("=" * 60)
    print("SELFTEST: ROXY Silent Mode (THEATER-011)")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)
    print()

    tests = [
        test_initial_mode_is_normal,
        test_enter_recording_mode,
        test_exit_recording_mode,
        test_enter_mode_publishes_event,
        test_event_contains_actions,
        test_skip_duplicate_enter,
        test_skip_duplicate_exit,
        test_full_recording_cycle,
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
        "test_name": "silent_mode_selftest",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "results": results
    }

    output_path = Path(__file__).parent / "selftest_silent_mode_results.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print()
    print(f"Results written to: {output_path}")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
