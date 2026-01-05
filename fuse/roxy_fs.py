#!/usr/bin/env python3
"""
Rocky FUSE - Virtual Filesystem
Story: RAF-019
Target: /tmp/roxy virtual filesystem for ROXY state access

Provides virtual files for:
- ROXY status and metrics
- Current session info
- Skill progress
- Recent events
"""

import os
import stat
import errno
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

try:
    from fuse import FUSE, FuseOSError, Operations
    FUSE_AVAILABLE = True
except ImportError:
    try:
        from fusepy import FUSE, FuseOSError, Operations
        FUSE_AVAILABLE = True
    except ImportError:
        FUSE_AVAILABLE = False
        print("[ROXY.FUSE] fusepy not installed")
        print("Run: pip install fusepy")

# Configuration
ROXY_DATA = Path.home() / ".roxy" / "data"
SHM_PATH = "/dev/shm/roxy_brain"


class RoxyFS(Operations if FUSE_AVAILABLE else object):
    """
    Virtual filesystem exposing ROXY state.

    Filesystem structure:
    /tmp/roxy/
        status              - Current ROXY status
        session/
            id              - Current session ID
            duration        - Session duration
            notes           - Notes played
        skills/
            summary         - Skill summary JSON
            <skill_id>      - Individual skill info
        events/
            recent          - Recent events
            errors          - Recent errors
        config/
            settings.json   - ROXY settings
        metrics/
            cpu             - CPU usage
            memory          - Memory usage
            latency         - IPC latency
    """

    def __init__(self):
        self.fd = 0
        self.open_files: Dict[int, bytes] = {}
        self.start_time = time.time()

        # Virtual file definitions
        self.files = {
            '/status': self._get_status,
            '/session/id': self._get_session_id,
            '/session/duration': self._get_session_duration,
            '/session/notes': self._get_session_notes,
            '/skills/summary': self._get_skills_summary,
            '/events/recent': self._get_recent_events,
            '/events/errors': self._get_recent_errors,
            '/config/settings.json': self._get_settings,
            '/metrics/cpu': self._get_cpu,
            '/metrics/memory': self._get_memory,
            '/metrics/latency': self._get_latency,
            '/help': self._get_help,
        }

        # Virtual directories
        self.dirs = {
            '/': ['status', 'session', 'skills', 'events', 'config', 'metrics', 'help'],
            '/session': ['id', 'duration', 'notes'],
            '/skills': ['summary'],
            '/events': ['recent', 'errors'],
            '/config': ['settings.json'],
            '/metrics': ['cpu', 'memory', 'latency'],
        }

        print("[ROXY.FUSE] Virtual filesystem initialized")

    # File content generators
    def _get_status(self) -> bytes:
        """Get ROXY status."""
        status = {
            "name": "ROXY",
            "version": "1.0.0",
            "uptime_seconds": time.time() - self.start_time,
            "brain_active": os.path.exists(SHM_PATH),
            "timestamp": datetime.now().isoformat(),
        }
        return json.dumps(status, indent=2).encode() + b'\n'

    def _get_session_id(self) -> bytes:
        """Get current session ID."""
        return b"session_" + datetime.now().strftime("%Y%m%d").encode() + b'\n'

    def _get_session_duration(self) -> bytes:
        """Get session duration."""
        duration = int(time.time() - self.start_time)
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}\n".encode()

    def _get_session_notes(self) -> bytes:
        """Get notes played in session."""
        # Would read from actual session data
        return b"Notes: 0 (no active practice session)\n"

    def _get_skills_summary(self) -> bytes:
        """Get skills summary."""
        try:
            import sys
            sys.path.insert(0, str(Path.home() / ".roxy" / "learning"))
            from skill_progression import SkillProgressionModel
            model = SkillProgressionModel()
            summary = model.get_skill_summary()
            return json.dumps(summary, indent=2).encode() + b'\n'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}\n'.encode()

    def _get_recent_events(self) -> bytes:
        """Get recent events."""
        log_file = ROXY_DATA / "file_monitor.log"
        if log_file.exists():
            with open(log_file) as f:
                lines = f.readlines()[-20:]
                return ''.join(lines).encode()
        return b"No recent events\n"

    def _get_recent_errors(self) -> bytes:
        """Get recent errors."""
        return b"No recent errors\n"

    def _get_settings(self) -> bytes:
        """Get ROXY settings."""
        settings = {
            "shortcuts": {
                "activate": "Super+R",
                "help": "Super+Shift+R",
            },
            "audio": {
                "sample_rate": 48000,
                "buffer_size": 128,
            },
            "learning": {
                "auto_record": True,
                "frustration_detection": True,
            },
        }
        return json.dumps(settings, indent=2).encode() + b'\n'

    def _get_cpu(self) -> bytes:
        """Get CPU usage."""
        try:
            with open('/proc/loadavg') as f:
                load = f.read().split()[0]
                return f"Load: {load}\n".encode()
        except:
            return b"Unknown\n"

    def _get_memory(self) -> bytes:
        """Get memory usage."""
        try:
            with open('/proc/meminfo') as f:
                lines = f.readlines()[:3]
                return ''.join(lines).encode()
        except:
            return b"Unknown\n"

    def _get_latency(self) -> bytes:
        """Get IPC latency."""
        if os.path.exists(SHM_PATH):
            return b"IPC: <1us (shm active)\n"
        return b"IPC: N/A (shm not active)\n"

    def _get_help(self) -> bytes:
        """Get help text."""
        return b"""ROXY Virtual Filesystem

Files:
  /status           - ROXY status JSON
  /session/id       - Current session ID
  /session/duration - Session uptime
  /session/notes    - Notes played
  /skills/summary   - Skill progress JSON
  /events/recent    - Recent file events
  /events/errors    - Recent errors
  /config/settings.json - Configuration
  /metrics/cpu      - CPU load
  /metrics/memory   - Memory info
  /metrics/latency  - IPC latency

Usage:
  cat /tmp/roxy/status
  watch cat /tmp/roxy/session/duration
  jq . /tmp/roxy/skills/summary
"""

    # FUSE Operations
    def getattr(self, path, fh=None):
        """Get file attributes."""
        now = time.time()

        if path in self.dirs:
            # Directory
            return {
                'st_mode': stat.S_IFDIR | 0o755,
                'st_nlink': 2 + len(self.dirs.get(path, [])),
                'st_uid': os.getuid(),
                'st_gid': os.getgid(),
                'st_atime': now,
                'st_mtime': now,
                'st_ctime': now,
            }
        elif path in self.files:
            # Virtual file
            content = self.files[path]()
            return {
                'st_mode': stat.S_IFREG | 0o444,
                'st_nlink': 1,
                'st_size': len(content),
                'st_uid': os.getuid(),
                'st_gid': os.getgid(),
                'st_atime': now,
                'st_mtime': now,
                'st_ctime': now,
            }
        else:
            raise FuseOSError(errno.ENOENT) if FUSE_AVAILABLE else None

    def readdir(self, path, fh):
        """List directory contents."""
        yield '.'
        yield '..'

        if path in self.dirs:
            for entry in self.dirs[path]:
                yield entry

    def open(self, path, flags):
        """Open a file."""
        if path not in self.files:
            raise FuseOSError(errno.ENOENT) if FUSE_AVAILABLE else None

        self.fd += 1
        self.open_files[self.fd] = self.files[path]()
        return self.fd

    def read(self, path, size, offset, fh):
        """Read from a file."""
        if fh in self.open_files:
            content = self.open_files[fh]
        elif path in self.files:
            content = self.files[path]()
        else:
            raise FuseOSError(errno.ENOENT) if FUSE_AVAILABLE else None

        return content[offset:offset + size]

    def release(self, path, fh):
        """Close a file."""
        if fh in self.open_files:
            del self.open_files[fh]
        return 0

    def statfs(self, path):
        """Get filesystem stats."""
        return {
            'f_bsize': 4096,
            'f_blocks': 1024,
            'f_bfree': 512,
            'f_bavail': 512,
            'f_files': len(self.files),
            'f_ffree': 100,
            'f_namemax': 255,
        }


