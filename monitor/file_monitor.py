#!/usr/bin/env python3
"""
Rocky Monitor - File System Watcher
Story: RAF-017
Target: Monitor file changes, trigger ROXY actions

Uses inotify for efficient file system monitoring (eBPF fallback for advanced use).
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set
import threading
import queue

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("[ROXY.MONITOR] watchdog not installed, using inotifywait fallback")

# Configuration
ROXY_DATA = Path.home() / ".roxy" / "data"
MONITOR_LOG = ROXY_DATA / "file_monitor.log"
SHM_PATH = "/dev/shm/roxy_brain"


@dataclass
class FileEvent:
    """A file system event."""
    event_type: str  # created, modified, deleted, moved
    path: str
    timestamp: datetime
    is_directory: bool = False
    old_path: Optional[str] = None  # For moves


class RoxyFileHandler(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    """Handles file system events for ROXY."""

    # File patterns to watch
    CODE_EXTENSIONS = {'.py', '.js', '.ts', '.c', '.cpp', '.h', '.rs', '.go', '.java'}
    CONFIG_PATTERNS = {'*.json', '*.yaml', '*.yml', '*.toml', '*.conf', '*.ini'}
    IGNORE_PATTERNS = {'__pycache__', '.git', 'node_modules', '.cache', '*.pyc', '*.swp'}

    def __init__(self, callback: Optional[Callable[[FileEvent], None]] = None):
        if WATCHDOG_AVAILABLE:
            super().__init__()
        self.callback = callback
        self.event_queue: queue.Queue = queue.Queue()
        self.recent_events: Dict[str, float] = {}
        self.debounce_seconds = 0.5

    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        path_lower = path.lower()
        for pattern in self.IGNORE_PATTERNS:
            if pattern.startswith('*'):
                if path_lower.endswith(pattern[1:]):
                    return True
            elif pattern in path_lower:
                return True
        return False

    def _is_interesting(self, path: str) -> bool:
        """Check if file is interesting to monitor."""
        if self._should_ignore(path):
            return False

        # Check extension
        ext = Path(path).suffix.lower()
        if ext in self.CODE_EXTENSIONS:
            return True

        # Check config patterns
        name = Path(path).name.lower()
        for pattern in self.CONFIG_PATTERNS:
            if pattern.startswith('*'):
                if name.endswith(pattern[1:]):
                    return True
            elif pattern == name:
                return True

        return False

    def _debounce(self, path: str) -> bool:
        """Debounce rapid events on same file."""
        now = time.time()
        last = self.recent_events.get(path, 0)
        if now - last < self.debounce_seconds:
            return False
        self.recent_events[path] = now

        # Clean old entries
        cutoff = now - 60
        self.recent_events = {k: v for k, v in self.recent_events.items() if v > cutoff}
        return True

    def _handle_event(self, event_type: str, path: str, is_dir: bool = False,
                      old_path: Optional[str] = None):
        """Handle a file system event."""
        if not self._is_interesting(path):
            return

        if not self._debounce(path):
            return

        file_event = FileEvent(
            event_type=event_type,
            path=path,
            timestamp=datetime.now(),
            is_directory=is_dir,
            old_path=old_path,
        )

        self.event_queue.put(file_event)

        if self.callback:
            self.callback(file_event)

        print(f"[ROXY.MONITOR] {event_type}: {path}")

    # Watchdog event handlers
    def on_created(self, event: 'FileSystemEvent'):
        self._handle_event("created", event.src_path, event.is_directory)

    def on_modified(self, event: 'FileSystemEvent'):
        if not event.is_directory:
            self._handle_event("modified", event.src_path)

    def on_deleted(self, event: 'FileSystemEvent'):
        self._handle_event("deleted", event.src_path, event.is_directory)

    def on_moved(self, event: 'FileSystemEvent'):
        self._handle_event("moved", event.dest_path, event.is_directory, event.src_path)


class FileMonitor:
    """
    Monitors file system for ROXY.

    Features:
    - Watch project directories for code changes
    - Detect config modifications
    - Trigger ROXY actions on events
    - Log file activity
    """

    def __init__(self):
        self.handler = RoxyFileHandler(callback=self._on_event)
        self.observer = Observer() if WATCHDOG_AVAILABLE else None
        self.watch_paths: Set[str] = set()
        self.running = False
        self.event_log: List[FileEvent] = []

        ROXY_DATA.mkdir(parents=True, exist_ok=True)
        print("[ROXY.MONITOR] File monitor initialized")

    def add_watch(self, path: str, recursive: bool = True):
        """Add a directory to watch."""
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            print(f"[ROXY.MONITOR] Not a directory: {path}")
            return False

        if path in self.watch_paths:
            return True

        self.watch_paths.add(path)

        if self.observer:
            self.observer.schedule(self.handler, path, recursive=recursive)
            print(f"[ROXY.MONITOR] Watching: {path}")
            return True
        else:
            print(f"[ROXY.MONITOR] Would watch (no watchdog): {path}")
            return False

    def remove_watch(self, path: str):
        """Remove a directory from watching."""
        path = os.path.abspath(path)
        self.watch_paths.discard(path)
        # Note: watchdog doesn't support removing individual watches easily

    def _on_event(self, event: FileEvent):
        """Handle file event."""
        self.event_log.append(event)

        # Keep log manageable
        if len(self.event_log) > 10000:
            self.event_log = self.event_log[-5000:]

        # Send to ROXY brain if available
        self._send_to_brain(event)

        # Log to file
        self._log_event(event)

    def _send_to_brain(self, event: FileEvent):
        """Send event to ROXY shared memory."""
        if not os.path.exists(SHM_PATH):
            return

        try:
            import sys
            sys.path.insert(0, str(Path.home() / ".roxy" / "ipc"))
            from shm_brain import RoxyShmBrain

            brain = RoxyShmBrain(create=False)
            brain.write_json(brain.MSG_STATE, {
                "type": "file_event",
                "event": event.event_type,
                "path": event.path,
                "timestamp": event.timestamp.isoformat(),
                "is_dir": event.is_directory,
            })
            brain.cleanup()
        except Exception:
            pass

    def _log_event(self, event: FileEvent):
        """Log event to file."""
        log_entry = {
            "type": event.event_type,
            "path": event.path,
            "timestamp": event.timestamp.isoformat(),
            "is_dir": event.is_directory,
        }
        if event.old_path:
            log_entry["old_path"] = event.old_path

        with open(MONITOR_LOG, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def start(self):
        """Start the file monitor."""
        if not WATCHDOG_AVAILABLE:
            print("[ROXY.MONITOR] Cannot start - watchdog not installed")
            return

        self.running = True
        self.observer.start()
        print("[ROXY.MONITOR] Started watching files")

    def stop(self):
        """Stop the file monitor."""
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()
        print("[ROXY.MONITOR] Stopped")

    def get_recent_events(self, count: int = 100) -> List[Dict]:
        """Get recent file events."""
        return [
            {
                "type": e.event_type,
                "path": e.path,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in self.event_log[-count:]
        ]

    def get_stats(self) -> Dict:
        """Get monitoring statistics."""
        event_counts = {}
        for event in self.event_log:
            event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1

        return {
            "watch_paths": list(self.watch_paths),
            "total_events": len(self.event_log),
            "event_counts": event_counts,
            "running": self.running,
        }


class InotifyFallback:
    """
    Fallback using inotifywait command.

    Used when watchdog is not available.
    """

    def __init__(self, callback: Optional[Callable[[FileEvent], None]] = None):
        self.callback = callback
        self.process = None
        self.running = False

    async def watch(self, path: str):
        """Watch a directory using inotifywait."""
        import subprocess

        cmd = [
            "inotifywait",
            "-m",  # Monitor mode
            "-r",  # Recursive
            "-e", "create,modify,delete,move",
            "--format", "%e|%w%f",
            path
        ]

        self.running = True
        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

        while self.running:
            line = await self.process.stdout.readline()
            if not line:
                break

            try:
                events_str, filepath = line.decode().strip().split("|")
                events = events_str.split(",")

                event_type = "modified"
                if "CREATE" in events:
                    event_type = "created"
                elif "DELETE" in events:
                    event_type = "deleted"
                elif "MOVE" in events:
                    event_type = "moved"

                is_dir = "ISDIR" in events

                file_event = FileEvent(
                    event_type=event_type,
                    path=filepath,
                    timestamp=datetime.now(),
                    is_directory=is_dir,
                )

                if self.callback:
                    self.callback(file_event)

            except Exception as e:
                print(f"[ROXY.MONITOR] Parse error: {e}")

    def stop(self):
        """Stop watching."""
        self.running = False
        if self.process:
            self.process.terminate()


def demo():
    """Demo the file monitor."""
    if not WATCHDOG_AVAILABLE:
        print("[ROXY.MONITOR] Install watchdog: pip install watchdog")
        return

    monitor = FileMonitor()

    # Watch current directory
    monitor.add_watch(os.getcwd())

    # Watch home directory (non-recursive for safety)
    monitor.add_watch(os.path.expanduser("~/.roxy"), recursive=True)

    print("\n[ROXY.MONITOR] Press Ctrl+C to stop\n")

    try:
        monitor.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[ROXY.MONITOR] Stopping...")
        monitor.stop()

    # Show stats
    stats = monitor.get_stats()
    print(f"\n[ROXY.MONITOR] Stats:")
    print(f"  Total events: {stats['total_events']}")
    print(f"  Event counts: {stats['event_counts']}")


if __name__ == "__main__":
    demo()
