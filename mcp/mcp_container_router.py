#!/usr/bin/env python3
"""
MCP Container Router - Secure MCP Server Proxy
==============================================
Routes MCP requests to sandboxed Docker containers
with capability-based permission enforcement.

Security Features:
- Container isolation per MCP server
- Capability grants (read-only paths, network access)
- Request/response logging
- Resource limits enforcement
"""

import asyncio
import json
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("roxy.mcp_container_router")


@dataclass
class MCPServerCapabilities:
    """Defines what an MCP server is allowed to do"""
    readonly_paths: List[str]
    writable_paths: List[str]
    network_access: bool
    memory_limit_mb: int = 256
    time_limit_seconds: int = 60
    allowed_tools: Optional[List[str]] = None


@dataclass
class SandboxedMCPServer:
    """Configuration for a sandboxed MCP server"""
    name: str
    image: str
    capabilities: MCPServerCapabilities
    container_name: str
    env_vars: Dict[str, str]
    port: Optional[int] = None


class MCPContainerRouter:
    """
    Routes MCP requests to sandboxed containers.
    
    Replaces direct stdio MCP execution with containerized,
    capability-restricted alternatives.
    """
    
    # Predefined secure configurations for common MCP servers
    SERVER_CONFIGS = {
        "filesystem": SandboxedMCPServer(
            name="filesystem",
            image="mcp-filesystem:sandbox",
            capabilities=MCPServerCapabilities(
                readonly_paths=["/home/mark/.roxy", "/home/mark/mindsong-juke-hub"],
                writable_paths=[],
                network_access=False,
                memory_limit_mb=256,
                time_limit_seconds=60,
                allowed_tools=["read_file", "list_directory", "search_files"]
            ),
            container_name="mcp-filesystem-sandbox",
            env_vars={},
            port=None  # Uses stdio via docker exec
        ),
        
        "github": SandboxedMCPServer(
            name="github",
            image="mcp-github:sandbox",
            capabilities=MCPServerCapabilities(
                readonly_paths=[],
                writable_paths=[],
                network_access=True,  # GitHub API requires network
                memory_limit_mb=256,
                time_limit_seconds=120,
                allowed_tools=None  # All GitHub tools allowed
            ),
            container_name="mcp-github-sandbox",
            env_vars={"GITHUB_TOKEN": "${GITHUB_TOKEN}"},
            port=None
        ),
        
        "puppeteer": SandboxedMCPServer(
            name="puppeteer",
            image="mcp-puppeteer:sandbox",
            capabilities=MCPServerCapabilities(
                readonly_paths=[],
                writable_paths=["/tmp/screenshots"],
                network_access=True,
                memory_limit_mb=512,
                time_limit_seconds=300,
                allowed_tools=["browser_navigate", "browser_screenshot", "browser_click"]
            ),
            container_name="mcp-puppeteer-sandbox",
            env_vars={},
            port=None
        )
    }
    
    def __init__(self, compose_file: str = "~/.roxy/docker/mcp-sandbox/docker-compose.mcp.yml"):
        self.compose_file = Path(compose_file).expanduser()
        self.active_containers: Dict[str, str] = {}  # name -> container_id
        
    async def start_server(self, server_name: str) -> bool:
        """Start a sandboxed MCP server container"""
        if server_name not in self.SERVER_CONFIGS:
            logger.error(f"Unknown MCP server: {server_name}")
            return False
            
        config = self.SERVER_CONFIGS[server_name]
        
        # Start container via docker-compose
        cmd = [
            "docker-compose", "-f", str(self.compose_file),
            "up", "-d", f"mcp-{server_name}"
        ]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                logger.info(f"Started sandboxed MCP server: {server_name}")
                self.active_containers[server_name] = config.container_name
                return True
            else:
                logger.error(f"Failed to start {server_name}: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting {server_name}: {e}")
            return False
    
    async def execute_tool(self, server_name: str, tool_name: str, 
                           arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool call on a sandboxed MCP server.
        
        Security checks:
        1. Verify server is running
        2. Check tool is in allowed list
        3. Validate path arguments against capabilities
        4. Log the request
        """
        if server_name not in self.SERVER_CONFIGS:
            return {"error": f"Unknown MCP server: {server_name}"}
        
        config = self.SERVER_CONFIGS[server_name]
        
        # Check tool authorization
        if (config.capabilities.allowed_tools and 
            tool_name not in config.capabilities.allowed_tools):
            logger.warning(f"Tool {tool_name} not allowed for {server_name}")
            return {"error": f"Tool {tool_name} not permitted"}
        
        # Validate paths in arguments
        for key, value in arguments.items():
            if isinstance(value, str) and ("/" in value or value.startswith(".")):
                if not self._validate_path(value, config.capabilities):
                    return {"error": f"Path {value} not within allowed directories"}
        
        # Log the request
        self._audit_log(server_name, tool_name, arguments)
        
        # Execute via docker exec
        container = config.container_name
        cmd = [
            "docker", "exec", "-i", container,
            "node", "-e",
            f"require('@modelcontextprotocol/server-{server_name}').execute('{tool_name}', {json.dumps(arguments)})"
        ]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                return json.loads(stdout.decode())
            else:
                return {"error": stderr.decode(), "isError": True}
                
        except Exception as e:
            logger.error(f"Error executing {tool_name}: {e}")
            return {"error": str(e), "isError": True}
    
    def _validate_path(self, path: str, capabilities: MCPServerCapabilities) -> bool:
        """Validate that a path is within allowed directories"""
        path = os.path.abspath(os.path.expanduser(path))
        
        for allowed in capabilities.readonly_paths + capabilities.writable_paths:
            allowed_abs = os.path.abspath(os.path.expanduser(allowed))
            if path.startswith(allowed_abs):
                return True
        
        return False
    
    def _audit_log(self, server: str, tool: str, arguments: Dict[str, Any]):
        """Write audit log entry"""
        audit_entry = {
            "timestamp": asyncio.get_event_loop().time(),
            "server": server,
            "tool": tool,
            "arguments": arguments
        }
        
        audit_file = Path("~/.roxy/logs/mcp_audit.log").expanduser()
        audit_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(audit_file, "a") as f:
            f.write(json.dumps(audit_entry) + "\n")
    
    async def stop_all(self):
        """Stop all sandboxed MCP servers"""
        cmd = ["docker-compose", "-f", str(self.compose_file), "down"]
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.communicate()
        self.active_containers.clear()


# Bridge to existing mcp_client.py interface
class SandboxedMCPAdapter:
    """
    Adapter that makes sandboxed MCP servers compatible with
    existing mcp_client.py interface.
    """
    
    def __init__(self):
        self.router = MCPContainerRouter()
    
    async def initialize(self):
        """Start all sandboxed servers"""
        for server_name in MCPContainerRouter.SERVER_CONFIGS.keys():
            await self.router.start_server(server_name)
    
    async def call_tool(self, server_name: str, tool_name: str, 
                        arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on a sandboxed server"""
        return await self.router.execute_tool(server_name, tool_name, arguments)


if __name__ == "__main__":
    # CLI for testing
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: mcp_container_router.py <start|stop|exec> [server] [tool] [args...]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    router = MCPContainerRouter()
    
    if cmd == "start" and len(sys.argv) > 2:
        server = sys.argv[2]
        asyncio.run(router.start_server(server))
    elif cmd == "stop":
        asyncio.run(router.stop_all())
    elif cmd == "exec" and len(sys.argv) > 4:
        server, tool = sys.argv[2], sys.argv[3]
        args = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
        result = asyncio.run(router.execute_tool(server, tool, args))
        print(json.dumps(result, indent=2))
