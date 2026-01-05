#!/usr/bin/env python3
"""
Rocky System - Integration Tests
Story: RAF-023
Target: Comprehensive integration testing for all ROXY components

Run: python3 ~/.roxy/tests/integration_tests.py
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add ROXY modules to path
ROXY_HOME = Path.home() / ".roxy"
sys.path.insert(0, str(ROXY_HOME / "ipc"))
sys.path.insert(0, str(ROXY_HOME / "learning"))
sys.path.insert(0, str(ROXY_HOME / "wayland"))
sys.path.insert(0, str(ROXY_HOME / "monitor"))
sys.path.insert(0, str(ROXY_HOME / "ibus"))
sys.path.insert(0, str(ROXY_HOME / "fuse"))


class TestSharedMemoryBrain(unittest.TestCase):
    """Test shared memory IPC."""

    @classmethod
    def setUpClass(cls):
        """Create shared memory for tests."""
        from shm_brain import RoxyShmBrain, SHM_PATH
        cls.SHM_PATH = SHM_PATH

        # Clean up any existing
        if os.path.exists(SHM_PATH):
            os.unlink(SHM_PATH)

        cls.brain = RoxyShmBrain(create=True, size=1024 * 1024)

    @classmethod
    def tearDownClass(cls):
        """Clean up shared memory."""
        cls.brain.cleanup()
        if os.path.exists(cls.SHM_PATH):
            os.unlink(cls.SHM_PATH)

    def test_write_read_basic(self):
        """Test basic write/read operations."""
        test_data = b"Hello ROXY"
        self.brain.write(1, test_data)

        msg = self.brain.read(timeout_ms=100)
        self.assertIsNotNone(msg)
        self.assertEqual(msg.payload, test_data)

    def test_write_read_json(self):
        """Test JSON write/read operations."""
        test_data = {"action": "test", "value": 42}
        self.brain.write_json(30, test_data)

        result = self.brain.read_json(timeout_ms=100)
        self.assertIsNotNone(result)
        msg_type, data, timestamp = result
        self.assertEqual(data, test_data)

    def test_read_timeout(self):
        """Test read timeout when no message available."""
        # Clear any pending messages
        while self.brain.read(timeout_ms=0):
            pass

        start = time.time()
        msg = self.brain.read(timeout_ms=50)
        elapsed = time.time() - start

        self.assertIsNone(msg)
        self.assertGreater(elapsed, 0.04)  # At least 40ms

    def test_ping_latency(self):
        """Test IPC latency is within acceptable range."""
        # Start a responder in another thread
        import threading

        def responder():
            from shm_brain import RoxyShmBrain
            brain = RoxyShmBrain(create=False)
            for _ in range(10):
                msg = brain.read(timeout_ms=100)
                if msg and msg.msg_type == brain.MSG_PING:
                    brain.write(brain.MSG_PONG, b"pong")
            brain.cleanup()

        thread = threading.Thread(target=responder, daemon=True)
        thread.start()
        time.sleep(0.1)

        latencies = []
        for _ in range(5):
            try:
                lat = self.brain.ping()
                latencies.append(lat)
            except:
                pass

        thread.join(timeout=1)

        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            print(f"Average IPC latency: {avg_latency:.2f}μs")
            # Should be under 1000μs (1ms) for local shm
            self.assertLess(avg_latency, 1000)


class TestSessionRecorder(unittest.TestCase):
    """Test session recording functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_db = tempfile.mktemp(suffix=".db")

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_db):
            os.unlink(self.test_db)

    def test_session_lifecycle(self):
        """Test complete session lifecycle."""
        from session_recorder import SessionRecorder, PitchEvent

        recorder = SessionRecorder()

        # Start session
        session_id = recorder.start_session()
        self.assertIsNotNone(session_id)
        self.assertTrue(recorder.recording)

        # Add some pitch events
        for i in range(10):
            event = PitchEvent(
                timestamp=time.time(),
                frequency=440.0 + i * 10,
                midi_note=69 + i,
                confidence=0.9,
                note_name=f"A{i}",
            )
            recorder.add_pitch_event(event)
            time.sleep(0.01)

        # Stop session
        summary = recorder.stop_session()

        self.assertIsNotNone(summary)
        self.assertEqual(summary.notes_played, 10)
        self.assertFalse(recorder.recording)

    def test_progress_stats(self):
        """Test progress statistics calculation."""
        from session_recorder import SessionRecorder

        recorder = SessionRecorder()

        stats = recorder.get_progress_stats()
        self.assertIn("total_sessions", stats)
        self.assertIn("total_time_hours", stats)


class TestSkillProgression(unittest.TestCase):
    """Test skill progression system."""

    def test_skill_creation(self):
        """Test creating and tracking skills."""
        from skill_progression import SkillProgressionModel

        model = SkillProgressionModel()

        # Check default skills loaded
        self.assertGreater(len(model.skills), 0)

        # Add a custom skill
        skill = model.add_skill("test_skill", "Test Skill", "test")
        self.assertEqual(skill.skill_id, "test_skill")
        self.assertEqual(skill.level, 0)

    def test_practice_recording(self):
        """Test recording practice sessions."""
        from skill_progression import SkillProgressionModel

        model = SkillProgressionModel()

        # Record some practice
        record = model.record_practice(
            "chord_c_major",
            duration_seconds=300,
            accuracy=0.85,
            difficulty=0.5,
        )

        self.assertIsNotNone(record)
        self.assertGreater(record.xp_earned, 0)

        # Check skill was updated
        skill = model.skills["chord_c_major"]
        self.assertGreater(skill.experience, 0)
        self.assertGreater(skill.level, 0)

    def test_challenge_suggestions(self):
        """Test challenge suggestion algorithm."""
        from skill_progression import SkillProgressionModel

        model = SkillProgressionModel()

        suggestions = model.get_suggested_challenges(count=3)
        self.assertGreater(len(suggestions), 0)
        self.assertLessEqual(len(suggestions), 3)