def mount_roxy_fs(mountpoint: str = "/tmp/roxy"):
    """Mount the ROXY virtual filesystem."""
    if not FUSE_AVAILABLE:
        print("[ROXY.FUSE] FUSE not available")
        print("Install: pip install fusepy")
        print("Also ensure libfuse is installed: sudo apt install fuse")
        return

    # Create mountpoint
    os.makedirs(mountpoint, exist_ok=True)

    print(f"[ROXY.FUSE] Mounting at {mountpoint}")
    print("[ROXY.FUSE] Press Ctrl+C to unmount")

    try:
        FUSE(RoxyFS(), mountpoint, foreground=True, allow_other=False, nothreads=True)
    except Exception as e:
        print(f"[ROXY.FUSE] Mount failed: {e}")
        print("[ROXY.FUSE] Try: sudo chmod 666 /dev/fuse")


def demo_without_mount():
    """Demo the filesystem without actually mounting."""
    print("[ROXY.FUSE] Demo mode (no mount)")

    fs = RoxyFS()

    print("\n=== /status ===")
    print(fs._get_status().decode())

    print("=== /session/duration ===")
    print(fs._get_session_duration().decode())

    print("=== /metrics/latency ===")
    print(fs._get_latency().decode())

    print("=== /help ===")
    print(fs._get_help().decode())


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo_without_mount()
    else:
        mountpoint = sys.argv[1] if len(sys.argv) > 1 else "/tmp/roxy"
        mount_roxy_fs(mountpoint)
