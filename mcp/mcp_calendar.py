#!/usr/bin/env python3
"""
MCP Calendar Server - Google Calendar Integration
==================================================
RU-004: Calendar MCP Server

Google Calendar integration with:
- OAuth token storage in vault
- Event creation/update/delete
- Calendar listing
- Free/busy queries

Tools:
- calendar_list: List all calendars
- calendar_events: Get events from calendar
- calendar_create: Create new event
- calendar_update: Update existing event
- calendar_delete: Delete event
- calendar_freebusy: Check availability

SECURITY INVARIANTS:
1. OAuth tokens stored in vault only
2. Automatic token refresh
3. All operations logged
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, List, Dict

# Import vault for token storage
import sys
sys.path.insert(0, str(Path(__file__).parent))
from mcp_vault import vault_get, vault_set

# Paths
ROXY_DIR = Path.home() / ".roxy"
AUDIT_LOG = ROXY_DIR / "logs" / "calendar_audit.log"
CONFIG_DIR = ROXY_DIR / "config"

# Google Calendar API
CALENDAR_API = "https://www.googleapis.com/calendar/v3"


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


def _get_access_token() -> Optional[str]:
    """Get Google access token from vault, refresh if needed"""
    # Get stored tokens
    access_result = vault_get("google_access_token")
    refresh_result = vault_get("google_refresh_token")
    expiry_result = vault_get("google_token_expiry")
    
    if not access_result.get("success"):
        return None
    
    access_token = access_result["value"]
    
    # Check if token expired
    if expiry_result.get("success"):
        try:
            expiry = float(expiry_result["value"])
            if time.time() > expiry - 60:  # Refresh 1 min before expiry
                # Need to refresh
                if refresh_result.get("success"):
                    new_token = _refresh_token(refresh_result["value"])
                    if new_token:
                        return new_token
        except:
            pass
    
    return access_token


def _refresh_token(refresh_token: str) -> Optional[str]:
    """Refresh Google access token"""
    import urllib.request
    import urllib.parse
    
    client_id_result = vault_get("google_client_id")
    client_secret_result = vault_get("google_client_secret")
    
    if not client_id_result.get("success") or not client_secret_result.get("success"):
        return None
    
    data = urllib.parse.urlencode({
        "client_id": client_id_result["value"],
        "client_secret": client_secret_result["value"],
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }).encode()
    
    try:
        req = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            
            new_access = result.get("access_token")
            expires_in = result.get("expires_in", 3600)
            
            if new_access:
                vault_set("google_access_token", new_access)
                vault_set("google_token_expiry", str(time.time() + expires_in))
                _audit_log("token_refresh", "Access token refreshed")
                return new_access
    except Exception as e:
        _audit_log("token_refresh", str(e), False)
    
    return None


def _api_call(method: str, endpoint: str, data: dict = None) -> dict:
    """Make Google Calendar API call"""
    import urllib.request
    import urllib.error
    
    token = _get_access_token()
    if not token:
        return {
            "success": False, 
            "error": "Google OAuth not configured. Store tokens in vault: google_access_token, google_refresh_token, google_client_id, google_client_secret"
        }
    
    url = f"{CALENDAR_API}{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        if data:
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


def calendar_list() -> dict:
    """
    List all calendars
    
    Returns:
        {"success": True, "calendars": [...]}
    """
    result = _api_call("GET", "/users/me/calendarList")
    
    if result.get("success"):
        calendars = []
        for cal in result.get("result", {}).get("items", []):
            calendars.append({
                "id": cal.get("id"),
                "summary": cal.get("summary"),
                "primary": cal.get("primary", False),
                "access_role": cal.get("accessRole")
            })
        _audit_log("list", f"Found {len(calendars)} calendars")
        return {"success": True, "calendars": calendars}
    
    _audit_log("list", result.get("error", ""), False)
    return result


def calendar_events(calendar_id: str = "primary", 
                    time_min: str = None, time_max: str = None,
                    max_results: int = 50, query: str = None) -> dict:
    """
    Get events from calendar
    
    Args:
        calendar_id: Calendar ID (default: primary)
        time_min: Start time (ISO format)
        time_max: End time (ISO format)
        max_results: Max events to return
        query: Search query
    
    Returns:
        {"success": True, "events": [...]}
    """
    import urllib.parse
    
    params = {
        "maxResults": min(max_results, 250),
        "singleEvents": "true",
        "orderBy": "startTime"
    }
    
    if time_min:
        params["timeMin"] = time_min
    else:
        # Default to now
        params["timeMin"] = datetime.now(timezone.utc).isoformat()
    
    if time_max:
        params["timeMax"] = time_max
    
    if query:
        params["q"] = query
    
    query_str = urllib.parse.urlencode(params)
    encoded_cal = urllib.parse.quote(calendar_id, safe='')
    
    result = _api_call("GET", f"/calendars/{encoded_cal}/events?{query_str}")
    
    if result.get("success"):
        events = []
        for evt in result.get("result", {}).get("items", []):
            start = evt.get("start", {})
            end = evt.get("end", {})
            events.append({
                "id": evt.get("id"),
                "summary": evt.get("summary"),
                "description": evt.get("description", "")[:200],
                "start": start.get("dateTime") or start.get("date"),
                "end": end.get("dateTime") or end.get("date"),
                "location": evt.get("location"),
                "status": evt.get("status"),
                "html_link": evt.get("htmlLink")
            })
        _audit_log("events", f"calendar={calendar_id}, count={len(events)}")
        return {"success": True, "events": events, "count": len(events)}
    
    _audit_log("events", result.get("error", ""), False)
    return result


def calendar_create(summary: str, start: str, end: str,
                    calendar_id: str = "primary",
                    description: str = "", location: str = "",
                    attendees: List[str] = None,
                    reminders: List[Dict] = None) -> dict:
    """
    Create new event
    
    Args:
        summary: Event title
        start: Start time (ISO format or YYYY-MM-DD for all-day)
        end: End time
        calendar_id: Target calendar
        description: Event description
        location: Event location
        attendees: List of email addresses
        reminders: Custom reminders [{method: 'email'/'popup', minutes: 10}]
    
    Returns:
        {"success": True, "event_id": str, "html_link": str}
    """
    import urllib.parse
    
    # Detect all-day vs timed event
    is_all_day = len(start) == 10  # YYYY-MM-DD format
    
    event = {
        "summary": summary,
        "description": description,
        "location": location
    }
    
    if is_all_day:
        event["start"] = {"date": start}
        event["end"] = {"date": end}
    else:
        event["start"] = {"dateTime": start}
        event["end"] = {"dateTime": end}
    
    if attendees:
        event["attendees"] = [{"email": email} for email in attendees]
    
    if reminders:
        event["reminders"] = {
            "useDefault": False,
            "overrides": reminders
        }
    
    encoded_cal = urllib.parse.quote(calendar_id, safe='')
    result = _api_call("POST", f"/calendars/{encoded_cal}/events", event)
    
    if result.get("success"):
        evt = result.get("result", {})
        _audit_log("create", f"event={evt.get('id')}, summary={summary[:50]}")
        return {
            "success": True,
            "event_id": evt.get("id"),
            "html_link": evt.get("htmlLink")
        }
    
    _audit_log("create", result.get("error", ""), False)
    return result


def calendar_update(event_id: str, calendar_id: str = "primary",
                    summary: str = None, start: str = None, end: str = None,
                    description: str = None, location: str = None) -> dict:
    """
    Update existing event
    
    Args:
        event_id: Event ID to update
        calendar_id: Calendar containing event
        summary: New title
        start: New start time
        end: New end time
        description: New description
        location: New location
    
    Returns:
        {"success": True, "event_id": str}
    """
    import urllib.parse
    
    # First get existing event
    encoded_cal = urllib.parse.quote(calendar_id, safe='')
    get_result = _api_call("GET", f"/calendars/{encoded_cal}/events/{event_id}")
    
    if not get_result.get("success"):
        return get_result
    
    event = get_result["result"]
    
    # Update fields
    if summary is not None:
        event["summary"] = summary
    if description is not None:
        event["description"] = description
    if location is not None:
        event["location"] = location
    if start is not None:
        is_all_day = len(start) == 10
        if is_all_day:
            event["start"] = {"date": start}
        else:
            event["start"] = {"dateTime": start}
    if end is not None:
        is_all_day = len(end) == 10
        if is_all_day:
            event["end"] = {"date": end}
        else:
            event["end"] = {"dateTime": end}
    
    result = _api_call("PUT", f"/calendars/{encoded_cal}/events/{event_id}", event)
    
    if result.get("success"):
        _audit_log("update", f"event={event_id}")
        return {"success": True, "event_id": event_id}
    
    _audit_log("update", result.get("error", ""), False)
    return result


def calendar_delete(event_id: str, calendar_id: str = "primary") -> dict:
    """
    Delete event
    
    Args:
        event_id: Event ID to delete
        calendar_id: Calendar containing event
    
    Returns:
        {"success": True}
    """
    import urllib.parse
    
    encoded_cal = urllib.parse.quote(calendar_id, safe='')
    result = _api_call("DELETE", f"/calendars/{encoded_cal}/events/{event_id}")
    
    if result.get("success"):
        _audit_log("delete", f"event={event_id}")
        return {"success": True}
    
    _audit_log("delete", result.get("error", ""), False)
    return result


def calendar_freebusy(time_min: str, time_max: str, 
                      calendars: List[str] = None) -> dict:
    """
    Check free/busy status
    
    Args:
        time_min: Start of range (ISO format)
        time_max: End of range (ISO format)
        calendars: List of calendar IDs (default: primary)
    
    Returns:
        {"success": True, "busy": [...]}
    """
    if calendars is None:
        calendars = ["primary"]
    
    data = {
        "timeMin": time_min,
        "timeMax": time_max,
        "items": [{"id": cal} for cal in calendars]
    }
    
    result = _api_call("POST", "/freeBusy", data)
    
    if result.get("success"):
        busy_times = []
        for cal_id, cal_data in result.get("result", {}).get("calendars", {}).items():
            for busy in cal_data.get("busy", []):
                busy_times.append({
                    "calendar": cal_id,
                    "start": busy.get("start"),
                    "end": busy.get("end")
                })
        _audit_log("freebusy", f"Found {len(busy_times)} busy blocks")
        return {"success": True, "busy": busy_times}
    
    _audit_log("freebusy", result.get("error", ""), False)
    return result


# =============================================================================
# MCP Server Interface
# =============================================================================

TOOLS = {
    "list": {
        "description": "List all Google calendars",
        "parameters": {},
        "required": []
    },
    "events": {
        "description": "Get events from calendar",
        "parameters": {
            "calendar_id": {"type": "string", "description": "Calendar ID", "default": "primary"},
            "time_min": {"type": "string", "description": "Start time (ISO format)"},
            "time_max": {"type": "string", "description": "End time (ISO format)"},
            "max_results": {"type": "integer", "description": "Max events", "default": 50},
            "query": {"type": "string", "description": "Search query"}
        },
        "required": []
    },
    "create": {
        "description": "Create new calendar event",
        "parameters": {
            "summary": {"type": "string", "description": "Event title"},
            "start": {"type": "string", "description": "Start time (ISO or YYYY-MM-DD)"},
            "end": {"type": "string", "description": "End time"},
            "calendar_id": {"type": "string", "default": "primary"},
            "description": {"type": "string"},
            "location": {"type": "string"},
            "attendees": {"type": "array", "description": "Email addresses"},
            "reminders": {"type": "array", "description": "Custom reminders"}
        },
        "required": ["summary", "start", "end"]
    },
    "update": {
        "description": "Update existing calendar event",
        "parameters": {
            "event_id": {"type": "string", "description": "Event ID"},
            "calendar_id": {"type": "string", "default": "primary"},
            "summary": {"type": "string"},
            "start": {"type": "string"},
            "end": {"type": "string"},
            "description": {"type": "string"},
            "location": {"type": "string"}
        },
        "required": ["event_id"]
    },
    "delete": {
        "description": "Delete calendar event",
        "parameters": {
            "event_id": {"type": "string", "description": "Event ID"},
            "calendar_id": {"type": "string", "default": "primary"}
        },
        "required": ["event_id"]
    },
    "freebusy": {
        "description": "Check free/busy status",
        "parameters": {
            "time_min": {"type": "string", "description": "Start of range"},
            "time_max": {"type": "string", "description": "End of range"},
            "calendars": {"type": "array", "description": "Calendar IDs"}
        },
        "required": ["time_min", "time_max"]
    }
}


def handle_tool(name: str, params: dict) -> Any:
    """MCP tool handler"""
    handlers = {
        "list": lambda p: calendar_list(),
        "events": lambda p: calendar_events(
            p.get("calendar_id", "primary"),
            p.get("time_min"), p.get("time_max"),
            p.get("max_results", 50), p.get("query")
        ),
        "create": lambda p: calendar_create(
            p["summary"], p["start"], p["end"],
            p.get("calendar_id", "primary"),
            p.get("description", ""), p.get("location", ""),
            p.get("attendees"), p.get("reminders")
        ),
        "update": lambda p: calendar_update(
            p["event_id"], p.get("calendar_id", "primary"),
            p.get("summary"), p.get("start"), p.get("end"),
            p.get("description"), p.get("location")
        ),
        "delete": lambda p: calendar_delete(p["event_id"], p.get("calendar_id", "primary")),
        "freebusy": lambda p: calendar_freebusy(p["time_min"], p["time_max"], p.get("calendars"))
    }
    
    if name not in handlers:
        return {"success": False, "error": f"Unknown tool: {name}"}
    
    return handlers[name](params)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: mcp_calendar.py <command>")
        print("Commands: list, events")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "list":
        result = calendar_list()
    elif cmd == "events":
        result = calendar_events()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
    
    print(json.dumps(result, indent=2))
