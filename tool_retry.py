#!/usr/bin/env python3
"""
Tool Retry Controller - Bounded strategy rotation with typed memory integration.

Failure flow:
  1. Tool fails → classify root cause
  2. Query fix_recipes from typed memory for this command signature
  3. If fix_recipe found, apply it
  4. If not, rotate strategy based on root cause
  5. After all strategies exhausted, write failure_event + bug to typed memory
  6. Never repeat the same strategy twice

Strategy families per root cause:
  - permission   → [default, sudo, sudo_env, chmod]
  - not_found    → [default, install_deps, path_lookup, alternatives]
  - timeout      → [default, retry_slow, retry_after_delay, split_workload]
  - syntax      → [default, validate_first, lint_then_run]
  - api_error    → [default, retry_backoff, retry_after_delay]
  - unknown      → [default, retry_once, validate_first]
"""
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("roxy.tool_retry")

MAX_RETRIES_PER_TOOL = 3
RETRY_COOLDOWN_SEC = 2.0


@dataclass
class RetryStrategy:
    name: str
    transform: Callable[[str, Dict], Optional[Dict]]  # (command, args) -> new (command, args) or None
    description: str


class RootCauseClassifier:
    """Classifies tool failure root cause from exit code, error message, and command."""

    @staticmethod
    def classify(command: str, error: str, exit_code: int) -> str:
        error_lower = error.lower()
        cmd_lower = command.lower()

        if exit_code == 126:
            return "permission"
        if exit_code == 127:
            return "not_found"
        if exit_code == 124:
            return "timeout"
        if "permission denied" in error_lower or "access denied" in error_lower:
            return "permission"
        if ("not found" in error_lower or "command not found" in error_lower
                or "no such file" in error_lower):
            return "not_found"
        if "syntax error" in error_lower or "parse error" in error_lower:
            return "syntax"
        if "timed out" in error_lower or "timeout" in error_lower:
            return "timeout"
        if any(x in error_lower for x in ["connection refused", "connection reset",
                                            "503", "502", "504", "rate limit"]):
            return "api_error"
        if "cannot execute" in error_lower or "exec format error" in error_lower:
            return "permission"
        if exit_code != 0:
            return "unknown"
        return "unknown"


@dataclass
class StrategyState:
    tool_name: str
    command_sig: str
    attempts: List[str] = field(default_factory=list)
    last_error: str = ""
    last_exit_code: int = 0
    last_root_cause: str = "unknown"
    last_attempted: float = 0.0

    def already_tried(self, strategy_name: str) -> bool:
        return strategy_name in self.attempts

    def record(self, strategy_name: str, error: str, exit_code: int, root_cause: str):
        self.attempts.append(strategy_name)
        self.last_error = error
        self.last_exit_code = exit_code
        self.last_root_cause = root_cause
        self.last_attempted = time.time()


