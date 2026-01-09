#!/usr/bin/env python3
"""
Chat Service - Thin client interface to roxy-core.

DOCTRINE:
- GTK app stays thin client
- All intelligence lives in roxy-core
- This service handles ONLY communication

Endpoints used:
- POST /run - Send chat message, get response
- (Future) WS /ws/chat - Streaming responses
- (Future) POST /api/voice/transcribe - STT
- (Future) POST /api/voice/speak - TTS
"""

import gi
gi.require_version('Soup', '3.0')
from gi.repository import GLib, Soup, Gio
import json
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable, List
from datetime import datetime
from enum import Enum
import uuid


# =============================================================================
# CONFIGURATION
# =============================================================================

ROXY_CORE_HOST = os.getenv("ROXY_HOST", "127.0.0.1")
ROXY_CORE_PORT = int(os.getenv("ROXY_PORT", "8766"))
ROXY_CORE_URL = f"http://{ROXY_CORE_HOST}:{ROXY_CORE_PORT}"

TOKEN_PATH = Path.home() / ".roxy" / "secret.token"


def get_auth_token() -> str:
    """Load auth token from ~/.roxy/secret.token"""
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text().strip()
    return ""


# =============================================================================
# DATA MODELS
# =============================================================================

class Identity(Enum):
    """User identity for routing."""
    ME = "me"
    MINDSONG = "mindsong"


class ChatMode(Enum):
    """Chat mode - human-in-the-loop control."""
    DRAFT = "draft"      # Roxy suggests, user approves
    SEND = "send"        # Roxy executes directly (requires explicit arming)


