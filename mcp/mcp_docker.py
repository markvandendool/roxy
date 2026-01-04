#!/usr/bin/env python3
"""
MCP Docker Server - Container management for AI assistants
Part of LUNA-000 CITADEL P6: MCP Architecture

Exposes:
- docker_ps: List running containers
- docker_logs: Get container logs
- docker_restart: Restart container
- docker_stats: Get container stats
"""

import json
import subprocess

TOOLS = {
    "docker_ps": {
        "description": "List running containers",
        "parameters": {"all": {"type": "boolean", "default": False}}
    },
    "docker_logs": {
        "description": "Get container logs",
        "parameters": {
            "container": {"type": "string", "required": True},
            "lines": {"type": "integer", "default": 50}
        }
    },
    "docker_restart": {
        "description": "Restart a container",
        "parameters": {"container": {"type": "string", "required": True}}
    },
    "docker_stats": {
        "description": "Get container resource stats",
        "parameters": {}
    }
}

def run_docker(args):
    """Run docker command"""
    try:
        result = subprocess.run(
            ["docker"] + args,
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip(),
            "error": result.stderr.strip() if result.returncode != 0 else None
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def handle_tool(name, params={}):
    """Handle MCP tool call"""
    if name == "docker_ps":
        args = ["ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Image}}"]
        if params.get("all"):
            args.insert(1, "-a")
        result = run_docker(args)
        if result["success"]:
            containers = []
            for line in result["output"].split("\n"):
                if line:
                    parts = line.split("\t")
                    containers.append({
                        "name": parts[0],
                        "status": parts[1] if len(parts) > 1 else "",
                        "image": parts[2] if len(parts) > 2 else ""
                    })
            return {"containers": containers}
        return result
    
    elif name == "docker_logs":
        container = params.get("container")
        lines = params.get("lines", 50)
        return run_docker(["logs", "--tail", str(lines), container])
    
    elif name == "docker_restart":
        container = params.get("container")
        return run_docker(["restart", container])
    
    elif name == "docker_stats":
        result = run_docker([
            "stats", "--no-stream", "--format",
            "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
        ])
        if result["success"]:
            stats = []
            for line in result["output"].split("\n"):
                if line:
                    parts = line.split("\t")
                    stats.append({
                        "name": parts[0],
                        "cpu": parts[1] if len(parts) > 1 else "",
                        "memory": parts[2] if len(parts) > 2 else ""
                    })
            return {"stats": stats}
        return result
    
    return {"error": f"Unknown tool: {name}"}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        tool = sys.argv[1]
        params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        result = handle_tool(tool, params)
        print(json.dumps(result, indent=2))
    else:
        print("MCP Docker Server")
        print("Tools:", list(TOOLS.keys()))
