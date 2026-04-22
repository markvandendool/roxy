import importlib.util
from pathlib import Path

MODULE_PATH = Path.home() / ".roxy" / "mcp" / "mcp_git.py"
SPEC = importlib.util.spec_from_file_location("roxy_mcp_git", MODULE_PATH)
mcp_git = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mcp_git)


def test_resolve_repo_path_honors_explicit_path(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    resolved = mcp_git._resolve_repo_path({"repo": str(repo)})
    assert resolved == repo


def test_default_repo_path_prefers_roxy_when_present():
    resolved = mcp_git._default_repo_path()
    assert resolved.exists()
    assert (resolved / ".git").exists()
