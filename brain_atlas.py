#!/usr/bin/env python3
"""
Brain Atlas v0 for ROXY.

Atlas v0 is intentionally narrow:
- read-only
- snapshot-based
- built from existing local runtime facts
- optionally mirrored into Neo4j
"""

from __future__ import annotations

import base64
import json
import os
import socket
import subprocess
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from gitnexus_client import DEFAULT_REPO as DEFAULT_GITNEXUS_REPO
from gitnexus_client import get_repo_status


ROXY_DIR = Path.home() / ".roxy"
ATLAS_ROOT = ROXY_DIR / "data" / "brain_atlas"
SNAPSHOT_DIR = ATLAS_ROOT / "snapshots"
LATEST_SNAPSHOT = ATLAS_ROOT / "atlas_latest.json"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

ATLAS_CACHE_TTL_SECONDS = int(os.getenv("ROXY_ATLAS_CACHE_TTL_SECONDS", "30"))
DEFAULT_NEO4J_HTTP_URL = os.getenv("ROXY_ATLAS_NEO4J_HTTP_URL", "http://127.0.0.1:7474")
DEFAULT_NEO4J_DB = os.getenv("ROXY_ATLAS_NEO4J_DB", "neo4j")
DEFAULT_NEO4J_USER = os.getenv("ROXY_ATLAS_NEO4J_USER", "neo4j")
DEFAULT_NEO4J_PASSWORD = os.getenv("ROXY_ATLAS_NEO4J_PASSWORD", "roxymusic2026")

_ATLAS_CACHE: Dict[str, Any] = {"built_at": 0.0, "snapshot": None}


def _json_sanitize(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_sanitize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_sanitize(v) for v in value]
    return value


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _git_repo_facts(repo_path: Path) -> Dict[str, Any]:
    if not (repo_path / ".git").exists():
        return {
            "exists": False,
            "repo_path": str(repo_path),
            "branch": None,
            "head_sha": None,
            "dirty": None,
            "changed_count": 0,
        }

    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    env.setdefault("GIT_ASKPASS", "/bin/true")
    env.setdefault("SSH_ASKPASS", "/bin/true")

    def _run(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repo_path), *args],
            capture_output=True,
            text=True,
            timeout=3,
            env=env,
        )
        return (result.stdout or result.stderr or "").strip()

    try:
        branch = _run("rev-parse", "--abbrev-ref", "HEAD")
        head_sha = _run("rev-parse", "--short", "HEAD")
        status = _run("status", "--porcelain")
        changed = [line for line in status.splitlines() if line.strip()]
        return {
            "exists": True,
            "repo_path": str(repo_path),
            "branch": branch or None,
            "head_sha": head_sha or None,
            "dirty": bool(changed),
            "changed_count": len(changed),
        }
    except Exception as exc:
        return {
            "exists": True,
            "repo_path": str(repo_path),
            "branch": None,
            "head_sha": None,
            "dirty": None,
            "changed_count": 0,
            "error": str(exc),
        }


