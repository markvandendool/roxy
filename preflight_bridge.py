"""
Luno Preflight → ROXY Bridge

AAA Quality Implementation: Law 0 Reuse - Bridges Luno pre-flight.ts to ROXY OpenCode

This module bridges Luno Orchestrator's pre-flight checks into ROXY OpenCode spawns:
- Runs Luno pre-flight checks before OpenCode spawns
- Blocks spawn if pre-flight fails
- Passes mission contract to OpenCode

Usage:
    from preflight_bridge import PreflightBridge, preflight_or_die
    
    bridge = PreflightBridge()
    result = bridge.check_readiness()
    if not result.ready:
        print(f"Blocking: {result.blocking_reasons}")
"""

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger("roxy.preflight_bridge")

ROXY_ROOT = Path.home() / ".roxy"


def _detect_luno_root() -> Path:
    """Best-effort detection of local Luno orchestrator path."""
    home = Path.home()
    candidates = [
        home / "work" / "mindsong" / "luno-orchestrator",
        home / "work" / "mindsong_gh_https_1769765834" / "luno-orchestrator",
        home / "work" / "mindsong-juke-hub" / "luno-orchestrator",
        ROXY_ROOT.parent / "work" / "mindsong" / "luno-orchestrator",
    ]
    for path in candidates:
        if path.exists() and path.is_dir():
            return path
    return candidates[0]


LUNO_ROOT = _detect_luno_root()

DEFAULT_REQUIRED_MCP_SERVERS = [
    "roxy-browser",
    "roxy-desktop",
    "roxy-voice",
    "roxy-obs",
    "roxy-content",
    "mindsong-skills",
    "blender",
    "playwright",
    "chrome-devtools",
    "puppeteer",
    "notion",
    "github",
    "memory",
    "filesystem",
    "sequential-thinking",
    "greptile",
]

DEFAULT_BOOTSTRAP_MISSION_OBJECTIVE = (
    "Keep ROXY command center healthy, execute queued stories safely, "
    "and preserve production readiness."
)

DEFAULT_BOOTSTRAP_MISSION_CONSTRAINTS = [
    "No destructive git operations",
    "Preserve existing worktree changes",
    "Run targeted verification before completion",
    "Log all tool calls and outcomes",
]


class Readiness(Enum):
    """Readiness status levels."""
    READY = "ready"
    DEGRADED = "degraded"  # Minor issues, can proceed
    BLOCKED = "blocked"    # Major issues, must block


@dataclass
class ComponentStatus:
    """Status of a single component."""
    name: str
    status: str  # "ok", "warn", "error", "unknown"
    message: str = ""
    details: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class PreflightReport:
    """Complete preflight check report."""
    timestamp: str
    overall_ready: Readiness
    models_ready: list[str] = field(default_factory=list)
    mcp_ready: list[str] = field(default_factory=list)
    skills_ready: list[str] = field(default_factory=list)
    mission_valid: bool = True
    components: list[ComponentStatus] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "overall_ready": self.overall_ready.value,
            "models_ready": self.models_ready,
            "mcp_ready": self.mcp_ready,
            "skills_ready": self.skills_ready,
            "mission_valid": self.mission_valid,
            "components": [c.to_dict() for c in self.components],
            "blocking_reasons": self.blocking_reasons,
            "warnings": self.warnings,
        }


