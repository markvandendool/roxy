#!/usr/bin/env python3
"""
MCP Luno Orchestrator Bridge - Task management and distributed execution
Part of ROCKY-ROXY-ROCKIN-V1: Unified Command Center

Story: RRR-001
Sprint: 1
Points: 8

Exposes:
- orchestrator_create_task: Create a new task in Luno
- orchestrator_get_status: Get task status
- orchestrator_dispatch_to_citadel: Send task to Friday/Citadel worker
- orchestrator_cancel_task: Cancel a running task
- orchestrator_list_tasks: List all tasks
- citadel_health_check: Check Citadel worker health
"""

import json
import logging
import os
from typing import Dict, Any, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from datetime import datetime

logger = logging.getLogger("roxy.mcp.orchestrator")

# Configuration
LUNO_API_BASE = (
    os.getenv("ROXY_ORCHESTRATOR_BASE")
    or os.getenv("ROXY_PODIUM_BASE_URL")
    or os.getenv("PODIUM_API_URL")
    or "http://127.0.0.1:3847"
)
LUNO_PODIUM_WS = os.getenv("ROXY_PODIUM_WS") or "ws://127.0.0.1:3847"
CITADEL_HOST = "10.0.0.65"
CITADEL_HEALTH_PORT = 8765
CITADEL_CONTROL_PORT = 8766
TIMEOUT = 5  # seconds

TOOLS = {
    "orchestrator_create_task": {
        "description": "Create a new task in Luno Orchestrator",
        "parameters": {
            "name": {"type": "string", "required": True, "description": "Task name"},
            "type": {"type": "string", "required": True, "description": "Task type: dev|music|voice|rag"},
            "payload": {"type": "object", "default": {}, "description": "Task-specific payload"},
            "priority": {"type": "integer", "default": 5, "description": "Priority 1-10 (higher=urgent)"}
        }
    },
    "orchestrator_get_status": {
        "description": "Get status of a task by ID",
        "parameters": {
            "task_id": {"type": "string", "required": True, "description": "Task UUID"}
        }
    },
    "orchestrator_dispatch_to_citadel": {
        "description": "Dispatch a task to Friday/Citadel worker at 10.0.0.65",
        "parameters": {
            "task_id": {"type": "string", "required": True, "description": "Task UUID to dispatch"},
            "worker": {"type": "string", "default": "friday", "description": "Target worker name"}
        }
    },
    "orchestrator_cancel_task": {
        "description": "Cancel a running task",
        "parameters": {
            "task_id": {"type": "string", "required": True, "description": "Task UUID to cancel"}
        }
    },
    "orchestrator_list_tasks": {
        "description": "List all tasks with optional filtering",
        "parameters": {
            "status": {"type": "string", "default": None, "description": "Filter by status: pending|running|completed|failed"},
            "type": {"type": "string", "default": None, "description": "Filter by task type"},
            "limit": {"type": "integer", "default": 20, "description": "Max tasks to return"}
        }
    },
    "citadel_health_check": {
        "description": "Check health of Citadel distributed worker network",
        "parameters": {
            "worker": {"type": "string", "default": "friday", "description": "Specific worker to check, or 'all'"}
        }
    }
}


def _auth_headers() -> Dict[str, str]:
    token = os.getenv("ROXY_PODIUM_TOKEN") or os.getenv("PODIUM_AUTH_TOKEN") or ""
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _http_get(url: str, timeout: int = TIMEOUT) -> Dict[str, Any]:
    """Make HTTP GET request with error handling"""
    try:
        req = Request(url, headers=_auth_headers())
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        if e.code == 503:
            # 503 with JSON body means reachable but degraded
            try:
                body = e.read().decode()
                parsed = json.loads(body)
                parsed["http_status"] = 503
                parsed["reachable"] = True
                return parsed
            except Exception:
                return {"error": f"HTTP 503: {e.reason}", "status": 503}
        return {"error": f"HTTP {e.code}: {e.reason}", "status": e.code}
    except URLError as e:
        return {"error": f"Connection failed: {e.reason}", "status": 0}
    except Exception as e:
        return {"error": str(e), "status": -1}


def _http_post(url: str, data: Dict, timeout: int = TIMEOUT) -> Dict[str, Any]:
    """Make HTTP POST request with error handling"""
    try:
        body = json.dumps(data).encode()
        headers = _auth_headers()
        headers["Content-Type"] = "application/json"
        req = Request(url, data=body, headers=headers)
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}", "status": e.code}
    except URLError as e:
        return {"error": f"Connection failed: {e.reason}", "status": 0}
    except Exception as e:
        return {"error": str(e), "status": -1}


