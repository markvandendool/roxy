#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   🚀 ROXY COMMAND CENTER - ULTRA PREMIUM TUI                                 ║
║                                                                              ║
║   A world-class terminal interface built with Textual                        ║
║   Inspired by: gh-dash, posting, Open-WebUI, LobeChat                        ║
║                                                                              ║
║   Features:                                                                  ║
║   • Real-time chat with streaming responses                                  ║
║   • Live infrastructure status monitoring                                    ║
║   • Expert router visualization                                              ║
║   • Voice mode toggle                                                        ║
║   • Conversation history                                                     ║
║   • System metrics dashboard                                                 ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import os
import sys
import httpx
from datetime import datetime
from pathlib import Path
from typing import Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    LoadingIndicator,
    Markdown,
    ProgressBar,
    RichLog,
    Rule,
    Static,
    Switch,
    TabbedContent,
    TabPane,
    Tree,
)
from textual.widgets.tree import TreeNode
from textual.reactive import reactive
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown as RichMarkdown

# ROXY Configuration
ROXY_HOST = os.getenv("ROXY_HOST", "127.0.0.1")
ROXY_PORT = int(os.getenv("ROXY_PORT", "8766"))
ROXY_BASE_URL = f"http://{ROXY_HOST}:{ROXY_PORT}"
TOKEN_PATH = Path.home() / ".roxy" / "secret.token"


def get_token() -> str:
    """Get ROXY authentication token."""
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text().strip()
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
# Custom Widgets
# ═══════════════════════════════════════════════════════════════════════════════


class StatusIndicator(Static):
    """A beautiful status indicator with pulsing effect."""
    
    status = reactive("unknown")
    
    def __init__(self, label: str = "", **kwargs):
        super().__init__(**kwargs)
        self.label = label
    
    def render(self) -> Text:
        colors = {
            "online": "green",
            "offline": "red",
            "loading": "yellow",
            "unknown": "dim white",
        }
        icons = {
            "online": "●",
            "offline": "○",
            "loading": "◐",
            "unknown": "◌",
        }
        color = colors.get(self.status, "white")
        icon = icons.get(self.status, "?")
        return Text(f"{icon} {self.label}", style=color)


