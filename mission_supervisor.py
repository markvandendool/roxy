#!/usr/bin/env python3
"""
Mission Supervisor - Lease-backed autonomous story execution.

Extends the background scheduler with mission-level execution:
  - MissionLedger: tracks active/complete/failed missions
  - MissionEnvelope: goal, constraints, evidence, verification plan
  - execute_mission(): calls ROXY streaming API with story goal
  - create_mission_task(): integrates with BackgroundScheduler

Mission lifecycle:
  ACQUIRED → RUNNING → VERIFYING → COMPLETE|FAILED
  (lease expires) → EXPIRED
"""
import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("roxy.mission_supervisor")

ROXY_DIR = Path.home() / ".roxy"
MISSION_LEDGER = ROXY_DIR / "data" / "mission_ledger.json"
EVIDENCE_DIR = ROXY_DIR / "evidence" / "missions"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

ROXY_BASE_URL = os.getenv("ROXY_BASE_URL", "http://127.0.0.1:8766")
AUTH_TOKEN_FILE = ROXY_DIR / "secret.token"

DEFAULT_MISSION_TIMEOUT = 600.0
DEFAULT_LEASE_TTL = 300.0
MAX_CONCURRENT_MISSIONS = 1


class MissionStatus(str, Enum):
    PENDING = "pending"
    ACQUIRED = "acquired"
    RUNNING = "running"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class MissionEnvelope:
    mission_id: str
    story_id: str
    story_title: str
    goal: str
    constraints: List[str] = field(default_factory=list)
    required_evidence: List[str] = field(default_factory=list)
    tool_budget: int = 10
    verification_plan: List[str] = field(default_factory=list)
    rollback_command: str = ""
    files_in_scope: List[str] = field(default_factory=list)
    max_retries: int = 2


@dataclass
class Mission:
    mission_id: str
    story_id: str
    story_title: str
    status: MissionStatus
    goal: str
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    lease_expires_at: Optional[float] = None
    attempts: int = 0
    max_retries: int = 2
    tool_calls: List[Dict] = field(default_factory=list)
    verification_results: List[str] = field(default_factory=list)
    evidence_bundle: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    files_modified: List[str] = field(default_factory=list)
    files_in_scope: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    required_evidence: List[str] = field(default_factory=list)
    tool_budget: int = 10
    verification_plan: List[str] = field(default_factory=list)
    rollback_command: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "story_id": self.story_id,
            "story_title": self.story_title,
            "status": self.status.value,
            "goal": self.goal,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "lease_expires_at": self.lease_expires_at,
            "attempts": self.attempts,
            "max_retries": self.max_retries,
            "tool_calls": self.tool_calls,
            "verification_results": self.verification_results,
            "evidence_bundle": self.evidence_bundle,
            "error": self.error,
            "files_modified": self.files_modified,
            "constraints": self.constraints,
            "required_evidence": self.required_evidence,
            "tool_budget": self.tool_budget,
            "verification_plan": self.verification_plan,
            "rollback_command": self.rollback_command,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Mission":
        status = MissionStatus(data.get("status", "pending"))
        m = cls(
            mission_id=data["mission_id"],
            story_id=data["story_id"],
            story_title=data.get("story_title", ""),
            status=status,
            goal=data.get("goal", ""),
            created_at=data.get("created_at", time.time()),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            lease_expires_at=data.get("lease_expires_at"),
            attempts=data.get("attempts", 0),
            max_retries=data.get("max_retries", 2),
            tool_calls=data.get("tool_calls", []),
            verification_results=data.get("verification_results", []),
            evidence_bundle=data.get("evidence_bundle", {}),
            error=data.get("error", ""),
            files_modified=data.get("files_modified", []),
            constraints=data.get("constraints", []),
            required_evidence=data.get("required_evidence", []),
            tool_budget=data.get("tool_budget", 10),
            verification_plan=data.get("verification_plan", []),
            rollback_command=data.get("rollback_command", ""),
        )
        return m