class ConnectionStatus(Enum):
    """Connection state to roxy-core."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class ChatMessage:
    """A message in the conversation."""
    id: str
    role: str           # "user", "assistant", "system"
    content: str
    timestamp: datetime
    identity: Identity = Identity.MINDSONG
    pending: bool = False  # True while waiting for response


@dataclass
class ChatSession:
    """A chat session with roxy-core."""
    id: str
    identity: Identity
    mode: ChatMode
    messages: List[ChatMessage]
    created_at: datetime
    model: str = "unknown"
    

# =============================================================================
# CHAT SERVICE
# =============================================================================

class ChatService:
    """
    Service for communicating with roxy-core.
    
    Responsibilities:
    - Send messages to roxy-core /run endpoint
    - Manage session state
    - Notify UI of responses (via callbacks)
    - Handle connection status
    
    Does NOT:
    - Process LLM directly
    - Handle STT/TTS directly
    - Render UI
    """
    
    def __init__(self):
        self._session: Optional[ChatSession] = None
        self._soup_session = Soup.Session()
        self._status = ConnectionStatus.DISCONNECTED
        self._auth_token = get_auth_token()
        
        # Callbacks
        self._on_message: Optional[Callable[[ChatMessage], None]] = None
        self._on_status_change: Optional[Callable[[ConnectionStatus, str], None]] = None
        self._on_typing: Optional[Callable[[bool], None]] = None
        
        # Metadata from last response
        self._last_model: str = "unknown"
        self._last_expert: str = "roxy"
        self._last_latency_ms: int = 0
    
    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    
    def connect(
        self,
        identity: Identity = Identity.MINDSONG,
        on_message: Optional[Callable[[ChatMessage], None]] = None,
        on_status_change: Optional[Callable[[ConnectionStatus, str], None]] = None,
        on_typing: Optional[Callable[[bool], None]] = None
    ):
        """
        Connect to roxy-core and create/load a session.
        
        Args:
            identity: Which identity to use (me vs mindsong)
            on_message: Callback when new message arrives
            on_status_change: Callback when connection status changes
            on_typing: Callback when typing indicator should show/hide
        """
        self._on_message = on_message
        self._on_status_change = on_status_change
        self._on_typing = on_typing
        
        # Create new session
        self._session = ChatSession(
            id=str(uuid.uuid4()),
            identity=identity,
            mode=ChatMode.DRAFT,
            messages=[],
            created_at=datetime.now()
        )
        
        # Test connection
        self._set_status(ConnectionStatus.CONNECTING, "Connecting to roxy-core...")
        self._ping_roxy_core()
    
    def disconnect(self):
        """Disconnect from roxy-core."""
        self._session = None
        self._set_status(ConnectionStatus.DISCONNECTED, "Disconnected")
    
    def send_message(self, text: str) -> Optional[ChatMessage]:
        """
        Send a message to Roxy and get a response.
        
        Args:
            text: The user's message
            
        Returns:
            The user message (assistant response comes via callback)
        """
        if not self._session:
            print("[ChatService] No session, cannot send")
            return None
        
        if not text.strip():
            return None
        
        # Create user message
        user_msg = ChatMessage(
            id=str(uuid.uuid4()),
            role="user",
            content=text,
            timestamp=datetime.now(),
            identity=self._session.identity
        )
        self._session.messages.append(user_msg)
        
        # Notify UI
        if self._on_message:
            self._on_message(user_msg)
        
        # Show typing indicator
        if self._on_typing:
            self._on_typing(True)
        
        # Send to roxy-core
        self._send_to_roxy_core(text)
        
        return user_msg
    
    def set_mode(self, mode: ChatMode):
        """Set chat mode (draft vs send)."""
        if self._session:
            self._session.mode = mode
            print(f"[ChatService] Mode set to {mode.value}")
    
    def set_identity(self, identity: Identity):
        """Switch identity."""
        if self._session:
            self._session.identity = identity
            print(f"[ChatService] Identity set to {identity.value}")
    
    @property
    def status(self) -> ConnectionStatus:
        return self._status
    
    @property
    def session(self) -> Optional[ChatSession]:
        return self._session
    
    @property
    def model(self) -> str:
        return self._last_model
    
    @property
    def expert(self) -> str:
        return self._last_expert
    
    @property
    def latency_ms(self) -> int:
        return self._last_latency_ms
    
    # -------------------------------------------------------------------------
    # Internal: roxy-core communication
    # -------------------------------------------------------------------------
    
    def _ping_roxy_core(self):
        """Test connection to roxy-core via /health endpoint."""
        uri = f"{ROXY_CORE_URL}/health"
        message = Soup.Message.new("GET", uri)
        
        if self._auth_token:
            message.get_request_headers().append("X-ROXY-Token", self._auth_token)
        
        self._soup_session.send_async(message, GLib.PRIORITY_DEFAULT, None, self._on_ping_response, None)
    
    def _on_ping_response(self, session, result, user_data):
        """Handle ping response from /health."""
        try:
            input_stream = session.send_finish(result)
            
            # Read response
            data_stream = Gio.DataInputStream.new(input_stream)
            lines = []
            while True:
                line, length = data_stream.read_line_utf8(None)
                if line is None:
                    break
                lines.append(line)
            
            data = "".join(lines)
            
            if data:
                try:
                    status = json.loads(data)
                    # Extract model from ollama check if available
                    ollama_status = status.get("checks", {}).get("ollama", "unknown")
                    self._last_model = ollama_status if isinstance(ollama_status, str) else "ready"
                    
                    self._set_status(
                        ConnectionStatus.CONNECTED,
                        f"Connected • roxy-core"
                    )
                    
                    # Add system message
                    if self._session and self._on_message:
                        sys_msg = ChatMessage(
                            id="system-connect",
                            role="system",
                            content=f"✅ Connected to ROXY ({ROXY_CORE_HOST}:{ROXY_CORE_PORT})",
                            timestamp=datetime.now()
                        )
                        self._on_message(sys_msg)
                except json.JSONDecodeError:
                    self._set_status(ConnectionStatus.CONNECTED, "Connected")
            else:
                self._set_status(ConnectionStatus.CONNECTED, "Connected (no status)")
                
        except Exception as e:
            print(f"[ChatService] Ping failed: {e}")
            self._set_status(ConnectionStatus.ERROR, f"Connection failed: {e}")
    
    def _send_to_roxy_core(self, text: str):
        """Send message to roxy-core /run endpoint."""
        uri = f"{ROXY_CORE_URL}/run"
        message = Soup.Message.new("POST", uri)
        
        # Set headers
        headers = message.get_request_headers()
        headers.append("Content-Type", "application/json")
        if self._auth_token:
            headers.append("X-ROXY-Token", self._auth_token)
        
        # Build payload
        payload = {
            "command": text,
            "identity": self._session.identity.value if self._session else "mindsong",
            "mode": self._session.mode.value if self._session else "draft",
            "session_id": self._session.id if self._session else None
        }
        
        # Set body
        body_bytes = json.dumps(payload).encode('utf-8')
        message.set_request_body_from_bytes("application/json", GLib.Bytes.new(body_bytes))
        
        # Record start time for latency
        start_time = GLib.get_monotonic_time()
        
        # Store start_time as instance var since user_data doesn't work reliably
        self._request_start_time = start_time
        
        print(f"[ChatService] Sending to {uri}...")
        
        # Send async
        self._soup_session.send_async(
            message, 
            GLib.PRIORITY_DEFAULT, 
            None, 
            self._on_run_response, 
            None  # user_data - not reliably passed in all libsoup versions
        )
    
    def _on_run_response(self, session, result, user_data):
        """Handle /run response from roxy-core."""
        print("[ChatService] Response callback triggered")
        
        # Hide typing indicator
        if self._on_typing:
            self._on_typing(False)
        
        try:
            input_stream = session.send_finish(result)
            
            # Calculate latency using stored start time
            end_time = GLib.get_monotonic_time()
            start_time = getattr(self, '_request_start_time', end_time)
            self._last_latency_ms = int((end_time - start_time) / 1000)
            print(f"[ChatService] Latency: {self._last_latency_ms}ms")
            
            # Read full response
            data_stream = Gio.DataInputStream.new(input_stream)
            lines = []
            while True:
                line, length = data_stream.read_line_utf8(None)
                if line is None:
                    break
                lines.append(line)
            
            response_text = "\n".join(lines)
            
            if response_text:
                try:
                    data = json.loads(response_text)
                    
                    # Extract response
                    assistant_text = data.get("result", data.get("response", ""))
                    self._last_expert = data.get("routed_to", data.get("expert", "roxy"))
                    
                    if assistant_text:
                        # Create assistant message
                        assistant_msg = ChatMessage(
                            id=str(uuid.uuid4()),
                            role="assistant",
                            content=assistant_text,
                            timestamp=datetime.now(),
                            identity=self._session.identity if self._session else Identity.MINDSONG
                        )
                        
                        if self._session:
                            self._session.messages.append(assistant_msg)
                        
                        if self._on_message:
                            self._on_message(assistant_msg)
                    else:
                        self._handle_error("Empty response from Roxy")
                        
                except json.JSONDecodeError as e:
                    # Maybe it's plain text?
                    if response_text.strip():
                        assistant_msg = ChatMessage(
                            id=str(uuid.uuid4()),
                            role="assistant",
                            content=response_text,
                            timestamp=datetime.now()
                        )
                        if self._session:
                            self._session.messages.append(assistant_msg)
                        if self._on_message:
                            self._on_message(assistant_msg)
                    else:
                        self._handle_error(f"Invalid response: {e}")
            else:
                self._handle_error("No response from roxy-core")
                
        except Exception as e:
            print(f"[ChatService] Error: {e}")
            self._handle_error(str(e))
    
    def _handle_error(self, error: str):
        """Handle error response."""
        if self._on_message:
            error_msg = ChatMessage(
                id=str(uuid.uuid4()),
                role="system",
                content=f"⚠️ Error: {error}",
                timestamp=datetime.now()
            )
            self._on_message(error_msg)
    
    def _set_status(self, status: ConnectionStatus, message: str):
        """Update connection status."""
        self._status = status
        print(f"[ChatService] Status: {status.value} - {message}")
        if self._on_status_change:
            self._on_status_change(status, message)


# =============================================================================
# VOICE SERVICE (Stub for Phase 2)
# =============================================================================

class VoiceService:
    """
    Service for voice input/output via roxy-core.
    
    Phase 1: Stub
    Phase 2: Push-to-talk → STT → Chat → TTS → Playback
    
    Endpoints (to be implemented in roxy-core):
    - POST /api/voice/transcribe - Audio → Text
    - POST /api/voice/speak - Text → Audio
    """
    
    def __init__(self, chat_service: ChatService):
        self._chat = chat_service
        self._is_recording = False
        self._speak_mode = False  # Option B: speak button, not auto-speak
        
        # Callbacks
        self._on_recording_change: Optional[Callable[[bool], None]] = None
        self._on_audio_play: Optional[Callable[[bytes], None]] = None
    
    @property
    def is_recording(self) -> bool:
        return self._is_recording
    
    @property
    def speak_mode(self) -> bool:
        return self._speak_mode
    
    @speak_mode.setter
    def speak_mode(self, value: bool):
        """Toggle speak mode (Option B: manual button)."""
        self._speak_mode = value
        print(f"[VoiceService] Speak mode: {value}")
    
    def start_recording(self):
        """Start recording (push-to-talk pressed)."""
        # TODO: Phase 2 - Start microphone capture
        self._is_recording = True
        print("[VoiceService] Recording started (stub)")
        if self._on_recording_change:
            self._on_recording_change(True)
    
    def stop_recording(self):
        """Stop recording and transcribe."""
        # TODO: Phase 2 - Stop capture, send to /api/voice/transcribe
        self._is_recording = False
        print("[VoiceService] Recording stopped (stub)")
        if self._on_recording_change:
            self._on_recording_change(False)
        
        # Stub: simulate transcription result
        # In Phase 2, this would call roxy-core /api/voice/transcribe
        # then auto-submit to chat_service.send_message(transcript)
    
    def speak(self, text: str):
        """Request TTS for text (Option B: manual speak button)."""
        if not self._speak_mode:
            print("[VoiceService] Speak mode disabled")
            return
        
        # TODO: Phase 2 - Call /api/voice/speak endpoint
        print(f"[VoiceService] Speak request (stub): {text[:50]}...")
        
        # In Phase 2:
        # 1. POST /api/voice/speak with text
        # 2. Get audio bytes back
        # 3. Call self._on_audio_play(audio_bytes)
    
    def set_callbacks(
        self,
        on_recording_change: Optional[Callable[[bool], None]] = None,
        on_audio_play: Optional[Callable[[bytes], None]] = None
    ):
        """Set callbacks for voice events."""
        self._on_recording_change = on_recording_change
        self._on_audio_play = on_audio_play


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_chat_service: Optional[ChatService] = None
_voice_service: Optional[VoiceService] = None


def get_chat_service() -> ChatService:
    """Get or create the global chat service."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service


def get_voice_service() -> VoiceService:
    """Get or create the global voice service."""
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService(get_chat_service())
    return _voice_service
