#!/usr/bin/env python3
"""
MCP Telegram Server - Telegram Bot Integration
===============================================
RU-006: Telegram Bot MCP Server

Telegram bot integration with:
- Message sending
- Photo/document sending
- Poll creation
- Message listening via polling
- Rate limiting (30 msg/s)

Tools:
- telegram_send: Send text message
- telegram_photo: Send photo
- telegram_document: Send document
- telegram_poll: Create poll
- telegram_listen: Get recent messages

SECURITY INVARIANTS:
1. Bot token stored in vault only
2. All operations logged (no message content in logs)
3. Rate limited to 30 messages/second
"""

import os
import json
import time
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional, List
from collections import deque
from threading import Lock

# Import vault for token retrieval
import sys
sys.path.insert(0, str(Path(__file__).parent))
from mcp_vault import vault_get

# Paths
ROXY_DIR = Path.home() / ".roxy"
AUDIT_LOG = ROXY_DIR / "logs" / "telegram_audit.log"

# Telegram API base
TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

# Rate limiting
RATE_LIMIT_WINDOW = 1  # 1 second
RATE_LIMIT_MAX = 30    # 30 per second
_request_times: deque = deque()
_lock = Lock()

# Last update ID for polling
_last_update_id = 0


def _audit_log(operation: str, details: str = "", success: bool = True):
    """Write to audit log - NEVER include message content"""
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
    """Get Telegram bot token from vault"""
    result = vault_get("telegram_bot_token")
    if result.get("success"):
        return result["value"]
    return None


async def _api_call(method: str, data: dict = None, files: dict = None) -> dict:
    """Make Telegram API call"""
    token = _get_token()
    if not token:
        return {"success": False, "error": "Telegram bot token not found in vault. Use vault_set('telegram_bot_token', 'YOUR_TOKEN')"}
    
    if not _check_rate_limit():
        return {"success": False, "error": "Rate limit exceeded (30 req/s)"}
    
    url = TELEGRAM_API.format(token=token, method=method)
    
    try:
        async with aiohttp.ClientSession() as session:
            if files:
                # Multipart form for file uploads
                form = aiohttp.FormData()
                for key, value in (data or {}).items():
                    form.add_field(key, str(value))
                for key, (filename, content, content_type) in files.items():
                    form.add_field(key, content, filename=filename, content_type=content_type)
                async with session.post(url, data=form) as resp:
                    result = await resp.json()
            else:
                async with session.post(url, json=data) as resp:
                    result = await resp.json()
            
            if result.get("ok"):
                return {"success": True, "result": result.get("result")}
            else:
                return {"success": False, "error": result.get("description", "Unknown error")}
                
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


def telegram_send(chat_id: str, text: str, parse_mode: str = "HTML", 
                  reply_to: Optional[int] = None, silent: bool = False) -> dict:
    """
    Send text message
    
    Args:
        chat_id: Target chat ID
        text: Message text (supports HTML/Markdown)
        parse_mode: HTML or Markdown
        reply_to: Message ID to reply to
        silent: Send without notification
    
    Returns:
        {"success": True, "message_id": int}
    """
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_notification": silent
    }
    
    if reply_to:
        data["reply_to_message_id"] = reply_to
    
    result = _run_async(_api_call("sendMessage", data))
    
    if result.get("success"):
        msg_id = result["result"].get("message_id")
        _audit_log("send", f"chat={chat_id}, msg_id={msg_id}")
        return {"success": True, "message_id": msg_id}
    
    _audit_log("send", result.get("error", ""), False)
    return result


