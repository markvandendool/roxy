#!/usr/bin/env python3
"""
Webhook Receiver Server - External Event Ingestion
===================================================
RU-008: Webhook Receiver Server

Receives webhooks from external services:
- GitHub (push, PR, issues, etc.)
- Stripe (payments, subscriptions)
- Custom webhooks with HMAC validation

Features:
- Signature validation per source
- Event queue (in-memory, NATS optional)
- Configurable routing rules
- Audit logging

Port: 8767

SECURITY INVARIANTS:
1. All webhooks validated via signature
2. Invalid signatures rejected with 401
3. All events logged (no sensitive payload data)
4. Secrets stored in vault only
"""

import os
import json
import hmac
import hashlib
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional, Dict, List, Callable
from collections import deque
from dataclasses import dataclass, asdict
import threading

# Web server
from aiohttp import web

# Import vault for secrets
import sys
sys.path.insert(0, str(Path(__file__).parent / "mcp"))
from mcp_vault import vault_get

# Paths
ROXY_DIR = Path.home() / ".roxy"
CONFIG_DIR = ROXY_DIR / "config"
AUDIT_LOG = ROXY_DIR / "logs" / "webhook_audit.log"

# Server config
WEBHOOK_PORT = 8767
MAX_QUEUE_SIZE = 1000


@dataclass
class WebhookEvent:
    """Webhook event structure"""
    id: str
    source: str
    event_type: str
    timestamp: str
    payload: Dict
    headers: Dict
    signature_valid: bool


# Event queue
_event_queue: deque = deque(maxlen=MAX_QUEUE_SIZE)
_event_handlers: List[Callable] = []
_queue_lock = threading.Lock()


def _audit_log(operation: str, details: str = "", success: bool = True):
    """Write to audit log - NEVER include full payloads"""
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


def _generate_event_id() -> str:
    """Generate unique event ID"""
    import uuid
    return f"evt_{uuid.uuid4().hex[:16]}"


def _get_webhook_secret(source: str) -> Optional[str]:
    """Get webhook secret from vault"""
    result = vault_get(f"webhook_secret_{source}")
    if result.get("success"):
        return result["value"]
    return None


def _verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature (X-Hub-Signature-256)"""
    if not signature or not signature.startswith("sha256="):
        return False
    
    expected = "sha256=" + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)


def _verify_stripe_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Stripe webhook signature"""
    try:
        # Stripe signature format: t=timestamp,v1=signature
        parts = dict(item.split("=") for item in signature.split(","))
        timestamp = parts.get("t", "")
        sig = parts.get("v1", "")
        
        # Compute expected signature
        signed_payload = f"{timestamp}.{payload.decode()}"
        expected = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(sig, expected)
    except:
        return False


