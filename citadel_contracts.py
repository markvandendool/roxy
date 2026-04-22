#!/usr/bin/env python3
"""
Citadel compatibility contracts for ROXY.

This layer does not replace existing packet shapes yet. It adapts the current
ROXY snapshot and Brain Atlas truth into a stable kernel-facing contract that
other native shells can consume over time.
"""

from __future__ import annotations

import os
import socket
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from brain_atlas import load_latest_snapshot


CITADEL_REGISTRY_VERSION = "citadel-registry-v1"
CITADEL_SNAPSHOT_VERSION = "citadel-snapshot-v1"
CITADEL_ACTION_VERSION = "citadel-action-v1"

CITADEL_ACTION_TYPES = (
    "command.run",
    "device.claim",
    "device.release",
    "email.send",
    "gitnexus.analyze",
    "gitnexus.resume",
    "mobile.alert.ack",
    "recording.start",
    "recording.stop",
    "repo.push",
    "repo.status",
    "service.restart",
    "worker.dispatch",
)

_ROXY_DIR = Path.home() / ".roxy"
_MINDSONG_DIR = Path.home() / "mindsong-juke-hub"

_KNOWN_MACHINES: List[Dict[str, Any]] = [
    {
        "machine_id": "roxy-macpro",
        "display_name": "ROXY Mac Pro",
        "hostname_aliases": ["macpro-linux", "roxy-macpro"],
        "ssh_target": "roxy",
        "os": "linux",
        "roles": ["primary-runtime", "command-center", "gpu-inference"],
        "repo_roots": [str(_ROXY_DIR), str(_MINDSONG_DIR)],
        "control_endpoints": {
            "roxy_core": "http://127.0.0.1:8766",
            "gitnexus": "http://127.0.0.1:4747",
            "brain_atlas": "http://127.0.0.1:8766/atlas/status",
        },
        "surfaces": ["linux-command-center"],
        "trust_level": "primary",
    },
    {
        "machine_id": "mac-studio",
        "display_name": "Mac Studio",
        "hostname_aliases": ["mac-studio", "Marks-Mac-mini.local", "marks-mac-mini.local"],
        "ssh_target": "macstudio",
        "os": "macos",
        "roles": ["owner-cockpit", "operator-bar", "lifepanel", "recording-oversight"],
        "repo_roots": [str(Path.home() / "mindsong-juke-hub")],
        "control_endpoints": {
            "operator_briefing": "http://127.0.0.1:3848/api/operator/briefing",
            "operator_ws": "ws://127.0.0.1:3848/ws",
            "run_gateway": "http://localhost:9136/api/runs",
            "hardware_authority": "http://127.0.0.1:49173",
        },
        "surfaces": ["operator-bar", "lifepanel"],
        "trust_level": "primary",
    },
    {
        "machine_id": "citadel-worker-1-imac",
        "display_name": "Citadel Worker 1 iMac",
        "hostname_aliases": ["citadel-worker-1-imac", "friday"],
        "ssh_target": "friday",
        "os": "macos",
        "roles": ["worker", "render", "orchestrator"],
        "repo_roots": [],
        "control_endpoints": {},
        "surfaces": [],
        "trust_level": "worker",
    },
    {
        "machine_id": "citadel-worker-2-macbook",
        "display_name": "Citadel Worker 2 MacBook",
        "hostname_aliases": ["citadel-worker-2-macbook"],
        "os": "macos",
        "roles": ["worker", "mobile-dev", "backup-ops"],
        "repo_roots": [],
        "control_endpoints": {},
        "surfaces": [],
        "trust_level": "worker",
    },
    {
        "machine_id": "phone-primary",
        "display_name": "Primary Phone",
        "hostname_aliases": ["phone-primary", "iphone-primary"],
        "os": "ios",
        "roles": ["alerts", "approvals", "emergency-stop"],
        "repo_roots": [],
        "control_endpoints": {},
        "surfaces": ["mobile"],
        "trust_level": "personal",
    },
]