def telegram_photo(chat_id: str, photo_path: str, caption: str = "") -> dict:
    """
    Send photo
    
    Args:
        chat_id: Target chat ID
        photo_path: Path to photo file
        caption: Optional caption
    
    Returns:
        {"success": True, "message_id": int}
    """
    photo_path = Path(photo_path)
    if not photo_path.exists():
        return {"success": False, "error": f"Photo not found: {photo_path}"}
    
    async def send():
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        
        with open(photo_path, "rb") as f:
            content = f.read()
        
        files = {
            "photo": (photo_path.name, content, "image/jpeg")
        }
        
        return await _api_call("sendPhoto", data, files)
    
    result = _run_async(send())
    
    if result.get("success"):
        msg_id = result["result"].get("message_id")
        _audit_log("photo", f"chat={chat_id}, file={photo_path.name}")
        return {"success": True, "message_id": msg_id}
    
    _audit_log("photo", result.get("error", ""), False)
    return result


def telegram_document(chat_id: str, doc_path: str, caption: str = "") -> dict:
    """
    Send document
    
    Args:
        chat_id: Target chat ID
        doc_path: Path to document file
        caption: Optional caption
    
    Returns:
        {"success": True, "message_id": int}
    """
    doc_path = Path(doc_path)
    if not doc_path.exists():
        return {"success": False, "error": f"Document not found: {doc_path}"}
    
    async def send():
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        
        with open(doc_path, "rb") as f:
            content = f.read()
        
        files = {
            "document": (doc_path.name, content, "application/octet-stream")
        }
        
        return await _api_call("sendDocument", data, files)
    
    result = _run_async(send())
    
    if result.get("success"):
        msg_id = result["result"].get("message_id")
        _audit_log("document", f"chat={chat_id}, file={doc_path.name}")
        return {"success": True, "message_id": msg_id}
    
    _audit_log("document", result.get("error", ""), False)
    return result


def telegram_poll(chat_id: str, question: str, options: List[str], 
                  is_anonymous: bool = True, allows_multiple: bool = False) -> dict:
    """
    Create poll
    
    Args:
        chat_id: Target chat ID
        question: Poll question
        options: List of answer options (2-10)
        is_anonymous: Anonymous voting
        allows_multiple: Allow multiple answers
    
    Returns:
        {"success": True, "poll_id": str, "message_id": int}
    """
    if len(options) < 2 or len(options) > 10:
        return {"success": False, "error": "Poll must have 2-10 options"}
    
    data = {
        "chat_id": chat_id,
        "question": question,
        "options": json.dumps(options),
        "is_anonymous": is_anonymous,
        "allows_multiple_answers": allows_multiple
    }
    
    result = _run_async(_api_call("sendPoll", data))
    
    if result.get("success"):
        poll = result["result"].get("poll", {})
        _audit_log("poll", f"chat={chat_id}, question_len={len(question)}")
        return {
            "success": True,
            "poll_id": poll.get("id"),
            "message_id": result["result"].get("message_id")
        }
    
    _audit_log("poll", result.get("error", ""), False)
    return result


def telegram_listen(timeout: int = 30, limit: int = 100) -> dict:
    """
    Get recent messages (long polling)
    
    Args:
        timeout: Long polling timeout in seconds
        limit: Max number of messages to return
    
    Returns:
        {"success": True, "messages": list}
    """
    global _last_update_id
    
    data = {
        "timeout": min(timeout, 60),
        "limit": min(limit, 100),
        "allowed_updates": ["message", "edited_message", "callback_query"]
    }
    
    if _last_update_id:
        data["offset"] = _last_update_id + 1
    
    result = _run_async(_api_call("getUpdates", data))
    
    if result.get("success"):
        updates = result.get("result", [])
        messages = []
        
        for update in updates:
            _last_update_id = max(_last_update_id, update.get("update_id", 0))
            
            msg = update.get("message") or update.get("edited_message")
            if msg:
                messages.append({
                    "update_id": update.get("update_id"),
                    "message_id": msg.get("message_id"),
                    "chat_id": msg.get("chat", {}).get("id"),
                    "chat_type": msg.get("chat", {}).get("type"),
                    "from_id": msg.get("from", {}).get("id"),
                    "from_username": msg.get("from", {}).get("username"),
                    "text": msg.get("text"),
                    "date": msg.get("date")
                })
        
        _audit_log("listen", f"received={len(messages)}")
        return {"success": True, "messages": messages, "count": len(messages)}
    
    _audit_log("listen", result.get("error", ""), False)
    return result