def _socket_reachable(host: str, port: int, timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def _http_reachable(url: str, timeout: float = 0.5) -> bool:
    try:
        request = Request(url, method="GET", headers={"User-Agent": "roxy-brain-atlas/1"})
        with urlopen(request, timeout=timeout) as response:
            return int(getattr(response, "status", 200)) < 500
    except HTTPError as exc:
        return int(getattr(exc, "code", 599)) < 500
    except Exception:
        return False


def _neo4j_auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def _neo4j_property_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        if all(item is None or isinstance(item, (str, int, float, bool)) for item in value):
            return list(value)
        return json.dumps(_json_sanitize(value), sort_keys=True)
    if isinstance(value, dict):
        return json.dumps(_json_sanitize(value), sort_keys=True)
    return str(value)


def _neo4j_property_map(props: Dict[str, Any]) -> Dict[str, Any]:
    return {
        str(key): _neo4j_property_value(value)
        for key, value in props.items()
        if value is not None
    }


def _neo4j_available(url: str = DEFAULT_NEO4J_HTTP_URL) -> bool:
    return _http_reachable(url, timeout=0.75)


def _neo4j_commit(statements: List[Dict[str, Any]]) -> Dict[str, Any]:
    endpoint = f"{DEFAULT_NEO4J_HTTP_URL.rstrip('/')}/db/{DEFAULT_NEO4J_DB}/tx/commit"
    payload = json.dumps({"statements": statements}).encode("utf-8")
    request = Request(endpoint, data=payload, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Authorization", _neo4j_auth_header(DEFAULT_NEO4J_USER, DEFAULT_NEO4J_PASSWORD))
    request.add_header("User-Agent", "roxy-brain-atlas/1")
    with urlopen(request, timeout=2.0) as response:
        raw = response.read()
    return json.loads(raw.decode("utf-8")) if raw else {}


def _upsert_snapshot_to_neo4j(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    if not _neo4j_available():
        return {"attempted": True, "reachable": False, "upserted": False, "error": "neo4j_unreachable"}

    statements: List[Dict[str, Any]] = []
    for node in snapshot.get("nodes", []):
        kind = str(node.get("kind") or "Entity")
        props = _neo4j_property_map(dict(node))
        props["atlas_id"] = node["atlas_id"]
        statements.append(
            {
                "statement": (
                    f"MERGE (n:AtlasNode:{kind} {{atlas_id: $atlas_id}}) "
                    "SET n += $props"
                ),
                "parameters": {"atlas_id": node["atlas_id"], "props": props},
            }
        )

    for edge in snapshot.get("edges", []):
        props = {
            "type": edge["type"],
            "source": edge["source"],
        }
        statements.append(
            {
                "statement": (
                    "MATCH (a:AtlasNode {atlas_id: $from_id}), (b:AtlasNode {atlas_id: $to_id}) "
                    "MERGE (a)-[r:ATLAS_REL {type: $edge_type, source: $source}]->(b) "
                    "SET r += $props"
                ),
                "parameters": {
                    "from_id": edge["from"],
                    "to_id": edge["to"],
                    "edge_type": edge["type"],
                    "source": edge["source"],
                    "props": props,
                },
            }
        )

    try:
        payload = _neo4j_commit(statements)
        errors = payload.get("errors") or []
        return {
            "attempted": True,
            "reachable": True,
            "upserted": not bool(errors),
            "error": errors[0].get("message") if errors else None,
        }
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        return {
            "attempted": True,
            "reachable": True,
            "upserted": False,
            "error": str(exc),
        }


def _entity_id(kind: str, name: str) -> str:
    return f"{kind.lower()}:{name}"


def _add_node(nodes: List[Dict[str, Any]], kind: str, name: str, **props: Any) -> Dict[str, Any]:
    atlas_id = _entity_id(kind, name)
    node = {"atlas_id": atlas_id, "kind": kind, "name": name}
    node.update({k: _json_sanitize(v) for k, v in props.items() if v is not None})
    if all(existing["atlas_id"] != atlas_id for existing in nodes):
        nodes.append(node)
    return node


def _add_edge(edges: List[Dict[str, Any]], from_id: str, edge_type: str, to_id: str, source: str) -> None:
    edge = {"from": from_id, "to": to_id, "type": edge_type, "source": source}
    if edge not in edges:
        edges.append(edge)


def _known_repos() -> List[Dict[str, str]]:
    return [
        {"name": "roxy", "path": str(ROXY_DIR), "owner": "ROXY"},
        {"name": "mindsong-juke-hub", "path": str(Path.home() / "mindsong-juke-hub"), "owner": "MindSong"},
    ]


def _known_services() -> List[Dict[str, Any]]:
    return [
        {
            "name": "roxy-core",
            "repo_name": "roxy",
            "owner": "ROXY",
            "process": "roxy_core.py",
            "endpoint": "http://127.0.0.1:8766",
            "runbook": str(ROXY_DIR / "brain" / "02_architecture" / "INFRASTRUCTURE.md"),
        },
        {
            "name": "roxy-command-center",
            "repo_name": "roxy",
            "owner": "ROXY",
            "process": "main.py",
            "endpoint": None,
            "runbook": str(ROXY_DIR / "apps" / "roxy-command-center" / "ENGINEERING_CHECKLIST.md"),
        },
        {
            "name": "gitnexus",
            "repo_name": DEFAULT_GITNEXUS_REPO,
            "owner": "MindSong",
            "process": "gitnexus",
            "endpoint": "http://127.0.0.1:4747",
            "runbook": str(Path.home() / "mindsong-juke-hub" / "tools" / "operator-menubar" / "README.md"),
        },
        {
            "name": "langfuse",
            "repo_name": "roxy",
            "owner": "ROXY",
            "process": "langfuse",
            "endpoint": "http://127.0.0.1:3000",
            "runbook": str(ROXY_DIR / "docker" / "langfuse" / "docker-compose.yml"),
        },
        {
            "name": "roxy-neo4j",
            "repo_name": "roxy",
            "owner": "ROXY",
            "process": "neo4j",
            "endpoint": DEFAULT_NEO4J_HTTP_URL,
            "runbook": str(ROXY_DIR / "docker" / "docker-compose.neo4j.yaml"),
        },
    ]


def build_snapshot(force: bool = False) -> Dict[str, Any]:
    cached = _ATLAS_CACHE.get("snapshot")
    if not force and cached and (time.time() - float(_ATLAS_CACHE.get("built_at") or 0.0)) < ATLAS_CACHE_TTL_SECONDS:
        return deepcopy(cached)

    machine_name = socket.gethostname()
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    warnings: List[str] = []
    sources: List[str] = []

    machine = _add_node(nodes, "Machine", machine_name, hostname=machine_name)

    for repo in _known_repos():
        repo_path = Path(repo["path"]).expanduser()
        repo_facts = _git_repo_facts(repo_path)
        if not repo_facts.get("exists"):
            warnings.append(f"repo_missing:{repo['name']}")
            continue
        sources.append(f"git:{repo['name']}")
        owner = _add_node(nodes, "Owner", repo["owner"])
        repo_node = _add_node(
            nodes,
            "Repo",
            repo["name"],
            path=repo["path"],
            branch=repo_facts.get("branch"),
            head_sha=repo_facts.get("head_sha"),
            dirty=repo_facts.get("dirty"),
            changed_count=repo_facts.get("changed_count"),
        )
        _add_edge(edges, machine["atlas_id"], "HOSTS_REPO", repo_node["atlas_id"], "local_git")
        _add_edge(edges, owner["atlas_id"], "OWNS", repo_node["atlas_id"], "local_config")

        if repo["name"] == DEFAULT_GITNEXUS_REPO:
            gitnexus = get_repo_status(repo["name"])
            repo_node["gitnexus"] = {
                "available": gitnexus.get("available"),
                "indexed": gitnexus.get("indexed"),
                "indexed_at": gitnexus.get("indexed_at"),
                "stats": gitnexus.get("stats"),
                "error": gitnexus.get("error"),
            }

    datastores = [
        {
            "name": "neo4j",
            "path": str(ROXY_DIR / "docker" / "docker-compose.neo4j.yaml"),
            "healthy": _socket_reachable("127.0.0.1", 7687),
        },
        {
            "name": "chroma_db",
            "path": str(ROXY_DIR / "chroma_db"),
            "healthy": (ROXY_DIR / "chroma_db").exists(),
        },
        {
            "name": "postgres_memory",
            "path": str(ROXY_DIR / "data"),
            "healthy": bool(_read_json(ROXY_DIR / "config.json")),
        },
    ]
    for datastore in datastores:
        data_node = _add_node(
            nodes,
            "DataStore",
            datastore["name"],
            path=datastore["path"],
            healthy=datastore["healthy"],
        )
        _add_edge(edges, machine["atlas_id"], "HOSTS_DATASTORE", data_node["atlas_id"], "local_runtime")

    for service in _known_services():
        owner = _add_node(nodes, "Owner", service["owner"])
        service_node = _add_node(
            nodes,
            "Service",
            service["name"],
            process=service["process"],
            endpoint=service["endpoint"],
            reachable=_http_reachable(service["endpoint"]) if service["endpoint"] else None,
        )
        _add_edge(edges, owner["atlas_id"], "OWNS", service_node["atlas_id"], "local_config")
        _add_edge(edges, machine["atlas_id"], "RUNS_ON", service_node["atlas_id"], "local_runtime")

        repo_node_id = _entity_id("Repo", service["repo_name"])
        if any(node["atlas_id"] == repo_node_id for node in nodes):
            _add_edge(edges, service_node["atlas_id"], "BACKED_BY", repo_node_id, "local_config")

        if service["endpoint"]:
            endpoint = service["endpoint"]
            endpoint_node = _add_node(nodes, "Endpoint", endpoint, url=endpoint, reachable=_http_reachable(endpoint))
            _add_edge(edges, service_node["atlas_id"], "EXPOSES", endpoint_node["atlas_id"], "local_runtime")

        runbook_path = Path(service["runbook"]).expanduser()
        if runbook_path.exists():
            runbook = _add_node(nodes, "Runbook", runbook_path.name, path=str(runbook_path))
            _add_edge(edges, service_node["atlas_id"], "DOCUMENTED_BY", runbook["atlas_id"], "local_docs")
        else:
            warnings.append(f"runbook_missing:{service['name']}")

    atlas_snapshot: Dict[str, Any] = {
        "version": "brain-atlas-v0",
        "built_at": _now_iso(),
        "machine": machine_name,
        "nodes": nodes,
        "edges": edges,
        "sources": sorted(set(sources)),
        "warnings": warnings,
        "summary": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "repo_count": sum(1 for node in nodes if node["kind"] == "Repo"),
            "service_count": sum(1 for node in nodes if node["kind"] == "Service"),
            "endpoint_count": sum(1 for node in nodes if node["kind"] == "Endpoint"),
        },
    }

    neo4j_status = _upsert_snapshot_to_neo4j(atlas_snapshot)
    atlas_snapshot["neo4j"] = neo4j_status

    timestamp_name = f"atlas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    snapshot_path = SNAPSHOT_DIR / timestamp_name
    snapshot_path.write_text(json.dumps(_json_sanitize(atlas_snapshot), indent=2))
    LATEST_SNAPSHOT.write_text(json.dumps(_json_sanitize(atlas_snapshot), indent=2))
    atlas_snapshot["snapshot_path"] = str(snapshot_path)
    atlas_snapshot["latest_path"] = str(LATEST_SNAPSHOT)

    _ATLAS_CACHE["built_at"] = time.time()
    _ATLAS_CACHE["snapshot"] = deepcopy(atlas_snapshot)
    return atlas_snapshot


def get_atlas_status(force: bool = False) -> Dict[str, Any]:
    snapshot = build_snapshot(force=force)
    summary = snapshot.get("summary") or {}
    neo4j_status = snapshot.get("neo4j") or {}
    return {
        "available": True,
        "built_at": snapshot.get("built_at"),
        "node_count": int(summary.get("node_count") or 0),
        "edge_count": int(summary.get("edge_count") or 0),
        "repo_count": int(summary.get("repo_count") or 0),
        "service_count": int(summary.get("service_count") or 0),
        "warnings": snapshot.get("warnings", []),
        "snapshot_path": snapshot.get("latest_path") or str(LATEST_SNAPSHOT),
        "neo4j": neo4j_status,
        "truth_source": "brain_atlas",
    }


def load_latest_snapshot() -> Dict[str, Any]:
    cached = _ATLAS_CACHE.get("snapshot")
    if cached:
        return deepcopy(cached)
    if LATEST_SNAPSHOT.exists():
        return _read_json(LATEST_SNAPSHOT)
    return build_snapshot(force=False)


def atlas_lookup_entity(kind: Optional[str] = None, name: Optional[str] = None, atlas_id: Optional[str] = None) -> Dict[str, Any]:
    snapshot = load_latest_snapshot()
    for node in snapshot.get("nodes", []):
        if atlas_id and node.get("atlas_id") == atlas_id:
            return {"found": True, "entity": node}
        if kind and name and node.get("kind") == kind and node.get("name") == name:
            return {"found": True, "entity": node}
    return {"found": False, "entity": None}


def atlas_neighbors(atlas_id: str) -> Dict[str, Any]:
    snapshot = load_latest_snapshot()
    nodes = {node["atlas_id"]: node for node in snapshot.get("nodes", [])}
    related = []
    for edge in snapshot.get("edges", []):
        if edge["from"] == atlas_id:
            related.append({"direction": "out", "edge": edge, "entity": nodes.get(edge["to"])})
        elif edge["to"] == atlas_id:
            related.append({"direction": "in", "edge": edge, "entity": nodes.get(edge["from"])})
    return {"found": bool(nodes.get(atlas_id)), "neighbors": related}


def atlas_service_truth(name: str) -> Dict[str, Any]:
    lookup = atlas_lookup_entity(kind="Service", name=name)
    entity = lookup.get("entity")
    if not entity:
        return {"found": False, "service": None, "neighbors": []}
    neighbors = atlas_neighbors(entity["atlas_id"]).get("neighbors", [])
    return {"found": True, "service": entity, "neighbors": neighbors}


def atlas_repo_truth(name: Optional[str] = None, repo_path: Optional[str] = None) -> Dict[str, Any]:
    snapshot = load_latest_snapshot()
    entity = None
    target_name = name
    if not target_name and repo_path:
        normalized = str(Path(repo_path).expanduser())
        for node in snapshot.get("nodes", []):
            if node.get("kind") == "Repo" and node.get("path") == normalized:
                entity = node
                break
    if entity is None and target_name:
        entity = atlas_lookup_entity(kind="Repo", name=target_name).get("entity")
    if not entity:
        return {"found": False, "repo": None, "neighbors": []}
    neighbors = atlas_neighbors(entity["atlas_id"]).get("neighbors", [])
    return {"found": True, "repo": entity, "neighbors": neighbors}