def handle_tool(name: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    """Handle MCP tool call"""
    if params is None:
        params = {}
    
    try:
        if name == "orchestrator_create_task":
            task_name = params.get("name")
            payload = params.get("payload", {}) or {}

            if not task_name and not payload:
                return {"error": "name or payload with storyId is required"}

            story_id = (
                payload.get("storyId")
                or payload.get("story_id")
                or payload.get("id")
                or task_name
            )
            if not story_id:
                return {"error": "Unable to determine storyId for enqueue"}

            force = bool(payload.get("force") or payload.get("bypassDependencies") or payload.get("bypass_dependencies"))
            command = {
                "type": "FORCE_ENQUEUE_STORY" if force else "ENQUEUE_STORY",
                "storyId": story_id,
            }
            if force:
                command["bypassDependencies"] = True

            result = _http_post(f"{LUNO_API_BASE}/api/command", command)
            if "error" not in result:
                logger.info(f"Enqueued story: {story_id}")
            return result
        
        elif name == "orchestrator_get_status":
            task_id = params.get("task_id")
            if task_id:
                result = _http_get(f"{LUNO_API_BASE}/api/logs?limit=200")
                return {"task_id": task_id, "logs": result}
            return _http_get(f"{LUNO_API_BASE}/health/orchestrator")
        
        elif name == "orchestrator_dispatch_to_citadel":
            task_id = params.get("task_id")
            worker = params.get("worker", "friday")
            
            if not task_id:
                return {"error": "task_id is required"}
            
            # First check if Citadel is healthy
            citadel_url = f"http://{CITADEL_HOST}:{CITADEL_CONTROL_PORT}/dispatch"
            dispatch_data = {
                "task_id": task_id,
                "worker": worker,
                "dispatched_at": datetime.utcnow().isoformat()
            }
            
            result = _http_post(citadel_url, dispatch_data)
            if "error" not in result:
                logger.info(f"Dispatched task {task_id} to {worker}")
            return result
        
        elif name == "orchestrator_cancel_task":
            task_id = params.get("task_id")
            if not task_id:
                return {"error": "task_id is required"}
            command = {"type": "CANCEL_STORY", "storyId": task_id}
            return _http_post(f"{LUNO_API_BASE}/api/command", command)
        
        elif name == "orchestrator_list_tasks":
            limit = params.get("limit", 50)
            metrics = _http_get(f"{LUNO_API_BASE}/api/metrics")
            logs = _http_get(f"{LUNO_API_BASE}/api/logs?limit={limit}")
            return {"metrics": metrics, "logs": logs}
        
        elif name == "citadel_health_check":
            worker = params.get("worker", "friday")
            
            workers = {}
            
            # Check Friday (primary worker)
            if worker in ("friday", "all"):
                friday_health = _http_get(f"http://{CITADEL_HOST}:{CITADEL_HEALTH_PORT}/health")
                workers["friday"] = {
                    "host": CITADEL_HOST,
                    "health_port": CITADEL_HEALTH_PORT,
                    "control_port": CITADEL_CONTROL_PORT,
                    "status": "healthy" if "error" not in friday_health else "unreachable",
                    "response": friday_health
                }
            
            return {
                "workers": workers,
                "timestamp": datetime.utcnow().isoformat(),
                "summary": {
                    "total": len(workers),
                    "healthy": sum(1 for w in workers.values() if w["status"] == "healthy"),
                    "unreachable": sum(1 for w in workers.values() if w["status"] == "unreachable")
                }
            }
        
        else:
            return {"error": f"Unknown tool: {name}"}
    
    except Exception as e:
        logger.error(f"Error in {name}: {e}")
        return {"error": str(e)}


def health_check() -> Dict[str, Any]:
    """Bridge health check for infrastructure monitoring"""
    luno_status = _http_get(f"{LUNO_API_BASE}/health/orchestrator")
    citadel_status = _http_get(f"http://{CITADEL_HOST}:{CITADEL_HEALTH_PORT}/health")

    luno_error = isinstance(luno_status, dict) and "error" in luno_status
    luno_reachable = bool(luno_status.get("reachable")) if isinstance(luno_status, dict) else False
    if not luno_error:
        luno_reachable = True
    http_status = luno_status.get("http_status") if isinstance(luno_status, dict) else None

    luno_ready = True
    luno_state = "ok"
    if luno_error or not luno_reachable:
        luno_ready = False
        luno_state = "down"
    elif http_status == 503 or (isinstance(luno_status, dict) and luno_status.get("status") == "degraded"):
        luno_ready = False
        luno_state = "degraded"

    return {
        "bridge": "mcp_orchestrator",
        "status": "healthy" if (luno_reachable and luno_ready) else "degraded",
        "endpoints": {
            "luno_api": {
                "url": LUNO_API_BASE,
                "up": bool(luno_reachable and not luno_error),
                "ready": bool(luno_ready),
                "state": luno_state,
                "http_status": http_status
            },
            "citadel": {
                "url": f"http://{CITADEL_HOST}:{CITADEL_HEALTH_PORT}",
                "status": "up" if "error" not in citadel_status else "down"
            }
        },
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    # Quick test
    print("MCP Orchestrator Bridge - Health Check")
    print(json.dumps(health_check(), indent=2))
