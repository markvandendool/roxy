#!/usr/bin/env python3
"""
Cross-Pollination Module - Rocky ↔ ROXY Integration Layer
Part of ROCKY-ROXY-ROCKIN-V1: Sprint 3 - Cross-Pollination

This module provides bidirectional integration between:
- Rocky (music teacher persona) 
- ROXY (dev assistant infrastructure)
- Orchestrator (task management)
- n8n (workflow automation)
- Citadel/Friday (remote execution)
- ChromaDB (unified knowledge base)

Stories:
- RRR-010: Rocky prompts in Orchestrator
- RRR-011: n8n triggers from Rocky  
- RRR-012: Citadel notifications
- RRR-013: ChromaDB cross-index
- RRR-014: Friday sync protocol
"""

import asyncio
import aiohttp
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cross_pollination")

# ═══════════════════════════════════════════════════════════════
# Service Endpoints
# ═══════════════════════════════════════════════════════════════

ENDPOINTS = {
    "roxy": "http://127.0.0.1:8766",
    "orchestrator": "http://127.0.0.1:3000",
    "podium": "ws://127.0.0.1:3847",
    "n8n": "http://127.0.0.1:5678",
    "chromadb": "http://127.0.0.1:8000",
    "friday_health": "http://10.0.0.65:8765",
    "friday_control": "http://10.0.0.65:8766",
    "ollama": "http://127.0.0.1:11434",
}

# ═══════════════════════════════════════════════════════════════
# RRR-010: Rocky Prompts in Orchestrator
# ═══════════════════════════════════════════════════════════════