_KNOWN_SURFACES: List[Dict[str, Any]] = [
    {
        "surface_id": "linux-command-center",
        "display_name": "ROXY Command Center",
        "machine_id": "roxy-macpro",
        "role": "deep-execution",
        "contract": "/ui/snapshot",
    },
    {
        "surface_id": "operator-bar",
        "display_name": "OperatorBar",
        "machine_id": "mac-studio",
        "role": "owner-cockpit",
        "contract": "/api/operator/briefing",
    },
    {
        "surface_id": "lifepanel",
        "display_name": "LifePanel",
        "machine_id": "mac-studio",
        "role": "owner-cockpit",
        "contract": "/api/operator/briefing",
    },
    {
        "surface_id": "web-operator",
        "display_name": "Web Operator",
        "machine_id": "mac-studio",
        "role": "shared-dashboard",
        "contract": "/api/operator/briefing",
    },
    {
        "surface_id": "mobile",
        "display_name": "Mobile Control",
        "machine_id": "phone-primary",
        "role": "alerts-approvals",
        "contract": "adapter_pending",
    },
]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _json_sanitize(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_sanitize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_sanitize(v) for v in value]
    return value


def resolve_machine_id(hostname: Optional[str] = None) -> Optional[str]:
    target = (hostname or socket.gethostname()).strip().lower()
    if not target:
        return None
    for machine in _KNOWN_MACHINES:
        aliases = [str(alias).strip().lower() for alias in machine.get("hostname_aliases", [])]
        if target in aliases:
            return str(machine["machine_id"])
    return None


def build_citadel_registry(current_hostname: Optional[str] = None) -> Dict[str, Any]:
    hostname = (current_hostname or socket.gethostname()).strip()
    current_machine_id = resolve_machine_id(hostname)
    machines = deepcopy(_KNOWN_MACHINES)
    for machine in machines:
        machine["is_current"] = machine.get("machine_id") == current_machine_id

    return {
        "version": CITADEL_REGISTRY_VERSION,
        "generated_at": _now_iso(),
        "current_hostname": hostname,
        "current_machine_id": current_machine_id,
        "machines": machines,
        "surfaces": deepcopy(_KNOWN_SURFACES),
        "action_types": list(CITADEL_ACTION_TYPES),
        "summary": {
            "machine_count": len(machines),
            "surface_count": len(_KNOWN_SURFACES),
            "current_machine_resolved": bool(current_machine_id),
        },
    }