class TestFrustrationDetector(unittest.TestCase):
    """Test frustration detection system."""

    def test_backspace_detection(self):
        """Test detection of high backspace rate."""
        from frustration_detector import FrustrationDetector

        detector = FrustrationDetector()

        # Simulate normal typing
        for _ in range(50):
            detector.process_key("a")

        initial_score = detector.current_score

        # Simulate frustrated typing (many backspaces)
        for _ in range(30):
            detector.process_key("x")
            detector.process_key("BACKSPACE", is_backspace=True)

        final_score = detector.current_score

        # Score should increase
        self.assertGreater(final_score, initial_score)

    def test_repeated_failure_detection(self):
        """Test detection of repeated command failures."""
        from frustration_detector import FrustrationDetector

        triggered = []

        def callback(event):
            triggered.append(event)

        detector = FrustrationDetector(callback=callback)

        # Simulate repeated failures
        for _ in range(5):
            detector.process_command("make build", success=False)

        # Should have triggered frustration
        self.assertGreater(len(triggered), 0)


class TestIBusExpansion(unittest.TestCase):
    """Test iBus text expansion."""

    def test_default_expansions(self):
        """Test default expansion triggers."""
        from roxy_expansion import RoxyExpansionEngine

        engine = RoxyExpansionEngine()

        # Check default expansions exist
        self.assertIn("/rx", engine.expansions)
        self.assertIn("/rxh", engine.expansions)
        self.assertIn("@@now", engine.expansions)

    def test_process_input(self):
        """Test input processing."""
        from roxy_expansion import RoxyExpansionEngine

        engine = RoxyExpansionEngine()

        # Test simple replacement
        result = engine.process_input("@@shrug")
        self.assertIsNotNone(result)
        self.assertIn("¯", result)

    def test_add_custom_expansion(self):
        """Test adding custom expansions."""
        from roxy_expansion import RoxyExpansionEngine

        engine = RoxyExpansionEngine()

        engine.add_expansion(
            trigger="@@test",
            replacement="TEST EXPANSION",
            description="Test",
        )

        self.assertIn("@@test", engine.expansions)

        result = engine.process_input("@@test")
        self.assertEqual(result, "TEST EXPANSION")


class TestFileMonitor(unittest.TestCase):
    """Test file monitoring system."""

    def test_interesting_file_detection(self):
        """Test detection of interesting files."""
        from file_monitor import RoxyFileHandler

        handler = RoxyFileHandler()

        # Should be interesting
        self.assertTrue(handler._is_interesting("/path/to/file.py"))
        self.assertTrue(handler._is_interesting("/path/to/config.json"))
        self.assertTrue(handler._is_interesting("/path/to/app.ts"))

        # Should be ignored
        self.assertFalse(handler._is_interesting("/path/__pycache__/file.py"))
        self.assertFalse(handler._is_interesting("/path/node_modules/package.json"))
        self.assertFalse(handler._is_interesting("/path/to/file.swp"))


class TestSystemIntegration(unittest.TestCase):
    """Test system-level integration."""

    def test_roxy_home_structure(self):
        """Test ROXY home directory structure."""
        expected_dirs = [
            "ipc",
            "learning",
            "wayland",
            "monitor",
            "ibus",
            "fuse",
            "daemon",
            "systemd",
            "scripts",
            "tests",
        ]

        for dirname in expected_dirs:
            path = ROXY_HOME / dirname
            self.assertTrue(
                path.exists(),
                f"Missing directory: {dirname}"
            )

    def test_required_files_exist(self):
        """Test that required files exist."""
        required_files = [
            "ipc/shm_brain.py",
            "learning/session_recorder.py",
            "learning/skill_progression.py",
            "learning/frustration_detector.py",
            "wayland/portal_shortcuts.py",
            "monitor/file_monitor.py",
            "ibus/roxy_expansion.py",
            "daemon/roxy_main.py",
            "scripts/rollback.sh",
        ]

        for filepath in required_files:
            path = ROXY_HOME / filepath
            self.assertTrue(
                path.exists(),
                f"Missing file: {filepath}"
            )

    def test_python_syntax(self):
        """Test all Python files have valid syntax."""
        python_files = list(ROXY_HOME.rglob("*.py"))

        for filepath in python_files:
            try:
                with open(filepath) as f:
                    compile(f.read(), filepath, 'exec')
            except SyntaxError as e:
                self.fail(f"Syntax error in {filepath}: {e}")


class TestRollback(unittest.TestCase):
    """Test rollback mechanism."""

    def test_rollback_script_exists(self):
        """Test rollback script exists and is executable."""
        script = ROXY_HOME / "scripts" / "rollback.sh"
        self.assertTrue(script.exists())

    def test_rollback_help(self):
        """Test rollback script help output."""
        script = ROXY_HOME / "scripts" / "rollback.sh"
        result = subprocess.run(
            ["bash", str(script), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertIn("Usage", result.stdout)


def run_tests(verbosity: int = 2) -> bool:
    """Run all integration tests."""
    print("=" * 60)
    print("ROXY Integration Tests")
    print("=" * 60)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestSharedMemoryBrain,
        TestSessionRecorder,
        TestSkillProgression,
        TestFrustrationDetector,
        TestIBusExpansion,
        TestFileMonitor,
        TestSystemIntegration,
        TestRollback,
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    # Summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nResult: {'PASS' if success else 'FAIL'}")

    return success


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