class MetricCard(Static):
    """A dashboard metric card."""
    
    value = reactive("--")
    
    def __init__(self, title: str, icon: str = "📊", **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.icon = icon
    
    def render(self) -> Panel:
        content = Text()
        content.append(f"{self.icon} ", style="bold")
        content.append(f"{self.title}\n", style="bold cyan")
        content.append(f"{self.value}", style="bold green")
        return Panel(content, border_style="bright_blue")


class ChatMessage(Static):
    """A single chat message display."""
    
    def __init__(self, role: str, content: str, **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.msg_content = content
    
    def render(self) -> Panel:
        if self.role == "user":
            return Panel(
                Text(self.msg_content, style="white"),
                title="👤 You",
                title_align="left",
                border_style="cyan",
            )
        elif self.role == "assistant":
            return Panel(
                RichMarkdown(self.msg_content),
                title="🤖 ROXY",
                title_align="left",
                border_style="magenta",
            )
        else:
            return Panel(
                Text(self.msg_content, style="dim"),
                title=f"📝 {self.role}",
                title_align="left",
                border_style="dim",
            )


class ExpertCard(Static):
    """Display an expert model card."""
    
    def __init__(self, name: str, specialty: str, status: str = "ready", **kwargs):
        super().__init__(**kwargs)
        self.expert_name = name
        self.specialty = specialty
        self.expert_status = status
    
    def render(self) -> Panel:
        status_icon = "✅" if self.expert_status == "ready" else "⏳"
        content = Text()
        content.append(f"🧠 {self.expert_name}\n", style="bold cyan")
        content.append(f"   {self.specialty}\n", style="dim")
        content.append(f"   {status_icon} {self.expert_status}", style="green" if self.expert_status == "ready" else "yellow")
        return Panel(content, border_style="blue")


# ═══════════════════════════════════════════════════════════════════════════════
# Screens
# ═══════════════════════════════════════════════════════════════════════════════


class HelpScreen(ModalScreen):
    """Help screen with keyboard shortcuts."""
    
    BINDINGS = [("escape", "dismiss", "Close")]
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        🎮 ROXY COMMAND CENTER - HELP                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  NAVIGATION                                                                  ║
║  ──────────────────────────────────────────────────────────────────────────  ║
║  Tab / Shift+Tab    Navigate between panels                                  ║
║  ↑/↓                Scroll chat history                                      ║
║  Ctrl+T             Switch tabs                                              ║
║                                                                              ║
║  CHAT                                                                        ║
║  ──────────────────────────────────────────────────────────────────────────  ║
║  Enter              Send message                                             ║
║  Ctrl+C             Clear input                                              ║
║  Ctrl+V             Toggle voice mode                                        ║
║                                                                              ║
║  ACTIONS                                                                     ║
║  ──────────────────────────────────────────────────────────────────────────  ║
║  Ctrl+R             Refresh status                                           ║
║  Ctrl+S             Take screenshot                                          ║
║  F1/?               Show this help                                           ║
║  Ctrl+Q             Quit                                                     ║
║                                                                              ║
║  Press ESC to close                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
            """, id="help-content"),
            id="help-dialog",
        )


class VoiceModeScreen(ModalScreen):
    """Voice mode screen."""
    
    BINDINGS = [("escape", "dismiss", "Close")]
    
    def compose(self) -> ComposeResult:
        yield Container(
            Vertical(
                Static("🎤 VOICE MODE", id="voice-title"),
                Rule(),
                Static("Press and hold SPACE to talk", id="voice-instruction"),
                Static("◉ Listening...", id="voice-status"),
                ProgressBar(id="voice-level", total=100, show_eta=False),
                Rule(),
                Button("Close (ESC)", variant="primary", id="voice-close"),
                id="voice-content",
            ),
            id="voice-dialog",
        )
    
    @on(Button.Pressed, "#voice-close")
    def close_voice(self) -> None:
        self.dismiss()


# ═══════════════════════════════════════════════════════════════════════════════
# Main Application
# ═══════════════════════════════════════════════════════════════════════════════


class RoxyCommandCenter(App):
    """ROXY Command Center - Ultra Premium TUI."""
    
    TITLE = "🚀 ROXY Command Center"
    SUB_TITLE = "Your AI Operating System"
    
    CSS = """
    /* Global Styles */
    Screen {
        background: $surface;
    }
    
    /* Header */
    Header {
        background: $primary;
        color: $text;
        text-style: bold;
    }
    
    /* Status Bar */
    #status-bar {
        dock: top;
        height: 3;
        background: $surface-darken-1;
        padding: 0 1;
    }
    
    #status-bar StatusIndicator {
        width: auto;
        margin: 0 2;
    }
    
    /* Main Layout */
    #main-container {
        layout: horizontal;
    }
    
    /* Left Panel - Chat */
    #chat-panel {
        width: 70%;
        border: solid $primary;
        padding: 1;
    }
    
    #chat-container {
        height: 1fr;
    }
    
    #chat-scroll {
        height: 1fr;
    }
    
    #chat-input-container {
        dock: bottom;
        height: 3;
        padding: 0 1;
    }
    
    #chat-input {
        width: 1fr;
    }
    
    /* Right Panel - Dashboard */
    #dashboard-panel {
        width: 30%;
        border: solid $secondary;
    }
    
    /* Metrics Grid */
    #metrics-grid {
        layout: grid;
        grid-size: 2;
        grid-gutter: 1;
        padding: 1;
        height: auto;
    }
    
    MetricCard {
        height: 5;
    }
    
    /* Experts Panel */
    #experts-container {
        height: auto;
        max-height: 20;
        padding: 1;
    }
    
    ExpertCard {
        height: 5;
        margin-bottom: 1;
    }
    
    /* Tabs */
    TabbedContent {
        height: 1fr;
    }
    
    TabPane {
        padding: 1;
    }
    
    /* Chat Messages */
    ChatMessage {
        margin-bottom: 1;
    }
    
    /* Help Dialog */
    #help-dialog {
        align: center middle;
        width: 90;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }
    
    #help-content {
        text-align: center;
    }
    
    /* Voice Dialog */
    #voice-dialog {
        align: center middle;
        width: 60;
        height: 20;
        border: thick $success;
        background: $surface;
        padding: 2;
    }
    
    #voice-title {
        text-align: center;
        text-style: bold;
        color: $success;
    }
    
    #voice-instruction {
        text-align: center;
        margin: 1 0;
    }
    
    #voice-status {
        text-align: center;
        color: $warning;
    }
    
    #voice-level {
        margin: 1 0;
    }
    
    /* Loading */
    LoadingIndicator {
        background: transparent;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("f1", "help", "Help"),
        Binding("question_mark", "help", "Help", show=False),
        Binding("ctrl+r", "refresh", "Refresh"),
        Binding("ctrl+v", "voice_mode", "Voice"),
        Binding("ctrl+t", "toggle_tab", "Toggle Tab"),
    ]
    
    # Reactive state
    roxy_status = reactive("loading")
    redis_status = reactive("loading")
    postgres_status = reactive("loading")
    nats_status = reactive("loading")
    
    def __init__(self):
        super().__init__()
        self.token = get_token()
        self.messages = []
        self.experts = []
        self.metrics = {
            "requests": 0,
            "cache_hits": 0,
            "uptime": "0s",
            "memory": "0MB",
        }
    
    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()
        
        # Status Bar
        yield Horizontal(
            StatusIndicator("ROXY Core", id="status-roxy"),
            StatusIndicator("Redis", id="status-redis"),
            StatusIndicator("PostgreSQL", id="status-postgres"),
            StatusIndicator("NATS", id="status-nats"),
            id="status-bar",
        )
        
        # Main Container
        yield Horizontal(
            # Left: Chat Panel
            Vertical(
                VerticalScroll(id="chat-scroll"),
                Horizontal(
                    Input(placeholder="Ask ROXY anything... (Enter to send)", id="chat-input"),
                    Button("🎤", id="voice-btn", variant="primary"),
                    Button("📤", id="send-btn", variant="success"),
                    id="chat-input-container",
                ),
                id="chat-panel",
            ),
            
            # Right: Dashboard Panel  
            Vertical(
                TabbedContent(
                    TabPane("📊 Dashboard", id="tab-dashboard"),
                    TabPane("🧠 Experts", id="tab-experts"),
                    TabPane("📜 History", id="tab-history"),
                ),
                id="dashboard-panel",
            ),
            id="main-container",
        )
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when app is mounted."""
        # Initialize dashboard
        self._populate_dashboard()
        self._populate_experts()
        
        # Add welcome message
        self._add_message("assistant", """