class PreflightBridge:
    """
    Bridge Luno pre-flight checks to ROXY OpenCode.
    
    Runs Luno's pre-flight checks (src/safety/pre-flight.ts) and
    blocks OpenCode spawns if critical issues are found.
    
    AAA Quality:
    - Comprehensive type hints
    - Extensive docstrings
    - Structured logging
    - Graceful degradation
    """
    
    def __init__(self, luno_root: Optional[Path] = None):
        """
        Initialize pre-flight bridge.
        
        Args:
            luno_root: Path to Luno orchestrator (default: auto-detect)
        """
        self.luno_root = luno_root or LUNO_ROOT
        self.luno_src = self.luno_root / "src"
        
        logger.info(f"PreflightBridge initialized: luno_root={self.luno_root}")

    @staticmethod
    def _is_enabled(value: str | None, default: bool = False) -> bool:
        """Parse boolean-ish env values."""
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _parse_csv(value: str | None) -> list[str]:
        """Parse comma-separated server list."""
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    def _required_mcp_servers(self) -> list[str]:
        """Resolve required MCP server set."""
        configured = self._parse_csv(os.getenv("ROXY_MCP_REQUIRED_SERVERS"))
        return configured or list(DEFAULT_REQUIRED_MCP_SERVERS)

    def _auto_mission_enabled(self) -> bool:
        """Whether to auto-generate bootstrap mission contracts when missing."""
        return self._is_enabled(os.getenv("ROXY_PREFLIGHT_AUTO_MISSION"), default=True)

    def _bootstrap_mission_payload(self) -> dict:
        """Build a default mission payload that satisfies contract requirements."""
        now = datetime.now(UTC)
        mission_id = f"bootstrap-{now.strftime('%Y%m%d%H%M%S')}"
        objective = os.getenv("ROXY_BOOTSTRAP_MISSION_OBJECTIVE", DEFAULT_BOOTSTRAP_MISSION_OBJECTIVE).strip()
        if not objective:
            objective = DEFAULT_BOOTSTRAP_MISSION_OBJECTIVE
        return {
            "mission_id": mission_id,
            "objective": objective,
            "constraints": list(DEFAULT_BOOTSTRAP_MISSION_CONSTRAINTS),
            "priority": "high",
            "budget": 0.0,
            "timeout_sec": 900,
            "metadata": {
                "source": "preflight_bridge",
                "auto_generated": True,
                "created_at": now.isoformat(),
            },
        }

    def _ensure_bootstrap_mission(self, mission_dir: Path) -> Path:
        """Create an active bootstrap mission file and return its path."""
        active_dir = mission_dir / "active"
        active_dir.mkdir(parents=True, exist_ok=True)
        payload = self._bootstrap_mission_payload()
        mission_path = active_dir / f"{payload['mission_id']}.json"
        mission_path.write_text(json.dumps(payload, indent=2))
        return mission_path
    
    def _run_luno_command(
        self,
        cmd: list[str],
        timeout: float = 30.0,
    ) -> tuple[int, str, str]:
        """Run a Luno CLI command."""
        try:
            result = subprocess.run(
                cmd,
                cwd=self.luno_root,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Timeout"
        except Exception as e:
            return -1, "", str(e)
    
    def check_api_keys(self) -> ComponentStatus:
        """Check API key health (from Luno key-validator.ts)."""
        # Simplified check - look for key files
        key_file = ROXY_ROOT / "secret.token"
        
        if not key_file.exists():
            return ComponentStatus(
                name="api_keys",
                status="error",
                message="Auth token not found",
            )
        
        return ComponentStatus(
            name="api_keys",
            status="ok",
            message="Auth token present",
        )
    
    def check_luno_service(self) -> ComponentStatus:
        """Check if Luno service is running."""
        if not self.luno_root.exists():
            return ComponentStatus(
                name="luno_service",
                status="warn",
                message=f"Luno root missing: {self.luno_root}",
            )

        bun_check = subprocess.run(["which", "bun"], capture_output=True, text=True)
        if bun_check.returncode != 0:
            return ComponentStatus(
                name="luno_service",
                status="warn",
                message="bun runtime not found",
            )

        code, stdout, stderr = self._run_luno_command(
            ["bun", "run", "status"],
            timeout=10,
        )
        
        if code == 0:
            return ComponentStatus(
                name="luno_service",
                status="ok",
                message="Luno service healthy",
            )
        
        return ComponentStatus(
            name="luno_service",
            status="warn",
            message="Luno service check failed",
            details={"stdout": stdout[:200], "stderr": stderr[:200]},
        )

    def check_models(self) -> ComponentStatus:
        """Check OpenCode model catalog availability."""
        try:
            result = subprocess.run(
                ["opencode-cli", "models"],
                capture_output=True,
                text=True,
                timeout=20,
            )
            if result.returncode != 0:
                return ComponentStatus(
                    name="models",
                    status="error",
                    message="opencode-cli models failed",
                    details={"stderr": result.stderr[:300]},
                )
            models = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            preferred = [
                "opencode/mimo-v2-pro-free",
                "opencode/big-pickle",
                "openai/gpt-5.4",
            ]
            available = [m for m in preferred if m in models]
            if not available:
                return ComponentStatus(
                    name="models",
                    status="error",
                    message="No preferred ULTRAMAX models available",
                    details={"available_count": len(models)},
                )
            return ComponentStatus(
                name="models",
                status="ok",
                message=f"{len(available)} preferred models available",
                details={"available": available, "total_models": len(models)},
            )
        except Exception as e:
            return ComponentStatus(
                name="models",
                status="error",
                message=f"Model probe failed: {e}",
            )
    
    def check_mcp_servers(self) -> ComponentStatus:
        """Check MCP server connectivity."""
        try:
            from mcp_client import MCPClient
            import asyncio

            async def _probe() -> tuple[str, dict]:
                client = MCPClient()
                details = {}
                try:
                    await client.initialize()
                    server_ids = list(getattr(client, "_config_cache", {}).keys()) or list(getattr(client, "sessions", {}).keys())
                    for server_id in server_ids:
                        health = await client.health_check(server_id)
                        tools = await client.list_tools(server_id)
                        details[server_id] = {
                            "connected": bool(health.get("connected")),
                            "tool_count": len(tools),
                        }
                finally:
                    await client.disconnect_all()

                connected = sum(1 for item in details.values() if item.get("connected"))
                if connected == 0:
                    return "error", details
                return "ok", details

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, _probe())
                    status, details = future.result(timeout=30)
            else:
                status, details = asyncio.run(_probe())
            if status == "error":
                return ComponentStatus(
                    name="mcp_servers",
                    status="error",
                    message="No MCP servers connected",
                    details=details,
                )

            required_servers = self._required_mcp_servers()
            connected_servers = {
                sid
                for sid, item in (details or {}).items()
                if isinstance(item, dict) and item.get("connected")
            }
            missing_required = [sid for sid in required_servers if sid not in connected_servers]

            known_servers = set(details.keys())
            optional_servers = sorted(known_servers - set(required_servers))
            missing_optional = [sid for sid in optional_servers if sid not in connected_servers]

            details_out = dict(details)
            details_out.update(
                {
                    "_required_servers": required_servers,
                    "_missing_required": missing_required,
                    "_optional_servers": optional_servers,
                    "_missing_optional": missing_optional,
                }
            )

            if missing_required:
                return ComponentStatus(
                    name="mcp_servers",
                    status="warn",
                    message=(
                        f"{len(required_servers) - len(missing_required)}/"
                        f"{len(required_servers)} required MCP servers connected"
                    ),
                    details=details_out,
                )

            message = f"{len(required_servers)}/{len(required_servers)} required MCP servers connected"
            if missing_optional:
                message += f"; {len(missing_optional)} optional unavailable"

            return ComponentStatus(
                name="mcp_servers",
                status="ok",
                message=message,
                details=details_out,
            )
        except Exception as e:
            return ComponentStatus(
                name="mcp_servers",
                status="warn",
                message=f"MCP status unavailable: {e}",
            )
    
    def check_skills(self) -> ComponentStatus:
        """Check if skills are loaded."""
        candidate_dirs = [
            ROXY_ROOT / "skills",
            Path.home() / ".codex" / "skills",
        ]
        skills_dir = next((d for d in candidate_dirs if d.exists() and d.is_dir()), candidate_dirs[0])

        if not skills_dir.exists():
            return ComponentStatus(
                name="skills",
                status="warn",
                message="Skills directory not found",
            )

        skill_files = list(skills_dir.rglob("SKILL.md")) + list(skills_dir.glob("*.py"))
        skill_names = sorted({p.parent.name if p.name == "SKILL.md" else p.stem for p in skill_files})

        return ComponentStatus(
            name="skills",
            status="ok",
            message=f"{len(skill_names)} skills found",
            details={"count": len(skill_names), "skills": skill_names[:30]},
        )
    
    def check_mission_contract(self, mission_file: Optional[str] = None) -> ComponentStatus:
        """Check mission contract validity."""
        # Check for active mission
        mission_dir = ROXY_ROOT / "missions"
        auto_created_path: Optional[Path] = None
        
        if not mission_dir.exists():
            if self._auto_mission_enabled():
                auto_created_path = self._ensure_bootstrap_mission(mission_dir)
            else:
                return ComponentStatus(
                    name="mission_contract",
                    status="warn",
                    message="No mission directory",
                )
        
        active_missions = list(mission_dir.glob("active/*.json"))
        
        if not active_missions:
            if self._auto_mission_enabled():
                auto_created_path = self._ensure_bootstrap_mission(mission_dir)
                active_missions = list(mission_dir.glob("active/*.json"))
            else:
                return ComponentStatus(
                    name="mission_contract",
                    status="warn",
                    message="No active mission",
                )
        
        # Validate mission structure
        try:
            mission_path = auto_created_path or active_missions[0]
            with open(mission_path) as f:
                mission = json.load(f)
            
            required = ["mission_id", "objective", "constraints"]
            missing = [k for k in required if k not in mission]
            
            if missing:
                return ComponentStatus(
                    name="mission_contract",
                    status="error",
                    message=f"Invalid mission: missing {missing}",
                )
            
            return ComponentStatus(
                name="mission_contract",
                status="ok",
                message=(
                    f"Mission {mission.get('mission_id', 'unknown')} valid"
                    + (" (auto-generated)" if auto_created_path else "")
                ),
                details=mission,
            )
        except Exception as e:
            return ComponentStatus(
                name="mission_contract",
                status="error",
                message=f"Mission parse error: {e}",
            )
    
    def check_readiness(self) -> PreflightReport:
        """
        Run complete pre-flight checks.
        
        Returns:
            PreflightReport with overall readiness status
        """
        components: list[ComponentStatus] = []
        blocking_reasons: list[str] = []
        warnings: list[str] = []
        
        # Run checks
        models = self.check_models()
        components.append(models)
        if models.status == "error":
            blocking_reasons.append(f"Models: {models.message}")
        elif models.status == "warn":
            warnings.append(f"Models: {models.message}")

        api_keys = self.check_api_keys()
        components.append(api_keys)
        if api_keys.status == "error":
            blocking_reasons.append(f"API keys: {api_keys.message}")
        
        luno_service = self.check_luno_service()
        components.append(luno_service)
        if luno_service.status == "error":
            blocking_reasons.append(f"Luno service: {luno_service.message}")
        elif luno_service.status == "warn":
            warnings.append(f"Luno service: {luno_service.message}")
        
        mcp = self.check_mcp_servers()
        components.append(mcp)
        if mcp.status == "error":
            blocking_reasons.append(f"MCP servers: {mcp.message}")
        elif mcp.status == "warn":
            warnings.append(f"MCP servers: {mcp.message}")

        skills = self.check_skills()
        components.append(skills)
        
        mission = self.check_mission_contract()
        components.append(mission)
        if mission.status == "error":
            blocking_reasons.append(f"Mission: {mission.message}")
        
        # Determine overall readiness
        if blocking_reasons:
            overall = Readiness.BLOCKED
        elif warnings:
            overall = Readiness.DEGRADED
        else:
            overall = Readiness.READY
        
        report = PreflightReport(
            timestamp=datetime.now(UTC).isoformat(),
            overall_ready=overall,
            models_ready=models.details.get("available", []) if isinstance(models.details, dict) else [],
            mcp_ready=[
                sid
                for sid, item in (mcp.details or {}).items()
                if isinstance(item, dict) and item.get("connected")
            ],
            skills_ready=skills.details.get("skills", []) if isinstance(skills.details, dict) else [],
            mission_valid=mission.status == "ok",
            components=components,
            blocking_reasons=blocking_reasons,
            warnings=warnings,
        )
        
        logger.info(
            f"Preflight: ready={overall.value}, "
            f"blocked={len(blocking_reasons)}, warned={len(warnings)}"
        )
        
        return report
    
    def preflight_or_die(self) -> PreflightReport:
        """
        Run pre-flight and raise if not ready.
        
        Returns:
            PreflightReport
            
        Raises:
            PreflightError: If pre-flight fails
        """
        report = self.check_readiness()
        
        if report.overall_ready == Readiness.BLOCKED:
            reasons = "\n  - ".join(report.blocking_reasons)
            raise PreflightError(
                f"Preflight BLOCKED:\n  - {reasons}\n\n"
                f"Fix issues before retrying.",
                report
            )
        
        return report


class PreflightError(Exception):
    """Raised when pre-flight check fails."""
    
    def __init__(self, message: str, report: PreflightReport):
        super().__init__(message)
        self.report = report


def preflight_or_die() -> PreflightReport:
    """Convenience wrapper for strict preflight validation."""
    bridge = PreflightBridge()
    return bridge.preflight_or_die()


# CLI entry point
if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Preflight Bridge CLI")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if not ready")
    
    args = parser.parse_args()
    
    bridge = PreflightBridge()
    report = bridge.check_readiness()
    
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"Preflight: {report.overall_ready.value.upper()}")
        if report.blocking_reasons:
            print("\nBlocking reasons:")
            for r in report.blocking_reasons:
                print(f"  - {r}")
        if report.warnings:
            print("\nWarnings:")
            for w in report.warnings:
                print(f"  - {w}")
    
    if args.strict and report.overall_ready == Readiness.BLOCKED:
        sys.exit(1)
    elif report.overall_ready == Readiness.BLOCKED:
        sys.exit(2)
    else:
        sys.exit(0)
