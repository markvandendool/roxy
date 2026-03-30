"""
Mission Contract Bridge

AAA Quality Implementation: Law 0 Reuse - Bridges Luno mission schema to ROXY OpenCode

This module bridges Luno Orchestrator's mission contract schema to ROXY OpenCode:
- Loads mission contracts from Luno
- Injects typed mission context into OpenCode spawns
- Validates mission contract compliance

Usage:
    from mission_contract import MissionContract, inject_context
    
    contract = MissionContract()
    context = contract.get_opencode_context()
    print(context)  # Ready for OpenCode spawn
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

logger = logging.getLogger("roxy.mission_contract")

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


@dataclass
class MissionRequest:
    """Luno MissionRequest schema (from execution-spec.schema.ts)."""
    mission_id: str
    objective: str
    constraints: list[str] = field(default_factory=list)
    priority: str = "normal"
    budget: float = 0.0
    timeout_sec: int = 300
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "objective": self.objective,
            "constraints": self.constraints,
            "priority": self.priority,
            "budget": self.budget,
            "timeout_sec": self.timeout_sec,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MissionRequest":
        return cls(
            mission_id=data.get("mission_id", "unknown"),
            objective=data.get("objective", ""),
            constraints=data.get("constraints", []),
            priority=data.get("priority", "normal"),
            budget=data.get("budget", 0.0),
            timeout_sec=data.get("timeout_sec", 300),
            metadata=data.get("metadata", {}),
        )


@dataclass
class MissionResult:
    """Luno MissionResult schema."""
    status: str  # "success", "failure", "partial"
    artifacts: list[str] = field(default_factory=list)
    confidence: float = 0.0
    trace_id: str = ""
    verification: str = "unverified"
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "artifacts": self.artifacts,
            "confidence": self.confidence,
            "trace_id": self.trace_id,
            "verification": self.verification,
            "metadata": self.metadata,
        }


class MissionContract:
    """
    Mission contract bridge for ROXY ↔ Luno integration.
    
    Bridges Luno's mission contract schema (mission_id, objective,
    constraints, etc.) to ROXY OpenCode context.
    
    AAA Quality:
    - Comprehensive type hints
    - Extensive docstrings
    - Structured logging
    - Graceful degradation
    """
    
    def __init__(self, luno_root: Optional[Path] = None):
        """
        Initialize mission contract bridge.
        
        Args:
            luno_root: Path to Luno orchestrator
        """
        self.luno_root = luno_root or LUNO_ROOT
        self.luno_src = self.luno_root / "src"
        self.mission_dir = ROXY_ROOT / "missions"
        self.mission_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"MissionContract initialized: luno_root={self.luno_root}")
    
    def get_active_mission(self) -> Optional[MissionRequest]:
        """
        Get the currently active mission.
        
        Returns:
            MissionRequest if found, None otherwise
        """
        # Check for active mission file
        active_dir = self.mission_dir / "active"
        active_dir.mkdir(exist_ok=True)
        
        active_files = list(active_dir.glob("*.json"))
        
        if not active_files:
            return None
        
        try:
            with open(active_files[0]) as f:
                data = json.load(f)
            
            return MissionRequest.from_dict(data)
        except Exception as e:
            logger.warning(f"Could not load mission: {e}")
            return None
    
    def get_opencode_context(
        self,
        mission: Optional[MissionRequest] = None,
        include_objective: bool = True,
        include_constraints: bool = True,
        include_priority: bool = True,
        max_chars: int = 2000,
    ) -> str:
        """
        Generate OpenCode context from mission contract.
        
        Args:
            mission: Mission to use (default: active mission)
            include_objective: Include objective section
            include_constraints: Include constraints section
            include_priority: Include priority section
            max_chars: Maximum context length
            
        Returns:
            Context string for OpenCode
        """
        if mission is None:
            mission = self.get_active_mission()
        
        if mission is None:
            return ""
        
        sections: list[str] = []
        remaining = max_chars
        
        if include_objective and remaining > 100:
            objective_text = f"""
## Mission Objective
**ID:** {mission.mission_id}
**Task:** {mission.objective}
"""
            sections.append(objective_text)
            remaining -= len(objective_text)
        
        if include_constraints and remaining > 100 and mission.constraints:
            constraints_text = f"""
## Constraints
"""
            for i, constraint in enumerate(mission.constraints[:10]):  # Limit to 10
                constraints_text += f"- {constraint}\n"
            sections.append(constraints_text)
            remaining -= len(constraints_text)
        
        if include_priority and remaining > 50:
            priority_text = f"""