# 👋 Welcome to ROXY Command Center!

I'm **ROXY**, your AI Operating System. I'm here to help you with:

- 💻 **Code** - Ask me programming questions
- 🔧 **System** - Control your computer  
- 📊 **Analysis** - Data and research
- 🎨 **Creative** - Writing and brainstorming

**Quick Tips:**
- Press `F1` for help
- Press `Ctrl+V` for voice mode
- Press `Ctrl+R` to refresh status

What can I help you with today?
        """)
        
        # Start background status refresh
        self.refresh_status()
    
    def _populate_dashboard(self) -> None:
        """Populate the dashboard with metric cards."""
        dashboard = self.query_one("#tab-dashboard", TabPane)
        dashboard.mount(
            Container(
                MetricCard("Requests", "📨", id="metric-requests"),
                MetricCard("Cache Hits", "⚡", id="metric-cache"),
                MetricCard("Uptime", "⏱️", id="metric-uptime"),
                MetricCard("Memory", "💾", id="metric-memory"),
                id="metrics-grid",
            )
        )
    
    def _populate_experts(self) -> None:
        """Populate the experts panel."""
        experts_tab = self.query_one("#tab-experts", TabPane)
        experts_container = VerticalScroll(id="experts-container")
        
        # Default experts
        default_experts = [
            ("phi:2.7b", "Query Classifier", "ready"),
            ("deepseek-coder:6.7b", "Code Specialist", "ready"),
            ("wizard-math:7b", "Math Specialist", "ready"),
            ("llama3:8b", "General/Creative", "ready"),
            ("qwen2.5-coder:14b", "Primary Coder", "ready"),
        ]
        
        for name, specialty, status in default_experts:
            experts_container.mount(ExpertCard(name, specialty, status))
        
        experts_tab.mount(experts_container)
    
    def _add_message(self, role: str, content: str) -> None:
        """Add a message to the chat."""
        self.messages.append({"role": role, "content": content})
        chat_scroll = self.query_one("#chat-scroll", VerticalScroll)
        chat_scroll.mount(ChatMessage(role, content))
        chat_scroll.scroll_end(animate=True)
    
    @work(exclusive=True)
    async def refresh_status(self) -> None:
        """Refresh infrastructure status."""
        headers = {"X-ROXY-Token": self.token}
        
        async with httpx.AsyncClient() as client:
            try:
                # Check ROXY core
                r = await client.get(f"{ROXY_BASE_URL}/ping", headers=headers, timeout=5.0)
                if r.status_code == 200:
                    self.query_one("#status-roxy", StatusIndicator).status = "online"
                else:
                    self.query_one("#status-roxy", StatusIndicator).status = "offline"
            except Exception:
                self.query_one("#status-roxy", StatusIndicator).status = "offline"
            
            try:
                # Get infrastructure status
                r = await client.get(f"{ROXY_BASE_URL}/infrastructure", headers=headers, timeout=5.0)
                if r.status_code == 200:
                    data = r.json()
                    
                    # Update status indicators
                    if data.get("redis", {}).get("status") == "connected":
                        self.query_one("#status-redis", StatusIndicator).status = "online"
                    else:
                        self.query_one("#status-redis", StatusIndicator).status = "offline"
                    
                    if data.get("postgres", {}).get("status") == "connected":
                        self.query_one("#status-postgres", StatusIndicator).status = "online"
                    else:
                        self.query_one("#status-postgres", StatusIndicator).status = "offline"
                    
                    if data.get("nats", {}).get("status") == "connected":
                        self.query_one("#status-nats", StatusIndicator).status = "online"
                    else:
                        self.query_one("#status-nats", StatusIndicator).status = "offline"
                    
                    # Update metrics
                    try:
                        self.query_one("#metric-cache", MetricCard).value = \
                            data.get("redis", {}).get("memory_human", "N/A")
                    except Exception:
                        pass
                    
            except Exception as e:
                self.query_one("#status-redis", StatusIndicator).status = "unknown"
                self.query_one("#status-postgres", StatusIndicator).status = "unknown"
                self.query_one("#status-nats", StatusIndicator).status = "unknown"
    
    @work(exclusive=True, thread=True)
    async def send_message(self, message: str) -> None:
        """Send a message to ROXY."""
        headers = {
            "X-ROXY-Token": self.token,
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(
                    f"{ROXY_BASE_URL}/expert",
                    headers=headers,
                    json={"message": message},
                    timeout=60.0,
                )
                
                if r.status_code == 200:
                    data = r.json()
                    response = data.get("response", "No response")
                    expert = data.get("expert", "unknown")
                    
                    # Format response with expert info
                    full_response = f"*Expert: {expert}*\n\n{response}"
                    self.call_from_thread(self._add_message, "assistant", full_response)
                else:
                    self.call_from_thread(
                        self._add_message, 
                        "system", 
                        f"Error: {r.status_code} - {r.text}"
                    )
            except Exception as e:
                self.call_from_thread(self._add_message, "system", f"Error: {str(e)}")
    
    @on(Input.Submitted, "#chat-input")
    def handle_input(self, event: Input.Submitted) -> None:
        """Handle chat input submission."""
        message = event.value.strip()
        if message:
            self._add_message("user", message)
            event.input.clear()
            self.send_message(message)
    
    @on(Button.Pressed, "#send-btn")
    def handle_send_button(self) -> None:
        """Handle send button click."""
        chat_input = self.query_one("#chat-input", Input)
        message = chat_input.value.strip()
        if message:
            self._add_message("user", message)
            chat_input.clear()
            self.send_message(message)
    
    @on(Button.Pressed, "#voice-btn")
    def handle_voice_button(self) -> None:
        """Handle voice button click."""
        self.action_voice_mode()
    
    def action_help(self) -> None:
        """Show help screen."""
        self.push_screen(HelpScreen())
    
    def action_voice_mode(self) -> None:
        """Show voice mode screen."""
        self.push_screen(VoiceModeScreen())
    
    def action_refresh(self) -> None:
        """Refresh status."""
        self.refresh_status()
        self.notify("Refreshing status...", title="ROXY")
    
    def action_toggle_tab(self) -> None:
        """Toggle between tabs."""
        tabbed = self.query_one(TabbedContent)
        tabs = ["tab-dashboard", "tab-experts", "tab-history"]
        current = tabbed.active
        current_idx = tabs.index(current) if current in tabs else 0
        next_idx = (current_idx + 1) % len(tabs)
        tabbed.active = tabs[next_idx]


# ═══════════════════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    """Run the ROXY Command Center."""
    app = RoxyCommandCenter()
    app.run()


if __name__ == "__main__":
    main()
