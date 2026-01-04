#!/usr/bin/env python3
"""
MCP n8n Workflow Bridge - Workflow automation and triggers
Part of ROCKY-ROXY-ROCKIN-V1: Unified Command Center

Story: RRR-003
Sprint: 1
Points: 8

Exposes:
- n8n_list_workflows: List all available workflows
- n8n_trigger_workflow: Trigger a workflow by ID or alias
- n8n_get_execution: Get execution status and output
- n8n_get_workflow: Get workflow details
- n8n_search_workflows: Search workflows by name/tags

Plus 30+ workflow aliases for common operations:
- onboard_student, send_invoice, post_social, etc.
"""

import json
import logging
import os
from typing import Dict, Any, Optional, List
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from datetime import datetime

logger = logging.getLogger("roxy.mcp.n8n")

# Configuration
N8N_BASE = os.environ.get("N8N_BASE_URL", "http://localhost:5678")
N8N_API_KEY = os.environ.get("N8N_API_KEY", "")  # Optional, for auth
TIMEOUT = 10

# Workflow aliases - map friendly names to workflow IDs
# These will be discovered dynamically but we predefine common ones
WORKFLOW_ALIASES = {
    # Student & Teaching workflows
    "onboard_student": "student-onboarding",
    "new_student": "student-onboarding",
    "student_welcome": "student-onboarding",
    "schedule_lesson": "lesson-scheduler",
    "lesson_reminder": "lesson-reminder",
    "practice_log": "practice-logger",
    "progress_report": "progress-report-generator",
    
    # Payment & Business workflows
    "send_invoice": "payment-invoice",
    "invoice": "payment-invoice",
    "payment_reminder": "payment-reminder",
    "receipt": "payment-receipt",
    
    # Social Media workflows
    "post_social": "social-media-post",
    "post_twitter": "twitter-post",
    "post_instagram": "instagram-post",
    "post_youtube": "youtube-upload",
    "social_schedule": "social-scheduler",
    
    # YouTube workflows
    "youtube_upload": "youtube-upload",
    "youtube_schedule": "youtube-scheduler",
    "youtube_analytics": "youtube-analytics",
    
    # Communication workflows
    "send_email": "email-sender",
    "email_blast": "email-blast",
    "newsletter": "newsletter-sender",
    "sms_alert": "sms-notification",
    
    # Backup & System workflows
    "backup_data": "data-backup",
    "sync_contacts": "contact-sync",
    "cleanup": "system-cleanup",
    "health_report": "system-health-report",
    
    # Rocky-specific workflows
    "rocky_daily_tip": "rocky-daily-tip",
    "rocky_practice_reminder": "rocky-practice-reminder",
    "rocky_achievement": "rocky-achievement-notification",
    
    # ROXY-specific workflows
    "roxy_code_review": "roxy-code-review-notification",
    "roxy_deploy_alert": "roxy-deploy-alert",
    "roxy_error_alert": "roxy-error-notification"
}

TOOLS = {
    "n8n_list_workflows": {
        "description": "List all available n8n workflows",
        "parameters": {
            "active_only": {"type": "boolean", "default": True, "description": "Only show active workflows"},
            "tags": {"type": "array", "default": None, "description": "Filter by tags"}
        }
    },
    "n8n_trigger_workflow": {
        "description": "Trigger a workflow by ID, name, or alias",
        "parameters": {
            "workflow": {"type": "string", "required": True, "description": "Workflow ID, name, or alias"},
            "payload": {"type": "object", "default": {}, "description": "Data to pass to the workflow"},
            "wait": {"type": "boolean", "default": False, "description": "Wait for execution to complete"}
        }
    },
    "n8n_get_execution": {
        "description": "Get status and output of a workflow execution",
        "parameters": {
            "execution_id": {"type": "string", "required": True, "description": "Execution ID"}
        }
    },
    "n8n_get_workflow": {
        "description": "Get details of a specific workflow",
        "parameters": {
            "workflow_id": {"type": "string", "required": True, "description": "Workflow ID"}
        }
    },
    "n8n_search_workflows": {
        "description": "Search workflows by name or description",
        "parameters": {
            "query": {"type": "string", "required": True, "description": "Search query"},
            "limit": {"type": "integer", "default": 10, "description": "Max results"}
        }
    }
}

# Add alias tools dynamically
for alias in WORKFLOW_ALIASES.keys():
    TOOLS[f"n8n_{alias}"] = {
        "description": f"Trigger the '{alias}' workflow (alias for {WORKFLOW_ALIASES[alias]})",
        "parameters": {
            "payload": {"type": "object", "default": {}, "description": "Data to pass to the workflow"}
        }
    }


def _get_headers() -> Dict[str, str]:
    """Get HTTP headers for n8n API"""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    if N8N_API_KEY:
        headers["X-N8N-API-KEY"] = N8N_API_KEY
    return headers


