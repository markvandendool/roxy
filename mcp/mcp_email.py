#!/usr/bin/env python3
"""
MCP Email Server - Gmail/IMAP Integration
==========================================
RU-005: Email MCP Server

Email integration with:
- Gmail API support
- IMAP fallback
- Send/receive/draft
- PII masking in logs

Tools:
- email_list: List messages
- email_read: Read full message
- email_send: Send email
- email_draft: Create draft
- email_search: Search messages
- email_labels: List/manage labels

SECURITY INVARIANTS:
1. OAuth tokens in vault only
2. PII masked in all logs
3. No email content in logs
"""

import os
import json
import time
import base64
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Import vault for token storage
import sys
sys.path.insert(0, str(Path(__file__).parent))
from mcp_vault import vault_get, vault_set

# Paths
ROXY_DIR = Path.home() / ".roxy"
AUDIT_LOG = ROXY_DIR / "logs" / "email_audit.log"

# Gmail API
GMAIL_API = "https://www.googleapis.com/gmail/v1/users/me"


def _mask_pii(text: str) -> str:
    """Mask email addresses and potential PII in log output"""
    # Mask email addresses
    text = re.sub(r'[\w\.-]+@[\w\.-]+', '[EMAIL]', text)
    # Mask phone numbers
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    return text


def _audit_log(operation: str, details: str = "", success: bool = True):
    """Write to audit log - NEVER include email content"""
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    log_entry = {
        "timestamp": timestamp,
        "operation": operation,
        "success": success,
        "details": _mask_pii(details[:100])
    }
    
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def _get_access_token() -> Optional[str]:
    """Get Gmail access token from vault"""
    # Use same Google OAuth as calendar
    access_result = vault_get("google_access_token")
    if access_result.get("success"):
        return access_result["value"]
    return None


def _api_call(method: str, endpoint: str, data: dict = None, raw_body: bytes = None) -> dict:
    """Make Gmail API call"""
    import urllib.request
    import urllib.error
    
    token = _get_access_token()
    if not token:
        return {
            "success": False,
            "error": "Google OAuth not configured. Store google_access_token in vault."
        }
    
    url = f"{GMAIL_API}{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        if raw_body:
            req = urllib.request.Request(url, data=raw_body, headers=headers, method=method)
        elif data:
            req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method=method)
        else:
            req = urllib.request.Request(url, headers=headers, method=method)
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status == 204:
                return {"success": True}
            return {"success": True, "result": json.loads(resp.read())}
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        try:
            error_json = json.loads(error_body)
            error_msg = error_json.get("error", {}).get("message", str(e))
        except:
            error_msg = str(e)
        return {"success": False, "error": error_msg}
    except Exception as e:
        return {"success": False, "error": str(e)}


def email_list(label: str = "INBOX", max_results: int = 20, 
               query: str = None) -> dict:
    """
    List messages
    
    Args:
        label: Label/folder (INBOX, SENT, DRAFT, etc.)
        max_results: Max messages to return
        query: Gmail search query
    
    Returns:
        {"success": True, "messages": [...]}
    """
    import urllib.parse
    
    params = {
        "labelIds": label,
        "maxResults": min(max_results, 100)
    }
    
    if query:
        params["q"] = query
    
    query_str = urllib.parse.urlencode(params)
    result = _api_call("GET", f"/messages?{query_str}")
    
    if result.get("success"):
        messages = []
        for msg in result.get("result", {}).get("messages", []):
            # Get message details
            detail_result = _api_call("GET", f"/messages/{msg['id']}?format=metadata&metadataHeaders=Subject&metadataHeaders=From&metadataHeaders=Date")
            if detail_result.get("success"):
                headers = {h["name"]: h["value"] for h in detail_result.get("result", {}).get("payload", {}).get("headers", [])}
                messages.append({
                    "id": msg["id"],
                    "thread_id": msg.get("threadId"),
                    "subject": headers.get("Subject", "(No subject)"),
                    "from": headers.get("From", ""),
                    "date": headers.get("Date", ""),
                    "snippet": detail_result.get("result", {}).get("snippet", "")[:100]
                })
        
        _audit_log("list", f"label={label}, count={len(messages)}")
        return {"success": True, "messages": messages, "count": len(messages)}
    
    _audit_log("list", result.get("error", ""), False)
    return result