## Priority
- **Level:** {mission.priority}
- **Budget:** ${mission.budget:.2f}
- **Timeout:** {mission.timeout_sec}s
"""
            sections.append(priority_text)
        
        context = "\n".join(sections)
        
        if len(context) > max_chars:
            context = context[:max_chars] + "\n\n[Context truncated...]"
        
        logger.info(
            f"Mission context: mission_id={mission.mission_id}, "
            f"chars={len(context)}"
        )
        
        return context
    
    def create_mission_result(
        self,
        mission: MissionRequest,
        status: str,
        artifacts: list[str],
        confidence: float = 0.8,
        trace_id: str = "",
    ) -> MissionResult:
        """
        Create a mission result following the schema.
        
        Args:
            mission: Original mission
            status: Result status
            artifacts: List of output artifacts
            confidence: Confidence score
            trace_id: Trace identifier
            
        Returns:
            MissionResult
        """
        result = MissionResult(
            status=status,
            artifacts=artifacts,
            confidence=confidence,
            trace_id=trace_id or f"trace-{mission.mission_id}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            verification="pending",
            metadata={
                "mission_id": mission.mission_id,
                "original_objective": mission.objective,
                "priority": mission.priority,
            },
        )
        
        # Save result
        self._save_result(result)
        
        return result
    
    def _save_result(self, result: MissionResult) -> Path:
        """Save mission result to file."""
        results_dir = self.mission_dir / "results"
        results_dir.mkdir(exist_ok=True)
        
        filename = f"{result.trace_id}.json"
        result_file = results_dir / filename
        
        with open(result_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        
        logger.info(f"Saved mission result: {result_file}")
        
        return result_file
    
    def validate_schema(self, data: dict) -> tuple[bool, str]:
        """
        Validate mission data against schema.
        
        Args:
            data: Data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ["mission_id", "objective"]
        
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Validate types
        if not isinstance(data.get("mission_id"), str):
            return False, "mission_id must be a string"
        if not isinstance(data.get("objective"), str):
            return False, "objective must be a string"

        if "constraints" in data and not isinstance(data["constraints"], list):
            return False, "constraints must be a list"
        if "priority" in data and not isinstance(data["priority"], str):
            return False, "priority must be a string"
        if "timeout_sec" in data and not isinstance(data["timeout_sec"], int):
            return False, "timeout_sec must be an int"
        if "budget" in data and not isinstance(data["budget"], (int, float)):
            return False, "budget must be a number"
        
        return True, "ok"
    
    def inject_to_opencode_prompt(
        self,
        base_prompt: str,
        mission: Optional[MissionRequest] = None,
    ) -> str:
        """
        Inject mission contract into OpenCode prompt.
        
        Args:
            base_prompt: Original prompt
            mission: Mission to inject
            
        Returns:
            Enhanced prompt with mission context
        """
        context = self.get_opencode_context(mission)
        
        if not context:
            return base_prompt
        
        enhanced = f"""{context}

---

## Your Task
{base_prompt}

---

**Important:** Complete the task within the constraints above.
"""
        
        return enhanced


# Singleton
_contract: Optional[MissionContract] = None


def get_contract() -> MissionContract:
    """Get singleton mission contract."""
    global _contract
    if _contract is None:
        _contract = MissionContract()
    return _contract


def get_mission() -> Optional[MissionRequest]:
    """Get active mission."""
    return get_contract().get_active_mission()


def inject_context(prompt: str, mission: Optional[MissionRequest] = None) -> str:
    """Inject mission context into prompt."""
    return get_contract().inject_to_opencode_prompt(prompt, mission)


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Mission Contract CLI")
    parser.add_argument("--context", action="store_true", help="Show mission context")
    parser.add_argument("--mission", help="Load mission from file")
    parser.add_argument("--validate", help="Validate mission JSON")
    
    args = parser.parse_args()
    
    contract = MissionContract()
    
    if args.validate:
        try:
            with open(args.validate) as f:
                data = json.load(f)
            valid, msg = contract.validate_schema(data)
            print(f"Valid: {valid}, {msg}")
        except Exception as e:
            print(f"Error: {e}")
    
    if args.context:
        context = contract.get_opencode_context()
        if context:
            print(context)
        else:
            print("No active mission")
    
    if not (args.context or args.validate):
        parser.print_help()
