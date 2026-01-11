#!/usr/bin/env python3
"""
PROJECT SKYBEAM -- OBS WebSocket Client (SKYBEAM-STORY-004)

Remote control wrapper for OBS Studio via WebSocket protocol.
Provides start/stop recording, scene switching, and status monitoring.
Publishes events to NATS ghost.obs.* topics for Ghost Protocol UI.

Requirements:
  - OBS Studio with WebSocket server enabled on port 4455
  - obs-websocket-py: pip install obs-websocket-py
  - nats-py: pip install nats-py

Usage:
  # As module
  from obs_client import OBSClient
  async with OBSClient() as obs:
      await obs.start_recording()

  # CLI
  python3 obs_client.py start       # Start recording
  python3 obs_client.py stop        # Stop recording
  python3 obs_client.py status      # Get status
  python3 obs_client.py --daemon    # Run event listener daemon

Topics published to NATS:
  ghost.obs.status          - Recording/streaming status updates
  ghost.obs.recording.start - Recording started event
  ghost.obs.recording.stop  - Recording stopped event
  ghost.obs.scene.changed   - Scene switch events
  ghost.obs.error           - Error events
"""

import asyncio
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Suppress verbose logging from obsws_python BEFORE importing
# This prevents the library from printing tracebacks on connection errors
logging.getLogger("obsws_python").setLevel(logging.CRITICAL)
logging.getLogger("obsws_python.baseclient").setLevel(logging.CRITICAL)
logging.getLogger("obsws_python.baseclient.ReqClient").setLevel(logging.CRITICAL)
logging.getLogger("websocket").setLevel(logging.CRITICAL)

try:
    import obsws_python as obs
    from obsws_python import error as obs_error
except ImportError:
    logger.error("obs-websocket-py not installed. Run: pip install obs-websocket-py")
    sys.exit(1)

try:
    import nats
except ImportError:
    logger.warning("nats-py not installed. NATS publishing disabled. Run: pip install nats-py")
    nats = None


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class OBSConfig:
    """OBS WebSocket connection configuration."""
    host: str = "localhost"
    port: int = 4455
    password: str = ""
    timeout: int = 5
    reconnect_delay: float = 5.0
    max_reconnect_attempts: int = -1  # -1 = infinite
    recording_path: str = str(Path.home() / ".roxy" / "content-pipeline" / "input")
    nats_url: str = "nats://127.0.0.1:4222"
    publish_interval: float = 10.0  # Status publish interval in daemon mode

    @classmethod
    def from_env(cls) -> "OBSConfig":
        """Load configuration from environment variables."""
        return cls(
            host=os.getenv("OBS_HOST", "localhost"),
            port=int(os.getenv("OBS_PORT", "4455")),
            password=os.getenv("OBS_PASSWORD", ""),
            timeout=int(os.getenv("OBS_TIMEOUT", "5")),
            reconnect_delay=float(os.getenv("OBS_RECONNECT_DELAY", "5.0")),
            max_reconnect_attempts=int(os.getenv("OBS_MAX_RECONNECT", "-1")),
            recording_path=os.getenv(
                "OBS_RECORDING_PATH",
                str(Path.home() / ".roxy" / "content-pipeline" / "input")
            ),
            nats_url=os.getenv("NATS_URL", "nats://127.0.0.1:4222"),
            publish_interval=float(os.getenv("OBS_PUBLISH_INTERVAL", "10.0")),
        )


# =============================================================================
# Event Data Classes
# =============================================================================

@dataclass
class OBSEvent:
    """Base event class for OBS events."""
    event_type: str
    timestamp: str
    source: str = "obs_client"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> bytes:
        return json.dumps(self.to_dict()).encode()


@dataclass
class RecordingEvent(OBSEvent):
    """Recording state change event."""
    recording: bool = False
    paused: bool = False
    output_path: str = ""
    duration_ms: int = 0


@dataclass
class StatusEvent(OBSEvent):
    """Full OBS status event."""
    connected: bool = False
    recording: bool = False
    recording_paused: bool = False
    streaming: bool = False
    virtual_cam: bool = False
    current_scene: str = ""
    output_path: str = ""
    cpu_usage: float = 0.0
    memory_usage_mb: float = 0.0
    disk_space_mb: float = 0.0


