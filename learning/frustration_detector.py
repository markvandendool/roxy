#!/usr/bin/env python3
"""
Rocky Learning - Frustration Detection
Story: RAF-013
Target: Detect user frustration via typing patterns, offer help

Analyzes typing patterns to detect frustration and proactively offer assistance.
"""

import asyncio
import json
import os
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional
import threading

# Configuration
ROXY_DATA = Path.home() / ".roxy" / "data"
FRUSTRATION_LOG = ROXY_DATA / "frustration_log.json"


@dataclass
class TypingEvent:
    """Single typing event."""
    timestamp: float
    key: str
    is_backspace: bool = False
    is_enter: bool = False
    interval_ms: float = 0  # Time since last key


@dataclass
class FrustrationMetrics:
    """Metrics indicating frustration level."""
    backspace_rate: float = 0  # Backspaces per minute
    typing_speed_variance: float = 0  # Variance in typing speed
    rapid_corrections: int = 0  # Quick backspace sequences
    repeated_commands: int = 0  # Same command repeated
    error_rate: float = 0  # Detected errors per minute
    session_duration: float = 0
    frustration_score: float = 0  # 0-100


@dataclass
class FrustrationEvent:
    """Detected frustration event."""
    timestamp: datetime
    score: float
    trigger: str  # What triggered the detection
    context: Dict = field(default_factory=dict)
    help_offered: bool = False


