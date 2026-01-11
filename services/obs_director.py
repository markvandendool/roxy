#!/usr/bin/env python3
"""
SKYBEAM OBS Director Service (THEATER-006)

Orchestrates OBS recording for MindSong Theater sessions.
Connects to Theater Control WebSocket, manages recording lifecycle,
and handles file handoff to SKYBEAM pipeline.

Documentation: file:///home/mark/.roxy/SKYBEAM_CURRENT_STATE.md

Input:
- Session manifest JSON (theater-sessions/session_*.json)
- Theater Control WebSocket events (ws://localhost:9137/theater-control)

Output:
- Recording files (landscape + portrait)
- Handoff manifest to SKYBEAM input path

NATS topics:
- ghost.theater.status
- ghost.theater.recording.start
- ghost.theater.recording.stop
- ghost.theater.session.complete
- ghost.theater.error

Usage:
  # Start a session from manifest
  python3 obs_director.py start /path/to/session_manifest.json

  # Run as daemon (listens for NATS commands)
  python3 obs_director.py --daemon

  # Check status
  python3 obs_director.py status
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import sys
import websockets
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

try:
    import nats
except ImportError:
    logger.warning("nats-py not installed. NATS publishing disabled.")
    nats = None

try:
    import jsonschema
except ImportError:
    logger.warning("jsonschema not installed. Schema validation disabled.")
    jsonschema = None


# =============================================================================
# Configuration
# =============================================================================

ROXY_BASE = Path.home() / ".roxy"
THEATER_SESSIONS_DIR = ROXY_BASE / "theater-sessions"
CONFIG_DIR = ROXY_BASE / "config"
PIPELINE_INPUT = ROXY_BASE / "content-pipeline" / "input"
SCHEMA_PATH = THEATER_SESSIONS_DIR / "session_manifest_schema.json"
MAPPING_PATH = CONFIG_DIR / "theater_obs_mapping.json"

THEATER_CONTROL_WS = "ws://localhost:9137/theater-control?role=director"
NATS_URL = os.getenv("NATS_URL", "nats://127.0.0.1:4222")


class SessionStatus(Enum):
    PENDING = "pending"
    RECORDING = "recording"
    COMPLETED = "completed"
    FAILED = "failed"
    INGESTED = "ingested"


@dataclass
class DirectorConfig:
    """OBS Director configuration."""
    nats_url: str = NATS_URL
    theater_ws_url: str = THEATER_CONTROL_WS
    sessions_dir: Path = THEATER_SESSIONS_DIR
    pipeline_input: Path = PIPELINE_INPUT
    obs_host: str = "localhost"
    obs_port: int = 4455
    obs_password: str = ""
    reconnect_delay: float = 5.0

    @classmethod
    def from_env(cls) -> "DirectorConfig":
        return cls(
            nats_url=os.getenv("NATS_URL", NATS_URL),
            theater_ws_url=os.getenv("THEATER_WS_URL", THEATER_CONTROL_WS),
            obs_host=os.getenv("OBS_HOST", "localhost"),
            obs_port=int(os.getenv("OBS_PORT", "4455")),
            obs_password=os.getenv("OBS_PASSWORD", ""),
        )


# =============================================================================
# Event Data Classes
# =============================================================================

@dataclass
class TheaterEvent:
    """Event from Theater Control WebSocket."""
    event_type: str
    timestamp: str
    payload: dict = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict) -> "TheaterEvent":
        return cls(
            event_type=data.get("type", "unknown"),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            payload=data.get("payload", {})
        )


@dataclass
class DirectorEvent:
    """Event published by OBS Director."""
    event_type: str
    session_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> bytes:
        return json.dumps(self.to_dict()).encode()


# =============================================================================
# Session Manager
# =============================================================================

class SessionManager:
    """Manages theater session manifests."""

    def __init__(self, sessions_dir: Path = THEATER_SESSIONS_DIR):
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._schema = self._load_schema()

    def _load_schema(self) -> Optional[dict]:
        """Load session manifest schema for validation."""
        if not SCHEMA_PATH.exists():
            logger.warning(f"Schema not found: {SCHEMA_PATH}")
            return None
        try:
            with open(SCHEMA_PATH) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load schema: {e}")
            return None

    def validate_manifest(self, manifest: dict) -> tuple[bool, str]:
        """Validate a session manifest against schema."""
        if jsonschema is None:
            logger.warning("jsonschema not installed, skipping validation")
            return True, "Validation skipped (no jsonschema)"

        if self._schema is None:
            return True, "Validation skipped (no schema)"

        try:
            jsonschema.validate(manifest, self._schema)
            return True, "Valid"
        except jsonschema.ValidationError as e:
            return False, f"Validation error: {e.message}"

    def load_manifest(self, path: Path) -> Optional[dict]:
        """Load and validate a session manifest."""
        if not path.exists():
            logger.error(f"Manifest not found: {path}")
            return None

        try:
            with open(path) as f:
                manifest = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in manifest: {e}")
            return None

        valid, msg = self.validate_manifest(manifest)
        if not valid:
            logger.error(f"Invalid manifest: {msg}")
            return None

        logger.info(f"Loaded manifest: {manifest.get('session_id', 'unknown')}")
        return manifest

    def save_manifest(self, manifest: dict) -> Path:
        """Save a session manifest."""
        session_id = manifest.get("session_id", self._generate_session_id())
        path = self.sessions_dir / f"session_{session_id}.json"
        with open(path, "w") as f:
            json.dump(manifest, f, indent=2)
        logger.info(f"Saved manifest: {path}")
        return path

    def update_status(self, path: Path, status: SessionStatus, error: dict = None, result: dict = None) -> None:
        """Update session status in manifest."""
        with open(path) as f:
            manifest = json.load(f)

        manifest["status"] = status.value
        if error:
            manifest["error"] = error
        if result:
            manifest["result"] = result

        with open(path, "w") as f:
            json.dump(manifest, f, indent=2)

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y%m%d_%H%M%S")
        h = hashlib.sha256(f"{ts}{os.getpid()}{now.microsecond}".encode()).hexdigest()[:8]
        return f"SESSION_{ts}_{h}"


# =============================================================================
# Theater Control WebSocket Client
# =============================================================================

class TheaterControlClient:
    """WebSocket client for MindSong Theater Control Hub (Director role)."""

    HEARTBEAT_INTERVAL = 30.0  # seconds

    def __init__(self, url: str = THEATER_CONTROL_WS):
        self.url = url
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._event_handlers: dict[str, list] = {}
        self._message_id = 0
        self._pending_responses: dict[str, asyncio.Future] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._client_id = f"roxy-director-{os.getpid()}"

    async def connect(self) -> bool:
        """Connect to Theater Control Hub as director."""
        try:
            self._ws = await websockets.connect(self.url)
            self._connected = True
            logger.info(f"Connected to Theater Control Hub (director): {self.url}")

            # Start heartbeat task
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            return True
        except Exception as e:
            logger.error(f"Failed to connect to Theater Control Hub: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from Theater Control Hub."""
        # Cancel heartbeat
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

        if self._ws:
            await self._ws.close()
            self._ws = None
        self._connected = False
        logger.info("Disconnected from Theater Control Hub")

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to keep connection alive."""
        while self._connected and self._ws:
            try:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                if self._connected and self._ws:
                    msg = {
                        "type": "heartbeat",
                        "id": self._next_message_id(),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "payload": {
                            "role": "director",
                            "clientId": self._client_id
                        }
                    }
                    await self._ws.send(json.dumps(msg))
                    logger.debug("Heartbeat sent")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Heartbeat error: {e}")

    @property
    def connected(self) -> bool:
        return self._connected and self._ws is not None

    def _next_message_id(self) -> str:
        self._message_id += 1
        return f"msg_{self._message_id}"

    async def send_command(self, action: str, **kwargs) -> dict:
        """Send a command to Theater Control Hub (relayed to stage)."""
        if not self.connected:
            raise ConnectionError("Not connected to Theater Control Hub")

        msg_id = self._next_message_id()
        msg = {
            "type": "command",
            "id": msg_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"action": action, **kwargs}
        }

        await self._ws.send(json.dumps(msg))
        logger.debug(f"Sent command to hub: {action}")

        # Commands don't get direct responses from hub (fire-and-forget to stage)
        # But hub may return an error if stage is not connected
        try:
            response = await asyncio.wait_for(self._ws.recv(), timeout=2.0)
            data = json.loads(response)
            # Check if it's an error from the hub
            if data.get("type") == "error":
                logger.warning(f"Hub error for command {action}: {data.get('payload', {}).get('message')}")
                return {"error": data.get("payload", {}).get("code", "unknown")}
            # Otherwise it might be an unrelated event, ignore for now
            return {"success": True}
        except asyncio.TimeoutError:
            # No error means command was accepted by hub
            return {"success": True}

    async def query(self, query_type: str) -> dict:
        """Send a query to Theater Control Hub."""
        if not self.connected:
            raise ConnectionError("Not connected to Theater Control Hub")

        msg_id = self._next_message_id()
        msg = {
            "type": "query",
            "id": msg_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"query": query_type}
        }

        await self._ws.send(json.dumps(msg))

        # Wait for response with matching requestId
        try:
            while True:
                response = await asyncio.wait_for(self._ws.recv(), timeout=5.0)
                data = json.loads(response)
                # Check if this is our response
                if data.get("type") == "response":
                    payload = data.get("payload", {})
                    if payload.get("requestId") == msg_id:
                        return payload.get("data", {})
                elif data.get("type") == "error":
                    payload = data.get("payload", {})
                    if payload.get("requestId") == msg_id:
                        return {"error": payload.get("code"), "message": payload.get("message")}
                # Ignore other messages (events)
        except asyncio.TimeoutError:
            return {"error": "timeout"}

    async def play(self) -> dict:
        return await self.send_command("play")

    async def pause(self) -> dict:
        return await self.send_command("pause")

    async def stop(self) -> dict:
        return await self.send_command("stop")

    async def seek(self, tick: int) -> dict:
        return await self.send_command("seek", tick=tick)

    async def set_preset(self, preset: str) -> dict:
        return await self.send_command("set_preset", preset=preset)

    async def start_ndi(self, quality: str = "high") -> dict:
        return await self.send_command("start_ndi", quality=quality)

    async def stop_ndi(self) -> dict:
        return await self.send_command("stop_ndi")

    async def get_state(self) -> dict:
        return await self.query("playback_state")

    async def listen_events(self, handler) -> None:
        """Listen for events from Theater Control."""
        if not self.connected:
            raise ConnectionError("Not connected to Theater Control")

        try:
            async for message in self._ws:
                data = json.loads(message)
                if data.get("type") == "event":
                    event = TheaterEvent.from_json(data)
                    await handler(event)
        except websockets.ConnectionClosed:
            logger.info("Theater Control connection closed")
            self._connected = False


# =============================================================================
# OBS Director Service
# =============================================================================

class OBSDirectorService:
    """
    Orchestrates OBS recording for MindSong Theater sessions.

    Workflow:
    1. Load session manifest
    2. Connect to Theater Control WebSocket
    3. Configure OBS scenes/sources for NDI
    4. Start NDI streaming from MindSong
    5. Start OBS recording (with pre-roll)
    6. Send play command to MindSong
    7. Listen for song_ended event
    8. Wait post-roll, stop recording
    9. Hand off files to SKYBEAM
    """

    NATS_TOPICS = {
        "status": "ghost.theater.status",
        "recording_start": "ghost.theater.recording.start",
        "recording_stop": "ghost.theater.recording.stop",
        "session_complete": "ghost.theater.session.complete",
        "error": "ghost.theater.error",
        "roxy_mode": "ghost.roxy.mode"  # THEATER-011: Silent mode
    }

    def __init__(self, config: Optional[DirectorConfig] = None):
        self.config = config or DirectorConfig.from_env()
        self.session_manager = SessionManager(self.config.sessions_dir)
        self.theater_client = TheaterControlClient(self.config.theater_ws_url)
        self._nats = None
        self._obs_client = None
        self._current_session: Optional[dict] = None
        self._current_manifest_path: Optional[Path] = None
        self._recording = False
        self._preset_mapping = self._load_preset_mapping()
        self._current_preset: Optional[str] = None
        self._roxy_mode: str = "normal"  # THEATER-011: normal | recording

    def _load_preset_mapping(self) -> dict:
        """Load theater preset to OBS scene mapping from config."""
        if not MAPPING_PATH.exists():
            logger.warning(f"OBS mapping config not found: {MAPPING_PATH}")
            return {}
        try:
            with open(MAPPING_PATH) as f:
                data = json.load(f)
            mapping = data.get("mappings", {}).get("presets", {})
            logger.info(f"Loaded {len(mapping)} preset mappings from {MAPPING_PATH}")
            return mapping
        except Exception as e:
            logger.error(f"Failed to load preset mapping: {e}")
            return {}

    # =========================================================================
    # THEATER-011: ROXY Silent Mode
    # =========================================================================

    async def enter_recording_mode(self, session_id: str) -> bool:
        """
        Enter recording mode - signals ROXY to pause automation.

        When in recording mode:
        - SKYBEAM timers are paused
        - Non-essential notifications are muted
        - Only critical events are processed

        Args:
            session_id: The active session ID

        Returns:
            True if mode change successful
        """
        if self._roxy_mode == "recording":
            logger.debug("Already in recording mode")
            return True

        self._roxy_mode = "recording"
        logger.info(f"Entering recording mode for session: {session_id}")

        # Publish mode change event
        await self._publish_event(
            self.NATS_TOPICS["roxy_mode"],
            DirectorEvent(
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
        """
        Exit recording mode - signals ROXY to resume automation.

        Args:
            session_id: The session that was being recorded

        Returns:
            True if mode change successful
        """
        if self._roxy_mode == "normal":
            logger.debug("Already in normal mode")
            return True

        self._roxy_mode = "normal"
        logger.info(f"Exiting recording mode for session: {session_id}")

        # Publish mode change event
        await self._publish_event(
            self.NATS_TOPICS["roxy_mode"],
            DirectorEvent(
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
        """Get current ROXY mode (normal or recording)."""
        return self._roxy_mode

    async def connect(self) -> bool:
        """Initialize connections to NATS, OBS, and Theater Control."""
        success = True

        # Connect to NATS
        if nats:
            try:
                self._nats = await nats.connect(self.config.nats_url)
                logger.info(f"Connected to NATS: {self.config.nats_url}")
            except Exception as e:
                logger.warning(f"NATS connection failed: {e}")

        # Import and connect to OBS
        try:
            from obs_client import OBSClient, OBSConfig
            obs_config = OBSConfig(
                host=self.config.obs_host,
                port=self.config.obs_port,
                password=self.config.obs_password
            )
            self._obs_client = OBSClient(obs_config)
            if not await self._obs_client.connect():
                logger.error("Failed to connect to OBS")
                success = False
        except ImportError:
            logger.error("obs_client module not found")
            success = False
        except Exception as e:
            logger.error(f"OBS connection failed: {e}")
            success = False

        return success

    async def disconnect(self) -> None:
        """Clean up all connections."""
        if self.theater_client.connected:
            await self.theater_client.disconnect()

        if self._obs_client:
            await self._obs_client.disconnect()

        if self._nats:
            await self._nats.drain()
            self._nats = None

    async def _publish_event(self, topic: str, event: DirectorEvent) -> None:
        """Publish event to NATS."""
        if self._nats:
            try:
                await self._nats.publish(topic, event.to_json())
            except Exception as e:
                logger.warning(f"Failed to publish to {topic}: {e}")

    async def start_session(self, manifest_path: str) -> Optional[str]:
        """
        Initialize a recording session from manifest.

        Returns session_id on success, None on failure.
        """
        path = Path(manifest_path)
        manifest = self.session_manager.load_manifest(path)
        if not manifest:
            return None

        session_id = manifest.get("session_id")
        logger.info(f"Starting session: {session_id}")

        # Store current session
        self._current_session = manifest
        self._current_manifest_path = path

        # Update status to pending
        self.session_manager.update_status(path, SessionStatus.PENDING)

        # Connect to Theater Control
        if not await self.theater_client.connect():
            await self._handle_error("theater_connection_failed", "Could not connect to MindSong Theater")
            return None

        # Set theater preset
        preset = manifest.get("theater", {}).get("preset", "performance")
        await self.theater_client.set_preset(preset)
        logger.info(f"Theater preset: {preset}")

        # Publish session start event
        await self._publish_event(
            self.NATS_TOPICS["status"],
            DirectorEvent(
                event_type="session_started",
                session_id=session_id,
                data={"preset": preset, "manifest_path": str(path)}
            )
        )

        return session_id

    async def begin_recording(self, session_id: str) -> bool:
        """
        Start OBS recording with configured settings.

        Returns True on success.
        """
        if not self._current_session or self._current_session.get("session_id") != session_id:
            logger.error(f"Session not found: {session_id}")
            return False

        if not self._obs_client or not self._obs_client.connected:
            await self._handle_error("obs_not_connected", "OBS is not connected")
            return False

        manifest = self._current_session
        recording_config = manifest.get("recording", {})
        pre_roll = recording_config.get("pre_roll_seconds", 2)

        logger.info(f"Starting recording with {pre_roll}s pre-roll")

        # THEATER-011: Enter recording mode (pauses ROXY automation)
        await self.enter_recording_mode(session_id)

        # Update status
        self.session_manager.update_status(self._current_manifest_path, SessionStatus.RECORDING)

        # Start NDI streaming
        await self.theater_client.start_ndi("high")
        await asyncio.sleep(1)  # Let NDI stabilize

        # Start OBS recording
        try:
            result = await self._obs_client.start_recording()
            if not result.get("success"):
                await self._handle_error("recording_start_failed", "OBS failed to start recording")
                return False
        except Exception as e:
            await self._handle_error("recording_start_exception", str(e))
            return False

        self._recording = True

        # Publish recording start event
        await self._publish_event(
            self.NATS_TOPICS["recording_start"],
            DirectorEvent(
                event_type="recording_started",
                session_id=session_id,
                data={"pre_roll_seconds": pre_roll}
            )
        )

        # Wait pre-roll
        await asyncio.sleep(pre_roll)

        # Start playback
        await self.theater_client.play()
        logger.info("Playback started")

        return True

    async def stop_recording(self, session_id: str) -> dict:
        """
        Stop recording and return file paths.

        Returns dict with file info.
        """
        if not self._recording:
            logger.warning("No recording in progress")
            return {}

        manifest = self._current_session
        recording_config = manifest.get("recording", {})
        post_roll = recording_config.get("post_roll_seconds", 2)

        logger.info(f"Stopping with {post_roll}s post-roll")

        # Stop playback
        await self.theater_client.stop()

        # Wait post-roll
        await asyncio.sleep(post_roll)

        # Stop OBS recording
        try:
            result = await self._obs_client.stop_recording()
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            result = {}

        self._recording = False

        # Stop NDI
        await self.theater_client.stop_ndi()

        # Publish recording stop event
        await self._publish_event(
            self.NATS_TOPICS["recording_stop"],
            DirectorEvent(
                event_type="recording_stopped",
                session_id=session_id,
                data={"post_roll_seconds": post_roll, "output": result}
            )
        )

        # THEATER-011: Exit recording mode (resumes ROXY automation)
        await self.exit_recording_mode(session_id)

        return result

    async def switch_scene_for_preset(
        self,
        preset: str,
        orientation: str = "landscape"
    ) -> bool:
        """
        Switch OBS scene based on theater preset.

        Args:
            preset: Theater preset name (analysis, performance, teaching, minimal, composer)
            orientation: Either "landscape" or "portrait"

        Returns:
            True if scene switch successful, False otherwise
        """
        if not self._obs_client or not self._obs_client.connected:
            logger.warning("Cannot switch scene: OBS not connected")
            return False

        # Look up scene name from mapping
        preset_config = self._preset_mapping.get(preset)
        if not preset_config:
            logger.warning(f"No mapping found for preset: {preset}")
            return False

        scene_key = f"obs_scene_{orientation}"
        scene_name = preset_config.get(scene_key)
        if not scene_name:
            logger.warning(f"No {orientation} scene for preset: {preset}")
            return False

        # Skip if already on this preset
        if self._current_preset == preset:
            logger.debug(f"Already on preset: {preset}")
            return True

        try:
            result = await self._obs_client.switch_scene(scene_name)
            if result.get("success"):
                self._current_preset = preset
                logger.info(f"Switched to scene: {scene_name} (preset: {preset})")

                # Publish scene change event
                if self._current_session:
                    await self._publish_event(
                        "ghost.obs.scene.switch",
                        DirectorEvent(
                            event_type="scene_switched",
                            session_id=self._current_session.get("session_id", ""),
                            data={
                                "preset": preset,
                                "scene": scene_name,
                                "orientation": orientation
                            }
                        )
                    )
                return True
            else:
                logger.error(f"Scene switch failed: {result.get('error', 'unknown')}")
                return False
        except Exception as e:
            logger.error(f"Scene switch error: {e}")
            return False

    async def on_theater_event(self, event: TheaterEvent) -> None:
        """Handle events from Theater Control WebSocket."""
        payload = event.payload

        if payload.get("event") == "song_ended":
            logger.info("Song ended event received")
            if self._recording and self._current_session:
                session_id = self._current_session.get("session_id")
                result = await self.stop_recording(session_id)
                await self.handoff_to_skybeam(session_id)

        elif payload.get("event") == "preset_changed":
            preset = payload.get("preset")
            logger.info(f"Preset changed: {preset}")
            # Switch OBS scene to match preset (THEATER-010)
            await self.switch_scene_for_preset(preset, "landscape")
            # TODO: Also switch portrait scene if using Aitum Vertical

    async def handoff_to_skybeam(self, session_id: str) -> Optional[str]:
        """
        Move recordings to SKYBEAM input, return job_id.

        Creates a handoff manifest and copies files to pipeline input.
        """
        if not self._current_session:
            logger.error("No current session for handoff")
            return None

        manifest = self._current_session
        skybeam_config = manifest.get("skybeam", {})

        if not skybeam_config.get("auto_ingest", True):
            logger.info("Auto-ingest disabled, skipping handoff")
            return None

        # Generate job ID
        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y%m%d_%H%M%S")
        h = hashlib.sha256(f"{session_id}{ts}".encode()).hexdigest()[:8]
        job_id = f"JOB_{ts}_{h}"

        # Create job directory
        job_dir = self.config.pipeline_input / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Handoff to SKYBEAM: {job_id}")

        # Build handoff manifest
        handoff = {
            "handoff_id": f"HANDOFF_{ts}_{h}",
            "session_id": session_id,
            "job_id": job_id,
            "timestamp": now.isoformat(),
            "files": {},
            "metadata": {
                "song_title": manifest.get("song", {}).get("title", "Unknown"),
                "theater_preset": manifest.get("theater", {}).get("preset", "performance"),
                "auto_process": True
            }
        }

        # TODO: Copy actual recording files from OBS output
        # For now, create placeholder
        handoff_path = job_dir / "handoff_manifest.json"
        with open(handoff_path, "w") as f:
            json.dump(handoff, f, indent=2)

        # Update session status
        self.session_manager.update_status(
            self._current_manifest_path,
            SessionStatus.INGESTED,
            result={"job_id": job_id, "handoff_path": str(handoff_path)}
        )

        # Publish session complete event
        await self._publish_event(
            self.NATS_TOPICS["session_complete"],
            DirectorEvent(
                event_type="session_complete",
                session_id=session_id,
                data={"job_id": job_id, "status": "ingested"}
            )
        )

        logger.info(f"Handoff complete: {job_id}")
        return job_id

    async def _handle_error(self, code: str, message: str) -> None:
        """Handle and report an error."""
        logger.error(f"[{code}] {message}")

        if self._current_session and self._current_manifest_path:
            self.session_manager.update_status(
                self._current_manifest_path,
                SessionStatus.FAILED,
                error={
                    "code": code,
                    "message": message,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )

        session_id = self._current_session.get("session_id", "unknown") if self._current_session else "unknown"
        await self._publish_event(
            self.NATS_TOPICS["error"],
            DirectorEvent(
                event_type="error",
                session_id=session_id,
                data={"code": code, "message": message}
            )
        )

    async def run_session(self, manifest_path: str) -> bool:
        """
        Run a complete recording session from manifest.

        This is the main entry point for automated recording.
        """
        # Start session
        session_id = await self.start_session(manifest_path)
        if not session_id:
            return False

        # Begin recording
        if not await self.begin_recording(session_id):
            return False

        # Listen for theater events (song_ended will trigger stop)
        try:
            await self.theater_client.listen_events(self.on_theater_event)
        except Exception as e:
            logger.error(f"Event listener error: {e}")
            # If we lost connection, stop recording gracefully
            if self._recording:
                await self.stop_recording(session_id)
                await self.handoff_to_skybeam(session_id)

        return True


# =============================================================================
# CLI
# =============================================================================

async def main() -> int:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: obs_director.py <command> [args]")
        print("Commands:")
        print("  start <manifest.json>  - Start a recording session")
        print("  status                 - Show current status")
        print("  --daemon               - Run as daemon")
        return 1

    command = sys.argv[1]
    director = OBSDirectorService()

    try:
        if command == "start" and len(sys.argv) > 2:
            await director.connect()
            success = await director.run_session(sys.argv[2])
            return 0 if success else 1

        elif command == "status":
            await director.connect()
            # TODO: Implement status query
            print("Status: Ready")
            return 0

        elif command == "--daemon":
            await director.connect()
            logger.info("OBS Director daemon started")
            # TODO: Implement NATS command listener
            while True:
                await asyncio.sleep(60)

        else:
            print(f"Unknown command: {command}")
            return 1

    finally:
        await director.disconnect()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
