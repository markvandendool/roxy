#!/usr/bin/env python3
"""
Citadel event log and lightweight kernel state helpers.

This is intentionally file-backed for v1 so the shared Citadel control plane
can emit a stable audit/event feed before a heavier event spine exists.
"""

from __future__ import annotations

import json
import uuid
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional


CITADEL_EVENT_VERSION = "citadel-event-v1"

_ROOT = Path.home() / ".roxy" / "run" / "citadel"
EVENT_LOG_PATH = _ROOT / "events.jsonl"
AUTHORITY_STATE_PATH = _ROOT / "authority_state.json"
WORKER_DISPATCH_LOG_PATH = _ROOT / "worker_dispatches.jsonl"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _ensure_root() -> None:
    _ROOT.mkdir(parents=True, exist_ok=True)


def _json_sanitize(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_sanitize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_sanitize(v) for v in value]
    return value


def _write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    _ensure_root()
    with NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as handle:
        json.dump(_json_sanitize(payload), handle, indent=2, sort_keys=True)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def append_event(
    event_type: str,
    *,
    status: str = "info",
    source: str = "citadel-kernel",
    machine_id: Optional[str] = None,
    action: Optional[Dict[str, Any]] = None,
    payload: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    _ensure_root()
    event = {
        "version": CITADEL_EVENT_VERSION,
        "event_id": f"evt-{uuid.uuid4().hex}",
        "event_type": str(event_type).strip() or "unknown",
        "status": str(status).strip() or "info",
        "created_at": _now_iso(),
        "source": source,
        "machine_id": machine_id,
        "action_id": action.get("action_id") if isinstance(action, dict) else None,
        "action_type": action.get("action_type") if isinstance(action, dict) else None,
        "requested_by": action.get("requested_by") if isinstance(action, dict) else None,
        "requested_from_surface": action.get("requested_from_surface") if isinstance(action, dict) else None,
        "target_machine": action.get("target_machine") if isinstance(action, dict) else None,
        "tags": list(tags or []),
        "payload": _json_sanitize(payload or {}),
    }
    with EVENT_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True))
        handle.write("\n")
    return event


def list_events(limit: int = 50, before_event_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if limit <= 0:
        return []
    if not EVENT_LOG_PATH.exists():
        return []

    items: List[Dict[str, Any]] = []
    for raw_line in EVENT_LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            decoded = json.loads(line)
        except Exception:
            continue
        if isinstance(decoded, dict):
            items.append(decoded)

    if before_event_id:
        for index, item in enumerate(items):
            if str(item.get("event_id") or "") == before_event_id:
                items = items[:index]
                break

    return list(reversed(items[-limit:]))


def load_authority_state() -> Dict[str, Any]:
    if not AUTHORITY_STATE_PATH.exists():
        return {"version": 1, "updated_at": None, "claims": {}}
    try:
        payload = json.loads(AUTHORITY_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "updated_at": None, "claims": {}}
    if not isinstance(payload, dict):
        return {"version": 1, "updated_at": None, "claims": {}}
    claims = payload.get("claims")
    if not isinstance(claims, dict):
        payload["claims"] = {}
    payload.setdefault("version", 1)
    payload.setdefault("updated_at", None)
    return payload


def store_authority_state(state: Dict[str, Any]) -> Dict[str, Any]:
    payload = deepcopy(state)
    payload["version"] = 1
    payload["updated_at"] = _now_iso()
    payload.setdefault("claims", {})
    _write_json_atomic(AUTHORITY_STATE_PATH, payload)
    return payload


def claim_device(
    device_id: str,
    *,
    owner: str,
    target_machine: Optional[str],
    requested_from_surface: Optional[str],
    note: Optional[str] = None,
) -> Dict[str, Any]:
    state = load_authority_state()
    claims = state.setdefault("claims", {})
    claim = {
        "device_id": device_id,
        "owner": owner,
        "target_machine": target_machine,
        "requested_from_surface": requested_from_surface,
        "note": note,
        "claimed_at": _now_iso(),
    }
    claims[device_id] = claim
    store_authority_state(state)
    return claim


def release_device(device_id: str) -> Dict[str, Any]:
    state = load_authority_state()
    claims = state.setdefault("claims", {})
    released = claims.pop(device_id, None)
    store_authority_state(state)
    return released if isinstance(released, dict) else {}


def append_worker_dispatch(dispatch: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_root()
    record = _json_sanitize(dict(dispatch))
    with WORKER_DISPATCH_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True))
        handle.write("\n")
    return record