class FrustrationDetector:
    """
    Detects user frustration from typing patterns.

    Indicators:
    - High backspace rate (corrections)
    - Erratic typing speed
    - Repeated command failures
    - Rapid key sequences followed by deletions
    - Same error repeated multiple times
    """

    # Thresholds
    BACKSPACE_THRESHOLD = 30  # per minute
    RAPID_CORRECTION_THRESHOLD = 5  # in 10 seconds
    SPEED_VARIANCE_THRESHOLD = 3.0  # standard deviations
    FRUSTRATION_THRESHOLD = 60  # score 0-100

    def __init__(self, callback: Optional[Callable[[FrustrationEvent], None]] = None):
        self.callback = callback
        self.running = False

        # Event buffers
        self.events: deque = deque(maxlen=1000)
        self.intervals: deque = deque(maxlen=100)
        self.commands: deque = deque(maxlen=50)

        # State
        self.session_start = time.time()
        self.last_key_time = 0
        self.backspace_count = 0
        self.total_keys = 0
        self.rapid_corrections = 0
        self.last_rapid_check = time.time()

        # Frustration history
        self.frustration_events: List[FrustrationEvent] = []
        self.current_score = 0

        # Cooldown to avoid spam
        self.last_help_offered = 0
        self.help_cooldown = 60  # seconds

        ROXY_DATA.mkdir(parents=True, exist_ok=True)
        print("[ROXY.FRUSTRATION] Detector initialized")

    def process_key(self, key: str, is_backspace: bool = False, is_enter: bool = False):
        """Process a key event."""
        now = time.time()
        interval = (now - self.last_key_time) * 1000 if self.last_key_time else 0
        self.last_key_time = now

        event = TypingEvent(
            timestamp=now,
            key=key,
            is_backspace=is_backspace,
            is_enter=is_enter,
            interval_ms=interval,
        )
        self.events.append(event)

        # Track metrics
        self.total_keys += 1
        if is_backspace:
            self.backspace_count += 1

        if interval > 0:
            self.intervals.append(interval)

        # Check for rapid corrections
        self._check_rapid_corrections()

        # Calculate frustration score
        self._update_frustration_score()

    def process_command(self, command: str, success: bool):
        """Process a command execution."""
        self.commands.append({
            "cmd": command,
            "success": success,
            "time": time.time(),
        })

        # Check for repeated failed commands
        self._check_repeated_failures()

    def _check_rapid_corrections(self):
        """Check for rapid backspace sequences."""
        now = time.time()
        if now - self.last_rapid_check < 1:
            return

        self.last_rapid_check = now

        # Count backspaces in last 10 seconds
        cutoff = now - 10
        recent_backspaces = sum(
            1 for e in self.events
            if e.timestamp > cutoff and e.is_backspace
        )

        if recent_backspaces >= self.RAPID_CORRECTION_THRESHOLD:
            self.rapid_corrections += 1

    def _check_repeated_failures(self):
        """Check for repeated command failures."""
        if len(self.commands) < 3:
            return

        # Get last 3 failed commands
        recent = list(self.commands)[-5:]
        failed = [c for c in recent if not c["success"]]

        if len(failed) >= 3:
            # Check if same command repeated
            cmds = [c["cmd"].split()[0] if c["cmd"] else "" for c in failed]
            if len(set(cmds)) == 1:
                self._trigger_frustration(
                    "repeated_failure",
                    {"command": cmds[0], "count": len(failed)}
                )

    def _update_frustration_score(self):
        """Calculate current frustration score."""
        now = time.time()
        session_duration = now - self.session_start
        if session_duration < 10:
            return

        # Calculate metrics
        metrics = self.get_metrics()

        # Score components (each 0-25)
        backspace_score = min(25, (metrics.backspace_rate / self.BACKSPACE_THRESHOLD) * 25)
        variance_score = min(25, (metrics.typing_speed_variance / self.SPEED_VARIANCE_THRESHOLD) * 25)
        correction_score = min(25, (metrics.rapid_corrections / 5) * 25)
        error_score = min(25, (metrics.error_rate / 10) * 25)

        self.current_score = backspace_score + variance_score + correction_score + error_score
        metrics.frustration_score = self.current_score

        # Check threshold
        if self.current_score >= self.FRUSTRATION_THRESHOLD:
            self._trigger_frustration("high_score", {"score": self.current_score})

    def _trigger_frustration(self, trigger: str, context: Dict):
        """Handle frustration detection."""
        now = time.time()

        # Check cooldown
        if now - self.last_help_offered < self.help_cooldown:
            return

        event = FrustrationEvent(
            timestamp=datetime.now(),
            score=self.current_score,
            trigger=trigger,
            context=context,
        )

        self.frustration_events.append(event)
        print(f"[ROXY.FRUSTRATION] Detected: {trigger} (score: {self.current_score:.1f})")

        # Invoke callback
        if self.callback:
            self.callback(event)
            event.help_offered = True
            self.last_help_offered = now

        # Log event
        self._log_event(event)

    def _log_event(self, event: FrustrationEvent):
        """Log frustration event to file."""
        log_entry = {
            "timestamp": event.timestamp.isoformat(),
            "score": event.score,
            "trigger": event.trigger,
            "context": event.context,
            "help_offered": event.help_offered,
        }

        # Append to log file
        logs = []
        if FRUSTRATION_LOG.exists():
            try:
                with open(FRUSTRATION_LOG) as f:
                    logs = json.load(f)
            except:
                pass

        logs.append(log_entry)

        # Keep last 1000 entries
        logs = logs[-1000:]

        with open(FRUSTRATION_LOG, "w") as f:
            json.dump(logs, f, indent=2)

    def get_metrics(self) -> FrustrationMetrics:
        """Get current frustration metrics."""
        now = time.time()
        session_duration = now - self.session_start

        # Backspace rate (per minute)
        if session_duration > 0:
            backspace_rate = (self.backspace_count / session_duration) * 60
        else:
            backspace_rate = 0

        # Typing speed variance
        if len(self.intervals) > 10:
            import statistics
            mean = statistics.mean(self.intervals)
            stdev = statistics.stdev(self.intervals)
            variance = stdev / mean if mean > 0 else 0
        else:
            variance = 0

        # Error rate (failed commands per minute)
        failed = sum(1 for c in self.commands if not c["success"])
        error_rate = (failed / session_duration) * 60 if session_duration > 0 else 0

        return FrustrationMetrics(
            backspace_rate=backspace_rate,
            typing_speed_variance=variance,
            rapid_corrections=self.rapid_corrections,
            repeated_commands=len(self.commands),
            error_rate=error_rate,
            session_duration=session_duration,
            frustration_score=self.current_score,
        )

    def reset_session(self):
        """Reset session metrics."""
        self.session_start = time.time()
        self.events.clear()
        self.intervals.clear()
        self.commands.clear()
        self.backspace_count = 0
        self.total_keys = 0
        self.rapid_corrections = 0
        self.current_score = 0

    def get_help_suggestion(self, event: FrustrationEvent) -> str:
        """Generate a help suggestion based on frustration trigger."""
        suggestions = {
            "repeated_failure": (
                f"I noticed you're having trouble with '{event.context.get('command', 'a command')}'. "
                "Would you like me to help troubleshoot?"
            ),
            "high_score": (
                "It looks like things might be getting frustrating. "
                "Would you like to take a short break or would some help be useful?"
            ),
            "rapid_corrections": (
                "I see a lot of corrections. If you're debugging something tricky, "
                "I'm happy to take a look."
            ),
        }

        return suggestions.get(event.trigger, "Need any help?")