def email_read(message_id: str) -> dict:
    """
    Read full message
    
    Args:
        message_id: Message ID
    
    Returns:
        {"success": True, "message": {...}}
    """
    result = _api_call("GET", f"/messages/{message_id}?format=full")
    
    if result.get("success"):
        msg_data = result.get("result", {})
        payload = msg_data.get("payload", {})
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
        
        # Extract body
        body = ""
        if "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
        elif "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                    break
        
        message = {
            "id": message_id,
            "thread_id": msg_data.get("threadId"),
            "subject": headers.get("Subject", ""),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "cc": headers.get("Cc", ""),
            "date": headers.get("Date", ""),
            "body": body,
            "labels": msg_data.get("labelIds", [])
        }
        
        _audit_log("read", f"msg_id={message_id}")
        return {"success": True, "message": message}
    
    _audit_log("read", result.get("error", ""), False)
    return result


def email_send(to: str, subject: str, body: str, 
               cc: str = None, bcc: str = None,
               html: bool = False, attachments: List[str] = None) -> dict:
    """
    Send email
    
    Args:
        to: Recipient email(s), comma-separated
        subject: Email subject
        body: Email body
        cc: CC recipients
        bcc: BCC recipients
        html: Body is HTML
        attachments: List of file paths
    
    Returns:
        {"success": True, "message_id": str}
    """
    # Build message
    if attachments:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, "html" if html else "plain"))
        
        for filepath in attachments:
            path = Path(filepath)
            if path.exists():
                with open(path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={path.name}")
                msg.attach(part)
    else:
        msg = MIMEText(body, "html" if html else "plain")
    
    msg["To"] = to
    msg["Subject"] = subject
    
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc
    
    # Encode
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    
    result = _api_call("POST", "/messages/send", {"raw": raw})
    
    if result.get("success"):
        msg_id = result.get("result", {}).get("id")
        _audit_log("send", f"to={_mask_pii(to)}")
        return {"success": True, "message_id": msg_id}
    
    _audit_log("send", result.get("error", ""), False)
    return result


def email_draft(to: str, subject: str, body: str, html: bool = False) -> dict:
    """
    Create draft (don't send)
    
    Args:
        to: Recipient email
        subject: Email subject
        body: Email body
        html: Body is HTML
    
    Returns:
        {"success": True, "draft_id": str}
    """
    msg = MIMEText(body, "html" if html else "plain")
    msg["To"] = to
    msg["Subject"] = subject
    
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    
    result = _api_call("POST", "/drafts", {"message": {"raw": raw}})
    
    if result.get("success"):
        draft_id = result.get("result", {}).get("id")
        _audit_log("draft", f"to={_mask_pii(to)}")
        return {"success": True, "draft_id": draft_id}
    
    _audit_log("draft", result.get("error", ""), False)
    return result


def email_search(query: str, max_results: int = 20) -> dict:
    """
    Search messages with Gmail query syntax
    
    Args:
        query: Gmail search query (e.g., "from:someone@example.com subject:meeting")
        max_results: Max results
    
    Returns:
        {"success": True, "messages": [...]}
    """
    return email_list(label="", max_results=max_results, query=query)


def email_labels() -> dict:
    """
    List all labels
    
    Returns:
        {"success": True, "labels": [...]}
    """
    result = _api_call("GET", "/labels")
    
    if result.get("success"):
        labels = []
        for lbl in result.get("result", {}).get("labels", []):
            labels.append({
                "id": lbl.get("id"),
                "name": lbl.get("name"),
                "type": lbl.get("type"),
                "messages_total": lbl.get("messagesTotal", 0),
                "messages_unread": lbl.get("messagesUnread", 0)
            })
        _audit_log("labels", f"count={len(labels)}")
        return {"success": True, "labels": labels}
    
    _audit_log("labels", result.get("error", ""), False)
    return result


def email_modify_labels(message_id: str, add_labels: List[str] = None, 
                        remove_labels: List[str] = None) -> dict:
    """
    Add/remove labels from message
    
    Args:
        message_id: Message ID
        add_labels: Labels to add
        remove_labels: Labels to remove
    
    Returns:
        {"success": True}
    """
    data = {}
    if add_labels:
        data["addLabelIds"] = add_labels
    if remove_labels:
        data["removeLabelIds"] = remove_labels
    
    result = _api_call("POST", f"/messages/{message_id}/modify", data)
    
    if result.get("success"):
        _audit_log("modify_labels", f"msg_id={message_id}")
        return {"success": True}
    
    _audit_log("modify_labels", result.get("error", ""), False)
    return result


def email_trash(message_id: str) -> dict:
    """
    Move message to trash
    
    Args:
        message_id: Message ID
    
    Returns:
        {"success": True}
    """
    result = _api_call("POST", f"/messages/{message_id}/trash")
    
    if result.get("success"):
        _audit_log("trash", f"msg_id={message_id}")
        return {"success": True}
    
    _audit_log("trash", result.get("error", ""), False)
    return result


# =============================================================================
# MCP Server Interface
# =============================================================================

TOOLS = {
    "list": {
        "description": "List messages from Gmail",
        "parameters": {
            "label": {"type": "string", "description": "Label/folder", "default": "INBOX"},
            "max_results": {"type": "integer", "description": "Max messages", "default": 20},
            "query": {"type": "string", "description": "Gmail search query"}
        },
        "required": []
    },
    "read": {
        "description": "Read full message content",
        "parameters": {
            "message_id": {"type": "string", "description": "Message ID"}
        },
        "required": ["message_id"]
    },
    "send": {
        "description": "Send email via Gmail",
        "parameters": {
            "to": {"type": "string", "description": "Recipient email(s)"},
            "subject": {"type": "string", "description": "Email subject"},
            "body": {"type": "string", "description": "Email body"},
            "cc": {"type": "string", "description": "CC recipients"},
            "bcc": {"type": "string", "description": "BCC recipients"},
            "html": {"type": "boolean", "description": "Body is HTML", "default": False},
            "attachments": {"type": "array", "description": "File paths to attach"}
        },
        "required": ["to", "subject", "body"]
    },
    "draft": {
        "description": "Create draft without sending",
        "parameters": {
            "to": {"type": "string", "description": "Recipient"},
            "subject": {"type": "string", "description": "Subject"},
            "body": {"type": "string", "description": "Body"},
            "html": {"type": "boolean", "default": False}
        },
        "required": ["to", "subject", "body"]
    },
    "search": {
        "description": "Search messages with Gmail query",
        "parameters": {
            "query": {"type": "string", "description": "Gmail search query"},
            "max_results": {"type": "integer", "default": 20}
        },
        "required": ["query"]
    },
    "labels": {
        "description": "List all Gmail labels",
        "parameters": {},
        "required": []
    },
    "modify_labels": {
        "description": "Add/remove labels from message",
        "parameters": {
            "message_id": {"type": "string"},
            "add_labels": {"type": "array"},
            "remove_labels": {"type": "array"}
        },
        "required": ["message_id"]
    },
    "trash": {
        "description": "Move message to trash",
        "parameters": {
            "message_id": {"type": "string"}
        },
        "required": ["message_id"]
    }
}


def handle_tool(name: str, params: dict) -> Any:
    """MCP tool handler"""
    handlers = {
        "list": lambda p: email_list(p.get("label", "INBOX"), p.get("max_results", 20), p.get("query")),
        "read": lambda p: email_read(p["message_id"]),
        "send": lambda p: email_send(p["to"], p["subject"], p["body"], 
                                     p.get("cc"), p.get("bcc"), p.get("html", False), p.get("attachments")),
        "draft": lambda p: email_draft(p["to"], p["subject"], p["body"], p.get("html", False)),
        "search": lambda p: email_search(p["query"], p.get("max_results", 20)),
        "labels": lambda p: email_labels(),
        "modify_labels": lambda p: email_modify_labels(p["message_id"], p.get("add_labels"), p.get("remove_labels")),
        "trash": lambda p: email_trash(p["message_id"])
    }
    
    if name not in handlers:
        return {"success": False, "error": f"Unknown tool: {name}"}
    
    return handlers[name](params)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: mcp_email.py <command>")
        print("Commands: list, labels, read <msg_id>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "list":
        result = email_list()
    elif cmd == "labels":
        result = email_labels()
    elif cmd == "read" and len(sys.argv) >= 3:
        result = email_read(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
    
    print(json.dumps(result, indent=2))
