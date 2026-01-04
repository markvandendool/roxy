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
import subprocess
from pathlib import Path

REPO_PATH = Path.home() / "mindsong-juke-hub"

def run_git(args):
    """Run git command and return result"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=REPO_PATH,
            capture_output=True,
            text=True,
            timeout=60
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# MCP Tool Definitions
TOOLS = {
    "git_status": {
        "description": "Get git repository status",
        "parameters": {}
    },
    "git_commit": {
        "description": "Stage all and commit with message",
        "parameters": {"message": {"type": "string", "required": True}}
    },
    "git_push": {
        "description": "Push commits to remote",
        "parameters": {}
    },
    "git_pull": {
        "description": "Pull changes from remote",
        "parameters": {}
    },
    "git_diff": {
        "description": "Show uncommitted changes",
        "parameters": {"staged": {"type": "boolean", "default": False}}
    },
    "git_log": {
        "description": "Show recent commits",
        "parameters": {"count": {"type": "integer", "default": 5}}
    }
}

def handle_tool(name, params={}):
    """Handle MCP tool call"""
    if name == "git_status":
        return run_git(["status", "--porcelain"])
    
    elif name == "git_commit":
        run_git(["add", "-A"])
        msg = params.get("message", "Update")
        return run_git(["commit", "-m", msg])
    
    elif name == "git_push":
        return run_git(["push"])
    
    elif name == "git_pull":
        return run_git(["pull"])
    
    elif name == "git_diff":
        args = ["diff", "--stat"]
        if params.get("staged"):
            args.insert(1, "--staged")
        return run_git(args)
    
    elif name == "git_log":
        count = params.get("count", 5)
        return run_git(["log", f"-{count}", "--oneline"])
    
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