def telegram_get_me() -> dict:
    """
    Get bot info
    
    Returns:
        {"success": True, "bot": {...}}
    """
    result = _run_async(_api_call("getMe"))
    
    if result.get("success"):
        _audit_log("get_me", "Bot info retrieved")
        return {"success": True, "bot": result.get("result")}
    
    return result


# =============================================================================
# MCP Server Interface
# =============================================================================

TOOLS = {
    "send": {
        "description": "Send text message to Telegram chat",
        "parameters": {
            "chat_id": {"type": "string", "description": "Target chat ID"},
            "text": {"type": "string", "description": "Message text (HTML supported)"},
            "parse_mode": {"type": "string", "description": "HTML or Markdown", "default": "HTML"},
            "reply_to": {"type": "integer", "description": "Message ID to reply to"},
            "silent": {"type": "boolean", "description": "Send without notification", "default": False}
        },
        "required": ["chat_id", "text"]
    },
    "photo": {
        "description": "Send photo to Telegram chat",
        "parameters": {
            "chat_id": {"type": "string", "description": "Target chat ID"},
            "photo_path": {"type": "string", "description": "Path to photo file"},
            "caption": {"type": "string", "description": "Photo caption"}
        },
        "required": ["chat_id", "photo_path"]
    },
    "document": {
        "description": "Send document to Telegram chat",
        "parameters": {
            "chat_id": {"type": "string", "description": "Target chat ID"},
            "doc_path": {"type": "string", "description": "Path to document file"},
            "caption": {"type": "string", "description": "Document caption"}
        },
        "required": ["chat_id", "doc_path"]
    },
    "poll": {
        "description": "Create poll in Telegram chat",
        "parameters": {
            "chat_id": {"type": "string", "description": "Target chat ID"},
            "question": {"type": "string", "description": "Poll question"},
            "options": {"type": "array", "description": "Answer options (2-10)"},
            "is_anonymous": {"type": "boolean", "default": True},
            "allows_multiple": {"type": "boolean", "default": False}
        },
        "required": ["chat_id", "question", "options"]
    },
    "listen": {
        "description": "Get recent messages from Telegram",
        "parameters": {
            "timeout": {"type": "integer", "description": "Long polling timeout", "default": 30},
            "limit": {"type": "integer", "description": "Max messages", "default": 100}
        },
        "required": []
    },
    "get_me": {
        "description": "Get bot info",
        "parameters": {},
        "required": []
    }
}


def handle_tool(name: str, params: dict) -> Any:
    """MCP tool handler"""
    handlers = {
        "send": lambda p: telegram_send(p["chat_id"], p["text"], 
                                        p.get("parse_mode", "HTML"),
                                        p.get("reply_to"), p.get("silent", False)),
        "photo": lambda p: telegram_photo(p["chat_id"], p["photo_path"], p.get("caption", "")),
        "document": lambda p: telegram_document(p["chat_id"], p["doc_path"], p.get("caption", "")),
        "poll": lambda p: telegram_poll(p["chat_id"], p["question"], p["options"],
                                        p.get("is_anonymous", True), p.get("allows_multiple", False)),
        "listen": lambda p: telegram_listen(p.get("timeout", 30), p.get("limit", 100)),
        "get_me": lambda p: telegram_get_me()
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
        print("Usage: mcp_telegram.py <command> [args...]")
        print("Commands: get_me, send <chat_id> <text>, listen")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "get_me":
        result = telegram_get_me()
    elif cmd == "send" and len(sys.argv) >= 4:
        result = telegram_send(sys.argv[2], sys.argv[3])
    elif cmd == "listen":
        result = telegram_listen(timeout=5)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
    
    print(json.dumps(result, indent=2))
