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
    monkeypatch.setitem(gitnexus_client.REPO_PATH_HINTS, "mindsong-juke-hub", str(repo))

    state = gitnexus_client._read_local_index_state("mindsong-juke-hub")

    assert state["indexed_commit"] == current_head
    assert state["current_commit"] == new_head
    assert state["meta_repo_path"] == str(repo)
    assert state["repo_path_match"] is True
    assert state["fresh"] is False
    assert state["staleness_reason"] == "head_mismatch"
    assert state["indexed_at_local"] == "2026-04-21T19:04:36.853Z"
