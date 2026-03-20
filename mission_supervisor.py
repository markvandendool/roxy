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
import re
import shlex
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

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
LEASE_TOUCH_INTERVAL = 30.0
VERIFICATION_COMMAND_PREFIXES = ("cmd:", "bash:", "shell:")
VERIFICATION_COMMAND_STARTERS = (
    "bun ", "npm ", "pnpm ", "pytest ", "python ", "python3 ", "node ",
    "npx ", "tsx ", "vitest ", "playwright ", "./", "bash ", "git ",
)


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
            "files_in_scope": self.files_in_scope,
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
            files_in_scope=data.get("files_in_scope", []),
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

    def _write_evidence_artifact(self, mission: Mission, payload: Dict[str, Any]) -> str:
        artifact_path = EVIDENCE_DIR / f"{mission.mission_id}.json"
        try:
            with open(artifact_path, "w") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write mission evidence artifact {artifact_path}: {e}")
        return str(artifact_path)

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
            artifact_path = self._write_evidence_artifact(
                m,
                {
                    "mission": m.to_dict(),
                    "evidence_bundle": evidence_bundle,
                    "written_at": datetime.now().isoformat(),
                },
            )
            m.evidence_bundle = {**evidence_bundle, "artifact_path": artifact_path}
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
                artifact_path = self._write_evidence_artifact(
                    m,
                    {
                        "mission": m.to_dict(),
                        "error": error,
                        "written_at": datetime.now().isoformat(),
                    },
                )
                m.evidence_bundle = {**m.evidence_bundle, "artifact_path": artifact_path}
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
            artifact_path = self._write_evidence_artifact(
                m,
                {
                    "mission": m.to_dict(),
                    "reason": "lease_expired",
                    "written_at": datetime.now().isoformat(),
                },
            )
            m.evidence_bundle = {**m.evidence_bundle, "artifact_path": artifact_path}
            self._active = None
            self._save()

    def touch_lease(self, mission_id: str, ttl_seconds: float = DEFAULT_LEASE_TTL):
        if mission_id in self.missions:
            mission = self.missions[mission_id]
            mission.lease_expires_at = time.time() + max(ttl_seconds, DEFAULT_LEASE_TTL)
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
        self._package_json_cache: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _extract_file_targets(tool_name: str, arguments: Dict[str, Any]) -> List[str]:
        file_keys = ("file_path", "path", "target_path", "source_path", "destination", "output")
        files = []
        for key in file_keys:
            value = arguments.get(key)
            if isinstance(value, str) and value.strip():
                files.append(value.strip())
        if tool_name == "bash":
            command = str(arguments.get("command", "") or "")
            for match in re.findall(r"([A-Za-z0-9_./-]+\.(?:py|ts|tsx|js|jsx|json|md|sh|ya?ml|toml|css|scss|html|go|rs))", command):
                if match not in files:
                    files.append(match)
        return files[:8]

    @staticmethod
    def _normalize_repo_relative_path(path_value: str, repo_root: Path) -> Optional[str]:
        if not path_value:
            return None
        candidate = Path(str(path_value).strip()).expanduser()
        try:
            if candidate.is_absolute():
                return str(candidate.resolve().relative_to(repo_root))
            return str(candidate).lstrip("./")
        except Exception:
            return str(candidate).lstrip("./")

    def _load_package_json(self, package_root: Path) -> Dict[str, Any]:
        cache_key = str(package_root.resolve())
        if cache_key in self._package_json_cache:
            return self._package_json_cache[cache_key]
        package_json_path = package_root / "package.json"
        try:
            data = json.loads(package_json_path.read_text())
        except Exception:
            data = {}
        self._package_json_cache[cache_key] = data
        return data

    def _find_package_root(self, file_path: str, repo_root: Path) -> Optional[Path]:
        candidate = (repo_root / file_path).resolve()
        search_root = candidate.parent if candidate.suffix else candidate
        for directory in [search_root, *search_root.parents]:
            if directory == directory.parent and directory != repo_root:
                break
            if (directory / "package.json").exists():
                return directory
            if directory == repo_root:
                break
        if (repo_root / "package.json").exists():
            return repo_root
        return None

    @staticmethod
    def _looks_like_command(step: str) -> bool:
        lowered = step.strip().lower()
        if any(lowered.startswith(prefix) for prefix in VERIFICATION_COMMAND_PREFIXES):
            return True
        return any(lowered.startswith(starter) for starter in VERIFICATION_COMMAND_STARTERS)

    def _extract_explicit_verification_commands(self, mission: Mission) -> List[Dict[str, Any]]:
        commands: List[Dict[str, Any]] = []
        for step in mission.verification_plan:
            raw_step = str(step or "").strip()
            if not raw_step:
                continue
            lowered = raw_step.lower()
            command = ""
            for prefix in VERIFICATION_COMMAND_PREFIXES:
                if lowered.startswith(prefix):
                    command = raw_step[len(prefix):].strip()
                    break
            if not command and self._looks_like_command(raw_step):
                command = raw_step
            if command:
                commands.append({
                    "source": "verification_plan",
                    "label": raw_step,
                    "command": command,
                })
        return commands

    def _derive_auto_verification_commands(self, mission: Mission, files_modified: List[str]) -> List[Dict[str, Any]]:
        repo_root = Path(os.getenv("ROXY_REPO_ROOT", "/home/mark/work/mindsong_gh_https_1769765834")).expanduser()
        if not repo_root.exists():
            return []

        try:
            from repo_intel import get_file_context
        except Exception:
            return []

        candidate_files = []
        seen_files = set()
        for path_value in [*files_modified, *mission.files_in_scope]:
            normalized = self._normalize_repo_relative_path(path_value, repo_root)
            if normalized and normalized not in seen_files:
                seen_files.add(normalized)
                candidate_files.append(normalized)

        python_tests = []
        package_tests: Dict[str, Dict[str, Any]] = {}
        package_typechecks: Dict[str, Dict[str, Any]] = {}

        for file_path in candidate_files:
            context = get_file_context(file_path, repo_root=repo_root) or {}
            tests = context.get("tests", []) or []
            package_root = self._find_package_root(file_path, repo_root)
            package_json = self._load_package_json(package_root) if package_root else {}
            scripts = package_json.get("scripts", {}) if isinstance(package_json, dict) else {}

            if package_root and any(file_path.endswith(ext) for ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")):
                package_key = str(package_root)
                rel_file_path = str(Path(file_path))
                if "typecheck" in scripts:
                    package_typechecks[package_key] = {
                        "source": "repo_intel",
                        "label": f"typecheck:{package_root.name or 'repo'}",
                        "command": "bun run typecheck",
                        "cwd": str(package_root),
                    }

                for test_path in tests:
                    rel_test_path = self._normalize_repo_relative_path(test_path, repo_root)
                    if not rel_test_path:
                        continue
                    entry = package_tests.setdefault(package_key, {
                        "package_root": package_root,
                        "tests": [],
                        "scripts": scripts,
                    })
                    if rel_test_path not in entry["tests"]:
                        entry["tests"].append(rel_test_path)
            elif any(test.endswith(".py") for test in tests):
                for test_path in tests:
                    rel_test_path = self._normalize_repo_relative_path(test_path, repo_root)
                    if rel_test_path and rel_test_path not in python_tests:
                        python_tests.append(rel_test_path)

        commands: List[Dict[str, Any]] = list(package_typechecks.values())

        for package_key, entry in package_tests.items():
            package_root = entry["package_root"]
            tests = entry["tests"]
            scripts = entry["scripts"]
            if not tests:
                continue
            quoted_tests = " ".join(shlex.quote(test) for test in tests[:8])
            if "test:unit" in scripts:
                command = f"bun run test:unit -- {quoted_tests}"
            elif "test" in scripts:
                command = f"bun run test -- {quoted_tests}"
            else:
                command = f"bun test {quoted_tests}"
            commands.append({
                "source": "repo_intel",
                "label": f"tests:{package_root.name or 'repo'}",
                "command": command,
                "cwd": str(package_root),
            })

        if python_tests:
            commands.append({
                "source": "repo_intel",
                "label": "pytest:auto",
                "command": "pytest -q " + " ".join(shlex.quote(test) for test in python_tests[:8]),
                "cwd": str(repo_root),
            })

        deduped = []
        seen = set()
        for item in commands:
            key = (item.get("cwd"), item.get("command"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    async def _run_verification_command(
        self,
        command: str,
        cwd: str,
        label: str,
        source: str,
    ) -> Dict[str, Any]:
        started = time.time()
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return {
            "label": label,
            "source": source,
            "command": command,
            "cwd": cwd,
            "success": process.returncode == 0,
            "exit_code": process.returncode,
            "duration": round(time.time() - started, 3),
            "stdout": (stdout or b"").decode("utf-8", errors="replace")[:4000],
            "stderr": (stderr or b"").decode("utf-8", errors="replace")[:4000],
        }

    async def execute_verification(self, mission: Mission, files_modified: List[str]) -> List[Dict[str, Any]]:
        commands = self._extract_explicit_verification_commands(mission)
        commands.extend(self._derive_auto_verification_commands(mission, files_modified))
        if not commands:
            return [{
                "label": "verification:none",
                "source": "none",
                "command": "",
                "cwd": "",
                "success": True,
                "exit_code": 0,
                "duration": 0.0,
                "stdout": "",
                "stderr": "",
                "skipped": "no_executable_verification_commands",
            }]

        results = []
        for step in commands:
            cwd = step.get("cwd") or str(Path(os.getenv("ROXY_REPO_ROOT", "/home/mark/work/mindsong_gh_https_1769765834")).expanduser())
            result = await self._run_verification_command(
                step["command"],
                cwd=cwd,
                label=step.get("label", step["command"]),
                source=step.get("source", "verification"),
            )
            results.append(result)
            if not result["success"]:
                break
        return results

    def _load_auth_token(self) -> Optional[str]:
        try:
            if AUTH_TOKEN_FILE.exists():
                return AUTH_TOKEN_FILE.read_text().strip()
        except Exception:
            pass
        return None

    async def execute(
        self,
        mission: Mission,
        lease_touch: Optional[Callable[[float], None]] = None,
    ) -> Dict[str, Any]:
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
        output = ""
        last_touch = time.time()

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
                    if lease_touch and (time.time() - last_touch) >= LEASE_TOUCH_INTERVAL:
                        lease_touch(max(DEFAULT_MISSION_TIMEOUT + 60, DEFAULT_LEASE_TTL))
                        last_touch = time.time()
                    if line.startswith(b"data: "):
                        data = json.loads(line[6:])
                    else:
                        continue

                    event_type = data.get("event", "")
                    if event_type == "tool_call_detected":
                        tool_name = data.get("tool_name")
                        arguments = data.get("arguments", {}) or {}
                        tool_calls.append({
                            "type": "detected",
                            "tool": tool_name,
                            "arguments": arguments,
                            "call_id": data.get("call_id"),
                            "timestamp": time.time(),
                        })
                        for target in self._extract_file_targets(str(tool_name or ""), arguments):
                            files_modified.add(target)
                    elif event_type == "tool_execution_started":
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
                    elif event_type == "tool_retry_exhausted":
                        tool_calls.append({
                            "type": "retry_exhausted",
                            "tool": data.get("tool_name"),
                            "error": data.get("error", ""),
                            "timestamp": time.time(),
                        })

                    if event_type == "complete":
                        output = data.get("data", {}).get("response", "")
                    if lease_touch:
                        lease_touch(max(DEFAULT_MISSION_TIMEOUT + 60, DEFAULT_LEASE_TTL))
                        last_touch = time.time()

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
        mission.lease_expires_at = time.time() + max(DEFAULT_MISSION_TIMEOUT + 60, DEFAULT_LEASE_TTL)
        ledger._save()

        result = await executor.execute(
            mission,
            lease_touch=lambda ttl: ledger.touch_lease(mission.mission_id, ttl_seconds=ttl),
        )

        if result["success"]:
            mission.status = MissionStatus.VERIFYING
            mission.tool_calls = result["tool_calls"]
            mission.files_modified = result["files_modified"]
            ledger.touch_lease(mission.mission_id, ttl_seconds=120)
            ledger._save()

            verification_results = await executor.execute_verification(
                mission,
                result["files_modified"],
            )
            mission.verification_results = verification_results
            verification_failed = any(not step.get("success", False) for step in verification_results)
            if verification_failed:
                failure_summary = next(
                    (
                        f"{step.get('label')}: {step.get('stderr') or step.get('stdout') or 'verification failed'}"
                        for step in verification_results
                        if not step.get("success", False)
                    ),
                    "verification_failed",
                )
                ledger.fail(mission.mission_id, failure_summary[:500])
                logger.warning(f"[Mission] Verification failed: {mission.story_id} - {failure_summary[:200]}")
                return f"Mission {mission.story_id} verification failed: {failure_summary[:200]}"

            completed_at = time.time()
            evidence_bundle = {
                "mission_id": mission.mission_id,
                "story_id": mission.story_id,
                "story_title": mission.story_title,
                "completed_at": completed_at,
                "duration": max(0.0, completed_at - (mission.started_at or completed_at)),
                "tool_calls": result["tool_calls"],
                "files_modified": result["files_modified"],
                "files_in_scope": mission.files_in_scope,
                "output": result.get("output", "")[:1000],
                "verification_results": mission.verification_results,
                "verification_plan": mission.verification_plan,
                "required_evidence": mission.required_evidence,
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
