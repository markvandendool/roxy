#!/usr/bin/env python3
"""
Streaming Tools - Read/Write/Edit/Glob/Grep as native tool calls
Part of ROXY-AUTONOMOUS-CODING-AGENT-V1 (RCA-002)
"""
import asyncio
import difflib
import json
import logging
import os
import re
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Dict, Any, List, Optional, Tuple

logger = logging.getLogger("roxy.streaming_tools")

MAX_FILE_SIZE = 1024 * 1024
MAX_SEARCH_RESULTS = 100
MAX_OPENCODE_EVENTS = int(os.getenv("ROXY_OPENCODE_MAX_EVENTS", "5000"))
DEFAULT_OPENCODE_MODEL = os.getenv("ROXY_OPENCODE_MODEL", "opencode/mimo-v2-pro-free")
DEFAULT_OPENCODE_TIMEOUT_SEC = float(os.getenv("ROXY_OPENCODE_TIMEOUT_SEC", "180"))
DEFAULT_OPENCODE_PROFILE = os.getenv("ROXY_OPENCODE_PROFILE", "primary")
ENABLE_OPENCODE_ULTRAMAX = os.getenv("ROXY_OPENCODE_ULTRAMAX", "1").lower() in ("1", "true", "yes")
ENABLE_OPENCODE_BOOTSTRAP = os.getenv("ROXY_OPENCODE_BOOTSTRAP", "1").lower() in ("1", "true", "yes")
ENABLE_OPENCODE_FREE_FALLBACK = os.getenv("ROXY_OPENCODE_FREE_FALLBACK", "1").lower() in ("1", "true", "yes")
OPENCODE_BOOTSTRAP_MAX_CHARS = int(os.getenv("ROXY_OPENCODE_BOOTSTRAP_MAX_CHARS", "5000"))
OPENCODE_CHAIN_MAX_STEPS = int(os.getenv("ROXY_OPENCODE_CHAIN_MAX_STEPS", "8"))
OPENCODE_DEFAULT_VARIANT = os.getenv("ROXY_OPENCODE_DEFAULT_VARIANT", "high")

ROXY_ROOT = Path.home() / ".roxy"

OPENCODE_PROFILE_MAP: Dict[str, Dict[str, Any]] = {
    "primary": {
        "model": "opencode/mimo-v2-pro-free",
        "variant": "high",
        "thinking": True,
    },
    "reasoning": {
        "model": "opencode/big-pickle",
        "variant": "max",
        "thinking": True,
    },
    "fast": {
        "model": "opencode/gpt-5-nano",
        "variant": "low",
        "thinking": False,
    },
    "bigbrain": {
        "model": "opencode/nemotron-3-super-free",
        "variant": "high",
        "thinking": True,
    },
    "architect": {
        "model": "opencode/mimo-v2-omni-free",
        "variant": "high",
        "thinking": True,
    },
    "free": {
        "model": "opencode/minimax-m2.5-free",
        "variant": "high",
        "thinking": True,
    },
    "max": {
        "model": "openai/gpt-5.4",
        "variant": "high",
        "thinking": True,
    },
    "codexmax": {
        "model": "openai/gpt-5.1-codex-max",
        "variant": "high",
        "thinking": True,
    },
    "copilot": {
        "model": "github-copilot/claude-opus-4.6",
        "variant": "high",
        "thinking": True,
    },
    "gmodels": {
        "model": "github-models/deepseek/deepseek-r1-0528",
        "variant": "high",
        "thinking": True,
    },
}

OPENCODE_FREE_FALLBACK_CHAIN: List[str] = [
    "opencode/mimo-v2-pro-free",
    "opencode/nemotron-3-super-free",
    "opencode/minimax-m2.5-free",
    "opencode/gpt-5-nano",
]