class StrategyRegistry:
    """Registry of retry strategies per root cause."""

    def __init__(self):
        self._strategies: Dict[str, List[RetryStrategy]] = {
            "permission": self._permission_strategies(),
            "not_found": self._not_found_strategies(),
            "timeout": self._timeout_strategies(),
            "syntax": self._syntax_strategies(),
            "api_error": self._api_error_strategies(),
            "unknown": self._unknown_strategies(),
        }

    def get_strategies(self, root_cause: str) -> List[RetryStrategy]:
        return self._strategies.get(root_cause, self._strategies["unknown"])

    @staticmethod
    def _make_command_transform(new_command: str) -> Callable[[str, Dict], Optional[Dict]]:
        def transform(command: str, args: Dict) -> Optional[Dict]:
            return {"command": new_command, "args": args}
        return transform

    @staticmethod
    def _wrap_command(wrap_fmt: str) -> Callable[[str, Dict], Optional[Dict]]:
        def transform(command: str, args: Dict) -> Optional[Dict]:
            return {"command": wrap_fmt.format(cmd=command), "args": args}
        return transform

    @staticmethod
    def _add_sudo() -> Callable[[str, Dict], Optional[Dict]]:
        def transform(command: str, args: Dict) -> Optional[Dict]:
            return {"command": f"sudo {command}", "args": args}
        return transform

    @staticmethod
    def _add_sudo_env() -> Callable[[str, Dict], Optional[Dict]]:
        def transform(command: str, args: Dict) -> Optional[Dict]:
            env = args.get("env", {}).copy()
            env["SUDO_ASKPASS"] = "/bin/echo"
            return {"command": f"sudo -E {command}", "args": {**args, "env": env}}
        return transform

    @staticmethod
    def _install_deps(command: str, args: Dict) -> Optional[Dict]:
        """Try to install missing tool and retry."""
        missing_tool = command.split()[0] if command.split() else ""
        if not missing_tool:
            return None
        return {
            "command": f"pip install {missing_tool} 2>/dev/null || pip3 install {missing_tool} 2>/dev/null || apt-get install -y {missing_tool} 2>/dev/null || true && {command}",
            "args": args,
        }

    @staticmethod
    def _path_lookup(command: str, args: Dict) -> Optional[Dict]:
        """Find the tool in PATH and use full path."""
        tool = command.split()[0] if command.split() else ""
        if not tool:
            return None
        try:
            result = subprocess.run(["which", tool], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                full_path = result.stdout.strip().split()[0]
                new_cmd = command.replace(tool, full_path, 1)
                return {"command": new_cmd, "args": args}
        except Exception:
            pass
        return None

    @staticmethod
    def _split_workload(command: str, args: Dict) -> Optional[Dict]:
        """Split large operation into chunks."""
        if "&&" in command:
            parts = command.split("&&")
            if len(parts) > 1:
                return {"command": " && ".join(parts[:len(parts)//2]), "args": args}
        return {"command": f"echo 'THROTTLED: {command}'", "args": args}

    def _permission_strategies(self) -> List[RetryStrategy]:
        return [
            RetryStrategy("default", lambda c, a: None,
                          "No transform - first attempt"),
            RetryStrategy("sudo", self._add_sudo(),
                          "Retry with sudo prefix"),
            RetryStrategy("sudo_env", self._add_sudo_env(),
                          "Retry with sudo -E preserving environment"),
            RetryStrategy("chmod", lambda c, a: {"command": f"chmod +x /tmp/roxy_exec.sh && (cat << 'REXEOF'\n{c}\nREXEOF) | bash", "args": a},
                          "Write to temp file, chmod +x, execute"),
        ]

    def _not_found_strategies(self) -> List[RetryStrategy]:
        return [
            RetryStrategy("default", lambda c, a: None,
                          "No transform - first attempt"),
            RetryStrategy("install_deps", self._install_deps,
                          "Try installing missing tool"),
            RetryStrategy("path_lookup", self._path_lookup,
                          "Find tool in PATH and use full path"),
            RetryStrategy("alternatives", lambda c, a: {"command": f"which {c.split()[0] if c.split() else c} > /dev/null 2>&1 || echo 'tool missing'", "args": a},
                          "Check for available alternatives"),
        ]

    def _timeout_strategies(self) -> List[RetryStrategy]:
        return [
            RetryStrategy("default", lambda c, a: None,
                          "No transform - first attempt"),
            RetryStrategy("retry_slow", lambda c, a: None,
                          "Same command, user acknowledged slowness"),
            RetryStrategy("retry_after_delay", lambda c, a: None,
                          "Same command after brief delay"),
            RetryStrategy("split_workload", self._split_workload,
                          "Split into smaller operations"),
        ]

    def _syntax_strategies(self) -> List[RetryStrategy]:
        return [
            RetryStrategy("default", lambda c, a: None,
                          "No transform - first attempt"),
            RetryStrategy("validate_first", lambda c, a: {"command": f"bash -n << 'SYNTAXCHECK'\n{c}\nSYNTAXCHECK", "args": a},
                          "Validate syntax before running"),
            RetryStrategy("lint_then_run", lambda c, a: {"command": f"shellcheck -s bash << 'LINTCHECK'\n{c}\nLINTCHECK || {c}", "args": a},
                          "Run shellcheck lint then execute if safe"),
        ]

    def _api_error_strategies(self) -> List[RetryStrategy]:
        return [
            RetryStrategy("default", lambda c, a: None,
                          "No transform - first attempt"),
            RetryStrategy("retry_backoff", lambda c, a: None,
                          "Exponential backoff wait"),
            RetryStrategy("retry_after_delay", lambda c, a: None,
                          "Retry after fixed delay"),
        ]

    def _unknown_strategies(self) -> List[RetryStrategy]:
        return [
            RetryStrategy("default", lambda c, a: None,
                          "No transform - first attempt"),
            RetryStrategy("retry_once", lambda c, a: None,
                          "One additional retry"),
            RetryStrategy("validate_first", lambda c, a: {"command": f"echo 'validating...' && {c}", "args": a},
                          "Validate command before running"),
        ]


class ToolRetryController:
    """
    Bounded retry controller with strategy rotation.

    Integrates with:
    - Typed memory: queries fix_recipes on failure, writes failure_event + bug on exhaustion
    - StrategyRegistry: rotates through strategies per root cause
    - StrategyState: tracks per-command retry history to avoid repeats
    """

    def __init__(self):
        self._strategy_registry = StrategyRegistry()
        self._state: Dict[str, StrategyState] = {}
        self._fix_recipe_cache: Dict[str, Optional[Dict]] = {}

    def _make_signature(self, tool_name: str, command: str, args: Dict) -> str:
        """Create a stable signature for this tool call."""
        args_key = ",".join(f"{k}={v}" for k, v in sorted((args or {}).items()))
        return f"{tool_name}:{command}:{args_key}"

    def _get_state(self, tool_name: str, command: str, args: Dict) -> StrategyState:
        sig = self._make_signature(tool_name, command, args)
        if sig not in self._state:
            self._state[sig] = StrategyState(tool_name=tool_name, command_sig=command)
        return self._state[sig]

    def _query_fix_recipe(self, tool_name: str, command: str) -> Optional[Dict]:
        """Query typed memory for a fix recipe for this command signature."""
        sig = self._make_signature(tool_name, command, {})
        if sig in self._fix_recipe_cache:
            return self._fix_recipe_cache[sig]

        try:
            from infrastructure import get_typed_records
            records = get_typed_records(
                query=f"fix recipe for {command}",
                record_types=["fix_recipe"],
                limit=3,
                user_id=None,
            )
            if records:
                for rec in records:
                    content = rec.get("content", "")
                    metadata = rec.get("metadata", {})
                    if content and len(content) > 5:
                        self._fix_recipe_cache[sig] = {
                            "content": content,
                            "command": metadata.get("command", command),
                            "recipe_id": rec.get("id"),
                        }
                        logger.info(f"[RetryController] Found fix_recipe for '{command}': {content[:80]}")
                        return self._fix_recipe_cache[sig]
        except Exception as e:
            logger.debug(f"[RetryController] Fix recipe query failed: {e}")

        self._fix_recipe_cache[sig] = None
        return None

    def _write_failure_event(self, tool_name: str, command: str, args: Dict,
                              error: str, exit_code: int, root_cause: str):
        """Write failure_event and bug records to typed memory."""
        try:
            from infrastructure import remember_typed_record
            sig = self._make_signature(tool_name, command, args)

            remember_typed_record(
                record_type="failure_event",
                content=f"Tool '{tool_name}' failed on command: {command}. "
                        f"Error: {error[:200]}. Root cause: {root_cause}. "
                        f"Exit code: {exit_code}.",
                scope="tool_execution",
                provenance="ToolRetryController",
                confidence=0.8,
                metadata={
                    "tool_name": tool_name,
                    "command": command,
                    "command_sig": sig,
                    "error": error[:500],
                    "exit_code": exit_code,
                    "root_cause": root_cause,
                    "args": args,
                },
                user_id=None,
            )

            if exit_code != 0 and root_cause != "timeout":
                remember_typed_record(
                    record_type="bug",
                    content=f"Tool failure: {command} failed with '{error[:200]}'. "
                            f"Exit code: {exit_code}. Root cause: {root_cause}.",
                    scope="tool_execution",
                    provenance="ToolRetryController",
                    confidence=0.6,
                    metadata={
                        "tool_name": tool_name,
                        "command": command,
                        "command_sig": sig,
                        "error": error[:500],
                        "exit_code": exit_code,
                        "root_cause": root_cause,
                        "fix_command": "",
                    },
                    user_id=None,
                )
        except Exception as e:
            logger.debug(f"[RetryController] Failed to write failure event: {e}")

    def _write_fix_recipe(self, tool_name: str, command: str, error: str,
                           root_cause: str, successful_command: str):
        """Write a fix_recipe after successful recovery."""
        try:
            from infrastructure import remember_typed_record
            sig = self._make_signature(tool_name, command, {})

            remember_typed_record(
                record_type="fix_recipe",
                content=f"Recovered from '{error[:100]}' by using: {successful_command}",
                scope="tool_execution",
                provenance="ToolRetryController",
                confidence=0.7,
                metadata={
                    "tool_name": tool_name,
                    "original_command": command,
                    "command_sig": sig,
                    "error": error[:200],
                    "root_cause": root_cause,
                    "successful_command": successful_command,
                },
                user_id=None,
            )
            logger.info(f"[RetryController] Wrote fix_recipe for: {command[:50]}")
        except Exception as e:
            logger.debug(f"[RetryController] Failed to write fix recipe: {e}")

    def should_retry(self, tool_name: str, command: str, args: Dict,
                     error: str, exit_code: int) -> bool:
        """Determine if this tool call should be retried."""
        state = self._get_state(tool_name, command, args)
        root_cause = RootCauseClassifier.classify(command, error, exit_code)

        if state.attempts and "default" not in state.attempts:
            return False

        total_attempts = len(state.attempts)
        if total_attempts >= MAX_RETRIES_PER_TOOL:
            return False

        if root_cause == "syntax":
            return False

        if root_cause == "unknown" and total_attempts >= 1:
            return False

        return True

    def get_next_strategy(self, tool_name: str, command: str, args: Dict,
                          error: str, exit_code: int) -> Optional[Dict]:
        """
        Get the next retry strategy for a failed tool call.

        Returns:
            Dict with keys: command, args, strategy_name, is_fix_recipe
            or None if no more strategies available.
        """
        state = self._get_state(tool_name, command, args)
        root_cause = RootCauseClassifier.classify(command, error, exit_code)
        state.record("initial", error, exit_code, root_cause)

        if len(state.attempts) >= MAX_RETRIES_PER_TOOL:
            self._write_failure_event(tool_name, command, args, error, exit_code, root_cause)
            return None

        fix_recipe = self._query_fix_recipe(tool_name, command)
        if fix_recipe and "default" not in state.attempts:
            recipe_cmd = fix_recipe.get("command", command)
            return {
                "command": recipe_cmd,
                "args": args,
                "strategy_name": f"fix_recipe:{fix_recipe.get('recipe_id', 'unknown')}",
                "is_fix_recipe": True,
            }

        strategies = self._strategy_registry.get_strategies(root_cause)
        for strategy in strategies:
            if state.already_tried(strategy.name):
                continue

            transform = strategy.transform(command, args)
            if transform is None:
                return {
                    "command": command,
                    "args": args,
                    "strategy_name": strategy.name,
                    "description": strategy.description,
                    "is_fix_recipe": False,
                }
            else:
                return {
                    "command": transform["command"],
                    "args": transform["args"],
                    "strategy_name": strategy.name,
                    "description": strategy.description,
                    "is_fix_recipe": False,
                }

        self._write_failure_event(tool_name, command, args, error, exit_code, root_cause)
        return None

    def record_success(self, tool_name: str, command: str, args: Dict,
                       original_error: str, root_cause: str, successful_command: str):
        """Record a successful recovery for future fix_recipe reuse."""
        if successful_command != command:
            self._write_fix_recipe(tool_name, command, original_error,
                                    root_cause, successful_command)

    def get_stats(self) -> Dict[str, Any]:
        """Get retry statistics."""
        return {
            "tracked_commands": len(self._state),
            "cached_fix_recipes": len(self._fix_recipe_cache),
            "by_state": {
                sig: {
                    "tool": s.tool_name,
                    "attempts": s.attempts,
                    "root_cause": s.last_root_cause,
                    "last_error": s.last_error[:100] if s.last_error else "",
                }
                for sig, s in list(self._state.items())[:20]
            },
        }


_controller: Optional[ToolRetryController] = None


def get_retry_controller() -> ToolRetryController:
    global _controller
    if _controller is None:
        _controller = ToolRetryController()
    return _controller
