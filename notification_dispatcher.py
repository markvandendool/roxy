#!/usr/bin/env python3
"""
Notification Dispatcher - Unified Outbound Notifications
=========================================================
RU-009: Notification Dispatcher

Unified notification system across all channels:
- Email (via mcp_email)
- Telegram (via mcp_telegram)
- Discord (via mcp_discord)
- Desktop notifications (via notify-send)

Features:
- Priority levels (urgent, high, normal, low)
- Automatic fallback on failure
- Rate limiting
- Notification templates
- Audit logging

SECURITY INVARIANTS:
1. No sensitive data in logs
2. Channel credentials via MCP servers
3. Rate limiting prevents abuse
"""

import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict
from collections import deque
from threading import Lock
from dataclasses import dataclass, asdict
from enum import Enum

# Import MCP modules
import sys
sys.path.insert(0, str(Path(__file__).parent / "mcp"))

# Paths
ROXY_DIR = Path.home() / ".roxy"
CONFIG_DIR = ROXY_DIR / "config"
AUDIT_LOG = ROXY_DIR / "logs" / "notification_audit.log"

# Rate limiting
RATE_LIMITS = {
    "email": {"window": 60, "max": 5},
    "telegram": {"window": 1, "max": 30},
    "discord": {"window": 1, "max": 5},
    "desktop": {"window": 1, "max": 10}
}

_rate_counters: Dict[str, deque] = {ch: deque() for ch in RATE_LIMITS}
_lock = Lock()


class Priority(Enum):
    URGENT = "urgent"    # Desktop + primary channel immediately
    HIGH = "high"        # Primary channel
    NORMAL = "normal"    # Primary channel, may be batched
    LOW = "low"          # Logged only, or batched


@dataclass
class Notification:
    """Notification structure"""
    id: str
    message: str
    title: str
    priority: str
    channels: List[str]
    timestamp: str
    metadata: Dict


# Notification history
_notification_history: deque = deque(maxlen=500)


def _audit_log(operation: str, details: str = "", success: bool = True):
    """Write to audit log"""
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    log_entry = {
        "timestamp": timestamp,
        "operation": operation,
        "success": success,
        "details": details[:200]
    }
    
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def _generate_id() -> str:
    """Generate notification ID"""
    import uuid
    return f"notif_{uuid.uuid4().hex[:12]}"


def _check_rate_limit(channel: str) -> bool:
    """Check if channel rate limit allows notification"""
    if channel not in RATE_LIMITS:
        return True
    
    config = RATE_LIMITS[channel]
    now = time.time()
    
    with _lock:
        counter = _rate_counters[channel]
        
        # Remove old entries
        while counter and counter[0] < now - config["window"]:
            counter.popleft()
        
        if len(counter) >= config["max"]:
            return False
        
        counter.append(now)
        return True


def _send_desktop(title: str, message: str, urgency: str = "normal") -> bool:
    """Send desktop notification via notify-send"""
    try:
        cmd = ["notify-send", "-u", urgency, title, message]
        subprocess.run(cmd, timeout=5, capture_output=True)
        return True
    except Exception as e:
        _audit_log("desktop_error", str(e), False)
        return False


def _send_email(to: str, subject: str, body: str) -> bool:
    """Send email via mcp_email"""
    try:
        from mcp_email import email_send
        result = email_send(to, subject, body)
        return result.get("success", False)
    except Exception as e:
        _audit_log("email_error", str(e), False)
        return False


def _send_telegram(chat_id: str, message: str) -> bool:
    """Send Telegram message via mcp_telegram"""
    try:
        from mcp_telegram import telegram_send
        result = telegram_send(chat_id, message)
        return result.get("success", False)
    except Exception as e:
        _audit_log("telegram_error", str(e), False)
        return False


def _send_discord(channel_id: str, message: str) -> bool:
    """Send Discord message via mcp_discord"""
    try:
        from mcp_discord import discord_send
        result = discord_send(channel_id, message)
        return result.get("success", False)
    except Exception as e:
        _audit_log("discord_error", str(e), False)
        return False


def _load_channel_config() -> Dict:
    """Load channel configuration"""
    config_file = CONFIG_DIR / "notifications.yaml"
    
    if config_file.exists():
        try:
            import yaml
            with open(config_file) as f:
                return yaml.safe_load(f) or {}
        except:
            pass
    
    # Default config
    return {
        "primary_channel": "desktop",
        "channels": {
            "desktop": {"enabled": True},
            "telegram": {"enabled": False, "chat_id": ""},
            "discord": {"enabled": False, "channel_id": ""},
            "email": {"enabled": False, "to": ""}
        },
        "fallback_order": ["desktop", "telegram", "discord", "email"]
    }