def _atlas_repo_items(atlas_snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    repos: List[Dict[str, Any]] = []
    for node in atlas_snapshot.get("nodes", []):
        if node.get("kind") != "Repo":
            continue
        repos.append(
            {
                "name": node.get("name"),
                "path": node.get("path"),
                "branch": node.get("branch"),
                "head_sha": node.get("head_sha"),
                "dirty": node.get("dirty"),
                "changed_count": node.get("changed_count"),
                "truth_source": "brain_atlas",
            }
        )
    return repos


def _upsert_repo_item(items: List[Dict[str, Any]], repo: Dict[str, Any]) -> None:
    repo_name = str(repo.get("name") or "").strip()
    repo_path = str(repo.get("path") or "").strip()
    for existing in items:
        if repo_name and existing.get("name") == repo_name:
            existing.update({k: v for k, v in repo.items() if v is not None})
            return
        if repo_path and existing.get("path") == repo_path:
            existing.update({k: v for k, v in repo.items() if v is not None})
            return
    items.append(repo)


def _build_repo_section(ui_snapshot: Dict[str, Any], atlas_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    info = ui_snapshot.get("info") or {}
    git = info.get("git") or {}
    gitnexus = info.get("gitnexus") or {}
    repo_items = _atlas_repo_items(atlas_snapshot)

    _upsert_repo_item(
        repo_items,
        {
            "name": "roxy",
            "path": str(_ROXY_DIR),
            "branch": git.get("branch"),
            "head_sha": git.get("head_sha"),
            "dirty": git.get("dirty"),
            "changed_count": None,
            "truth_source": "raw_git",
        },
    )

    if gitnexus.get("repo_name"):
        _upsert_repo_item(
            repo_items,
            {
                "name": gitnexus.get("repo_name"),
                "path": gitnexus.get("repo_path_hint"),
                "index_path": gitnexus.get("index_path_hint"),
                "indexed_commit": gitnexus.get("indexed_commit"),
                "current_commit": gitnexus.get("current_commit"),
                "canonical_current_commit": gitnexus.get("canonical_current_commit"),
                "gitnexus": {
                    "available": gitnexus.get("available"),
                    "indexed": gitnexus.get("indexed"),
                    "fresh": gitnexus.get("fresh"),
                    "error": gitnexus.get("error"),
                    "bootstrap_state": gitnexus.get("bootstrap_state"),
                    "staleness_reason": gitnexus.get("staleness_reason"),
                },
                "truth_source": "gitnexus",
            },
        )

    degraded_reasons: List[str] = []
    if gitnexus.get("available") and not gitnexus.get("indexed"):
        degraded_reasons.append("gitnexus_not_indexed")
    if gitnexus.get("fresh") is False:
        degraded_reasons.append("gitnexus_stale")
    if gitnexus.get("bootstrap_state") == "indexing":
        degraded_reasons.append("gitnexus_bootstrap_indexing")

    return {
        "items": repo_items,
        "truth_contract": info.get("truth_contract") or {},
        "gitnexus": {
            "repo_name": gitnexus.get("repo_name"),
            "available": gitnexus.get("available"),
            "indexed": gitnexus.get("indexed"),
            "fresh": gitnexus.get("fresh"),
            "bootstrap_state": gitnexus.get("bootstrap_state"),
            "error": gitnexus.get("error"),
            "degraded_reasons": degraded_reasons,
        },
    }


def _build_capabilities(ui_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    info = ui_snapshot.get("info") or {}
    github = info.get("github") or {}
    gitnexus = info.get("gitnexus") or {}
    atlas = info.get("atlas") or {}
    bench = ui_snapshot.get("bench") or {}
    roxy = ui_snapshot.get("roxy") or {}

    return {
        "local_machine_id": resolve_machine_id(info.get("hostname")),
        "command_run": roxy.get("status") == "healthy",
        "raw_git_truth": True,
        "github_read": bool(github.get("configured") and github.get("reachable")),
        "gitnexus_code_truth": bool(gitnexus.get("available") and gitnexus.get("indexed")),
        "brain_atlas_graph": bool(atlas.get("available")),
        "benchmark_control": bool(bench.get("available")),
    }


def _build_next_actions(ui_snapshot: Dict[str, Any]) -> List[Dict[str, str]]:
    info = ui_snapshot.get("info") or {}
    gitnexus = info.get("gitnexus") or {}
    atlas = info.get("atlas") or {}
    roxy = ui_snapshot.get("roxy") or {}
    actions: List[Dict[str, str]] = []

    if roxy.get("status") != "healthy":
        actions.append(
            {
                "id": "repair_roxy_core",
                "severity": "critical",
                "message": "ROXY core is not healthy; repair the primary control plane first.",
            }
        )
    if gitnexus.get("available") and not gitnexus.get("indexed"):
        actions.append(
            {
                "id": "gitnexus_bootstrap",
                "severity": "warning",
                "message": "GitNexus indexing is incomplete; code-structure truth is degraded.",
            }
        )
    if gitnexus.get("fresh") is False:
        actions.append(
            {
                "id": "gitnexus_refresh",
                "severity": "warning",
                "message": "GitNexus index is stale against canonical head and needs refresh.",
            }
        )
    if not atlas.get("available"):
        actions.append(
            {
                "id": "repair_brain_atlas",
                "severity": "warning",
                "message": "Brain Atlas is unavailable; fleet topology truth is degraded.",
            }
        )
    if ui_snapshot.get("remote_error"):
        actions.append(
            {
                "id": "repair_remote_snapshot",
                "severity": "warning",
                "message": "The upstream UI snapshot reported a remote error and needs inspection.",
            }
        )
    return actions


def build_citadel_snapshot(
    ui_snapshot: Dict[str, Any],
    *,
    registry: Optional[Dict[str, Any]] = None,
    atlas_snapshot: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    registry_payload = deepcopy(registry) if registry else build_citadel_registry()
    atlas_payload = deepcopy(atlas_snapshot) if atlas_snapshot is not None else load_latest_snapshot()

    info = ui_snapshot.get("info") or {}
    current_hostname = info.get("hostname") or registry_payload.get("current_hostname") or socket.gethostname()
    current_machine_id = resolve_machine_id(current_hostname)
    mode = ui_snapshot.get("mode") or "local"
    alerts = ui_snapshot.get("alerts") or []
    services = ui_snapshot.get("services") or {}

    payload = {
        "version": CITADEL_SNAPSHOT_VERSION,
        "generated_at": _now_iso(),
        "fleet": {
            "current_machine_id": current_machine_id,
            "current_hostname": current_hostname,
            "mode": mode,
            "machines": registry_payload.get("machines", []),
            "surfaces": registry_payload.get("surfaces", []),
        },
        "repos": _build_repo_section(ui_snapshot, atlas_payload),
        "atlas": {
            "status": info.get("atlas") or {},
            "summary": atlas_payload.get("summary") or {},
            "machine": atlas_payload.get("machine"),
            "warnings": atlas_payload.get("warnings") or [],
        },
        "services": services,
        "models": {
            "ollama": ui_snapshot.get("ollama") or {},
            "routing_policy": info.get("routing_policy"),
        },
        "operator": {
            "alerts": alerts,
            "bench": ui_snapshot.get("bench") or {},
            "remote_error": ui_snapshot.get("remote_error"),
            "next_actions": _build_next_actions(ui_snapshot),
        },
        "capabilities": _build_capabilities(ui_snapshot),
        "provenance": {
            "source": "roxy-core.citadel_compat",
            "generated_at": _now_iso(),
            "upstream_contract": {
                "ui_snapshot": "/ui/snapshot",
                "operator_briefing": "/api/operator/briefing (adapter pending)",
            },
            "truth_contract": info.get("truth_contract") or {},
            "snapshot_meta": ui_snapshot.get("snapshot_meta") or {},
        },
        "legacy": {
            "ui_snapshot_version": ui_snapshot.get("version"),
            "source": ui_snapshot.get("source"),
        },
    }
    return _json_sanitize(payload)


def validate_citadel_action_envelope(payload: Any) -> Dict[str, Any]:
    errors: List[str] = []
    if not isinstance(payload, dict):
        return {"valid": False, "errors": ["payload_must_be_object"], "normalized": {}}

    normalized = {str(key): value for key, value in payload.items()}
    for key in ("action_id", "action_type", "target_machine", "requested_by", "requested_from_surface"):
        value = normalized.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"missing_or_invalid:{key}")

    action_type = normalized.get("action_type")
    if isinstance(action_type, str) and action_type not in CITADEL_ACTION_TYPES:
        errors.append("unsupported:action_type")

    requires_confirmation = normalized.get("requires_confirmation")
    if requires_confirmation is not None and not isinstance(requires_confirmation, bool):
        errors.append("invalid:requires_confirmation")

    audit_tags = normalized.get("audit_tags")
    if audit_tags is not None and not isinstance(audit_tags, list):
        errors.append("invalid:audit_tags")

    target_scope = normalized.get("target_scope")
    if target_scope is not None and not isinstance(target_scope, dict):
        errors.append("invalid:target_scope")

    action_payload = normalized.get("payload")
    if action_payload is not None and not isinstance(action_payload, dict):
        errors.append("invalid:payload")

    normalized.setdefault("target_scope", {})
    normalized.setdefault("payload", {})
    normalized.setdefault("audit_tags", [])
    normalized.setdefault("requires_confirmation", False)
    normalized.setdefault("version", CITADEL_ACTION_VERSION)
    return {"valid": not errors, "errors": errors, "normalized": _json_sanitize(normalized)}