class MissionLedger:
    """
    Tracks mission lifecycle with lease management.
    Persists to JSON for crash recovery.
    """

    def __init__(self):
        self.missions: Dict[str, Mission] = {}
        self._active: Optional[str] = None
        self._load()

    def _load(self):
        if MISSION_LEDGER.exists():
            try:
                with open(MISSION_LEDGER) as f:
                    data = json.load(f)
                self.missions = {
                    k: Mission.from_dict(v) for k, v in data.get("missions", {}).items()
                }
                self._active = data.get("active_mission_id")
            except Exception as e:
                logger.warning(f"Failed to load mission ledger: {e}")

    def _save(self):
        try:
            MISSION_LEDGER.parent.mkdir(parents=True, exist_ok=True)
            with open(MISSION_LEDGER, "w") as f:
                json.dump({
                    "missions": {k: v.to_dict() for k, v in self.missions.items()},
                    "active_mission_id": self._active,
                    "saved_at": time.time(),
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save mission ledger: {e}")

    def create_mission(self, envelope: MissionEnvelope) -> Mission:
        mission = Mission(
            mission_id=envelope.mission_id,
            story_id=envelope.story_id,
            story_title=envelope.story_title,
            status=MissionStatus.ACQUIRED,
            goal=envelope.goal,
            constraints=envelope.constraints,
            required_evidence=envelope.required_evidence,
            tool_budget=envelope.tool_budget,
            verification_plan=envelope.verification_plan,
            rollback_command=envelope.rollback_command,
            max_retries=envelope.max_retries,
            files_in_scope=envelope.files_in_scope,
            created_at=time.time(),
            lease_expires_at=time.time() + DEFAULT_LEASE_TTL,
        )
        self.missions[mission.mission_id] = mission
        self._active = mission.mission_id
        self._save()
        return mission

    def get_active(self) -> Optional[Mission]:
        if self._active and self._active in self.missions:
            return self.missions[self._active]
        return None

    def get_pending(self) -> List[Mission]:
        return [
            m for m in self.missions.values()
            if m.status == MissionStatus.PENDING
        ]

    def complete(self, mission_id: str, evidence_bundle: Dict[str, Any]):
        if mission_id in self.missions:
            m = self.missions[mission_id]
            m.status = MissionStatus.COMPLETE
            m.completed_at = time.time()
            m.evidence_bundle = evidence_bundle
            self._active = None
            self._save()

    def fail(self, mission_id: str, error: str):
        if mission_id in self.missions:
            m = self.missions[mission_id]
            m.attempts += 1
            if m.attempts >= m.max_retries:
                m.status = MissionStatus.FAILED
                m.error = error
                m.completed_at = time.time()
                self._active = None
            else:
                m.status = MissionStatus.ACQUIRED
                m.lease_expires_at = time.time() + DEFAULT_LEASE_TTL
            self._save()

    def expire(self, mission_id: str):
        if mission_id in self.missions:
            m = self.missions[mission_id]
            m.status = MissionStatus.EXPIRED
            m.completed_at = time.time()
            self._active = None
            self._save()

    def is_lease_valid(self, mission_id: str) -> bool:
        if mission_id not in self.missions:
            return False
        m = self.missions[mission_id]
        if m.lease_expires_at is None:
            return True
        return time.time() < m.lease_expires_at

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.missions)
        by_status = {}
        for m in self.missions.values():
            key = m.status.value
            by_status[key] = by_status.get(key, 0) + 1
        return {
            "total_missions": total,
            "by_status": by_status,
            "active": self._active,
            "completed": by_status.get("complete", 0),
            "failed": by_status.get("failed", 0),
        }


class MissionExecutor:
    """
    Executes a mission by calling the ROXY streaming API.

    Calls /stream with the mission goal and captures:
    - Tool calls made
    - Files modified
    - Verification results
    - Final output
    """

    def __init__(self):
        self._auth_token = self._load_auth_token()

    def _load_auth_token(self) -> Optional[str]:
        try:
            if AUTH_TOKEN_FILE.exists():
                return AUTH_TOKEN_FILE.read_text().strip()
        except Exception:
            pass
        return None

    async def execute(self, mission: Mission) -> Dict[str, Any]:
        """
        Execute a mission by calling the ROXY streaming API.

        Returns:
            Dict with: success, tool_calls, files_modified, output, error
        """
        import requests

        goal = self._build_goal(mission)

        headers = {"Content-Type": "application/json"}
        if self._auth_token:
            headers["X-ROXY-Token"] = self._auth_token

        tool_calls = []
        files_modified = set()

        try:
            response = requests.post(
                f"{ROXY_BASE_URL}/stream",
                headers=headers,
                json={"command": goal},
                stream=True,
                timeout=DEFAULT_MISSION_TIMEOUT,
            )

            if response.status_code not in (200, 202):
                return {
                    "success": False,
                    "error": f"ROXY returned {response.status_code}: {response.text[:200]}",
                    "tool_calls": [],
                    "files_modified": [],
                    "output": "",
                }

            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    if line.startswith(b"data: "):
                        data = json.loads(line[6:])
                    else:
                        continue

                    event_type = data.get("event", "")
                    if event_type == "tool_execution_started":
                        tool_calls.append({
                            "type": "started",
                            "tool": data.get("tool_name"),
                            "call_id": data.get("call_id"),
                            "timestamp": time.time(),
                        })
                    elif event_type == "tool_execution_finished":
                        tool_calls.append({
                            "type": "finished",
                            "tool": data.get("tool_name"),
                            "success": data.get("success"),
                            "timestamp": time.time(),
                        })
                    elif event_type == "tool_execution_failed":
                        tool_calls.append({
                            "type": "failed",
                            "tool": data.get("tool_name"),
                            "error": data.get("error", ""),
                            "timestamp": time.time(),
                        })
                    elif event_type == "tool_retry_attempt":
                        tool_calls.append({
                            "type": "retry",
                            "tool": data.get("tool_name"),
                            "strategy": data.get("strategy"),
                            "attempt": data.get("attempt"),
                            "timestamp": time.time(),
                        })
                    elif event_type == "tool_retry_success":
                        tool_calls.append({
                            "type": "retry_recovered",
                            "tool": data.get("tool_name"),
                            "attempt": data.get("attempt"),
                            "timestamp": time.time(),
                        })

                    if event_type == "complete":
                        output = data.get("data", {}).get("response", "")

                except Exception:
                    continue

            return {
                "success": True,
                "tool_calls": tool_calls,
                "files_modified": list(files_modified),
                "output": output if "output" in dir() else "",
                "error": "",
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": f"Mission timed out after {DEFAULT_MISSION_TIMEOUT}s",
                "tool_calls": tool_calls,
                "files_modified": list(files_modified),
                "output": "",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tool_calls": tool_calls,
                "files_modified": list(files_modified),
                "output": "",
            }

    def _build_goal(self, mission: Mission) -> str:
        """Build the goal prompt for the mission."""
        goal = mission.goal

        if mission.files_in_scope:
            goal += f"\n\nFiles in scope: {', '.join(mission.files_in_scope)}"

        if mission.constraints:
            goal += "\n\nConstraints:"
            for c in mission.constraints:
                goal += f"\n  - {c}"

        if mission.verification_plan:
            goal += "\n\nVerification steps:"
            for i, step in enumerate(mission.verification_plan, 1):
                goal += f"\n  {i}. {step}"

        goal += "\n\nProvide detailed evidence of completion."

        return goal


_ledger: Optional[MissionLedger] = None
_executor: Optional[MissionExecutor] = None


def get_ledger() -> MissionLedger:
    global _ledger
    if _ledger is None:
        _ledger = MissionLedger()
    return _ledger


def get_executor() -> MissionExecutor:
    global _executor
    if _executor is None:
        _executor = MissionExecutor()
    return _executor


def create_mission_from_story(story) -> Optional[Mission]:
    """Create a mission from a story selector result."""
    try:
        from story_selector import StorySelector
        selector = StorySelector()
        envelope = selector.build_envelope(story)
        ledger = get_ledger()
        return ledger.create_mission(envelope)
    except Exception as e:
        logger.warning(f"Failed to create mission from story: {e}")
        return None


async def run_mission_task() -> str:
    """
    Mission execution task for the background scheduler.
    Called periodically by the scheduler.
    """
    ledger = get_ledger()
    executor = get_executor()

    if ledger.get_active():
        active = ledger.get_active()
        if ledger.is_lease_valid(active.mission_id):
            return f"Mission {active.mission_id} ({active.story_id}) still running"

        ledger.expire(active.mission_id)
        return f"Mission {active.mission_id} expired"

    try:
        from story_selector import StorySelector
        selector = StorySelector()
        next_story = selector.get_next_story()

        if not next_story:
            return "No eligible stories found"

        envelope = selector.build_envelope(next_story)
        mission = ledger.create_mission(envelope)

        logger.info(f"[Mission] Starting: {mission.story_id} - {mission.story_title}")

        mission.status = MissionStatus.RUNNING
        mission.started_at = time.time()
        ledger._save()

        result = await executor.execute(mission)

        if result["success"]:
            evidence_bundle = {
                "mission_id": mission.mission_id,
                "story_id": mission.story_id,
                "completed_at": time.time(),
                "duration": mission.completed_at - mission.started_at if mission.completed_at else 0,
                "tool_calls": result["tool_calls"],
                "files_modified": result["files_modified"],
                "output": result.get("output", "")[:1000],
                "verification_results": mission.verification_results,
            }

            ledger.complete(mission.mission_id, evidence_bundle)
            selector.mark_complete(next_story.id)

            logger.info(f"[Mission] Complete: {mission.story_id}")
            return f"Mission {mission.story_id} completed successfully"

        else:
            ledger.fail(mission.mission_id, result["error"])
            logger.warning(f"[Mission] Failed: {mission.story_id} - {result['error']}")
            return f"Mission {mission.story_id} failed: {result['error'][:200]}"

    except Exception as e:
        logger.error(f"[Mission] Error: {e}")
        return f"Mission error: {e}"


def create_mission_task():
    """Task factory for the background scheduler."""
    async def task():
        return await run_mission_task()
    return task