def notify(message: str, title: str = "ROXY", 
           priority: str = "normal", 
           channels: List[str] = None,
           metadata: Dict = None) -> Dict:
    """
    Send notification across channels
    
    Args:
        message: Notification message
        title: Notification title
        priority: urgent, high, normal, low
        channels: Specific channels to use (default: auto based on priority)
        metadata: Additional data (not sent, for logging)
    
    Returns:
        {"success": True, "sent_to": [...], "failed": [...]}
    """
    config = _load_channel_config()
    
    # Determine channels based on priority
    if channels is None:
        if priority == "urgent":
            channels = ["desktop", config.get("primary_channel", "telegram")]
        elif priority == "high":
            channels = [config.get("primary_channel", "telegram")]
        elif priority == "normal":
            channels = [config.get("primary_channel", "telegram")]
        else:  # low
            channels = []  # Just log
    
    # Remove duplicates while preserving order
    channels = list(dict.fromkeys(channels))
    
    # Create notification record
    notif = Notification(
        id=_generate_id(),
        message=message[:500],
        title=title,
        priority=priority,
        channels=channels,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        metadata=metadata or {}
    )
    
    sent_to = []
    failed = []
    
    # Send to each channel
    for channel in channels:
        ch_config = config.get("channels", {}).get(channel, {})
        
        if not ch_config.get("enabled", False) and channel != "desktop":
            failed.append({"channel": channel, "reason": "disabled"})
            continue
        
        if not _check_rate_limit(channel):
            failed.append({"channel": channel, "reason": "rate_limited"})
            continue
        
        success = False
        
        if channel == "desktop":
            urgency = "critical" if priority == "urgent" else "normal"
            success = _send_desktop(title, message, urgency)
        
        elif channel == "telegram":
            chat_id = ch_config.get("chat_id", "")
            if chat_id:
                success = _send_telegram(chat_id, f"<b>{title}</b>\n\n{message}")
        
        elif channel == "discord":
            channel_id = ch_config.get("channel_id", "")
            if channel_id:
                success = _send_discord(channel_id, f"**{title}**\n{message}")
        
        elif channel == "email":
            to = ch_config.get("to", "")
            if to:
                success = _send_email(to, f"[ROXY] {title}", message)
        
        if success:
            sent_to.append(channel)
        else:
            failed.append({"channel": channel, "reason": "send_failed"})
    
    # Try fallback if primary failed
    if not sent_to and priority in ["urgent", "high"]:
        for fallback in config.get("fallback_order", []):
            if fallback not in channels and _check_rate_limit(fallback):
                if fallback == "desktop":
                    if _send_desktop(title, message, "normal"):
                        sent_to.append(f"{fallback} (fallback)")
                        break
    
    # Store in history
    _notification_history.append(notif)
    
    # Log
    _audit_log("notify", f"id={notif.id}, priority={priority}, sent={sent_to}")
    
    return {
        "success": len(sent_to) > 0 or priority == "low",
        "notification_id": notif.id,
        "sent_to": sent_to,
        "failed": failed
    }


def get_history(limit: int = 50) -> List[Dict]:
    """Get notification history"""
    return [asdict(n) for n in list(_notification_history)[-limit:]]


def notify_urgent(message: str, title: str = "URGENT") -> Dict:
    """Send urgent notification (convenience)"""
    return notify(message, title, priority="urgent")


def notify_error(message: str, title: str = "Error") -> Dict:
    """Send error notification (convenience)"""
    return notify(message, title, priority="high")


# =============================================================================
# MCP Interface
# =============================================================================

TOOLS = {
    "send": {
        "description": "Send notification across configured channels",
        "parameters": {
            "message": {"type": "string", "description": "Notification message"},
            "title": {"type": "string", "description": "Notification title", "default": "ROXY"},
            "priority": {"type": "string", "description": "urgent, high, normal, low", "default": "normal"},
            "channels": {"type": "array", "description": "Specific channels"}
        },
        "required": ["message"]
    },
    "urgent": {
        "description": "Send urgent notification (desktop + primary)",
        "parameters": {
            "message": {"type": "string"},
            "title": {"type": "string", "default": "URGENT"}
        },
        "required": ["message"]
    },
    "history": {
        "description": "Get notification history",
        "parameters": {
            "limit": {"type": "integer", "default": 50}
        },
        "required": []
    },
    "status": {
        "description": "Get notification system status",
        "parameters": {},
        "required": []
    }
}


def handle_tool(name: str, params: dict) -> Any:
    """MCP tool handler"""
    if name == "send":
        return notify(
            params["message"],
            params.get("title", "ROXY"),
            params.get("priority", "normal"),
            params.get("channels")
        )
    elif name == "urgent":
        return notify_urgent(params["message"], params.get("title", "URGENT"))
    elif name == "history":
        return {"success": True, "notifications": get_history(params.get("limit", 50))}
    elif name == "status":
        config = _load_channel_config()
        return {
            "success": True,
            "primary_channel": config.get("primary_channel"),
            "enabled_channels": [ch for ch, cfg in config.get("channels", {}).items() if cfg.get("enabled")],
            "history_count": len(_notification_history)
        }
    return {"success": False, "error": f"Unknown tool: {name}"}


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: notification_dispatcher.py <command> [args...]")
        print("Commands: send <message>, urgent <message>, history, status")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "send" and len(sys.argv) >= 3:
        result = notify(sys.argv[2])
    elif cmd == "urgent" and len(sys.argv) >= 3:
        result = notify_urgent(sys.argv[2])
    elif cmd == "history":
        result = {"notifications": get_history()}
    elif cmd == "status":
        result = handle_tool("status", {})
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
    
    print(json.dumps(result, indent=2))
