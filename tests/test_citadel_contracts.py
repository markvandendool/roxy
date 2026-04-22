import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".roxy"))

import citadel_contracts


def test_registry_contains_stable_machine_ids():
    registry = citadel_contracts.build_citadel_registry(current_hostname="macpro-linux")

    machine_ids = {machine["machine_id"] for machine in registry["machines"]}
    assert {
        "roxy-macpro",
        "mac-studio",
        "citadel-worker-1-imac",
        "citadel-worker-2-macbook",
        "phone-primary",
    }.issubset(machine_ids)
    assert registry["current_machine_id"] == "roxy-macpro"


def test_build_citadel_snapshot_wraps_current_roxy_truth(monkeypatch):
    monkeypatch.setattr(
        citadel_contracts,
        "load_latest_snapshot",
        lambda: {
            "machine": "macpro-linux",
            "summary": {"node_count": 9, "edge_count": 12, "repo_count": 2, "service_count": 3},
            "warnings": [],
            "nodes": [
                {
                    "kind": "Repo",
                    "name": "roxy",
                    "path": "/home/mark/.roxy",
                    "branch": "main",
                    "head_sha": "abc1234",
                    "dirty": True,
                    "changed_count": 4,
                },
                {
                    "kind": "Repo",
                    "name": "mindsong-juke-hub",
                    "path": "/home/mark/mindsong-juke-hub",
                    "branch": "main",
                    "head_sha": "def5678",
                    "dirty": False,
                    "changed_count": 0,
                },
            ],
        },
    )

    ui_snapshot = {
        "version": "2.0.0",
        "mode": "local",
        "source": "roxy-core",
        "roxy": {"status": "healthy"},
        "services": {"roxy_core": {"active": True, "health_ok": True}},
        "ollama": {"fast": {"active": True}},
        "bench": {"available": True, "status": "idle"},
        "alerts": [],
        "snapshot_meta": {"source": "roxy-core", "transport": "roxy-core.ui_snapshot"},
        "info": {
            "hostname": "macpro-linux",
            "routing_policy": "auto",
            "truth_contract": {
                "worktree": "raw_git",
                "code_structure": "gitnexus",
                "system_graph": "brain_atlas",
            },
            "git": {"branch": "main", "head_sha": "abc1234", "dirty": True},
            "gitnexus": {
                "available": True,
                "repo_name": "mindsong-juke-hub",
                "repo_path_hint": "/home/mark/mindsong-juke-hub",
                "index_path_hint": "/home/mark/work/gitnexus-mirrors/mindsong-juke-hub",
                "indexed": False,
                "fresh": None,
                "bootstrap_state": "indexing",
                "error": "indexing",
            },
            "atlas": {"available": True, "node_count": 9, "edge_count": 12},
            "github": {"configured": True, "reachable": True},
        },
    }

    payload = citadel_contracts.build_citadel_snapshot(ui_snapshot)

    assert payload["version"] == citadel_contracts.CITADEL_SNAPSHOT_VERSION
    assert payload["fleet"]["current_machine_id"] == "roxy-macpro"
    assert payload["repos"]["truth_contract"]["system_graph"] == "brain_atlas"
    assert any(repo["name"] == "roxy" for repo in payload["repos"]["items"])
    assert any(repo["name"] == "mindsong-juke-hub" for repo in payload["repos"]["items"])
    next_action_ids = {item["id"] for item in payload["operator"]["next_actions"]}
    assert "gitnexus_bootstrap" in next_action_ids


def test_validate_citadel_action_envelope_requires_core_fields():
    invalid = citadel_contracts.validate_citadel_action_envelope({"action_type": "repo.status"})
    assert invalid["valid"] is False
    assert "missing_or_invalid:action_id" in invalid["errors"]

    valid = citadel_contracts.validate_citadel_action_envelope(
        {
            "action_id": "act-123",
            "action_type": "repo.status",
            "target_machine": "roxy-macpro",
            "requested_by": "codex",
            "requested_from_surface": "linux-command-center",
        }
    )
    assert valid["valid"] is True
    assert valid["normalized"]["version"] == citadel_contracts.CITADEL_ACTION_VERSION
