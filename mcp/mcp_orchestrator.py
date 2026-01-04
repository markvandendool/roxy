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
from typing import Dict, Any, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from datetime import datetime

logger = logging.getLogger("roxy.mcp.orchestrator")

# Configuration
LUNO_API_BASE = "http://localhost:3000"
LUNO_PODIUM_WS = "ws://localhost:3847"
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


def _http_get(url: str, timeout: int = TIMEOUT) -> Dict[str, Any]:
    """Make HTTP GET request with error handling"""
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}", "status": e.code}
    except URLError as e:
        return {"error": f"Connection failed: {e.reason}", "status": 0}
    except Exception as e:
        return {"error": str(e), "status": -1}


def _http_post(url: str, data: Dict, timeout: int = TIMEOUT) -> Dict[str, Any]:
    """Make HTTP POST request with error handling"""
    try:
        body = json.dumps(data).encode()
        req = Request(url, data=body, headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
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
            task_type = params.get("type")
            payload = params.get("payload", {})
            priority = params.get("priority", 5)
            
            if not task_name or not task_type:
                return {"error": "name and type are required"}
            
            task_data = {
                "name": task_name,
                "type": task_type,
                "payload": payload,
                "priority": priority,
                "created_at": datetime.utcnow().isoformat(),
                "status": "pending"
            }
            
            result = _http_post(f"{LUNO_API_BASE}/api/tasks", task_data)
            if "error" not in result:
                logger.info(f"Created task: {task_name} ({task_type})")
            return result
        
        elif name == "orchestrator_get_status":
            task_id = params.get("task_id")
            if not task_id:
                return {"error": "task_id is required"}
            
            return _http_get(f"{LUNO_API_BASE}/api/tasks/{task_id}")
        
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
            
            cancel_data = {"status": "cancelled", "cancelled_at": datetime.utcnow().isoformat()}
            return _http_post(f"{LUNO_API_BASE}/api/tasks/{task_id}/cancel", cancel_data)
        
        elif name == "orchestrator_list_tasks":
            status = params.get("status")
            task_type = params.get("type")
            limit = params.get("limit", 20)
            
            query_parts = [f"limit={limit}"]
            if status:
                query_parts.append(f"status={status}")
            if task_type:
                query_parts.append(f"type={task_type}")
            
            query = "&".join(query_parts)
            return _http_get(f"{LUNO_API_BASE}/api/tasks?{query}")
        
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
    luno_status = _http_get(f"{LUNO_API_BASE}/api/health")
    citadel_status = _http_get(f"http://{CITADEL_HOST}:{CITADEL_HEALTH_PORT}/health")
    
    return {
        "bridge": "mcp_orchestrator",
        "status": "healthy" if "error" not in luno_status else "degraded",
        "endpoints": {
            "luno_api": {
                "url": LUNO_API_BASE,
                "status": "up" if "error" not in luno_status else "down"
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