@dataclass
class ToolResponse:
    success: bool
    data: Any = None
    error: str = ""
    tool_name: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class StreamingTools:
    """Collection of file operations as async tools."""
    
    def __init__(self, workdir: Optional[str] = None):
        self.workdir = workdir or os.getcwd()
    
    async def read_file(
        self,
        file_path: str,
        offset: int = 0,
        limit: int = None,
        stream_callback=None
    ) -> ToolResponse:
        """
        Read file content with optional streaming.
        
        Args:
            file_path: Path to file (absolute or relative to workdir)
            offset: Line number to start from (1-indexed)
            limit: Maximum lines to read (None = all)
            stream_callback: Optional async callback for streaming
            
        Returns:
            ToolResponse with file content
        """
        try:
            path = self._resolve_path(file_path)
            
            if not path.exists():
                return ToolResponse(
                    success=False,
                    error=f"File not found: {file_path}",
                    tool_name="read"
                )
            
            if not path.is_file():
                return ToolResponse(
                    success=False,
                    error=f"Not a file: {file_path}",
                    tool_name="read"
                )
            
            file_size = path.stat().st_size
            if file_size > MAX_FILE_SIZE:
                return ToolResponse(
                    success=False,
                    error=f"File too large: {file_size} bytes (max {MAX_FILE_SIZE})",
                    tool_name="read"
                )
            
            content = path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            if offset > 0:
                lines = lines[offset - 1:]
            
            if limit is not None:
                lines = lines[:limit]
            
            result_lines = []
            for i, line in enumerate(lines, start=offset or 1):
                line_content = f"{i}: {line}\n"
                result_lines.append(line_content)
                if stream_callback:
                    await stream_callback(line_content)
            
            final_content = ''.join(result_lines)
            
            return ToolResponse(
                success=True,
                data=final_content,
                tool_name="read",
                metadata={
                    "file_path": str(path),
                    "lines_read": len(result_lines),
                    "total_lines": len(content.split('\n')),
                    "offset": offset,
                    "limit": limit,
                    "size_bytes": file_size
                }
            )
            
        except PermissionError:
            return ToolResponse(
                success=False,
                error=f"Permission denied: {file_path}",
                tool_name="read"
            )
        except UnicodeDecodeError:
            return ToolResponse(
                success=False,
                error=f"Cannot decode file as UTF-8: {file_path}",
                tool_name="read"
            )
        except Exception as e:
            logger.error(f"Read error: {e}")
            return ToolResponse(
                success=False,
                error=str(e),
                tool_name="read"
            )
    
    async def write_file(
        self,
        file_path: str,
        content: str,
        create_parents: bool = True
    ) -> ToolResponse:
        """
        Write content to file (creates if not exists, overwrites if exists).
        
        Args:
            file_path: Path to file (absolute or relative to workdir)
            content: Content to write
            create_parents: Create parent directories if needed
            
        Returns:
            ToolResponse with write result
        """
        try:
            path = self._resolve_path(file_path)
            
            if create_parents:
                path.parent.mkdir(parents=True, exist_ok=True)
            
            path.write_text(content, encoding='utf-8')
            
            return ToolResponse(
                success=True,
                data={"path": str(path), "bytes_written": len(content.encode('utf-8'))},
                tool_name="write",
                metadata={"file_path": str(path), "size": len(content)}
            )
            
        except PermissionError:
            return ToolResponse(
                success=False,
                error=f"Permission denied: {file_path}",
                tool_name="write"
            )
        except Exception as e:
            logger.error(f"Write error: {e}")
            return ToolResponse(
                success=False,
                error=str(e),
                tool_name="write"
            )
    
    async def edit_file(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        create_backup: bool = True
    ) -> ToolResponse:
        """
        Edit file by replacing old_string with new_string.
        
        Args:
            file_path: Path to file
            old_string: String to replace
            new_string: Replacement string
            create_backup: Create .bak backup before edit
            
        Returns:
            ToolResponse with diff and result
        """
        try:
            path = self._resolve_path(file_path)
            
            if not path.exists():
                return ToolResponse(
                    success=False,
                    error=f"File not found: {file_path}",
                    tool_name="edit"
                )
            
            original_content = path.read_text(encoding='utf-8')
            
            if old_string not in original_content:
                return ToolResponse(
                    success=False,
                    error=f"old_string not found in file. Check for exact match including whitespace.",
                    tool_name="edit",
                    metadata={
                        "old_string_length": len(old_string),
                        "file_content_length": len(original_content)
                    }
                )
            
            if create_backup:
                backup_path = path.with_suffix(path.suffix + '.bak')
                backup_path.write_text(original_content, encoding='utf-8')
            
            new_content = original_content.replace(old_string, new_string, 1)
            
            diff = list(difflib.unified_diff(
                original_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=str(path),
                tofile=str(path),
                lineterm=''
            ))
            
            path.write_text(new_content, encoding='utf-8')
            
            return ToolResponse(
                success=True,
                data={
                    "path": str(path),
                    "diff": ''.join(diff),
                    "backup_created": str(path.with_suffix('.bak')) if create_backup else None
                },
                tool_name="edit",
                metadata={
                    "file_path": str(path),
                    "bytes_changed": len(new_content) - len(original_content)
                }
            )
            
        except PermissionError:
            return ToolResponse(
                success=False,
                error=f"Permission denied: {file_path}",
                tool_name="edit"
            )
        except Exception as e:
            logger.error(f"Edit error: {e}")
            return ToolResponse(
                success=False,
                error=str(e),
                tool_name="edit"
            )
    
    async def glob(
        self,
        pattern: str,
        base_path: Optional[str] = None,
        recursive: bool = True
    ) -> ToolResponse:
        """
        Find files matching glob pattern.
        
        Args:
            pattern: Glob pattern (e.g., "**/*.py", "src/*.ts")
            base_path: Base directory to search (defaults to workdir)
            recursive: Search recursively
            
        Returns:
            ToolResponse with list of matching files
        """
        try:
            base = self._resolve_path(base_path) if base_path else Path(self.workdir)
            
            if recursive and '**' not in pattern:
                pattern = '**/' + pattern
            
            matches = list(base.glob(pattern))[:MAX_SEARCH_RESULTS]
            
            return ToolResponse(
                success=True,
                data=[str(m) for m in matches],
                tool_name="glob",
                metadata={
                    "pattern": pattern,
                    "base_path": str(base),
                    "matches_count": len(matches),
                    "truncated": len(matches) >= MAX_SEARCH_RESULTS
                }
            )
            
        except Exception as e:
            logger.error(f"Glob error: {e}")
            return ToolResponse(
                success=False,
                error=str(e),
                tool_name="glob"
            )
    
    async def grep(
        self,
        pattern: str,
        path: Optional[str] = None,
        file_pattern: str = "*",
        case_sensitive: bool = True,
        context_lines: int = 0
    ) -> ToolResponse:
        """
        Search for pattern in files.
        
        Args:
            pattern: Regex or string pattern to search
            path: Directory to search (defaults to workdir)
            file_pattern: File glob pattern (e.g., "*.py", "*.{ts,tsx}")
            case_sensitive: Case-sensitive search
            context_lines: Lines of context before/after match
            
        Returns:
            ToolResponse with search results
        """
        try:
            search_path = self._resolve_path(path) if path else Path(self.workdir)
            
            if not search_path.exists():
                return ToolResponse(
                    success=False,
                    error=f"Path not found: {path or self.workdir}",
                    tool_name="grep"
                )
            
            flags = 0 if case_sensitive else re.IGNORECASE
            compiled_pattern = re.compile(pattern, flags)
            
            results = []
            file_patterns = file_pattern.replace(',', ' ').split()
            
            for fp in file_patterns:
                for file_path in search_path.rglob(fp):
                    if not file_path.is_file():
                        continue
                    
                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        lines = content.split('\n')
                        
                        for i, line in enumerate(lines, 1):
                            if compiled_pattern.search(line):
                                match_data = {
                                    "file": str(file_path),
                                    "line": i,
                                    "content": line.strip(),
                                    "column": line.find(compiled_pattern.search(line).group())
                                }
                                
                                if context_lines > 0:
                                    start = max(0, i - context_lines - 1)
                                    end = min(len(lines), i + context_lines)
                                    match_data["context"] = [
                                        f"{j}: {lines[j]}" 
                                        for j in range(start, end)
                                    ]
                                
                                results.append(match_data)
                                
                                if len(results) >= MAX_SEARCH_RESULTS:
                                    return ToolResponse(
                                        success=True,
                                        data=results,
                                        tool_name="grep",
                                        metadata={
                                            "pattern": pattern,
                                            "path": str(search_path),
                                            "files_searched": "multiple",
                                            "truncated": True,
                                            "total_matches": len(results)
                                        }
                                    )
                                
                    except Exception:
                        continue
            
            return ToolResponse(
                success=True,
                data=results,
                tool_name="grep",
                metadata={
                    "pattern": pattern,
                    "path": str(search_path),
                    "matches_count": len(results),
                    "truncated": len(results) >= MAX_SEARCH_RESULTS
                }
            )
            
        except re.error as e:
            return ToolResponse(
                success=False,
                error=f"Invalid regex: {e}",
                tool_name="grep"
            )
        except Exception as e:
            logger.error(f"Grep error: {e}")
            return ToolResponse(
                success=False,
                error=str(e),
                tool_name="grep"
            )

    @staticmethod
    def _to_bool(value: Any, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("1", "true", "yes", "on")

    @staticmethod
    def _get_profile(mode: Optional[str]) -> Dict[str, Any]:
        selected = str(mode or DEFAULT_OPENCODE_PROFILE).strip().lower()
        return OPENCODE_PROFILE_MAP.get(selected, OPENCODE_PROFILE_MAP["primary"])

    @staticmethod
    def _should_use_free_fallback(error_text: str) -> bool:
        lower = str(error_text or "").lower()
        patterns = [
            "locked billing",
            "insufficient_quota",
            "quota",
            "statuscode\":403",
            "status code 403",
            "auth",
            "unauthorized",
            "forbidden",
            "permission",
            "payment",
        ]
        return any(token in lower for token in patterns)

    @staticmethod
    def _build_fallback_model_chain(primary_model: str) -> List[str]:
        chain = [primary_model] if primary_model else []
        for candidate in OPENCODE_FREE_FALLBACK_CHAIN:
            if candidate not in chain:
                chain.append(candidate)
        return chain

    def _resolve_bootstrap_files(self) -> List[Path]:
        env_override = os.getenv("ROXY_OPENCODE_BOOTSTRAP_FILES", "").strip()
        if env_override:
            files: List[Path] = []
            for item in env_override.split(","):
                value = item.strip()
                if not value:
                    continue
                files.append(Path(value).expanduser())
            return files

        defaults = [
            ROXY_ROOT / "ROXY_IDENTITY.md",
            ROXY_ROOT / "docs" / "ROXY_STATUS_DOCTRINE.md",
            ROXY_ROOT / "docs" / "ROXY_RUNBOOK_CORE.md",
            ROXY_ROOT / "docs" / "docs" / "onboarding" / "START_HERE.md",
            ROXY_ROOT / "docs" / "docs" / "brain" / "INDEX.md",
        ]
        skoreq_glob = sorted((ROXY_ROOT / "docs" / "skoreq").glob("**/00_PLAN.md"))
        defaults.extend(skoreq_glob[:4])
        return defaults

    def _build_spawn_boost_context(self, max_chars: int = OPENCODE_BOOTSTRAP_MAX_CHARS) -> str:
        snippets: List[str] = []
        remaining = max(512, int(max_chars))

        for path in self._resolve_bootstrap_files():
            if remaining <= 200:
                break
            try:
                if not path.exists() or not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore").strip()
                if not text:
                    continue
                excerpt_budget = min(1200, max(120, remaining - 80))
                excerpt = text[:excerpt_budget]
                snippets.append(f"[{path.name}]\n{excerpt}")
                remaining -= len(excerpt) + len(path.name) + 8
            except Exception:
                continue

        # Add latest qualification signal if present.
        try:
            qualification_files = sorted(
                (ROXY_ROOT / "briefings").glob("qualification-day4-day7-*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if qualification_files and remaining > 180:
                payload = json.loads(qualification_files[0].read_text(encoding="utf-8", errors="ignore"))
                qualified = payload.get("qualified")
                summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
                line = (
                    f"[qualification]\nqualified={qualified}; "
                    f"core={summary.get('core_pass_rate')}; "
                    f"adversarial={summary.get('adversarial_pass_rate')}; "
                    f"latency_p95={summary.get('latency_p95_sec')}"
                )
                snippets.append(line[: min(len(line), remaining)])
        except Exception:
            pass

        if not snippets:
            return ""

        return (
            "ULTRAMAX SPAWN BRIEFING (Luno/SKOREQ/Skills):\n"
            + "\n\n".join(snippets)
            + "\n\nApply this context while solving the user's task."
        )

    async def opencode(
        self,
        prompt: str = "",
        action: str = "run",
        mode: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        attach_url: Optional[str] = None,
        password: Optional[str] = None,
        session: Optional[str] = None,
        continue_session: bool = False,
        fork: bool = False,
        agent: Optional[str] = None,
        variant: Optional[str] = None,
        thinking: bool = False,
        files: Optional[List[str]] = None,
        timeout: float = DEFAULT_OPENCODE_TIMEOUT_SEC,
        verbose: bool = False,
        refresh: bool = False,
        dir: Optional[str] = None,
        ultramax: Optional[bool] = None,
        bootstrap: Optional[bool] = None,
        fallback_free: Optional[bool] = None,
        chain_steps: int = 2,
        chain_followup_template: Optional[str] = None,
        chain_stop_prefix: str = "COMPLETE:",
        chain_max_output_chars: int = 6000,
    ) -> ToolResponse:
        """
        Execute OpenCode CLI actions (run/models/providers).

        Default action is `run` and defaults model to free cloud model
        `opencode/mimo-v2-pro-free`.
        """
        opencode_bin = shutil.which("opencode-cli")
        if not opencode_bin:
            return ToolResponse(
                success=False,
                error="opencode-cli not found in PATH",
                tool_name="opencode",
            )

        action = (action or "run").strip().lower()
        cmd: List[str] = [opencode_bin]
        prompt_payload = ""
        ultramax_enabled = self._to_bool(ultramax, ENABLE_OPENCODE_ULTRAMAX)
        bootstrap_enabled = self._to_bool(bootstrap, ENABLE_OPENCODE_BOOTSTRAP)
        fallback_enabled = self._to_bool(fallback_free, ENABLE_OPENCODE_FREE_FALLBACK)

        profile = self._get_profile(mode)
        effective_model = str(model or profile.get("model") or DEFAULT_OPENCODE_MODEL).strip()
        effective_variant = str(variant or "").strip()
        effective_thinking = bool(thinking)

        if ultramax_enabled:
            if not effective_variant:
                effective_variant = str(profile.get("variant") or OPENCODE_DEFAULT_VARIANT).strip()
            if not thinking:
                effective_thinking = bool(profile.get("thinking", True))
            timeout = max(float(timeout), DEFAULT_OPENCODE_TIMEOUT_SEC)

        if action == "chain":
            prompt_text = str(prompt or "").strip()
            if not prompt_text:
                return ToolResponse(
                    success=False,
                    error="opencode chain requires a non-empty prompt",
                    tool_name="opencode",
                )

            max_steps = max(1, min(OPENCODE_CHAIN_MAX_STEPS, int(chain_steps)))
            followup_template = (
                chain_followup_template
                or (
                    "Original task:\n{original_prompt}\n\n"
                    "Prior OpenCode output (step {step_index}):\n{previous_output}\n\n"
                    "Continue the task. If fully complete, begin your response with "
                    f"'{chain_stop_prefix}'."
                )
            )

            step_outputs: List[Dict[str, Any]] = []
            current_prompt = prompt_text
            final_text = ""
            stop_prefix = str(chain_stop_prefix or "COMPLETE:").strip()
            for step_idx in range(1, max_steps + 1):
                run_result = await self.opencode(
                    prompt=current_prompt,
                    action="run",
                    mode=mode,
                    model=model,
                    provider=provider,
                    attach_url=attach_url,
                    password=password,
                    session=session,
                    continue_session=continue_session if step_idx == 1 else True,
                    fork=fork if step_idx == 1 else False,
                    agent=agent,
                    variant=variant,
                    thinking=thinking,
                    files=files,
                    timeout=timeout,
                    dir=dir,
                    ultramax=ultramax_enabled,
                    bootstrap=bootstrap_enabled if step_idx == 1 else False,
                    fallback_free=fallback_enabled,
                )
                step_text = str(run_result.data or "")
                final_text = step_text
                step_outputs.append(
                    {
                        "step": step_idx,
                        "success": bool(run_result.success),
                        "output_preview": step_text[:600],
                        "error": str(run_result.error or "")[:400],
                        "metadata": run_result.metadata,
                    }
                )
                if not run_result.success:
                    return ToolResponse(
                        success=False,
                        data=final_text,
                        error=run_result.error or f"OpenCode chain failed at step {step_idx}",
                        tool_name="opencode",
                        metadata={
                            "action": "chain",
                            "steps_requested": max_steps,
                            "steps_completed": step_idx,
                            "step_outputs": step_outputs,
                        },
                    )

                if stop_prefix and step_text.strip().upper().startswith(stop_prefix.upper()):
                    return ToolResponse(
                        success=True,
                        data=final_text,
                        tool_name="opencode",
                        metadata={
                            "action": "chain",
                            "steps_requested": max_steps,
                            "steps_completed": step_idx,
                            "stopped_by_prefix": stop_prefix,
                            "step_outputs": step_outputs,
                        },
                    )

                current_prompt = followup_template.format(
                    original_prompt=prompt_text,
                    step_index=step_idx,
                    previous_output=step_text[: max(512, int(chain_max_output_chars))],
                )

            return ToolResponse(
                success=True,
                data=final_text,
                tool_name="opencode",
                metadata={
                    "action": "chain",
                    "steps_requested": max_steps,
                    "steps_completed": max_steps,
                    "step_outputs": step_outputs,
                },
            )

        if action == "models":
            cmd.extend(["models"])
            if provider:
                cmd.append(provider.strip())
            if verbose:
                cmd.append("--verbose")
            if refresh:
                cmd.append("--refresh")
        elif action in {"providers", "provider", "providers_list"}:
            cmd.extend(["providers", "list"])
        else:
            prompt_text = str(prompt or "").strip()
            if not prompt_text:
                return ToolResponse(
                    success=False,
                    error="opencode run requires a non-empty prompt",
                    tool_name="opencode",
                )
            if bootstrap_enabled:
                spawn_context = self._build_spawn_boost_context()
                if spawn_context:
                    prompt_text = (
                        f"{spawn_context}\n\n"
                        f"USER TASK:\n{prompt_text}\n\n"
                        "Return actionable output for the task."
                    )
            prompt_payload = prompt_text

        run_dir = str(self._resolve_path(dir)) if dir else self.workdir
        timeout_sec = max(10.0, float(timeout))
        effective_password = str(password or os.getenv("OPENCODE_SERVER_PASSWORD", "")).strip()

        def _build_run_cmd(selected_model: str) -> List[str]:
            run_cmd: List[str] = [opencode_bin, "run", "--format", "json"]
            if selected_model:
                run_cmd.extend(["--model", selected_model])
            if attach_url:
                run_cmd.extend(["--attach", str(attach_url).strip()])
            if effective_password:
                run_cmd.extend(["--password", effective_password])
            if session:
                run_cmd.extend(["--session", str(session).strip()])
            if continue_session:
                run_cmd.append("--continue")
            if fork:
                run_cmd.append("--fork")
            if agent:
                run_cmd.extend(["--agent", str(agent).strip()])
            if effective_variant:
                run_cmd.extend(["--variant", effective_variant])
            if effective_thinking:
                run_cmd.append("--thinking")
            if files:
                for file_item in files:
                    resolved = self._resolve_path(str(file_item))
                    run_cmd.extend(["--file", str(resolved)])
            run_cmd.append(prompt_payload)
            return run_cmd

        attempt_models = [effective_model]
        if action == "run" and fallback_enabled:
            attempt_models = self._build_fallback_model_chain(effective_model)
        attempt_failures: List[Dict[str, Any]] = []

        for attempt_idx, attempt_model in enumerate(attempt_models, start=1):
            attempt_cmd = cmd if action != "run" else _build_run_cmd(attempt_model)
            command_str = " ".join(shlex.quote(x) for x in attempt_cmd)

            try:
                proc = await asyncio.create_subprocess_exec(
                    *attempt_cmd,
                    cwd=run_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            except Exception as e:
                logger.error(f"OpenCode spawn error: {e}")
                return ToolResponse(
                    success=False,
                    error=str(e),
                    tool_name="opencode",
                    metadata={
                        "action": action,
                        "model": attempt_model or effective_model,
                        "attempt": attempt_idx,
                        "attempt_count": len(attempt_models),
                        "command": command_str,
                        "cwd": run_dir,
                    },
                )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                return ToolResponse(
                    success=False,
                    error=f"OpenCode command timed out after {timeout_sec:.1f}s",
                    tool_name="opencode",
                    metadata={
                        "action": action,
                        "model": attempt_model or effective_model,
                        "attempt": attempt_idx,
                        "attempt_count": len(attempt_models),
                        "command": command_str,
                        "cwd": run_dir,
                    },
                )

            stdout_text = (stdout_bytes or b"").decode("utf-8", errors="replace")
            stderr_text = (stderr_bytes or b"").decode("utf-8", errors="replace")
            exit_code = int(proc.returncode or 0)

            if action in {"models", "providers", "provider", "providers_list"}:
                ok = exit_code == 0
                return ToolResponse(
                    success=ok,
                    data=stdout_text.strip(),
                    error="" if ok else (stderr_text.strip() or stdout_text.strip() or f"OpenCode exit code {exit_code}"),
                    tool_name="opencode",
                    metadata={
                        "action": action,
                        "command": command_str,
                        "cwd": run_dir,
                        "exit_code": exit_code,
                    },
                )

            # Parse JSON event stream from opencode run.
            text_parts: List[str] = []
            event_count = 0
            error_events: List[str] = []
            session_id = ""
            finish_reason = ""
            token_usage: Dict[str, Any] = {}

            for raw_line in stdout_text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except Exception:
                    continue
                if not isinstance(event, dict):
                    continue

                event_count += 1
                if event_count > MAX_OPENCODE_EVENTS:
                    break

                event_type = str(event.get("type", ""))
                if not session_id:
                    session_id = str(event.get("sessionID", "") or "")

                if event_type == "text":
                    part = event.get("part", {}) or {}
                    text = str(part.get("text", "") or "")
                    if text:
                        text_parts.append(text)
                elif event_type == "error":
                    error_obj = event.get("error", {}) or {}
                    if isinstance(error_obj, dict):
                        nested = error_obj.get("data", {}) or {}
                        nested_message = nested.get("message", "") if isinstance(nested, dict) else ""
                        message = str(
                            error_obj.get("message")
                            or nested_message
                            or error_obj.get("name")
                            or json.dumps(error_obj)
                        )
                    else:
                        message = str(error_obj)
                    if message:
                        error_events.append(message)
                elif event_type == "step_finish":
                    part = event.get("part", {}) or {}
                    finish_reason = str(part.get("reason", "") or finish_reason)
                    token_usage = part.get("tokens", token_usage) or token_usage

            combined_text = "".join(text_parts).strip()
            if not combined_text and stdout_text.strip():
                combined_text = stdout_text.strip()

            run_error = ""
            if error_events:
                run_error = "\n".join(error_events[:5])
            elif exit_code != 0:
                run_error = stderr_text.strip() or combined_text or f"OpenCode exit code {exit_code}"

            metadata_base = {
                "action": "run",
                "mode": str(mode or DEFAULT_OPENCODE_PROFILE),
                "model": attempt_model or effective_model,
                "requested_model": effective_model,
                "profile_model": profile.get("model"),
                "variant": effective_variant,
                "thinking": bool(effective_thinking),
                "ultramax": bool(ultramax_enabled),
                "bootstrap": bool(bootstrap_enabled),
                "fallback_free": bool(fallback_enabled),
                "attempt": attempt_idx,
                "attempt_count": len(attempt_models),
                "attempt_models": attempt_models,
                "attempt_failures": attempt_failures,
                "session_id": session_id,
                "finish_reason": finish_reason,
                "tokens": token_usage,
                "event_count": event_count,
                "exit_code": exit_code,
                "command": command_str,
                "cwd": run_dir,
            }

            if run_error:
                attempt_failures.append(
                    {
                        "model": attempt_model,
                        "attempt": attempt_idx,
                        "exit_code": exit_code,
                        "error": run_error[:400],
                        "stderr": stderr_text.strip()[:400],
                    }
                )
                if (
                    fallback_enabled
                    and attempt_idx < len(attempt_models)
                    and self._should_use_free_fallback(f"{run_error}\n{stderr_text}")
                ):
                    continue
                return ToolResponse(
                    success=False,
                    data=combined_text,
                    error=run_error,
                    tool_name="opencode",
                    metadata={**metadata_base, "attempt_failures": attempt_failures, "stderr": stderr_text.strip()[:2000]},
                )

            return ToolResponse(
                success=True,
                data=combined_text,
                tool_name="opencode",
                metadata={**metadata_base, "attempt_failures": attempt_failures},
            )

        return ToolResponse(
            success=False,
            error="OpenCode run failed for all configured fallback models",
            tool_name="opencode",
            metadata={
                "action": action,
                "mode": str(mode or DEFAULT_OPENCODE_PROFILE),
                "requested_model": effective_model,
                "attempt_models": attempt_models,
                "attempt_failures": attempt_failures,
                "cwd": run_dir,
            },
        )
    
    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> ToolResponse:
        """Execute a tool by name with arguments."""
        tool_map = {
            "read": self.read_file,
            "write": self.write_file,
            "edit": self.edit_file,
            "glob": self.glob,
            "grep": self.grep,
            "opencode": self.opencode,
        }
        
        if tool_name not in tool_map:
            return ToolResponse(
                success=False,
                error=f"Unknown tool: {tool_name}",
                tool_name=tool_name
            )
        
        return await tool_map[tool_name](**arguments)
    
    def _resolve_path(self, file_path: str) -> Path:
        """Resolve a path relative to workdir or as absolute."""
        path = Path(file_path)
        if path.is_absolute():
            return path
        return Path(self.workdir) / path


async def test_streaming_tools():
    """Test streaming tools."""
    tools = StreamingTools(workdir="/home/mark/.roxy")
    
    print("Test 1: Read file")
    result = await tools.read_file("tool_executor.py", limit=20)
    print(f"  Success: {result.success}")
    print(f"  Lines: {result.metadata.get('lines_read')}")
    
    print("\nTest 2: Write file")
    result = await tools.write_file(
        "/tmp/roxy_test.txt",
        "Hello from ROXY streaming tools!"
    )
    print(f"  Success: {result.success}")
    print(f"  Data: {result.data}")
    
    print("\nTest 3: Edit file")
    result = await tools.edit_file(
        "/tmp/roxy_test.txt",
        "Hello",
        "Hello World!"
    )
    print(f"  Success: {result.success}")
    print(f"  Diff: {result.data.get('diff')[:100] if result.data else 'N/A'}")
    
    print("\nTest 4: Glob")
    result = await tools.glob("*.py", base_path="/home/mark/.roxy", recursive=False)
    print(f"  Success: {result.success}")
    print(f"  Matches: {len(result.data) if result.data else 0} files")
    
    print("\nTest 5: Grep")
    result = await tools.grep(
        "ToolExecutor",
        path="/home/mark/.roxy",
        file_pattern="tool_executor.py"
    )
    print(f"  Success: {result.success}")
    print(f"  Matches: {len(result.data) if result.data else 0}")


if __name__ == "__main__":
    asyncio.run(test_streaming_tools())
