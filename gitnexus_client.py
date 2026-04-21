#!/usr/bin/env python3
"""
GitNexus client helpers for ROXY.

This module treats GitNexus as code-structure truth and keeps the contract
small, explicit, and read-only. Raw git remains authoritative for live
worktree state elsewhere.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = os.getenv("ROXY_GITNEXUS_URL", "http://127.0.0.1:4747").rstrip("/")
DEFAULT_REPO = os.getenv("ROXY_GITNEXUS_REPO", "mindsong-juke-hub").strip() or "mindsong-juke-hub"
DEFAULT_TIMEOUT_SECONDS = float(os.getenv("ROXY_GITNEXUS_TIMEOUT_SECONDS", "1.25"))
DEFAULT_REPO_STATUS_TIMEOUT_SECONDS = float(
    os.getenv("ROXY_GITNEXUS_REPO_STATUS_TIMEOUT_SECONDS", str(max(DEFAULT_TIMEOUT_SECONDS, 5.0)))
)
DEFAULT_MIRROR_ROOT = Path(
    os.getenv("ROXY_GITNEXUS_MIRROR_ROOT", str(Path.home() / "work" / "gitnexus-mirrors"))
).expanduser()
DEFAULT_STATUS_ROOT = Path(
    os.getenv("ROXY_GITNEXUS_STATUS_ROOT", str(Path.home() / ".roxy" / "run" / "gitnexus"))
).expanduser()

REPO_NAME_HINTS = {
    ".roxy": "roxy",
    "roxy": "roxy",
    "mindsong-juke-hub": "mindsong-juke-hub",
    "mindsong-juke-hub-sandbox": "mindsong-juke-hub",
    "mindsong_runtime_main": "mindsong-juke-hub",
}

REPO_PATH_HINTS = {
    "roxy": str(Path.home() / ".roxy"),
    "mindsong-juke-hub": str(Path.home() / "mindsong-juke-hub"),
}

REPO_INDEX_PATH_HINTS = {
    "roxy": str(Path.home() / ".roxy"),
    "mindsong-juke-hub": str(DEFAULT_MIRROR_ROOT / "mindsong-juke-hub"),
}

REPO_RUNTIME_STATUS_HINTS = {
    "mindsong-juke-hub": str(DEFAULT_STATUS_ROOT / "mindsong_status.json"),
}


def _global_registry_path() -> Path:
    home = os.getenv("GITNEXUS_HOME", str(Path.home() / ".gitnexus"))
    return Path(home).expanduser() / "registry.json"


def _read_registry_entry(repo_name: Optional[str], repo_path: Optional[Path]) -> Dict[str, Any]:
    path = _global_registry_path()
    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    entries = payload if isinstance(payload, list) else []
    normalized_repo = resolve_repo_name(repo_name)
    target_repo_path = None
    if repo_path:
        try:
            target_repo_path = repo_path.resolve()
        except Exception:
            target_repo_path = repo_path

    def _entry_matches(entry: Dict[str, Any]) -> bool:
        if not isinstance(entry, dict):
            return False
        entry_path = entry.get("path")
        if target_repo_path and entry_path:
            try:
                if Path(str(entry_path)).expanduser().resolve() == target_repo_path:
                    return True
            except Exception:
                if str(entry_path) == str(repo_path):
                    return True
        return bool(normalized_repo) and str(entry.get("name") or "").strip() == normalized_repo

    for entry in entries:
        if _entry_matches(entry):
            return entry
    return {}


def _request_json(
    path: str,
    params: Optional[Dict[str, Any]] = None,
    payload: Optional[Dict[str, Any]] = None,
    method: str = "GET",
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    base_url: str = DEFAULT_BASE_URL,
) -> Dict[str, Any]:
    url = f"{base_url}{path}"
    if params:
        encoded = urlencode({k: v for k, v in params.items() if v not in (None, "")})
        if encoded:
            url = f"{url}?{encoded}"

    data = None
    headers = {"User-Agent": "roxy-gitnexus-client/1"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, method=method.upper(), headers=headers)
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
    return json.loads(raw.decode("utf-8")) if raw else {}


def _http_error_message(exc: HTTPError) -> str:
    try:
        raw = exc.read()
        if raw:
            payload = json.loads(raw.decode("utf-8"))
            message = payload.get("error")
            if message:
                return f"HTTP Error {exc.code}: {message}"
    except Exception:
        pass
    return str(exc)


def _request_ok(
    path: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    base_url: str = DEFAULT_BASE_URL,
) -> bool:
    url = f"{base_url}{path}"
    if params:
        encoded = urlencode({k: v for k, v in params.items() if v not in (None, "")})
        if encoded:
            url = f"{url}?{encoded}"
    request = Request(url, method="GET", headers={"User-Agent": "roxy-gitnexus-client/1"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return 200 <= int(getattr(response, "status", 200)) < 300
    except Exception:
        return False


def _cypher_literal(value: str) -> str:
    escaped = (value or "").replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def resolve_repo_name(repo_identifier: Optional[str]) -> Optional[str]:
    """Resolve a local path or repo-like token into the GitNexus repo name."""
    if not repo_identifier:
        return DEFAULT_REPO

    raw = str(repo_identifier).strip()
    if not raw:
        return DEFAULT_REPO

    if raw in REPO_NAME_HINTS:
        return REPO_NAME_HINTS[raw]

    path = Path(raw).expanduser()
    name = path.name or raw
    if name in REPO_NAME_HINTS:
        return REPO_NAME_HINTS[name]

    return name


def resolve_repo_path_hint(repo_name: Optional[str]) -> Optional[str]:
    normalized = resolve_repo_name(repo_name)
    if not normalized:
        return None
    return REPO_PATH_HINTS.get(normalized)


def resolve_repo_index_path_hint(repo_name: Optional[str]) -> Optional[str]:
    normalized = resolve_repo_name(repo_name)
    if not normalized:
        return None
    return REPO_INDEX_PATH_HINTS.get(normalized)


def _resolve_repo_fs_path(repo_name: Optional[str]) -> Optional[Path]:
    hint = resolve_repo_index_path_hint(repo_name) or resolve_repo_path_hint(repo_name)
    if hint:
        return Path(hint).expanduser()

    if not repo_name:
        return None
    candidate = Path(str(repo_name)).expanduser()
    if candidate.exists():
        return candidate
    return None


def _read_runtime_status(repo_name: Optional[str]) -> Dict[str, Any]:
    normalized = resolve_repo_name(repo_name)
    path_hint = REPO_RUNTIME_STATUS_HINTS.get(normalized or "")
    if not path_hint:
        return {}

    status_path = Path(path_hint).expanduser()
    if not status_path.exists():
        return {}

    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    return payload if isinstance(payload, dict) else {}


def _read_local_index_state(repo_name: Optional[str]) -> Dict[str, Any]:
    repo_path = _resolve_repo_fs_path(repo_name)
    registry_entry = _read_registry_entry(repo_name, repo_path)
    state: Dict[str, Any] = {
        "index_path": str(repo_path) if repo_path else None,
        "meta_repo_path": None,
        "indexed_commit": None,
        "current_commit": None,
        "fresh": None,
        "repo_path_match": None,
        "staleness_reason": None,
        "indexed_at_local": None,
    }
    if not repo_path:
        return state

    meta_path = repo_path / ".gitnexus" / "meta.json"
    meta: Dict[str, Any] = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta = {}

    meta_repo_path = meta.get("repoPath")
    indexed_commit = meta.get("lastCommit")
    indexed_at_local = meta.get("indexedAt")
    if not meta_repo_path and registry_entry.get("path"):
        meta_repo_path = registry_entry.get("path")
    if not indexed_commit and registry_entry.get("lastCommit"):
        indexed_commit = registry_entry.get("lastCommit")
    if not indexed_at_local and registry_entry.get("indexedAt"):
        indexed_at_local = registry_entry.get("indexedAt")
    state["meta_repo_path"] = str(meta_repo_path) if meta_repo_path else None
    state["indexed_commit"] = str(indexed_commit) if indexed_commit else None
    state["indexed_at_local"] = str(indexed_at_local) if indexed_at_local else None

    if meta_repo_path:
        try:
            state["repo_path_match"] = Path(str(meta_repo_path)).expanduser().resolve() == repo_path.resolve()
        except Exception:
            state["repo_path_match"] = str(meta_repo_path) == str(repo_path)

    git_dir = repo_path / ".git"
    if git_dir.exists():
        try:
            current = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            head = (current.stdout or "").strip()
            if head and head != "HEAD":
                state["current_commit"] = head
        except Exception:
            state["current_commit"] = None

    repo_path_match = state["repo_path_match"]
    current_commit = state["current_commit"]
    if indexed_commit and current_commit:
        fresh = indexed_commit == current_commit
        if repo_path_match is False:
            fresh = False
            state["staleness_reason"] = "repo_path_mismatch"
        elif not fresh:
            state["staleness_reason"] = "head_mismatch"
        state["fresh"] = fresh
    elif repo_path_match is False:
        state["fresh"] = False
        state["staleness_reason"] = "repo_path_mismatch"

    return state


def is_indexed_repo(payload: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(payload, dict):
        return False
    indexed_at = str(payload.get("indexedAt") or "").strip()
    if indexed_at:
        return True
    stats = payload.get("stats") or {}
    return any(int(stats.get(key) or 0) > 0 for key in ("files", "nodes", "processes"))


def get_server_info(
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    try:
        payload = _request_json("/api/info", timeout=timeout, base_url=base_url)
        return {
            "available": True,
            "base_url": base_url,
            "version": payload.get("version"),
            "launch_context": payload.get("launchContext"),
            "error": None,
        }
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        return {
            "available": False,
            "base_url": base_url,
            "version": None,
            "launch_context": None,
            "error": str(exc),
        }


def get_repo_status(
    repo_name: str = DEFAULT_REPO,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    normalized_repo = resolve_repo_name(repo_name) or DEFAULT_REPO
    local_state = _read_local_index_state(normalized_repo)
    runtime_state = _read_runtime_status(normalized_repo)
    canonical_path_hint = resolve_repo_path_hint(normalized_repo)
    index_path_hint = resolve_repo_index_path_hint(normalized_repo) or canonical_path_hint

    def _status_base() -> Dict[str, Any]:
        bootstrap_progress = runtime_state.get("progress") or {}
        return {
            "truth_source": "gitnexus",
            "indexed_commit": local_state.get("indexed_commit"),
            "current_commit": local_state.get("current_commit"),
            "fresh": local_state.get("fresh"),
            "meta_repo_path": local_state.get("meta_repo_path"),
            "repo_path_match": local_state.get("repo_path_match"),
            "staleness_reason": local_state.get("staleness_reason"),
            "bootstrap_state": runtime_state.get("state"),
            "bootstrap_job_id": runtime_state.get("job_id"),
            "bootstrap_progress": bootstrap_progress,
            "bootstrap_updated_at": runtime_state.get("updated_at"),
            "bootstrap_error": runtime_state.get("error"),
            "bootstrap_registered": runtime_state.get("registered"),
            "bootstrap_repo_name": runtime_state.get("repo_name"),
            "bootstrap_mirror_root": runtime_state.get("mirror_root"),
            "bootstrap_source_head": runtime_state.get("source_head"),
            "bootstrap_mirror_head": runtime_state.get("mirror_head"),
            "bootstrap_canonical_head": runtime_state.get("canonical_head"),
        }

    def _bootstrap_message(fallback: Optional[str]) -> Optional[str]:
        state = str(runtime_state.get("state") or "").strip()
        if state not in {"starting", "submitted", "indexing"}:
            return fallback
        progress = runtime_state.get("progress") or {}
        phase = progress.get("phase") or state
        percent = progress.get("percent")
        message = progress.get("message") or ""
        prefix = f"GitNexus bootstrap {state}"
        if percent is not None:
            prefix = f"{prefix}: {phase} {percent}%"
        elif phase:
            prefix = f"{prefix}: {phase}"
        if message:
            prefix = f"{prefix} - {message}"
        if fallback:
            return f"{prefix} (backend: {fallback})"
        return prefix

    server = get_server_info(base_url=base_url, timeout=timeout)
    if not server.get("available"):
        return {
            "available": False,
            "repo_name": normalized_repo,
            "repo_path_hint": canonical_path_hint,
            "index_path_hint": index_path_hint,
            "indexed": False,
            "indexed_at": local_state.get("indexed_at_local"),
            "stats": {"files": 0, "nodes": 0, "processes": 0},
            "error": server.get("error"),
            "base_url": base_url,
            **_status_base(),
        }

    try:
        payload = _request_json(
            "/api/repo",
            params={"repo": normalized_repo},
            timeout=max(timeout, DEFAULT_REPO_STATUS_TIMEOUT_SECONDS),
            base_url=base_url,
        )
        stats = payload.get("stats") or {}
        status_base = _status_base()
        if (
            is_indexed_repo(payload)
            and status_base.get("bootstrap_state") in {"starting", "submitted", "indexing"}
            and status_base.get("fresh") is True
            and status_base.get("indexed_commit")
            and status_base.get("indexed_commit") == status_base.get("current_commit")
        ):
            status_base["bootstrap_state"] = "complete"
            status_base["bootstrap_progress"] = {}
            status_base["bootstrap_registered"] = True
        return {
            "available": True,
            "repo_name": normalized_repo,
            "repo_path_hint": canonical_path_hint,
            "index_path_hint": index_path_hint,
            "indexed": is_indexed_repo(payload),
            "indexed_at": payload.get("indexedAt") or local_state.get("indexed_at_local"),
            "stats": {
                "files": int(stats.get("files") or 0),
                "nodes": int(stats.get("nodes") or 0),
                "processes": int(stats.get("processes") or 0),
            },
            "error": None,
            "base_url": base_url,
            "version": server.get("version"),
            "launch_context": server.get("launch_context"),
            **status_base,
        }
    except HTTPError as exc:
        return {
            "available": True,
            "repo_name": normalized_repo,
            "repo_path_hint": canonical_path_hint,
            "index_path_hint": index_path_hint,
            "indexed": False,
            "indexed_at": local_state.get("indexed_at_local"),
            "stats": {"files": 0, "nodes": 0, "processes": 0},
            "error": _bootstrap_message(_http_error_message(exc)),
            "base_url": base_url,
            "version": server.get("version"),
            "launch_context": server.get("launch_context"),
            **_status_base(),
        }
    except (URLError, TimeoutError, ValueError, OSError) as exc:
        return {
            "available": True,
            "repo_name": normalized_repo,
            "repo_path_hint": canonical_path_hint,
            "index_path_hint": index_path_hint,
            "indexed": False,
            "indexed_at": local_state.get("indexed_at_local"),
            "stats": {"files": 0, "nodes": 0, "processes": 0},
            "error": _bootstrap_message(str(exc)),
            "base_url": base_url,
            "version": server.get("version"),
            "launch_context": server.get("launch_context"),
            **_status_base(),
        }


def verify_file(
    repo_name: str,
    path: str,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> bool:
    normalized_repo = resolve_repo_name(repo_name) or DEFAULT_REPO
    if not path:
        return False
    return _request_ok(
        "/api/file",
        params={"repo": normalized_repo, "path": path},
        timeout=timeout,
        base_url=base_url,
    )


def grep(
    repo_name: str,
    pattern: str,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> List[Dict[str, Any]]:
    normalized_repo = resolve_repo_name(repo_name) or DEFAULT_REPO
    if not pattern.strip():
        return []
    try:
        payload = _request_json(
            "/api/grep",
            params={"repo": normalized_repo, "pattern": pattern},
            timeout=timeout,
            base_url=base_url,
        )
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        return []
    results = payload.get("results") or []
    return results if isinstance(results, list) else []


def query_cypher(
    repo_name: str,
    cypher: str,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> List[Dict[str, Any]]:
    normalized_repo = resolve_repo_name(repo_name) or DEFAULT_REPO
    if not cypher.strip():
        return []
    try:
        payload = _request_json(
            "/api/query",
            params={"repo": normalized_repo},
            payload={"cypher": cypher},
            method="POST",
            timeout=timeout,
            base_url=base_url,
        )
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        return []
    results = payload.get("result") or []
    return results if isinstance(results, list) else []


def _grep_candidates(label: str, file_path: str) -> List[str]:
    values = [label or "", file_path or ""]
    basename = Path(file_path).name if file_path else ""
    if basename:
        values.append(basename)
    ordered: List[str] = []
    for candidate in values:
        trimmed = str(candidate).strip()
        if trimmed and trimmed not in ordered:
            ordered.append(trimmed)
    return ordered


def _pick_grep_match(candidate: str, matches: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    normalized = candidate.strip().lower()
    if not normalized:
        return None

    def _file_contains(match: Dict[str, Any]) -> bool:
        return normalized in str(match.get("filePath") or "").lower()

    def _text_declares(match: Dict[str, Any]) -> bool:
        text = str(match.get("text") or "").strip().lower()
        return (
            text.startswith(f"export function {normalized}")
            or text.startswith(f"function {normalized}")
            or text.startswith(f"export const {normalized}")
            or text.startswith(f"const {normalized}")
        )

    for predicate in (_file_contains, _text_declares):
        for match in matches:
            if predicate(match):
                return match
    for match in matches:
        if str(match.get("filePath") or "").startswith("src/"):
            return match
    return matches[0] if matches else None


def resolve_focus(
    repo_name: str = DEFAULT_REPO,
    label: str = "",
    file_path: str = "",
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """
    Resolve an operator focus against GitNexus using the same order of trust
    as the native OperatorBar bridge: verified file, symbol, then grep fallback.
    """
    normalized_repo = resolve_repo_name(repo_name) or DEFAULT_REPO
    server = get_server_info(base_url=base_url, timeout=timeout)
    repo_status = get_repo_status(normalized_repo, base_url=base_url, timeout=timeout)
    signature = f"{label.strip()}|{file_path.strip()}".strip("|")

    result: Dict[str, Any] = {
        "status": "unresolved",
        "repo_name": normalized_repo,
        "repo_path_hint": resolve_repo_path_hint(normalized_repo),
        "available": bool(server.get("available")),
        "indexed": bool(repo_status.get("indexed")),
        "entity_type": None,
        "best_match_label": None,
        "best_match_path": None,
        "verified_files": [],
        "message": None,
        "resolved_signature": signature,
        "truth_source": "gitnexus",
        "error": server.get("error") or repo_status.get("error"),
    }

    if not server.get("available"):
        result["status"] = "offline"
        result["message"] = "GitNexus server is unavailable."
        return result

    if not repo_status.get("indexed"):
        result["status"] = "not_indexed"
        result["message"] = "GitNexus repo is not indexed."
        return result

    if file_path and verify_file(normalized_repo, file_path, base_url=base_url, timeout=timeout):
        literal = _cypher_literal(file_path)
        rows = query_cypher(
            normalized_repo,
            (
                "MATCH (n:File {filePath: "
                f"{literal}"
                "}) RETURN n.id AS id, coalesce(n.name, n.filePath, n.id) AS label, n.filePath AS filePath LIMIT 1"
            ),
            base_url=base_url,
            timeout=timeout,
        )
        row = rows[0] if rows else {}
        result.update(
            {
                "status": "verified",
                "entity_type": "file",
                "best_match_label": row.get("label") or file_path,
                "best_match_path": row.get("filePath") or file_path,
                "verified_files": [file_path],
                "message": None,
                "error": None,
            }
        )
        return result

    if label.strip():
        literal = _cypher_literal(label.strip())
        rows = query_cypher(
            normalized_repo,
            (
                "MATCH (n) "
                "WHERE lower(coalesce(n.name, '')) = lower("
                f"{literal}"
                ") OR lower(coalesce(n.label, '')) = lower("
                f"{literal}"
                ") "
                "RETURN n.id AS id, coalesce(n.name, n.label, n.filePath, n.id) AS label, n.filePath AS filePath LIMIT 5"
            ),
            base_url=base_url,
            timeout=timeout,
        )
        if rows:
            top = rows[0]
            status = "partial" if len(rows) > 1 else "verified"
            message = None
            if len(rows) > 1:
                message = "Multiple exact symbol matches exist. Use a file path to disambiguate."
            result.update(
                {
                    "status": status,
                    "entity_type": "symbol",
                    "best_match_label": top.get("label") or label.strip(),
                    "best_match_path": top.get("filePath"),
                    "message": message,
                    "error": None,
                }
            )
            return result

    for candidate in _grep_candidates(label, file_path):
        matches = grep(normalized_repo, candidate, base_url=base_url, timeout=timeout)
        match = _pick_grep_match(candidate, matches)
        if not match:
            continue
        best_match_path = match.get("filePath")
        best_match_label = best_match_path or candidate
        if best_match_path and match.get("line"):
            best_match_label = f"{best_match_path}:{match['line']}"
        result.update(
            {
                "status": "partial",
                "entity_type": "search",
                "best_match_label": best_match_label,
                "best_match_path": best_match_path,
                "message": "Fallback grep evidence only.",
                "error": None,
            }
        )
        return result

    result["message"] = "No GitNexus focus match found."
    return result
