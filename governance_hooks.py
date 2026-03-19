#!/usr/bin/env python3
"""
Governance Hooks - PreToolUse/PostToolUse for approval and audit
Part of ROXY-AUTONOMOUS-CODING-AGENT-V1 (RCA-007)

Provides typed governance hooks for tool execution safety.
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("roxy.governance")


class ApprovalLevel(Enum):
    AUTO = "auto"
    APPROVED = "approved"
    DENIED = "denied"


class SafetyLevel(Enum):
    SAFE = "safe"
    GUARDED = "guarded"
    DANGEROUS = "dangerous"


@dataclass
class ToolContext:
    tool_name: str
    arguments: Dict[str, Any]
    source: str = "model"
    safety_level: str = "safe"
    workdir: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class GovernanceDecision:
    allowed: bool
    reason: str
    approval_level: ApprovalLevel
    timestamp: float
    tool_name: str
    arguments_hash: str


@dataclass
class AuditEntry:
    timestamp: float
    tool_name: str
    arguments_hash: str
    decision: str
    duration: float
    exit_code: int
    success: bool
    output_size: int
    error_size: int
    user_id: Optional[str]
    source: str


class GovernancePolicy:
    """
    Configurable governance policy for tool execution.
    
    Default behavior:
    - Read-only tools (read, glob, grep): auto-allow
    - Write tools (write, edit): require approval
    - Dangerous tools (bash, delete): deny by default
    """
    
    def __init__(self):
        self.safe_tools = {"read", "glob", "grep", "search", "fetch"}
        self.guarded_tools = {"write", "edit", "mcp_*"}
        self.dangerous_tools = {"bash", "shell", "exec", "delete", "remove", "drop"}
        
        self.dangerous_patterns = [
            r"rm\s+-rf", r"dd\s+if=", r"mkfs", r"drop\s+(table|database)",
            r"truncate", r"shutdown", r"reboot", r":\(\){",
            r"curl.*\|.*sh", r"wget.*\|.*sh"
        ]
        
        self.dangerous_paths = [
            "/etc", "/bin", "/sbin", "/usr/bin", "/usr/sbin",
            "/root", "~/.ssh", "~/.aws", "/sys", "/proc"
        ]
    
    def get_safety_level(self, tool_name: str) -> SafetyLevel:
        """Get safety level for a tool."""
        tool_lower = tool_name.lower()
        
        if tool_lower in self.dangerous_tools:
            return SafetyLevel.DANGEROUS
        
        if tool_lower in self.safe_tools:
            return SafetyLevel.SAFE
        
        if tool_lower.startswith("mcp_"):
            return SafetyLevel.GUARDED
        
        return SafetyLevel.GUARDED
    
    def check_dangerous_patterns(self, arguments: Dict[str, Any]) -> Optional[str]:
        """Check if arguments contain dangerous patterns."""
        args_str = json.dumps(arguments, sort_keys=True).lower()
        
        for pattern in self.dangerous_patterns:
            import re
            if re.search(pattern, args_str, re.IGNORECASE):
                return f"Argument matches dangerous pattern: {pattern}"
        
        return None
    
    def check_dangerous_paths(self, arguments: Dict[str, Any]) -> Optional[str]:
        """Check if arguments reference dangerous paths."""
        args_str = json.dumps(arguments, sort_keys=True)
        
        for dangerous_path in self.dangerous_paths:
            if dangerous_path in args_str:
                return f"Argument references protected path: {dangerous_path}"
        
        return None
    
    def should_approve(self, context: ToolContext) -> tuple[bool, str, ApprovalLevel]:
        """
        Determine if a tool should be approved.
        
        Returns:
            (allowed, reason, approval_level)
        """
        safety = self.get_safety_level(context.tool_name)
        
        if safety == SafetyLevel.DANGEROUS:
            return False, f"Tool '{context.tool_name}' is in dangerous tools list", ApprovalLevel.DENIED
        
        if safety == SafetyLevel.GUARDED:
            danger_reason = self.check_dangerous_patterns(context.arguments)
            if danger_reason:
                return False, danger_reason, ApprovalLevel.DENIED
            
            path_reason = self.check_dangerous_paths(context.arguments)
            if path_reason:
                return False, path_reason, ApprovalLevel.DENIED
            
            return True, "Guarded tool approved", ApprovalLevel.APPROVED
        
        return True, "Safe tool auto-approved", ApprovalLevel.AUTO


class GovernanceHooks:
    """
    PreToolUse and PostToolUse hooks for tool execution governance.
    """
    
    def __init__(self, policy: Optional[GovernancePolicy] = None):
        self.policy = policy or GovernancePolicy()
        self.audit_log_path = Path.home() / ".roxy" / "data" / "tool_audit.jsonl"
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.pre_checks: List[Callable] = []
        self.post_hooks: List[Callable] = []
    
    def add_pre_check(self, check: Callable):
        """Add a pre-tool check function."""
        self.pre_checks.append(check)
    
    def add_post_hook(self, hook: Callable):
        """Add a post-tool logging function."""
        self.post_hooks.append(hook)
    
    async def pre_tool_use(self, context: ToolContext) -> GovernanceDecision:
        """
        PreToolUse hook - called before tool execution.
        
        Returns:
            GovernanceDecision with allow/deny and reason
        """
        allowed, reason, level = self.policy.should_approve(context)
        
        args_hash = hash(json.dumps(context.arguments, sort_keys=True))
        
        for check in self.pre_checks:
            try:
                result = await check(context)
                if result is False:
                    allowed = False
                    reason = f"Pre-check failed: {reason}"
                    level = ApprovalLevel.DENIED
                    break
            except Exception as e:
                logger.error(f"Pre-check error: {e}")
        
        decision = GovernanceDecision(
            allowed=allowed,
            reason=reason,
            approval_level=level,
            timestamp=time.time(),
            tool_name=context.tool_name,
            arguments_hash=str(args_hash)
        )
        
        logger.info(
            f"PreToolUse: {context.tool_name} - "
            f"{'ALLOWED' if allowed else 'DENIED'} ({level.value}): {reason}"
        )
        
        return decision
    
    async def post_tool_use(
        self,
        context: ToolContext,
        result: Dict[str, Any],
        decision: GovernanceDecision
    ):
        """
        PostToolUse hook - called after tool execution.
        
        Logs execution to audit trail.
        """
        audit = AuditEntry(
            timestamp=time.time(),
            tool_name=context.tool_name,
            arguments_hash=decision.arguments_hash,
            decision="allowed" if decision.allowed else "denied",
            duration=result.get("duration", 0),
            exit_code=result.get("exit_code", -1),
            success=result.get("success", False),
            output_size=len(result.get("output", "")),
            error_size=len(result.get("error", "")),
            user_id=context.user_id,
            source=context.source
        )
        
        self._log_audit(audit)
        
        for hook in self.post_hooks:
            try:
                hook(audit)
            except Exception as e:
                logger.error(f"Post-hook error: {e}")
    
    def _log_audit(self, audit: AuditEntry):
        """Append audit entry to log file."""
        try:
            with open(self.audit_log_path, "a") as f:
                f.write(json.dumps({
                    "timestamp": audit.timestamp,
                    "tool": audit.tool_name,
                    "args_hash": audit.arguments_hash,
                    "decision": audit.decision,
                    "duration": audit.duration,
                    "exit_code": audit.exit_code,
                    "success": audit.success,
                    "output_size": audit.output_size,
                    "error_size": audit.error_size,
                    "user_id": audit.user_id,
                    "source": audit.source
                }) + "\n")
        except Exception as e:
            logger.error(f"Audit log error: {e}")
    
    def get_audit_log(
        self,
        since: Optional[float] = None,
        tool_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Retrieve audit log entries."""
        entries = []
        
        if not self.audit_log_path.exists():
            return entries
        
        try:
            with open(self.audit_log_path, "r") as f:
                for line in f:
                    if len(entries) >= limit:
                        break
                    
                    try:
                        entry = json.loads(line)
                        
                        if since and entry.get("timestamp", 0) < since:
                            continue
                        
                        if tool_name and entry.get("tool") != tool_name:
                            continue
                        
                        entries.append(entry)
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            logger.error(f"Audit read error: {e}")
        
        return entries