@dataclass
class SceneEvent(OBSEvent):
    """Scene change event."""
    scene_name: str = ""
    previous_scene: str = ""


@dataclass
class ErrorEvent(OBSEvent):
    """Error event."""
    error_code: str = ""
    error_message: str = ""
    recoverable: bool = True


# =============================================================================
# OBS Client
# =============================================================================

class OBSClient:
    """
    Async OBS WebSocket client with automatic reconnection and NATS publishing.

    Example:
        async with OBSClient() as obs:
            await obs.start_recording()
            status = await obs.get_status()
            print(f"Recording: {status['recording']}")
            await obs.stop_recording()
    """

    def __init__(self, config: Optional[OBSConfig] = None):
        self.config = config or OBSConfig.from_env()
        self._req_client: Optional[obs.ReqClient] = None
        self._event_client: Optional[obs.EventClient] = None
        self._nats: Optional[Any] = None
        self._connected = False
        self._reconnect_task: Optional[asyncio.Task] = None
        self._event_handlers: dict[str, list[Callable]] = {}
        self._current_scene: str = ""

        # Ensure recording path exists
        Path(self.config.recording_path).mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Context Manager
    # -------------------------------------------------------------------------

    async def __aenter__(self) -> "OBSClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()

    # -------------------------------------------------------------------------
    # Connection Management
    # -------------------------------------------------------------------------

    async def connect(self) -> bool:
        """
        Connect to OBS WebSocket server.
        Returns True if connected successfully.
        """
        import io
        import contextlib

        try:
            logger.info(f"Connecting to OBS at {self.config.host}:{self.config.port}...")

            # Suppress library's verbose error output during connection
            with contextlib.redirect_stderr(io.StringIO()):
                # Create request client
                self._req_client = obs.ReqClient(
                    host=self.config.host,
                    port=self.config.port,
                    password=self.config.password if self.config.password else None,
                    timeout=self.config.timeout,
                )

            # Verify connection by getting version
            version = self._req_client.get_version()
            logger.info(f"Connected to OBS {version.obs_version} (WebSocket {version.obs_web_socket_version})")

            # Configure recording path
            await self._configure_recording_path()

            # Connect to NATS if available
            await self._connect_nats()

            self._connected = True

            # Publish connection event
            await self._publish_status()

            return True

        except Exception as e:
            logger.error(f"Failed to connect to OBS: {e}")
            self._connected = False
            await self._publish_error("connection_failed", str(e))
            return False

    async def disconnect(self) -> None:
        """Disconnect from OBS and NATS."""
        logger.info("Disconnecting from OBS...")

        # Cancel reconnect task if running
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        # Disconnect OBS clients
        if self._req_client:
            try:
                self._req_client.disconnect()
            except Exception:
                pass
            self._req_client = None

        if self._event_client:
            try:
                self._event_client.disconnect()
            except Exception:
                pass
            self._event_client = None

        # Disconnect NATS
        if self._nats:
            try:
                await self._nats.drain()
            except Exception:
                pass
            self._nats = None

        self._connected = False
        logger.info("Disconnected from OBS")

    async def reconnect(self) -> bool:
        """
        Attempt to reconnect to OBS with exponential backoff.
        Survives OBS restarts.
        """
        attempts = 0
        delay = self.config.reconnect_delay

        while self.config.max_reconnect_attempts == -1 or attempts < self.config.max_reconnect_attempts:
            attempts += 1
            logger.info(f"Reconnection attempt {attempts}...")

            # Clean up existing connections
            if self._req_client:
                try:
                    self._req_client.disconnect()
                except Exception:
                    pass
                self._req_client = None

            # Try to connect
            if await self.connect():
                logger.info("Reconnected successfully!")
                return True

            # Exponential backoff with jitter
            jitter = delay * 0.1 * (2 * (0.5 - time.time() % 1))
            wait_time = min(delay + jitter, 60.0)  # Cap at 60 seconds
            logger.info(f"Waiting {wait_time:.1f}s before next attempt...")
            await asyncio.sleep(wait_time)
            delay = min(delay * 1.5, 60.0)

        logger.error(f"Failed to reconnect after {attempts} attempts")
        return False

    @property
    def connected(self) -> bool:
        """Check if connected to OBS."""
        return self._connected and self._req_client is not None

    async def _connect_nats(self) -> None:
        """Connect to NATS server."""
        if nats is None:
            return

        try:
            self._nats = await nats.connect(self.config.nats_url)
            logger.info(f"Connected to NATS at {self.config.nats_url}")
        except Exception as e:
            logger.warning(f"Failed to connect to NATS: {e}")
            self._nats = None

    async def _configure_recording_path(self) -> None:
        """Configure OBS recording output path."""
        if not self._req_client:
            return

        try:
            current_path = self._req_client.get_record_directory()
            target_path = self.config.recording_path

            if current_path.record_directory != target_path:
                self._req_client.set_record_directory(target_path)
                logger.info(f"Recording path set to: {target_path}")
            else:
                logger.info(f"Recording path already configured: {target_path}")

        except Exception as e:
            logger.warning(f"Could not configure recording path: {e}")

    # -------------------------------------------------------------------------
    # Recording Controls
    # -------------------------------------------------------------------------

    async def start_recording(self) -> dict[str, Any]:
        """
        Start OBS recording.

        Returns:
            dict with status information

        Raises:
            ConnectionError: If not connected to OBS
            RuntimeError: If recording fails to start
        """
        self._ensure_connected()

        try:
            # Check if already recording
            status = self._req_client.get_record_status()
            if status.output_active:
                logger.info("Recording already in progress")
                return {
                    "success": True,
                    "already_recording": True,
                    "output_path": self.config.recording_path,
                }

            # Start recording
            self._req_client.start_record()
            logger.info("Recording started")

            # Publish event
            await self._publish_event(
                "ghost.obs.recording.start",
                RecordingEvent(
                    event_type="recording_started",
                    timestamp=self._timestamp(),
                    recording=True,
                    output_path=self.config.recording_path,
                )
            )

            return {
                "success": True,
                "already_recording": False,
                "output_path": self.config.recording_path,
            }

        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            await self._publish_error("recording_start_failed", str(e))
            raise RuntimeError(f"Failed to start recording: {e}") from e

    async def stop_recording(self) -> dict[str, Any]:
        """
        Stop OBS recording.

        Returns:
            dict with status information and output file path

        Raises:
            ConnectionError: If not connected to OBS
            RuntimeError: If recording fails to stop
        """
        self._ensure_connected()

        try:
            # Check if recording
            status = self._req_client.get_record_status()
            if not status.output_active:
                logger.info("Not currently recording")
                return {
                    "success": True,
                    "was_recording": False,
                    "output_path": None,
                }

            # Get duration before stopping
            duration_ms = int(status.output_duration * 1000) if hasattr(status, 'output_duration') else 0

            # Stop recording
            result = self._req_client.stop_record()
            output_path = result.output_path if hasattr(result, 'output_path') else None

            logger.info(f"Recording stopped. Output: {output_path}")

            # Publish event
            await self._publish_event(
                "ghost.obs.recording.stop",
                RecordingEvent(
                    event_type="recording_stopped",
                    timestamp=self._timestamp(),
                    recording=False,
                    output_path=output_path or self.config.recording_path,
                    duration_ms=duration_ms,
                )
            )

            return {
                "success": True,
                "was_recording": True,
                "output_path": output_path,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            await self._publish_error("recording_stop_failed", str(e))
            raise RuntimeError(f"Failed to stop recording: {e}") from e

    async def pause_recording(self) -> dict[str, Any]:
        """Pause current recording."""
        self._ensure_connected()

        try:
            self._req_client.pause_record()
            logger.info("Recording paused")

            await self._publish_event(
                "ghost.obs.recording.pause",
                RecordingEvent(
                    event_type="recording_paused",
                    timestamp=self._timestamp(),
                    recording=True,
                    paused=True,
                )
            )

            return {"success": True, "paused": True}

        except Exception as e:
            logger.error(f"Failed to pause recording: {e}")
            raise RuntimeError(f"Failed to pause recording: {e}") from e

    async def resume_recording(self) -> dict[str, Any]:
        """Resume paused recording."""
        self._ensure_connected()

        try:
            self._req_client.resume_record()
            logger.info("Recording resumed")

            await self._publish_event(
                "ghost.obs.recording.resume",
                RecordingEvent(
                    event_type="recording_resumed",
                    timestamp=self._timestamp(),
                    recording=True,
                    paused=False,
                )
            )

            return {"success": True, "paused": False}

        except Exception as e:
            logger.error(f"Failed to resume recording: {e}")
            raise RuntimeError(f"Failed to resume recording: {e}") from e

    async def toggle_recording(self) -> dict[str, Any]:
        """Toggle recording on/off."""
        self._ensure_connected()

        status = self._req_client.get_record_status()
        if status.output_active:
            return await self.stop_recording()
        else:
            return await self.start_recording()

    # -------------------------------------------------------------------------
    # Scene Controls
    # -------------------------------------------------------------------------

    async def get_scenes(self) -> list[dict[str, Any]]:
        """Get list of available scenes."""
        self._ensure_connected()

        result = self._req_client.get_scene_list()
        scenes = []
        for scene in result.scenes:
            scenes.append({
                "name": scene.get("sceneName", ""),
                "index": scene.get("sceneIndex", 0),
            })

        return scenes

    async def get_current_scene(self) -> str:
        """Get current active scene name."""
        self._ensure_connected()

        result = self._req_client.get_current_program_scene()
        return result.scene_name

    async def switch_scene(self, scene_name: str) -> dict[str, Any]:
        """
        Switch to a different scene.

        Args:
            scene_name: Name of scene to switch to

        Returns:
            dict with status information
        """
        self._ensure_connected()

        try:
            previous_scene = await self.get_current_scene()
            self._req_client.set_current_program_scene(scene_name)

            logger.info(f"Switched scene: {previous_scene} -> {scene_name}")

            await self._publish_event(
                "ghost.obs.scene.changed",
                SceneEvent(
                    event_type="scene_changed",
                    timestamp=self._timestamp(),
                    scene_name=scene_name,
                    previous_scene=previous_scene,
                )
            )

            return {
                "success": True,
                "scene": scene_name,
                "previous_scene": previous_scene,
            }

        except Exception as e:
            logger.error(f"Failed to switch scene: {e}")
            raise RuntimeError(f"Failed to switch scene: {e}") from e

    # -------------------------------------------------------------------------
    # Status Methods
    # -------------------------------------------------------------------------

    async def get_status(self) -> dict[str, Any]:
        """
        Get comprehensive OBS status.

        Returns:
            dict with current OBS state
        """
        self._ensure_connected()

        try:
            # Get various status info
            record_status = self._req_client.get_record_status()
            stream_status = self._req_client.get_stream_status()
            vcam_status = self._req_client.get_virtual_cam_status()
            stats = self._req_client.get_stats()
            current_scene = await self.get_current_scene()
            record_dir = self._req_client.get_record_directory()

            return {
                "connected": True,
                "recording": record_status.output_active,
                "recording_paused": record_status.output_paused,
                "recording_duration": record_status.output_duration if hasattr(record_status, 'output_duration') else 0,
                "streaming": stream_status.output_active,
                "virtual_cam": vcam_status.output_active,
                "current_scene": current_scene,
                "output_path": record_dir.record_directory,
                "stats": {
                    "cpu_usage": stats.cpu_usage,
                    "memory_usage_mb": stats.memory_usage,
                    "available_disk_space_mb": stats.available_disk_space,
                    "active_fps": stats.active_fps,
                    "average_frame_time": stats.average_frame_time_ms,
                    "render_skipped_frames": stats.render_skipped_frames,
                    "output_skipped_frames": stats.output_skipped_frames,
                },
            }

        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {
                "connected": False,
                "error": str(e),
            }

    async def get_recording_status(self) -> dict[str, Any]:
        """Get recording-specific status."""
        self._ensure_connected()

        status = self._req_client.get_record_status()
        return {
            "recording": status.output_active,
            "paused": status.output_paused,
            "duration": status.output_duration if hasattr(status, 'output_duration') else 0,
            "bytes": status.output_bytes if hasattr(status, 'output_bytes') else 0,
        }

    # -------------------------------------------------------------------------
    # Screenshot Methods
    # -------------------------------------------------------------------------

    async def take_screenshot(self, output_path: Optional[str] = None) -> dict[str, Any]:
        """
        Take a screenshot of current OBS output.

        Args:
            output_path: Optional path to save screenshot.
                        Defaults to content-pipeline/input/screenshot_<timestamp>.png
        """
        self._ensure_connected()

        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(Path(self.config.recording_path) / f"screenshot_{timestamp}.png")

        try:
            current_scene = await self.get_current_scene()
            self._req_client.save_source_screenshot(
                source_name=current_scene,
                img_format="png",
                file_path=output_path,
            )

            logger.info(f"Screenshot saved: {output_path}")
            return {
                "success": True,
                "path": output_path,
            }

        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            raise RuntimeError(f"Failed to take screenshot: {e}") from e

    # -------------------------------------------------------------------------
    # NATS Publishing
    # -------------------------------------------------------------------------

    async def _publish_event(self, topic: str, event: OBSEvent) -> None:
        """Publish event to NATS topic."""
        if not self._nats:
            return

        try:
            await self._nats.publish(topic, event.to_json())
            await self._nats.flush()
            logger.debug(f"Published to {topic}")
        except Exception as e:
            logger.warning(f"Failed to publish to {topic}: {e}")

    async def _publish_status(self) -> None:
        """Publish full status to NATS."""
        if not self._nats:
            return

        try:
            status = await self.get_status()
            event = StatusEvent(
                event_type="status",
                timestamp=self._timestamp(),
                connected=status.get("connected", False),
                recording=status.get("recording", False),
                recording_paused=status.get("recording_paused", False),
                streaming=status.get("streaming", False),
                virtual_cam=status.get("virtual_cam", False),
                current_scene=status.get("current_scene", ""),
                output_path=status.get("output_path", ""),
                cpu_usage=status.get("stats", {}).get("cpu_usage", 0.0),
                memory_usage_mb=status.get("stats", {}).get("memory_usage_mb", 0.0),
                disk_space_mb=status.get("stats", {}).get("available_disk_space_mb", 0.0),
            )
            await self._publish_event("ghost.obs.status", event)
        except Exception as e:
            logger.warning(f"Failed to publish status: {e}")

    async def _publish_error(self, error_code: str, message: str) -> None:
        """Publish error event to NATS."""
        if not self._nats:
            return

        event = ErrorEvent(
            event_type="error",
            timestamp=self._timestamp(),
            error_code=error_code,
            error_message=message,
        )
        await self._publish_event("ghost.obs.error", event)

    # -------------------------------------------------------------------------
    # Daemon Mode
    # -------------------------------------------------------------------------

    async def run_daemon(self) -> None:
        """
        Run as daemon: maintain connection and publish status periodically.
        Handles OBS restarts automatically.
        """
        logger.info("Starting OBS client daemon...")
        logger.info(f"Publishing status every {self.config.publish_interval}s")

        while True:
            try:
                # Connect if not connected
                if not self.connected:
                    if not await self.connect():
                        logger.warning(f"Connection failed, retrying in {self.config.reconnect_delay}s...")
                        await asyncio.sleep(self.config.reconnect_delay)
                        continue

                # Publish status
                await self._publish_status()

                # Wait for next interval
                await asyncio.sleep(self.config.publish_interval)

            except KeyboardInterrupt:
                logger.info("Daemon interrupted by user")
                break
            except Exception as e:
                logger.error(f"Daemon error: {e}")
                self._connected = False
                await asyncio.sleep(self.config.reconnect_delay)

        await self.disconnect()

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def _ensure_connected(self) -> None:
        """Ensure we're connected to OBS."""
        if not self.connected:
            raise ConnectionError("Not connected to OBS. Call connect() first.")

    @staticmethod
    def _timestamp() -> str:
        """Get current UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# =============================================================================
# CLI Interface
# =============================================================================

async def cli_start():
    """CLI: Start recording."""
    async with OBSClient() as client:
        result = await client.start_recording()
        if result["success"]:
            if result.get("already_recording"):
                print("Already recording")
            else:
                print(f"Recording started. Output: {result['output_path']}")
        else:
            print("Failed to start recording")
            sys.exit(1)


async def cli_stop():
    """CLI: Stop recording."""
    async with OBSClient() as client:
        result = await client.stop_recording()
        if result["success"]:
            if result.get("was_recording"):
                print(f"Recording stopped. Output: {result['output_path']}")
                print(f"Duration: {result['duration_ms']}ms")
            else:
                print("Was not recording")
        else:
            print("Failed to stop recording")
            sys.exit(1)


async def cli_status():
    """CLI: Get OBS status."""
    async with OBSClient() as client:
        status = await client.get_status()
        print("OBS Status:")
        print(f"  Connected: {status.get('connected', False)}")
        print(f"  Recording: {status.get('recording', False)}")
        print(f"  Recording Paused: {status.get('recording_paused', False)}")
        print(f"  Streaming: {status.get('streaming', False)}")
        print(f"  Virtual Cam: {status.get('virtual_cam', False)}")
        print(f"  Current Scene: {status.get('current_scene', 'N/A')}")
        print(f"  Output Path: {status.get('output_path', 'N/A')}")

        stats = status.get('stats', {})
        if stats:
            print(f"  CPU Usage: {stats.get('cpu_usage', 0):.1f}%")
            print(f"  Memory: {stats.get('memory_usage_mb', 0):.1f} MB")
            print(f"  Disk Space: {stats.get('available_disk_space_mb', 0):.1f} MB")


async def cli_scenes():
    """CLI: List available scenes."""
    async with OBSClient() as client:
        scenes = await client.get_scenes()
        current = await client.get_current_scene()
        print("Available Scenes:")
        for scene in scenes:
            marker = "*" if scene['name'] == current else " "
            print(f"  {marker} {scene['name']}")


async def cli_switch(scene_name: str):
    """CLI: Switch to scene."""
    async with OBSClient() as client:
        result = await client.switch_scene(scene_name)
        print(f"Switched to scene: {result['scene']}")


async def cli_screenshot():
    """CLI: Take screenshot."""
    async with OBSClient() as client:
        result = await client.take_screenshot()
        print(f"Screenshot saved: {result['path']}")


async def cli_daemon():
    """CLI: Run as daemon."""
    client = OBSClient()
    await client.run_daemon()


def print_usage():
    """Print CLI usage."""
    print("""
OBS WebSocket Client - Project SKYBEAM

Usage:
  python3 obs_client.py <command> [args]

Commands:
  start       Start recording
  stop        Stop recording
  status      Get OBS status
  scenes      List available scenes
  switch <n>  Switch to scene <n>
  screenshot  Take screenshot
  --daemon    Run as daemon (continuous status publishing)

Environment Variables:
  OBS_HOST              OBS WebSocket host (default: localhost)
  OBS_PORT              OBS WebSocket port (default: 4455)
  OBS_PASSWORD          OBS WebSocket password (default: empty)
  OBS_RECORDING_PATH    Recording output path (default: ~/.roxy/content-pipeline/input)
  NATS_URL              NATS server URL (default: nats://127.0.0.1:4222)

Examples:
  python3 obs_client.py start
  python3 obs_client.py stop
  python3 obs_client.py switch "Gaming"
  python3 obs_client.py --daemon
""")


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)

    cmd = sys.argv[1].lower()

    try:
        if cmd == "start":
            asyncio.run(cli_start())
        elif cmd == "stop":
            asyncio.run(cli_stop())
        elif cmd == "status":
            asyncio.run(cli_status())
        elif cmd == "scenes":
            asyncio.run(cli_scenes())
        elif cmd == "switch" and len(sys.argv) >= 3:
            asyncio.run(cli_switch(sys.argv[2]))
        elif cmd == "screenshot":
            asyncio.run(cli_screenshot())
        elif cmd == "--daemon" or cmd == "daemon":
            asyncio.run(cli_daemon())
        elif cmd == "--help" or cmd == "-h":
            print_usage()
        else:
            print(f"Unknown command: {cmd}")
            print_usage()
            sys.exit(1)
    except ConnectionError as e:
        print(f"Connection error: {e}")
        print("Make sure OBS is running with WebSocket server enabled on port 4455")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
