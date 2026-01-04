#!/usr/bin/env python3
"""
MCP Cross-Pollination Bridge - Expose cross-pollination as MCP tools
Part of ROCKY-ROXY-ROCKIN-V1: Sprint 3 - Cross-Pollination

Exposes all cross-pollination features as MCP tools for the UI.
"""

import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the cross-pollination module
from cross_pollination import (
    CrossPollinator,
    RockyEnhancedOrchestrator,
    RockyWorkflowTriggers,
    CitadelNotifier,
    UnifiedKnowledgeBase,
    FridaySyncProtocol,
)

# ═══════════════════════════════════════════════════════════════
# MCP Tool Definitions
# ═══════════════════════════════════════════════════════════════

TOOLS = {
    # RRR-010: Rocky in Orchestrator
    "cp_create_music_task": {
        "description": "Create a Rocky-enhanced task in Orchestrator with music context",
        "parameters": {
            "title": {"type": "string", "required": True},
            "description": {"type": "string", "required": True},
            "song": {"type": "string", "required": False},
            "skill": {"type": "string", "required": False},
            "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"], "default": "medium"},
        }
    },
    "cp_rocky_enhance_task": {
        "description": "Add Rocky commentary to an existing task",
        "parameters": {
            "task_id": {"type": "string", "required": True},
            "event": {"type": "string", "enum": ["task_created", "task_blocked", "task_completed"], "required": True},
        }
    },
    
    # RRR-011: n8n from Rocky
    "cp_trigger_workflow": {
        "description": "Trigger an n8n workflow with Rocky context",
        "parameters": {
            "workflow": {"type": "string", "enum": ["practice_reminder", "lesson_backup", "progress_report", "song_learned", "skill_milestone", "sync_to_friday", "backup_system"], "required": True},
            "payload": {"type": "object", "required": False},
        }
    },
    "cp_song_learned": {
        "description": "Trigger celebration workflow when a song is mastered",
        "parameters": {
            "song_name": {"type": "string", "required": True},
            "student_id": {"type": "string", "default": "default"},
        }
    },
    "cp_skill_milestone": {
        "description": "Trigger achievement workflow for skill progression",
        "parameters": {
            "skill": {"type": "string", "required": True},
            "level": {"type": "integer", "required": True},
            "student_id": {"type": "string", "default": "default"},
        }
    },
    
    # RRR-012: Citadel Notifications
    "cp_notify_friday": {
        "description": "Send a notification to Friday/Citadel",
        "parameters": {
            "title": {"type": "string", "required": True},
            "message": {"type": "string", "required": True},
            "priority": {"type": "string", "enum": ["low", "normal", "high", "critical"], "default": "normal"},
            "notification_type": {"type": "string", "enum": ["alert", "info", "task", "sync"], "default": "info"},
        }
    },
    "cp_friday_alert": {
        "description": "Send a high-priority alert to Friday",
        "parameters": {
            "title": {"type": "string", "required": True},
            "message": {"type": "string", "required": True},
        }
    },
    "cp_assign_friday_task": {
        "description": "Assign a task to Friday for remote execution",
        "parameters": {
            "title": {"type": "string", "required": True},
            "description": {"type": "string", "required": True},
            "due_date": {"type": "string", "required": False},
        }
    },
    
    # RRR-013: ChromaDB Cross-Index
    "cp_unified_search": {
        "description": "Search across all Rocky and ROXY knowledge bases",
        "parameters": {
            "query": {"type": "string", "required": True},
            "collections": {"type": "array", "items": {"type": "string"}, "required": False},
            "limit": {"type": "integer", "default": 10},
        }
    },
    "cp_search_music": {
        "description": "Search only music-related knowledge (lessons, songs)",
        "parameters": {
            "query": {"type": "string", "required": True},
            "limit": {"type": "integer", "default": 10},
        }
    },
    "cp_search_code": {
        "description": "Search only code/documentation knowledge",
        "parameters": {
            "query": {"type": "string", "required": True},
            "limit": {"type": "integer", "default": 10},
        }
    },
    "cp_add_to_knowledge": {
        "description": "Add a document to the knowledge base",
        "parameters": {
            "collection": {"type": "string", "enum": ["rocky_lessons", "rocky_songs", "roxy_docs", "roxy_code"], "required": True},
            "document": {"type": "string", "required": True},
            "metadata": {"type": "object", "required": False},
        }
    },
    
    # RRR-014: Friday Sync
    "cp_sync_domain": {
        "description": "Sync a specific domain with Friday",
        "parameters": {
            "domain": {"type": "string", "enum": ["tasks", "config", "knowledge", "workflows"], "required": True},
        }
    },
    "cp_sync_all": {
        "description": "Perform full sync with Friday across all domains",
        "parameters": {}
    },
    "cp_push_to_friday": {
        "description": "Push local changes to Friday",
        "parameters": {
            "domain": {"type": "string", "required": True},
            "changes": {"type": "array", "required": True},
            "force": {"type": "boolean", "default": False},
        }
    },
    "cp_pull_from_friday": {
        "description": "Pull remote changes from Friday",
        "parameters": {
            "domain": {"type": "string", "required": True},
        }
    },
    
    # Health & Status
    "cp_health_check": {
        "description": "Check health of all cross-pollination services",
        "parameters": {}
    },
}

# ═══════════════════════════════════════════════════════════════
# Tool Handler
# ═══════════════════════════════════════════════════════════════

