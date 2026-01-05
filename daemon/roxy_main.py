#!/usr/bin/env python3
"""
Rocky System - Main Daemon Coordinator
Story: RAF-020
Target: Coordinate all ROXY subsystems

Central daemon that:
- Initializes shared memory brain
- Starts audio pipeline
- Manages shortcuts
- Coordinates learning systems
- Handles IPC between components
"""

import asyncio
import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
import threading

# Add ROXY modules to path
ROXY_HOME = Path.home() / ".roxy"
sys.path.insert(0, str(ROXY_HOME / "ipc"))
sys.path.insert(0, str(ROXY_HOME / "learning"))
sys.path.insert(0, str(ROXY_HOME / "wayland"))
sys.path.insert(0, str(ROXY_HOME / "monitor"))

# Configuration
ROXY_DATA = ROXY_HOME / "data"
ROXY_LOGS = ROXY_HOME / "logs"
PID_FILE = ROXY_DATA / "roxy.pid"
STATUS_FILE = ROXY_DATA / "status.json"


class RoxyDaemon:
    """
    Main ROXY daemon coordinator.

    Manages:
    - Shared memory brain
    - Keyboard shortcuts
    - File monitoring
    - Learning systems
    - Health monitoring
    """

    VERSION = "1.0.0"

    def __init__(self):
        self.running = False
        self.start_time = None
        self.brain = None
        self.shortcuts = None
        self.file_monitor = None
        self.components = {}

        # Ensure directories exist
        ROXY_DATA.mkdir(parents=True, exist_ok=True)
        ROXY_LOGS.mkdir(parents=True, exist_ok=True)

        print(f"[ROXY] Daemon v{self.VERSION} initializing...")

    async def start(self):
        """Start all ROXY components."""
        self.running = True
        self.start_time = datetime.now()

        # Write PID file
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGHUP, self._handle_reload)

        # Initialize components
        await self._init_brain()
        await self._init_shortcuts()
        await self._init_monitor()

        # Update status
        self._update_status("running")

        # Notify systemd we're ready
        self._notify_ready()

        print("[ROXY] All components started")
        print("[ROXY] Listening for commands...")

        # Main loop
        await self._main_loop()

    async def _init_brain(self):
        """Initialize shared memory brain."""
        try:
            from shm_brain import RoxyShmBrain
            self.brain = RoxyShmBrain(create=True)
            self.components["brain"] = "running"
            print("[ROXY] Brain: OK")
        except Exception as e:
            print(f"[ROXY] Brain: FAILED - {e}")
            self.components["brain"] = f"error: {e}"

    async def _init_shortcuts(self):
        """Initialize keyboard shortcuts."""
        try:
            from portal_shortcuts import RoxyShortcuts
            self.shortcuts = RoxyShortcuts()

            # Register shortcuts
            await self.shortcuts.register(
                "roxy-activate",
                "Activate ROXY",
                "<Super>r",
                self._on_activate,
            )
            await self.shortcuts.register(
                "roxy-help",
                "ROXY Help",
                "<Super><Shift>r",
                self._on_help,
            )

            # Start listening in background
            asyncio.create_task(self.shortcuts.listen())

            self.components["shortcuts"] = "running"
            print("[ROXY] Shortcuts: OK")
        except Exception as e:
            print(f"[ROXY] Shortcuts: FAILED - {e}")
            self.components["shortcuts"] = f"error: {e}"

    async def _init_monitor(self):
        """Initialize file monitor."""
        try:
            from file_monitor import FileMonitor
            self.file_monitor = FileMonitor()

            # Watch common directories
            self.file_monitor.add_watch(os.path.expanduser("~/"), recursive=False)

            # Start monitoring
            self.file_monitor.start()

            self.components["monitor"] = "running"
            print("[ROXY] File Monitor: OK")
        except Exception as e:
            print(f"[ROXY] File Monitor: FAILED - {e}")
            self.components["monitor"] = f"error: {e}"

    async def _main_loop(self):
        """Main event loop."""
        while self.running:
            try:
                # Process brain messages
                if self.brain:
                    msg = self.brain.read(timeout_ms=100)
                    if msg:
                        await self._handle_message(msg)

                # Periodic health check
                if int(time.time()) % 60 == 0:
                    self._health_check()

                await asyncio.sleep(0.01)

            except Exception as e:
                print(f"[ROXY] Loop error: {e}")
                await asyncio.sleep(1)

    async def _handle_message(self, msg):
        """Handle a message from the brain."""
        from shm_brain import RoxyShmBrain

        if msg.msg_type == RoxyShmBrain.MSG_PING:
            self.brain.write(RoxyShmBrain.MSG_PONG, b"pong")

        elif msg.msg_type == RoxyShmBrain.MSG_COMMAND:
            try:
                data = json.loads(msg.payload.decode())
                cmd = data.get("cmd", "")
                await self._handle_command(cmd, data)
            except json.JSONDecodeError:
                pass

    async def _handle_command(self, cmd: str, data: dict):
        """Handle a ROXY command."""
        print(f"[ROXY] Command: {cmd}")

        if cmd == "status":
            self._send_status()
        elif cmd == "activate":
            self._on_activate()
        elif cmd == "help":
            self._on_help()
        elif cmd == "practice":
            await self._start_practice()
        elif cmd == "stop":
            self.running = False

    def _on_activate(self):
        """Handle activation shortcut."""
        print("[ROXY] ACTIVATED!")
        # Would show UI or process voice command
        self._notify_user("ROXY activated")

    def _on_help(self):
        """Handle help shortcut."""
        print("[ROXY] Help requested")
        self._notify_user("ROXY Help: Super+R to activate")

    async def _start_practice(self):
        """Start a practice session."""
        try:
            from session_recorder import SessionRecorder
            recorder = SessionRecorder()
            session_id = recorder.start_session()
            print(f"[ROXY] Practice session started: {session_id}")
        except Exception as e:
            print(f"[ROXY] Failed to start practice: {e}")

    def _send_status(self):
        """Send status via brain."""
        if self.brain:
            from shm_brain import RoxyShmBrain
            status = self._get_status()
            self.brain.write_json(RoxyShmBrain.MSG_RESPONSE, status)

    def _get_status(self) -> dict:
        """Get current status."""
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        return {
            "version": self.VERSION,
            "status": "running" if self.running else "stopped",
            "uptime_seconds": uptime,
            "components": self.components,
            "pid": os.getpid(),
            "timestamp": datetime.now().isoformat(),
        }

    def _update_status(self, status: str):
        """Update status file."""
        data = self._get_status()
        data["status"] = status
        with open(STATUS_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _health_check(self):
        """Perform health check."""
        # Check brain
        if self.brain:
            try:
                self.brain._read_header()
                self.components["brain"] = "running"
            except:
                self.components["brain"] = "error"

        # Update status file
        self._update_status("running")

    def _notify_user(self, message: str):
        """Send notification to user."""
        try:
            import subprocess
            subprocess.run([
                "notify-send",
                "--app-name=ROXY",
                "--icon=dialog-information",
                "ROXY",
                message
            ], capture_output=True)
        except:
            pass

    def _notify_ready(self):
        """Notify systemd that we're ready."""
        try:
            import socket
            notify_socket = os.environ.get("NOTIFY_SOCKET")
            if notify_socket:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                sock.connect(notify_socket)
                sock.send(b"READY=1")
                sock.close()
        except:
            pass

    def _handle_signal(self, signum, frame):
        """Handle termination signal."""
        print(f"\n[ROXY] Received signal {signum}, shutting down...")
        self.running = False

    def _handle_reload(self, signum, frame):
        """Handle reload signal."""
        print("[ROXY] Reloading configuration...")
        # Would reload config here

    async def stop(self):
        """Stop all components."""
        print("[ROXY] Stopping...")
        self.running = False

        # Update status
        self._update_status("stopped")

        # Stop components
        if self.file_monitor:
            self.file_monitor.stop()

        if self.brain:
            self.brain.cleanup()

        # Remove PID file
        if PID_FILE.exists():
            PID_FILE.unlink()

        print("[ROXY] Stopped")


async def main():
    """Main entry point."""
    daemon = RoxyDaemon()

    try:
        await daemon.start()
    except KeyboardInterrupt:
        pass
    finally:
        await daemon.stop()


if __name__ == "__main__":
    asyncio.run(main())