def _http_get(endpoint: str) -> Dict[str, Any]:
    """Make HTTP GET request to n8n API"""
    try:
        url = f"{N8N_BASE}/api/v1/{endpoint}"
        req = Request(url, headers=_get_headers())
        with urlopen(req, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except URLError as e:
        return {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def _http_post(endpoint: str, data: Dict) -> Dict[str, Any]:
    """Make HTTP POST request to n8n API"""
    try:
        url = f"{N8N_BASE}/api/v1/{endpoint}"
        body = json.dumps(data).encode()
        req = Request(url, data=body, headers=_get_headers())
        with urlopen(req, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except URLError as e:
        return {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def _resolve_workflow(workflow: str) -> Optional[str]:
    """Resolve workflow alias/name to workflow ID"""
    # Check if it's an alias
    if workflow in WORKFLOW_ALIASES:
        workflow = WORKFLOW_ALIASES[workflow]
    
    # If it looks like an ID (numeric or uuid-like), return it
    if workflow.isdigit() or len(workflow) == 36:
        return workflow
    
    # Otherwise, search by name
    workflows = _http_get("workflows")
    if "error" in workflows:
        return None
    
    for wf in workflows.get("data", []):
        if wf.get("name", "").lower() == workflow.lower():
            return wf.get("id")
        # Also check if name contains the search term
        if workflow.lower() in wf.get("name", "").lower():
            return wf.get("id")
    
    return None


def handle_tool(name: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    """Handle MCP tool call"""
    if params is None:
        params = {}
    
    try:
        # Handle alias tools (n8n_onboard_student, etc.)
        if name.startswith("n8n_") and name[4:] in WORKFLOW_ALIASES:
            alias = name[4:]
            workflow = WORKFLOW_ALIASES[alias]
            payload = params.get("payload", {})
            
            workflow_id = _resolve_workflow(workflow)
            if not workflow_id:
                return {"error": f"Could not resolve workflow alias: {alias}"}
            
            result = _http_post(f"workflows/{workflow_id}/execute", {"data": payload})
            if "error" not in result:
                logger.info(f"Triggered workflow via alias '{alias}': {workflow}")
            return {
                "alias": alias,
                "workflow": workflow,
                "workflow_id": workflow_id,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        if name == "n8n_list_workflows":
            active_only = params.get("active_only", True)
            tags = params.get("tags")
            
            result = _http_get("workflows")
            if "error" in result:
                return result
            
            workflows = result.get("data", [])
            
            # Filter active
            if active_only:
                workflows = [w for w in workflows if w.get("active", False)]
            
            # Filter by tags
            if tags:
                workflows = [w for w in workflows if any(t in w.get("tags", []) for t in tags)]
            
            return {
                "workflows": [
                    {
                        "id": w.get("id"),
                        "name": w.get("name"),
                        "active": w.get("active"),
                        "tags": w.get("tags", [])
                    }
                    for w in workflows
                ],
                "count": len(workflows),
                "aliases_available": list(WORKFLOW_ALIASES.keys()),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif name == "n8n_trigger_workflow":
            workflow = params.get("workflow")
            payload = params.get("payload", {})
            wait = params.get("wait", False)
            
            if not workflow:
                return {"error": "workflow is required"}
            
            workflow_id = _resolve_workflow(workflow)
            if not workflow_id:
                return {"error": f"Could not resolve workflow: {workflow}"}
            
            # Execute workflow
            endpoint = f"workflows/{workflow_id}/execute"
            result = _http_post(endpoint, {"data": payload})
            
            if "error" not in result:
                logger.info(f"Triggered workflow: {workflow} (ID: {workflow_id})")
            
            return {
                "workflow": workflow,
                "workflow_id": workflow_id,
                "execution": result,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif name == "n8n_get_execution":
            execution_id = params.get("execution_id")
            
            if not execution_id:
                return {"error": "execution_id is required"}
            
            return _http_get(f"executions/{execution_id}")
        
        elif name == "n8n_get_workflow":
            workflow_id = params.get("workflow_id")
            
            if not workflow_id:
                return {"error": "workflow_id is required"}
            
            return _http_get(f"workflows/{workflow_id}")
        
        elif name == "n8n_search_workflows":
            query = params.get("query")
            limit = params.get("limit", 10)
            
            if not query:
                return {"error": "query is required"}
            
            result = _http_get("workflows")
            if "error" in result:
                return result
            
            workflows = result.get("data", [])
            query_lower = query.lower()
            
            # Search by name and description
            matches = []
            for wf in workflows:
                name_match = query_lower in wf.get("name", "").lower()
                # n8n workflows don't always have descriptions in API response
                if name_match:
                    matches.append({
                        "id": wf.get("id"),
                        "name": wf.get("name"),
                        "active": wf.get("active"),
                        "tags": wf.get("tags", [])
                    })
            
            # Also check aliases
            alias_matches = [
                {"alias": k, "workflow": v}
                for k, v in WORKFLOW_ALIASES.items()
                if query_lower in k or query_lower in v
            ]
            
            return {
                "query": query,
                "workflows": matches[:limit],
                "alias_matches": alias_matches[:limit],
                "total_matches": len(matches),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        else:
            return {"error": f"Unknown tool: {name}"}
    
    except Exception as e:
        logger.error(f"Error in {name}: {e}")
        return {"error": str(e)}


def health_check() -> Dict[str, Any]:
    """Bridge health check for infrastructure monitoring"""
    result = _http_get("workflows")
    
    if "error" in result:
        status = "down"
        workflow_count = 0
    else:
        status = "up"
        workflow_count = len(result.get("data", []))
    
    return {
        "bridge": "mcp_n8n",
        "status": "healthy" if status == "up" else "degraded",
        "endpoints": {
            "n8n_api": {"url": N8N_BASE, "status": status}
        },
        "workflow_count": workflow_count,
        "aliases_available": len(WORKFLOW_ALIASES),
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    print("MCP n8n Bridge - Health Check")
    print(json.dumps(health_check(), indent=2))