async def test_governance():
    """Test governance hooks."""
    governance = GovernanceHooks()
    
    print("Test 1: Safe tool (read)")
    ctx = ToolContext(
        tool_name="read",
        arguments={"file_path": "/etc/passwd"}
    )
    decision = await governance.pre_tool_use(ctx)
    print(f"  Decision: {'ALLOWED' if decision.allowed else 'DENIED'}")
    print(f"  Level: {decision.approval_level.value}")
    print(f"  Reason: {decision.reason}")
    
    print("\nTest 2: Dangerous tool (bash)")
    ctx = ToolContext(
        tool_name="bash",
        arguments={"command": "rm -rf /tmp/test"}
    )
    decision = await governance.pre_tool_use(ctx)
    print(f"  Decision: {'ALLOWED' if decision.allowed else 'DENIED'}")
    print(f"  Level: {decision.approval_level.value}")
    print(f"  Reason: {decision.reason}")
    
    print("\nTest 3: Post-tool audit")
    ctx = ToolContext(tool_name="read", arguments={})
    result = {"success": True, "duration": 0.1, "exit_code": 0}
    await governance.post_tool_use(ctx, result, decision)
    print(f"  Audit logged")
    
    print("\nTest 4: Audit log retrieval")
    entries = governance.get_audit_log(limit=5)
    print(f"  Found {len(entries)} entries")


if __name__ == "__main__":
    asyncio.run(test_governance())