def _verify_custom_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify custom HMAC-SHA256 signature"""
    if not signature:
        return False
    
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Support both raw and prefixed formats
    if signature.startswith("sha256="):
        signature = signature[7:]
    
    return hmac.compare_digest(signature.lower(), expected.lower())


def verify_signature(source: str, payload: bytes, headers: Dict) -> bool:
    """Verify webhook signature based on source"""
    secret = _get_webhook_secret(source)
    if not secret:
        _audit_log("signature_check", f"No secret configured for {source}", False)
        return False
    
    if source == "github":
        sig = headers.get("X-Hub-Signature-256", "")
        return _verify_github_signature(payload, sig, secret)
    
    elif source == "stripe":
        sig = headers.get("Stripe-Signature", "")
        return _verify_stripe_signature(payload, sig, secret)
    
    else:
        # Custom webhook - check common header names
        sig = (
            headers.get("X-Signature") or 
            headers.get("X-Webhook-Signature") or
            headers.get("X-Hub-Signature-256") or
            ""
        )
        return _verify_custom_signature(payload, sig, secret)


def queue_event(event: WebhookEvent):
    """Add event to queue and notify handlers"""
    with _queue_lock:
        _event_queue.append(event)
    
    # Notify registered handlers
    for handler in _event_handlers:
        try:
            handler(event)
        except Exception as e:
            _audit_log("handler_error", str(e), False)


def register_handler(handler: Callable[[WebhookEvent], None]):
    """Register event handler"""
    _event_handlers.append(handler)


def get_events(limit: int = 50, source: str = None) -> List[Dict]:
    """Get recent events from queue"""
    with _queue_lock:
        events = list(_event_queue)
    
    if source:
        events = [e for e in events if e.source == source]
    
    return [asdict(e) for e in events[-limit:]]


def clear_events():
    """Clear event queue"""
    with _queue_lock:
        _event_queue.clear()


# =============================================================================
# HTTP Handlers
# =============================================================================

async def handle_webhook(request: web.Request) -> web.Response:
    """Handle incoming webhook"""
    # Get source from path
    source = request.match_info.get("source", "custom")
    
    # Read payload
    try:
        payload = await request.read()
    except Exception as e:
        _audit_log("webhook_error", f"Failed to read payload: {e}", False)
        return web.Response(status=400, text="Bad request")
    
    # Get headers
    headers = dict(request.headers)
    
    # Verify signature
    sig_valid = verify_signature(source, payload, headers)
    
    if not sig_valid:
        _audit_log("webhook_rejected", f"Invalid signature for {source}", False)
        return web.Response(status=401, text="Invalid signature")
    
    # Parse payload
    try:
        if request.content_type == "application/json":
            data = json.loads(payload)
        else:
            data = {"raw": payload.decode("utf-8", errors="replace")}
    except:
        data = {"raw": payload.decode("utf-8", errors="replace")}
    
    # Determine event type
    if source == "github":
        event_type = headers.get("X-GitHub-Event", "unknown")
    elif source == "stripe":
        event_type = data.get("type", "unknown")
    else:
        event_type = headers.get("X-Event-Type", data.get("event", "unknown"))
    
    # Create event
    event = WebhookEvent(
        id=_generate_event_id(),
        source=source,
        event_type=event_type,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        payload=data,
        headers={k: v for k, v in headers.items() if not k.lower().startswith("authorization")},
        signature_valid=True
    )
    
    # Queue event
    queue_event(event)
    
    _audit_log("webhook_received", f"source={source}, type={event_type}, id={event.id}")
    
    return web.json_response({
        "success": True,
        "event_id": event.id
    })


async def handle_events(request: web.Request) -> web.Response:
    """Get queued events"""
    limit = int(request.query.get("limit", 50))
    source = request.query.get("source")
    
    events = get_events(limit, source)
    
    return web.json_response({
        "success": True,
        "events": events,
        "count": len(events)
    })


async def handle_health(request: web.Request) -> web.Response:
    """Health check"""
    return web.json_response({
        "status": "healthy",
        "service": "webhook_receiver",
        "port": WEBHOOK_PORT,
        "queue_size": len(_event_queue)
    })


async def handle_clear(request: web.Request) -> web.Response:
    """Clear event queue"""
    clear_events()
    return web.json_response({"success": True})


# =============================================================================
# Server Setup
# =============================================================================

def create_app() -> web.Application:
    """Create aiohttp application"""
    app = web.Application()
    
    # Routes
    app.router.add_post("/webhook/{source}", handle_webhook)
    app.router.add_post("/webhook", handle_webhook)  # Default source
    app.router.add_get("/events", handle_events)
    app.router.add_get("/health", handle_health)
    app.router.add_post("/clear", handle_clear)
    
    return app


def run_server(port: int = WEBHOOK_PORT):
    """Run webhook server"""
    app = create_app()
    _audit_log("server_start", f"Webhook receiver starting on port {port}")
    print(f"🔗 Webhook Receiver starting on port {port}")
    print(f"   POST /webhook/{{source}} - Receive webhook")
    print(f"   GET  /events            - List queued events")
    print(f"   GET  /health            - Health check")
    web.run_app(app, port=port, print=None)


# =============================================================================
# MCP Interface (for querying events)
# =============================================================================

TOOLS = {
    "list_events": {
        "description": "List recent webhook events",
        "parameters": {
            "limit": {"type": "integer", "description": "Max events", "default": 50},
            "source": {"type": "string", "description": "Filter by source"}
        },
        "required": []
    },
    "clear_events": {
        "description": "Clear event queue",
        "parameters": {},
        "required": []
    },
    "status": {
        "description": "Get webhook receiver status",
        "parameters": {},
        "required": []
    }
}


def handle_tool(name: str, params: dict) -> Any:
    """MCP tool handler"""
    if name == "list_events":
        return {"success": True, "events": get_events(params.get("limit", 50), params.get("source"))}
    elif name == "clear_events":
        clear_events()
        return {"success": True}
    elif name == "status":
        return {
            "success": True,
            "port": WEBHOOK_PORT,
            "queue_size": len(_event_queue),
            "handlers_count": len(_event_handlers)
        }
    return {"success": False, "error": f"Unknown tool: {name}"}


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "events":
            print(json.dumps(get_events(), indent=2))
        elif cmd == "status":
            print(json.dumps(handle_tool("status", {}), indent=2))
        else:
            print(f"Unknown command: {cmd}")
    else:
        run_server()
