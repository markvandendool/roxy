#!/usr/bin/env python3
"""
Home Console Page - The ROXY Command Center cockpit.

NORTH STAR: Home = Talk + Triage + Execute
- Not a dashboard. An operations console.
- GTK is thin client; roxy-core is the brain.

Layout:
  [Left: Triage/Inbox]  [Center: Roxy Chat]  [Right: Progressions/Runs]

All data is placeholder/mock until roxy-core endpoints are wired.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Pango
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import random


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
            
            # Content
            content_label = Gtk.Label(label=message.content)
            content_label.set_wrap(True)
            content_label.set_xalign(0)
            content_label.set_max_width_chars(60)
            bubble.append(content_label)


class TalkColumn(Gtk.Box):
    """Center column: Roxy Conversation."""
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add_css_class("talk-column")
        self.set_hexpand(True)
        
        self._messages: List[ChatMessage] = []
        self._draft_mode = True  # Human-in-the-loop default
        
        self._build_ui()
        self._load_mock_data()
    
    def _build_ui(self):
        # Header with context chips
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header.set_margin_top(12)
        header.set_margin_start(12)
        header.set_margin_end(12)
        self.append(header)
        
        title = Gtk.Label(label="Roxy")
        title.add_css_class("title-2")
        title.set_xalign(0)
        header.append(title)
        
        # Context chips row
        chips_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        chips_box.set_margin_bottom(8)
        header.append(chips_box)
        
        chip_texts = [
            ("🖥️ Local", "Connected to local ROXY"),
            ("🧠 qwen2.5:14b", "Current model"),
            ("🎵 MindSong", "Active project context"),
        ]
        for text, tooltip in chip_texts:
            chip = Gtk.Label(label=text)
            chip.add_css_class("dim-label")
            chip.add_css_class("caption")
            chip.set_tooltip_text(tooltip)
            chips_box.append(chip)
        
        # Chat transcript
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(scrolled)
        
        self.chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scrolled.set_child(self.chat_box)
        
        # Input area
        input_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        input_area.set_margin_start(12)
        input_area.set_margin_end(12)
        input_area.set_margin_bottom(12)
        self.append(input_area)
        
        # Mode toggle
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
        
        # Input row
        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_area.append(input_row)
        
        # Voice button (stub)
        voice_btn = Gtk.Button()
        voice_btn.set_icon_name("audio-input-microphone-symbolic")
        voice_btn.set_tooltip_text("Push to talk (coming soon)")
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
    
    def _on_mode_toggle(self, button, is_draft: bool):
        if button.get_active():
            self._draft_mode = is_draft
            if is_draft:
                self.send_btn.set_active(False)
            else:
                self.draft_btn.set_active(False)
                # Warn about send mode
                print("[Talk] WARNING: Send mode enabled - Roxy will execute without approval")
    
    def _on_voice_click(self, button):
        """Voice button stub - TODO: wire to wyoming/whisper."""
        print("[Talk] Voice input not yet implemented (Phase 2)")
    
    def _on_send(self, widget):
        """Send message - TODO: wire to roxy-core."""
        text = self.entry.get_text().strip()
        if not text:
            return
        
        # Add user message
        msg = ChatMessage(
            id=f"msg-{len(self._messages)+1}",
            role="user",
            content=text,
            timestamp=datetime.now()
        )
        self._add_message(msg)
        self.entry.set_text("")
        
        # Simulate Roxy response (TODO: call roxy-core)
        GLib.timeout_add(500, self._simulate_response, text)
    
    def _simulate_response(self, user_text: str):
        """Simulate Roxy response - TODO: replace with real API call."""
        response = ChatMessage(
            id=f"msg-{len(self._messages)+1}",
            role="assistant",
            content=f"I understood your request about '{user_text[:30]}...'. "
                    "In Draft mode, I'll prepare a response for your approval. "
                    "[This is placeholder - roxy-core integration pending]",
            timestamp=datetime.now()
        )
        self._add_message(response)
        return False
    
    def _add_message(self, message: ChatMessage):
        self._messages.append(message)
        widget = ChatMessage_Widget(message)
        self.chat_box.append(widget)
    
    def _load_mock_data(self):
        for msg in MockDataStore.get_mock_chat():
            self._add_message(msg)


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
        # For now, just log that we received data
        # The mock data is loaded on init
        pass
