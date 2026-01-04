#!/usr/bin/env python3
"""
MCP Discord Server - Discord Bot Integration
=============================================
RU-007: Discord Bot MCP Server

Discord bot integration with:
- Message sending
- Rich embeds
- Reactions
- Message listening
- Webhook support

Tools:
- discord_send: Send text message
- discord_embed: Send rich embed
- discord_react: Add reaction
- discord_listen: Get recent messages
- discord_webhook: Send via webhook

SECURITY INVARIANTS:
1. Bot token stored in vault only
2. All operations logged (no message content)
3. Proper async handling for discord.py
"""

import os
import json
import time
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict
from collections import deque
from threading import Lock

# Import vault for token retrieval
import sys
sys.path.insert(0, str(Path(__file__).parent))
from mcp_vault import vault_get

# Paths
ROXY_DIR = Path.home() / ".roxy"
AUDIT_LOG = ROXY_DIR / "logs" / "discord_audit.log"

# Discord API base
DISCORD_API = "https://discord.com/api/v10"

# Rate limiting (per channel - simplified)
RATE_LIMIT_WINDOW = 1
RATE_LIMIT_MAX = 5  # 5 per second per channel
_request_times: deque = deque()
_lock = Lock()


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


def _check_rate_limit() -> bool:
    """Check if rate limit allows request"""
    now = time.time()
    
    with _lock:
        while _request_times and _request_times[0] < now - RATE_LIMIT_WINDOW:
            _request_times.popleft()
        
        if len(_request_times) >= RATE_LIMIT_MAX:
            return False
        
        _request_times.append(now)
        return True


def _get_token() -> Optional[str]:
    """Get Discord bot token from vault"""
    result = vault_get("discord_bot_token")
    if result.get("success"):
        return result["value"]
    return None


async def _api_call(method: str, endpoint: str, data: dict = None, 
                    use_bot_auth: bool = True) -> dict:
    """Make Discord API call"""
    if use_bot_auth:
        token = _get_token()
        if not token:
            return {"success": False, "error": "Discord bot token not found in vault. Use vault_set('discord_bot_token', 'YOUR_TOKEN')"}
    
    if not _check_rate_limit():
        return {"success": False, "error": "Rate limit exceeded (5 req/s)"}
    
    url = f"{DISCORD_API}{endpoint}"
    headers = {
        "Content-Type": "application/json"
    }
    
    if use_bot_auth:
        headers["Authorization"] = f"Bot {token}"
    
    try:
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 204:
                        return {"success": True}
                    result = await resp.json()
            elif method == "POST":
                async with session.post(url, headers=headers, json=data) as resp:
                    if resp.status == 204:
                        return {"success": True}
                    result = await resp.json()
            elif method == "PUT":
                async with session.put(url, headers=headers, json=data) as resp:
                    if resp.status == 204:
                        return {"success": True}
                    result = await resp.json()
            elif method == "DELETE":
                async with session.delete(url, headers=headers) as resp:
                    if resp.status == 204:
                        return {"success": True}
                    result = await resp.json()
            
            if isinstance(result, dict) and "message" in result:
                return {"success": False, "error": result.get("message")}
            
            return {"success": True, "result": result}
                
    except Exception as e:
        return {"success": False, "error": str(e)}


