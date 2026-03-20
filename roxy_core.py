#!/usr/bin/env python3
"""
ROXY Core - Always-On Background Service
Runs as systemd user service, no UI, exposes HTTP IPC

Part of LUNA-000 CITADEL - Wayland-correct architecture
"""

import os
import sys
import logging
import signal
import time
import asyncio
import subprocess
import atexit
import uuid
import hashlib
import re
from pathlib import Path
from datetime import datetime, UTC
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, urlparse
import json
from threading import Thread, Lock
from typing import Optional, Tuple, List, Dict, Any, Callable
from collections import defaultdict, deque

# =============================================================================
# ZOMBIE RESURRECTION GUARDRAIL - Added 2026-01-05
# Prevents the lobotomized stub version from ever running
# =============================================================================
_this_file = Path(__file__).resolve()
_this_cwd = Path.cwd().resolve()
_canonical_core = Path.home() / ".roxy" / "roxy_core.py"
_canonical_exec = f"{Path.home()}/.roxy/venv/bin/python {_canonical_core}"

if '/services/' in str(_this_file) or _this_file.name != 'roxy_core.py':
    print(f"FATAL: Refusing to run stub copy. Detected={_this_file} | Required={_canonical_core}", file=sys.stderr)
    sys.exit(99)

_legacy_root = os.environ.get('ROXY_LEGACY_ROOT', '/opt/roxy')
if str(_this_cwd) == _legacy_root:
    print(f"FATAL: CWD is frozen archive /opt/roxy. Required ExecStart={_canonical_exec}", file=sys.stderr)
    sys.exit(99)
# =============================================================================

# Logging setup
LOG_DIR = Path.home() / ".roxy" / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "roxy-core.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("roxy-core")

# -----------------------------------------------------------------------------
# JSON sanitation helpers
# -----------------------------------------------------------------------------
def _json_sanitize(obj):
    """Recursively convert non-JSON-serializable values (e.g., datetime)."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_sanitize(v) for v in obj]
    return obj

# Configuration - single source of truth
ROXY_DIR = Path.home() / ".roxy"
CONFIG_FILE = ROXY_DIR / "config.json"
TOKEN_FILE = ROXY_DIR / "secret.token"

# Default model selection (max-strength Qwen 14B unless explicitly overridden)
DEFAULT_QWEN_MODEL = os.getenv("ROXY_DEFAULT_MODEL", "qwen2.5-coder:14b")
_MODEL_CACHE = {"selected": {}, "models": [], "ts": 0.0}
_MODEL_CACHE_TTL = 60.0


def _score_qwen_model(name: str) -> int:
    lower = name.lower()
    score = 0
    if "qwen3" in lower:
        score += 25
    elif "qwen2.5" in lower:
        score += 15
    if "instruct" in lower:
        score += 50
    if "q6" in lower:
        score += 20
    elif "q5" in lower:
        score += 15
    elif "q4" in lower:
        score += 10
    if "k_m" in lower:
        score += 2
    return score


def _fetch_model_names(base_url: Optional[str]) -> List[str]:
    if not base_url:
        return []
    try:
        import urllib.request
        req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        models = payload.get("models", [])
        names = [m.get("name") for m in models if isinstance(m, dict)]
        return [n for n in names if isinstance(n, str)]
    except Exception:
        return []


def _infer_model_task(query: str, mode: str = "") -> str:
    q = (query or "").lower()
    if mode.upper() == "EXEC":
        return "code"
    code_markers = ("code", "python", "bash", "stack trace", "traceback", "refactor", "unit test", "compile")
    reasoning_markers = ("why", "reason", "analyze", "benchmark", "evaluate", "compare", "tradeoff")
    if any(marker in q for marker in code_markers):
        return "code"
    if any(marker in q for marker in reasoning_markers):
        return "reasoning"
    return "general"


def _score_runtime_model(name: str, task: str = "general") -> int:
    lower = name.lower()
    score = 0
    if "14b" in lower:
        score += 80
    if any(big in lower for big in ("32b", "34b", "70b", "72b")):
        score -= 120
    if "qwen3" in lower:
        score += 30
    if "qwen2.5" in lower:
        score += 20
    if "deepseek-r1" in lower:
        score += 45 if task == "reasoning" else 18
    if "deepcoder" in lower or "coder" in lower:
        score += 50 if task == "code" else 5
    if "instruct" in lower:
        score += 18
    if "q6" in lower:
        score += 16
    elif "q5" in lower:
        score += 12
    elif "q4" in lower:
        score += 8
    if ":latest" in lower:
        score -= 2
    return score


def _select_best_model(base_url: Optional[str], query: str = "", mode: str = "") -> str:
    fallback = DEFAULT_QWEN_MODEL
    names = _fetch_model_names(base_url)
    if not names:
        return fallback

    task = _infer_model_task(query, mode)
    candidates = [n for n in names if "14b" in n.lower()]
    if not candidates:
        candidates = [n for n in names if "qwen" in n.lower()]
    if not candidates:
        return fallback
    candidates.sort(key=lambda name: _score_runtime_model(name, task=task), reverse=True)
    return candidates[0]


def _get_default_model(base_url: Optional[str] = None, query: str = "", mode: str = "") -> str:
    override = os.getenv("ROXY_DEFAULT_MODEL")
    if override:
        return override.strip()
    cache_key = f"{base_url or _get_ollama_base_url()}::{_infer_model_task(query, mode)}"
    now = time.time()
    cached = _MODEL_CACHE.get("selected", {}).get(cache_key)
    if cached and (now - _MODEL_CACHE.get("ts", 0.0) < _MODEL_CACHE_TTL):
        return cached
    selected = _select_best_model(base_url or _get_ollama_base_url(), query=query, mode=mode)
    _MODEL_CACHE.setdefault("selected", {})[cache_key] = selected
    _MODEL_CACHE["ts"] = now
    return selected


_GREETING_PATTERNS = [
    re.compile(r"^(hi|hello|hey|yo|sup|howdy)(\s+roxy)?[!\.\s]*$", re.IGNORECASE),
    re.compile(r"^good\s+(morning|afternoon|evening)(\s+roxy)?[!\.\s]*$", re.IGNORECASE),
    re.compile(r"^(what'?s\s+up|wassup|how'?s\s+it\s+going)(\s+roxy)?[!\.\s]*$", re.IGNORECASE),
]


def _is_pure_greeting(text: str) -> bool:
    if not text:
        return True
    stripped = text.strip()
    if not stripped:
        return True
    for pattern in _GREETING_PATTERNS:
        if pattern.match(stripped):
            return True
    return False


MIN_STREAM_MEMORY_CHARS = int(os.getenv("ROXY_MIN_MEMORY_CHARS", "20"))


def _should_commit_memory(response_text: str) -> bool:
    if not response_text:
        return False
    stripped = response_text.strip()
    if not stripped:
        return False
    if _is_pure_greeting(stripped):
        return False
    if len(stripped) < MIN_STREAM_MEMORY_CHARS:
        return False
    return True


# --------------------------------------------------------------------------
# RCA-003 streaming tool-call execution settings
# --------------------------------------------------------------------------
ENABLE_STREAM_TOOL_CALLS = os.getenv("ROXY_ENABLE_STREAM_TOOL_CALLS", "1").lower() in ("1", "true", "yes")
MAX_STREAM_TOOL_CALLS = max(1, int(os.getenv("ROXY_MAX_STREAM_TOOL_CALLS", "3")))
MAX_STREAM_TOOL_RUNTIME_SEC = max(10.0, float(os.getenv("ROXY_MAX_STREAM_TOOL_RUNTIME_SEC", "90")))
STREAM_TOOL_EXEC_TIMEOUT_SEC = max(5.0, float(os.getenv("ROXY_STREAM_TOOL_EXEC_TIMEOUT_SEC", "30")))
MAX_STREAM_TOOL_DELTA_CHARS = max(128, int(os.getenv("ROXY_MAX_STREAM_TOOL_DELTA_CHARS", "1200")))
MAX_STREAM_TOOL_RESULT_CHARS = max(256, int(os.getenv("ROXY_MAX_STREAM_TOOL_RESULT_CHARS", "8000")))
STREAM_TOOL_AUDIT_FILE = ROXY_DIR / "data" / "tool_audit.jsonl"
STREAM_TOOL_AUDIT_LOCK = Lock()

STREAM_TOOL_ALLOWED = {"bash", "read", "write", "edit", "glob", "grep", "opencode"}
STREAM_TOOL_ALIASES = {
    "execute_command": "bash",
    "read_file": "read",
    "write_file": "write",
    "edit_file": "edit",
    "search_code": "grep",
    "list_files": "glob",
    "opencode_run": "opencode",
    "opencode_chain": "opencode",
}

STREAM_TOOL_DANGEROUS_BASH_PATTERNS = [
    r"(^|\s)rm\s+-rf\s+/",
    r"(^|\s)mkfs(\.| )",
    r"(^|\s)fdisk(\s|$)",
    r"(^|\s)dd\s+if=",
    r"(^|\s)(shutdown|reboot|poweroff|halt)(\s|$)",
    r":\(\)\s*\{",  # fork bomb pattern
]

STREAM_TOOL_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
STREAM_TOOL_INLINE_JSON = re.compile(r"<<tool_call>>\s*(\{.*?\})", re.DOTALL | re.IGNORECASE)
STREAM_TOOL_TAG_PATTERN = re.compile(
    r"<<(bash|read|write|edit|glob|grep|opencode)>>\s*(.*?)\s*<</\1>>",
    re.DOTALL | re.IGNORECASE,
)

MCP_TOOL_PATTERN = re.compile(r"<<mcp_([a-z0-9_-]+)>>\s*(.*?)\s*<</mcp_\1>>", re.DOTALL | re.IGNORECASE)

_MCP_CLIENT_CACHE = None


def _get_mcp_client():
    """Lazy-load MCP client singleton."""
    global _MCP_CLIENT_CACHE
    if _MCP_CLIENT_CACHE is None:
        try:
            from mcp_client import MCPClient
            _MCP_CLIENT_CACHE = MCPClient()
        except ImportError:
            _MCP_CLIENT_CACHE = False
    return _MCP_CLIENT_CACHE


def _truncate_tool_text(text: Any, max_chars: int = MAX_STREAM_TOOL_RESULT_CHARS) -> str:
    value = str(text or "")
    if len(value) <= max_chars:
        return value
    return value[:max_chars] + f"\n...[truncated {len(value) - max_chars} chars]"


def _normalize_stream_tool_call(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return None
    raw_name = str(payload.get("tool") or payload.get("name") or "").strip().lower()
    if not raw_name:
        return None
    name = STREAM_TOOL_ALIASES.get(raw_name, raw_name)
    if name not in STREAM_TOOL_ALLOWED and not name.startswith("mcp_"):
        return None
    arguments = payload.get("args", payload.get("arguments", {}))
    if not isinstance(arguments, dict):
        arguments = {}
    if name == "bash":
        command = arguments.get("command", arguments.get("cmd", ""))
        arguments = {"command": str(command).strip(), **{k: v for k, v in arguments.items() if k not in ("command", "cmd")}}
    return {
        "name": name,
        "arguments": arguments,
        "call_id": str(payload.get("call_id") or payload.get("id") or uuid.uuid4())[:12],
    }


def _extract_stream_tool_calls(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []

    candidates: List[Dict[str, Any]] = []
    seen = set()

    def _add_candidate(candidate: Optional[Dict[str, Any]]) -> None:
        if not candidate:
            return
        signature = json.dumps({"name": candidate["name"], "arguments": candidate["arguments"]}, sort_keys=True)
        if signature in seen:
            return
        seen.add(signature)
        candidates.append(candidate)

    # 1) Tagged tool blocks: <<bash>>...<</bash>>
    for match in STREAM_TOOL_TAG_PATTERN.finditer(text):
        tool_name = match.group(1).strip().lower()
        content = (match.group(2) or "").strip()
        payload = {
            "name": tool_name,
            "arguments": {"command": content} if tool_name == "bash" else {"content": content},
        }
        if tool_name == "read":
            payload["arguments"] = {"file_path": content}
        elif tool_name == "glob":
            payload["arguments"] = {"pattern": content}
        elif tool_name == "grep":
            payload["arguments"] = {"pattern": content}
        elif tool_name == "opencode":
            payload["arguments"] = {"prompt": content}
        _add_candidate(_normalize_stream_tool_call(payload))

    # 1b) MCP tool blocks: <<mcp_<server>_<tool>>>...<</mcp_<server>_<tool>>>
    for match in MCP_TOOL_PATTERN.finditer(text):
        full_name = match.group(1).strip().lower()
        content = (match.group(2) or "").strip()
        try:
            mcp_args = json.loads(content) if content else {}
        except (json.JSONDecodeError, TypeError):
            mcp_args = {"query": content} if content else {}
        payload = {
            "name": f"mcp_{full_name}",
            "arguments": mcp_args,
        }
        _add_candidate(_normalize_stream_tool_call(payload))

    # 2) <<tool_call>>{...}
    for match in STREAM_TOOL_INLINE_JSON.finditer(text):
        candidate = match.group(1)
        try:
            payload = json.loads(candidate)
        except Exception:
            continue
        if isinstance(payload, list):
            for item in payload:
                _add_candidate(_normalize_stream_tool_call(item))
        else:
            _add_candidate(_normalize_stream_tool_call(payload))

    # 3) ```json {...} ```
    for match in STREAM_TOOL_JSON_FENCE.finditer(text):
        candidate = match.group(1)
        try:
            payload = json.loads(candidate)
        except Exception:
            continue
        if isinstance(payload, list):
            for item in payload:
                _add_candidate(_normalize_stream_tool_call(item))
        else:
            _add_candidate(_normalize_stream_tool_call(payload))

    # 4) Raw JSON object fallback (only if no candidates found yet)
    if not candidates:
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                payload = json.loads(stripped)
                _add_candidate(_normalize_stream_tool_call(payload))
            except Exception:
                pass

    return candidates


def _pre_tool_use_policy(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    safety_level = "safe"
    reason = "allowed"
    allowed = True

    if tool_name == "bash":
        safety_level = "guarded"
        command = str(arguments.get("command", "")).strip()
        if not command:
            return {"allow": False, "reason": "missing_command", "safety_level": "guarded"}
        for pattern in STREAM_TOOL_DANGEROUS_BASH_PATTERNS:
            if re.search(pattern, command, flags=re.IGNORECASE):
                return {"allow": False, "reason": f"blocked_pattern:{pattern}", "safety_level": "dangerous"}
        if command.startswith("sudo "):
            return {"allow": False, "reason": "sudo_blocked", "safety_level": "dangerous"}

    if tool_name in {"write", "edit"}:
        safety_level = "guarded"
        file_path = arguments.get("file_path") or arguments.get("path") or ""
        file_path = str(file_path).strip()
        if not file_path:
            return {"allow": False, "reason": "missing_file_path", "safety_level": "guarded"}
        try:
            candidate = Path(file_path).expanduser()
            resolved = candidate if candidate.is_absolute() else (ROXY_DIR / candidate).resolve()
            roots = [Path.home().resolve(), ROXY_DIR.resolve()]
            if not any(str(resolved).startswith(str(root)) for root in roots):
                return {"allow": False, "reason": "path_outside_allowed_roots", "safety_level": "dangerous"}
        except Exception:
            return {"allow": False, "reason": "path_resolution_failed", "safety_level": "guarded"}

    if tool_name == "opencode":
        safety_level = "guarded"
        action = str(arguments.get("action", "run")).strip().lower()
        if action in {"models", "providers", "provider", "providers_list"}:
            return {"allow": True, "reason": "allowed", "safety_level": safety_level}
        prompt = str(arguments.get("prompt", "")).strip()
        if not prompt:
            return {"allow": False, "reason": "missing_prompt", "safety_level": "guarded"}
        # Keep OpenCode prompts bounded to reduce runaway remote token spend.
        if len(prompt) > 8000:
            return {"allow": False, "reason": "prompt_too_large", "safety_level": "guarded"}

    if tool_name.startswith("mcp_"):
        safety_level = "guarded"
        parts = tool_name.split("_", 2)
        if len(parts) >= 3:
            server = parts[1]
            mcp_read_only_servers = {"desktop", "voice", "obs", "content"}
            if server not in mcp_read_only_servers:
                allowed = True

    return {"allow": allowed, "reason": reason, "safety_level": safety_level}


def _append_tool_audit(record: Dict[str, Any]) -> None:
    try:
        STREAM_TOOL_AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = _json_sanitize(record)
        with STREAM_TOOL_AUDIT_LOCK:
            with STREAM_TOOL_AUDIT_FILE.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except Exception as exc:
        logger.debug(f"Tool audit append failed (non-critical): {exc}")


def _write_tool_failure_memory(record: Dict[str, Any]) -> None:
    """Persist failed tool executions as typed memory for future repair loops."""
    if not INFRASTRUCTURE_AVAILABLE or not record or record.get("status") != "failed":
        return
    try:
        tool_name = str(record.get("tool_name") or "unknown")
        error_message = str(record.get("error") or record.get("reason") or "tool_failed")
        arguments = record.get("arguments", {}) or {}
        command = str(arguments.get("command") or "")
        metadata = {
            "request_id": record.get("request_id"),
            "session_id": record.get("session_id"),
            "call_id": record.get("call_id"),
            "safety_level": record.get("safety_level"),
            "reason": record.get("reason"),
            "duration": record.get("duration"),
            "exit_code": record.get("exit_code"),
            "arguments": arguments,
        }
        remember_typed_record(
            "failure_event",
            f"{tool_name}: {error_message}",
            metadata=metadata,
            provenance="tool_runtime",
            user_id=record.get("user_id"),
            scope=tool_name,
        )
        if tool_name == "bash" and command:
            remember_typed_record(
                "bug",
                f"Bash tool failure: {command}\n{error_message}",
                metadata=metadata,
                provenance="tool_runtime",
                user_id=record.get("user_id"),
                scope=tool_name,
            )
    except Exception as exc:
        logger.debug(f"Tool failure memory write failed (non-critical): {exc}")

    try:
        from learning_loop import record_failure as learning_record_failure

        arguments = record.get("arguments", {}) or {}
        command_hint = str(arguments.get("command") or "")[:120]
        learning_record_failure(
            tool_name=str(record.get("tool_name") or "unknown"),
            error_type=str(record.get("reason") or "tool_failed"),
            error_message=str(record.get("error") or ""),
            command_hint=command_hint,
        )
    except Exception as exc:
        logger.debug(f"Learning loop record failed (non-critical): {exc}")


ENABLE_SECRET_SCAN_PREFLIGHT = os.getenv("ROXY_ENABLE_SECRET_SCAN_PREFLIGHT", "1").lower() in ("1", "true", "yes")
SECRET_SCAN_DRY_RUN = os.getenv("ROXY_SECRET_SCAN_DRY_RUN", "1").lower() in ("1", "true", "yes")
SECRET_SCAN_INTERVAL_SEC = max(10, int(os.getenv("ROXY_SECRET_SCAN_INTERVAL_SEC", "300")))
SECRET_SCAN_ROOT = Path(os.getenv("ROXY_SECRET_SCAN_ROOT", str(ROXY_DIR))).expanduser()
SECRET_SCAN_MIN_SEVERITY = os.getenv("ROXY_SECRET_SCAN_MIN_SEVERITY", "high").lower()
SECRET_SCAN_BACKGROUND = os.getenv("ROXY_SECRET_SCAN_BACKGROUND", "1").lower() in ("1", "true", "yes")
SECRET_SCAN_FORCE_TIMEOUT_SEC = max(0.2, float(os.getenv("ROXY_SECRET_SCAN_FORCE_TIMEOUT_SEC", "1.5")))
ENABLE_MISSION_PREFLIGHT_GATE = os.getenv("ROXY_ENABLE_MISSION_PREFLIGHT_GATE", "1").lower() in ("1", "true", "yes")
MISSION_BLOCK_ON_DEGRADED = os.getenv("ROXY_MISSION_BLOCK_ON_DEGRADED", "0").lower() in ("1", "true", "yes")

_SECRET_SCAN_CACHE: Dict[str, Any] = {"ts": 0.0, "result": {}}
_SECRET_SCAN_LOCK = Lock()
_SECRET_SCAN_THREAD: Optional[Thread] = None
_SECRET_SCAN_RUNNING = False


def _secret_scan_pending_payload(reason: str = "pending") -> Dict[str, Any]:
    return {
        "enabled": True,
        "passed": True,
        "blocked": False,
        "dry_run": SECRET_SCAN_DRY_RUN,
        "root": str(SECRET_SCAN_ROOT),
        "violations": 0,
        "critical": 0,
        "high": 0,
        "error": "",
        "pending": True,
        "pending_reason": reason,
    }


def _execute_secret_scan() -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "enabled": True,
        "passed": True,
        "blocked": False,
        "dry_run": SECRET_SCAN_DRY_RUN,
        "root": str(SECRET_SCAN_ROOT),
        "violations": 0,
        "critical": 0,
        "high": 0,
        "error": "",
        "pending": False,
    }
    try:
        from secret_scanner import SecretScanner, Severity

        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
        }
        scanner = SecretScanner(
            dry_run=SECRET_SCAN_DRY_RUN,
            min_severity=severity_map.get(SECRET_SCAN_MIN_SEVERITY, Severity.HIGH),
        )
        result = scanner.scan_workspace(str(SECRET_SCAN_ROOT))
        payload.update(
            {
                "passed": bool(result.passed),
                "blocked": bool(result.blocked),
                "violations": len(result.violations),
                "critical": sum(
                    1
                    for v in result.violations
                    if str(getattr(getattr(v, "severity", None), "value", "")).lower() == "critical"
                ),
                "high": sum(
                    1
                    for v in result.violations
                    if str(getattr(getattr(v, "severity", None), "value", "")).lower() == "high"
                ),
                "duration_ms": round(float(result.scan_duration_ms), 1),
            }
        )
        if result.error_message:
            payload["error"] = str(result.error_message)
    except Exception as exc:
        payload["passed"] = False
        payload["blocked"] = False
        payload["error"] = f"secret_scan_unavailable: {exc}"
    return payload


def _secret_scan_worker():
    global _SECRET_SCAN_RUNNING
    try:
        payload = _execute_secret_scan()
        with _SECRET_SCAN_LOCK:
            _SECRET_SCAN_CACHE["ts"] = time.time()
            _SECRET_SCAN_CACHE["result"] = payload
    finally:
        with _SECRET_SCAN_LOCK:
            _SECRET_SCAN_RUNNING = False


def _run_secret_scan_preflight(force: bool = False) -> Dict[str, Any]:
    """
    Run cached secret scan preflight and return structured status.

    Default behavior is non-blocking on the request path:
    - If cache is fresh, return cache
    - If stale and background mode enabled, trigger background scan and return
      cached result (or pending payload if no cache yet)
    - Force mode performs a bounded synchronous scan and degrades to pending if timeout
    """
    global _SECRET_SCAN_THREAD, _SECRET_SCAN_RUNNING
    now = time.time()

    with _SECRET_SCAN_LOCK:
        cached = _SECRET_SCAN_CACHE.get("result") or {}
        cache_age = now - float(_SECRET_SCAN_CACHE.get("ts", 0.0))
        if not force and cached and cache_age < SECRET_SCAN_INTERVAL_SEC:
            return cached

    # /missions/run can request force=True; keep bounded to avoid hanging API threads.
    if force:
        done = {"payload": None}

        def _target():
            done["payload"] = _execute_secret_scan()

        worker = Thread(target=_target, daemon=True)
        worker.start()
        worker.join(timeout=SECRET_SCAN_FORCE_TIMEOUT_SEC)
        if worker.is_alive():
            with _SECRET_SCAN_LOCK:
                cached = _SECRET_SCAN_CACHE.get("result") or {}
            return cached or _secret_scan_pending_payload("force_timeout")

        payload = done.get("payload") or _secret_scan_pending_payload("force_no_result")
        with _SECRET_SCAN_LOCK:
            _SECRET_SCAN_CACHE["ts"] = time.time()
            _SECRET_SCAN_CACHE["result"] = payload
        return payload

    if SECRET_SCAN_BACKGROUND:
        with _SECRET_SCAN_LOCK:
            running = _SECRET_SCAN_RUNNING
            if not running:
                _SECRET_SCAN_RUNNING = True
                _SECRET_SCAN_THREAD = Thread(target=_secret_scan_worker, daemon=True)
                _SECRET_SCAN_THREAD.start()
            cached = _SECRET_SCAN_CACHE.get("result") or {}
        return cached or _secret_scan_pending_payload("background_warmup")

    payload = _execute_secret_scan()
    with _SECRET_SCAN_LOCK:
        _SECRET_SCAN_CACHE["ts"] = time.time()
        _SECRET_SCAN_CACHE["result"] = payload
    return payload


MAX_MEMORY_CONTEXT_CHARS = int(os.getenv("ROXY_MEMORY_CONTEXT_MAX_CHARS", "2200"))
MAX_MEMORY_SNIPPET_CHARS = int(os.getenv("ROXY_MEMORY_SNIPPET_CHARS", "220"))
MAX_MEMORY_RECALL_ITEMS = int(os.getenv("ROXY_MEMORY_RECALL_ITEMS", "5"))
MAX_PROFILE_ITEMS = int(os.getenv("ROXY_PROFILE_ITEMS", "8"))
MIN_MEMORY_RECALL_SCORE = float(os.getenv("ROXY_MEMORY_RECALL_MIN_SCORE", "0.20"))
MIN_MEMORY_RECALL_SIMILARITY = float(os.getenv("ROXY_MEMORY_RECALL_MIN_SIMILARITY", "0.18"))
MIN_MEMORY_RECALL_LEXICAL = float(os.getenv("ROXY_MEMORY_RECALL_MIN_LEXICAL", "0.12"))
ENABLE_AGENTIC_PIPELINE = os.getenv("ROXY_ENABLE_AGENTIC_PIPELINE", "1").lower() in ("1", "true", "yes")
ENABLE_PROACTIVE_HINTS = os.getenv("ROXY_ENABLE_PROACTIVE_HINTS", "1").lower() in ("1", "true", "yes")
MAX_AGENTIC_PLAN_STEPS = int(os.getenv("ROXY_MAX_AGENTIC_PLAN_STEPS", "6"))
GOAL_TRACKER_LIMIT = int(os.getenv("ROXY_GOAL_TRACKER_LIMIT", "12"))
_USER_ID_SANITIZE = re.compile(r"[^a-zA-Z0-9_.:-]+")
try:
    from canonical_identity import CANONICAL_USER_ID  # type: ignore
except Exception:
    CANONICAL_USER_ID = "default"

DEFAULT_ROXY_USER_ID = (
    os.getenv("ROXY_USER_ID")
    or os.getenv("ROXY_DEFAULT_USER_ID")
    or os.getenv("ROXY_CANONICAL_USER_ID")
    or str(CANONICAL_USER_ID)
    or "default"
)

_AMBIGUOUS_REFERENCE_PATTERN = re.compile(
    r"\b(it|those|them|do that|do this|fix it|make it better)\b",
    re.IGNORECASE,
)
_PROFILE_QUERY_PATTERN = re.compile(
    r"\b(my name|who am i|how old am i|my age|what do i like|what do i dislike|remember about me|my preference)\b",
    re.IGNORECASE,
)
_MEMORY_MISS_PATTERN = re.compile(
    r"(no mention|cannot answer|can(?: ?')?t answer|not (?:provided|available)|given context|doesn(?: ?')?t contain|insufficient context)",
    re.IGNORECASE,
)
_GOAL_INTRO_PATTERN = re.compile(r"\b(i need to|i want to|my goal is|help me|please help)\b", re.IGNORECASE)
_ACTION_SPLIT_PATTERN = re.compile(r"\b(?:and then|and|then|after that|next|,|;)\b", re.IGNORECASE)
_INTENT_KEYWORDS = {
    "diagnose": ("error", "failing", "not working", "broken", "unstable"),
    "optimize": ("optimize", "improve", "speed", "latency", "benchmark", "score"),
    "implement": ("build", "implement", "add", "create", "upgrade"),
    "operate": ("run", "start", "restart", "status", "health", "open"),
}

_SESSION_GOALS: Dict[str, Dict[str, Any]] = {}
_SESSION_GOALS_LOCK = Lock()


def _sanitize_user_id(candidate: Optional[str]) -> str:
    cleaned = _USER_ID_SANITIZE.sub("-", str(candidate or "").strip())
    return cleaned or _USER_ID_SANITIZE.sub("-", str(DEFAULT_ROXY_USER_ID).strip()) or "default"


def _resolve_request_user_id(
    headers: Optional[Dict[str, str]] = None,
    payload_user_id: Optional[str] = None,
) -> str:
    header_user_id = None
    if headers:
        header_user_id = headers.get("X-ROXY-User-Id") or headers.get("X-ROXY-User")
    return _sanitize_user_id(payload_user_id or header_user_id or DEFAULT_ROXY_USER_ID)


def _verify_and_enhance_response(
    query: str,
    response_text: str,
    memory_context: str,
    truth_packet: str
) -> tuple[str, dict]:
    """
    Verify response for hallucinations and add confidence warnings.
    Returns (enhanced_response, verification_metadata).
    """
    verification = {
        "confidence": 1.0,
        "flags": [],
        "needs_reflection": False,
        "verified": True,
    }
    
    try:
        sys.path.insert(0, str(ROXY_DIR))
        from reflection import get_reflection_verifier
        verifier = get_reflection_verifier()
        verification = verifier.verify_response(
            query=query,
            response=response_text,
            memory_context=memory_context,
            truth_packet=truth_packet
        )
        
        # Add confidence warning to response if needed
        if verification.get("needs_reflection"):
            enhanced = verifier.add_confidence_warning(verification, response_text)
            return enhanced, verification
        
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Response verification failed (non-critical): {e}")
    
    return response_text, verification


# Configuration for retry behavior
ENABLE_REFLECTION_RETRY = os.getenv("ROXY_ENABLE_REFLECTION_RETRY", "1").lower() in ("1", "true", "yes")
REFLECTION_RETRY_THRESHOLD = float(os.getenv("ROXY_REFLECTION_RETRY_THRESHOLD", "0.7"))
REFLECTION_MAX_RETRIES = int(os.getenv("ROXY_REFLECTION_MAX_RETRIES", "2"))


def _regenerate_with_memory_first(
    query: str,
    session_id: str,
    memory_context: str,
    model: str = "qwen2.5-coder:14b-instruct"
) -> tuple[str, dict]:
    """
    Regenerate response with explicit memory-first prompting.
    Used when initial response has low confidence.
    
    Returns:
        (regenerated_response, regeneration_metadata)
    """
    meta = {
        "regenerated": True,
        "method": "memory_first_retry",
        "prompt_injected": bool(memory_context),
    }
    
    if not memory_context:
        meta["error"] = "no_memory_context"
        return "", meta
    
    try:
        # Build enhanced memory-first prompt
        enhanced_prompt = f"""You are ROXY, the MindSong Studios CEO AI. Answer based ONLY on the memory provided below.

