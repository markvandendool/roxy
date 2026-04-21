from __future__ import annotations

import json
import subprocess
from pathlib import Path

import gitnexus_client


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def test_local_index_state_falls_back_to_global_registry_when_meta_missing(monkeypatch, tmp_path):
    repo = tmp_path / "mindsong-juke-hub"
    repo.mkdir()
    _git(repo, "init")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Codex",
            "-c",
            "user.email=codex@example.com",
            "commit",
            "-m",
            "init",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    current_head = _git(repo, "rev-parse", "HEAD")

    # Advance HEAD so registry commit is stale.
    (repo / "README.md").write_text("hello\nworld\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Codex",
            "-c",
            "user.email=codex@example.com",
            "commit",
            "-m",
            "second",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    new_head = _git(repo, "rev-parse", "HEAD")
    assert new_head != current_head

    registry_home = tmp_path / "gitnexus-home"
    registry_home.mkdir()
    (registry_home / "registry.json").write_text(
        json.dumps(
            [
                {
                    "name": "mindsong-juke-hub",
                    "path": str(repo),
                    "storagePath": str(repo / ".gitnexus"),
                    "indexedAt": "2026-04-21T19:04:36.853Z",
                    "lastCommit": current_head,
                    "stats": {"files": 10, "nodes": 20, "processes": 2},
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("GITNEXUS_HOME", str(registry_home))
    monkeypatch.setitem(gitnexus_client.REPO_PATH_HINTS, "mindsong-juke-hub", "/canonical/mindsong-juke-hub")
    monkeypatch.setitem(gitnexus_client.REPO_INDEX_PATH_HINTS, "mindsong-juke-hub", str(repo))

    state = gitnexus_client._read_local_index_state("mindsong-juke-hub")

    assert state["indexed_commit"] == current_head
    assert state["current_commit"] == new_head
    assert state["meta_repo_path"] == str(repo)
    assert state["repo_path_match"] is True
    assert state["fresh"] is False
    assert state["staleness_reason"] == "head_mismatch"
    assert state["indexed_at_local"] == "2026-04-21T19:04:36.853Z"


def test_get_repo_status_exposes_separate_canonical_and_index_path_hints(monkeypatch):
    monkeypatch.setitem(gitnexus_client.REPO_PATH_HINTS, "mindsong-juke-hub", "/canonical/mindsong-juke-hub")
    monkeypatch.setitem(
        gitnexus_client.REPO_INDEX_PATH_HINTS,
        "mindsong-juke-hub",
        "/local/gitnexus-mirrors/mindsong-juke-hub",
    )

    monkeypatch.setattr(
        gitnexus_client,
        "get_server_info",
        lambda **_kwargs: {"available": False, "error": "down"},
    )
    monkeypatch.setattr(
        gitnexus_client,
        "_read_local_index_state",
        lambda _repo: {
            "indexed_at_local": "2026-04-21T19:04:36.853Z",
            "indexed_commit": "abc123",
            "current_commit": "def456",
            "fresh": False,
            "meta_repo_path": "/local/gitnexus-mirrors/mindsong-juke-hub",
            "repo_path_match": True,
            "staleness_reason": "head_mismatch",
        },
    )

    status = gitnexus_client.get_repo_status("mindsong-juke-hub")

    assert status["repo_path_hint"] == "/canonical/mindsong-juke-hub"
    assert status["index_path_hint"] == "/local/gitnexus-mirrors/mindsong-juke-hub"
    assert status["fresh"] is False


def test_local_index_state_ignores_unborn_head(monkeypatch, tmp_path):
    repo = tmp_path / "mindsong-juke-hub"
    repo.mkdir()
    _git(repo, "init")

    monkeypatch.setitem(gitnexus_client.REPO_INDEX_PATH_HINTS, "mindsong-juke-hub", str(repo))

    state = gitnexus_client._read_local_index_state("mindsong-juke-hub")

    assert state["current_commit"] is None


def test_read_runtime_status_uses_repo_specific_status_file(monkeypatch, tmp_path):
    status_path = tmp_path / "mindsong_status.json"
    status_path.write_text(
        json.dumps(
            {
                "state": "indexing",
                "job_id": "job-123",
                "progress": {"phase": "lbug", "percent": 73, "message": "Loading nodes"},
                "updated_at": "2026-04-21T21:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setitem(gitnexus_client.REPO_RUNTIME_STATUS_HINTS, "mindsong-juke-hub", str(status_path))

    payload = gitnexus_client._read_runtime_status("mindsong-juke-hub")

    assert payload["state"] == "indexing"
    assert payload["job_id"] == "job-123"
    assert payload["progress"]["percent"] == 73


def test_get_repo_status_surfaces_bootstrap_progress_on_repo_404(monkeypatch):
    monkeypatch.setitem(gitnexus_client.REPO_PATH_HINTS, "mindsong-juke-hub", "/canonical/mindsong-juke-hub")
    monkeypatch.setitem(
        gitnexus_client.REPO_INDEX_PATH_HINTS,
        "mindsong-juke-hub",
        "/local/gitnexus-mirrors/mindsong-juke-hub",
    )
    monkeypatch.setattr(
        gitnexus_client,
        "get_server_info",
        lambda **_kwargs: {"available": True, "version": "1.6.2", "launch_context": "global"},
    )
    monkeypatch.setattr(
        gitnexus_client,
        "_read_local_index_state",
        lambda _repo: {
            "indexed_at_local": None,
            "indexed_commit": None,
            "current_commit": "mirror-head",
            "fresh": None,
            "meta_repo_path": None,
            "repo_path_match": None,
            "staleness_reason": None,
        },
    )
    monkeypatch.setattr(
        gitnexus_client,
        "_read_runtime_status",
        lambda _repo: {
            "state": "indexing",
            "job_id": "job-123",
            "progress": {"phase": "lbug", "percent": 73, "message": "Loading nodes"},
            "updated_at": "2026-04-21T21:00:00Z",
            "mirror_root": "/local/gitnexus-mirrors/mindsong-juke-hub",
        },
    )

    class FakeHTTPError(gitnexus_client.HTTPError):
        def __init__(self):
            super().__init__("http://127.0.0.1:4747/api/repo", 404, "Not Found", hdrs=None, fp=None)

    monkeypatch.setattr(
        gitnexus_client,
        "_request_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(FakeHTTPError()) if args and args[0] == "/api/repo" else {},
    )

    status = gitnexus_client.get_repo_status("mindsong-juke-hub")

    assert status["indexed"] is False
    assert status["bootstrap_state"] == "indexing"
    assert status["bootstrap_progress"]["percent"] == 73
    assert "GitNexus bootstrap indexing: lbug 73%" in status["error"]


def test_get_repo_status_marks_bootstrap_complete_when_repo_is_indexed(monkeypatch):
    monkeypatch.setitem(gitnexus_client.REPO_PATH_HINTS, "mindsong-juke-hub", "/canonical/mindsong-juke-hub")
    monkeypatch.setitem(
        gitnexus_client.REPO_INDEX_PATH_HINTS,
        "mindsong-juke-hub",
        "/local/gitnexus-mirrors/mindsong-juke-hub",
    )
    monkeypatch.setattr(
        gitnexus_client,
        "get_server_info",
        lambda **_kwargs: {"available": True, "version": "1.6.2", "launch_context": "global"},
    )
    monkeypatch.setattr(
        gitnexus_client,
        "_read_local_index_state",
        lambda _repo: {
            "indexed_at_local": "2026-04-21T21:17:07.671Z",
            "indexed_commit": "mirror-head",
            "current_commit": "mirror-head",
            "fresh": True,
            "meta_repo_path": "/local/gitnexus-mirrors/mindsong-juke-hub",
            "repo_path_match": True,
            "staleness_reason": None,
        },
    )
    monkeypatch.setattr(
        gitnexus_client,
        "_read_runtime_status",
        lambda _repo: {
            "state": "indexing",
            "job_id": "job-123",
            "progress": {"phase": "fts", "percent": 85, "message": "Creating search indexes..."},
            "updated_at": "2026-04-21T21:16:30Z",
            "mirror_root": "/local/gitnexus-mirrors/mindsong-juke-hub",
        },
    )
    monkeypatch.setattr(
        gitnexus_client,
        "_request_json",
        lambda *args, **kwargs: {
            "indexedAt": "2026-04-21T21:17:07.671Z",
            "stats": {"files": 34503, "nodes": 553007, "processes": 300},
        },
    )

    status = gitnexus_client.get_repo_status("mindsong-juke-hub")

    assert status["indexed"] is True
    assert status["fresh"] is True
    assert status["bootstrap_state"] == "complete"
    assert status["bootstrap_progress"] == {}
    assert status["bootstrap_registered"] is True


def test_get_repo_status_keeps_bootstrap_active_while_refresh_is_still_catching_up(monkeypatch):
    monkeypatch.setitem(gitnexus_client.REPO_PATH_HINTS, "mindsong-juke-hub", "/canonical/mindsong-juke-hub")
    monkeypatch.setitem(
        gitnexus_client.REPO_INDEX_PATH_HINTS,
        "mindsong-juke-hub",
        "/local/gitnexus-mirrors/mindsong-juke-hub",
    )
    monkeypatch.setattr(
        gitnexus_client,
        "get_server_info",
        lambda **_kwargs: {"available": True, "version": "1.6.2", "launch_context": "global"},
    )
    monkeypatch.setattr(
        gitnexus_client,
        "_read_local_index_state",
        lambda _repo: {
            "indexed_at_local": "2026-04-21T21:17:07.671Z",
            "indexed_commit": "old-indexed-head",
            "current_commit": "new-mirror-head",
            "fresh": False,
            "meta_repo_path": "/local/gitnexus-mirrors/mindsong-juke-hub",
            "repo_path_match": True,
            "staleness_reason": "head_mismatch",
        },
    )
    monkeypatch.setattr(
        gitnexus_client,
        "_read_runtime_status",
        lambda _repo: {
            "state": "indexing",
            "job_id": "job-123",
            "progress": {"phase": "done", "percent": 98, "message": "Saving metadata..."},
            "updated_at": "2026-04-21T21:21:15Z",
            "mirror_root": "/local/gitnexus-mirrors/mindsong-juke-hub",
        },
    )
    monkeypatch.setattr(
        gitnexus_client,
        "_request_json",
        lambda *args, **kwargs: {
            "indexedAt": "2026-04-21T21:17:07.671Z",
            "stats": {"files": 34503, "nodes": 553007, "processes": 300},
        },
    )

    status = gitnexus_client.get_repo_status("mindsong-juke-hub")

    assert status["indexed"] is True
    assert status["fresh"] is False
    assert status["bootstrap_state"] == "indexing"
    assert status["bootstrap_progress"]["percent"] == 98