def _run_async(coro):
    """Run async coroutine in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)


def discord_send(channel_id: str, content: str, tts: bool = False) -> dict:
    """
    Send text message to channel
    
    Args:
        channel_id: Target channel ID
        content: Message content (max 2000 chars)
        tts: Text-to-speech
    
    Returns:
        {"success": True, "message_id": str}
    """
    if len(content) > 2000:
        return {"success": False, "error": "Message exceeds 2000 character limit"}
    
    data = {
        "content": content,
        "tts": tts
    }
    
    result = _run_async(_api_call("POST", f"/channels/{channel_id}/messages", data))
    
    if result.get("success"):
        msg_id = result["result"].get("id")
        _audit_log("send", f"channel={channel_id}, msg_id={msg_id}")
        return {"success": True, "message_id": msg_id}
    
    _audit_log("send", result.get("error", ""), False)
    return result


def discord_embed(channel_id: str, embed: Dict, content: str = "") -> dict:
    """
    Send rich embed to channel
    
    Args:
        channel_id: Target channel ID
        embed: Embed object with title, description, color, fields, etc.
        content: Optional text content alongside embed
    
    Embed structure:
        {
            "title": "Title",
            "description": "Description",
            "color": 0x00ff00,  # Decimal or hex
            "fields": [{"name": "Field", "value": "Value", "inline": True}],
            "footer": {"text": "Footer"},
            "thumbnail": {"url": "https://..."},
            "image": {"url": "https://..."}
        }
    
    Returns:
        {"success": True, "message_id": str}
    """
    data = {
        "embeds": [embed]
    }
    
    if content:
        data["content"] = content
    
    result = _run_async(_api_call("POST", f"/channels/{channel_id}/messages", data))
    
    if result.get("success"):
        msg_id = result["result"].get("id")
        _audit_log("embed", f"channel={channel_id}, msg_id={msg_id}")
        return {"success": True, "message_id": msg_id}
    
    _audit_log("embed", result.get("error", ""), False)
    return result


def discord_react(channel_id: str, message_id: str, emoji: str) -> dict:
    """
    Add reaction to message
    
    Args:
        channel_id: Channel containing message
        message_id: Message to react to
        emoji: Unicode emoji or custom emoji (name:id)
    
    Returns:
        {"success": True}
    """
    # URL encode the emoji
    import urllib.parse
    encoded_emoji = urllib.parse.quote(emoji)
    
    result = _run_async(_api_call(
        "PUT", 
        f"/channels/{channel_id}/messages/{message_id}/reactions/{encoded_emoji}/@me"
    ))
    
    if result.get("success"):
        _audit_log("react", f"channel={channel_id}, msg={message_id}")
        return {"success": True}
    
    _audit_log("react", result.get("error", ""), False)
    return result


def discord_listen(channel_id: str, limit: int = 50, before: str = None, after: str = None) -> dict:
    """
    Get recent messages from channel
    
    Args:
        channel_id: Channel to fetch from
        limit: Number of messages (1-100)
        before: Get messages before this ID
        after: Get messages after this ID
    
    Returns:
        {"success": True, "messages": list}
    """
    params = [f"limit={min(limit, 100)}"]
    if before:
        params.append(f"before={before}")
    if after:
        params.append(f"after={after}")
    
    query = "&".join(params)
    result = _run_async(_api_call("GET", f"/channels/{channel_id}/messages?{query}"))
    
    if result.get("success"):
        raw_messages = result.get("result", [])
        messages = []
        
        for msg in raw_messages:
            messages.append({
                "id": msg.get("id"),
                "content": msg.get("content"),
                "author_id": msg.get("author", {}).get("id"),
                "author_username": msg.get("author", {}).get("username"),
                "timestamp": msg.get("timestamp"),
                "embeds_count": len(msg.get("embeds", [])),
                "attachments_count": len(msg.get("attachments", []))
            })
        
        _audit_log("listen", f"channel={channel_id}, count={len(messages)}")
        return {"success": True, "messages": messages, "count": len(messages)}
    
    _audit_log("listen", result.get("error", ""), False)
    return result


def discord_webhook(webhook_url: str, content: str = "", embeds: List[Dict] = None,
                    username: str = None, avatar_url: str = None) -> dict:
    """
    Send message via webhook (no bot token needed)
    
    Args:
        webhook_url: Full webhook URL
        content: Text content
        embeds: List of embed objects
        username: Override webhook username
        avatar_url: Override webhook avatar
    
    Returns:
        {"success": True}
    """
    data = {}
    
    if content:
        data["content"] = content
    if embeds:
        data["embeds"] = embeds
    if username:
        data["username"] = username
    if avatar_url:
        data["avatar_url"] = avatar_url
    
    if not data:
        return {"success": False, "error": "Must provide content or embeds"}
    
    async def send_webhook():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=data) as resp:
                    if resp.status == 204:
                        return {"success": True}
                    if resp.status >= 400:
                        result = await resp.json()
                        return {"success": False, "error": result.get("message", f"HTTP {resp.status}")}
                    return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    result = _run_async(send_webhook())
    
    if result.get("success"):
        _audit_log("webhook", "Message sent via webhook")
    else:
        _audit_log("webhook", result.get("error", ""), False)
    
    return result


def discord_get_channel(channel_id: str) -> dict:
    """
    Get channel info
    
    Args:
        channel_id: Channel ID
    
    Returns:
        {"success": True, "channel": {...}}
    """
    result = _run_async(_api_call("GET", f"/channels/{channel_id}"))
    
    if result.get("success"):
        _audit_log("get_channel", f"channel={channel_id}")
        return {"success": True, "channel": result.get("result")}
    
    return result


def discord_get_guild(guild_id: str) -> dict:
    """
    Get server/guild info
    
    Args:
        guild_id: Guild ID
    
    Returns:
        {"success": True, "guild": {...}}
    """
    result = _run_async(_api_call("GET", f"/guilds/{guild_id}"))
    
    if result.get("success"):
        _audit_log("get_guild", f"guild={guild_id}")
        return {"success": True, "guild": result.get("result")}
    
    return result


def discord_get_me() -> dict:
    """
    Get bot user info
    
    Returns:
        {"success": True, "user": {...}}
    """
    result = _run_async(_api_call("GET", "/users/@me"))
    
    if result.get("success"):
        _audit_log("get_me", "Bot info retrieved")
        return {"success": True, "user": result.get("result")}
    
    return result


# =============================================================================
# MCP Server Interface
# =============================================================================

TOOLS = {
    "send": {
        "description": "Send text message to Discord channel",
        "parameters": {
            "channel_id": {"type": "string", "description": "Target channel ID"},
            "content": {"type": "string", "description": "Message content (max 2000 chars)"},
            "tts": {"type": "boolean", "description": "Text-to-speech", "default": False}
        },
        "required": ["channel_id", "content"]
    },
    "embed": {
        "description": "Send rich embed to Discord channel",
        "parameters": {
            "channel_id": {"type": "string", "description": "Target channel ID"},
            "embed": {"type": "object", "description": "Embed object with title, description, color, fields"},
            "content": {"type": "string", "description": "Optional text alongside embed"}
        },
        "required": ["channel_id", "embed"]
    },
    "react": {
        "description": "Add reaction to message",
        "parameters": {
            "channel_id": {"type": "string", "description": "Channel ID"},
            "message_id": {"type": "string", "description": "Message ID"},
            "emoji": {"type": "string", "description": "Unicode emoji or custom (name:id)"}
        },
        "required": ["channel_id", "message_id", "emoji"]
    },
    "listen": {
        "description": "Get recent messages from channel",
        "parameters": {
            "channel_id": {"type": "string", "description": "Channel to fetch from"},
            "limit": {"type": "integer", "description": "Number of messages (1-100)", "default": 50},
            "before": {"type": "string", "description": "Get messages before this ID"},
            "after": {"type": "string", "description": "Get messages after this ID"}
        },
        "required": ["channel_id"]
    },
    "webhook": {
        "description": "Send message via webhook (no bot token needed)",
        "parameters": {
            "webhook_url": {"type": "string", "description": "Full webhook URL"},
            "content": {"type": "string", "description": "Text content"},
            "embeds": {"type": "array", "description": "List of embed objects"},
            "username": {"type": "string", "description": "Override webhook username"},
            "avatar_url": {"type": "string", "description": "Override webhook avatar"}
        },
        "required": ["webhook_url"]
    },
    "get_channel": {
        "description": "Get channel info",
        "parameters": {
            "channel_id": {"type": "string", "description": "Channel ID"}
        },
        "required": ["channel_id"]
    },
    "get_guild": {
        "description": "Get server/guild info",
        "parameters": {
            "guild_id": {"type": "string", "description": "Guild ID"}
        },
        "required": ["guild_id"]
    },
    "get_me": {
        "description": "Get bot user info",
        "parameters": {},
        "required": []
    }
}


def handle_tool(name: str, params: dict) -> Any:
    """MCP tool handler"""
    handlers = {
        "send": lambda p: discord_send(p["channel_id"], p["content"], p.get("tts", False)),
        "embed": lambda p: discord_embed(p["channel_id"], p["embed"], p.get("content", "")),
        "react": lambda p: discord_react(p["channel_id"], p["message_id"], p["emoji"]),
        "listen": lambda p: discord_listen(p["channel_id"], p.get("limit", 50), 
                                           p.get("before"), p.get("after")),
        "webhook": lambda p: discord_webhook(p["webhook_url"], p.get("content", ""),
                                             p.get("embeds"), p.get("username"), p.get("avatar_url")),
        "get_channel": lambda p: discord_get_channel(p["channel_id"]),
        "get_guild": lambda p: discord_get_guild(p["guild_id"]),
        "get_me": lambda p: discord_get_me()
    }
    
    if name not in handlers:
        return {"success": False, "error": f"Unknown tool: {name}"}
    
    return handlers[name](params)


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: mcp_discord.py <command> [args...]")
        print("Commands: get_me, send <channel_id> <text>, listen <channel_id>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "get_me":
        result = discord_get_me()
    elif cmd == "send" and len(sys.argv) >= 4:
        result = discord_send(sys.argv[2], sys.argv[3])
    elif cmd == "listen" and len(sys.argv) >= 3:
        result = discord_listen(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
    
    print(json.dumps(result, indent=2))
