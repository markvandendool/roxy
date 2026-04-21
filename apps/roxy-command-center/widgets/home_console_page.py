#!/usr/bin/env python3
"""
Home Console Page - The ROXY Command Center cockpit.

NORTH STAR: Home = Talk + Triage + Execute
- Not a dashboard. An operations console.
- GTK is thin client; roxy-core is the brain.

Layout:
  [Left: Triage/Inbox]  [Center: Roxy Chat]  [Right: Progressions/Runs]

Chat is REAL - wired to roxy-core via ChatService.
Voice is Option B: Speak button toggle (not auto-speak).
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Soup', '3.0')
from gi.repository import Gtk, Adw, GLib, Pango, Gio, Soup
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import json
import random
import sys
import os
import uuid

# Add parent dir to path for services import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.chat_service import (
    ChatService, VoiceService,
    ChatMessage as ServiceChatMessage,
    ChatMode, ConnectionStatus,
    Identity as ServiceIdentity,
    get_chat_service, get_voice_service
)

INFO_FETCH_TIMEOUT_SECONDS = 2.0



# =============================================================================
# DATA MODELS (Canonical Schema - matches FINISHING_PLAN.md)
# =============================================================================

class Identity(Enum):
    """User identity for routing."""
    ME = "me"           # 👤 Personal
    MINDSONG = "mindsong"  # 🎵 Brand


class Bucket(Enum):
    """Triage bucket for inbox items."""
    NOW = "now"         # Requires immediate reply
    QUEUED = "queued"   # Can wait, but needs response
    FYI = "fyi"         # No reply needed


class RunStatus(Enum):
    """Execution run status."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class InboxThread:
    """A thread in the unified inbox."""
    id: str
    source: str         # email, github, discord, instagram, etc.
    source_icon: str    # GTK icon name
    identity: Identity
    sender: str
    preview: str
    bucket: Bucket
    priority: int       # 0=P0 (critical), 1=P1, 2=P2
    timestamp: datetime
    unread: bool = True
    suggested_action: str = "Reply"  # Reply, Approve, Run, Ignore


@dataclass
class ExecutionRun:
    """A progression/run in the execution timeline."""
    id: str
    name: str
    type: str           # orchestrator, content_pipeline, deployment
    status: RunStatus
    started_at: Optional[datetime]
    progress_pct: Optional[int]
    can_cancel: bool = True


@dataclass
class ChatMessage:
    """A message in the Roxy conversation."""
    id: str
    role: str           # "user" or "assistant" or "system"
    content: str
    timestamp: datetime


# =============================================================================
# MOCK DATA STORE (Until roxy-core endpoints are ready)
# =============================================================================

class MockDataStore:
    """
    Placeholder data for UI development.
    TODO: Replace with roxy-core API calls.
    
    roxy-core endpoints needed:
    - GET /api/inbox/threads
    - GET /api/inbox/threads/:id
    - POST /api/inbox/threads/:id/reply
    - POST /api/inbox/threads/:id/action
    - GET /api/runs
    - POST /api/runs/:id/dispatch
    - POST /api/runs/:id/cancel
    - GET /api/chat/history
    - POST /api/chat/send
    """
    
    # All 20 sources + system sources as placeholders
    SOURCES = {
        # Human messaging
        "email_personal": ("mail-unread-symbolic", Identity.ME),
        "email_business": ("mail-unread-symbolic", Identity.MINDSONG),
        "sms": ("phone-symbolic", Identity.ME),
        "imessage": ("phone-apple-symbolic", Identity.ME),
        "github": ("system-software-install-symbolic", Identity.MINDSONG),
        "discord": ("user-available-symbolic", Identity.MINDSONG),
        "slack": ("user-available-symbolic", Identity.MINDSONG),
        "telegram": ("mail-send-symbolic", Identity.MINDSONG),
        "whatsapp": ("phone-symbolic", Identity.MINDSONG),
        "instagram_dm": ("camera-photo-symbolic", Identity.MINDSONG),
        "instagram_comment": ("camera-photo-symbolic", Identity.MINDSONG),
        "youtube_comment": ("video-display-symbolic", Identity.MINDSONG),
        "twitter_dm": ("user-available-symbolic", Identity.MINDSONG),
        "twitter_mention": ("user-available-symbolic", Identity.MINDSONG),
        "linkedin": ("avatar-default-symbolic", Identity.MINDSONG),
        "reddit": ("user-available-symbolic", Identity.MINDSONG),
        "twitch_chat": ("video-display-symbolic", Identity.MINDSONG),
        "signal": ("channel-secure-symbolic", Identity.ME),
        "matrix": ("network-server-symbolic", Identity.MINDSONG),
        "rss": ("application-rss+xml-symbolic", Identity.MINDSONG),
        # System sources
        "ops_alert": ("dialog-warning-symbolic", Identity.MINDSONG),
        "orchestrator": ("system-run-symbolic", Identity.MINDSONG),
        "stackkraft": ("media-playback-start-symbolic", Identity.MINDSONG),
        "service_health": ("emblem-ok-symbolic", Identity.MINDSONG),
    }
    
    @classmethod
    def get_mock_inbox(cls) -> List[InboxThread]:
        """Generate mock inbox threads."""
        now = datetime.now()
        
        threads = [
            InboxThread(
                id="1", source="email_personal", source_icon="mail-unread-symbolic",
                identity=Identity.ME, sender="Mom", preview="Hey, are you coming to dinner Sunday?",
                bucket=Bucket.NOW, priority=0, timestamp=now, suggested_action="Reply"
            ),
            InboxThread(
                id="2", source="github", source_icon="system-software-install-symbolic",
                identity=Identity.MINDSONG, sender="dependabot[bot]", preview="Bump axios from 1.6.0 to 1.6.2",
                bucket=Bucket.QUEUED, priority=2, timestamp=now, suggested_action="Approve"
            ),
            InboxThread(
                id="3", source="discord", source_icon="user-available-symbolic",
                identity=Identity.MINDSONG, sender="@techfan42", preview="Love the new video! How did you set up...",
                bucket=Bucket.QUEUED, priority=1, timestamp=now, suggested_action="Reply"
            ),
            InboxThread(
                id="4", source="youtube_comment", source_icon="video-display-symbolic",
                identity=Identity.MINDSONG, sender="MusicLover99", preview="This is exactly what I needed! 🔥",
                bucket=Bucket.FYI, priority=2, timestamp=now, suggested_action="Like"
            ),
            InboxThread(
                id="5", source="ops_alert", source_icon="dialog-warning-symbolic",
                identity=Identity.MINDSONG, sender="Grafana", preview="GPU1 temp > 55°C for 5 minutes",
                bucket=Bucket.NOW, priority=0, timestamp=now, suggested_action="Investigate"
            ),
            InboxThread(
                id="6", source="instagram_dm", source_icon="camera-photo-symbolic",
                identity=Identity.MINDSONG, sender="@producer_beats", preview="Collab? I make beats in your style",
                bucket=Bucket.QUEUED, priority=1, timestamp=now, suggested_action="Reply"
            ),
            InboxThread(
                id="7", source="twitter_mention", source_icon="user-available-symbolic",
                identity=Identity.MINDSONG, sender="@AIEnthusiast", preview="@novaxe your local LLM setup is insane!",
                bucket=Bucket.FYI, priority=2, timestamp=now, suggested_action="Like"
            ),
            InboxThread(
                id="8", source="email_business", source_icon="mail-unread-symbolic",
                identity=Identity.MINDSONG, sender="Gumroad", preview="New sale: AI Automation Starter Kit",
                bucket=Bucket.FYI, priority=2, timestamp=now, suggested_action="Archive"
            ),
            InboxThread(
                id="9", source="slack", source_icon="user-available-symbolic",
                identity=Identity.MINDSONG, sender="#dev-general", preview="Anyone tried the new Ollama release?",
                bucket=Bucket.FYI, priority=2, timestamp=now, suggested_action="Reply"
            ),
            InboxThread(
                id="10", source="stackkraft", source_icon="media-playback-start-symbolic",
                identity=Identity.MINDSONG, sender="Pipeline", preview="3 clips ready for TikTok publish",
                bucket=Bucket.QUEUED, priority=1, timestamp=now, suggested_action="Approve"
            ),
        ]
        return threads
    
    @classmethod
    def get_mock_runs(cls) -> List[ExecutionRun]:
        """Generate mock execution runs."""
        return [
            ExecutionRun(
                id="run-1", name="Deploy Command Center v1.2",
                type="deployment", status=RunStatus.QUEUED,
                started_at=None, progress_pct=None
            ),
            ExecutionRun(
                id="run-2", name="StackKraft: Publish to TikTok",
                type="content_pipeline", status=RunStatus.RUNNING,
                started_at=datetime.now(), progress_pct=45
            ),
            ExecutionRun(
                id="run-3", name="Backup PostgreSQL",
                type="orchestrator", status=RunStatus.COMPLETED,
                started_at=datetime.now(), progress_pct=100, can_cancel=False
            ),
            ExecutionRun(
                id="run-4", name="Sync MindSong to Mac Studio",
                type="orchestrator", status=RunStatus.FAILED,
                started_at=datetime.now(), progress_pct=67, can_cancel=False
            ),
        ]
    
    @classmethod
    def get_mock_chat(cls) -> List[ChatMessage]:
        """Generate mock chat history."""
        now = datetime.now()
        return [
            ChatMessage(
                id="msg-1", role="system",
                content="Connected to ROXY (local) • qwen2.5:14b • MindSong context",
                timestamp=now
            ),
            ChatMessage(
                id="msg-2", role="user",
                content="Check the GPU temps and deploy the fix if everything looks good",
                timestamp=now
            ),
            ChatMessage(
                id="msg-3", role="assistant",
                content="GPU0 (W7900) is at 38°C, GPU1 (W7800) at 52°C - both within normal range. "
                        "The deployment is ready. Should I proceed with the deploy?",
                timestamp=now
            ),
        ]


