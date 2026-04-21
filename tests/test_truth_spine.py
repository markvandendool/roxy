import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".roxy"))

import brain_atlas
import trace_spine


def test_brain_atlas_build_snapshot_links_repo_and_service(monkeypatch, tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    latest_path = tmp_path / "atlas_latest.json"

    monkeypatch.setattr(brain_atlas, "ATLAS_ROOT", tmp_path)
    monkeypatch.setattr(brain_atlas, "SNAPSHOT_DIR", snapshot_dir)
    monkeypatch.setattr(brain_atlas, "LATEST_SNAPSHOT", latest_path)
    monkeypatch.setattr(brain_atlas, "_ATLAS_CACHE", {"built_at": 0.0, "snapshot": None})
    monkeypatch.setattr(
        brain_atlas,
        "_known_repos",
        lambda: [
            {"name": "roxy", "path": "/tmp/roxy", "owner": "ROXY"},
            {"name": "mindsong-juke-hub", "path": "/tmp/mindsong-juke-hub", "owner": "MindSong"},
        ],
    )
    monkeypatch.setattr(
        brain_atlas,
        "_known_services",
        lambda: [
            {
                "name": "roxy-core",
                "repo_name": "roxy",
                "owner": "ROXY",
                "process": "roxy_core.py",
                "endpoint": "http://127.0.0.1:8766",
                "runbook": str(tmp_path / "runbook.md"),
            }
        ],
    )
    (tmp_path / "runbook.md").write_text("runbook")
    monkeypatch.setattr(
        brain_atlas,
        "_git_repo_facts",
        lambda repo_path: {
            "exists": True,
            "repo_path": str(repo_path),
            "branch": "main",
            "head_sha": "abc1234",
            "dirty": False,
            "changed_count": 0,
        },
    )
    monkeypatch.setattr(brain_atlas, "_http_reachable", lambda _url, timeout=0.5: True)
    monkeypatch.setattr(brain_atlas, "_socket_reachable", lambda _host, _port, timeout=0.35: True)
    monkeypatch.setattr(
        brain_atlas,
        "get_repo_status",
        lambda _repo: {
            "available": True,
            "repo_name": "mindsong-juke-hub",
            "indexed": True,
            "indexed_at": "2026-04-21T00:00:00Z",
            "stats": {"files": 100, "nodes": 200, "processes": 5},
            "error": None,
        },
    )
    monkeypatch.setattr(
        brain_atlas,
        "_upsert_snapshot_to_neo4j",
        lambda _snapshot: {"attempted": True, "reachable": True, "upserted": True, "error": None},
    )

    snapshot = brain_atlas.build_snapshot(force=True)

    kinds = {node["kind"] for node in snapshot["nodes"]}
    assert "Machine" in kinds
    assert "Repo" in kinds
    assert "Service" in kinds
    assert snapshot["summary"]["repo_count"] == 2
    assert snapshot["summary"]["service_count"] == 1
    assert latest_path.exists()
    assert any(edge["type"] == "BACKED_BY" for edge in snapshot["edges"])


def test_trace_spine_records_run_trace(monkeypatch, tmp_path):
    monkeypatch.setattr(trace_spine, "TRACE_DIR", tmp_path)
    trace_spine._TRACE_SPINE = None

    spine = trace_spine.get_trace_spine()
    output_path = spine.record_run_trace(
        "trace-123",
        "What changed?",
        "Repo is dirty.",
        {
            "route": "git_query",
            "operator_surface": "command_center",
            "truth_sources": {"primary": "raw_git", "sources": ["raw_git", "gitnexus"]},
            "repo": {"repo_path": "/tmp/repo", "branch": "main"},
        },
        spans=[{"name": "raw_git.snapshot", "attributes": {"branch": "main"}}],
    )

    payload = Path(output_path).read_text().strip().splitlines()
    assert payload
    entry = json.loads(payload[-1])
    assert entry["trace_id"] == "trace-123"
    assert entry["metadata"]["route"] == "git_query"
    assert entry["metadata"]["truth_sources"]["primary"] == "raw_git"