class EvdevMonitor:
    """
    Monitor keyboard via evdev (Linux input subsystem).

    Requires read access to /dev/input devices.
    """

    def __init__(self, detector: FrustrationDetector):
        self.detector = detector
        self.running = False

    async def start(self):
        """Start monitoring keyboard input."""
        try:
            import evdev
            from evdev import ecodes
        except ImportError:
            print("[ROXY.FRUSTRATION] evdev not installed")
            print("Run: pip install evdev")
            return

        # Find keyboard devices
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        keyboards = [d for d in devices if ecodes.EV_KEY in d.capabilities()]

        if not keyboards:
            print("[ROXY.FRUSTRATION] No keyboard devices found")
            return

        print(f"[ROXY.FRUSTRATION] Monitoring {len(keyboards)} keyboard(s)")
        self.running = True

        async def monitor_device(device):
            async for event in device.async_read_loop():
                if not self.running:
                    break

                if event.type == ecodes.EV_KEY and event.value == 1:  # Key press
                    key_name = ecodes.KEY.get(event.code, f"KEY_{event.code}")
                    is_backspace = event.code == ecodes.KEY_BACKSPACE
                    is_enter = event.code == ecodes.KEY_ENTER

                    self.detector.process_key(key_name, is_backspace, is_enter)

        # Monitor all keyboards
        tasks = [monitor_device(kb) for kb in keyboards]
        await asyncio.gather(*tasks)

    def stop(self):
        """Stop monitoring."""
        self.running = False


async def demo():
    """Demo the frustration detector."""
    def on_frustration(event):
        suggestion = detector.get_help_suggestion(event)
        print(f"\n[ROXY] {suggestion}\n")

    detector = FrustrationDetector(callback=on_frustration)

    # Simulate some typing
    print("[ROXY.FRUSTRATION] Simulating typing session...")

    # Normal typing
    for _ in range(50):
        detector.process_key("a")
        await asyncio.sleep(0.1)

    print(f"After normal typing: score = {detector.current_score:.1f}")

    # Simulate frustration - lots of backspaces
    for _ in range(30):
        detector.process_key("x")
        detector.process_key("BACKSPACE", is_backspace=True)
        await asyncio.sleep(0.05)

    print(f"After corrections: score = {detector.current_score:.1f}")

    # Simulate repeated failures
    for _ in range(5):
        detector.process_command("make build", success=False)
        await asyncio.sleep(0.5)

    print(f"After failures: score = {detector.current_score:.1f}")

    # Show metrics
    metrics = detector.get_metrics()
    print(f"\n[ROXY.FRUSTRATION] Session Metrics:")
    print(f"  Backspace rate: {metrics.backspace_rate:.1f}/min")
    print(f"  Speed variance: {metrics.typing_speed_variance:.2f}")
    print(f"  Rapid corrections: {metrics.rapid_corrections}")
    print(f"  Error rate: {metrics.error_rate:.1f}/min")
    print(f"  Frustration score: {metrics.frustration_score:.1f}")


if __name__ == "__main__":
    asyncio.run(demo())