MEMORY (use this first, it contains user facts and preferences):
{memory_context}

CRITICAL INSTRUCTIONS:
1. If the user asks about themselves (name, preferences, history), answer from MEMORY only
2. Do NOT say "I don't know" or "based on context" if MEMORY contains the answer
3. State facts directly: "Your name is Mark" not "Based on memory, your name is Mark"
4. If MEMORY does not contain the answer, say "I don't have that information in my memory"

User: {query}

Answer:"""
        
        # Call LLM directly
        import requests
        base_url = _get_ollama_base_url()
        resp = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": enhanced_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Lower temp for factual responses
                    "num_predict": 500
                }
            },
            timeout=30
        )
        
        if resp.status_code == 200:
            result = resp.json().get("response", "").strip()
            meta["success"] = True
            return result, meta
        else:
            meta["error"] = f"llm_error:{resp.status_code}"
            meta["success"] = False
            return "", meta
            
    except Exception as e:
        meta["error"] = str(e)
        meta["success"] = False
        return "", meta


def _verify_and_enhance_with_retry(
    query: str,
    response_text: str,
    memory_context: str,
    truth_packet: str,
    session_id: str,
    model: str = "qwen2.5-coder:14b-instruct"
) -> tuple[str, dict]:
    """
    Verify response, regenerate if confidence is low, and return best result.
    Implements true retry loop for hallucination prevention.
    """
    # Initial verification
    result, verification = _verify_and_enhance_response(
        query, response_text, memory_context, truth_packet
    )
    
    # If confidence is acceptable, return as-is
    if verification.get("confidence", 1.0) >= REFLECTION_RETRY_THRESHOLD:
        verification["retry_performed"] = False
        return result, verification
    
    # Confidence is low - check if retries are enabled
    if not ENABLE_REFLECTION_RETRY:
        verification["retry_performed"] = False
        verification["retry_skipped"] = "disabled"
        return result, verification
    
    # Attempt regeneration with memory-first prompt
    logger.info(f"Low confidence ({verification.get('confidence')}), attempting memory-first regeneration...")
    
    for attempt in range(REFLECTION_MAX_RETRIES):
        # Regenerate with explicit memory injection
        regenerated, regen_meta = _regenerate_with_memory_first(
            query, session_id, memory_context, model
        )
        
        if not regenerated:
            verification["retry_performed"] = True
            verification["regeneration_attempts"] = attempt + 1
            verification["regeneration_failed"] = True
            break
        
        # Verify the regenerated response
        result, verification = _verify_and_enhance_response(
            query, regenerated, memory_context, truth_packet
        )
        
        # Check if confidence improved
        if verification.get("confidence", 0) >= REFLECTION_RETRY_THRESHOLD:
            verification["retry_performed"] = True
            verification["regeneration_attempts"] = attempt + 1
            verification["regeneration_improved"] = True
            logger.info(f"Regeneration improved confidence to {verification.get('confidence')}")
            return result, verification
        
        logger.debug(f"Regeneration attempt {attempt + 1} still low confidence: {verification.get('confidence')}")
    
    # All retries exhausted or failed
    verification["retry_performed"] = True
    verification["regeneration_attempts"] = REFLECTION_MAX_RETRIES
    verification["regeneration_exhausted"] = True
    
    # Add warning about low confidence
    try:
        from reflection import get_reflection_verifier
        verifier = get_reflection_verifier()
        result = verifier.add_confidence_warning(verification, result)
    except:
        pass
    
    return result, verification


def _trim_text(value: str, max_len: int = 200) -> str:
    text = (value or "").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "..."


def _build_memory_context_for_prompt(
    query: str,
    session_id: Optional[str],
    user_id: Optional[str] = None,
) -> tuple[str, dict]:
    """
    Build prompt-ready episodic memory + profile block.
    Returns (context_block, metadata).
    """
    meta = {
        "enabled": False,
        "memory_items": 0,
        "profile_items": 0,
        "typed_record_items": 0,
        "repo_context_items": 0,
        "context_chars": 0,
        "query_rewritten": False,
        "user_id": _sanitize_user_id(user_id),
    }

    memories = []
    profile = []
    typed_records = []

    if INFRASTRUCTURE_AVAILABLE:
        # Apply query rewriting for better retrieval
        try:
            from query_rewriting import rewrite_query_for_retrieval
            rewritten_query, query_meta = rewrite_query_for_retrieval(query)
            meta["query_rewritten"] = query_meta.get("rewritten") != query
            meta["query_entities"] = query_meta.get("entities", [])
            if meta["query_rewritten"]:
                logger.debug(f"Query rewritten: '{query}' -> '{rewritten_query}'")
                query = rewritten_query
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Query rewriting failed: {e}")

        try:
            memories = recall_conversations(
                query,
                k=MAX_MEMORY_RECALL_ITEMS,
                session_id=session_id,
                user_id=meta["user_id"],
                min_score=MIN_MEMORY_RECALL_SCORE,
                min_similarity=MIN_MEMORY_RECALL_SIMILARITY,
            ) or []

            # If session-scoped recall is sparse, blend in global recall for cross-session continuity.
            if len(memories) < 2:
                global_memories = recall_conversations(
                    query,
                    k=MAX_MEMORY_RECALL_ITEMS,
                    user_id=meta["user_id"],
                    min_score=max(MIN_MEMORY_RECALL_SCORE - 0.04, 0.0),
                    min_similarity=max(MIN_MEMORY_RECALL_SIMILARITY - 0.05, 0.0),
                ) or []
                seen = set()
                merged = []
                for m in memories + global_memories:
                    key = (
                        m.get("id"),
                        m.get("query"),
                        m.get("created_at"),
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    merged.append(m)
                memories = merged[:MAX_MEMORY_RECALL_ITEMS]
        except Exception as e:
            logger.debug(f"Memory recall context build failed: {e}")
            memories = []

        try:
            profile = get_user_profile(limit=MAX_PROFILE_ITEMS, user_id=meta["user_id"]) or []
        except Exception as e:
            logger.debug(f"Profile context build failed: {e}")
            profile = []

        try:
            typed_records = get_typed_records(
                query=query,
                limit=4,
                user_id=meta["user_id"],
            ) or []
        except Exception as e:
            logger.debug(f"Typed memory context build failed: {e}")
            typed_records = []

    sections = []
    if memories:
        filtered_memories = []
        for memory in memories:
            try:
                score = float(memory.get("score", 0.0))
            except Exception:
                score = 0.0
            try:
                similarity = float(memory.get("similarity", 0.0))
            except Exception:
                similarity = 0.0
            try:
                lexical_overlap = float(memory.get("lexical_overlap", 0.0))
            except Exception:
                lexical_overlap = 0.0
            if (
                score >= MIN_MEMORY_RECALL_SCORE
                or similarity >= MIN_MEMORY_RECALL_SIMILARITY
                or lexical_overlap >= MIN_MEMORY_RECALL_LEXICAL
            ):
                filtered_memories.append(memory)
        if not filtered_memories:
            filtered_memories = memories[: min(len(memories), 2)]

        lines = []
        for idx, memory in enumerate(filtered_memories[:MAX_MEMORY_RECALL_ITEMS], start=1):
            q = _trim_text(memory.get("query", ""), max_len=120)
            r = _trim_text(memory.get("response", ""), max_len=MAX_MEMORY_SNIPPET_CHARS)
            lines.append(f"{idx}. User: {q}")
            lines.append(f"   ROXY: {r}")
        sections.append("Relevant past conversation snippets:\n" + "\n".join(lines))
        meta["memory_items"] = len(filtered_memories[:MAX_MEMORY_RECALL_ITEMS])

    if profile:
        identity_values = []
        lines = []
        for item in profile[:MAX_PROFILE_ITEMS]:
            category = item.get("category", "general")
            preference = item.get("preference", "")
            if not preference:
                continue
            if category in {"name", "preferred_name"}:
                identity_values.append(str(preference).strip().lower())
            confidence = item.get("confidence")
            if confidence is None:
                lines.append(f"- {category}: {preference}")
            else:
                try:
                    lines.append(f"- {category}: {preference} (confidence {float(confidence):.2f})")
                except Exception:
                    lines.append(f"- {category}: {preference}")
        if lines:
            sections.append("Learned user profile facts/preferences:\n" + "\n".join(lines))
            meta["profile_items"] = len(lines)
        unique_identity_values = sorted({v for v in identity_values if v})
        if len(unique_identity_values) > 1:
            meta["identity_conflict"] = True
            meta["identity_candidates"] = unique_identity_values
            logger.warning(
                "Identity conflict detected user_id=%s candidates=%s",
                meta["user_id"],
                unique_identity_values,
            )
        elif unique_identity_values:
            meta["identity_conflict"] = False
            meta["identity_candidates"] = unique_identity_values

    if typed_records:
        typed_lines = []
        for idx, record in enumerate(typed_records[:4], start=1):
            record_type = record.get("record_type", "record")
            content = _trim_text(record.get("content", ""), max_len=MAX_MEMORY_SNIPPET_CHARS)
            typed_lines.append(f"{idx}. [{record_type}] {content}")
        if typed_lines:
            sections.append("Relevant typed operational memory:\n" + "\n".join(typed_lines))
            meta["typed_record_items"] = len(typed_lines)

    repo_context, repo_meta = _build_repo_context_for_prompt(query)
    if repo_context:
        sections.append(repo_context)
        meta["repo_context_items"] = int(repo_meta.get("repo_context_items", 0))

    if not sections:
        return "", meta

    context_block = (
        "EPISODIC MEMORY CONTEXT (cross-session, use only when relevant):\n"
        + "\n\n".join(sections)
    )
    context_block = _trim_text(context_block, max_len=MAX_MEMORY_CONTEXT_CHARS)
    meta["enabled"] = True
    meta["context_chars"] = len(context_block)
    return context_block, meta


_REPO_FILE_CANDIDATE_RE = re.compile(
    r"(?<![\w/])([A-Za-z0-9_./-]+\.(?:py|ts|tsx|js|jsx|mjs|cjs|json|md|sh|ya?ml|toml|css|scss|html|go|rs))(?![\w/])"
)
_REPO_SYMBOL_CANDIDATE_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]{2,})\b")
_REPO_SYMBOL_STOPWORDS = {
    "what", "when", "where", "which", "with", "from", "into", "have", "that",
    "this", "there", "their", "about", "would", "could", "should", "please",
    "need", "show", "file", "files", "class", "function", "method", "repo",
    "code", "test", "tests", "edit", "fix", "line", "lines", "path", "paths",
    "roxy", "mindsong", "juke", "hub", "write", "read", "does", "make", "work",
}


def _build_repo_context_for_prompt(query: str, max_items: int = 4) -> tuple[str, dict]:
    """Build a compact RepoIntel context block from file/symbol mentions in the query."""
    meta = {"repo_context_items": 0, "repo_file_items": 0, "repo_symbol_items": 0}
    if not REPO_INTEL_AVAILABLE or not query:
        return "", meta

    lowered = query.lower()
    query_looks_repo_related = any(
        marker in lowered
        for marker in ("file", "files", "class", "function", "method", "symbol", "repo", "code", "test", "import", "module")
    )

    file_candidates = []
    for raw in _REPO_FILE_CANDIDATE_RE.findall(query):
        candidate = raw.strip().strip("`'\"()[]{}:,")
        if candidate and candidate not in file_candidates:
            file_candidates.append(candidate)

    try:
        idx = get_repo_index()
    except Exception as e:
        logger.debug(f"RepoIntel index unavailable for prompt context: {e}")
        return "", meta

    symbol_candidates = []
    if idx:
        for raw in _REPO_SYMBOL_CANDIDATE_RE.findall(query):
            token = raw.strip()
            if not token or token.lower() in _REPO_SYMBOL_STOPWORDS:
                continue
            if token.lower() in getattr(idx, "symbol_index", {}):
                symbol_candidates.append(token)
                continue
            # Prefer symbol-like names over generic prose.
            if "_" in token or any(ch.isupper() for ch in token[1:]):
                matches = query_symbol(token)
                if matches:
                    symbol_candidates.append(token)
            if len(symbol_candidates) >= max_items:
                break

    if not query_looks_repo_related and not file_candidates and not symbol_candidates:
        return "", meta

    lines: List[str] = []
    seen_files = set()
    for candidate in file_candidates[:max_items]:
        normalized = candidate.lstrip("./")
        try:
            repo_root = Path(getattr(idx, "root", REPO_INTEL_DEFAULT_REPO))
            if Path(candidate).is_absolute():
                normalized = str(Path(candidate).resolve().relative_to(repo_root))
        except Exception:
            pass
        file_context = get_file_context(normalized)
        if not file_context:
            continue
        path_key = file_context.get("path")
        if not path_key or path_key in seen_files:
            continue
        seen_files.add(path_key)
        symbol_names = ", ".join(sym.get("name", "") for sym in file_context.get("symbols", [])[:4] if sym.get("name"))
        test_names = ", ".join(file_context.get("tests", [])[:2]) or "none"
        summary = f"- file {path_key} [{file_context.get('language', 'unknown')}]"
        if symbol_names:
            summary += f", symbols: {symbol_names}"
        summary += f", tests: {test_names}"
        lines.append(summary)
        meta["repo_file_items"] += 1
        if len(lines) >= max_items:
            break

    seen_symbol_hits = set()
    for symbol in symbol_candidates[:max_items]:
        for hit in query_symbol(symbol)[:2]:
            key = (hit.get("file"), hit.get("line"), hit.get("symbol"))
            if key in seen_symbol_hits:
                continue
            seen_symbol_hits.add(key)
            lines.append(
                f"- symbol {hit.get('symbol')} ({hit.get('kind', 'symbol')}) -> "
                f"{hit.get('file')}:{hit.get('line')}"
            )
            meta["repo_symbol_items"] += 1
            if len(lines) >= max_items:
                break
        if len(lines) >= max_items:
            break

    if not lines:
        return "", meta

    meta["repo_context_items"] = len(lines)
    return "Relevant repository context:\n" + "\n".join(lines), meta


def _run_command_capture(cmd: List[str], cwd: Optional[Path] = None, timeout: float = 5.0) -> str:
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode == 0:
            return (result.stdout or "").strip()
        return ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    except Exception:
        return ""


def _read_json_if_exists(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        return None
    return None


def _list_listening_ports(limit: int = 12) -> List[int]:
    output = _run_command_capture(["ss", "-ltnH"], timeout=3.0)
    ports: List[int] = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        local = parts[3].strip()
        port_text = local.rsplit(":", 1)[-1].strip("[]")
        if port_text.isdigit():
            port_value = int(port_text)
            if port_value not in ports:
                ports.append(port_value)
        if len(ports) >= limit:
            break
    return ports


def _get_runtime_state_snapshot() -> Dict[str, Any]:
    """Collect a compact runtime/workspace snapshot for operators and prompts."""
    repo_root = Path(os.getenv("ROXY_REPO_ROOT", str(REPO_INTEL_DEFAULT_REPO))).expanduser()
    state: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "repo": {
            "root": str(repo_root),
            "exists": repo_root.exists(),
        },
        "scheduler": {
            "heartbeat": _read_json_if_exists(ROXY_DIR / "data" / "scheduler_heartbeat.json"),
            "lease": _read_json_if_exists(ROXY_DIR / "data" / "scheduler_lease.json"),
        },
        "missions": {},
        "tool_retry": {},
        "listeners": _list_listening_ports(),
    }

    if repo_root.exists():
        branch = _run_command_capture(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root, timeout=5.0)
        dirty = _run_command_capture(
            ["git", "status", "--short", "--untracked-files=normal"],
            cwd=repo_root,
            timeout=8.0,
        )
        dirty_lines = [line for line in dirty.splitlines() if line.strip()]
        state["repo"].update({
            "branch": branch or None,
            "dirty_files": len(dirty_lines),
            "dirty_preview": dirty_lines[:20],
        })

    if REPO_INTEL_AVAILABLE:
        try:
            idx = get_repo_index(repo_root=repo_root)
            state["repo_intel"] = {
                "root": getattr(idx, "root", str(repo_root)),
                "file_count": getattr(idx, "file_count", 0),
                "symbol_count": len(getattr(idx, "symbol_index", {}) or {}),
                "language_stats": getattr(idx, "language_stats", {}),
                "built_at": datetime.fromtimestamp(getattr(idx, "built_at", time.time())).isoformat(),
                "stale": bool(idx.is_stale()) if idx else True,
            }
        except Exception as e:
            state["repo_intel"] = {"error": str(e)}
    else:
        state["repo_intel"] = {"error": "not_available"}

    try:
        from mission_supervisor import get_ledger
        ledger = get_ledger()
        active = ledger.get_active()
        state["missions"] = {
            "stats": ledger.get_stats(),
            "active": active.to_dict() if active else None,
        }
    except Exception as e:
        state["missions"] = {"error": str(e)}

    try:
        from tool_retry import get_retry_controller
        state["tool_retry"] = get_retry_controller().get_stats()
    except Exception as e:
        state["tool_retry"] = {"error": str(e)}

    return state


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _infer_intent(query: str) -> str:
    lowered = (query or "").lower()
    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return intent
    if "?" in lowered:
        return "question"
    return "general"


def _is_complex_query(query: str) -> bool:
    cleaned = _normalize_text(query)
    if not cleaned:
        return False
    words = cleaned.split()
    if len(words) >= 16:
        return True
    if len(_ACTION_SPLIT_PATTERN.split(cleaned)) >= 3:
        return True
    complexity_markers = ("first", "second", "third", "step", "pipeline", "end-to-end")
    return any(marker in cleaned.lower() for marker in complexity_markers)


def _build_plan_steps(query: str, limit: int = MAX_AGENTIC_PLAN_STEPS) -> List[str]:
    lowered = _normalize_text(query).lower()
    if not lowered:
        return []

    if "benchmark" in lowered or "score" in lowered:
        plan = [
            "Establish baseline metrics from current benchmark harness.",
            "Identify worst-performing categories and map to concrete code paths.",
            "Apply targeted fixes and model/runtime tuning.",
            "Re-run benchmark suite and compare deltas by metric.",
        ]
    elif any(token in lowered for token in ("error", "failing", "broken", "not working", "unstable")):
        plan = [
            "Capture current failure symptoms and reproducible signals.",
            "Isolate likely root-cause components from logs and health checks.",
            "Apply minimal corrective changes with rollback-safe scope.",
            "Validate fix with direct smoke tests and regression checks.",
        ]
    elif any(token in lowered for token in ("implement", "build", "add", "upgrade")):
        plan = [
            "Define scope and acceptance criteria for requested capability.",
            "Implement smallest high-leverage code changes first.",
            "Add tests for new behavior and edge cases.",
            "Verify runtime behavior in live service path.",
        ]
    else:
        plan = [
            "Clarify the target outcome and constraints.",
            "Execute the highest-impact action first.",
            "Validate result quality and reliability.",
        ]

    return plan[: max(1, int(limit))]


def _analyze_agentic_request(query: str) -> Dict[str, Any]:
    cleaned = _normalize_text(query)
    lowered = cleaned.lower()
    is_complex = _is_complex_query(cleaned)
    has_ambiguous_ref = bool(_AMBIGUOUS_REFERENCE_PATTERN.search(cleaned))
    noun_anchors = ("roxy", "model", "service", "memory", "benchmark", "repo", "file", "gpu", "command center")
    anchored = any(anchor in lowered for anchor in noun_anchors)
    needs_clarification = has_ambiguous_ref and not anchored and len(cleaned.split()) <= 14
    clarifying_question = ""
    if needs_clarification:
        clarifying_question = "Can you specify exactly what 'it/that' refers to (service, file, model, or workflow)?"

    return {
        "intent": _infer_intent(cleaned),
        "complex": is_complex,
        "needs_clarification": needs_clarification,
        "clarifying_question": clarifying_question,
        "plan_steps": _build_plan_steps(cleaned) if is_complex else [],
    }


def _response_indicates_memory_miss(response_text: str) -> bool:
    if not response_text:
        return True
    return bool(_MEMORY_MISS_PATTERN.search(response_text))


def _should_attempt_memory_rescue(query: str, response_text: str, memory_context: str) -> bool:
    if not memory_context:
        return False
    if not _PROFILE_QUERY_PATTERN.search(query or ""):
        return False
    return _response_indicates_memory_miss(response_text)


def _build_proactive_suggestions(query: str) -> List[str]:
    lowered = (query or "").lower()
    suggestions: List[str] = []

    if any(token in lowered for token in ("benchmark", "score", "performance", "latency")):
        suggestions.extend([
            "Run a fresh benchmark baseline before and after each change to track measurable deltas.",
            "Tune context length and quantization per model to balance quality and throughput on GPU.",
        ])
    if any(token in lowered for token in ("error", "failing", "broken", "not working", "unstable")):
        suggestions.extend([
            "Capture a timestamped health snapshot and the latest service logs for root-cause clarity.",
            "Validate the fix with a minimal reproducible command before broader testing.",
        ])
    if any(token in lowered for token in ("install", "setup", "upgrade", "update")):
        suggestions.extend([
            "Pin versions for critical dependencies and record them in service metadata.",
            "Add a smoke-test endpoint check after installation to prevent silent startup failures.",
        ])

    deduped: List[str] = []
    seen = set()
    for item in suggestions:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:3]


def _append_proactive_suggestions(query: str, result_text: str) -> tuple[str, List[str]]:
    if not ENABLE_PROACTIVE_HINTS:
        return result_text, []
    if not result_text:
        return result_text, []
    if "Recommended next steps:" in result_text:
        return result_text, []

    suggestions = _build_proactive_suggestions(query)
    if not suggestions:
        return result_text, []

    lines = [result_text.rstrip(), "", "Recommended next steps:"]
    for idx, item in enumerate(suggestions, start=1):
        lines.append(f"{idx}. {item}")
    return "\n".join(lines), suggestions


def _update_goal_tracker(session_id: str, query: str, result_text: str):
    if not session_id:
        return
    cleaned = _normalize_text(query)
    if not cleaned:
        return
    completed = bool(re.search(r"\b(done|completed|resolved|fixed)\b", result_text or "", re.IGNORECASE))
    with _SESSION_GOALS_LOCK:
        state = _SESSION_GOALS.setdefault(session_id, {"active": deque(maxlen=GOAL_TRACKER_LIMIT), "history": deque(maxlen=GOAL_TRACKER_LIMIT)})
        if _GOAL_INTRO_PATTERN.search(cleaned):
            state["active"].append(cleaned)
        if completed and state["active"]:
            goal = state["active"].popleft()
            state["history"].append(goal)


def _goal_tracker_summary(session_id: str) -> Dict[str, int]:
    if not session_id:
        return {"active_goals": 0, "completed_goals": 0}
    with _SESSION_GOALS_LOCK:
        state = _SESSION_GOALS.get(session_id, {})
        active = state.get("active") or []
        history = state.get("history") or []
        return {"active_goals": len(active), "completed_goals": len(history)}


def _normalize_base_url(url: str | None) -> str | None:
    """Normalize localhost variants and strip trailing slash."""
    if not url:
        return url
    normalized = url.replace("localhost", "127.0.0.1").replace("[::1]", "127.0.0.1")
    return normalized.rstrip('/')


# Pool identity helpers (normalize pool aliases, read env overrides)
try:
    sys.path.insert(0, str(ROXY_DIR))
    from pool_identity import normalize_pool_key, get_pool_url  # type: ignore
    POOL_IDENTITY_AVAILABLE = True
except ImportError:
    POOL_IDENTITY_AVAILABLE = False

    def normalize_pool_key(pool_requested: str) -> tuple[str, str]:
        key = (pool_requested or "auto").lower()
        return pool_requested, key

    def get_pool_url(pool_key: str) -> tuple[str, bool]:
        canonical = (pool_key or "w5700x").lower()
        env_var = f"ROXY_OLLAMA_{canonical.upper()}_URL"
        env_value = os.getenv(env_var) or ""
        if env_value:
            return (_normalize_base_url(env_value) or env_value, True)
        port_defaults = {"w5700x": 11434, "6900xt": 11435}
        port = port_defaults.get(canonical, 11435)
        return (f"http://127.0.0.1:{port}", False)


def _infer_gpu_lane(base_url: Optional[str]) -> Optional[str]:
    if not base_url:
        return None
    normalized = _normalize_base_url(base_url) or base_url
    pool_config = _resolve_ollama_pools()
    lane_map = {
        "6900XT": _normalize_base_url(pool_config.get("6900xt", {}).get("url")),
        "W5700X": _normalize_base_url(pool_config.get("w5700x", {}).get("url")),
    }
    for lane, url in lane_map.items():
        if url and normalized.startswith(url):
            return lane
    if "11435" in normalized:
        return "6900XT"
    if "11434" in normalized:
        return "W5700X"
    return None


# Service bridge for advanced services (optional)
try:
    sys.path.insert(0, str(ROXY_DIR))
    from adapters.service_bridge import (
        check_services_availability,
        is_advanced_mode,
        get_availability_report
    )
    SERVICE_BRIDGE_AVAILABLE = True
except ImportError:
    SERVICE_BRIDGE_AVAILABLE = False
    logger.debug("Service bridge not available, using basic mode")

# Import Prometheus metrics (graceful fallback)
try:
    from prometheus_metrics import (
        init_prometheus, MetricsMiddleware,
        record_rag_query, record_cache_hit, record_cache_miss,
        record_ollama_call, record_blocked_command, record_rate_limit,
        record_pool_status, record_ready_check,
        is_available as prometheus_available,
        export_metrics,
    )
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.debug("Prometheus metrics not available")
METRICS_BOOT_WARNING_EMITTED = False

# Truth Gate for response validation (prevent hallucinations)
try:
    sys.path.insert(0, str(ROXY_DIR))
    from truth_gate import get_truth_gate
    TRUTH_GATE_AVAILABLE = True
    logger.info("✅ Truth Gate initialized (hallucination prevention)")
except ImportError:
    TRUTH_GATE_AVAILABLE = False
    logger.debug("Truth Gate not available, responses unvalidated")

# Infrastructure Integration (Redis, PostgreSQL, NATS, Expert Router)
try:
    sys.path.insert(0, str(ROXY_DIR))
    from infrastructure import (
        initialize_infrastructure,
        get_infrastructure_status,
        get_cache, get_memory, get_router, get_event_stream, get_feedback,
        cache_query, get_cached_response,
        remember_conversation, recall_conversations,
        learn_user_facts, get_user_profile,
        remember_typed_record, get_typed_records,
        route_query, classify_query,
        publish_event, publish_query_event, publish_response_event,
        record_feedback, get_feedback_stats, get_all_stats
    )
    INFRASTRUCTURE_AVAILABLE = True
    # Initialize all infrastructure on import
    _infra_status = initialize_infrastructure()
    logger.info(f"✅ Infrastructure initialized: {sum(_infra_status.values())}/{len(_infra_status)} components")
    require_postgres = os.getenv("ROXY_MEMORY_REQUIRE_POSTGRES", "0").lower() in ("1", "true", "yes")
    if require_postgres and not _infra_status.get("postgres_memory", False):
        raise RuntimeError("ROXY_MEMORY_REQUIRE_POSTGRES=1 but postgres_memory is unavailable")
except ImportError as e:
    INFRASTRUCTURE_AVAILABLE = False
    logger.warning(f"⚠️ Infrastructure not available: {e}")

    def initialize_infrastructure(): return {}

    def get_infrastructure_status(): return {'initialized': False}

    def get_cache(): return None

    def get_memory(): return None

    def get_router(): return None

    def get_event_stream(): return None

    def get_feedback(): return None

    def cache_query(*args, **kwargs): pass

    def get_cached_response(*args, **kwargs): return None

    def remember_conversation(*args, **kwargs): pass

    def recall_conversations(*args, **kwargs): return []

    def learn_user_facts(*args, **kwargs): return {"learned": [], "count": 0}

    def get_user_profile(*args, **kwargs): return []

    def route_query(*args, **kwargs): return ""

    def classify_query(*args, **kwargs): return ('general', 0.5)

    def publish_event(*args, **kwargs): pass

    def publish_query_event(*args, **kwargs): pass

    def publish_response_event(*args, **kwargs): pass

    def record_feedback(*args, **kwargs): pass

    def get_feedback_stats(): return {}

    def get_all_stats(): return {}

    def remember_typed_record(*args, **kwargs): return None

    def get_typed_records(*args, **kwargs): return []

# Repo intelligence integration
try:
    sys.path.insert(0, str(ROXY_DIR))
    from repo_intel import (
        DEFAULT_REPO as REPO_INTEL_DEFAULT_REPO,
        get_repo_index,
        get_file_context,
        query_symbol,
    )
    REPO_INTEL_AVAILABLE = True
except ImportError as e:
    REPO_INTEL_AVAILABLE = False
    logger.warning(f"⚠️ RepoIntel not available: {e}")

    REPO_INTEL_DEFAULT_REPO = Path.home() / "work" / "mindsong_gh_https_1769765834"

    def get_repo_index(*args, **kwargs): return None

    def get_file_context(*args, **kwargs): return {}

    def query_symbol(*args, **kwargs): return []

# Load config
if CONFIG_FILE.exists():
    with open(CONFIG_FILE) as f:
        config = json.load(f)
        IPC_HOST = config.get("host", "127.0.0.1")
        IPC_PORT = int(os.getenv("ROXY_PORT", config.get("port", 8766)))
else:
    IPC_HOST = "127.0.0.1"
    IPC_PORT = int(os.getenv("ROXY_PORT", 8766))
    logger.warning(f"Config file not found at {CONFIG_FILE}, using defaults")

# Load auth token - MANDATORY FOR SECURITY
if TOKEN_FILE.exists():
    AUTH_TOKEN = TOKEN_FILE.read_text().strip()
    if not AUTH_TOKEN:
        logger.error("FATAL: Auth token file exists but is empty")
        logger.error("Set token in ~/.roxy/secret.token or AUTH_TOKEN environment variable")
        logger.error("Generate token: python3 -c 'import secrets; print(secrets.token_urlsafe(32))'")
        sys.exit(1)
    logger.info("✓ Auth token loaded")
elif os.getenv("AUTH_TOKEN"):
    AUTH_TOKEN = os.getenv("AUTH_TOKEN").strip()
    if not AUTH_TOKEN:
        logger.error("FATAL: AUTH_TOKEN environment variable is empty")
        sys.exit(1)
    logger.info("✓ Auth token loaded from environment")
else:
    logger.error("FATAL: AUTH_TOKEN not configured - authentication is MANDATORY")
    logger.error("Set token in ~/.roxy/secret.token or AUTH_TOKEN environment variable")
    logger.error("Generate token: python3 -c 'import secrets; print(secrets.token_urlsafe(32))'")
    logger.error("Security policy: System will not start without authentication")
    sys.exit(1)  # FAIL FAST - DO NOT START WITHOUT AUTH

# Global semaphore to limit concurrent subprocess executions (prevent system overload)
import threading
import urllib.request
import urllib.error

MAX_CONCURRENT_SUBPROCESSES = 3  # Allow max 3 simultaneous roxy_commands.py processes
subprocess_semaphore = threading.Semaphore(MAX_CONCURRENT_SUBPROCESSES)

# Track pool logging state (prevent log spam)
_POOL_LOG_STATE = {
    "single_pool": False,
    "misconfigured": False,
}


def _resolve_ollama_pools() -> dict:
    """Resolve configured Ollama pool endpoints with safety checks."""
    single_pool_mode = os.getenv("ROXY_SINGLE_POOL", "").lower() in ("1", "true", "yes")
    forced_unified = _normalize_base_url(os.getenv("ROXY_SINGLE_POOL_URL") or None)
    default_override = _normalize_base_url(os.getenv("ROXY_OLLAMA_DEFAULT_URL") or None)

    default_url = default_override or _normalize_base_url(os.getenv("OLLAMA_HOST") or None) or "http://127.0.0.1:11435"

    w5700x_url, w5700x_configured = get_pool_url("w5700x")
    xt6900_url, xt6900_configured = get_pool_url("6900xt")

    w5700x_url = _normalize_base_url(w5700x_url) or f"http://127.0.0.1:11434"
    xt6900_url = _normalize_base_url(xt6900_url) or f"http://127.0.0.1:11435"

    if single_pool_mode:
        unified_url = forced_unified or default_override
        if not unified_url:
            unified_url = w5700x_url if w5700x_configured else None
        if not unified_url:
            unified_url = xt6900_url if xt6900_configured else None
        unified_url = _normalize_base_url(unified_url) or default_url

        w5700x_url = xt6900_url = unified_url
        default_url = unified_url
        w5700x_configured = xt6900_configured = True

        if not _POOL_LOG_STATE["single_pool"]:
            logger.info(f"SINGLE-POOL MODE: Both pools unified to {unified_url} (intentional)")
            _POOL_LOG_STATE["single_pool"] = True

    misconfigured = False
    if w5700x_url and xt6900_url and w5700x_url == xt6900_url and not single_pool_mode:
        misconfigured = True
        if not _POOL_LOG_STATE["misconfigured"]:
            logger.error(f"POOL MISCONFIGURATION: W5700X and 6900XT point to same endpoint: {w5700x_url}")
            _POOL_LOG_STATE["misconfigured"] = True

    return {
        "w5700x": {"url": w5700x_url, "configured": bool(w5700x_configured)},
        "6900xt": {"url": xt6900_url, "configured": bool(xt6900_configured)},
        "default": default_url,
        "misconfigured": misconfigured,
        "single_pool": single_pool_mode,
    }

def _check_ollama_reachability(url: str, timeout: float = 1.0) -> dict:
    """Check if Ollama URL is reachable. Returns {reachable: bool, latency_ms: float|None, error: str|None}"""
    if not url:
        return {"reachable": False, "latency_ms": None, "error": "no url configured"}
    
    try:
        import urllib.request
        start = time.time()
        req = urllib.request.Request(f"{url}/api/version", method="GET")  # /api/version is lighter than /api/tags
        req.add_header("User-Agent", "roxy-core/reachability-check")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            latency_ms = round((time.time() - start) * 1000, 2)
            return {"reachable": resp.status == 200, "latency_ms": latency_ms, "error": None}
    except Exception as e:
        return {"reachable": False, "latency_ms": None, "error": str(e)}


def _get_ollama_base_url() -> str:
    """Resolve Ollama base URL via authentic pool resolution."""
    return _resolve_ollama_pools()["default"]


# Global startup config validation result (set at boot)
STARTUP_CONFIG_VALIDATION = None

def validate_startup_config() -> dict:
    """
    Comprehensive startup configuration validation.
    Runs at boot and caches result. /ready uses this for config health.

    Returns:
        {
            "valid": bool,
            "errors": [str],
            "warnings": [str],
            "config_summary": {
                "auth_token": bool,
                "pools": {...},
                "log_path": str,
                "port": int,
            }
        }
    """
    global STARTUP_CONFIG_VALIDATION

    errors = []
    warnings = []

    # 1. AUTH_TOKEN (already fails fast at module load, but double-check)
    auth_ok = bool(AUTH_TOKEN)
    if not auth_ok:
        errors.append("AUTH_TOKEN not configured")

    # 2. Pool configuration
    pools = _resolve_ollama_pools()
    single_pool_mode = os.getenv("ROXY_SINGLE_POOL", "").lower() in ("1", "true", "yes")
    if pools["misconfigured"]:
        errors.append(f"Pool misconfiguration: W5700X and 6900XT point to same endpoint")
    if single_pool_mode:
        warnings.append("SINGLE-POOL MODE active: all requests route to unified endpoint")
    if not pools["w5700x"]["configured"]:
        warnings.append("W5700X pool not explicitly configured (using default)")
    if not pools["6900xt"]["configured"]:
        warnings.append("6900XT pool not explicitly configured (using default)")

    # 3. Log directory
    log_dir = Path.home() / ".roxy" / "logs"
    log_path = str(log_dir / "roxy-core.log")
    if not log_dir.exists():
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create log directory: {e}")

    # 4. Proofs directory
    proofs_dir = Path.home() / ".roxy" / "proofs"
    if not proofs_dir.exists():
        try:
            proofs_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            warnings.append(f"Cannot create proofs directory: {e}")

    # 5. Config file
    config_file = Path.home() / ".roxy" / "config.json"
    if not config_file.exists():
        warnings.append("config.json not found, using defaults")

    # Build result
    result = {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "config_summary": {
            "auth_token": auth_ok,
            "pools": {
                "w5700x": pools["w5700x"]["url"],
                "6900xt": pools["6900xt"]["url"],
                "default": pools["default"],
                "misconfigured": pools["misconfigured"],
            },
            "log_path": log_path,
            "port": IPC_PORT,
            "host": IPC_HOST,
        },
        "validated_at": datetime.now().isoformat(),
    }

    # Log summary at startup
    logger.info("=" * 50)
    logger.info("STARTUP CONFIG VALIDATION")
    logger.info("=" * 50)
    logger.info(f"Auth token: {'OK' if auth_ok else 'MISSING'}")
    logger.info(f"W5700X pool: {pools['w5700x']['url'] or 'not configured'}")
    logger.info(f"6900XT pool: {pools['6900xt']['url'] or 'not configured'}")
    logger.info(f"Default pool: {pools['default']}")
    logger.info(f"Port: {IPC_PORT}")
    if errors:
        for err in errors:
            logger.error(f"CONFIG ERROR: {err}")
    if warnings:
        for warn in warnings:
            logger.warning(f"CONFIG WARNING: {warn}")
    logger.info(f"Config valid: {result['valid']}")
    logger.info("=" * 50)

    # Cache for /ready
    STARTUP_CONFIG_VALIDATION = result
    return result


OLLAMA_HEALTH_LOCK = threading.Lock()
_ollama_health_state = {
    "last_ok_ts": None,
    "last_error": None,
    "last_latency_ms": None,
}


def _record_ollama_success(latency_ms: float) -> None:
    with OLLAMA_HEALTH_LOCK:
        _ollama_health_state["last_ok_ts"] = int(time.time())
        _ollama_health_state["last_latency_ms"] = round(latency_ms, 2)
        _ollama_health_state["last_error"] = None


def _record_ollama_error(message: str) -> None:
    with OLLAMA_HEALTH_LOCK:
        _ollama_health_state["last_error"] = message.strip()[:300] if message else ""
        _ollama_health_state["last_latency_ms"] = None


def _snapshot_ollama_health() -> dict:
    with OLLAMA_HEALTH_LOCK:
        return dict(_ollama_health_state)


# ========== GITHUB STATUS CACHE ==========
# Simple in-memory cache to prevent UI refresh loops from rate-limit chewing

GITHUB_STATUS_CACHE_LOCK = threading.Lock()
_github_status_cache = {
    "data": None,
    "timestamp": 0,
    "ttl": 60  # 60 seconds cache TTL
}

def _get_cached_github_status() -> Optional[dict]:
    """Get cached GitHub status if still valid."""
    with GITHUB_STATUS_CACHE_LOCK:
        if _github_status_cache["data"] and (time.time() - _github_status_cache["timestamp"]) < _github_status_cache["ttl"]:
            return _github_status_cache["data"]
    return None

def _cache_github_status(status: dict) -> None:
    """Cache GitHub status."""
    with GITHUB_STATUS_CACHE_LOCK:
        _github_status_cache["data"] = status
        _github_status_cache["timestamp"] = time.time()


# ========== GITHUB API FUNCTIONS ==========
# Read-only GitHub API integration for repo awareness

def _is_placeholder_token(token: Optional[str]) -> bool:
    """Check if token is a placeholder (not real)."""
    if not token:
        return True
    # Common placeholder patterns
    placeholder_patterns = [
        "EXAMPLE", "REPLACE", "FAKE", "TEST", "PLACEHOLDER",
        "YOUR", "ACTUAL", "ghp_EXAMPLE", "ghp_FAKE"
    ]
    token_upper = token.upper()
    return any(pattern in token_upper for pattern in placeholder_patterns)

def _get_github_token() -> Optional[str]:
    """Get GitHub token from environment/config/file

    Priority order:
    1. GITHUB_TOKEN env var (preferred)
    2. GITHUB_PAT env var (alternative)
    3. ~/.roxy/github.token file
    4. config.json github.token

    Returns None if token is placeholder/fake.
    """
    # Check environment first (preferred)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PAT")
    if token and not _is_placeholder_token(token):
        return token

    # Check dedicated token file
    token_file = ROXY_DIR / "github.token"
    if token_file.exists():
        try:
            token = token_file.read_text().strip()
            if token and not _is_placeholder_token(token):
                return token
        except Exception as e:
            logger.debug(f"Failed to read GitHub token from file: {e}")

    # Check config file
    config_file = ROXY_DIR / "config.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
                token = config_data.get("github", {}).get("token")
                if token and not _is_placeholder_token(token):
                    return token
        except Exception as e:
            logger.debug(f"Failed to read GitHub token from config: {e}")

    return None


def _check_github_reachability(token: Optional[str] = None, timeout: float = 2.0) -> dict:
    """Check if GitHub API is reachable. Returns {reachable: bool, latency_ms: float|None, error: str|None, rate_limit: dict|None}
    Uses 60s cache to prevent rate-limit spam from UI refresh loops."""
    
    # Check cache first
    cached = _get_cached_github_status()
    if cached:
        return cached
    
    try:
        import requests
        
        headers = {"User-Agent": "roxy-core/github-check"}
        if token:
            headers["Authorization"] = f"token {token}"
        
        start = time.time()
        # Use rate limit endpoint which is lightweight
        resp = requests.get("https://api.github.com/rate_limit", headers=headers, timeout=timeout)
        latency_ms = round((time.time() - start) * 1000, 2)
        
        # Extract rate limit from response body (more reliable than headers)
        rate_data = {}
        if resp.status_code == 200:
            try:
                rate_data = resp.json().get("rate", {})
            except:
                pass
        
        rate_limit = {
            "limit": rate_data.get("limit") or resp.headers.get("X-RateLimit-Limit"),
            "remaining": rate_data.get("remaining") or resp.headers.get("X-RateLimit-Remaining"),
            "reset": rate_data.get("reset") or resp.headers.get("X-RateLimit-Reset"),
            "used": rate_data.get("used") or resp.headers.get("X-RateLimit-Used")
        }
        
        result = {
            "reachable": resp.status_code == 200,
            "latency_ms": latency_ms,
            "error": None if resp.status_code == 200 else f"HTTP {resp.status_code}",
            "rate_limit": rate_limit
        }
        
        # Cache successful and failed results
        _cache_github_status(result)
        return result
        
    except Exception as e:
        return {
            "reachable": False,
            "latency_ms": None,
            "error": str(e),
            "rate_limit": None
        }


def _get_github_user_info(token: Optional[str] = None) -> dict:
    """Get authenticated user info from GitHub API"""
    try:
        import requests
        
        headers = {"User-Agent": "roxy-core/github-user"}
        if token:
            headers["Authorization"] = f"token {token}"
        
        resp = requests.get("https://api.github.com/user", headers=headers, timeout=5)
        resp.raise_for_status()
        
        user_data = resp.json()
        return {
            "login": user_data.get("login"),
            "name": user_data.get("name"),
            "type": user_data.get("type"),
            "public_repos": user_data.get("public_repos"),
            "private_repos": user_data.get("total_private_repos", 0)
        }
    except Exception as e:
        return {"error": str(e)}


def _github_api_call(endpoint: str, token: Optional[str] = None, params: dict = None, timeout: float = 10.0) -> dict:
    """Make a GitHub API call with proper error handling"""
    try:
        import requests

        url = f"https://api.github.com{endpoint}"
        headers = {"User-Agent": "roxy-core/github-api"}
        if token:
            headers["Authorization"] = f"token {token}"

        resp = requests.get(url, headers=headers, params=params, timeout=timeout)
        resp.raise_for_status()
        
        return {
            "success": True,
            "data": resp.json(),
            "rate_limit": {
                "limit": resp.headers.get("X-RateLimit-Limit"),
                "remaining": resp.headers.get("X-RateLimit-Remaining"),
                "reset": resp.headers.get("X-RateLimit-Reset")
            }
        }
    except requests.exceptions.HTTPError as e:
        return {
            "success": False,
            "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            "rate_limit": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "rate_limit": None
        }


# ========== GITHUB ENDPOINT CACHE ==========
# Unified cache for all GitHub endpoints to prevent rate limit abuse

GITHUB_CACHE_LOCK = threading.Lock()
_github_cache = {}  # key -> {data, timestamp, ttl}

GITHUB_CACHE_TTL = {
    "repos": 120,      # 2 min - repo list changes rarely
    "repo": 120,       # 2 min - single repo
    "issues": 60,      # 1 min - issues change more often
    "pulls": 60,       # 1 min - PRs change often
    "contents": 300,   # 5 min - file contents stable
    "status": 60       # 1 min - rate limit status
}

def _github_cache_key(endpoint: str, params: dict = None) -> str:
    """Generate cache key for GitHub endpoint."""
    param_str = "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
    return f"{endpoint}?{param_str}" if param_str else endpoint

def _github_cache_get(cache_key: str, endpoint_type: str) -> Optional[dict]:
    """Get cached GitHub response if valid."""
    with GITHUB_CACHE_LOCK:
        entry = _github_cache.get(cache_key)
        if entry:
            ttl = GITHUB_CACHE_TTL.get(endpoint_type, 60)
            if time.time() - entry["timestamp"] < ttl:
                return entry["data"]
    return None

def _github_cache_set(cache_key: str, data: dict) -> None:
    """Cache GitHub response."""
    with GITHUB_CACHE_LOCK:
        _github_cache[cache_key] = {
            "data": data,
            "timestamp": time.time()
        }
        # LRU eviction if cache grows too large
        if len(_github_cache) > 100:
            oldest_key = min(_github_cache.keys(), key=lambda k: _github_cache[k]["timestamp"])
            del _github_cache[oldest_key]

def _get_default_repo() -> Optional[dict]:
    """Get default repo from environment or config."""
    # Check environment
    repo_str = os.environ.get("GITHUB_DEFAULT_REPO", "")
    if repo_str and "/" in repo_str:
        parts = repo_str.split("/")
        logger.debug(f"Using default repo from env: {repo_str}")
        return {"owner": parts[0], "repo": parts[1], "ref": os.environ.get("GITHUB_DEFAULT_REF", "main")}

    # Check config
    gh_config = config.get("github", {})
    if gh_config.get("default_owner") and gh_config.get("default_repo"):
        return {
            "owner": gh_config["default_owner"],
            "repo": gh_config["default_repo"],
            "ref": gh_config.get("default_ref", "main")
        }

    return None

def _github_api_cached(endpoint: str, endpoint_type: str, token: Optional[str] = None, params: dict = None) -> dict:
    """Make GitHub API call with caching."""
    cache_key = _github_cache_key(endpoint, params)
    
    # Check cache
    cached = _github_cache_get(cache_key, endpoint_type)
    if cached:
        cached["_cached"] = True
        return cached
    
    # Make API call
    result = _github_api_call(endpoint, token, params)
    
    # Cache successful results
    if result.get("success"):
        result["_cached"] = False
        _github_cache_set(cache_key, result)
    
    return result


def query_ollama_direct(prompt: str, model: Optional[str] = None,
                        temperature: float = 0.0, max_tokens: int = 512,
                        timeout: int = 60) -> str:
    """Query Ollama directly, bypassing all ROXY layers.
    
    Used for benchmarks and technical mode where raw model output is needed.
    """
    try:
        data = json.dumps({
            "model": model or _get_default_model(),
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }).encode()
        
        req = urllib.request.Request(
            f"{_get_ollama_base_url().rstrip('/')}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            return result.get('response', '')
            
    except urllib.error.URLError as e:
        logger.error(f"Ollama connection failed: {e}")
        return f"ERROR: Ollama unavailable - {e}"
    except Exception as e:
        logger.error(f"Direct Ollama query failed: {e}")
        return f"ERROR: {e}"

UNAUTHORIZED_LOG_WINDOW = 60  # seconds
UNAUTHORIZED_LOG_LIMIT = 1
UNAUTHORIZED_RATE_WINDOW = 120  # seconds
UNAUTHORIZED_RATE_LIMIT = 5
_unauthorized_log_tracker = defaultdict(deque)
_unauthorized_rate_tracker = defaultdict(deque)


def _register_unauthorized_attempt(address: str, user_agent: str) -> Tuple[bool, bool]:
    """Track unauthorized attempts and determine logging/rate limits."""
    key = (address, user_agent or "unknown")
    now = time.time()

    log_queue = _unauthorized_log_tracker[key]
    while log_queue and now - log_queue[0] > UNAUTHORIZED_LOG_WINDOW:
        log_queue.popleft()
    should_log = len(log_queue) < UNAUTHORIZED_LOG_LIMIT
    log_queue.append(now)

    rate_queue = _unauthorized_rate_tracker[key]
    while rate_queue and now - rate_queue[0] > UNAUTHORIZED_RATE_WINDOW:
        rate_queue.popleft()
    rate_queue.append(now)
    rate_limited = len(rate_queue) > UNAUTHORIZED_RATE_LIMIT

    return should_log, rate_limited


class RoxyCoreHandler(BaseHTTPRequestHandler):
    """HTTP handler for ROXY core IPC"""
    
    def _safe_write(self, payload: str, request_id: Optional[str] = None) -> bool:
        """Write to client safely, handling disconnects without noise."""
        try:
            self.wfile.write(payload.encode())
            self.wfile.flush()
            return True
        except (BrokenPipeError, ConnectionResetError):
            rid = request_id or "unknown"
            logger.info(f"[STREAM] client disconnected requestId={rid}")
            return False

    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info("%s - %s" % (self.address_string(), format % args))
    
    def do_GET(self):
        """Health check and streaming endpoints"""
        # Support both versioned and unversioned paths
        path = self.path.split('?')[0]  # Remove query string
        
        if path == "/health" or path == "/v1/health":
            self._handle_health_check()
        elif path == "/ready" or path == "/v1/ready":
            self._handle_ready_check()
        elif path == "/version" or path == "/v1/version":
            self._handle_version()
        elif path == "/metrics" or path == "/v1/metrics":
            self._handle_metrics()
        elif path == "/modes" or path == "/v1/modes":
            self._handle_list_modes()
        elif path == "/infrastructure" or path == "/v1/infrastructure":
            self._handle_infrastructure_status()
        elif path == "/infrastructure/stats" or path == "/v1/infrastructure/stats":
            self._handle_infrastructure_stats()
        elif path == "/feedback/stats" or path == "/v1/feedback/stats":
            self._handle_feedback_stats()
        elif path == "/info" or path == "/v1/info":
            self._handle_info()
        elif path == "/auth/status" or path == "/v1/auth/status":
            self._handle_auth_status()
        elif path == "/github/status" or path == "/v1/github/status":
            self._handle_github_status()
        elif path == "/github/repos" or path == "/v1/github/repos":
            self._handle_github_repos()
        elif path == "/github/repo" or path == "/v1/github/repo":
            self._handle_github_repo()
        elif path == "/github/issues" or path == "/v1/github/issues":
            self._handle_github_issues()
        elif path in ("/github/pulls", "/github/prs", "/v1/github/pulls", "/v1/github/prs"):
            self._handle_github_pulls()
        elif path.startswith("/github/contents") or path.startswith("/v1/github/contents"):
            self._handle_github_contents()
        elif path.startswith("/stream") or path.startswith("/v1/stream"):
            # Streaming endpoint (SSE)
            self._handle_streaming()
        # Benchmark endpoints (PHASE 1 - lm-eval harness wrapper)
        elif path == "/bench/status" or path == "/v1/bench/status":
            self._handle_bench_status()
        elif path == "/bench/history" or path == "/v1/bench/history":
            self._handle_bench_history()
        elif path == "/bench/artifact" or path == "/v1/bench/artifact":
            self._handle_bench_artifact()
        elif path == "/bench/tasks" or path == "/v1/bench/tasks":
            self._handle_bench_tasks()
        elif path == "/stories" or path == "/v1/stories":
            self._handle_stories()
        elif path == "/stories/next" or path == "/v1/stories/next":
            self._handle_story_next()
        elif path == "/stories/status" or path == "/v1/stories/status":
            self._handle_story_status()
        elif path == "/scheduler/status" or path == "/v1/scheduler/status":
            self._handle_scheduler_status()
        elif path == "/debug/benchmarks" or path == "/v1/debug/benchmarks":
            self._handle_debug_benchmarks()
        elif path == "/debug/failures" or path == "/v1/debug/failures":
            self._handle_debug_failures()
        elif path == "/debug/runtime-state" or path == "/v1/debug/runtime-state":
            self._handle_debug_runtime_state()
        elif path == "/missions" or path == "/v1/missions":
            self._handle_missions_list()
        elif path == "/missions/active" or path == "/v1/missions/active":
            self._handle_missions_active()
        elif path == "/missions/run" or path == "/v1/missions/run":
            self._handle_missions_run()
        elif path == "/preflight/status" or path == "/v1/preflight/status":
            self._handle_preflight_status()
        elif path == "/qualification/status" or path == "/v1/qualification/status":
            self._handle_qualification_status()
        elif path == "/repo/intel" or path == "/v1/repo/intel":
            self._handle_repo_intel()
        else:
            self.send_response(404)
            self.end_headers()
    
    def _handle_health_check(self):
        """Health check with dependency verification"""
        health_status = {
            "status": "healthy",
            "service": "roxy-core",
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        all_healthy = True
        degraded_components = []
        
        # Check auth token
        if AUTH_TOKEN:
            health_status["checks"]["auth_token"] = "ok"
        else:
            health_status["checks"]["auth_token"] = "missing"
            all_healthy = False
            degraded_components.append("auth_token")
        
        # Check rate limiter
        try:
            sys.path.insert(0, str(ROXY_DIR))
            from rate_limiting import get_rate_limiter
            get_rate_limiter()
            health_status["checks"]["rate_limiter"] = "ok"
        except Exception as e:
            health_status["checks"]["rate_limiter"] = f"error: {str(e)[:50]}"
            all_healthy = False
            degraded_components.append("rate_limiter")
        
        # Check ChromaDB
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(ROXY_DIR / "chroma_db"))
            # Try to get a collection (doesn't matter if it exists)
            client.list_collections()
            health_status["checks"]["chromadb"] = "ok"
        except Exception as e:
            health_status["checks"]["chromadb"] = f"error: {str(e)[:50]}"
            all_healthy = False
            degraded_components.append("chromadb")
        
        # Check Ollama
        base_url = _get_ollama_base_url()
        snapshot = _snapshot_ollama_health()
        ollama_check = {
            "ok": False,
            "base_url": base_url,
            "latency_ms": snapshot.get("last_latency_ms"),
            "last_ok_ts": snapshot.get("last_ok_ts"),
            "last_error": snapshot.get("last_error"),
        }

        try:
            import requests

            start_time = time.perf_counter()
            response = requests.get(f"{base_url}/api/tags", timeout=3)
            response.raise_for_status()
            latency_ms = (time.perf_counter() - start_time) * 1000
            _record_ollama_success(latency_ms)

            snapshot = _snapshot_ollama_health()
            ollama_check.update({
                "ok": True,
                "latency_ms": snapshot.get("last_latency_ms"),
                "last_ok_ts": snapshot.get("last_ok_ts"),
                "last_error": snapshot.get("last_error"),
            })
        except Exception as e:
            logger.debug(f"Ollama health check failed: {e}")
            _record_ollama_error(str(e))
            snapshot = _snapshot_ollama_health()
            ollama_check.update({
                "ok": False,
                "latency_ms": snapshot.get("last_latency_ms"),
                "last_ok_ts": snapshot.get("last_ok_ts"),
                "last_error": snapshot.get("last_error"),
            })
            all_healthy = False
            degraded_components.append("ollama")

        health_status["checks"]["ollama"] = ollama_check
        
        # Check Infrastructure (Redis, PostgreSQL, NATS)
        if INFRASTRUCTURE_AVAILABLE:
            infra_status = get_infrastructure_status()
            health_status["checks"]["infrastructure"] = {
                "initialized": infra_status.get('initialized', False)
            }
            for name, component in infra_status.get('components', {}).items():
                if isinstance(component, dict):
                    is_healthy = component.get('healthy', False)
                    if is_healthy:
                        health_status["checks"][f"infra_{name}"] = "ok"
                    else:
                        health_status["checks"][f"infra_{name}"] = "degraded"
                        all_healthy = False
                        degraded_components.append(f"infra_{name}")
                else:
                    health_status["checks"][f"infra_{name}"] = "unknown"
        else:
            health_status["checks"]["infrastructure"] = "not_available"
        
        if not all_healthy:
            health_status["status"] = "degraded"
            if degraded_components:
                health_status["degraded_components"] = degraded_components

        # /health reports process liveness; always return HTTP 200
        self.send_response(200)
        
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(health_status).encode())

    def _evaluate_core_readiness(self) -> tuple[bool, dict, list[str]]:
        """Verify core ROXY capabilities independent of Ollama availability."""
        core_ok = True
        checks: Dict[str, Dict[str, Any]] = {}
        degraded: list[str] = []

        # HTTP server reached this handler → liveness is confirmed
        checks["http_server"] = {"ok": True}

        # Authentication token must exist for requests to be served
        if AUTH_TOKEN:
            checks["auth_token"] = {"ok": True}
        else:
            checks["auth_token"] = {"ok": False, "error": "missing"}
            degraded.append("auth_token")
            core_ok = False

        roxy_path = str(ROXY_DIR)
        added_path = False
        roxy_exec_command = None
        roxy_time_query = None
        try:
            if not sys.path or sys.path[0] != roxy_path:
                sys.path.insert(0, roxy_path)
                added_path = True
            from roxy_commands import execute_command as _execute_command, answer_time_query as _answer_time_query
            roxy_exec_command = _execute_command
            roxy_time_query = _answer_time_query
            checks["roxy_commands_import"] = {"ok": True}
        except Exception as exc:
            checks["roxy_commands_import"] = {"ok": False, "error": str(exc)}
            degraded.append("roxy_commands_import")
            return False, checks, degraded
        finally:
            if added_path and sys.path and sys.path[0] == roxy_path:
                sys.path.pop(0)

        # Verify ping fast-path executes without LLM
        try:
            ping_result = roxy_exec_command("ping_direct", [])
            if isinstance(ping_result, tuple):
                ping_output = ping_result[0]
            else:
                ping_output = ping_result
            if isinstance(ping_output, str) and ping_output.strip().upper() == "PONG":
                checks["ping_direct"] = {"ok": True}
            else:
                checks["ping_direct"] = {"ok": False, "error": f"unexpected:{str(ping_output)[:80]}"}
                degraded.append("ping_direct")
                core_ok = False
        except Exception as exc:
            checks["ping_direct"] = {"ok": False, "error": str(exc)}
            degraded.append("ping_direct")
            core_ok = False

        # Verify deterministic time fast-path
        try:
            time_output = roxy_time_query("what time is it?")
            if isinstance(time_output, str) and time_output.strip():
                checks["time_direct"] = {"ok": True}
            else:
                checks["time_direct"] = {"ok": False, "error": "empty_response"}
                degraded.append("time_direct")
                core_ok = False
        except Exception as exc:
            checks["time_direct"] = {"ok": False, "error": str(exc)}
            degraded.append("time_direct")
            core_ok = False

        # Verify Postgres memory backend when required
        require_postgres = os.getenv("ROXY_MEMORY_REQUIRE_POSTGRES", "0").lower() in ("1", "true", "yes")
        if require_postgres:
            mem_check: Dict[str, Any] = {"ok": False}
            try:
                backend = None
                details = None
                if INFRASTRUCTURE_AVAILABLE:
                    infra = get_infrastructure_status()
                    details = infra.get("components", {}).get("postgres_memory")
                    if isinstance(details, dict):
                        backend = details.get("backend")
                        mem_check["details"] = details
                if backend is None:
                    # Fallback: direct health check
                    sys.path.insert(0, str(ROXY_DIR))
                    from memory_postgres import PostgresMemory
                    details = PostgresMemory().health_check()
                    backend = details.get("backend")
                    mem_check["details"] = details

                mem_check["backend"] = backend
                mem_check["ok"] = backend == "postgres"
            except Exception as exc:
                mem_check["error"] = str(exc)
                mem_check["ok"] = False

            checks["memory_postgres"] = mem_check
            if not mem_check.get("ok"):
                degraded.append("memory_postgres")
                core_ok = False

        return core_ok, checks, degraded

    def _handle_ready_check(self):
        """
        Production readiness check - stricter than /health.

        Always returns HTTP 200 with detailed status. `ready` reflects
        whether ROXY core commands are available, independent of Ollama.
        """
        from benchmark_service import check_pool_invariants

        ready_status = {
            "ready": False,
            "timestamp": datetime.now().isoformat(),
            "checks": {},
        }
        try:
            core_ok, core_checks, degraded_components = self._evaluate_core_readiness()
            ready_status["checks"].update(core_checks)

            ollama_ok = False
            pools = {}
            invariants = {}

            try:
                invariants = check_pool_invariants()
                ready_status["checks"]["pool_invariants"] = invariants

                pools = invariants.get("pools", {})
                ollama_ok = invariants.get("ok", False)

                if METRICS_AVAILABLE:
                    for pool_name, pool_info in pools.items():
                        record_pool_status(
                            pool=pool_name,
                            reachable=pool_info.get("reachable", False),
                            latency_ms=pool_info.get("latency_ms")
                        )

                unreachable = [p for p, info in pools.items() if not info.get("reachable", False)]
                if unreachable:
                    ollama_ok = False
                    port_hints = {"w5700x": "11434", "6900xt": "11435"}
                    ready_status.setdefault("warnings", []).append(
                        f"Pools not reachable: {', '.join(unreachable)}"
                    )
                    ready_status["remediation_hint"] = (
                        "Verify Ollama responding: " + ", ".join(
                            f"{pool} (port {port_hints.get(pool, '?')})" for pool in unreachable
                        )
                    )
                    degraded_components.extend(f"pool_{pool}" for pool in unreachable)
            except Exception as exc:
                ready_status["checks"]["pool_invariants_error"] = str(exc)
                degraded_components.append("pool_invariants")

            ready_status["ready"] = core_ok
            ready_status["status"] = "ready" if core_ok else "degraded"
            ready_status["ollama_ok"] = bool(ollama_ok)
            ready_status["message"] = "Core command fast-paths available" if core_ok else "Core command check failed"

            if invariants and not invariants.get("ok", True):
                degraded_components.append("pool_invariants")
                ready_status.setdefault("warnings", []).append(
                    invariants.get("warning") or "Pool invariants check reported issues"
                )

            if degraded_components:
                seen: set[str] = set()
                ordered: list[str] = []
                for item in degraded_components:
                    if item not in seen:
                        seen.add(item)
                        ordered.append(item)
                ready_status["degraded_components"] = ordered

            if METRICS_AVAILABLE:
                record_ready_check(ready=core_ok)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(ready_status, indent=2).encode())

        except Exception as exc:
            ready_status["error_code"] = "INTERNAL_ERROR"
            ready_status["message"] = str(exc)
            ready_status["remediation_hint"] = "Check roxy-core logs: journalctl --user -u roxy-core -f"
            if METRICS_AVAILABLE:
                record_ready_check(ready=False)
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(ready_status, indent=2).encode())

    def _handle_version(self):
        """
        Return version information for release tracking.
        GET /version - Returns {version, git_sha, build_time, python_version}
        """
        version_info = {
            "version": "1.0.0-rc2",
            "service": "roxy-core",
        }

        # Get git SHA
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=2, cwd=ROXY_DIR
            )
            version_info["git_sha"] = result.stdout.strip() if result.returncode == 0 else "unknown"

            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=2, cwd=ROXY_DIR
            )
            version_info["git_sha_full"] = result.stdout.strip() if result.returncode == 0 else "unknown"

            # Check if dirty
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=2, cwd=ROXY_DIR
            )
            version_info["git_dirty"] = bool(result.stdout.strip()) if result.returncode == 0 else None
        except Exception:
            version_info["git_sha"] = "unknown"
            version_info["git_sha_full"] = "unknown"
            version_info["git_dirty"] = None

        # Build time (file mtime of roxy_core.py as proxy)
        try:
            import platform
            roxy_core_path = ROXY_DIR / "roxy_core.py"
            mtime = roxy_core_path.stat().st_mtime
            version_info["build_time"] = datetime.fromtimestamp(mtime).isoformat()
            version_info["python_version"] = platform.python_version()
            version_info["platform"] = platform.system()
        except Exception:
            version_info["build_time"] = "unknown"

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(version_info, indent=2).encode())

    def _handle_info(self):
        """Return server info: time, hostname, git state, ollama status, routing policy.
        
        Chief's Truth Panel - authoritative data for Command Center.
        """
        import socket
        
        info = {
            "server_time_iso": datetime.now().isoformat(),
            "hostname": socket.gethostname(),
            "roxy_core_pid": os.getpid(),
            "git": {},
            "ollama": {},
            "routing_policy": config.get("routing_policy", "auto")
        }
        
        # Git state
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=2, cwd=ROXY_DIR
            )
            info["git"]["branch"] = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=2, cwd=ROXY_DIR
            )
            info["git"]["head_sha"] = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=2, cwd=ROXY_DIR
            )
            info["git"]["dirty"] = bool(result.stdout.strip()) if result.returncode == 0 else None
            
            result = subprocess.run(
                ["git", "log", "-1", "--format=%s"],
                capture_output=True, text=True, timeout=2, cwd=ROXY_DIR
            )
            info["git"]["last_commit_subject"] = result.stdout.strip()[:80] if result.returncode == 0 else ""
        except Exception as e:
            info["git"]["error"] = str(e)
        
        # Ollama state
        pools = _resolve_ollama_pools()
        ollama_base = pools["default"]

        # CHIEF'S TRUTH CONTRACT: Expose pool configuration + reachability + MISCONFIGURATION
        # CHIEF DIRECTIVE: Pool names match hardware (w5700x, 6900xt), not semantic roles
        w5700x_reach = _check_ollama_reachability(pools["w5700x"]["url"])
        xt6900_reach = _check_ollama_reachability(pools["6900xt"]["url"])

        # Port -> service mapping (single source of truth)
        PORT_SERVICE_MAP = {
            11434: {"service": "ollama-w5700x.service", "gpu": "W5700X"},
            11435: {"service": "ollama-6900xt.service", "gpu": "6900XT"},
        }

        def _get_pool_hints(url: str) -> dict:
            """Get service/pid hints for a pool URL (best-effort)"""
            import re
            import subprocess
            hints = {"service_name": None, "gpu": None, "pid": None}
            if not url:
                return hints
            port_match = re.search(r':(\d+)', url)
            if not port_match:
                return hints
            port = int(port_match.group(1))
            # Service/GPU from mapping
            if port in PORT_SERVICE_MAP:
                hints["service_name"] = PORT_SERVICE_MAP[port]["service"]
                hints["gpu"] = PORT_SERVICE_MAP[port]["gpu"]
            # PID from lsof (best-effort)
            try:
                result = subprocess.run(
                    ["lsof", "-i", f":{port}", "-t"],
                    capture_output=True, text=True, timeout=1
                )
                if result.returncode == 0 and result.stdout.strip():
                    hints["pid"] = int(result.stdout.strip().split('\n')[0])
            except:
                pass
            return hints

        w5700x_hints = _get_pool_hints(pools["w5700x"]["url"])
        xt6900_hints = _get_pool_hints(pools["6900xt"]["url"])

        info["ollama"]["pools"] = {
            "w5700x": {
                "url": pools["w5700x"]["url"],
                "configured": pools["w5700x"]["configured"],
                "reachable": w5700x_reach["reachable"],
                "latency_ms": w5700x_reach["latency_ms"],
                "error": w5700x_reach["error"],
                "service_name": w5700x_hints["service_name"],
                "gpu": w5700x_hints["gpu"],
                "pid": w5700x_hints["pid"],
            },
            "6900xt": {
                "url": pools["6900xt"]["url"],
                "configured": pools["6900xt"]["configured"],
                "reachable": xt6900_reach["reachable"],
                "latency_ms": xt6900_reach["latency_ms"],
                "error": xt6900_reach["error"],
                "service_name": xt6900_hints["service_name"],
                "gpu": xt6900_hints["gpu"],
                "pid": xt6900_hints["pid"],
            }
        }
        info["ollama"]["base_url"] = ollama_base
        # Legacy field for compatibility
        info["ollama"]["fast_url"] = pools["6900xt"]["url"]
        # HARD INVARIANT: Expose misconfiguration state
        info["ollama"]["misconfigured"] = pools["misconfigured"]
        
        # Default pool reachability (for legacy compatibility)
        try:
            import urllib.request
            start = time.time()
            req = urllib.request.Request(f"{ollama_base}/api/tags", method="GET")
            req.add_header("User-Agent", "roxy-core/info-check")
            with urllib.request.urlopen(req, timeout=2) as resp:
                info["ollama"]["latency_ms"] = round((time.time() - start) * 1000, 2)
                info["ollama"]["ok"] = resp.status == 200
                info["ollama"]["error"] = None
        except Exception as e:
            info["ollama"]["ok"] = False
            info["ollama"]["error"] = str(e)
            info["ollama"]["latency_ms"] = None

        # CHIEF DIRECTIVE: Add pool invariants check (startup latency validation)
        try:
            from benchmark_service import check_pool_invariants
            info["ollama"]["pool_invariants"] = check_pool_invariants()
        except Exception as e:
            info["ollama"]["pool_invariants"] = {"error": str(e), "ok": False}

        # GitHub state
        github_token = _get_github_token()
        github_reach = _check_github_reachability(github_token)
        
        info["github"] = {
            "configured": bool(github_token),
            "reachable": github_reach["reachable"],
            "latency_ms": github_reach["latency_ms"],
            "error": github_reach["error"],
            "rate_limit": github_reach["rate_limit"]
        }
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(info, indent=2).encode())

    def _handle_auth_status(self):
        """GET /auth/status - Auth configuration info (no secrets exposed).

        Returns instructions for using authenticated endpoints.
        CHIEF DIRECTIVE: Auth clarity for operators.
        """
        # Determine token source
        token_source = None
        if TOKEN_FILE.exists():
            token_source = str(TOKEN_FILE)
        elif os.getenv("AUTH_TOKEN"):
            token_source = "AUTH_TOKEN environment variable"

        status = {
            "auth_enabled": bool(AUTH_TOKEN),
            "header": "X-ROXY-Token",
            "token_source": token_source,
            "token_file_path": str(TOKEN_FILE),
            "usage_example": 'curl -H "X-ROXY-Token: YOUR_TOKEN" http://127.0.0.1:8766/bench/run ...',
            "protected_endpoints": [
                "/bench/run",
                "/bench/cancel",
                "/run",
                "/github/*",
            ],
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(status, indent=2).encode())

    def _handle_metrics(self):
        """Expose Prometheus metrics with graceful degradation."""
        request_id = str(uuid.uuid4())[:8]

        if not METRICS_AVAILABLE or not prometheus_available():
            global METRICS_BOOT_WARNING_EMITTED
            if not METRICS_BOOT_WARNING_EMITTED:
                logger.warning("[METRICS] Prometheus disabled reason=prometheus_client missing")
                METRICS_BOOT_WARNING_EMITTED = True
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {
                "disabled": True,
                "reason": "prometheus_client missing",
                "request_id": request_id,
            }
            self._safe_write(json.dumps(payload), request_id)
            return

        try:
            metrics_body, content_type = export_metrics()
        except RuntimeError as exc:
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {
                "disabled": True,
                "reason": str(exc),
                "request_id": request_id,
            }
            self._safe_write(json.dumps(payload), request_id)
            return
        except Exception as exc:  # pragma: no cover - unexpected failure
            logger.error(f"Metrics export failed: {exc}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {
                "status": "error",
                "reason": "metrics export failure",
                "request_id": request_id,
            }
            self._safe_write(json.dumps(payload), request_id)
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(metrics_body)
        except (BrokenPipeError, ConnectionResetError):
            logger.info(f"[METRICS] client disconnected requestId={request_id}")
    
    def _handle_streaming(self):
        """Handle Server-Sent Events streaming"""
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        # Track metrics
        if METRICS_AVAILABLE:
            metrics_ctx = MetricsMiddleware(endpoint="/stream")
            metrics_ctx.__enter__()
        else:
            metrics_ctx = None
        metrics_closed = False
        
        try:
            # Rate limiting for streaming endpoint
            rate_limiting_enabled = config.get("rate_limiting_enabled", False)
            if rate_limiting_enabled:
                try:
                    sys.path.insert(0, str(ROXY_DIR))
                    from rate_limiting import get_rate_limiter
                    rate_limiter = get_rate_limiter()
                    client_ip = self.client_address[0]
                    if not rate_limiter.check_rate_limit(client_ip, "/stream"):
                        if METRICS_AVAILABLE:
                            record_rate_limit("/stream")
                        self.send_response(429)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        response = {"status": "error", "message": "Rate limit exceeded"}
                        self._safe_write(json.dumps(response), request_id)
                        if metrics_ctx and not metrics_closed:
                            metrics_ctx.set_status("rate_limited")
                            metrics_ctx.__exit__(None, None, None)
                            metrics_closed = True
                        return
                except Exception as e:
                    logger.warning(f"Rate limiting check failed for streaming: {e}")
            
            # Parse query parameters - accept both 'q' and 'command'
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            command = params.get('q', params.get('command', [''])[0])[0] if params.get('q') else params.get('command', [''])[0]
            allow_greeting = params.get('allow_greeting', [''])[0].lower() in ("1", "true", "yes")
            if self.headers.get('X-ROXY-Allow-Greeting', '').lower() in ("1", "true", "yes"):
                allow_greeting = True
            self._allow_stream_greeting = allow_greeting
            debug_echo = params.get('debug_echo', [''])[0].lower() in ("1", "true", "yes")
            if os.getenv("ROXY_DEBUG_ECHO", "").lower() in ("1", "true", "yes"):
                debug_echo = True
            if self.headers.get('X-ROXY-Debug', '').lower() in ("1", "true", "yes"):
                debug_echo = True
            self._debug_stream_echo = debug_echo
            self._stream_request_echo = command
            
            if not command:
                self.send_error(400, "No command provided (use 'q' or 'command' query parameter)")
                if metrics_ctx:
                    metrics_ctx.set_status("error")
                    metrics_ctx.__exit__(None, None, None)
                    metrics_closed = True
                return
            
            # Validate auth token if configured
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    self.send_error(403, "Forbidden: Invalid or missing token")
                    return
            
            # Set SSE headers
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("X-Accel-Buffering", "no")  # Nginx compatibility
            self.end_headers()
            
            # Stream response
            self._stream_command_response(command, request_id)
            if metrics_ctx and not metrics_closed:
                metrics_ctx.set_status("success")
                metrics_ctx.__exit__(None, None, None)
                metrics_closed = True
            
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            # Close metrics context on error
            if METRICS_AVAILABLE and metrics_ctx:
                metrics_ctx.set_status("error")
                metrics_ctx.__exit__(type(e), e, None)
                metrics_closed = True
            self.send_error(500, str(e))
        finally:
            if metrics_ctx and not metrics_closed:
                metrics_ctx.__exit__(None, None, None)
    
    def _stream_command_response(self, command: str, request_id: str):
        """Stream command response as SSE events with real Ollama streaming"""
        try:
            full_response = ""
            allow_greeting = getattr(self, "_allow_stream_greeting", False)
            debug_echo = getattr(self, "_debug_stream_echo", False)
            request_echo = getattr(self, "_stream_request_echo", "")
            session_id = self.headers.get('X-ROXY-Session', request_id)
            user_id = _resolve_request_user_id(self.headers)
            memory_context = ""
            memory_context_meta = {
                "enabled": False,
                "memory_items": 0,
                "profile_items": 0,
                "typed_record_items": 0,
                "repo_context_items": 0,
                "context_chars": 0,
            }
            memory_context, memory_context_meta = _build_memory_context_for_prompt(
                command,
                session_id,
                user_id=user_id,
            )

            # Import streaming module
            sys.path.insert(0, str(ROXY_DIR))
            from streaming import get_streamer
            streamer = get_streamer()

            def _emit_event(event_type: str, payload: Dict[str, Any]) -> bool:
                event_payload = _json_sanitize(payload)
                return self._safe_write(
                    f"event: {event_type}\ndata: {json.dumps(event_payload)}\n\n",
                    request_id,
                )

            def _parse_sse_event(event_str: str) -> Tuple[str, Dict[str, Any]]:
                if not event_str:
                    return "unknown", {}
                event_type = "message"
                payload: Dict[str, Any] = {}
                for line in event_str.splitlines():
                    if line.startswith("event: "):
                        event_type = line[len("event: "):].strip()
                    elif line.startswith("data: "):
                        try:
                            payload = json.loads(line[len("data: "):])
                        except Exception:
                            payload = {"raw": line[len("data: "):]}
                return event_type, payload

            def _stream_rag_pass(query_text: str, context_text: str = "") -> Tuple[bool, str]:
                pass_text = ""
                for sse_event in streamer.stream_rag_response(
                    query=query_text,
                    context=context_text,
                    model=selected_model,
                    request_id=request_id,
                    base_url=selected_endpoint,
                ):
                    # Keep-alive comments from upstream streamer
                    if sse_event.startswith(":"):
                        if not self._safe_write(sse_event, request_id):
                            return False, pass_text
                        continue
                    event_type, payload = _parse_sse_event(sse_event)
                    if event_type == "token":
                        token = str(payload.get("token") or payload.get("response") or "")
                        if token:
                            pass_text += token
                    # Suppress upstream complete so we can emit one terminal event.
                    if event_type == "complete":
                        continue
                    if not _emit_event(event_type, payload):
                        return False, pass_text
                return True, pass_text

            def _execute_stream_tool_call(tool_call: Dict[str, Any]) -> Dict[str, Any]:
                tool_name = tool_call.get("name", "")
                arguments = tool_call.get("arguments", {}) or {}
                call_id = tool_call.get("call_id", str(uuid.uuid4())[:12])
                started = time.time()
                result_payload: Dict[str, Any] = {
                    "call_id": call_id,
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "success": False,
                }

                if tool_name == "bash":
                    try:
                        from tool_executor import ToolExecutor

                        async def _run_bash() -> Any:
                            executor = ToolExecutor(
                                timeout=STREAM_TOOL_EXEC_TIMEOUT_SEC,
                                workdir=str(ROXY_DIR),
                            )

                            async def _stream_callback(chunk: str, is_error: bool = False) -> None:
                                await asyncio.sleep(0)
                                _emit_event(
                                    "tool_output_delta",
                                    {
                                        "call_id": call_id,
                                        "tool_name": tool_name,
                                        "stream": "stderr" if is_error else "stdout",
                                        "chunk": _truncate_tool_text(chunk, MAX_STREAM_TOOL_DELTA_CHARS),
                                    },
                                )

                            return await executor.execute_bash(
                                str(arguments.get("command", "")),
                                timeout=float(arguments.get("timeout", STREAM_TOOL_EXEC_TIMEOUT_SEC)),
                                workdir=arguments.get("workdir", str(ROXY_DIR)),
                                stream_callback=_stream_callback,
                            )

                        tool_result = asyncio.run(_run_bash())
                        result_payload.update(
                            {
                                "success": bool(tool_result.success),
                                "exit_code": int(tool_result.exit_code),
                                "duration": float(tool_result.duration),
                                "output": _truncate_tool_text(tool_result.output, MAX_STREAM_TOOL_RESULT_CHARS),
                                "error": _truncate_tool_text(tool_result.error, MAX_STREAM_TOOL_RESULT_CHARS),
                                "metadata": tool_result.metadata,
                            }
                        )
                    except Exception as exc:
                        result_payload.update({"success": False, "error": str(exc), "exit_code": -1})
                elif tool_name.startswith("mcp_"):
                    try:
                        mcp_client = _get_mcp_client()
                        if not mcp_client:
                            result_payload.update({"success": False, "error": "MCP client not available"})
                        else:
                            parts = tool_name.split("_", 2)
                            if len(parts) >= 3:
                                server_id = parts[1]
                                mcp_tool_name = parts[2]

                                async def _call_mcp():
                                    return await mcp_client.call_tool(
                                        server_id,
                                        mcp_tool_name,
                                        arguments,
                                        timeout=float(arguments.get("_timeout", STREAM_TOOL_EXEC_TIMEOUT_SEC)),
                                    )

                                mcp_result = asyncio.run(_call_mcp())
                                if mcp_result:
                                    content_text = ""
                                    for content_block in (mcp_result.content or []):
                                        if isinstance(content_block, dict):
                                            content_text += str(content_block.get("text", ""))
                                        elif isinstance(content_block, str):
                                            content_text += content_block
                                    result_payload.update({
                                        "success": not mcp_result.isError,
                                        "output": _truncate_tool_text(content_text, MAX_STREAM_TOOL_RESULT_CHARS),
                                        "error": "" if not mcp_result.isError else content_text,
                                        "metadata": {"mcp_server": server_id, "mcp_tool": mcp_tool_name},
                                    })
                                    if content_text:
                                        _emit_event(
                                            "tool_output_delta",
                                            {
                                                "call_id": call_id,
                                                "tool_name": tool_name,
                                                "stream": "stdout",
                                                "chunk": _truncate_tool_text(content_text, MAX_STREAM_TOOL_DELTA_CHARS),
                                            },
                                        )
                                else:
                                    result_payload.update({"success": False, "error": "MCP tool call returned no result"})
                            else:
                                result_payload.update({"success": False, "error": f"Invalid MCP tool name: {tool_name}"})
                    except Exception as exc:
                        result_payload.update({"success": False, "error": str(exc)})
                else:
                    try:
                        from tools.streaming_tools import StreamingTools

                        async def _run_file_tool() -> Any:
                            tools = StreamingTools(workdir=str(ROXY_DIR))
                            return await tools.execute_tool(tool_name, arguments)

                        tool_result = asyncio.run(_run_file_tool())
                        data_preview = tool_result.data
                        if isinstance(data_preview, (dict, list)):
                            data_preview = json.dumps(data_preview)
                        result_payload.update(
                            {
                                "success": bool(tool_result.success),
                                "output": _truncate_tool_text(data_preview, MAX_STREAM_TOOL_RESULT_CHARS),
                                "error": _truncate_tool_text(tool_result.error, MAX_STREAM_TOOL_RESULT_CHARS),
                                "metadata": tool_result.metadata,
                            }
                        )
                        if data_preview:
                            _emit_event(
                                "tool_output_delta",
                                {
                                    "call_id": call_id,
                                    "tool_name": tool_name,
                                    "stream": "stdout",
                                    "chunk": _truncate_tool_text(data_preview, MAX_STREAM_TOOL_DELTA_CHARS),
                                },
                            )
                    except Exception as exc:
                        result_payload.update({"success": False, "error": str(exc)})

                result_payload["duration"] = float(time.time() - started)
                return result_payload

            def _execute_tool_with_retry(
                tool_call: Dict[str, Any],
                request_id: str,
                session_id: str,
                user_id: str,
                emit_event: Callable[[str, Dict[str, Any]], bool],
                append_audit: Callable[[Dict[str, Any]], None],
                write_failure_memory: Callable[[Dict[str, Any]], None],
                truncate_text: Callable[[str, int], str],
                pre_policy_fn: Callable[[str, Dict, str, str], Dict],
            ) -> Dict[str, Any]:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("arguments", {}) or {}
                call_id = tool_call.get("call_id", str(uuid.uuid4())[:12])
                command = str(tool_args.get("command") or "")

                from tool_retry import get_retry_controller, RootCauseClassifier
                controller = get_retry_controller()

                attempt = 0
                max_attempts = 3
                last_result: Optional[Dict[str, Any]] = None
                original_command = command
                original_tool_args = dict(tool_args)
                original_error = ""
                original_root_cause = "unknown"

                while attempt < max_attempts:
                    if attempt > 0:
                        strategy = controller.get_next_strategy(
                            tool_name, original_command, original_tool_args,
                            last_result.get("error", "") if last_result else "",
                            last_result.get("exit_code", -1) if last_result else -1,
                        )
                        if strategy is None:
                            break

                        new_command = strategy.get("command", command)
                        strategy_name = strategy.get("strategy_name", "unknown")

                        emit_event("tool_retry_attempt", {
                            "call_id": call_id,
                            "tool_name": tool_name,
                            "attempt": attempt,
                            "strategy": strategy_name,
                            "description": strategy.get("description", ""),
                        })

                        retry_tool_call = {
                            "name": tool_name,
                            "arguments": {**original_tool_args, "command": new_command},
                            "call_id": f"{call_id}-r{attempt}",
                        }
                        last_result = _execute_stream_tool_call(retry_tool_call)
                        command = new_command
                    else:
                        last_result = _execute_stream_tool_call(tool_call)

                    attempt += 1

                    if last_result.get("success"):
                        append_audit({
                            "event": "tool_execution",
                            "request_id": request_id,
                            "session_id": session_id,
                            "user_id": user_id,
                            "call_id": call_id,
                            "tool_name": tool_name,
                            "arguments": {**original_tool_args, "command": command},
                            "success": True,
                            "error": last_result.get("error"),
                            "exit_code": last_result.get("exit_code"),
                            "duration": last_result.get("duration", 0.0),
                            "attempts": attempt,
                            "timestamp": time.time(),
                        })
                        if attempt > 1:
                            controller.record_success(
                                tool_name, original_command, original_tool_args,
                                original_error,
                                original_root_cause,
                                command,
                            )
                            emit_event("tool_retry_success", {
                                "call_id": call_id,
                                "tool_name": tool_name,
                                "attempts": attempt,
                            })
                        return last_result

                    if attempt == 1:
                        original_error = str(last_result.get("error", "") or "")
                        original_root_cause = RootCauseClassifier.classify(
                            original_command,
                            original_error,
                            int(last_result.get("exit_code", -1) or -1),
                        )

                    if attempt >= max_attempts:
                        break

                final_result = last_result or {
                    "call_id": call_id,
                    "tool_name": tool_name,
                    "success": False,
                    "error": "retry_exhausted",
                }

                append_audit({
                    "event": "tool_execution",
                    "request_id": request_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "call_id": call_id,
                    "tool_name": tool_name,
                    "arguments": {**original_tool_args, "command": command},
                    "success": final_result.get("success", False),
                    "error": final_result.get("error"),
                    "exit_code": final_result.get("exit_code"),
                    "duration": final_result.get("duration", 0.0),
                    "attempts": attempt,
                    "timestamp": time.time(),
                })

                if not final_result.get("success"):
                    write_failure_memory({
                        "status": "failed",
                        "tool_name": tool_name,
                        "arguments": {**original_tool_args, "command": command},
                        "error": final_result.get("error"),
                        "exit_code": final_result.get("exit_code"),
                        "request_id": request_id,
                        "session_id": session_id,
                        "call_id": call_id,
                        "duration": final_result.get("duration", 0.0),
                    })
                    emit_event("tool_retry_exhausted", {
                        "call_id": call_id,
                        "tool_name": tool_name,
                        "attempts": attempt,
                        "error": final_result.get("error", "unknown"),
                    })

                return final_result

            if debug_echo:
                debug_payload = json.dumps({"request_echo": request_echo, "request_id": request_id})
                self._safe_write(f"event: debug\ndata: {debug_payload}\n\n", request_id)
            
            # Greeting fast-path only when explicitly allowed
            if _is_pure_greeting(command) and allow_greeting:
                response = "Hi! I'm ROXY, your resident AI assistant. How can I help you?"
                for char in response:
                    event_data = json.dumps({"token": char, "done": False})
                    if not self._safe_write(f"data: {event_data}\n\n", request_id):
                        return
                    time.sleep(0.01)
                self._safe_write(f"event: complete\ndata: {json.dumps({'done': True})}\n\n", request_id)
                return
            
            # Check if it's a RAG query (not a command)
            is_command = any(cmd in command.lower() for cmd in [
                "git", "obs", "health", "open", "launch", "start", "stop"
            ])

            # Import query classifiers (Directives #3, #5)
            skip_rag = False
            skip_rag_reason = None
            try:
                from streaming import is_time_date_query, is_repo_query
                if is_time_date_query(command):
                    skip_rag = True
                    skip_rag_reason = "time_date_query"
                    logger.info(f"[ROUTING] Time/date query detected - skipping RAG requestId={request_id}")
                elif is_repo_query(command):
                    skip_rag = True
                    skip_rag_reason = "repo_query"
                    logger.info(f"[ROUTING] Repo/git query detected - skipping RAG requestId={request_id}")
            except ImportError:
                pass

            # Build routing metadata (Directive #10) + Expert routing (Directive #8)
            import time as time_mod
            route_start = time_mod.time()

            # Check for /deep prefix to force BIG pool
            force_deep = command.lower().startswith("/deep ")
            if force_deep:
                command = command[6:].strip()  # Remove /deep prefix

            # Route query using router_integration
            try:
                from router_integration import route_query, to_routing_meta
                routing_decision = route_query(command, force_deep=force_deep)
                routing_meta = to_routing_meta(routing_decision)

                # Chief directive A: routed_mode must reflect reality
                if is_command:
                    routing_meta["routed_mode"] = "command"
                elif skip_rag:
                    routing_meta["routed_mode"] = "truth_only"  # No RAG, TruthPacket handles it
                else:
                    routing_meta["routed_mode"] = "rag"

                routing_meta["skip_rag"] = skip_rag
                routing_meta["skip_rag_reason"] = skip_rag_reason
                routing_meta["request_id"] = request_id

                # Chief directive B: override query_type for time/repo queries
                if skip_rag_reason == "time_date_query":
                    routing_meta["query_type"] = "time_date"
                    routing_meta["reason"] = "skip_rag:time_date_query"
                elif skip_rag_reason == "repo_query":
                    routing_meta["query_type"] = "repo"
                    routing_meta["reason"] = "skip_rag:repo_query"

                selected_model = routing_decision.selected_model
                selected_endpoint = routing_decision.selected_endpoint
                if not selected_model:
                    selected_model = _get_default_model(selected_endpoint, query=command, mode=routing_meta.get("routed_mode", ""))
            except ImportError:
                logger.warning("[ROUTING] router_integration not available, using defaults")
                # Default to FAST pool for speed (Chief directive: FAST unless router says BIG)
                # Chief directive A: routed_mode must reflect reality
                if is_command:
                    mode = "command"
                elif skip_rag:
                    mode = "truth_only"
                else:
                    mode = "rag"

                # Chief directive B/D: override query_type and reason for time/repo
                if skip_rag_reason == "time_date_query":
                    qtype, reason = "time_date", "skip_rag:time_date_query"
                elif skip_rag_reason == "repo_query":
                    qtype, reason = "repo", "skip_rag:repo_query"
                else:
                    qtype, reason = "general", "fallback:general:no_router"

                routing_meta = {
                    "routed_mode": mode,
                    "query_type": qtype,
                    "reason": reason,
                    "selected_pool": "6900xt",
                    "selected_endpoint": "http://127.0.0.1:11435",
                    "selected_model": _get_default_model("http://127.0.0.1:11435", query=command, mode=mode),
                    "confidence": 0.0,
                    "skip_rag": skip_rag,
                    "skip_rag_reason": skip_rag_reason,
                    "request_id": request_id,
                }
                selected_model = routing_meta["selected_model"]
                selected_endpoint = "http://127.0.0.1:11435"

            if not is_command:
                # Likely RAG query - get context and stream
                # But skip RAG for time/date queries (Directive #3)
                context = ""
                rag_skipped = False
                rag_sources = []  # Top 3 RAG sources for routing_meta

                if skip_rag:
                    # Time/date query - TruthPacket will handle it, no RAG needed
                    logger.debug(f"[RAG] Skipping RAG for time/date query requestId={request_id}")
                    rag_skipped = True
                else:
                    try:
                        # Get RAG context with retry and circuit breaker
                        import chromadb
                        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
                        from roxy_commands import _expand_query

                        # Import resilience utilities
                        try:
                            from retry_utils import retry
                            from circuit_breaker import get_circuit_breaker, CircuitBreakerError
                            RESILIENCE_AVAILABLE = True
                        except ImportError:
                            RESILIENCE_AVAILABLE = False

                        expanded_query = _expand_query(command)
                        ef = DefaultEmbeddingFunction()

                        @retry(max_attempts=3, delay=1.0, backoff=2.0) if RESILIENCE_AVAILABLE else lambda f: f
                        def _get_embedding():
                            return ef([expanded_query])[0]

                        embedding = _get_embedding()

                        @retry(max_attempts=3, delay=1.0, backoff=2.0) if RESILIENCE_AVAILABLE else lambda f: f
                        def _query_chromadb():
                            client = chromadb.PersistentClient(path=str(ROXY_DIR / "chroma_db"))
                            collection = client.get_collection("mindsong_docs", embedding_function=ef)
                            return collection.query(
                                query_embeddings=[embedding],
                                n_results=5,  # Get more for boosting, use top 3
                                include=["documents", "metadatas", "distances"]
                            )

                        # Use circuit breaker if available
                        if RESILIENCE_AVAILABLE:
                            chromadb_circuit = get_circuit_breaker("chromadb", failure_threshold=5, timeout=60.0)
                            try:
                                results = chromadb_circuit.call(_query_chromadb)
                            except CircuitBreakerError as e:
                                logger.error(f"ChromaDB circuit breaker is OPEN: {e}")
                                results = {"documents": [[]], "metadatas": [[]]}
                        else:
                            results = _query_chromadb()

                        # Apply ops docs priority boosts (Chief directive #6)
                        try:
                            from rag.rebuild_index_clean import apply_ops_boosts
                            results = apply_ops_boosts(results, command)
                        except ImportError:
                            pass  # Boost not available, continue with raw results

                        context_chunks = results["documents"][0] if results and results["documents"] else []
                        context = "\n\n".join(context_chunks[:3]) if context_chunks else ""

                        # Extract top 3 sources for routing_meta (Directive B)
                        # Chief directive C: Deduplicate sources while preserving order
                        rag_sources = []
                        seen_sources = set()
                        if results and results.get("metadatas"):
                            for meta in results["metadatas"][0]:
                                if meta and "source" in meta:
                                    source = meta["source"]
                                    if source and source not in seen_sources:
                                        seen_sources.add(source)
                                        rag_sources.append(source)
                                        if len(rag_sources) >= 3:
                                            break

                    except Exception as e:
                        logger.debug(f"RAG context fetch failed: {e}, continuing with empty context")
                        context = ""
                        # rag_sources already initialized to [] at start

                # Stream RAG response (with or without context)
                try:
                    if memory_context and not rag_skipped:
                        context = f"{memory_context}\n\n{context}" if context else memory_context

                    # Emit routing metadata event (Directive #10)
                    routing_meta["latency_ms"] = int((time_mod.time() - route_start) * 1000)
                    routing_meta["rag_context_len"] = len(context) if context else 0
                    routing_meta["rag_sources_top3"] = rag_sources
                    routing_meta["memory_context_len"] = int(memory_context_meta.get("context_chars", 0))
                    routing_meta["memory_items"] = int(memory_context_meta.get("memory_items", 0))
                    routing_meta["profile_items"] = int(memory_context_meta.get("profile_items", 0))
                    routing_meta["typed_record_items"] = int(memory_context_meta.get("typed_record_items", 0))
                    routing_meta["repo_context_items"] = int(memory_context_meta.get("repo_context_items", 0))
                    if not _emit_event("routing_meta", routing_meta):
                        return

                    # Pass 1: stream model output
                    ok, initial_response = _stream_rag_pass(
                        query_text=command,
                        context_text=context if not rag_skipped else "",
                    )
                    if not ok:
                        return
                    full_response += initial_response

                    # RCA-003: detect tool calls in streamed model output and execute with hooks.
                    if ENABLE_STREAM_TOOL_CALLS:
                        stream_start = time.time()
                        executed_count = 0
                        seen_signatures = set()
                        latest_response = initial_response

                        while executed_count < MAX_STREAM_TOOL_CALLS:
                            if (time.time() - stream_start) > MAX_STREAM_TOOL_RUNTIME_SEC:
                                _emit_event(
                                    "tool_execution_failed",
                                    {
                                        "reason": "tool_runtime_budget_exceeded",
                                        "max_runtime_sec": MAX_STREAM_TOOL_RUNTIME_SEC,
                                        "executed_count": executed_count,
                                    },
                                )
                                break

                            tool_calls = _extract_stream_tool_calls(latest_response)
                            if not tool_calls:
                                break

                            selected_call = None
                            for candidate in tool_calls:
                                signature = json.dumps(
                                    {"name": candidate.get("name"), "arguments": candidate.get("arguments", {})},
                                    sort_keys=True,
                                )
                                if signature in seen_signatures:
                                    continue
                                seen_signatures.add(signature)
                                selected_call = candidate
                                break

                            if not selected_call:
                                break

                            call_id = selected_call.get("call_id", str(uuid.uuid4())[:12])
                            tool_name = selected_call.get("name")
                            tool_args = selected_call.get("arguments", {})

                            if not _emit_event(
                                "tool_call_detected",
                                {"call_id": call_id, "tool_name": tool_name, "arguments": tool_args},
                            ):
                                return

                            pre_policy = _pre_tool_use_policy(tool_name, tool_args)
                            if not pre_policy.get("allow", False):
                                denial_record = {
                                    "timestamp": datetime.now().isoformat(),
                                    "request_id": request_id,
                                    "session_id": session_id,
                                    "user_id": user_id,
                                    "call_id": call_id,
                                    "tool_name": tool_name,
                                    "arguments": tool_args,
                                    "status": "denied",
                                    "reason": pre_policy.get("reason", "policy_denied"),
                                    "safety_level": pre_policy.get("safety_level", "guarded"),
                                }
                                _append_tool_audit(denial_record)
                                _write_tool_failure_memory({
                                    **denial_record,
                                    "status": "failed",
                                    "error": pre_policy.get("reason", "policy_denied"),
                                })
                                if not _emit_event(
                                    "tool_execution_failed",
                                    {
                                        "call_id": call_id,
                                        "tool_name": tool_name,
                                        "reason": pre_policy.get("reason", "policy_denied"),
                                        "safety_level": pre_policy.get("safety_level", "guarded"),
                                    },
                                ):
                                    return
                                latest_response = ""
                                continue

                            if not _emit_event(
                                "tool_execution_started",
                                {
                                    "call_id": call_id,
                                    "tool_name": tool_name,
                                    "safety_level": pre_policy.get("safety_level", "safe"),
                                },
                            ):
                                return

                            tool_result = _execute_tool_with_retry(
                                {"name": tool_name, "arguments": tool_args, "call_id": call_id},
                                request_id,
                                session_id,
                                user_id,
                                _emit_event,
                                _append_tool_audit,
                                _write_tool_failure_memory,
                                _truncate_tool_text,
                                _pre_tool_use_policy,
                            )
                            executed_count += 1

                            if not tool_result.get("success"):
                                if not _emit_event(
                                    "tool_execution_failed",
                                    {
                                        "call_id": call_id,
                                        "tool_name": tool_name,
                                        "error": tool_result.get("error", "tool_failed"),
                                        "duration": tool_result.get("duration", 0.0),
                                    },
                                ):
                                    return
                                latest_response = ""
                                continue

                            if not _emit_event(
                                "tool_execution_finished",
                                {
                                    "call_id": call_id,
                                    "tool_name": tool_name,
                                    "success": True,
                                    "duration": tool_result.get("duration", 0.0),
                                    "exit_code": tool_result.get("exit_code", 0),
                                },
                            ):
                                return

                            # Ask model to synthesize final response from tool output.
                            # This enables model->tool->response loop in streaming mode.
                            tool_output = tool_result.get("output", "")
                            tool_error = tool_result.get("error", "")
                            followup_query = (
                                f"Original user request:\n{command}\n\n"
                                f"Tool executed: {tool_name}\n"
                                f"Tool arguments: {json.dumps(tool_args, ensure_ascii=True)}\n"
                                f"Tool output:\n{_truncate_tool_text(tool_output, 3000)}\n"
                                f"Tool error:\n{_truncate_tool_text(tool_error, 800)}\n\n"
                                "Respond to the user with the result. "
                                "Do not emit tool calls, JSON tool payloads, or pseudo-tags."
                            )

                            ok, followup_response = _stream_rag_pass(query_text=followup_query, context_text="")
                            if not ok:
                                return
                            if followup_response:
                                full_response += ("\n" + followup_response)
                            latest_response = followup_response

                        if executed_count:
                            _emit_event(
                                "tool_execution_summary",
                                {
                                    "executed": executed_count,
                                    "max_allowed": MAX_STREAM_TOOL_CALLS,
                                    "runtime_sec": round(time.time() - stream_start, 3),
                                },
                            )

                    # Final completion event (single terminal event for full pipeline)
                    _emit_event("complete", {"done": True})
                    # Commit memory after streaming completes
                    if INFRASTRUCTURE_AVAILABLE and _should_commit_memory(full_response):
                        try:
                            remember_conversation(command, full_response, session_id, {
                                'response_time': time.time(),
                                'client_ip': self.client_address[0],
                                'endpoint': '/stream'
                            }, user_id=user_id)
                        except Exception as e:
                            logger.debug(f"Streaming memory write failed (non-critical): {e}")
                    if INFRASTRUCTURE_AVAILABLE:
                        try:
                            learn_user_facts(command, session_id=session_id, user_id=user_id)
                        except Exception as e:
                            logger.debug(f"Streaming fact learning failed (non-critical): {e}")
                    return
                except Exception as e:
                    logger.debug(f"RAG streaming failed: {e}, falling back to simple response")
            
            # For commands or fallback, execute and stream result
            commands_script = ROXY_DIR / "roxy_commands.py"
            if commands_script.exists():
                env = os.environ.copy()
                if request_id:
                    env["ROXY_REQUEST_ID"] = request_id
                else:
                    env.pop("ROXY_REQUEST_ID", None)
                if session_id:
                    env["ROXY_SESSION_ID"] = session_id
                else:
                    env.pop("ROXY_SESSION_ID", None)
                env["ROXY_USER_ID"] = user_id
                if memory_context:
                    env["ROXY_MEMORY_CONTEXT"] = memory_context
                else:
                    env.pop("ROXY_MEMORY_CONTEXT", None)

                commands_python = ROXY_DIR / "venv" / "bin" / "python"
                python_exec = str(commands_python) if commands_python.exists() else sys.executable
                if os.getenv("ROXY_DEBUG_COMMANDS_PY", "").lower() in ("1", "true", "yes"):
                    logger.info(f"roxy_commands python_exec={python_exec}")
                result = subprocess.run(
                    [python_exec, str(commands_script), command],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=ROXY_DIR,
                    env=env
                )
                
                response_text = (result.stdout or result.stderr or "Command completed").strip()
                full_response = response_text
                
                # Stream response character by character for real-time feel
                for char in response_text:
                    event_data = json.dumps({"token": char, "done": False})
                    if not self._safe_write(f"data: {event_data}\n\n", request_id):
                        return
                    time.sleep(0.01)  # Small delay for readability
                
                self._safe_write(f"event: complete\ndata: {json.dumps({'done': True})}\n\n", request_id)
                if INFRASTRUCTURE_AVAILABLE and _should_commit_memory(full_response):
                    try:
                        remember_conversation(command, full_response, session_id, {
                            'response_time': time.time(),
                            'client_ip': self.client_address[0],
                            'endpoint': '/stream'
                        }, user_id=user_id)
                    except Exception as e:
                        logger.debug(f"Streaming memory write failed (non-critical): {e}")
                if INFRASTRUCTURE_AVAILABLE:
                    try:
                        learn_user_facts(command, session_id=session_id, user_id=user_id)
                    except Exception as e:
                        logger.debug(f"Streaming fact learning failed (non-critical): {e}")
            else:
                error_data = json.dumps({"error": "roxy_commands.py not found", "done": True})
                self._safe_write(f"event: error\ndata: {error_data}\n\n", request_id)
            
        except (BrokenPipeError, ConnectionResetError):
            logger.info(f"[STREAM] client disconnected requestId={request_id}")
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            error_data = json.dumps({"error": str(e), "done": True})
            self._safe_write(f"event: error\ndata: {error_data}\n\n", request_id)
    
    def do_POST(self):
        """Execute command endpoint"""
        # Support both versioned and unversioned paths
        path = self.path.split('?')[0]  # Remove query string
        
        if path == "/run" or path == "/v1/run":
            self._handle_run_command()
        elif path == "/batch" or path == "/v1/batch":
            self._handle_batch_command()
        elif path == "/benchmark" or path == "/v1/benchmark":
            self._handle_benchmark_mode()
        elif path == "/raw" or path == "/v1/raw":
            self._handle_raw_query()
        elif path == "/modes" or path == "/v1/modes":
            self._handle_list_modes()
        elif path == "/feedback" or path == "/v1/feedback":
            self._handle_feedback_submission()
        elif path == "/memory/recall" or path == "/v1/memory/recall":
            self._handle_memory_recall()
        elif path == "/expert" or path == "/v1/expert":
            self._handle_expert_route()
        elif path == "/warmup" or path == "/v1/warmup":
            self._handle_warmup()
        elif path == "/missions/run" or path == "/v1/missions/run":
            self._handle_missions_run()
        elif path == "/qualification/run" or path == "/v1/qualification/run":
            self._handle_qualification_run()
        elif path == "/github/status" or path == "/v1/github/status":
            # POST deprecated: use GET for read-only status
            self.send_response(405)
            self.send_header("Content-Type", "application/json")
            self.send_header("Allow", "GET")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "Method Not Allowed",
                "message": "Use GET /github/status for read-only status",
                "status_code": 405
            }).encode())
            return
        elif path.startswith("/mcp/"):
            self._handle_mcp_tool(path)
        # Benchmark run endpoint (PHASE 1)
        elif path == "/bench/run" or path == "/v1/bench/run":
            self._handle_bench_run()
        # Benchmark cancel endpoint (P0 operator control)
        elif path == "/bench/cancel" or path == "/v1/bench/cancel":
            self._handle_bench_cancel()
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_mcp_tool(self, path: str):
        """Handle MCP tool calls - /mcp/{module}/{tool}"""
        try:
            parts = path.strip('/').split('/')
            if len(parts) < 3:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid MCP path. Use /mcp/{module}/{tool}"}).encode())
                return
            
            _, module_name, tool_name = parts[0], parts[1], parts[2]
            
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b'{}'
            params = json.loads(body.decode('utf-8')) if body else {}
            
            # Load MCP module dynamically
            import importlib.util
            mcp_dir = Path.home() / ".roxy" / "mcp"
            module_path = mcp_dir / f"mcp_{module_name}.py"
            
            if not module_path.exists():
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"MCP module not found: {module_name}"}).encode())
                return
            
            spec = importlib.util.spec_from_file_location(f"mcp_{module_name}", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Call tool
            if hasattr(module, 'handle_tool'):
                result = module.handle_tool(tool_name, params)
            else:
                result = {"error": f"Module {module_name} has no handle_tool function"}
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except json.JSONDecodeError as e:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Invalid JSON: {e}"}).encode())
        except Exception as e:
            logger.error(f"MCP tool error: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_feedback_submission(self):
        """Handle user feedback submission"""
        try:
            # Auth check
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                    return
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            query = data.get('query', '')
            response = data.get('response', '')
            feedback_type = data.get('type', 'neutral')  # positive, negative, neutral, correction
            correction = data.get('correction')
            metadata = data.get('metadata', {})
            
            if not query or not response:
                self.send_error(400, "Query and response required")
                return
            
            if INFRASTRUCTURE_AVAILABLE:
                record_feedback(query, response, feedback_type, correction, metadata)
                result = {"status": "recorded", "type": feedback_type}
            else:
                result = {"status": "skipped", "reason": "feedback system unavailable"}
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            logger.error(f"Feedback submission failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def _handle_memory_recall(self):
        """Handle memory recall request"""
        try:
            # Auth check
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                    return
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            query = data.get('query', '').strip()
            k = int(data.get('k', data.get('limit', 5)))
            session_id = data.get('session_id')
            user_id = _resolve_request_user_id(self.headers, data.get("user_id"))
            time_window_days = data.get('time_window_days')
            min_score = data.get('min_score')
            min_similarity = data.get('min_similarity')
            if time_window_days is not None:
                try:
                    time_window_days = int(time_window_days)
                except Exception:
                    time_window_days = None
            if min_score is not None:
                try:
                    min_score = float(min_score)
                except Exception:
                    min_score = None
            if min_similarity is not None:
                try:
                    min_similarity = float(min_similarity)
                except Exception:
                    min_similarity = None
            
            if not query:
                self.send_error(400, "Query required")
                return
            
            if INFRASTRUCTURE_AVAILABLE:
                memories = recall_conversations(
                    query,
                    k,
                    session_id=session_id,
                    user_id=user_id,
                    time_window_days=time_window_days,
                    min_score=min_score,
                    min_similarity=min_similarity,
                )
            else:
                memories = []

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            sanitized = _json_sanitize(memories)
            self.wfile.write(json.dumps({"memories": sanitized, "count": len(sanitized)}).encode())
            
        except Exception as e:
            logger.error(f"Memory recall failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def _handle_expert_route(self):
        """Handle expert model routing"""
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        try:
            # Auth check
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                    return
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            query = data.get('query', '').strip()
            context = data.get('context', {})
            system_prompt = data.get('system')
            
            if not query:
                self.send_error(400, "Query required")
                return
            
            # Classify the query first
            if INFRASTRUCTURE_AVAILABLE:
                query_type, confidence = classify_query(query)
                response_text = route_query(query, context, system_prompt)
            else:
                query_type, confidence = 'general', 0.5
                # Fallback to standard Ollama
                response_text = query_ollama_direct(query)
            
            response_time = time.time() - start_time
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            # Convert query_type to string if it's an enum
            query_type_str = query_type.value if hasattr(query_type, 'value') else str(query_type)
            
            result = {
                "status": "success",
                "mode": "expert",
                "query_type": query_type_str,
                "confidence": confidence,
                "response": response_text,
                "response_time": round(response_time, 3),
                "request_id": request_id
            }
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            logger.error(f"Expert routing failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_benchmark_mode(self):
        """Handle benchmark mode - direct model access for testing"""
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        try:
            # Auth check
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                    return
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            prompt = data.get('prompt', '').strip()
            model = data.get('model') or _get_default_model()
            temperature = float(data.get('temperature', 0.0))
            max_tokens = int(data.get('max_tokens', 512))
            
            if not prompt:
                self.send_error(400, "No prompt provided")
                return
            
            logger.info(f"[BENCHMARK] model={model} temp={temperature} requestId={request_id}")
            
            # Direct Ollama query - NO personality, NO RAG, NO validation
            result = query_ollama_direct(prompt, model, temperature, max_tokens)
            
            response_time = time.time() - start_time
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            response = {
                "status": "success",
                "mode": "benchmark",
                "model": model,
                "result": result,
                "response_time": round(response_time, 3),
                "request_id": request_id
            }
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            logger.error(f"Benchmark mode failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def _handle_raw_query(self):
        """Handle raw query - technical mode with minimal processing"""
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        try:
            # Auth check
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                    return
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            prompt = data.get('prompt', '').strip()
            model = data.get('model') or _get_default_model()
            mode = data.get('mode', 'technical')
            
            if mode not in ROXY_MODES:
                mode = 'technical'
            
            mode_config = ROXY_MODES[mode]
            temperature = float(data.get('temperature', mode_config['temperature']))
            max_tokens = int(data.get('max_tokens', 1024))
            
            if not prompt:
                self.send_error(400, "No prompt provided")
                return
            
            logger.info(f"[RAW] mode={mode} model={model} requestId={request_id}")
            
            # Apply system prompt only if mode requires it
            if mode_config['system_prompt']:
                system = "You are ROXY, a helpful AI assistant. Be concise and accurate."
                full_prompt = f"System: {system}\n\nUser: {prompt}\n\nAssistant:"
            else:
                full_prompt = prompt
            
            result = query_ollama_direct(full_prompt, model, temperature, max_tokens)
            response_time = time.time() - start_time
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            response = {
                "status": "success",
                "mode": mode,
                "model": model,
                "result": result,
                "response_time": round(response_time, 3),
                "request_id": request_id
            }
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            logger.error(f"Raw query failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_warmup(self):
        """Warm up Ollama by issuing a minimal generate call."""
        base_url = _get_ollama_base_url()
        snapshot = _snapshot_ollama_health()
        result = {
            "ok": False,
            "base_url": base_url,
            "model": None,
            "latency_ms": snapshot.get("last_latency_ms"),
            "last_ok_ts": snapshot.get("last_ok_ts"),
            "last_error": snapshot.get("last_error"),
            "error": None,
        }

        try:
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                    return

            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b"{}"

            try:
                data = json.loads(body.decode('utf-8')) if body else {}
            except json.JSONDecodeError as exc:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {exc}"}).encode())
                return

            config_defaults = config if 'config' in globals() else {}
            model = (data.get("model") or config_defaults.get("default_model") or _get_default_model()).strip()
            result["model"] = model
            prompt = data.get("prompt", "Warmup check.")
            num_predict = max(1, int(data.get("num_predict", 1)))
            timeout = int(data.get("timeout", 30))

            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": num_predict
                }
            }

            import requests

            start_time = time.perf_counter()
            response = requests.post(f"{base_url}/api/generate", json=payload, timeout=timeout)
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200:
                _record_ollama_success(latency_ms)
                snapshot = _snapshot_ollama_health()
                result.update({
                    "ok": True,
                    "model": model,
                    "latency_ms": snapshot.get("last_latency_ms"),
                    "last_ok_ts": snapshot.get("last_ok_ts"),
                    "last_error": snapshot.get("last_error"),
                })
                status_code = 200
            else:
                error_msg = f"Status {response.status_code}: {response.text[:200]}"
                _record_ollama_error(error_msg)
                snapshot = _snapshot_ollama_health()
                result.update({
                    "ok": False,
                    "model": model,
                    "latency_ms": snapshot.get("last_latency_ms"),
                    "last_ok_ts": snapshot.get("last_ok_ts"),
                    "last_error": snapshot.get("last_error"),
                    "error": error_msg,
                })
                status_code = 502

        except Exception as exc:
            error_msg = str(exc)
            _record_ollama_error(error_msg)
            snapshot = _snapshot_ollama_health()
            result.update({
                "ok": False,
                "model": result.get("model"),
                "latency_ms": snapshot.get("last_latency_ms"),
                "last_ok_ts": snapshot.get("last_ok_ts"),
                "last_error": snapshot.get("last_error"),
                "error": error_msg,
            })
            status_code = 500

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())
    
    def _handle_github_status(self):
        """Get GitHub API status and user info"""
        try:
            # Auth check
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                    return
            
            # Check if requests is available
            try:
                import requests
            except ImportError:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "requests library not available"}).encode())
                return
            
            # Get GitHub token
            github_token = _get_github_token()
            
            # Check reachability
            reachability = _check_github_reachability(github_token)
            
            status = {
                "configured": bool(github_token),
                "reachable": reachability["reachable"],
                "latency_ms": reachability["latency_ms"],
                "error": reachability["error"],
                "rate_limit": reachability["rate_limit"],
                "user": None
            }
            
            # Get user info if reachable and configured
            if status["reachable"] and status["configured"]:
                user_info = _get_github_user_info(github_token)
                if "error" not in user_info:
                    status["user"] = user_info
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(status, indent=2).encode())
            
        except Exception as e:
            logger.error(f"GitHub status check failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def _github_auth_check(self) -> bool:
        """Check X-ROXY-Token for GitHub endpoints. Returns False if unauthorized (and sends 403)."""
        if AUTH_TOKEN:
            provided_token = self.headers.get('X-ROXY-Token')
            if not provided_token or provided_token != AUTH_TOKEN:
                self.send_response(403)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Unauthorized - X-ROXY-Token required"}).encode())
                return False
        return True
    
    def _parse_query_params(self) -> dict:
        """Parse query parameters from URL."""
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        # Flatten single-value lists
        return {k: v[0] if len(v) == 1 else v for k, v in params.items()}
    
    def _handle_github_repos(self):
        """GET /github/repos - List repos for authenticated user"""
        if not self._github_auth_check():
            return
        
        try:
            github_token = _get_github_token()
            if not github_token:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "GitHub not configured",
                    "hint": "Set GITHUB_TOKEN or GITHUB_PAT in systemd drop-in or config.json"
                }).encode())
                return
            
            params = self._parse_query_params()
            api_params = {
                "per_page": min(int(params.get("per_page", 30)), 100),
                "page": int(params.get("page", 1)),
                "sort": params.get("sort", "updated"),
                "type": params.get("type", "all")
            }
            
            result = _github_api_cached("/user/repos", "repos", github_token, api_params)
            
            if not result.get("success"):
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": result.get("error", "GitHub API error")}).encode())
                return
            
            # Normalize response
            repos = []
            for repo in result.get("data", []):
                repos.append({
                    "full_name": repo.get("full_name"),
                    "owner": repo.get("owner", {}).get("login"),
                    "name": repo.get("name"),
                    "description": repo.get("description"),
                    "private": repo.get("private"),
                    "fork": repo.get("fork"),
                    "language": repo.get("language"),
                    "default_branch": repo.get("default_branch"),
                    "updated_at": repo.get("updated_at"),
                    "pushed_at": repo.get("pushed_at"),
                    "stargazers_count": repo.get("stargazers_count"),
                    "open_issues_count": repo.get("open_issues_count"),
                    "html_url": repo.get("html_url")
                })
            
            response = {
                "repos": repos,
                "count": len(repos),
                "cached": result.get("_cached", False),
                "rate_limit": result.get("rate_limit")
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        except Exception as e:
            logger.error(f"GitHub repos failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def _handle_github_repo(self):
        """GET /github/repo - Get default repo info"""
        if not self._github_auth_check():
            return
        
        try:
            github_token = _get_github_token()
            default_repo = _get_default_repo()
            
            if not default_repo:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "No default repo configured",
                    "hint": "Set GITHUB_DEFAULT_REPO=owner/repo in env or github.default_owner/repo in config.json"
                }).encode())
                return
            
            if not github_token:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "GitHub not configured",
                    "hint": "Set GITHUB_TOKEN or GITHUB_PAT"
                }).encode())
                return
            
            endpoint = f"/repos/{default_repo['owner']}/{default_repo['repo']}"
            result = _github_api_cached(endpoint, "repo", github_token)
            
            if not result.get("success"):
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": result.get("error")}).encode())
                return
            
            repo = result.get("data", {})
            response = {
                "full_name": repo.get("full_name"),
                "owner": repo.get("owner", {}).get("login"),
                "name": repo.get("name"),
                "description": repo.get("description"),
                "private": repo.get("private"),
                "default_branch": repo.get("default_branch"),
                "language": repo.get("language"),
                "topics": repo.get("topics", []),
                "open_issues_count": repo.get("open_issues_count"),
                "open_pr_count": None,  # Would need separate API call
                "html_url": repo.get("html_url"),
                "clone_url": repo.get("clone_url"),
                "ssh_url": repo.get("ssh_url"),
                "ref": default_repo.get("ref", "main"),
                "default_repo_used": f"{default_repo['owner']}/{default_repo['repo']}",
                "cached": result.get("_cached", False),
                "rate_limit": result.get("rate_limit")
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        except Exception as e:
            logger.error(f"GitHub repo failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def _handle_github_issues(self):
        """GET /github/issues - List issues for default repo or specified owner/repo"""
        if not self._github_auth_check():
            return

        try:
            github_token = _get_github_token()
            if not github_token:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "GitHub not configured"}).encode())
                return

            params = self._parse_query_params()

            # Get repo from params or default
            owner = params.get("owner")
            repo = params.get("repo")
            default_repo_used = None

            if not owner or not repo:
                default_repo = _get_default_repo()
                if default_repo:
                    owner = owner or default_repo["owner"]
                    repo = repo or default_repo["repo"]
                    default_repo_used = f"{default_repo['owner']}/{default_repo['repo']}"
                else:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "error": "No repo specified and no default configured",
                        "hint": "Use ?owner=X&repo=Y or set GITHUB_DEFAULT_REPO"
                    }).encode())
                    return
            
            api_params = {
                "state": params.get("state", "open"),
                "per_page": min(int(params.get("limit", 50)), 100),
                "sort": params.get("sort", "updated"),
                "direction": params.get("direction", "desc")
            }
            
            endpoint = f"/repos/{owner}/{repo}/issues"
            result = _github_api_cached(endpoint, "issues", github_token, api_params)
            
            if not result.get("success"):
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": result.get("error")}).encode())
                return
            
            # Normalize issues (filter out PRs - they also come through issues endpoint)
            issues = []
            for issue in result.get("data", []):
                if "pull_request" not in issue:  # Skip PRs
                    issues.append({
                        "number": issue.get("number"),
                        "title": issue.get("title"),
                        "state": issue.get("state"),
                        "updated_at": issue.get("updated_at"),
                        "created_at": issue.get("created_at"),
                        "labels": [l.get("name") for l in issue.get("labels", [])],
                        "assignees": [a.get("login") for a in issue.get("assignees", [])],
                        "comments": issue.get("comments", 0),
                        "html_url": issue.get("html_url"),
                        "user": issue.get("user", {}).get("login")
                    })
            
            response = {
                "repo": f"{owner}/{repo}",
                "issues": issues,
                "count": len(issues),
                "state_filter": api_params["state"],
                "default_repo_used": default_repo_used,
                "cached": result.get("_cached", False),
                "rate_limit": result.get("rate_limit")
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        except Exception as e:
            logger.error(f"GitHub issues failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def _handle_github_pulls(self):
        """GET /github/pulls - List pull requests for default repo or specified owner/repo"""
        if not self._github_auth_check():
            return

        try:
            github_token = _get_github_token()
            if not github_token:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "GitHub not configured"}).encode())
                return

            params = self._parse_query_params()

            # Get repo from params or default
            owner = params.get("owner")
            repo = params.get("repo")
            default_repo_used = None

            if not owner or not repo:
                default_repo = _get_default_repo()
                if default_repo:
                    owner = owner or default_repo["owner"]
                    repo = repo or default_repo["repo"]
                    default_repo_used = f"{default_repo['owner']}/{default_repo['repo']}"
                else:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "error": "No repo specified and no default configured"
                    }).encode())
                    return
            
            api_params = {
                "state": params.get("state", "open"),
                "per_page": min(int(params.get("limit", 50)), 100),
                "sort": params.get("sort", "updated"),
                "direction": params.get("direction", "desc")
            }
            
            endpoint = f"/repos/{owner}/{repo}/pulls"
            result = _github_api_cached(endpoint, "pulls", github_token, api_params)
            
            if not result.get("success"):
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": result.get("error")}).encode())
                return
            
            # Normalize PRs
            pulls = []
            for pr in result.get("data", []):
                pulls.append({
                    "number": pr.get("number"),
                    "title": pr.get("title"),
                    "state": pr.get("state"),
                    "draft": pr.get("draft", False),
                    "updated_at": pr.get("updated_at"),
                    "created_at": pr.get("created_at"),
                    "merged_at": pr.get("merged_at"),
                    "head_branch": pr.get("head", {}).get("ref"),
                    "base_branch": pr.get("base", {}).get("ref"),
                    "labels": [l.get("name") for l in pr.get("labels", [])],
                    "assignees": [a.get("login") for a in pr.get("assignees", [])],
                    "html_url": pr.get("html_url"),
                    "user": pr.get("user", {}).get("login"),
                    "mergeable": pr.get("mergeable"),
                    "review_comments": pr.get("review_comments", 0),
                    "commits": pr.get("commits", 0),
                    "additions": pr.get("additions"),
                    "deletions": pr.get("deletions")
                })
            
            response = {
                "repo": f"{owner}/{repo}",
                "pulls": pulls,
                "count": len(pulls),
                "state_filter": api_params["state"],
                "default_repo_used": default_repo_used,
                "cached": result.get("_cached", False),
                "rate_limit": result.get("rate_limit")
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode())

        except Exception as e:
            logger.error(f"GitHub pulls failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def _handle_github_contents(self):
        """GET /github/contents - Get file/directory contents"""
        if not self._github_auth_check():
            return
        
        try:
            github_token = _get_github_token()
            if not github_token:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "GitHub not configured"}).encode())
                return
            
            params = self._parse_query_params()

            # Get repo from params or default
            owner = params.get("owner")
            repo = params.get("repo")
            path = params.get("path", "")
            ref = params.get("ref")
            default_repo_used = None

            if not owner or not repo:
                default_repo = _get_default_repo()
                if default_repo:
                    owner = owner or default_repo["owner"]
                    repo = repo or default_repo["repo"]
                    ref = ref or default_repo.get("ref", "main")
                    default_repo_used = f"{default_repo['owner']}/{default_repo['repo']}"
                else:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "error": "No repo specified and no default configured"
                    }).encode())
                    return
            
            api_params = {}
            if ref:
                api_params["ref"] = ref
            
            endpoint = f"/repos/{owner}/{repo}/contents/{path.lstrip('/')}"
            result = _github_api_cached(endpoint, "contents", github_token, api_params)
            
            if not result.get("success"):
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": result.get("error")}).encode())
                return
            
            data = result.get("data", {})
            
            # Handle directory listing
            if isinstance(data, list):
                contents = []
                for item in data:
                    contents.append({
                        "name": item.get("name"),
                        "path": item.get("path"),
                        "type": item.get("type"),  # "file" or "dir"
                        "size": item.get("size"),
                        "sha": item.get("sha"),
                        "html_url": item.get("html_url")
                    })
                
                response = {
                    "repo": f"{owner}/{repo}",
                    "path": path or "/",
                    "ref": ref or "default",
                    "type": "directory",
                    "contents": contents,
                    "count": len(contents),
                    "default_repo_used": default_repo_used,
                    "cached": result.get("_cached", False),
                    "rate_limit": result.get("rate_limit")
                }
            
            # Handle file
            else:
                import base64
                
                content = None
                is_binary = False
                encoding = data.get("encoding")
                
                if encoding == "base64" and data.get("content"):
                    try:
                        raw_content = base64.b64decode(data.get("content", ""))
                        # Check if binary (simple heuristic)
                        try:
                            content = raw_content.decode("utf-8")
                        except UnicodeDecodeError:
                            is_binary = True
                            content = f"[Binary file, {len(raw_content)} bytes]"
                    except Exception:
                        content = "[Decode error]"
                
                # Size limit for text content
                if content and len(content) > 100000:
                    content = content[:100000] + f"\n\n... [Truncated, total {len(content)} chars]"
                
                response = {
                    "repo": f"{owner}/{repo}",
                    "path": data.get("path", path),
                    "ref": ref or "default",
                    "type": "file",
                    "name": data.get("name"),
                    "size": data.get("size"),
                    "sha": data.get("sha"),
                    "encoding": encoding,
                    "is_binary": is_binary,
                    "content": content,
                    "html_url": data.get("html_url"),
                    "download_url": data.get("download_url"),
                    "default_repo_used": default_repo_used,
                    "cached": result.get("_cached", False),
                    "rate_limit": result.get("rate_limit")
                }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        except Exception as e:
            logger.error(f"GitHub contents failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def _handle_list_modes(self):
        """List available ROXY modes"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        modes_info = {}
        for mode_name, mode_config in ROXY_MODES.items():
            modes_info[mode_name] = {
                "description": mode_config['description'],
                "system_prompt": mode_config['system_prompt'],
                "temperature": mode_config['temperature']
            }
        
        response = {
            "modes": modes_info,
            "default": "broadcast",
            "endpoints": {
                "/run": "Full ROXY with personality (broadcast mode)",
                "/benchmark": "Direct model access, no personality",
                "/raw": "Configurable mode (technical, creative, etc.)",
                "/modes": "List available modes",
                "/infrastructure": "Infrastructure component status",
                "/infrastructure/stats": "Detailed infrastructure statistics",
                "/feedback/stats": "User feedback statistics"
            }
        }
        self.wfile.write(json.dumps(response, indent=2).encode())
    
    def _handle_infrastructure_status(self):
        """Return infrastructure component status"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        if INFRASTRUCTURE_AVAILABLE:
            status = get_infrastructure_status()
        else:
            status = {
                "initialized": False,
                "available": False,
                "message": "Infrastructure module not available"
            }
        
        self.wfile.write(json.dumps(status, indent=2).encode())
    
    def _handle_infrastructure_stats(self):
        """Return detailed infrastructure statistics"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        if INFRASTRUCTURE_AVAILABLE:
            stats = get_all_stats()
        else:
            stats = {
                "error": "Infrastructure not available",
                "timestamp": datetime.now().isoformat()
            }
        
        self.wfile.write(json.dumps(stats, indent=2).encode())
    
    def _handle_feedback_stats(self):
        """Return feedback statistics"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        if INFRASTRUCTURE_AVAILABLE:
            stats = get_feedback_stats()
        else:
            stats = {"error": "Feedback system not available"}
        
        self.wfile.write(json.dumps(stats, indent=2).encode())

    def _handle_run_command(self):
        """Handle single command execution"""
        start_time = time.time()
        client_ip = self.client_address[0]
        request_id = str(uuid.uuid4())[:8]
        
        # Track request metrics
        if METRICS_AVAILABLE:
            metrics_ctx = MetricsMiddleware(endpoint="/run")
            metrics_ctx.__enter__()
        else:
            metrics_ctx = None
        
        try:
            # Rate limiting - CRITICAL SECURITY FEATURE
            rate_limiting_enabled = config.get("rate_limiting_enabled", False)
            if rate_limiting_enabled:
                try:
                    sys.path.insert(0, str(ROXY_DIR))
                    from rate_limiting import get_rate_limiter
                    rate_limiter = get_rate_limiter()
                    if not rate_limiter.check_rate_limit(client_ip, "/run"):
                        if METRICS_AVAILABLE:
                            record_rate_limit("/run")
                        if METRICS_AVAILABLE and metrics_ctx:
                            metrics_ctx.set_status("rate_limited")
                            metrics_ctx.__exit__(None, None, None)
                        self.send_response(429)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        response = {"status": "error", "message": "Rate limit exceeded"}
                        self.wfile.write(json.dumps(response).encode())
                        return
                except ImportError as e:
                    logger.error(f"CRITICAL: Rate limiting module not available: {e}")
                    logger.error("Rate limiting is enabled in config but module is missing")
                    logger.error("Security feature unavailable - request blocked")
                    self.send_response(503)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    response = {"status": "error", "message": "Rate limiting service unavailable"}
                    self.wfile.write(json.dumps(response).encode())
                    return
                except Exception as e:
                    logger.error(f"Rate limiting check failed: {e}", exc_info=True)
                    # Fail secure: block request if rate limiting fails
                    self.send_response(503)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    response = {"status": "error", "message": "Rate limiting service error"}
                    self.wfile.write(json.dumps(response).encode())
                    return
            
            # Validate auth token if configured
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    user_agent = self.headers.get('User-Agent', 'unknown')
                    token_present = bool(provided_token)
                    token_hash_prefix = hashlib.sha256(provided_token.encode()).hexdigest()[:8] if token_present else "none"
                    reason = "missing_token" if not token_present else "invalid_token"
                    should_log, rate_limited = _register_unauthorized_attempt(client_ip, user_agent)
                    log_line = (
                        f"[AUTH] 403 requestId={request_id} ip={client_ip} path=/run "
                        f"ua=\"{user_agent}\" token_present={str(token_present).lower()} "
                        f"token_hash_prefix={token_hash_prefix} reason={reason}"
                    )
                    if rate_limited:
                        if should_log:
                            logger.warning(f"{log_line} action=rate_limited")
                        if METRICS_AVAILABLE and metrics_ctx:
                            metrics_ctx.set_status("rate_limited")
                            metrics_ctx.__exit__(None, None, None)
                        self.send_response(429)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        payload = {
                            "status": "error",
                            "message": "Too many unauthorized attempts",
                            "request_id": request_id,
                        }
                        self._safe_write(json.dumps(payload), request_id)
                        return

                    if should_log:
                        logger.warning(log_line)
                    else:
                        logger.debug(f"{log_line} (suppressed)")

                    if METRICS_AVAILABLE and metrics_ctx:
                        metrics_ctx.set_status("unauthorized")
                        metrics_ctx.__exit__(None, None, None)
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    payload = {
                        "status": "error",
                        "message": "Forbidden: Invalid or missing token",
                        "request_id": request_id,
                    }
                    self._safe_write(json.dumps(payload), request_id)
                    return
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            command = data.get('command', '').strip()
            if not command:
                self.send_error(400, "No command provided")
                return
            
            # Extract explicit mode and pool from request (Chief's operator controls)
            explicit_mode = data.get('mode', '').upper()  # CHAT, RAG, EXEC
            explicit_pool = data.get('pool', '').upper()  # AUTO, W5700X, 6900XT (or legacy BIG/FAST)
            model_override = data.get('model', '')  # Optional model override
            session_id = data.get('session_id') or self.headers.get('X-ROXY-Session') or request_id
            user_id = _resolve_request_user_id(self.headers, data.get("user_id"))
            
            # Security: Sanitize input - CRITICAL SECURITY FEATURE
            try:
                sys.path.insert(0, str(ROXY_DIR))
                from security import get_security
                security = get_security()
                sanitized = security.sanitize_input(command)
                    
                if sanitized.get("blocked"):
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    response = {
                        "status": "error",
                        "message": "Command blocked for security reasons",
                        "warnings": sanitized.get("warnings", [])
                    }
                    self.wfile.write(json.dumps(response).encode())
                    return
                
                # Use sanitized command
                command = sanitized.get("sanitized", command)
            except ImportError as e:
                logger.error(f"CRITICAL: Security module not available: {e}")
                logger.error("Security feature unavailable - request blocked")
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response = {"status": "error", "message": "Security service unavailable"}
                self.wfile.write(json.dumps(response).encode())
                return
            except Exception as e:
                logger.error(f"Security check failed: {e}", exc_info=True)
                # Fail secure: block request if security check fails
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response = {"status": "error", "message": "Security check error"}
                self.wfile.write(json.dumps(response).encode())
                return
            
            secret_scan_meta: Dict[str, Any] = {"enabled": False}
            if ENABLE_SECRET_SCAN_PREFLIGHT:
                secret_scan_meta = _run_secret_scan_preflight(force=False)
                if secret_scan_meta.get("blocked") and not SECRET_SCAN_DRY_RUN:
                    self.send_response(423)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    payload = {
                        "status": "error",
                        "message": "Secret preflight blocked execution",
                        "request_id": request_id,
                        "metadata": {"secret_scan": secret_scan_meta},
                    }
                    self._safe_write(json.dumps(payload), request_id)
                    return

            if _is_pure_greeting(command):
                response_time = time.time() - start_time
                result = "Hi! I'm ROXY, your resident AI assistant. How can I help you today?"
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response = {
                    "status": "success",
                    "command": command,
                    "result": result,
                    "response_time": round(response_time, 3),
                    "metadata": {
                        "trace_id": request_id,
                        "mode": explicit_mode.lower() if explicit_mode else "auto",
                        "route": "greeting_fastpath",
                        "pool": explicit_pool.lower() if explicit_pool else "auto",
                        "memory": {
                            "enabled": False,
                            "context_injected": False,
                            "context_chars": 0,
                            "memory_items": 0,
                            "profile_items": 0,
                            "typed_record_items": 0,
                            "repo_context_items": 0,
                            "facts_learned": 0,
                            "user_id": user_id,
                        },
                        "secret_scan": secret_scan_meta,
                    },
                }
                self.wfile.write(json.dumps(response).encode())
                if METRICS_AVAILABLE and metrics_ctx:
                    metrics_ctx.set_status("success")
                    metrics_ctx.__exit__(None, None, None)
                return

            logger.info(
                f"Executing command: {command} mode={explicit_mode or 'auto'} "
                f"pool={explicit_pool or 'auto'} request_id={request_id}"
            )

            memory_context = ""
            memory_context_meta = {
                "enabled": False,
                "memory_items": 0,
                "profile_items": 0,
                "typed_record_items": 0,
                "repo_context_items": 0,
                "context_chars": 0,
            }
            memory_context, memory_context_meta = _build_memory_context_for_prompt(
                command,
                session_id,
                user_id=user_id,
            )

            agentic_meta = {
                "intent": "general",
                "complex": False,
                "needs_clarification": False,
                "clarifying_question": "",
                "plan_steps": [],
            }
            if ENABLE_AGENTIC_PIPELINE:
                agentic_meta = _analyze_agentic_request(command)
                if agentic_meta.get("needs_clarification"):
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    response = {
                        "status": "clarification_needed",
                        "command": command,
                        "result": agentic_meta.get("clarifying_question"),
                        "metadata": {
                            "mode": "agentic",
                            "route": "clarification",
                            "memory": {
                                "context_injected": bool(memory_context),
                                "context_chars": int(memory_context_meta.get("context_chars", 0)),
                                "memory_items": int(memory_context_meta.get("memory_items", 0)),
                                "profile_items": int(memory_context_meta.get("profile_items", 0)),
                                "typed_record_items": int(memory_context_meta.get("typed_record_items", 0)),
                                "repo_context_items": int(memory_context_meta.get("repo_context_items", 0)),
                            },
                            "agentic": {
                                "intent": agentic_meta.get("intent"),
                                "complex_query": bool(agentic_meta.get("complex")),
                                "needs_clarification": True,
                                "plan_steps": agentic_meta.get("plan_steps", []),
                            },
                        },
                    }
                    self.wfile.write(json.dumps(response).encode())
                    return
            
            # Track execution timing for metadata
            exec_start = time.time()
            
            # Route through existing roxy_commands.py with explicit mode/pool
            result = self._execute_command(
                command, 
                request_id=request_id,
                mode=explicit_mode,
                pool=explicit_pool,
                model_override=model_override,
                session_id=session_id,
                user_id=user_id,
                memory_context=memory_context,
                plan_steps=agentic_meta.get("plan_steps", []),
            )
            memory_rescue_attempted = False
            memory_rescue_applied = False
            if ENABLE_AGENTIC_PIPELINE and _should_attempt_memory_rescue(command, result, memory_context):
                memory_rescue_attempted = True
                rescue_prompt = (
                    "Use known user memory facts to answer directly and concisely. "
                    "If unknown, say unknown without guessing.\n"
                    f"Question: {command}"
                )
                rescue_result = self._execute_command(
                    rescue_prompt,
                    request_id=request_id,
                    mode="CHAT",
                    pool=explicit_pool,
                    model_override=model_override,
                    session_id=session_id,
                    user_id=user_id,
                    memory_context=memory_context,
                    plan_steps=[],
                )
                if (
                    rescue_result
                    and not str(rescue_result).startswith("ERROR:")
                    and not _response_indicates_memory_miss(str(rescue_result))
                ):
                    result = rescue_result
                    memory_rescue_applied = True
            exec_end = time.time()
            response_time = exec_end - start_time
            total_ms = round((exec_end - exec_start) * 1000, 1)

            exec_meta_ref = getattr(self, '_last_execution_metadata', {})
            if isinstance(exec_meta_ref, dict) and ("total_ms" not in exec_meta_ref or not exec_meta_ref.get("cache_hit")):
                exec_meta_ref["total_ms"] = total_ms
            
            # CHIEF P0: Pool errors must be HTTP errors, not embedded strings
            if isinstance(result, str) and result.startswith("ERROR:"):
                error_msg = result[6:].strip()  # Remove "ERROR:" prefix
                # Determine HTTP status based on error type
                if "MISCONFIGURED" in error_msg or "distinct" in error_msg.lower():
                    http_status = 400  # Bad Request - configuration error
                elif "not reachable" in error_msg.lower():
                    http_status = 503  # Service Unavailable - pool down
                elif "not configured" in error_msg.lower():
                    http_status = 400  # Bad Request - missing configuration
                else:
                    http_status = 503  # Default to service unavailable
                
                if METRICS_AVAILABLE and metrics_ctx:
                    metrics_ctx.set_status("pool_error")
                    metrics_ctx.__exit__(None, None, None)
                
                self.send_response(http_status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                exec_meta = getattr(self, '_last_execution_metadata', {})
                response = {
                    "status": "error",
                    "error": error_msg,
                    "command": command,
                    "metadata": {
                        "mode": exec_meta.get("mode", explicit_mode.lower() or "auto"),
                        "pool": exec_meta.get("pool", explicit_pool.lower() or "auto"),
                        "pool_error": True
                    }
                }
                self.wfile.write(json.dumps(response).encode())
                return
            
            # Record metrics for successful execution
            if METRICS_AVAILABLE and metrics_ctx:
                metrics_ctx.set_status("success")
            
            # Security: Filter output - CRITICAL SECURITY FEATURE
            try:
                sys.path.insert(0, str(ROXY_DIR))
                from security import get_security
                security = get_security()
                filtered = security.filter_output(result)
                result = filtered.get("filtered", result)
                if filtered.get("warnings"):
                    logger.warning(f"Output filtered: {filtered['warnings']}")
            except ImportError as e:
                logger.error(f"CRITICAL: Security module not available for output filtering: {e}")
                logger.error("Output filtering disabled - potential security risk")
                # Don't block response, but log error
            except Exception as e:
                logger.error(f"Output filtering failed: {e}", exc_info=True)
                # Log but don't block - output filtering is less critical than input

            proactive_suggestions: List[str] = []
            if ENABLE_AGENTIC_PIPELINE:
                result, proactive_suggestions = _append_proactive_suggestions(command, result)
                _update_goal_tracker(session_id, command, result)
            
            # Observability - ALWAYS log (don't swallow errors)
            sys.path.insert(0, str(ROXY_DIR))
            from observability import get_observability
            obs = get_observability()
            obs.log_request(command, result, response_time, 
                           metadata={"request_id": request_id},
                           request_id=request_id,
                           endpoint="/run")
            
            # Evaluation metrics - Non-critical, allow graceful degradation
            try:
                sys.path.insert(0, str(ROXY_DIR))
                from evaluation.metrics import get_metrics_collector
                collector = get_metrics_collector()
                collector.record_query(
                    query=command,
                    response=result,
                    response_time=response_time,
                    source_attribution="📌" in result or "Source:" in result
                )
            except ImportError:
                # Metrics module not available - not critical, continue
                pass
            except Exception as e:
                logger.warning(f"Metrics collection failed: {e}")
                # Non-critical, continue execution
            
            # Infrastructure integration - Cache, Memory, Events (non-blocking)
            learned_facts = []
            if INFRASTRUCTURE_AVAILABLE:
                try:
                    # Cache the response with routing metadata preserved
                    exec_meta = getattr(self, '_last_execution_metadata', {})
                    cache_metadata = {
                        "mode": exec_meta.get("mode", "auto"),
                        "route": exec_meta.get("route", "unknown"),
                        "model_used": exec_meta.get("model_used"),
                        "pool": exec_meta.get("pool", "auto"),
                        "base_url_used": exec_meta.get("base_url_used", _get_ollama_base_url()),
                        "tools_executed": exec_meta.get("tools_executed", []),
                        "total_ms": exec_meta.get("total_ms") if isinstance(exec_meta, dict) else None,
                        "memory_context_chars": exec_meta.get("memory_context_chars", 0) if isinstance(exec_meta, dict) else 0,
                    }
                    cache_query(command, result, metadata=cache_metadata)
                    
                    # Store in episodic memory (skip if memory_store already wrote)
                    exec_meta = getattr(self, '_last_execution_metadata', {})
                    flags = exec_meta.get("flags", {}) if isinstance(exec_meta, dict) else {}
                    skip_memory = isinstance(exec_meta, dict) and (
                        exec_meta.get("route") == "memory_store" or flags.get("memory_store") is True
                    )
                    if not skip_memory:
                        remember_conversation(command, result, session_id, {
                            'response_time': response_time,
                            'client_ip': client_ip,
                            'endpoint': '/run',
                            'intent': agentic_meta.get("intent"),
                            'complex_query': bool(agentic_meta.get("complex")),
                            'proactive_suggestions': len(proactive_suggestions),
                        }, user_id=user_id)
                    try:
                        fact_learning = learn_user_facts(command, session_id=session_id, user_id=user_id)
                        learned_facts = fact_learning.get("learned", []) if isinstance(fact_learning, dict) else []
                    except Exception as e:
                        logger.debug(f"User fact learning failed (non-critical): {e}")
                    
                    # Publish response event
                    publish_response_event(
                        query=command,
                        response=result,
                        elapsed=response_time,
                        session_id=session_id,
                        cached=False
                    )
                except Exception as e:
                    logger.debug(f"Infrastructure integration failed (non-critical): {e}")
            
            # Reflection/Verification pass - check for hallucinations, regenerate if needed
            try:
                truth_packet_snippet = ""
                model_used = exec_meta.get("selected_model") or exec_meta.get("model_used") or "qwen2.5-coder:14b-instruct"
                result, verification = _verify_and_enhance_with_retry(
                    query=command,
                    response_text=result,
                    memory_context=memory_context,
                    truth_packet=truth_packet_snippet,
                    session_id=session_id,
                    model=model_used
                )
            except Exception as e:
                logger.debug(f"Response verification failed (non-critical): {e}")
                verification = {"confidence": 1.0, "flags": [], "needs_reflection": False}
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            # Build response with execution metadata (Chief's Truth Panel)
            exec_meta = getattr(self, '_last_execution_metadata', {})
            reported_total_ms = None
            if isinstance(exec_meta, dict):
                reported_total_ms = exec_meta.get("total_ms")
            if reported_total_ms is None and 'total_ms' in locals():
                reported_total_ms = total_ms
            response = {
                "status": "success",
                "command": command,
                "result": result,
                "response_time": round(response_time, 3),
                "metadata": {
                    "mode": exec_meta.get("mode", "auto"),
                    "model_used": exec_meta.get("model_used"),
                    "selected_model": exec_meta.get("selected_model") or exec_meta.get("model_used"),
                    "trace_id": request_id,
                    "route": exec_meta.get("route", "unknown"),
                    "pool": exec_meta.get("pool", "auto"),
                    "base_url_used": exec_meta.get("base_url_used", _get_ollama_base_url()),
                    "total_ms": reported_total_ms,
                    "cache_hit": exec_meta.get("cache_hit", False),
                    "tools_count": len(exec_meta.get("tools_executed", []))
                }
            }
            debug_echo = os.getenv("ROXY_DEBUG_ECHO", "").lower() in ("1", "true", "yes")
            if self.headers.get("X-ROXY-Debug", "").lower() in ("1", "true", "yes"):
                debug_echo = True
            if debug_echo:
                response["metadata"]["request_echo"] = command
            # Add proof-grade metadata for pool + memory state
            base_url_used = response["metadata"].get("base_url_used")
            lane = _infer_gpu_lane(base_url_used)
            if lane:
                response["metadata"]["gpu_lane"] = lane
            memory_status = {"enabled": False}
            if INFRASTRUCTURE_AVAILABLE:
                try:
                    infra = get_infrastructure_status()
                    mem = infra.get("components", {}).get("postgres_memory", {})
                    memory_status["enabled"] = bool(mem.get("healthy"))
                    if mem.get("backend"):
                        memory_status["backend"] = mem.get("backend")
                    if mem.get("error"):
                        memory_status["error"] = mem.get("error")
                except Exception as e:
                    memory_status["error"] = str(e)
            response["metadata"]["memory"] = memory_status
            response["metadata"]["memory"]["context_injected"] = bool(memory_context)
            response["metadata"]["memory"]["context_chars"] = int(memory_context_meta.get("context_chars", 0))
            response["metadata"]["memory"]["memory_items"] = int(memory_context_meta.get("memory_items", 0))
            response["metadata"]["memory"]["profile_items"] = int(memory_context_meta.get("profile_items", 0))
            response["metadata"]["memory"]["typed_record_items"] = int(memory_context_meta.get("typed_record_items", 0))
            response["metadata"]["memory"]["repo_context_items"] = int(memory_context_meta.get("repo_context_items", 0))
            response["metadata"]["memory"]["facts_learned"] = len(learned_facts)
            response["metadata"]["memory"]["user_id"] = user_id
            response["metadata"]["memory"]["identity_conflict"] = bool(memory_context_meta.get("identity_conflict", False))
            response["metadata"]["memory"]["identity_candidates"] = memory_context_meta.get("identity_candidates", [])
            response["metadata"]["agentic"] = {
                "enabled": ENABLE_AGENTIC_PIPELINE,
                "intent": agentic_meta.get("intent"),
                "complex_query": bool(agentic_meta.get("complex")),
                "plan_steps": agentic_meta.get("plan_steps", []),
                "needs_clarification": bool(agentic_meta.get("needs_clarification")),
                "memory_rescue_attempted": memory_rescue_attempted,
                "memory_rescue_applied": memory_rescue_applied,
                "proactive_suggestions_added": len(proactive_suggestions),
                **_goal_tracker_summary(session_id),
            }
            # Add reflection/verification metadata
            response["metadata"]["reflection"] = {
                "confidence": verification.get("confidence", 1.0),
                "flags": verification.get("flags", []),
                "needs_reflection": verification.get("needs_reflection", False),
                "unverified_claims": verification.get("unverified_claims", []),
            }
            response["metadata"]["secret_scan"] = secret_scan_meta
            self.wfile.write(json.dumps(response).encode())
            
            # Mark metrics as successful and close context
            if METRICS_AVAILABLE and metrics_ctx:
                metrics_ctx.set_status("success")
                metrics_ctx.__exit__(None, None, None)
                
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"Command execution failed: {e}")
            
            # Mark metrics as error and close context
            if METRICS_AVAILABLE and metrics_ctx:
                metrics_ctx.set_status("error")
                metrics_ctx.__exit__(type(e), e, None)
            
            # Log error to observability
            try:
                sys.path.insert(0, str(ROXY_DIR))
                from observability import get_observability
                obs = get_observability()
                obs.log_error(command if 'command' in locals() else "", str(e))
            except:
                pass
            
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"status": "error", "message": str(e)}
            self.wfile.write(json.dumps(response).encode())
    
    def _handle_batch_command(self):
        """Handle batch command execution"""
        start_time = time.time()
        client_ip = self.client_address[0]
        request_id = str(uuid.uuid4())[:8]
        
        # Track request metrics
        if METRICS_AVAILABLE:
            metrics_ctx = MetricsMiddleware(endpoint="/batch")
            metrics_ctx.__enter__()
        else:
            metrics_ctx = None
        
        try:
            # Rate limiting - CRITICAL SECURITY FEATURE
            rate_limiting_enabled = config.get("rate_limiting_enabled", False)
            if rate_limiting_enabled:
                try:
                    sys.path.insert(0, str(ROXY_DIR))
                    from rate_limiting import get_rate_limiter
                    rate_limiter = get_rate_limiter()
                    if not rate_limiter.check_rate_limit(client_ip, "/batch"):
                        if METRICS_AVAILABLE:
                            record_rate_limit("/batch")
                        if METRICS_AVAILABLE and metrics_ctx:
                            metrics_ctx.set_status("rate_limited")
                            metrics_ctx.__exit__(None, None, None)
                        self.send_response(429)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        response = {"status": "error", "message": "Rate limit exceeded"}
                        self.wfile.write(json.dumps(response).encode())
                        return
                except ImportError as e:
                    logger.error(f"CRITICAL: Rate limiting module not available: {e}")
                    logger.error("Rate limiting is enabled in config but module is missing")
                    logger.error("Security feature unavailable - request blocked")
                    self.send_response(503)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    response = {"status": "error", "message": "Rate limiting service unavailable"}
                    self.wfile.write(json.dumps(response).encode())
                    return
                except Exception as e:
                    logger.error(f"Rate limiting check failed: {e}", exc_info=True)
                    # Fail secure: block request if rate limiting fails
                    self.send_response(503)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    response = {"status": "error", "message": "Rate limiting service error"}
                    self.wfile.write(json.dumps(response).encode())
                    return
            
            # Validate auth token if configured
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    user_agent = self.headers.get('User-Agent', 'unknown')
                    token_present = bool(provided_token)
                    token_hash_prefix = hashlib.sha256(provided_token.encode()).hexdigest()[:8] if token_present else "none"
                    reason = "missing_token" if not token_present else "invalid_token"
                    should_log, rate_limited = _register_unauthorized_attempt(client_ip, user_agent)
                    log_line = (
                        f"[AUTH] 403 requestId={request_id} ip={client_ip} path=/batch "
                        f"ua=\"{user_agent}\" token_present={str(token_present).lower()} "
                        f"token_hash_prefix={token_hash_prefix} reason={reason}"
                    )
                    if rate_limited:
                        if should_log:
                            logger.warning(f"{log_line} action=rate_limited")
                        if METRICS_AVAILABLE and metrics_ctx:
                            metrics_ctx.set_status("rate_limited")
                            metrics_ctx.__exit__(None, None, None)
                        self.send_response(429)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        payload = {
                            "status": "error",
                            "message": "Too many unauthorized attempts",
                            "request_id": request_id,
                        }
                        self._safe_write(json.dumps(payload), request_id)
                        return

                    if should_log:
                        logger.warning(log_line)
                    else:
                        logger.debug(f"{log_line} (suppressed)")

                    if METRICS_AVAILABLE and metrics_ctx:
                        metrics_ctx.set_status("unauthorized")
                        metrics_ctx.__exit__(None, None, None)
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    payload = {
                        "status": "error",
                        "message": "Forbidden: Invalid or missing token",
                        "request_id": request_id,
                    }
                    self._safe_write(json.dumps(payload), request_id)
                    return
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            commands = data.get('commands', [])
            batch_session_id = data.get('session_id') or self.headers.get('X-ROXY-Session') or request_id
            batch_user_id = _resolve_request_user_id(self.headers, data.get("user_id"))
            if not commands or not isinstance(commands, list):
                self.send_error(400, "No commands provided or invalid format")
                return
            
            logger.info(f"Executing batch: {len(commands)} commands")
            
            # Execute commands in parallel (async batch processing)
            import concurrent.futures
            results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = {
                    executor.submit(
                        self._execute_command,
                        cmd,
                        request_id=f"{request_id}:{idx}",
                        session_id=batch_session_id,
                        user_id=batch_user_id,
                    ): cmd
                    for idx, cmd in enumerate(commands)
                }
                for future in concurrent.futures.as_completed(futures):
                    cmd = futures[future]
                    try:
                        result = future.result(timeout=30)
                        results.append({"command": cmd, "status": "success", "result": result})
                    except Exception as e:
                        results.append({"command": cmd, "status": "error", "error": str(e)})
            
            response_time = time.time() - start_time
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            response = {
                "status": "success",
                "commands": results,
                "total": len(commands),
                "response_time": round(response_time, 3)
            }
            self.wfile.write(json.dumps(response).encode())
            
            # Close metrics context on success
            if METRICS_AVAILABLE and metrics_ctx:
                metrics_ctx.set_status("success")
                metrics_ctx.__exit__(None, None, None)
            
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"Batch command execution failed: {e}")
            
            # Close metrics context on error
            if METRICS_AVAILABLE and metrics_ctx:
                metrics_ctx.set_status("error")
                metrics_ctx.__exit__(type(e), e, None)
            
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"status": "error", "message": str(e)}
            self.wfile.write(json.dumps(response).encode())
    
    def _execute_command(
        self,
        command: str,
        request_id: Optional[str] = None,
        mode: str = "",
        pool: str = "",
        model_override: str = "",
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        memory_context: str = "",
        plan_steps: Optional[List[str]] = None,
    ) -> str:
        """Execute command via roxy_commands.py with caching and validation

        Args:
            command: The user command to execute
            request_id: Optional request tracking ID
            mode: Explicit mode (CHAT, RAG, EXEC) - empty means auto-route
            pool: Explicit pool (AUTO, W5700X, 6900XT or legacy BIG/FAST) - empty means auto
            model_override: Optional model name override
            session_id: Optional conversation session identifier
            user_id: Optional user identifier for memory/profile isolation
            memory_context: Optional prebuilt memory/profile context for prompt injection
            plan_steps: Optional execution plan hints for agentic prompting
        """
        effective_session_id = session_id or self.headers.get('X-ROXY-Session') or request_id
        effective_user_id = _sanitize_user_id(user_id)
        effective_memory_context = memory_context or ""
        effective_plan_steps = [step.strip() for step in (plan_steps or []) if str(step).strip()]
        if not effective_memory_context:
            try:
                built_context, _ = _build_memory_context_for_prompt(
                    command,
                    effective_session_id,
                    user_id=effective_user_id,
                )
                effective_memory_context = built_context or ""
            except Exception as e:
                logger.debug(f"Memory context assembly failed in execute path: {e}")
        
        # Initialize execution metadata for this call
        self._last_execution_metadata = {
            "mode": mode.lower() if mode else "auto",
            "model_used": model_override or None,
            "route": "unknown",
            "pool": pool.lower() if pool else "auto",
            "base_url_used": _get_ollama_base_url(),
            "tools_executed": [],
            "memory_context_chars": len(effective_memory_context),
            "plan_steps": effective_plan_steps,
        }
        
        # GREETING FASTPATH - keep health/smoke interactions off the heavy execution path.
        disable_greeting_fastpath = os.getenv("ROXY_DISABLE_GREETING_FASTPATH", "0").lower() in ("1", "true", "yes")
        allow_greeting_header = self.headers.get("X-ROXY-Allow-Greeting", "").lower() in ("1", "true", "yes")
        greeting_fastpath_enabled = (not disable_greeting_fastpath) or allow_greeting_header
        if _is_pure_greeting(command) and greeting_fastpath_enabled:
            return "Hi! I'm ROXY, your resident AI assistant. How can I help you today?"

        normalized_command = (command or "").strip().lower()
        if normalized_command == "git status":
            try:
                git_result = subprocess.run(
                    ["git", "-C", str(ROXY_DIR), "status", "--short", "--branch"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                )
                git_output = (git_result.stdout or git_result.stderr or "").strip()
                self._last_execution_metadata.update(
                    {
                        "route": "local_fastpath_git_status",
                        "mode": "exec",
                        "model_used": None,
                        "tools_executed": [],
                    }
                )
                return git_output or "No changes"
            except Exception as exc:
                logger.debug(f"git status fastpath failed, falling back: {exc}")
        
        # CONVERSATIONAL BYPASS - Detect casual chat (for Truth Gate)
        casual_chat_patterns = [
            r"(how are you|how'?s?\s+you|how do you feel|are you ok)",
            r"(tell me (a joke|something|about yourself))",
            r"(what do you think|your opinion)",
        ]
        is_casual_chat = any(re.search(p, command, re.IGNORECASE) for p in casual_chat_patterns)
        
        # Get context from conversation history
        try:
            sys.path.insert(0, str(ROXY_DIR))
            from context_manager import get_context_manager
            context_mgr = get_context_manager()
            context = context_mgr.get_context(command, include_recent=5)
        except Exception as e:
            logger.debug(f"Context manager failed: {e}")
            context = None
        
        # CHIEF'S CACHE FIX: Never bypass routing for tool-forcing or file queries
        # Cache discipline: only cache AFTER we know mode == "rag" from roxy_commands
        
        # Skip cache for anything that needs preflight routing
        bypass_cache = (
            command.strip().startswith('{') or  # JSON tool calls
            command.startswith('RUN_TOOL ') or  # Explicit tool syntax
            self._is_file_claim_query(command)  # File-existence queries
        )
        if effective_memory_context:
            # Personalized responses should not use generic cache entries.
            bypass_cache = True
        
        # Check cache first (for pure RAG queries only)
        if not bypass_cache and self._is_rag_query(command):
            try:
                # Use infrastructure cache (Redis with fallback)
                if INFRASTRUCTURE_AVAILABLE:
                    cached = get_cached_response(command)
                else:
                    sys.path.insert(0, str(ROXY_DIR))
                    from cache import get_cache as get_legacy_cache
                    cache = get_legacy_cache()
                    cached = cache.get(command) if cache else None
                    
                if cached:
                    # Record cache hit
                    if METRICS_AVAILABLE:
                        record_cache_hit()
                    cached_payload = cached if isinstance(cached, dict) else {"response": cached, "metadata": {}}

                    response_text = cached_payload.get("response", "")
                    similarity = cached_payload.get("similarity")
                    cached_query = cached_payload.get("cached_query", "")
                    if similarity is not None and similarity < 0.9 and cached_query:
                        response_text += f"\n\n(Similar to: {cached_query[:50]}...)"

                    cached_metadata = cached_payload.get("metadata") or {}
                    self._last_execution_metadata.update({
                        "mode": cached_metadata.get("mode", self._last_execution_metadata.get("mode", "auto")),
                        "route": cached_metadata.get("route", self._last_execution_metadata.get("route", "rag")),
                        "model_used": cached_metadata.get("model_used", self._last_execution_metadata.get("model_used")),
                        "pool": cached_metadata.get("pool", self._last_execution_metadata.get("pool", "auto")),
                        "base_url_used": cached_metadata.get("base_url_used", self._last_execution_metadata.get("base_url_used", _get_ollama_base_url())),
                        "tools_executed": cached_metadata.get("tools_executed", self._last_execution_metadata.get("tools_executed", [])),
                        "memory_context_chars": cached_metadata.get(
                            "memory_context_chars",
                            self._last_execution_metadata.get("memory_context_chars", 0),
                        ),
                    })
                    if "total_ms" in cached_metadata:
                        self._last_execution_metadata["total_ms"] = cached_metadata["total_ms"]
                    self._last_execution_metadata["cache_hit"] = True

                    return response_text
                else:
                    # Record cache miss
                    if METRICS_AVAILABLE:
                        record_cache_miss()
            except Exception as e:
                logger.debug(f"Cache lookup failed: {e}")
                if METRICS_AVAILABLE:
                    record_cache_miss()
        
        # Define commands script path
        commands_script = ROXY_DIR / "roxy_commands.py"
        if not commands_script.exists():
            return "ERROR: roxy_commands.py not found"
        
        # Acquire semaphore to limit concurrent subprocess spawns (prevent system overload)
        with subprocess_semaphore:
            try:
                env = os.environ.copy()
                if request_id:
                    env["ROXY_REQUEST_ID"] = request_id
                else:
                    env.pop("ROXY_REQUEST_ID", None)
                if effective_session_id:
                    env["ROXY_SESSION_ID"] = effective_session_id
                else:
                    env.pop("ROXY_SESSION_ID", None)
                env["ROXY_USER_ID"] = effective_user_id
                if effective_memory_context:
                    env["ROXY_MEMORY_CONTEXT"] = effective_memory_context
                else:
                    env.pop("ROXY_MEMORY_CONTEXT", None)
                if effective_plan_steps:
                    env["ROXY_PLAN_CONTEXT"] = "\n".join(
                        f"{idx}. {step}" for idx, step in enumerate(effective_plan_steps, start=1)
                    )
                else:
                    env.pop("ROXY_PLAN_CONTEXT", None)
                
                # Pass explicit operator controls as env vars (Chief's mode/pool)
                # --- CHIEF'S LOGIC: Strict Pool Enforcement ---
                effective_mode = mode.upper() if mode else "AUTO"
                effective_pool = pool.upper() if pool else "AUTO"
                pool_config = _resolve_ollama_pools()

                # Normalize pool aliases using pool_identity module (handles deprecation warnings)
                _, pool_canonical = normalize_pool_key(effective_pool)
                pool_normalized = pool_canonical.upper()  # This code expects uppercase

                # HARD INVARIANT: Check for misconfiguration (W5700X == 6900XT)
                if pool_config["misconfigured"]:
                    if effective_mode == "CHAT" and pool_normalized == "AUTO":
                        return "ERROR: CHAT mode requires distinct W5700X/6900XT pools. Pools are MISCONFIGURED (both point to same endpoint). Fix ROXY_OLLAMA_W5700X_URL and ROXY_OLLAMA_6900XT_URL."
                    elif pool_normalized in ("W5700X", "6900XT"):
                        return f"ERROR: Pool {pool_normalized} requested but pools are MISCONFIGURED (both point to same endpoint). Fix ROXY_OLLAMA_W5700X_URL and ROXY_OLLAMA_6900XT_URL."

                # AUTO pool: default to 6900XT for max strength unless explicitly overridden.
                if pool_normalized == "AUTO":
                    xt6900_reach = _check_ollama_reachability(pool_config["6900xt"]["url"])
                    if pool_config["6900xt"]["configured"] and xt6900_reach["reachable"]:
                        pool_normalized = "6900XT"
                    else:
                        w5700x_reach = _check_ollama_reachability(pool_config["w5700x"]["url"])
                        if pool_config["w5700x"]["configured"] and w5700x_reach["reachable"]:
                            pool_normalized = "W5700X"
                            logger.warning("AUTO pool fallback -> W5700X (6900XT unavailable)")
                        else:
                            reason = "6900XT not configured/reachable and W5700X unavailable"
                            return f"ERROR: No reachable pool for AUTO. Configure ROXY_OLLAMA_6900XT_URL (preferred) or ROXY_OLLAMA_W5700X_URL. {reason}."

                # Validate explicit requests (also check reachability)
                if pool_normalized == "W5700X":
                    if not pool_config["w5700x"]["configured"]:
                        return "ERROR: Pool W5700X requested but not configured (ROXY_OLLAMA_W5700X_URL missing)."
                    w5700x_reach = _check_ollama_reachability(pool_config["w5700x"]["url"])
                    if not w5700x_reach["reachable"]:
                        return f"ERROR: Pool W5700X requested but not reachable ({pool_config['w5700x']['url']}: {w5700x_reach['error']})."
                if pool_normalized == "6900XT":
                    if not pool_config["6900xt"]["configured"]:
                        return "ERROR: Pool 6900XT requested but not configured (ROXY_OLLAMA_6900XT_URL missing)."
                    xt6900_reach = _check_ollama_reachability(pool_config["6900xt"]["url"])
                    if not xt6900_reach["reachable"]:
                        return f"ERROR: Pool 6900XT requested but not reachable ({pool_config['6900xt']['url']}: {xt6900_reach['error']})."

                # Update metadata so it reflects the forced decision even if parsing fails later
                self._last_execution_metadata["pool"] = pool_normalized.lower()
                self._last_execution_metadata["mode"] = effective_mode.lower()

                # Set base_url_used based on effective pool
                if pool_normalized == "W5700X" and pool_config["w5700x"]["configured"]:
                    self._last_execution_metadata["base_url_used"] = pool_config["w5700x"]["url"]
                elif pool_normalized == "6900XT" and pool_config["6900xt"]["configured"]:
                    self._last_execution_metadata["base_url_used"] = pool_config["6900xt"]["url"]
                else:
                    self._last_execution_metadata["base_url_used"] = pool_config["default"]

                if mode:
                    env["ROXY_MODE"] = effective_mode
                
                # Always pass normalized pool and default model to roxy_commands
                env["ROXY_POOL"] = pool_normalized
                selected_model = model_override or _get_default_model(
                    self._last_execution_metadata.get("base_url_used"),
                    query=command,
                    mode=effective_mode,
                )
                self._last_execution_metadata["selected_model"] = selected_model
                env["ROXY_MODEL"] = selected_model
                env["ROXY_DEFAULT_MODEL"] = selected_model
                if not self._last_execution_metadata.get("model_used"):
                    self._last_execution_metadata["model_used"] = selected_model

                commands_python = ROXY_DIR / "venv" / "bin" / "python"
                python_exec = str(commands_python) if commands_python.exists() else sys.executable
                if os.getenv("ROXY_DEBUG_COMMANDS_PY", "").lower() in ("1", "true", "yes"):
                    logger.info(f"roxy_commands python_exec={python_exec}")
                result = subprocess.run(
                    [python_exec, str(commands_script), command],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=ROXY_DIR,
                    env=env
                )
                
                output = result.stdout or result.stderr or "Command completed (no output)"
                response_text = output.strip()
                
                # Parse structured response (Chief's Phase 2 - replaces JSON footer)
                tools_executed = []
                mode = "unknown"
                metadata = {}
                
                if "__STRUCTURED_RESPONSE__" in response_text:
                    parts = response_text.split("__STRUCTURED_RESPONSE__")
                    response_text = parts[0].strip()  # Text before marker
                    if len(parts) > 1:
                        try:
                            import json
                            structured = json.loads(parts[1].strip())
                            tools_executed = structured.get("tools_executed", [])
                            mode = structured.get("mode", "unknown")
                            metadata = structured.get("metadata", {})
                            logger.debug(f"Parsed structured response: mode={mode}, tools={len(tools_executed)}")
                            
                            # Store metadata for caller (Chief's Truth Panel)
                            existing_meta = self._last_execution_metadata.copy()
                            flags = metadata.get("flags") or {}
                            self._last_execution_metadata = {
                                "mode": mode,
                                "model_used": metadata.get("routing_meta", {}).get("model_used") or metadata.get("model", metadata.get("model_used")),
                                "route": mode,  # rag, tool_direct, etc.
                                "pool": metadata.get("routing_meta", {}).get("selected_pool", effective_pool.lower()),
                                "tools_executed": tools_executed,
                                "flags": flags,
                                "memory_context_chars": existing_meta.get("memory_context_chars", len(effective_memory_context)),
                                "plan_steps": existing_meta.get("plan_steps", effective_plan_steps),
                            }
                            # Preserve base_url_used from our earlier decision
                            self._last_execution_metadata["base_url_used"] = existing_meta.get("base_url_used", pool_config["default"])
                            self._last_execution_metadata["selected_model"] = existing_meta.get("selected_model") or self._last_execution_metadata.get("model_used")
                            if not self._last_execution_metadata.get("model_used"):
                                self._last_execution_metadata["model_used"] = selected_model
                        except json.JSONDecodeError as e:
                            logger.debug(f"Failed to parse structured response: {e}")
                
                # Backward compatibility: try old JSON footer
                elif "__TOOLS_EXECUTED__" in response_text:
                    parts = response_text.split("__TOOLS_EXECUTED__")
                    response_text = parts[0].strip()
                    if len(parts) > 1:
                        try:
                            import json
                            tools_executed = json.loads(parts[1].strip())
                            logger.debug(f"Extracted {len(tools_executed)} tool executions (legacy footer)")
                        except json.JSONDecodeError as e:
                            logger.debug(f"Failed to parse tools_executed JSON: {e}")
                
                # Apply Truth Gate validation (prevent hallucinations)
                if TRUTH_GATE_AVAILABLE:
                    try:
                        truth_gate = get_truth_gate()
                        # Disable file verification for RAG (files are in context, thus verified)
                        check_files = not self._is_rag_query(command)
                        # Disable action checking for casual chat
                        check_actions = not is_casual_chat
                        response_text = truth_gate.validate_response(
                            response_text, 
                            tools_executed,
                            check_file_claims=check_files,
                            check_action_claims=check_actions
                        )
                        logger.debug(f"Truth Gate applied (file_check={check_files}, action_check={check_actions})")
                    except Exception as e:
                        logger.debug(f"Truth Gate validation failed: {e}")
                
                # Cache response if it's a RAG query
                if self._is_rag_query(command):
                    try:
                        cache_exec_meta = getattr(self, '_last_execution_metadata', {})
                        cache_metadata = {
                            "mode": cache_exec_meta.get("mode", "auto"),
                            "route": cache_exec_meta.get("route", "unknown"),
                            "model_used": cache_exec_meta.get("model_used"),
                            "pool": cache_exec_meta.get("pool", "auto"),
                            "base_url_used": cache_exec_meta.get("base_url_used", _get_ollama_base_url()),
                            "tools_executed": cache_exec_meta.get("tools_executed", []),
                            "total_ms": cache_exec_meta.get("total_ms"),
                            "memory_context_chars": cache_exec_meta.get("memory_context_chars", 0),
                        }
                        # Use infrastructure cache (Redis with fallback)
                        if INFRASTRUCTURE_AVAILABLE:
                            cache_query(command, response_text, metadata=cache_metadata)
                        else:
                            sys.path.insert(0, str(ROXY_DIR))
                            from cache import get_cache as get_legacy_cache
                            cache = get_legacy_cache()
                            if cache:
                                payload = {
                                    "response": response_text,
                                    "metadata": cache_metadata,
                                    "cached_at": datetime.utcnow().isoformat()
                                }
                                cache.set(command, json.dumps(payload))
                    except Exception as e:
                        logger.debug(f"Cache storage failed: {e}")
                    
                    # Validate response
                    response_text = self._validate_response(response_text, command)
                    
                    # Add to conversation history
                    try:
                        sys.path.insert(0, str(ROXY_DIR))
                        from context_manager import get_context_manager
                        context_mgr = get_context_manager()
                        context_mgr.add_to_history(command, response_text)
                    except Exception as e:
                        logger.debug(f"Context manager add failed: {e}")
                
                return response_text
                
            except subprocess.TimeoutExpired:
                return "ERROR: Command timed out after 30 seconds"
            except Exception as e:
                return f"ERROR: {str(e)}"
    
    def _is_rag_query(self, command: str) -> bool:
        """Check if command is a RAG query"""
        rag_indicators = ["what", "how", "explain", "tell me", "describe", "?"]
        command_lower = command.lower()
        return any(indicator in command_lower for indicator in rag_indicators) or "?" in command
    
    def _is_file_claim_query(self, command: str) -> bool:
        """Check if command is asking about files (needs preflight verification)"""
        import re
        command_lower = command.lower()
        
        # Phrase-based triggers
        file_triggers = [
            "onboarding documents", "onboarding docs", "which onboarding",
            "list onboarding", "what onboarding", "onboarding files",
            "which docs", "list docs", "what docs exist",
            "which files", "list files", "what files"
        ]
        
        if any(trigger in command_lower for trigger in file_triggers):
            return True
        
        # File extension detection (more robust than phrase matching)
        # Match: roxy_assistant.py, START_HERE.md, config.json, etc.
        file_pattern = re.search(r'\b[\w./-]+\.(py|md|js|ts|tsx|jsx|json|yaml|yml|sh|txt|rs|go)\b', command_lower)
        if file_pattern:
            return True
        
        return False
    
    def _validate_response(self, response: str, query: str) -> str:
        """Validate response using validation gates"""
        try:
            sys.path.insert(0, str(ROXY_DIR))
            from validation.fact_checker import FactChecker
            from validation.source_verifier import SourceVerifier
            from validation.confidence_scorer import ConfidenceScorer
            
            fact_checker = FactChecker()
            source_verifier = SourceVerifier()
            confidence_scorer = ConfidenceScorer()
            
            # Fact check
            fact_result = fact_checker.validate_response(response, query)
            
            # Source verify
            source_result = source_verifier.verify_rag_result(
                query, response, 
                context_chunks=response.count("📌") or 1
            )
            
            # Calculate confidence
            confidence = confidence_scorer.calculate_confidence(
                fact_result,
                source_result,
                response_length=len(response),
                has_source="📌" in response or "Source:" in response
            )
            
            # Log validation results (INFO level for visibility)
            logger.info(f"[VALIDATION] fact_check={fact_result.get('is_valid')}, "
                       f"source_check={source_result.get('is_verified')}, "
                       f"confidence={confidence:.2f}")
            
            # Add confidence indicator if low
            if confidence < 0.7:
                confidence_level = confidence_scorer.get_confidence_level(confidence)
                response += f"\n\n⚠️ Confidence: {confidence_level} ({confidence:.0%})"
                if fact_result.get("warnings"):
                    response += f"\n⚠️ Warnings: {', '.join(fact_result['warnings'][:2])}"
            
            return response
        except ImportError:
            # Validation not available, return original response
            logger.debug("Validation modules not available")
            return response
        except Exception as e:
            logger.warning(f"Validation failed: {e}")
            return response

    # -------------------------------------------------------------------------
    # BENCHMARK ENDPOINTS (PHASE 1 - lm-eval harness wrapper)
    # -------------------------------------------------------------------------

    def _handle_bench_status(self):
        """GET /bench/status - Get current benchmark status"""
        try:
            from benchmark_service import get_status
            status = get_status()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(status, indent=2).encode())
        except ImportError as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "Benchmark service not available",
                "detail": str(e)
            }).encode())
        except Exception as e:
            logger.error(f"Benchmark status failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_bench_history(self):
        """GET /bench/history - List benchmark evidence bundles (auth required for paths)"""
        try:
            from benchmark_service import get_history

            # Auth check - required for path exposure
            authenticated = False
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if provided_token and provided_token == AUTH_TOKEN:
                    authenticated = True

            params = self._parse_query_params()
            limit = int(params.get("limit", 10))

            history = get_history(limit=limit, include_paths=authenticated)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "history": history,
                "count": len(history),
                "limit": limit,
                "authenticated": authenticated
            }, indent=2).encode())
        except ImportError as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "Benchmark service not available",
                "detail": str(e)
            }).encode())
        except Exception as e:
            logger.error(f"Benchmark history failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_bench_artifact(self):
        """GET /bench/artifact - Get evidence bundle details (auth required)"""
        try:
            # Auth check - required for artifact access
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "error": "Unauthorized",
                        "hint": "X-ROXY-Token header required for artifact access"
                    }).encode())
                    return

            from benchmark_service import get_artifact

            params = self._parse_query_params()
            evidence_id = params.get("id")

            if not evidence_id:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "Missing required parameter: id",
                    "hint": "Use ?id=<evidence_id> from /bench/history"
                }).encode())
                return

            artifact = get_artifact(evidence_id)

            if not artifact:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": f"Evidence bundle not found: {evidence_id}"
                }).encode())
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(artifact, indent=2).encode())
        except ImportError as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "Benchmark service not available",
                "detail": str(e)
            }).encode())
        except Exception as e:
            logger.error(f"Benchmark artifact failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_bench_tasks(self):
        """GET /bench/tasks - List supported benchmark tasks"""
        try:
            from benchmark_service import list_tasks
            tasks = list_tasks()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(tasks, indent=2).encode())
        except ImportError as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "Benchmark service not available",
                "detail": str(e)
            }).encode())
        except Exception as e:
            logger.error(f"Benchmark tasks failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_bench_run(self):
        """POST /bench/run - Start a benchmark run (gated + queued)"""
        try:
            # Auth check
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                    return

            from benchmark_service import start_run

            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b'{}'
            params = json.loads(body.decode('utf-8')) if body else {}

            # Extract parameters with defaults
            task = params.get("task", "gsm8k")
            model = params.get("model") or _get_default_model()
            pool = params.get("pool", "W5700X")  # Default W5700X (hardware name)
            num_fewshot = params.get("num_fewshot", 5)
            limit = params.get("limit", 50)  # Default 50 samples for quick runs

            # TRUE DRY RUN: Parse dry_run flag - skips lock/evidence/threads
            dry_run = bool(params.get("dry_run", False))

            result = start_run(
                task=task,
                model=model,
                pool=pool,
                num_fewshot=num_fewshot,
                limit=limit,
                dry_run=dry_run,
            )

            # Bulletproof error check (immune to error: None)
            err = result.get("error") or ""
            if err:
                self.send_response(409 if "already running" in err else 400)
            elif dry_run:
                self.send_response(200)  # OK for dry_run (no async work started)
            else:
                self.send_response(202)  # Accepted (async benchmark started)

            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result, indent=2).encode())

        except ImportError as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "Benchmark service not available",
                "detail": str(e)
            }).encode())
        except json.JSONDecodeError as e:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "Invalid JSON in request body",
                "detail": str(e)
            }).encode())
        except Exception as e:
            logger.error(f"Benchmark run failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_bench_cancel(self):
        """POST /bench/cancel - Cancel running benchmark (P0 operator control)"""
        try:
            # Auth check - required for cancel
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                    return

            from benchmark_service import cancel_run

            result = cancel_run()

            if "error" in result:
                # 404 if nothing running, 500 for other errors
                status_code = 404 if result.get("status") == "idle" else 500
                self.send_response(status_code)
            else:
                self.send_response(200)

            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result, indent=2).encode())

        except ImportError as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "Benchmark service not available",
                "detail": str(e)
            }).encode())
        except Exception as e:
            logger.error(f"Benchmark cancel failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_stories(self):
        """GET /stories - List stories from SKOREQ plans"""
        try:
            from story_selector import StorySelector
            selector = StorySelector()
            stories = selector.find_all_stories()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "total": len(stories),
                "stories": [
                    {
                        "id": s.id,
                        "title": s.title,
                        "priority": s.priority,
                        "status": s.status,
                        "points": s.points,
                        "plan": s.plan_id,
                        "sprint": s.sprint,
                    }
                    for s in stories[:50]
                ]
            }, indent=2).encode())
        except Exception as e:
            logger.error(f"Stories list failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_story_next(self):
        """GET /stories/next - Get next best story to work on"""
        try:
            from story_selector import StorySelector
            selector = StorySelector()
            story = selector.get_next_story()
            if not story:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "No stories available"}).encode())
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "id": story.id,
                "title": story.title,
                "description": story.description,
                "priority": story.priority,
                "status": story.status,
                "points": story.points,
                "plan": story.plan_id,
                "sprint": story.sprint,
                "files_in_scope": story.files_in_scope,
                "acceptance_criteria": story.acceptance_criteria,
                "dependencies": story.dependencies,
            }, indent=2).encode())
        except Exception as e:
            logger.error(f"Story next failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_story_status(self):
        """GET /stories/status - Get story status summary"""
        try:
            from story_selector import StorySelector
            selector = StorySelector()
            summary = selector.get_status_summary()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(summary, indent=2).encode())
        except Exception as e:
            logger.error(f"Story status failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_scheduler_status(self):
        """GET /scheduler/status - Get background scheduler status"""
        try:
            core = getattr(self, "_core", None) or getattr(getattr(self, "server", None), "roxy_core", None)
            if not core or not hasattr(core, "background_scheduler"):
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Scheduler not available"}).encode())
                return
            status = core.background_scheduler._get_status()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(status, indent=2).encode())
        except Exception as e:
            logger.error(f"Scheduler status failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_debug_benchmarks(self):
        """GET/POST /debug/benchmarks - Run or list ROXY performance benchmarks"""
        try:
            import asyncio
            from benchmark_suite import run_all_benchmarks, save_benchmark_evidence

            method = self.command
            if method == "POST":
                loop = asyncio.new_event_loop()
                results = loop.run_until_complete(run_all_benchmarks())
                loop.close()
                evidence_file = save_benchmark_evidence(results)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "results": results,
                    "evidence_file": str(evidence_file),
                }, indent=2).encode())
            else:
                from pathlib import Path
                evidence_dir = Path.home() / ".roxy" / "evidence" / "benchmarks"
                files = sorted(evidence_dir.glob("benchmark_*.json"), reverse=True)[:10]
                history = []
                for f in files:
                    try:
                        with open(f) as fp:
                            data = json.load(fp)
                            history.append({
                                "file": f.name,
                                "timestamp": data.get("timestamp"),
                                "summary": data.get("summary"),
                            })
                    except Exception:
                        continue
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"history": history}, indent=2).encode())
        except Exception as e:
            logger.error(f"Debug benchmarks failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_debug_failures(self):
        """GET /debug/failures - Analyze failure patterns and clustering"""
        try:
            params = self._parse_query_params()
            hours = int(params.get("hours", 24))
            from failure_cluster import FailureClusterer
            clusterer = FailureClusterer()
            clusterer.load_failures_from_audit(hours)
            clusterer.load_failures_from_errors(hours)
            report = clusterer.get_analysis_report()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(report, indent=2).encode())
        except Exception as e:
            logger.error(f"Debug failures failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_debug_runtime_state(self):
        """GET /debug/runtime-state - Collect repo, scheduler, mission, and retry state."""
        try:
            snapshot = _get_runtime_state_snapshot()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(snapshot, indent=2).encode())
        except Exception as e:
            logger.error(f"Debug runtime state failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_repo_intel(self):
        """GET /repo/intel - RepoIntel summary plus optional file/symbol lookup."""
        try:
            params = self._parse_query_params()
            file_path = str(params.get("file", "")).strip()
            symbol = str(params.get("symbol", "")).strip()
            force = str(params.get("force", "")).lower() in ("1", "true", "yes")

            repo_root = Path(os.getenv("ROXY_REPO_ROOT", str(REPO_INTEL_DEFAULT_REPO))).expanduser()
            idx = get_repo_index(repo_root=repo_root, force=force) if REPO_INTEL_AVAILABLE else None

            payload: Dict[str, Any] = {
                "repo_root": str(repo_root),
                "available": bool(REPO_INTEL_AVAILABLE and idx),
            }
            if idx:
                payload["summary"] = {
                    "file_count": idx.file_count,
                    "symbol_count": len(idx.symbol_index),
                    "language_stats": idx.get_language_stats(),
                    "built_at": datetime.fromtimestamp(idx.built_at).isoformat(),
                    "stale": idx.is_stale(),
                }
            if file_path:
                payload["file_context"] = get_file_context(file_path, repo_root=repo_root)
            if symbol:
                payload["symbol_matches"] = query_symbol(symbol, repo_root=repo_root)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload, indent=2).encode())
        except Exception as e:
            logger.error(f"Repo intel failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_missions_list(self):
        """GET /missions - List all missions from the ledger"""
        try:
            from mission_supervisor import get_ledger
            ledger = get_ledger()
            stats = ledger.get_stats()
            missions = [m.to_dict() for m in ledger.missions.values()]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"stats": stats, "missions": missions}, indent=2).encode())
        except Exception as e:
            logger.error(f"Missions list failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_missions_active(self):
        """GET /missions/active - Get current active mission"""
        try:
            from mission_supervisor import get_ledger
            ledger = get_ledger()
            active = ledger.get_active()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if active:
                self.wfile.write(json.dumps(active.to_dict(), indent=2).encode())
            else:
                self.wfile.write(json.dumps({"active": None}, indent=2).encode())
        except Exception as e:
            logger.error(f"Missions active failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_missions_run(self):
        """POST /missions/run - Trigger immediate mission execution"""
        try:
            preflight_meta: Dict[str, Any] = {"enabled": False}
            if ENABLE_MISSION_PREFLIGHT_GATE:
                from preflight_bridge import PreflightBridge, Readiness

                preflight = PreflightBridge()
                report = preflight.check_readiness()
                preflight_meta = report.to_dict()
                preflight_meta["enabled"] = True
                if report.overall_ready == Readiness.BLOCKED or (
                    MISSION_BLOCK_ON_DEGRADED and report.overall_ready == Readiness.DEGRADED
                ):
                    self.send_response(503)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        json.dumps(
                            {
                                "status": "error",
                                "message": "Mission preflight failed",
                                "preflight": preflight_meta,
                            },
                            indent=2,
                        ).encode()
                    )
                    return

            secret_scan_meta: Dict[str, Any] = {"enabled": False}
            if ENABLE_SECRET_SCAN_PREFLIGHT:
                secret_scan_meta = _run_secret_scan_preflight(force=True)
                if secret_scan_meta.get("blocked") and not SECRET_SCAN_DRY_RUN:
                    self.send_response(423)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        json.dumps(
                            {
                                "status": "error",
                                "message": "Mission blocked by secret preflight",
                                "secret_scan": secret_scan_meta,
                            },
                            indent=2,
                        ).encode()
                    )
                    return

            import asyncio
            from mission_supervisor import run_mission_task
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(run_mission_task())
            loop.close()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "result": result,
                        "preflight": preflight_meta,
                        "secret_scan": secret_scan_meta,
                    },
                    indent=2,
                ).encode()
            )
        except Exception as e:
            logger.error(f"Missions run failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_preflight_status(self):
        """GET /preflight/status - report orchestration preflight readiness."""
        try:
            from preflight_bridge import PreflightBridge

            report = PreflightBridge().check_readiness()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(report.to_dict(), indent=2).encode())
        except Exception as e:
            logger.error(f"Preflight status failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_qualification_status(self):
        """GET /qualification/status - return latest qualification artifact if present."""
        try:
            briefings = sorted(
                (ROXY_DIR / "briefings").glob("qualification-*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if not briefings:
                self.wfile.write(json.dumps({"status": "none", "artifact": None}, indent=2).encode())
                return
            payload = json.loads(briefings[0].read_text(encoding="utf-8", errors="ignore"))
            self.wfile.write(json.dumps({"status": "ok", "artifact": briefings[0].name, "result": payload}, indent=2).encode())
        except Exception as e:
            logger.error(f"Qualification status failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_qualification_run(self):
        """POST /qualification/run - execute qualification pipeline and return result."""
        try:
            from qualification_pipeline import QualificationPipeline

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            params = json.loads(body.decode("utf-8")) if body else {}
            min_score = float(params.get("min_score", 0.8))
            pipeline = QualificationPipeline(min_score=min_score)
            result = pipeline.run()
            self.send_response(200 if result.qualified else 409)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result.to_dict(), indent=2).encode())
        except Exception as e:
            logger.error(f"Qualification run failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())


class RoxyCore:
    """Always-on ROXY background service"""
    
    def __init__(self):
        self.server = None
        self.server_thread = None
        self.running = True
        self.advanced_services = {}
        self.background_scheduler = None
        self.background_scheduler_thread = None
        self.background_scheduler_loop = None
        
        logger.info("=" * 60)
        logger.info("ROXY CORE INITIALIZING")
        logger.info(f"IPC Endpoint: http://{IPC_HOST}:{IPC_PORT}")
        logger.info("=" * 60)
        
        # Initialize Prometheus metrics if available
        if METRICS_AVAILABLE:
            try:
                if init_prometheus(port=9091):
                    logger.info("✓ Prometheus metrics server started on port 9091")
                else:
                    logger.warning("Prometheus metrics server failed to start")
            except Exception as e:
                logger.warning(f"Prometheus initialization failed: {e}")
        
        # Check for advanced services
        if SERVICE_BRIDGE_AVAILABLE:
            try:
                availability = check_services_availability()
                if is_advanced_mode():
                    logger.info("✓ Advanced services available")
                    report = get_availability_report()
                    for service, available in report.items():
                        if available:
                            logger.info(f"  - {service}: available")
                else:
                    logger.info("Using basic mode (advanced services not available)")
            except Exception as e:
                logger.debug(f"Service bridge check failed: {e}")
    
    def start(self):
        """Start the core service"""
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Start HTTP server (threaded to prevent deadlock under concurrent requests)
        class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
            daemon_threads = True  # Don't block shutdown

        try:
            self.server = ThreadingHTTPServer((IPC_HOST, IPC_PORT), RoxyCoreHandler)
            self.server.roxy_core = self
            logger.info(f"✓ HTTP IPC server listening on {IPC_HOST}:{IPC_PORT}")
            
            # Run server in background thread
            self.server_thread = Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            logger.info("✓ Server thread started")
            
        except OSError as e:
            if "Address already in use" in str(e):
                logger.error(f"ERROR: Port {IPC_PORT} already in use")
                logger.error("Another ROXY core instance may be running")
                logger.error(f"Check with: systemctl --user status roxy-core")
                sys.exit(1)
            raise
        
        # Background monitoring (optional - can add ChromaDB indexing, health checks, etc.)
        self._start_background_tasks()
        
        logger.info("=" * 60)
        logger.info("ROXY CORE RUNNING")
        logger.info("Test with: curl http://127.0.0.1:8765/health")
        logger.info("=" * 60)
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nShutdown signal received")
            self.stop()
    
    def stop(self):
        """Graceful shutdown"""
        logger.info("Stopping ROXY core...")
        self.running = False

        if self.background_scheduler:
            try:
                self.background_scheduler.stop()
            except Exception as e:
                logger.debug(f"Scheduler stop failed: {e}")

        if self.background_scheduler_loop:
            try:
                self.background_scheduler_loop.call_soon_threadsafe(self.background_scheduler_loop.stop)
            except Exception as e:
                logger.debug(f"Scheduler loop stop failed: {e}")
            self.background_scheduler_loop = None
        if self.background_scheduler_thread:
            try:
                self.background_scheduler_thread.join(timeout=5)
            except Exception:
                pass
            self.background_scheduler_thread = None
        
        if self.server:
            self.server.shutdown()
            logger.info("✓ HTTP server stopped")
        
        logger.info("ROXY core stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle termination signals"""
        if signum == signal.SIGTERM and os.getenv("ROXY_IGNORE_SIGTERM", "0").lower() in ("1", "true", "yes"):
            logger.warning("Ignoring SIGTERM (ROXY_IGNORE_SIGTERM=1)")
            return
        logger.info(f"Received signal {signum}")
        self.stop()
        sys.exit(0)
    
    def _start_background_tasks(self):
        """Start optional background monitoring/indexing"""
        try:
            from story_selector import StorySelector
            self.story_selector = StorySelector()
            logger.info(f"✓ Story selector ready ({self.story_selector.get_status_summary()['total_stories']} stories)")
        except Exception as e:
            logger.warning(f"Story selector unavailable: {e}")
        
        scheduler_enabled = os.getenv("ROXY_ENABLE_BACKGROUND_SCHEDULER", "1").lower() in ("1", "true", "yes")
        if scheduler_enabled:
            try:
                from background_scheduler import BackgroundScheduler, setup_scheduler
                self.background_scheduler = BackgroundScheduler()
                setup_scheduler(self.background_scheduler)
                logger.info(f"✓ Background scheduler ready ({len(self.background_scheduler.tasks)} tasks)")
                self._start_background_scheduler()
            except Exception as e:
                logger.warning(f"Background scheduler unavailable: {e}")
        else:
            logger.info("Background scheduler disabled via ROXY_ENABLE_BACKGROUND_SCHEDULER=0")
        
        if SERVICE_BRIDGE_AVAILABLE:
            try:
                from adapters.service_bridge import get_observability
                obs = get_observability()
                if obs:
                    self.advanced_services['observability'] = obs
                    logger.info("✓ Advanced observability enabled")
            except Exception as e:
                logger.debug(f"Observability initialization failed: {e}")
        
        logger.info("Background tasks: ready")

    def _start_background_scheduler(self):
        """Run the async scheduler in its own daemon thread."""
        if not self.background_scheduler or self.background_scheduler_thread:
            return

        def _runner():
            loop = asyncio.new_event_loop()
            self.background_scheduler_loop = loop
            asyncio.set_event_loop(loop)
            scheduler_task = loop.create_task(self.background_scheduler.start())
            scheduler_task.add_done_callback(lambda _task: loop.call_soon_threadsafe(loop.stop))
            try:
                loop.run_forever()
            except Exception as exc:
                logger.error(f"Background scheduler crashed: {exc}")
            finally:
                if not scheduler_task.done():
                    scheduler_task.cancel()
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    try:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    except Exception:
                        pass
                loop.close()

        self.background_scheduler_thread = Thread(target=_runner, daemon=True)
        self.background_scheduler_thread.start()
        logger.info("✓ Background scheduler started")


def main():
    """Main entry point"""
    # Verify environment
    roxy_dir = Path.home() / ".roxy"
    if not roxy_dir.exists():
        logger.error(f"ERROR: {roxy_dir} does not exist")
        logger.error("ROXY infrastructure not found")
        sys.exit(1)

    # Validate configuration at startup
    config_result = validate_startup_config()
    if not config_result["valid"]:
        logger.error("FATAL: Configuration validation failed")
        for err in config_result["errors"]:
            logger.error(f"  - {err}")
        logger.error("Fix configuration errors and restart. See docs/RUNBOOK.md")
        sys.exit(1)

    # Start core service
    core = RoxyCore()
    core.start()


if __name__ == "__main__":
    main()