class RockyEnhancedOrchestrator:
    """
    Enhances Orchestrator tasks with Rocky's music-aware context.
    
    Features:
    - Music metaphors in task descriptions
    - Rhythm-based priority suggestions
    - Practice-style task breakdowns
    - Motivational prompts from Rocky persona
    """
    
    ROCKY_PROMPTS = {
        "task_created": [
            "🎸 New task in the setlist! Let's rock this one!",
            "🎵 Added to your practice schedule. One step at a time!",
            "🎼 New piece to learn. Break it down, take it slow, then speed up!",
        ],
        "task_blocked": [
            "🎸 Hit a tricky passage? Let's isolate and practice that section!",
            "🎵 Stuck? Time to slow down and focus on the fundamentals.",
            "🎼 Every guitarist hits walls. Let's find a different fingering!",
        ],
        "task_completed": [
            "🎸 Nailed it! That's how you build a repertoire!",
            "🎵 Perfect execution! Ready to perform this one live!",
            "🎼 Another song mastered. Your setlist is growing!",
        ],
        "priority_high": [
            "🔥 This is your headline song - needs attention NOW!",
            "⚡ Critical passage - don't skip practice on this one!",
        ],
        "priority_low": [
            "🎶 Background rhythm part - keep it steady but relaxed.",
            "🎵 Nice to have in your repertoire, no rush.",
        ],
    }
    
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        
    @property
    def session(self) -> aiohttp.ClientSession:
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session
        
    async def close(self):
        if self._session:
            await self._session.close()
    
    def get_rocky_prompt(self, event_type: str, index: int = 0) -> str:
        """Get a Rocky-style prompt for an event type"""
        prompts = self.ROCKY_PROMPTS.get(event_type, ["🎸 Keep practicing!"])
        return prompts[index % len(prompts)]
    
    async def create_task_with_rocky(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        tags: List[str] = None,
        music_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a task in Orchestrator with Rocky's enhancements.
        
        Args:
            title: Task title
            description: Task description
            priority: low/medium/high/critical
            tags: Optional tags
            music_context: Optional music metadata (song, skill, etc.)
        """
        # Enhance description with Rocky prompt
        rocky_prompt = self.get_rocky_prompt(
            "priority_high" if priority in ("high", "critical") else "task_created"
        )
        
        enhanced_desc = f"{rocky_prompt}\n\n{description}"
        
        # Add music context if provided
        if music_context:
            enhanced_desc += f"\n\n🎵 Music Context:\n"
            for key, value in music_context.items():
                enhanced_desc += f"  • {key}: {value}\n"
        
        # Build task payload
        task_payload = {
            "title": title,
            "description": enhanced_desc,
            "priority": priority,
            "tags": tags or [],
            "metadata": {
                "source": "rocky_enhanced",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "music_context": music_context,
            }
        }
        
        try:
            # Send to Orchestrator via MCP bridge
            async with self.session.post(
                f"{ENDPOINTS['roxy']}/mcp/orchestrator/orchestrator_create_task",
                json=task_payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logger.info(f"[Rocky→Orchestrator] Task created: {title}")
                    return {"success": True, "task": result, "rocky_says": rocky_prompt}
                else:
                    return {"success": False, "error": f"Status {resp.status}"}
        except Exception as e:
            logger.error(f"[Rocky→Orchestrator] Failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def enhance_existing_task(self, task_id: str, event: str) -> Dict[str, Any]:
        """Add Rocky commentary to an existing task event"""
        prompt = self.get_rocky_prompt(event)
        
        try:
            async with self.session.post(
                f"{ENDPOINTS['roxy']}/mcp/orchestrator/orchestrator_update_task",
                json={
                    "task_id": task_id,
                    "comment": prompt,
                    "metadata": {"rocky_event": event}
                }
            ) as resp:
                return {"success": resp.status == 200, "rocky_says": prompt}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════
# RRR-011: n8n Workflow Triggers from Rocky
# ═══════════════════════════════════════════════════════════════

class RockyWorkflowTriggers:
    """
    Trigger n8n workflows based on music/learning events.
    
    Workflows that can be triggered:
    - practice_reminder: Daily practice nudges
    - lesson_backup: Auto-backup lesson recordings
    - progress_report: Weekly progress summaries
    - song_learned: Celebrate song completion
    - skill_milestone: Achievement unlocked
    """
    
    WORKFLOW_MAP = {
        "practice_reminder": "practice-reminder-webhook",
        "lesson_backup": "lesson-backup-webhook",
        "progress_report": "weekly-progress-webhook",
        "song_learned": "song-completion-webhook",
        "skill_milestone": "achievement-webhook",
        "sync_to_friday": "friday-sync-webhook",
        "backup_system": "full-backup-webhook",
    }
    
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        
    @property
    def session(self) -> aiohttp.ClientSession:
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session:
            await self._session.close()
    
    async def trigger_workflow(
        self,
        workflow_key: str,
        payload: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Trigger an n8n workflow via webhook.
        
        Args:
            workflow_key: Key from WORKFLOW_MAP
            payload: Data to send to the workflow
        """
        webhook_name = self.WORKFLOW_MAP.get(workflow_key)
        if not webhook_name:
            return {"success": False, "error": f"Unknown workflow: {workflow_key}"}
        
        webhook_url = f"{ENDPOINTS['n8n']}/webhook/{webhook_name}"
        
        data = {
            "source": "rocky_cross_pollination",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "workflow": workflow_key,
            **(payload or {})
        }
        
        try:
            async with self.session.post(
                webhook_url,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status in (200, 201, 202):
                    result = await resp.json() if resp.content_type == 'application/json' else {}
                    logger.info(f"[Rocky→n8n] Triggered: {workflow_key}")
                    return {"success": True, "workflow": workflow_key, "result": result}
                else:
                    return {"success": False, "error": f"Status {resp.status}"}
        except Exception as e:
            logger.error(f"[Rocky→n8n] Failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def on_song_learned(self, song_name: str, student_id: str = "default") -> Dict:
        """Trigger celebration workflow when a song is mastered"""
        return await self.trigger_workflow("song_learned", {
            "song": song_name,
            "student_id": student_id,
            "achievement": "song_mastered",
            "message": f"🎸 Congratulations! '{song_name}' is now in your repertoire!"
        })
    
    async def on_skill_milestone(
        self,
        skill: str,
        level: int,
        student_id: str = "default"
    ) -> Dict:
        """Trigger achievement workflow for skill progression"""
        return await self.trigger_workflow("skill_milestone", {
            "skill": skill,
            "level": level,
            "student_id": student_id,
            "message": f"⭐ Level {level} {skill} achieved!"
        })
    
    async def schedule_practice_reminder(
        self,
        time: str = "18:00",
        days: List[str] = None
    ) -> Dict:
        """Set up practice reminder workflow"""
        return await self.trigger_workflow("practice_reminder", {
            "schedule_time": time,
            "days": days or ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "action": "configure"
        })


# ═══════════════════════════════════════════════════════════════
# RRR-012: Citadel/Friday Notifications
# ═══════════════════════════════════════════════════════════════

class CitadelNotifier:
    """
    Send notifications to the Citadel/Friday remote system.
    
    Notification types:
    - alert: High-priority alerts
    - info: Informational messages
    - task: Task assignments for Friday
    - sync: State synchronization requests
    """
    
    class Priority(Enum):
        LOW = "low"
        NORMAL = "normal"
        HIGH = "high"
        CRITICAL = "critical"
    
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._friday_online: bool = False
        
    @property
    def session(self) -> aiohttp.ClientSession:
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session:
            await self._session.close()
    
    async def check_friday_status(self) -> Dict[str, Any]:
        """Check if Friday/Citadel is online"""
        try:
            async with self.session.get(
                f"{ENDPOINTS['friday_health']}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._friday_online = True
                    return {"online": True, "status": data}
        except Exception:
            pass
        
        self._friday_online = False
        return {"online": False, "status": None}
    
    async def send_notification(
        self,
        title: str,
        message: str,
        notification_type: str = "info",
        priority: Priority = Priority.NORMAL,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """
        Send a notification to Friday/Citadel.
        
        Args:
            title: Notification title
            message: Notification body
            notification_type: alert/info/task/sync
            priority: Priority level
            metadata: Additional data
        """
        payload = {
            "title": title,
            "message": message,
            "type": notification_type,
            "priority": priority.value,
            "source": "roxy_command_center",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }
        
        # Try direct Friday endpoint first
        try:
            async with self.session.post(
                f"{ENDPOINTS['friday_control']}/notify",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status in (200, 201, 202):
                    logger.info(f"[ROXY→Friday] Notification sent: {title}")
                    return {"success": True, "delivered_to": "friday_direct"}
        except Exception:
            pass
        
        # Fallback to MCP bridge → Orchestrator → Citadel
        try:
            async with self.session.post(
                f"{ENDPOINTS['roxy']}/mcp/orchestrator/orchestrator_dispatch_to_citadel",
                json={
                    "command": "notify",
                    "payload": payload
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    logger.info(f"[ROXY→Citadel] Notification queued: {title}")
                    return {"success": True, "delivered_to": "citadel_queue"}
        except Exception as e:
            logger.error(f"[Citadel] Notification failed: {e}")
        
        return {"success": False, "error": "All delivery methods failed"}
    
    async def alert(self, title: str, message: str, **kwargs) -> Dict:
        """Send a high-priority alert"""
        return await self.send_notification(
            title, message, "alert", self.Priority.HIGH, kwargs
        )
    
    async def task_assignment(
        self,
        task_title: str,
        task_description: str,
        due_date: Optional[str] = None
    ) -> Dict:
        """Assign a task to Friday"""
        return await self.send_notification(
            f"📋 Task: {task_title}",
            task_description,
            "task",
            self.Priority.NORMAL,
            {"due_date": due_date}
        )


# ═══════════════════════════════════════════════════════════════
# RRR-013: ChromaDB Cross-Index
# ═══════════════════════════════════════════════════════════════

class UnifiedKnowledgeBase:
    """
    Unified search across Rocky (music) and ROXY (dev) knowledge bases.
    
    Collections:
    - rocky_lessons: Music lessons, exercises, theory
    - rocky_songs: Song metadata, chord charts, tabs
    - roxy_docs: Technical documentation
    - roxy_code: Code snippets, examples
    - unified_index: Cross-referenced unified index
    """
    
    COLLECTIONS = {
        "rocky_lessons": "music lessons and theory",
        "rocky_songs": "song database and chord charts",
        "roxy_docs": "technical documentation",
        "roxy_code": "code snippets and examples",
        "unified_index": "cross-referenced search index"
    }
    
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        
    @property
    def session(self) -> aiohttp.ClientSession:
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session:
            await self._session.close()
    
    async def search(
        self,
        query: str,
        collections: List[str] = None,
        limit: int = 10,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Search across multiple knowledge base collections.
        
        Args:
            query: Search query
            collections: List of collections to search (default: all)
            limit: Max results per collection
            include_metadata: Include document metadata
        """
        target_collections = collections or list(self.COLLECTIONS.keys())
        all_results = []
        
        for collection in target_collections:
            try:
                async with self.session.post(
                    f"{ENDPOINTS['chromadb']}/api/v1/collections/{collection}/query",
                    json={
                        "query_texts": [query],
                        "n_results": limit,
                        "include": ["documents", "metadatas", "distances"] if include_metadata else ["documents"]
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("documents"):
                            for i, doc in enumerate(data["documents"][0]):
                                result = {
                                    "collection": collection,
                                    "document": doc,
                                    "score": 1 - (data.get("distances", [[]])[0][i] if data.get("distances") else 0)
                                }
                                if include_metadata and data.get("metadatas"):
                                    result["metadata"] = data["metadatas"][0][i]
                                all_results.append(result)
            except Exception as e:
                logger.warning(f"[ChromaDB] Search failed for {collection}: {e}")
        
        # Sort by relevance score
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return {
            "query": query,
            "total_results": len(all_results),
            "results": all_results[:limit * 2],  # Return top results across all collections
            "collections_searched": target_collections
        }
    
    async def add_document(
        self,
        collection: str,
        document: str,
        metadata: Dict = None,
        doc_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a document to a collection"""
        if collection not in self.COLLECTIONS:
            return {"success": False, "error": f"Unknown collection: {collection}"}
        
        doc_id = doc_id or f"{collection}_{datetime.now(timezone.utc).timestamp()}"
        
        try:
            async with self.session.post(
                f"{ENDPOINTS['chromadb']}/api/v1/collections/{collection}/add",
                json={
                    "ids": [doc_id],
                    "documents": [document],
                    "metadatas": [metadata or {}]
                }
            ) as resp:
                if resp.status in (200, 201):
                    logger.info(f"[ChromaDB] Added document to {collection}")
                    return {"success": True, "id": doc_id, "collection": collection}
        except Exception as e:
            logger.error(f"[ChromaDB] Add failed: {e}")
        
        return {"success": False, "error": "Failed to add document"}
    
    async def cross_index(
        self,
        source_collection: str,
        target_collection: str,
        link_type: str = "related"
    ) -> Dict[str, Any]:
        """
        Create cross-references between collections.
        
        This enables queries like "show me code examples for this music concept"
        """
        # This would typically run as a batch job to build cross-references
        # For now, we'll add it to the unified_index
        try:
            async with self.session.post(
                f"{ENDPOINTS['roxy']}/mcp/n8n/n8n_trigger_workflow",
                json={
                    "workflow_name": "chromadb-cross-index",
                    "payload": {
                        "source": source_collection,
                        "target": target_collection,
                        "link_type": link_type
                    }
                }
            ) as resp:
                return {"success": resp.status == 200, "job": "cross_index_queued"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════
# RRR-014: Friday Sync Protocol
# ═══════════════════════════════════════════════════════════════

@dataclass
class SyncState:
    """State object for Friday synchronization"""
    last_sync: Optional[datetime] = None
    local_version: int = 0
    remote_version: int = 0
    pending_changes: List[Dict] = field(default_factory=list)
    conflicts: List[Dict] = field(default_factory=list)

class FridaySyncProtocol:
    """
    Bidirectional state synchronization with Friday/Citadel.
    
    Sync domains:
    - tasks: Task state synchronization
    - config: Configuration sync
    - knowledge: Knowledge base sync
    - workflows: n8n workflow state
    """
    
    SYNC_DOMAINS = ["tasks", "config", "knowledge", "workflows"]
    
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._states: Dict[str, SyncState] = {d: SyncState() for d in self.SYNC_DOMAINS}
        
    @property
    def session(self) -> aiohttp.ClientSession:
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session:
            await self._session.close()
    
    async def get_remote_state(self, domain: str) -> Dict[str, Any]:
        """Fetch current state from Friday"""
        try:
            async with self.session.get(
                f"{ENDPOINTS['friday_control']}/sync/{domain}/state",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.warning(f"[FridaySync] Failed to get remote state for {domain}: {e}")
        
        return {"version": 0, "data": None}
    
    async def push_changes(
        self,
        domain: str,
        changes: List[Dict],
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Push local changes to Friday.
        
        Args:
            domain: Sync domain (tasks, config, etc.)
            changes: List of changes to push
            force: Force push even with conflicts
        """
        state = self._states.get(domain)
        if not state:
            return {"success": False, "error": f"Unknown domain: {domain}"}
        
        payload = {
            "domain": domain,
            "local_version": state.local_version,
            "changes": changes,
            "force": force,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            async with self.session.post(
                f"{ENDPOINTS['friday_control']}/sync/{domain}/push",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                result = await resp.json() if resp.content_type == 'application/json' else {}
                
                if resp.status == 200:
                    state.local_version += 1
                    state.remote_version = result.get("new_version", state.local_version)
                    state.last_sync = datetime.now(timezone.utc)
                    state.pending_changes = []
                    logger.info(f"[FridaySync] Pushed {len(changes)} changes to {domain}")
                    return {"success": True, "new_version": state.remote_version}
                    
                elif resp.status == 409:
                    # Conflict detected
                    state.conflicts = result.get("conflicts", [])
                    return {"success": False, "error": "conflict", "conflicts": state.conflicts}
                    
        except Exception as e:
            logger.error(f"[FridaySync] Push failed: {e}")
        
        return {"success": False, "error": "Push failed"}
    
    async def pull_changes(self, domain: str) -> Dict[str, Any]:
        """Pull remote changes from Friday"""
        state = self._states.get(domain)
        if not state:
            return {"success": False, "error": f"Unknown domain: {domain}"}
        
        try:
            async with self.session.get(
                f"{ENDPOINTS['friday_control']}/sync/{domain}/pull",
                params={"since_version": state.remote_version},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    changes = data.get("changes", [])
                    state.remote_version = data.get("version", state.remote_version)
                    state.last_sync = datetime.now(timezone.utc)
                    logger.info(f"[FridaySync] Pulled {len(changes)} changes from {domain}")
                    return {"success": True, "changes": changes, "version": state.remote_version}
        except Exception as e:
            logger.error(f"[FridaySync] Pull failed: {e}")
        
        return {"success": False, "error": "Pull failed"}
    
    async def full_sync(self, domain: str) -> Dict[str, Any]:
        """Perform a full bidirectional sync"""
        # First pull remote changes
        pull_result = await self.pull_changes(domain)
        
        # Then push local changes
        state = self._states[domain]
        if state.pending_changes:
            push_result = await self.push_changes(domain, state.pending_changes)
        else:
            push_result = {"success": True, "message": "No local changes"}
        
        return {
            "domain": domain,
            "pull": pull_result,
            "push": push_result,
            "synced_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def sync_all(self) -> Dict[str, Any]:
        """Sync all domains"""
        results = {}
        for domain in self.SYNC_DOMAINS:
            results[domain] = await self.full_sync(domain)
        return results
    
    def queue_change(self, domain: str, change: Dict):
        """Queue a local change for next sync"""
        if domain in self._states:
            self._states[domain].pending_changes.append({
                **change,
                "queued_at": datetime.now(timezone.utc).isoformat()
            })


# ═══════════════════════════════════════════════════════════════
# Unified Cross-Pollination Interface
# ═══════════════════════════════════════════════════════════════

class CrossPollinator:
    """
    Main interface for all cross-pollination operations.
    
    Usage:
        async with CrossPollinator() as cp:
            # Rocky → Orchestrator
            await cp.create_music_task("Practice scales", "G major scale exercises")
            
            # Rocky → n8n
            await cp.trigger_on_song_learned("Wonderwall")
            
            # ROXY → Citadel
            await cp.notify_friday("Build complete", "Production deploy successful")
            
            # Unified search
            results = await cp.search("chord progressions in Python")
            
            # Friday sync
            await cp.sync_with_friday()
    """
    
    def __init__(self):
        self.orchestrator = RockyEnhancedOrchestrator()
        self.workflows = RockyWorkflowTriggers()
        self.citadel = CitadelNotifier()
        self.knowledge = UnifiedKnowledgeBase()
        self.sync = FridaySyncProtocol()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()
    
    async def close(self):
        await self.orchestrator.close()
        await self.workflows.close()
        await self.citadel.close()
        await self.knowledge.close()
        await self.sync.close()
    
    # ─────────────────────────────────────────────────────────────
    # Convenience Methods
    # ─────────────────────────────────────────────────────────────
    
    async def create_music_task(
        self,
        title: str,
        description: str,
        song: str = None,
        skill: str = None,
        priority: str = "medium"
    ) -> Dict:
        """Create a Rocky-enhanced task in Orchestrator"""
        music_context = {}
        if song:
            music_context["song"] = song
        if skill:
            music_context["skill"] = skill
        
        return await self.orchestrator.create_task_with_rocky(
            title=title,
            description=description,
            priority=priority,
            tags=["music", "practice"],
            music_context=music_context or None
        )
    
    async def trigger_on_song_learned(self, song_name: str) -> Dict:
        """Trigger workflow when a song is mastered"""
        return await self.workflows.on_song_learned(song_name)
    
    async def notify_friday(
        self,
        title: str,
        message: str,
        priority: str = "normal"
    ) -> Dict:
        """Send notification to Friday/Citadel"""
        priority_map = {
            "low": CitadelNotifier.Priority.LOW,
            "normal": CitadelNotifier.Priority.NORMAL,
            "high": CitadelNotifier.Priority.HIGH,
            "critical": CitadelNotifier.Priority.CRITICAL,
        }
        return await self.citadel.send_notification(
            title, message, "info", priority_map.get(priority, CitadelNotifier.Priority.NORMAL)
        )
    
    async def search(
        self,
        query: str,
        music_only: bool = False,
        code_only: bool = False
    ) -> Dict:
        """Search unified knowledge base"""
        if music_only:
            collections = ["rocky_lessons", "rocky_songs"]
        elif code_only:
            collections = ["roxy_docs", "roxy_code"]
        else:
            collections = None  # All
        
        return await self.knowledge.search(query, collections)
    
    async def sync_with_friday(self, domain: str = None) -> Dict:
        """Sync with Friday"""
        if domain:
            return await self.sync.full_sync(domain)
        return await self.sync.sync_all()
    
    async def health_check(self) -> Dict[str, bool]:
        """Check all cross-pollination services"""
        status = {}
        
        # Check Friday
        friday_status = await self.citadel.check_friday_status()
        status["friday"] = friday_status.get("online", False)
        
        # Check ChromaDB
        try:
            async with self.knowledge.session.get(
                f"{ENDPOINTS['chromadb']}/api/v1/heartbeat"
            ) as resp:
                status["chromadb"] = resp.status == 200
        except:
            status["chromadb"] = False
        
        # Check n8n
        try:
            async with self.workflows.session.get(
                f"{ENDPOINTS['n8n']}/healthz"
            ) as resp:
                status["n8n"] = resp.status == 200
        except:
            status["n8n"] = False
        
        # Check Orchestrator (via ROXY)
        try:
            async with self.orchestrator.session.get(
                f"{ENDPOINTS['roxy']}/health"
            ) as resp:
                status["roxy"] = resp.status == 200
        except:
            status["roxy"] = False
        
        return status


# ═══════════════════════════════════════════════════════════════
# CLI Interface
# ═══════════════════════════════════════════════════════════════

async def main():
    """Test cross-pollination features"""
    print("=" * 60)
    print("🔄 ROCKY-ROXY Cross-Pollination Test")
    print("=" * 60)
    
    async with CrossPollinator() as cp:
        # Health check
        print("\n📡 Service Status:")
        status = await cp.health_check()
        for service, online in status.items():
            icon = "✅" if online else "❌"
            print(f"  {icon} {service}")
        
        # Test Rocky → Orchestrator
        print("\n🎸 Testing Rocky → Orchestrator:")
        result = await cp.create_music_task(
            title="Practice Pentatonic Scales",
            description="Run through all 5 positions of A minor pentatonic",
            skill="scales",
            priority="high"
        )
        print(f"  Result: {result.get('success', False)}")
        if result.get("rocky_says"):
            print(f"  Rocky says: {result['rocky_says']}")
        
        # Test unified search
        print("\n🔍 Testing Unified Search:")
        search_result = await cp.search("chord progressions")
        print(f"  Results: {search_result.get('total_results', 0)} documents found")
        
        print("\n" + "=" * 60)
        print("✅ Cross-Pollination Module Ready")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