# =============================================================================
# UI COMPONENTS
# =============================================================================

class IdentityChip(Gtk.Button):
    """Filter chip for identity selection."""
    
    def __init__(self, label: str, icon: str, identity: Optional[Identity], active: bool = False):
        super().__init__()
        self.identity = identity
        self.add_css_class("flat")
        self.add_css_class("identity-chip")
        if active:
            self.add_css_class("suggested-action")
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.set_child(box)
        
        icon_widget = Gtk.Label(label=icon)
        box.append(icon_widget)
        
        label_widget = Gtk.Label(label=label)
        box.append(label_widget)


class BucketTabs(Gtk.Box):
    """Now / Queued / FYI tab selector."""
    
    def __init__(self, on_bucket_change: Optional[callable] = None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add_css_class("linked")
        self.on_bucket_change = on_bucket_change
        self._buttons: Dict[Bucket, Gtk.ToggleButton] = {}
        self._current = Bucket.NOW
        
        for bucket in Bucket:
            btn = Gtk.ToggleButton(label=bucket.value.upper())
            btn.set_active(bucket == self._current)
            btn.connect("toggled", self._on_toggle, bucket)
            self._buttons[bucket] = btn
            self.append(btn)
    
    def _on_toggle(self, button: Gtk.ToggleButton, bucket: Bucket):
        if button.get_active():
            self._current = bucket
            for b, btn in self._buttons.items():
                if b != bucket:
                    btn.set_active(False)
            if self.on_bucket_change:
                self.on_bucket_change(bucket)


class InboxThreadRow(Gtk.ListBoxRow):
    """A single thread row in the inbox."""
    
    def __init__(self, thread: InboxThread):
        super().__init__()
        self.thread = thread
        self.add_css_class("inbox-thread-row")
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        main_box.set_margin_top(8)
        main_box.set_margin_bottom(8)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        self.set_child(main_box)
        
        # Top row: source icon, identity, sender, priority
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        main_box.append(top_row)
        
        # Source icon
        source_icon = Gtk.Image.new_from_icon_name(thread.source_icon)
        source_icon.set_pixel_size(16)
        source_icon.add_css_class("dim-label")
        top_row.append(source_icon)
        
        # Identity badge
        identity_label = Gtk.Label(label="👤" if thread.identity == Identity.ME else "🎵")
        identity_label.set_tooltip_text("Personal" if thread.identity == Identity.ME else "MindSong")
        top_row.append(identity_label)
        
        # Sender
        sender_label = Gtk.Label(label=thread.sender)
        sender_label.set_xalign(0)
        sender_label.set_hexpand(True)
        sender_label.add_css_class("heading")
        if thread.unread:
            sender_label.add_css_class("accent")
        top_row.append(sender_label)
        
        # Priority badge
        if thread.priority == 0:
            priority_label = Gtk.Label(label="P0")
            priority_label.add_css_class("error")
            top_row.append(priority_label)
        elif thread.priority == 1:
            priority_label = Gtk.Label(label="P1")
            priority_label.add_css_class("warning")
            top_row.append(priority_label)
        
        # Preview text
        preview_label = Gtk.Label(label=thread.preview)
        preview_label.set_xalign(0)
        preview_label.set_ellipsize(Pango.EllipsizeMode.END)
        preview_label.add_css_class("dim-label")
        main_box.append(preview_label)
        
        # Action buttons row
        actions_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions_row.set_margin_top(4)
        main_box.append(actions_row)
        
        # Suggested action button
        action_btn = Gtk.Button(label=thread.suggested_action)
        action_btn.add_css_class("suggested-action")
        action_btn.add_css_class("pill")
        action_btn.connect("clicked", self._on_action)
        actions_row.append(action_btn)
        
        # Secondary actions
        defer_btn = Gtk.Button(label="Defer")
        defer_btn.add_css_class("flat")
        defer_btn.add_css_class("dim-label")
        actions_row.append(defer_btn)
        
        roxy_btn = Gtk.Button(label="→ Roxy")
        roxy_btn.add_css_class("flat")
        roxy_btn.add_css_class("dim-label")
        roxy_btn.set_tooltip_text("Assign to Roxy")
        actions_row.append(roxy_btn)
    
    def _on_action(self, button):
        """Handle action click - TODO: wire to roxy-core."""
        print(f"[Inbox] Action '{self.thread.suggested_action}' on thread {self.thread.id}")


class TriageColumn(Gtk.Box):
    """Left column: Unified Inbox / Triage."""
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add_css_class("triage-column")
        self.set_size_request(320, -1)
        
        self._current_identity: Optional[Identity] = None
        self._current_bucket = Bucket.NOW
        self._threads: List[InboxThread] = []
        
        self._build_ui()
        self._load_mock_data()
    
    def _build_ui(self):
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header.set_margin_top(12)
        header.set_margin_start(12)
        header.set_margin_end(12)
        header.set_margin_bottom(8)
        self.append(header)
        
        # Title
        title = Gtk.Label(label="Inbox")
        title.add_css_class("title-2")
        title.set_xalign(0)
        header.append(title)
        
        # Identity filter chips
        identity_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        header.append(identity_box)
        
        all_chip = IdentityChip("All", "📬", None, active=True)
        all_chip.connect("clicked", self._on_identity_filter, None)
        identity_box.append(all_chip)
        
        me_chip = IdentityChip("Me", "👤", Identity.ME)
        me_chip.connect("clicked", self._on_identity_filter, Identity.ME)
        identity_box.append(me_chip)
        
        mindsong_chip = IdentityChip("MindSong", "🎵", Identity.MINDSONG)
        mindsong_chip.connect("clicked", self._on_identity_filter, Identity.MINDSONG)
        identity_box.append(mindsong_chip)
        
        # Bucket tabs
        self.bucket_tabs = BucketTabs(on_bucket_change=self._on_bucket_change)
        header.append(self.bucket_tabs)
        
        # Thread list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(scrolled)
        
        self.thread_list = Gtk.ListBox()
        self.thread_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.thread_list.add_css_class("navigation-sidebar")
        scrolled.set_child(self.thread_list)
        
        # Super reply bar
        reply_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        reply_box.set_margin_start(12)
        reply_box.set_margin_end(12)
        reply_box.set_margin_bottom(12)
        self.append(reply_box)
        
        reply_label = Gtk.Label(label="Super Reply")
        reply_label.add_css_class("dim-label")
        reply_label.add_css_class("caption")
        reply_label.set_xalign(0)
        reply_box.append(reply_label)
        
        reply_entry = Gtk.Entry()
        reply_entry.set_placeholder_text("Type to reply to selected...")
        reply_box.append(reply_entry)
    
    def _on_identity_filter(self, button, identity: Optional[Identity]):
        self._current_identity = identity
        self._refresh_list()
    
    def _on_bucket_change(self, bucket: Bucket):
        self._current_bucket = bucket
        self._refresh_list()
    
    def _load_mock_data(self):
        self._threads = MockDataStore.get_mock_inbox()
        self._refresh_list()
    
    def _refresh_list(self):
        # Clear
        while True:
            row = self.thread_list.get_row_at_index(0)
            if row:
                self.thread_list.remove(row)
            else:
                break
        
        # Filter and add
        for thread in self._threads:
            # Identity filter
            if self._current_identity and thread.identity != self._current_identity:
                continue
            # Bucket filter
            if thread.bucket != self._current_bucket:
                continue
            
            row = InboxThreadRow(thread)
            self.thread_list.append(row)


class ChatMessage_Widget(Gtk.Box):
    """A single chat message bubble."""
    
    def __init__(self, message: ChatMessage):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.set_margin_top(8)
        self.set_margin_start(12)
        self.set_margin_end(12)
        
        if message.role == "system":
            self.add_css_class("system-message")
            label = Gtk.Label(label=message.content)
            label.add_css_class("dim-label")
            label.add_css_class("caption")
            label.set_wrap(True)
            label.set_xalign(0.5)
            label.set_selectable(True)  # Enable text selection
            self.append(label)
        else:
            is_user = message.role == "user"
            
            # Message bubble
            bubble = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            bubble.add_css_class("chat-bubble")
            bubble.add_css_class("user-bubble" if is_user else "assistant-bubble")
            bubble.set_margin_start(50 if is_user else 0)
            bubble.set_margin_end(0 if is_user else 50)
            self.append(bubble)
            
            # Role label
            role_label = Gtk.Label(label="You" if is_user else "Roxy")
            role_label.add_css_class("caption")
            role_label.add_css_class("dim-label")
            role_label.set_xalign(0)
            bubble.append(role_label)
            
            # Content - SELECTABLE for copy/paste
            content_label = Gtk.Label(label=message.content)
            content_label.set_wrap(True)
            content_label.set_xalign(0)
            content_label.set_max_width_chars(60)
            content_label.set_selectable(True)  # Enable text selection
            bubble.append(content_label)


class TalkColumn(Gtk.Box):
    """Center column: Roxy Conversation - REAL roxy-core integration."""
    
    def __init__(self):
        print("[TalkColumn] ========== INIT BEGIN ==========" )
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add_css_class("talk-column")
        self.set_hexpand(True)
        print("[TalkColumn] Base widget initialized")
        
        self._draft_mode = True  # Human-in-the-loop default
        self._speak_mode = False  # Option B: speak button, not auto-speak
        self._is_typing = False
        
        # Operator controls (Chief's Truth Panel)
        self._routing_mode = "AUTO"  # CHAT, RAG, EXEC, AUTO
        self._pool_mode = "AUTO"  # AUTO, W5700X, 6900XT
        
        # Services
        print("[TalkColumn] Getting services...")
        self._chat_service = get_chat_service()
        self._voice_service = get_voice_service()
        print("[TalkColumn] Services acquired")

        self._disposed = False
        self._info_session = Soup.Session()
        try:
            self._info_session.set_property("timeout", max(1, int(INFO_FETCH_TIMEOUT_SECONDS)))
        except TypeError:
            try:
                self._info_session.props.timeout = max(1, int(INFO_FETCH_TIMEOUT_SECONDS))
            except Exception:
                pass
        except Exception:
            pass
        self._info_fetch_pending = False
        self._info_poll_active = False
        self._info_cancellable: Optional[Gio.Cancellable] = None
        
        # UI references
        self._status_chip: Optional[Gtk.Label] = None
        self._model_chip: Optional[Gtk.Label] = None
        self._latency_chip: Optional[Gtk.Label] = None
        self._typing_indicator: Optional[Gtk.Box] = None
        self._status_label: Optional[Gtk.Label] = None
        self._status_spinner: Optional[Gtk.Spinner] = None
        self._chat_scroller: Optional[Gtk.ScrolledWindow] = None
        
        # Truth Panel chips (from /info endpoint)
        self._time_chip: Optional[Gtk.Label] = None
        self._git_chip: Optional[Gtk.Label] = None
        self._ollama_chip: Optional[Gtk.Label] = None
        self._github_chip: Optional[Gtk.Label] = None
        self._info_poll_id: Optional[int] = None
        
        # Per-message meta display
        self._last_meta_chip: Optional[Gtk.Label] = None
        
        print("[TalkColumn] Building UI...")
        self._build_ui()
        print("[TalkColumn] Loading settings...")
        self._load_settings()  # Sticky settings (Phase 2C)
        print("[TalkColumn] Connecting to roxy...")
        self._connect_to_roxy()
        print("[TalkColumn] Truth panel awaiting unified snapshot...")
        print("[TalkColumn] ========== INIT COMPLETE ==========" )
    
    def _save_settings(self):
        """Persist sticky settings to JSON."""
        from pathlib import Path
        import json
        try:
            settings_dir = Path.home() / ".config" / "roxy-command-center"
            settings_dir.mkdir(parents=True, exist_ok=True)
            settings_file = settings_dir / "settings.json"
            
            data = {}
            if settings_file.exists():
                try:
                    data = json.loads(settings_file.read_text())
                except:
                    pass
            
            # Update values
            routes = ["AUTO", "CHAT", "RAG", "EXEC"]
            if hasattr(self, '_route_dropdown'):
                idx_route = self._route_dropdown.get_selected()
                if idx_route < len(routes):
                    data["route_mode"] = routes[idx_route]
            
            pools = ["AUTO", "W5700X", "6900XT"]
            if hasattr(self, '_pool_dropdown'):
                idx_pool = self._pool_dropdown.get_selected()
                if idx_pool < len(pools):
                    data["pool_mode"] = pools[idx_pool]
                
            settings_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[Talk] Failed to save settings: {e}")

    def _load_settings(self):
        """Load sticky settings."""
        from pathlib import Path
        import json
        try:
            settings_file = Path.home() / ".config" / "roxy-command-center" / "settings.json"
            if not settings_file.exists():
                return
                
            data = json.loads(settings_file.read_text())
            
            route = data.get("route_mode", "AUTO")
            routes = ["AUTO", "CHAT", "RAG", "EXEC"]
            if route in routes and hasattr(self, '_route_dropdown'):
                self._route_dropdown.set_selected(routes.index(route))
                self._routing_mode = route
                print(f"[Talk] Loaded sticky route: {route}")
            
            pool = data.get("pool_mode", "AUTO")
            # Normalize legacy aliases to hardware names
            pool_aliases = {"FAST": "6900XT", "BIG": "W5700X"}
            pool = pool_aliases.get(pool, pool)
            pools = ["AUTO", "W5700X", "6900XT"]
            if pool in pools and hasattr(self, '_pool_dropdown'):
                self._pool_dropdown.set_selected(pools.index(pool))
                self._pool_mode = pool
                print(f"[Talk] Loaded sticky pool: {pool}")
                
        except Exception as e:
            print(f"[Talk] Failed to load settings: {e}")

    def _build_ui(self):
        # Header with context chips
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header.set_margin_top(12)
        header.set_margin_start(12)
        header.set_margin_end(12)
        self.append(header)
        
        # Title row
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.append(title_row)
        
        title = Gtk.Label(label="Roxy")
        title.add_css_class("title-2")
        title.set_xalign(0)
        title_row.append(title)
        
        # Connection button
        connect_btn = Gtk.Button(label="Connect")
        connect_btn.add_css_class("suggested-action")
        connect_btn.add_css_class("pill")
        connect_btn.connect("clicked", self._on_connect_click)
        title_row.append(connect_btn)
        
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        title_row.append(spacer)
        
        # Context chips row - LIVE data from roxy-core
        chips_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        chips_box.set_margin_bottom(8)
        header.append(chips_box)
        
        # Status chip
        self._status_chip = Gtk.Label(label="⚪ Disconnected")
        self._status_chip.add_css_class("dim-label")
        self._status_chip.add_css_class("caption")
        self._status_chip.set_tooltip_text("Connection status")
        self._status_chip.set_xalign(0)
        self._status_chip.set_width_chars(20)
        chips_box.append(self._status_chip)
        
        # Model chip
        self._model_chip = Gtk.Label(label="🧠 --")
        self._model_chip.add_css_class("dim-label")
        self._model_chip.add_css_class("caption")
        self._model_chip.set_tooltip_text("Current model")
        self._model_chip.set_xalign(0)
        self._model_chip.set_width_chars(18)
        chips_box.append(self._model_chip)
        
        # Latency chip
        self._latency_chip = Gtk.Label(label="⏱️ --")
        self._latency_chip.add_css_class("dim-label")
        self._latency_chip.add_css_class("caption")
        self._latency_chip.set_tooltip_text("Response latency")
        self._latency_chip.set_xalign(0)
        self._latency_chip.set_width_chars(14)
        chips_box.append(self._latency_chip)
        
        # Identity chip
        identity_chip = Gtk.Label(label="🎵 MindSong")
        identity_chip.add_css_class("dim-label")
        identity_chip.add_css_class("caption")
        identity_chip.set_tooltip_text("Active project context")
        chips_box.append(identity_chip)

        # Truth Panel row - authoritative server data from /info
        truth_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        truth_box.set_margin_bottom(4)
        header.append(truth_box)
        
        # Server time chip
        self._time_chip = Gtk.Label(label="🕐 --:--")
        self._time_chip.add_css_class("dim-label")
        self._time_chip.add_css_class("caption")
        self._time_chip.set_tooltip_text("Server time")
        self._time_chip.set_xalign(0)
        self._time_chip.set_width_chars(18)  # Fixed width to prevent layout thrash
        truth_box.append(self._time_chip)
        
        # Git state chip
        self._git_chip = Gtk.Label(label="🔀 --")
        self._git_chip.add_css_class("dim-label")
        self._git_chip.add_css_class("caption")
        self._git_chip.set_tooltip_text("Git branch & commit")
        self._git_chip.set_xalign(0)
        self._git_chip.set_width_chars(22)  # Fixed width to prevent layout thrash
        truth_box.append(self._git_chip)
        
        # Ollama status chip
        self._ollama_chip = Gtk.Label(label="🦙 --")
        self._ollama_chip.add_css_class("dim-label")
        self._ollama_chip.add_css_class("caption")
        self._ollama_chip.set_tooltip_text("Ollama connection")
        self._ollama_chip.set_xalign(0)
        self._ollama_chip.set_width_chars(22)  # Fixed width to prevent layout thrash
        truth_box.append(self._ollama_chip)
        
        # GitHub status chip
        self._github_chip = Gtk.Label(label="🐙 --")
        self._github_chip.add_css_class("dim-label")
        self._github_chip.add_css_class("caption")
        self._github_chip.set_tooltip_text("GitHub API status")
        self._github_chip.set_xalign(0)
        self._github_chip.set_width_chars(10)  # Fixed width to prevent layout thrash
        truth_box.append(self._github_chip)

        # GitNexus status chip
        self._gitnexus_chip = Gtk.Label(label="🧬 --")
        self._gitnexus_chip.add_css_class("dim-label")
        self._gitnexus_chip.add_css_class("caption")
        self._gitnexus_chip.set_tooltip_text("GitNexus code-truth status")
        self._gitnexus_chip.set_xalign(0)
        self._gitnexus_chip.set_width_chars(18)
        truth_box.append(self._gitnexus_chip)

        # Brain Atlas status chip
        self._atlas_chip = Gtk.Label(label="🗺️ --")
        self._atlas_chip.add_css_class("dim-label")
        self._atlas_chip.add_css_class("caption")
        self._atlas_chip.set_tooltip_text("Brain Atlas system graph status")
        self._atlas_chip.set_xalign(0)
        self._atlas_chip.set_width_chars(18)
        truth_box.append(self._atlas_chip)

        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        status_box.set_margin_bottom(4)
        header.append(status_box)

        self._status_spinner = Gtk.Spinner()
        self._status_spinner.set_visible(False)
        status_box.append(self._status_spinner)

        self._status_label = Gtk.Label(label="Connect to Roxy to begin.")
        self._status_label.set_xalign(0)
        self._status_label.set_wrap(True)
        self._status_label.add_css_class("dim-label")
        status_box.append(self._status_label)
        
        # Chat transcript
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._chat_scroller = scrolled
        self.append(scrolled)
        
        self.chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scrolled.set_child(self.chat_box)
        
        # Typing indicator (hidden by default)
        self._typing_indicator = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._typing_indicator.set_margin_start(12)
        self._typing_indicator.set_margin_bottom(8)
        self._typing_indicator.set_visible(False)
        self.append(self._typing_indicator)
        
        typing_spinner = Gtk.Spinner()
        typing_spinner.start()
        self._typing_indicator.append(typing_spinner)
        
        typing_label = Gtk.Label(label="Roxy is thinking...")
        typing_label.add_css_class("dim-label")
        self._typing_indicator.append(typing_label)
        
        # Input area
        input_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        input_area.set_margin_start(12)
        input_area.set_margin_end(12)
        input_area.set_margin_bottom(12)
        self.append(input_area)
        
        # Mode toggle row
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_area.append(mode_box)
        
        mode_label = Gtk.Label(label="Mode:")
        mode_label.add_css_class("dim-label")
        mode_box.append(mode_label)
        
        self.draft_btn = Gtk.ToggleButton(label="Draft")
        self.draft_btn.set_active(True)
        self.draft_btn.set_tooltip_text("Roxy drafts, you approve (safe)")
        self.draft_btn.connect("toggled", self._on_mode_toggle, True)
        mode_box.append(self.draft_btn)
        
        self.send_btn = Gtk.ToggleButton(label="Send")
        self.send_btn.set_tooltip_text("Roxy sends directly (requires explicit arming)")
        self.send_btn.connect("toggled", self._on_mode_toggle, False)
        mode_box.append(self.send_btn)
        
        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        mode_box.append(spacer)
        
        # Speak toggle (Option B: manual button)
        self.speak_btn = Gtk.ToggleButton()
        self.speak_btn.set_icon_name("audio-speakers-symbolic")
        self.speak_btn.set_tooltip_text("Toggle voice output (Option B)")
        self.speak_btn.connect("toggled", self._on_speak_toggle)
        mode_box.append(self.speak_btn)
        
        # === OPERATOR CONTROLS ROW (Chief's Truth Panel) ===
        operator_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_area.append(operator_box)
        
        # Routing Mode: CHAT/RAG/EXEC/AUTO
        route_label = Gtk.Label(label="Route:")
        route_label.add_css_class("dim-label")
        operator_box.append(route_label)
        
        self._route_dropdown = Gtk.DropDown.new_from_strings(["AUTO", "CHAT", "RAG", "EXEC"])
        self._route_dropdown.set_selected(0)  # AUTO by default
        self._route_dropdown.set_tooltip_text("AUTO=smart routing, CHAT=direct LLM, RAG=retrieval, EXEC=strict")
        self._route_dropdown.connect("notify::selected", self._on_route_changed)
        operator_box.append(self._route_dropdown)
        
        # Pool: AUTO/W5700X/6900XT (hardware canonical names)
        pool_label = Gtk.Label(label="Pool:")
        pool_label.add_css_class("dim-label")
        pool_label.set_margin_start(12)
        operator_box.append(pool_label)

        self._pool_dropdown = Gtk.DropDown.new_from_strings(["AUTO", "W5700X", "6900XT"])
        self._pool_dropdown.set_selected(0)  # AUTO by default
        self._pool_dropdown.set_tooltip_text("AUTO=smart selection, W5700X=port 11434, 6900XT=port 11435")
        self._pool_dropdown.connect("notify::selected", self._on_pool_changed)
        operator_box.append(self._pool_dropdown)
        
        # Spacer
        op_spacer = Gtk.Box()
        op_spacer.set_hexpand(True)
        operator_box.append(op_spacer)
        
        # Last execution meta chip (updates after each message)
        self._last_meta_chip = Gtk.Label(label="")
        self._last_meta_chip.add_css_class("dim-label")
        self._last_meta_chip.add_css_class("caption")
        self._last_meta_chip.set_tooltip_text("Last request execution details")
        operator_box.append(self._last_meta_chip)
        
        # Input row
        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_area.append(input_row)
        
        # Voice button (push-to-talk)
        voice_btn = Gtk.Button()
        voice_btn.set_icon_name("audio-input-microphone-symbolic")
        voice_btn.set_tooltip_text("Push to talk (Phase 2)")
        voice_btn.add_css_class("circular")
        voice_btn.connect("clicked", self._on_voice_click)
        input_row.append(voice_btn)
        
        # Text entry
        self.entry = Gtk.Entry()
        self.entry.set_hexpand(True)
        self.entry.set_placeholder_text("Talk to Roxy...")
        self.entry.connect("activate", self._on_send)
        input_row.append(self.entry)
        
        # Send button
        send_btn = Gtk.Button(label="Send")
        send_btn.add_css_class("suggested-action")
        send_btn.connect("clicked", self._on_send)
        input_row.append(send_btn)
    
    def _connect_to_roxy(self):
        """Connect to roxy-core via ChatService."""
        self._chat_service.connect(
            identity=ServiceIdentity.MINDSONG,
            on_message=self._on_chat_message,
            on_status_change=self._on_status_change,
            on_typing=self._on_typing_change,
            on_meta_update=self._on_meta_update
        )

    def _short_model_name(self, model: Optional[str]) -> str:
        if not model or model == "none":
            return ""
        short = str(model)
        replacements = {
            "qwen2.5-coder:14b-instruct": "Qwen14B",
            "qwen2.5-coder:14b": "Qwen14B",
            "llama3.1:8b": "L3.8B",
        }
        for source, target in replacements.items():
            short = short.replace(source, target)
        return short.split(":")[0]

    def _display_model_name(self, meta: dict) -> str:
        route = meta.get("route") or ""
        deterministic_routes = {
            "memory_recall",
            "memory_store",
            "git_query",
            "local_fastpath_git_status",
            "time_direct",
            "ping_direct",
        }
        model_used = meta.get("model_used")
        if route in deterministic_routes:
            return self._short_model_name(model_used)
        return self._short_model_name(model_used or meta.get("selected_model"))

    def _is_deterministic_route(self, route: str) -> bool:
        return route in {
            "memory_recall",
            "memory_store",
            "git_query",
            "local_fastpath_git_status",
            "time_direct",
            "ping_direct",
        }

    def _format_last_execution_summary(self, meta: dict) -> tuple[str, str]:
        mode = (meta.get("mode") or "??").upper()
        pool = (meta.get("pool") or "AUTO").upper()
        route = meta.get("route") or "?"
        model = self._display_model_name(meta)
        total_ms = meta.get("total_ms")
        total_ms_text = f"{int(round(float(total_ms)))}ms" if total_ms is not None else ""
        repo = meta.get("repo") or {}
        memory = meta.get("memory") or {}
        truth_sources = meta.get("truth_sources") or {}
        gitnexus = meta.get("gitnexus") or {}
        atlas = meta.get("atlas") or {}

        summary_parts = []

        if repo.get("branch"):
            repo_state = "dirty" if repo.get("is_dirty") else "clean"
            changed = repo.get("changed_count")
            repo_text = f"repo:{repo['branch']}"
            if isinstance(changed, int):
                repo_text += f" {repo_state}:{changed}"
            else:
                repo_text += f" {repo_state}"
            summary_parts.append(repo_text)

        memory_backend = (
            memory.get("recall_backend")
            or memory.get("store_backend")
            or memory.get("learning_backend")
            or memory.get("backend")
        )
        if route == "memory_recall":
            mem_text = f"mem:{memory_backend or 'unknown'}"
            if memory.get("recall_succeeded") is True:
                mem_text += " hit"
            elif memory.get("recall_succeeded") is False:
                mem_text += " miss"
            summary_parts.append(mem_text)
        elif route == "memory_store":
            learned = memory.get("facts_learned")
            mem_text = f"learn:{learned}" if learned is not None else "learn:?"
            if memory_backend:
                mem_text += f" {memory_backend}"
            summary_parts.append(mem_text)
        elif memory_backend and memory.get("context_injected"):
            summary_parts.append(f"ctx:{memory_backend}")

        if gitnexus.get("available"):
            if gitnexus.get("indexed") and gitnexus.get("fresh") is False:
                summary_parts.append("nexus:stale")
            elif gitnexus.get("indexed"):
                summary_parts.append("nexus:fresh")
            else:
                summary_parts.append("nexus:live")

        if atlas.get("available"):
            node_count = atlas.get("node_count")
            if isinstance(node_count, int):
                summary_parts.append(f"atlas:{node_count}n")

        if model:
            summary_parts.append(f"model:{model}")

        if total_ms_text:
            summary_parts.append(total_ms_text)

        text = f"[{mode}:{pool}] {route}"
        if summary_parts:
            text += " • " + " • ".join(summary_parts[:3])

        lines = [
            "Last Execution",
            f"Trace: {meta.get('trace_id', '--')}",
            f"Surface: {meta.get('operator_surface', '--')}",
            f"Mode: {mode}",
            f"Pool: {pool}",
            f"Route: {route}",
        ]
        primary_truth = truth_sources.get("primary")
        if primary_truth:
            lines.append(f"Truth: {primary_truth}")
        sources = truth_sources.get("sources") or []
        if sources:
            lines.append("Sources: " + ", ".join(str(source) for source in sources))
        if model:
            lines.append(f"Model: {model}")
        if total_ms_text:
            lines.append(f"Total: {total_ms_text}")

        if repo:
            lines.append(
                "Repo: "
                + str(repo.get("repo_path") or "--")
            )
            lines.append(
                "Repo State: "
                + f"{repo.get('branch', '--')} "
                + ("dirty" if repo.get("is_dirty") else "clean")
                + f" ({repo.get('changed_count', 0)} changed)"
            )
            modified = repo.get("modified_paths") or []
            if modified:
                lines.append("Modified: " + ", ".join(modified[:5]))
            untracked = repo.get("untracked_paths") or []
            if untracked:
                lines.append("Untracked: " + ", ".join(untracked[:3]))

        if memory:
            lines.append(
                "Memory: backend="
                + str(memory_backend or "--")
                + f", recall={memory.get('recall_succeeded')}, store={memory.get('store_succeeded')}, learned={memory.get('facts_learned')}"
            )
            learned_facts = memory.get("learned_facts") or []
            if learned_facts:
                preview = []
                for item in learned_facts[:3]:
                    if isinstance(item, dict):
                        category = item.get("category") or "fact"
                        preference = item.get("preference") or item.get("value") or "?"
                        preview.append(f"{category}={preference}")
                    else:
                        preview.append(str(item))
                lines.append("Learned: " + ", ".join(preview))

        if gitnexus:
            lines.append(
                "GitNexus: repo="
                + str(gitnexus.get("repo_name") or "--")
                + f", live={gitnexus.get('available')}, indexed={gitnexus.get('indexed')}, fresh={gitnexus.get('fresh')}, indexed_at={gitnexus.get('indexed_at') or '--'}"
            )
            if gitnexus.get("indexed_commit") or gitnexus.get("current_commit"):
                lines.append(
                    "GitNexus Commits: indexed="
                    + str(gitnexus.get("indexed_commit") or "--")
                    + " current="
                    + str(gitnexus.get("current_commit") or "--")
                )

        if atlas:
            lines.append(
                "Atlas: built_at="
                + str(atlas.get("built_at") or "--")
                + f", nodes={atlas.get('node_count', 0)}, edges={atlas.get('edge_count', 0)}"
            )

        return text, "\n".join(lines)

    def _on_meta_update(self, meta: dict):
        """Update the last execution metadata chip."""
        if self._disposed:
            return
        if not self._last_meta_chip:
            return

        text, tooltip = self._format_last_execution_summary(meta)
        self._last_meta_chip.set_label(text)
        self._last_meta_chip.set_tooltip_text(tooltip)

        model = self._display_model_name(meta)
        route = meta.get("route") or "?"
        if self._model_chip:
            if model:
                self._model_chip.set_label(f"🧠 {model}")
            elif route in ("memory_recall", "memory_store", "git_query", "local_fastpath_git_status", "time_direct", "ping_direct"):
                self._model_chip.set_label("🧠 deterministic")
        if self._latency_chip and meta.get("total_ms") is not None:
            core_ms = int(round(float(meta["total_ms"])))
            self._latency_chip.set_label(f"⏱️ {core_ms}ms")
            self._latency_chip.set_tooltip_text(
                f"Core execution: {core_ms}ms\nEnd-to-end UI/transport: {self._chat_service.latency_ms}ms"
            )

    def update_snapshot(self, data: dict):
        """Apply the latest unified snapshot from roxy-core."""
        if self._disposed:
            return

        snapshot_info = data.get("info") or data.get("_raw", {}).get("info") or data.get("truth") or {}
        if snapshot_info:
            self._update_truth_panel(snapshot_info)
            return

        snapshot_error = (
            data.get("_raw", {}).get("snapshot_error")
            or data.get("_raw", {}).get("remote_error")
            or data.get("_raw", {}).get("error")
        )
        if snapshot_error:
            self._update_truth_panel_error(str(snapshot_error))
    
    def _start_info_polling(self):
        """Start polling /info endpoint for Truth Panel."""
        if self._disposed or self._info_poll_active:
            return

        self._info_poll_active = True
        self._info_poll_id = GLib.timeout_add_seconds(10, self._poll_info)
        GLib.idle_add(self._poll_info_once)

    def _poll_info_once(self):
        """Run exactly one immediate /info fetch after startup."""
        self._poll_info()
        return False

    def _stop_info_polling(self):
        """Cancel truth-panel polling and any active /info request."""
        self._info_poll_active = False

        if self._info_poll_id is not None:
            try:
                GLib.source_remove(self._info_poll_id)
            except Exception:
                pass
            self._info_poll_id = None

        cancellable = self._info_cancellable
        self._info_cancellable = None
        if cancellable is not None and not cancellable.is_cancelled():
            try:
                cancellable.cancel()
            except Exception:
                pass

        self._info_fetch_pending = False
    
    def _poll_info(self) -> bool:
        """Fetch /info endpoint and update Truth Panel chips."""
        if self._disposed or not self._info_poll_active:
            return False

        if self._info_fetch_pending:
            return True

        message = Soup.Message.new("GET", "http://127.0.0.1:8766/info")
        message.get_request_headers().append("User-Agent", "roxy-command-center/truth-panel")

        cancellable = Gio.Cancellable()
        self._info_fetch_pending = True
        self._info_cancellable = cancellable

        self._info_session.send_and_read_async(
            message,
            GLib.PRIORITY_DEFAULT,
            cancellable,
            self._on_info_response,
            None,
        )
        return True

    def _on_info_response(self, session, result, _user_data):
        """Handle async /info completion on the GTK main loop."""
        cancellable = self._info_cancellable
        self._info_cancellable = None
        try:
            response_bytes = session.send_and_read_finish(result)
            if self._disposed:
                return

            raw = bytes(response_bytes.get_data()).decode("utf-8")
            data = json.loads(raw) if raw else {}
            self._update_truth_panel(data)
        except Exception as exc:
            cancelled = bool(cancellable and cancellable.is_cancelled())
            if self._disposed or cancelled:
                return
            self._update_truth_panel_error(str(exc))
        finally:
            self._info_fetch_pending = False
    
    def _update_truth_panel(self, data: dict):
        """Update Truth Panel chips with /info data."""
        if self._disposed:
            return
        if self._time_chip:
            try:
                ts = data.get("server_time_iso", "")
                if ts:
                    # Parse ISO format for full date/time context
                    dt = datetime.fromisoformat(ts)
                    self._time_chip.set_label(f"🕐 {dt.strftime('%Y-%m-%d %H:%M')}")
            except:
                self._time_chip.set_label("🕐 --")
        
        if self._git_chip:
            git = data.get("git", {})
            branch = git.get("branch", "?")
            sha = git.get("head_sha", "?")[:7]
            # State: clean (✔) or dirty (⚠️)
            state = "⚠️" if git.get("dirty") else "✔"
            self._git_chip.set_label(f"🔀 {branch} • {sha} • {state}")
            self._git_chip.set_tooltip_text(git.get("last_commit_subject", ""))
        
        if self._ollama_chip:
            ollama = data.get("ollama", {})
            pools = ollama.get("pools", {})
            
            # Show pool status: W5700X: ok/err, 6900XT: ok/err
            w5700x_status = "unset"
            if pools.get("w5700x", {}).get("configured"):
                w5700x_status = "ok" if pools["w5700x"].get("reachable") else "err"

            xt6900_status = "unset"
            if pools.get("6900xt", {}).get("configured"):
                xt6900_status = "ok" if pools["6900xt"].get("reachable") else "err"

            self._ollama_chip.set_label(f"🦙 W5700X:{w5700x_status} 6900XT:{xt6900_status}")

            # Tooltip with details
            tooltip_parts = []
            if pools.get("w5700x", {}).get("configured"):
                w5700x = pools["w5700x"]
                tooltip_parts.append(f"W5700X: {w5700x['url']} ({w5700x.get('latency_ms', '??')}ms)" + (f" err: {w5700x['error']}" if not w5700x.get("reachable") else ""))
            if pools.get("6900xt", {}).get("configured"):
                xt6900 = pools["6900xt"]
                tooltip_parts.append(f"6900XT: {xt6900['url']} ({xt6900.get('latency_ms', '??')}ms)" + (f" err: {xt6900['error']}" if not xt6900.get("reachable") else ""))
            
            self._ollama_chip.set_tooltip_text("\n".join(tooltip_parts) if tooltip_parts else "No pools configured")
            
            # Color based on any reachable
            any_reachable = any(p.get("reachable", False) for p in pools.values() if isinstance(p, dict))
            if any_reachable:
                self._ollama_chip.remove_css_class("error")
            else:
                self._ollama_chip.add_css_class("error")
        
        if self._github_chip:
            github = data.get("github", {})
            
            # Show GitHub status: configured + reachable
            if github.get("configured"):
                status = "ok" if github.get("reachable") else "err"
                self._github_chip.set_label(f"🐙 {status}")
                
                # Tooltip with details
                tooltip_parts = []
                if github.get("latency_ms"):
                    tooltip_parts.append(f"Latency: {github['latency_ms']}ms")
                if github.get("rate_limit"):
                    rl = github["rate_limit"]
                    tooltip_parts.append(f"Rate limit: {rl.get('remaining', '?')}/{rl.get('limit', '?')}")
                if github.get("error"):
                    tooltip_parts.append(f"Error: {github['error']}")
                
                self._github_chip.set_tooltip_text("\n".join(tooltip_parts) if tooltip_parts else "GitHub API connected")
                
                # Color based on reachable
                if github.get("reachable"):
                    self._github_chip.remove_css_class("error")
                else:
                    self._github_chip.add_css_class("error")
            else:
                self._github_chip.set_label("🐙 unset")
                self._github_chip.set_tooltip_text("GitHub token not configured")
                self._github_chip.add_css_class("error")

        if self._gitnexus_chip:
            gitnexus = data.get("gitnexus", {})
            if gitnexus.get("available"):
                if gitnexus.get("indexed") and gitnexus.get("fresh") is False:
                    status = "stale"
                elif gitnexus.get("indexed"):
                    status = "fresh"
                else:
                    status = "live"
                self._gitnexus_chip.set_label(f"🧬 {status}")
                stats = gitnexus.get("stats") or {}
                self._gitnexus_chip.set_tooltip_text(
                    "\n".join(
                        [
                            f"Repo: {gitnexus.get('repo_name', '--')}",
                            f"Indexed: {gitnexus.get('indexed')}",
                            f"Fresh: {gitnexus.get('fresh')}",
                            f"Indexed At: {gitnexus.get('indexed_at') or '--'}",
                            f"Indexed Commit: {gitnexus.get('indexed_commit') or '--'}",
                            f"Current Commit: {gitnexus.get('current_commit') or '--'}",
                            f"Meta Repo Path: {gitnexus.get('meta_repo_path') or '--'}",
                            f"Files: {stats.get('files', 0)} Nodes: {stats.get('nodes', 0)} Processes: {stats.get('processes', 0)}",
                            f"Staleness: {gitnexus.get('staleness_reason') or '--'}",
                            f"Error: {gitnexus.get('error') or '--'}",
                        ]
                    )
                )
                if gitnexus.get("indexed") and gitnexus.get("fresh") is not False:
                    self._gitnexus_chip.remove_css_class("error")
                else:
                    self._gitnexus_chip.add_css_class("error")
            else:
                self._gitnexus_chip.set_label("🧬 off")
                self._gitnexus_chip.set_tooltip_text(f"GitNexus unavailable: {gitnexus.get('error') or '--'}")
                self._gitnexus_chip.add_css_class("error")

        if self._atlas_chip:
            atlas = data.get("atlas", {})
            if atlas.get("available"):
                node_count = int(atlas.get("node_count") or 0)
                edge_count = int(atlas.get("edge_count") or 0)
                self._atlas_chip.set_label(f"🗺️ {node_count}/{edge_count}")
                tooltip_lines = [
                    f"Built At: {atlas.get('built_at') or '--'}",
                    f"Nodes: {node_count}",
                    f"Edges: {edge_count}",
                ]
                warnings = atlas.get("warnings") or []
                if warnings:
                    tooltip_lines.append("Warnings: " + ", ".join(str(item) for item in warnings[:3]))
                neo4j = atlas.get("neo4j") or {}
                if neo4j:
                    tooltip_lines.append(
                        f"Neo4j: reachable={neo4j.get('reachable')} upserted={neo4j.get('upserted')} error={neo4j.get('error') or '--'}"
                    )
                self._atlas_chip.set_tooltip_text("\n".join(tooltip_lines))
                if warnings:
                    self._atlas_chip.add_css_class("error")
                else:
                    self._atlas_chip.remove_css_class("error")
            else:
                self._atlas_chip.set_label("🗺️ off")
                warnings = atlas.get("warnings") or []
                self._atlas_chip.set_tooltip_text("Atlas unavailable: " + ", ".join(str(item) for item in warnings[:3]))
                self._atlas_chip.add_css_class("error")
    
    def _update_truth_panel_error(self, error: str):
        """Handle /info fetch error."""
        if self._disposed:
            return
        if self._time_chip:
            self._time_chip.set_label("🕐 --:--")
        if self._git_chip:
            self._git_chip.set_label("🔀 --")
        if self._ollama_chip:
            self._ollama_chip.set_label("🦙 ❌")
            self._ollama_chip.set_tooltip_text(f"roxy-core unreachable: {error}")
        if self._github_chip:
            self._github_chip.set_label("🐙 --")
            self._github_chip.set_tooltip_text(f"roxy-core unreachable: {error}")
        if self._gitnexus_chip:
            self._gitnexus_chip.set_label("🧬 --")
            self._gitnexus_chip.set_tooltip_text(f"roxy-core unreachable: {error}")
        if self._atlas_chip:
            self._atlas_chip.set_label("🗺️ --")
            self._atlas_chip.set_tooltip_text(f"roxy-core unreachable: {error}")

    def _on_connect_click(self, button):
        """Manual reconnect."""
        if self._disposed:
            return
        if self._status_chip:
            self._status_chip.set_label("🟡 Connecting")
        if self._model_chip:
            self._model_chip.set_label("🧠 --")
        if self._latency_chip:
            self._latency_chip.set_label("⏱️ --")
        if self._status_label:
            self._status_label.set_label("Connecting to Roxy…")
        if self._status_spinner:
            self._status_spinner.set_visible(True)
            self._status_spinner.start()
        if self._typing_indicator:
            self._typing_indicator.set_visible(False)
        self._connect_to_roxy()
    
    def _on_chat_message(self, message: ServiceChatMessage):
        """Called when a new message arrives (user or assistant)."""
        if self._disposed:
            return
        # Convert to UI widget
        ui_message = ChatMessage(
            id=message.id,
            role=message.role,
            content=message.content,
            timestamp=message.timestamp
        )
        widget = ChatMessage_Widget(ui_message)
        self.chat_box.append(widget)
        self._scroll_chat_to_bottom()
        
        # Update latency chip for assistant messages
        if message.role == "assistant":
            latency = self._chat_service.latency_ms
            latest_meta = getattr(self._chat_service, "_last_execution_meta", {}) or {}
            total_ms = latest_meta.get("total_ms")
            if total_ms is not None:
                core_ms = int(round(float(total_ms)))
                self._latency_chip.set_label(f"⏱️ {core_ms}ms")
                self._latency_chip.set_tooltip_text(
                    f"Core execution: {core_ms}ms\nEnd-to-end UI/transport: {latency}ms"
                )
            else:
                self._latency_chip.set_label(f"⏱️ {latency}ms")
                self._latency_chip.set_tooltip_text("Response latency")
            
            # Speak if speak mode enabled (Option B)
            if self._speak_mode:
                self._voice_service.speak(message.content)

    def _append_system_message(self, text: str):
        if self._disposed:
            return
        message = ChatMessage(
            id=str(uuid.uuid4()),
            role="system",
            content=text,
            timestamp=datetime.now()
        )
        widget = ChatMessage_Widget(message)
        self.chat_box.append(widget)
        self._scroll_chat_to_bottom()

    def _scroll_chat_to_bottom(self):
        if self._disposed or not self._chat_scroller:
            return

        def _apply_scroll():
            if self._disposed or not self._chat_scroller:
                return False
            adjustment = self._chat_scroller.get_vadjustment()
            if adjustment is None:
                return False
            adjustment.set_value(max(0.0, adjustment.get_upper() - adjustment.get_page_size()))
            return False

        GLib.idle_add(_apply_scroll)
    
    def _on_status_change(self, status: ConnectionStatus, message: str):
        """Called when connection status changes."""
        if self._disposed:
            return
        status_icons = {
            ConnectionStatus.DISCONNECTED: "⚪",
            ConnectionStatus.CONNECTING: "🟡",
            ConnectionStatus.WARMING: "🟠",
            ConnectionStatus.CONNECTED: "🟢",
            ConnectionStatus.ERROR: "🔴"
        }
        icon = status_icons.get(status, "⚪")
        
        # Update chips
        if self._status_chip:
            self._status_chip.set_label(f"{icon} {status.value.title()}")

        if self._status_label:
            detail = message or status.value.title()
            self._status_label.set_label(detail)

        if self._status_spinner:
            show_spinner = status in (ConnectionStatus.CONNECTING, ConnectionStatus.WARMING)
            self._status_spinner.set_visible(show_spinner)
            if show_spinner:
                self._status_spinner.start()
            else:
                self._status_spinner.stop()

        if status == ConnectionStatus.CONNECTED:
            latest_meta = getattr(self._chat_service, "_last_execution_meta", {}) or {}
            route = latest_meta.get("route") or ""
            model = self._display_model_name(latest_meta)
            if self._model_chip:
                if model:
                    self._model_chip.set_label(f"🧠 {model}")
                elif self._is_deterministic_route(route):
                    self._model_chip.set_label("🧠 deterministic")
                else:
                    self._model_chip.set_label(f"🧠 {self._chat_service.model or 'ready'}")
        elif status == ConnectionStatus.WARMING:
            if self._model_chip:
                self._model_chip.set_label("🧠 warming…")
        elif status in (ConnectionStatus.DISCONNECTED, ConnectionStatus.ERROR):
            if self._model_chip:
                self._model_chip.set_label("🧠 --")

        if status != ConnectionStatus.CONNECTED and self._latency_chip:
            self._latency_chip.set_label("⏱️ --")
    
    def _on_typing_change(self, is_typing: bool):
        """Called when typing indicator should show/hide."""
        if self._disposed:
            return
        self._is_typing = is_typing
        if self._typing_indicator:
            self._typing_indicator.set_visible(is_typing)
    
    def _on_mode_toggle(self, button, is_draft: bool):
        if button.get_active():
            self._draft_mode = is_draft
            if is_draft:
                self.send_btn.set_active(False)
                self._chat_service.set_mode(ChatMode.DRAFT)
            else:
                self.draft_btn.set_active(False)
                self._chat_service.set_mode(ChatMode.SEND)
                # Warn about send mode
                print("[Talk] WARNING: Send mode enabled - Roxy will execute without approval")
    
    def _on_route_changed(self, dropdown, _pspec):
        """Handle routing mode change (CHAT/RAG/EXEC/AUTO)."""
        routes = ["AUTO", "CHAT", "RAG", "EXEC"]
        idx = dropdown.get_selected()
        self._routing_mode = routes[idx] if idx < len(routes) else "AUTO"
        print(f"[Talk] Routing mode: {self._routing_mode}")
        self._save_settings()
    
    def _on_pool_changed(self, dropdown, _pspec):
        """Handle pool change (AUTO/W5700X/6900XT)."""
        pools = ["AUTO", "W5700X", "6900XT"]
        idx = dropdown.get_selected()
        self._pool_mode = pools[idx] if idx < len(pools) else "AUTO"
        print(f"[Talk] Pool: {self._pool_mode}")
        self._save_settings()
    
    def _on_speak_toggle(self, button):
        """Toggle speak mode (Option B)."""
        self._speak_mode = button.get_active()
        self._voice_service.speak_mode = self._speak_mode
        if self._speak_mode:
            print("[Talk] Speak mode ON - responses will be spoken")
        else:
            print("[Talk] Speak mode OFF")
    
    def _on_voice_click(self, button):
        """Voice button - push-to-talk (Phase 2 stub)."""
        print("[Talk] Voice input not yet implemented (Phase 2)")
        # In Phase 2: self._voice_service.start_recording()
    
    def _on_send(self, widget):
        """Send message to roxy-core."""
        if self._disposed:
            return
        text = self.entry.get_text().strip()
        if not text:
            return
        
        status = self._chat_service.status
        if status in (ConnectionStatus.DISCONNECTED, ConnectionStatus.ERROR):
            if self._status_label:
                self._status_label.set_label("Not connected. Click Connect.")
            self._append_system_message("⚠️ Not connected. Click Connect to retry.")
            return

        self.entry.set_text("")
        
        # Pass operator controls to chat service (Chief's Truth Panel)
        self._chat_service.send_message(
            text, 
            routing_mode=self._routing_mode if self._routing_mode != "AUTO" else "",
            pool=self._pool_mode if self._pool_mode != "AUTO" else ""
        )

    def shutdown(self):
        """Release background work before the widget leaves the UI tree."""
        if self._disposed:
            return

        self._disposed = True
        self._stop_info_polling()

        try:
            self._chat_service.disconnect()
        except Exception as exc:
            print(f"[Talk] Chat disconnect cleanup failed: {exc}")

        if self._typing_indicator:
            self._typing_indicator.set_visible(False)
        if self._status_spinner:
            self._status_spinner.stop()
            self._status_spinner.set_visible(False)

    def do_unroot(self):
        self.shutdown()
        return super().do_unroot()


class ExecutionRunCard(Gtk.Box):
    """A card showing an execution run."""
    
    def __init__(self, run: ExecutionRun):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.run = run
        self.add_css_class("card")
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_bottom(8)
        
        # Main content
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        self.append(content)
        
        # Title row
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        content.append(title_row)
        
        # Status icon
        status_icons = {
            RunStatus.QUEUED: "content-loading-symbolic",
            RunStatus.RUNNING: "emblem-synchronizing-symbolic",
            RunStatus.COMPLETED: "emblem-ok-symbolic",
            RunStatus.FAILED: "dialog-error-symbolic",
            RunStatus.CANCELLED: "process-stop-symbolic",
        }
        icon = Gtk.Image.new_from_icon_name(status_icons.get(run.status, "emblem-default-symbolic"))
        icon.set_pixel_size(16)
        if run.status == RunStatus.COMPLETED:
            icon.add_css_class("success")
        elif run.status == RunStatus.FAILED:
            icon.add_css_class("error")
        elif run.status == RunStatus.RUNNING:
            icon.add_css_class("accent")
        title_row.append(icon)
        
        # Name
        name_label = Gtk.Label(label=run.name)
        name_label.set_xalign(0)
        name_label.set_hexpand(True)
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        title_row.append(name_label)
        
        # Progress bar (if running)
        if run.status == RunStatus.RUNNING and run.progress_pct is not None:
            progress = Gtk.ProgressBar()
            progress.set_fraction(run.progress_pct / 100.0)
            progress.set_text(f"{run.progress_pct}%")
            progress.set_show_text(True)
            content.append(progress)
        
        # Status text
        status_text = run.status.value.upper()
        if run.status == RunStatus.FAILED:
            status_text = "⚠ FAILED"
        status_label = Gtk.Label(label=status_text)
        status_label.add_css_class("caption")
        status_label.add_css_class("dim-label")
        status_label.set_xalign(0)
        content.append(status_label)
        
        # Action buttons
        actions_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions_row.set_margin_top(4)
        content.append(actions_row)
        
        if run.status == RunStatus.QUEUED:
            run_btn = Gtk.Button(label="▶ Run")
            run_btn.add_css_class("suggested-action")
            run_btn.connect("clicked", self._on_dispatch)
            actions_row.append(run_btn)
        
        if run.status == RunStatus.RUNNING and run.can_cancel:
            cancel_btn = Gtk.Button(label="⏹ Cancel")
            cancel_btn.add_css_class("destructive-action")
            cancel_btn.connect("clicked", self._on_cancel)
            actions_row.append(cancel_btn)
        
        logs_btn = Gtk.Button(label="📋 Logs")
        logs_btn.add_css_class("flat")
        logs_btn.connect("clicked", self._on_logs)
        actions_row.append(logs_btn)
    
    def _on_dispatch(self, button):
        """Dispatch run - TODO: call POST /api/runs/:id/dispatch."""
        print(f"[Execute] Dispatching run {self.run.id}")
    
    def _on_cancel(self, button):
        """Cancel run - TODO: call POST /api/runs/:id/cancel."""
        print(f"[Execute] Cancelling run {self.run.id}")
    
    def _on_logs(self, button):
        """Show logs - TODO: navigate to logs view."""
        print(f"[Execute] Opening logs for {self.run.id}")


class ExecuteColumn(Gtk.Box):
    """Right column: Progressions / Execution Timeline."""
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add_css_class("execute-column")
        self.set_size_request(300, -1)
        
        self._runs: List[ExecutionRun] = []
        
        self._build_ui()
        self._load_mock_data()
    
    def _build_ui(self):
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_top(12)
        header.set_margin_start(12)
        header.set_margin_end(12)
        header.set_margin_bottom(8)
        self.append(header)
        
        title = Gtk.Label(label="Progressions")
        title.add_css_class("title-2")
        title.set_xalign(0)
        title.set_hexpand(True)
        header.append(title)
        
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.add_css_class("flat")
        refresh_btn.set_tooltip_text("Refresh")
        header.append(refresh_btn)
        
        # Runs list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(scrolled)
        
        self.runs_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scrolled.set_child(self.runs_box)
        
        # Quick actions footer
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        footer.set_margin_start(12)
        footer.set_margin_end(12)
        footer.set_margin_bottom(12)
        self.append(footer)
        
        all_logs_btn = Gtk.Button(label="Open All Logs")
        all_logs_btn.add_css_class("flat")
        footer.append(all_logs_btn)
    
    def _load_mock_data(self):
        self._runs = MockDataStore.get_mock_runs()
        self._refresh_list()
    
    def _refresh_list(self):
        # Clear
        while True:
            child = self.runs_box.get_first_child()
            if child:
                self.runs_box.remove(child)
            else:
                break
        
        # Add runs
        for run in self._runs:
            card = ExecutionRunCard(run)
            self.runs_box.append(card)


# =============================================================================
# MAIN PAGE
# =============================================================================

class HomeConsolePage(Gtk.Box):
    """
    The ROXY Command Center Home Console.
    
    Layout: [Triage] [Talk] [Execute]
    
    This is the cockpit. Not a dashboard.
    """
    
    def __init__(self, on_navigate: Optional[callable] = None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.on_navigate = on_navigate
        self.add_css_class("home-console-page")
        
        self._build_ui()
    
    def _build_ui(self):
        # Left: Triage/Inbox column
        self.triage = TriageColumn()
        self.triage.add_css_class("sidebar-pane")
        self.append(self.triage)
        
        # Separator
        sep1 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.append(sep1)
        
        # Center: Talk/Roxy conversation
        self.talk = TalkColumn()
        self.append(self.talk)
        
        # Separator
        sep2 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.append(sep2)
        
        # Right: Execute/Progressions column
        self.execute = ExecuteColumn()
        self.execute.add_css_class("sidebar-pane")
        self.append(self.execute)
    
    def update(self, data: dict):
        """
        Update with daemon data.
        
        TODO: This will need to:
        1. Refresh inbox from roxy-core
        2. Refresh runs from orchestrator
        3. Update context chips in talk column
        """
        if hasattr(self, "talk"):
            self.talk.update_snapshot(data)

    def shutdown(self):
        if hasattr(self, "talk"):
            self.talk.shutdown()

    def do_unroot(self):
        self.shutdown()
        return super().do_unroot()
