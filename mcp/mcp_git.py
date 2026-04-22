#!/usr/bin/env python3
"""
MCP Git Server - Git operations for AI assistants
Part of LUNA-000 CITADEL P6: MCP Architecture

Exposes:
- git_status: Get repository status
- git_commit: Stage and commit changes
- git_push: Push to remote
- git_pull: Pull from remote
- git_diff: Show changes
- git_log: Recent commits
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional


def _find_git_root(path: Path) -> Optional[Path]:
    candidate = path.expanduser()
    if candidate.is_file():
        candidate = candidate.parent
    for current in (candidate, *candidate.parents):
        if (current / ".git").exists():
            return current
    return None


def _default_repo_path() -> Path:
    override = os.getenv("ROXY_GIT_REPO")
    if override:
        root = _find_git_root(Path(override))
        if root:
            return root
    for candidate in (
        Path.home() / ".roxy",
        Path.home() / "mindsong-juke-hub-sandbox",
        Path.home() / "mindsong-juke-hub",
    ):
        root = _find_git_root(candidate)
        if root:
            return root
    return Path.home() / ".roxy"


def _resolve_repo_path(params=None):
    params = params or {}
    for key in ("repo_path", "path", "repo"):
        value = params.get(key)
        if not value:
            continue
        raw = Path(str(value)).expanduser()
        if raw.is_absolute():
            root = _find_git_root(raw)
            if root:
                return root
        else:
            for candidate in (
                Path.home() / str(value),
                Path.home() / "work" / str(value),
                Path.home() / str(value).replace("/", "_"),
            ):
                root = _find_git_root(candidate)
                if root:
                    return root
    return _default_repo_path()


def run_git(args, repo_path=None):
    """Run git command and return result"""
    resolved_repo = _resolve_repo_path(repo_path or {})
    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    env.setdefault("GIT_ASKPASS", "/bin/true")
    env.setdefault("SSH_ASKPASS", "/bin/true")
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=resolved_repo,
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "repo_path": str(resolved_repo),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "repo_path": str(resolved_repo)}

# MCP Tool Definitions
TOOLS = {
    "git_status": {
        "description": "Get git repository status",
        "parameters": {"repo": {"type": "string", "required": False}}
    },
    "git_commit": {
        "description": "Stage all and commit with message",
        "parameters": {"message": {"type": "string", "required": True}, "repo": {"type": "string", "required": False}}
    },
    "git_push": {
        "description": "Push commits to remote",
        "parameters": {"repo": {"type": "string", "required": False}}
    },
    "git_pull": {
        "description": "Pull changes from remote",
        "parameters": {"repo": {"type": "string", "required": False}}
    },
    "git_diff": {
        "description": "Show uncommitted changes",
        "parameters": {"staged": {"type": "boolean", "default": False}, "repo": {"type": "string", "required": False}}
    },
    "git_log": {
        "description": "Show recent commits",
        "parameters": {"count": {"type": "integer", "default": 5}, "repo": {"type": "string", "required": False}}
    }
}

def handle_tool(name, params={}):
    """Handle MCP tool call"""
    if name == "git_status":
        return run_git(["status", "--porcelain", "--branch"], params)
    
    elif name == "git_commit":
        run_git(["add", "-A"], params)
        msg = params.get("message", "Update")
        return run_git(["commit", "-m", msg], params)
    
    elif name == "git_push":
        return run_git(["push"], params)
    
    elif name == "git_pull":
        return run_git(["pull"], params)
    
    elif name == "git_diff":
        args = ["diff", "--stat"]
        if params.get("staged"):
            args.insert(1, "--staged")
        return run_git(args, params)
    
    elif name == "git_log":
        count = params.get("count", 5)
        return run_git(["log", f"-{count}", "--oneline"], params)
    
    return {"error": f"Unknown tool: {name}"}

if __name__ == "__main__":
    # Test mode
    import sys
    if len(sys.argv) > 1:
        tool = sys.argv[1]
        params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        result = handle_tool(tool, params)
        print(json.dumps(result, indent=2))
    else:
        print("MCP Git Server")
        print("Tools:", list(TOOLS.keys()))