class CrossPollinationBridge:
    """MCP Bridge for Cross-Pollination features"""
    
    def __init__(self):
        self._pollinator: Optional[CrossPollinator] = None
    
    async def get_pollinator(self) -> CrossPollinator:
        if not self._pollinator:
            self._pollinator = CrossPollinator()
        return self._pollinator
    
    async def close(self):
        if self._pollinator:
            await self._pollinator.close()
            self._pollinator = None
    
    async def handle_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an MCP tool call"""
        cp = await self.get_pollinator()
        
        try:
            # RRR-010: Rocky in Orchestrator
            if tool_name == "cp_create_music_task":
                return await cp.create_music_task(
                    title=params["title"],
                    description=params["description"],
                    song=params.get("song"),
                    skill=params.get("skill"),
                    priority=params.get("priority", "medium")
                )
            
            elif tool_name == "cp_rocky_enhance_task":
                return await cp.orchestrator.enhance_existing_task(
                    params["task_id"],
                    params["event"]
                )
            
            # RRR-011: n8n from Rocky
            elif tool_name == "cp_trigger_workflow":
                return await cp.workflows.trigger_workflow(
                    params["workflow"],
                    params.get("payload", {})
                )
            
            elif tool_name == "cp_song_learned":
                return await cp.trigger_on_song_learned(params["song_name"])
            
            elif tool_name == "cp_skill_milestone":
                return await cp.workflows.on_skill_milestone(
                    params["skill"],
                    params["level"],
                    params.get("student_id", "default")
                )
            
            # RRR-012: Citadel Notifications
            elif tool_name == "cp_notify_friday":
                return await cp.citadel.send_notification(
                    params["title"],
                    params["message"],
                    params.get("notification_type", "info"),
                    CitadelNotifier.Priority[params.get("priority", "normal").upper()]
                )
            
            elif tool_name == "cp_friday_alert":
                return await cp.citadel.alert(params["title"], params["message"])
            
            elif tool_name == "cp_assign_friday_task":
                return await cp.citadel.task_assignment(
                    params["title"],
                    params["description"],
                    params.get("due_date")
                )
            
            # RRR-013: ChromaDB Cross-Index
            elif tool_name == "cp_unified_search":
                return await cp.knowledge.search(
                    params["query"],
                    params.get("collections"),
                    params.get("limit", 10)
                )
            
            elif tool_name == "cp_search_music":
                return await cp.search(params["query"], music_only=True)
            
            elif tool_name == "cp_search_code":
                return await cp.search(params["query"], code_only=True)
            
            elif tool_name == "cp_add_to_knowledge":
                return await cp.knowledge.add_document(
                    params["collection"],
                    params["document"],
                    params.get("metadata")
                )
            
            # RRR-014: Friday Sync
            elif tool_name == "cp_sync_domain":
                return await cp.sync.full_sync(params["domain"])
            
            elif tool_name == "cp_sync_all":
                return await cp.sync.sync_all()
            
            elif tool_name == "cp_push_to_friday":
                return await cp.sync.push_changes(
                    params["domain"],
                    params["changes"],
                    params.get("force", False)
                )
            
            elif tool_name == "cp_pull_from_friday":
                return await cp.sync.pull_changes(params["domain"])
            
            # Health
            elif tool_name == "cp_health_check":
                return await cp.health_check()
            
            else:
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            return {"error": str(e), "tool": tool_name}


# Global bridge instance
_bridge: Optional[CrossPollinationBridge] = None

async def get_bridge() -> CrossPollinationBridge:
    global _bridge
    if not _bridge:
        _bridge = CrossPollinationBridge()
    return _bridge

async def handle_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Main entry point for tool handling"""
    bridge = await get_bridge()
    return await bridge.handle_tool(tool_name, params)

def get_tools() -> Dict[str, Any]:
    """Return tool definitions for MCP registration"""
    return TOOLS

async def health_check() -> Dict[str, Any]:
    """Health check for the bridge"""
    bridge = await get_bridge()
    cp = await bridge.get_pollinator()
    status = await cp.health_check()
    
    return {
        "bridge": "cross_pollination",
        "status": "healthy" if any(status.values()) else "degraded",
        "services": status,
        "tools_available": len(TOOLS),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ═══════════════════════════════════════════════════════════════
# CLI Test
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    async def test():
        print("🔄 MCP Cross-Pollination Bridge")
        print("=" * 50)
        
        # List tools
        print(f"\n📋 Available Tools ({len(TOOLS)}):")
        for name, spec in TOOLS.items():
            print(f"  • {name}: {spec['description'][:50]}...")
        
        # Health check
        print("\n💚 Health Check:")
        result = await health_check()
        print(f"  Status: {result['status']}")
        for svc, online in result['services'].items():
            icon = "✅" if online else "❌"
            print(f"  {icon} {svc}")
        
        # Test a tool
        print("\n🧪 Testing cp_create_music_task:")
        result = await handle_tool("cp_create_music_task", {
            "title": "Learn Stairway to Heaven intro",
            "description": "Practice the fingerpicking pattern",
            "song": "Stairway to Heaven",
            "skill": "fingerpicking",
            "priority": "medium"
        })
        print(f"  Result: {result}")
        
        # Cleanup
        bridge = await get_bridge()
        await bridge.close()
        
        print("\n✅ Bridge test complete!")
    
    asyncio.run(test())
