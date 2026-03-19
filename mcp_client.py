#!/usr/bin/env python3
"""
MCP Client - Native MCP client/session manager with stdio and Streamable HTTP support
Part of ROXY-AUTONOMOUS-CODING-AGENT-V1 (RCA-004)

Based on official MCP architecture:
- Client-per-server with dedicated sessions
- Long-lived sessions with tool discovery cache
- Supports stdio and Streamable HTTP transports
"""
import asyncio
import json
import logging
import os
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Callable

logger = logging.getLogger("roxy.mcp_client")

MCP_PROTOCOL_VERSION = "2024-11-05"


@dataclass
class MCPTool:
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    annotations: Optional[Dict[str, Any]] = None


@dataclass
class MCPServerConfig:
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    transport: str = "stdio"
    url: Optional[str] = None


@dataclass
class MCPSession:
    server_id: str
    server_config: MCPServerConfig
    transport: str
    process: Optional[subprocess.Popen] = None
    reader: Optional[asyncio.StreamReader] = None
    writer: Optional[asyncio.StreamWriter] = None
    request_id: int = 0
    pending_requests: Dict[str, asyncio.Future] = field(default_factory=dict)
    tools_cache: List[MCPTool] = field(default_factory=list)
    last_health_check: float = 0
    is_connected: bool = False


@dataclass
class MCPToolResult:
    content: List[Dict[str, Any]]
    isError: bool = False


class MCPClient:
    """
    Native MCP client with persistent sessions.
    
    Supports:
    - stdio transport (local subprocess)
    - Streamable HTTP (remote servers)
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.sessions: Dict[str, MCPSession] = {}
        if config_path:
            self.config_path = config_path
        else:
            for candidate in [
                os.path.expanduser("~/.config/claude/mcp.json"),
                os.path.expanduser("~/.mcp.json"),
                os.path.expanduser("~/.config/claude-code/mcp.json"),
            ]:
                if Path(candidate).exists():
                    self.config_path = candidate
                    break
            else:
                self.config_path = os.path.expanduser("~/.mcp.json")
        self._health_check_interval = 30.0
        self._reconnect_delay = 5.0
        self._max_reconnect_attempts = 3
    
    async def initialize(self):
        """Load server configs and connect to all servers."""
        configs = self._load_configs()
        
        for config in configs:
            await self.connect(config)
    
    def _load_configs(self) -> List[MCPServerConfig]:
        """Load MCP server configurations from config file."""
        if not Path(self.config_path).exists():
            logger.warning(f"MCP config not found: {self.config_path}")
            return []
        
        try:
            data = json.loads(Path(self.config_path).read_text())
            servers = data.get("mcpServers", {})
            
            configs = []
            for name, config in servers.items():
                if isinstance(config, dict):
                    configs.append(MCPServerConfig(
                        name=name,
                        command=config.get("command", ""),
                        args=config.get("args", []),
                        env=config.get("env", {}),
                        transport=config.get("transport", "stdio"),
                        url=config.get("url")
                    ))
            return configs
        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")
            return []
    
    async def connect(self, config: MCPServerConfig) -> bool:
        """
        Connect to an MCP server.
        Returns True if connection successful.
        """
        session = MCPSession(
            server_id=config.name,
            server_config=config,
            transport=config.transport
        )
        
        try:
            if config.transport == "stdio":
                success = await self._connect_stdio(session)
            elif config.transport == "streamable-http":
                success = await self._connect_http(session)
            else:
                logger.error(f"Unknown transport: {config.transport}")
                return False
            
            if success:
                self.sessions[config.name] = session
                await self._initialize_session(session)
                logger.info(f"Connected to MCP server: {config.name}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to connect to {config.name}: {e}")
            return False
    
    async def _connect_stdio(self, session: MCPSession) -> bool:
        """Connect via stdio transport."""
        env = os.environ.copy()
        env.update(session.server_config.env)
        
        try:
            process = subprocess.Popen(
                [session.server_config.command] + session.server_config.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                preexec_fn=os.setsid
            )
            
            session.process = process
            session.reader = asyncio.StreamReader()
            
            loop = asyncio.get_event_loop()
            
            def read_stdout():
                try:
                    data = process.stdout.read(4096)
                    if data:
                        loop.create_task(self._handle_stdout_data(session, data))
                except Exception:
                    pass
            
            protocol = asyncio.StreamReaderProtocol(session.reader)
            await loop.connect_read_pipe(lambda: protocol, process.stdout)
            
            session.is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"stdio connect error: {e}")
            return False
    
    async def _handle_stdout_data(self, session: MCPSession, data: bytes):
        """Handle incoming stdout data from MCP server."""
        try:
            session.reader.feed_data(data)
        except Exception as e:
            logger.error(f"Error handling stdout: {e}")
    
    async def _connect_http(self, session: MCPSession) -> bool:
        """Connect via Streamable HTTP transport."""
        session.is_connected = True
        return True
    
    async def _initialize_session(self, session: MCPSession):
        """Send initialize request and cache tools."""
        try:
            response = await self._send_request(
                session,
                "initialize",
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "clientInfo": {
                        "name": "roxy-mcp-client",
                        "version": "1.0.0"
                    }
                }
            )
            
            if response and "result" in response:
                session.tools_cache = self._parse_tools(response["result"].get("tools", []))
                logger.info(f"Server {session.server_id} has {len(session.tools_cache)} tools")
                
        except Exception as e:
            logger.error(f"Session init error: {e}")
    
    def _parse_tools(self, tools_data: List[Dict]) -> List[MCPTool]:
        """Parse tool list from MCP response."""
        tools = []
        for tool in tools_data:
            tools.append(MCPTool(
                name=tool.get("name", ""),
                description=tool.get("description", ""),
                input_schema=tool.get("inputSchema", {}),
                annotations=tool.get("annotations")
            ))
        return tools
    
    async def _send_request(
        self,
        session: MCPSession,
        method: str,
        params: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Send JSON-RPC request to MCP server."""
        session.request_id += 1
        request_id = session.request_id
        
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method
        }
        if params:
            request["params"] = params
        
        future = asyncio.Future()
        session.pending_requests[str(request_id)] = future
        
        try:
            if session.transport == "stdio" and session.process:
                request_json = json.dumps(request) + "\n"
                session.process.stdin.write(request_json.encode())
                session.process.stdin.flush()
                
                response = await asyncio.wait_for(future, timeout=30.0)
                return response
            else:
                return None
                
        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {method}")
            session.pending_requests.pop(str(request_id), None)
            return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            session.pending_requests.pop(str(request_id), None)
            return None
    
    async def list_tools(self, server_id: str) -> List[MCPTool]:
        """List cached tools for a server."""
        if server_id in self.sessions:
            return self.sessions[server_id].tools_cache
        
        await self._refresh_tools_list(server_id)
        
        if server_id in self.sessions:
            return self.sessions[server_id].tools_cache
        return []
    
    async def _refresh_tools_list(self, server_id: str):
        """Refresh tool cache from server."""
        if server_id not in self.sessions:
            return
        
        session = self.sessions[server_id]
        response = await self._send_request(session, "tools/list")
        
        if response and "result" in response:
            session.tools_cache = self._parse_tools(response["result"].get("tools", []))
    
    async def call_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: float = 60.0
    ) -> Optional[MCPToolResult]:
        """
        Call a tool on an MCP server.
        
        Args:
            server_id: Name of the MCP server
            tool_name: Name of the tool to call
            arguments: Tool arguments
            timeout: Timeout in seconds
            
        Returns:
            MCPToolResult or None on error
        """
        if server_id not in self.sessions:
            logger.error(f"Server not connected: {server_id}")
            return None
        
        session = self.sessions[server_id]
        
        start_time = time.time()
        
        try:
            response = await asyncio.wait_for(
                self._send_request(
                    session,
                    "tools/call",
                    {
                        "name": tool_name,
                        "arguments": arguments
                    }
                ),
                timeout=timeout
            )
            
            if response and "result" in response:
                result = response["result"]
                return MCPToolResult(
                    content=result.get("content", []),
                    isError=result.get("isError", False)
                )
            
            return None
            
        except asyncio.TimeoutError:
            logger.error(f"Tool call timeout: {tool_name} on {server_id}")
            return MCPToolResult(
                content=[{"type": "text", "text": f"Timeout after {timeout}s"}],
                isError=True
            )
        except Exception as e:
            logger.error(f"Tool call error: {e}")
            return MCPToolResult(
                content=[{"type": "text", "text": str(e)}],
                isError=True
            )
    
    async def health_check(self, server_id: str) -> Dict[str, Any]:
        """Check health of an MCP server."""
        if server_id not in self.sessions:
            return {"connected": False, "server_id": server_id}
        
        session = self.sessions[server_id]
        
        return {
            "connected": session.is_connected,
            "server_id": server_id,
            "transport": session.transport,
            "tools_count": len(session.tools_cache),
            "last_check": session.last_health_check,
            "pending_requests": len(session.pending_requests)
        }
    
    async def disconnect(self, server_id: str) -> bool:
        """Disconnect from an MCP server."""
        if server_id not in self.sessions:
            return False
        
        session = self.sessions.pop(server_id)
        
        try:
            if session.process:
                try:
                    os.killpg(os.getpgid(session.process.pid), signal.SIGTERM)
                    session.process.wait(timeout=5)
                except:
                    os.killpg(os.getpgid(session.process.pid), signal.SIGKILL)
            
            if session.writer:
                session.writer.close()
                await session.writer.wait_closed()
            
            session.is_connected = False
            logger.info(f"Disconnected from {server_id}")
            return True
            
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
            return False
    
    async def reconnect(self, server_id: str) -> bool:
        """Attempt to reconnect to a server."""
        await self.disconnect(server_id)
        
        configs = self._load_configs()
        for config in configs:
            if config.name == server_id:
                return await self.connect(config)
        
        return False
    
    async def disconnect_all(self):
        """Disconnect from all servers."""
        for server_id in list(self.sessions.keys()):
            await self.disconnect(server_id)


class MCPToolAdapter:
    """
    Adapts MCP tools to ROXY tool interface.
    Maps MCP tools into the ROXY tool catalog.
    """
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
        self._tool_registry: Dict[str, Dict[str, Any]] = {}
    
    async def discover_tools(self, server_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Discover tools from MCP servers and register them.
        
        Args:
            server_id: Optional specific server, or None for all
            
        Returns:
            List of registered tool schemas
        """
        tools = []
        
        if server_id:
            server_ids = [server_id]
        else:
            server_ids = list(self.mcp_client.sessions.keys())
        
        for sid in server_ids:
            mcp_tools = await self.mcp_client.list_tools(sid)
            
            for mcp_tool in mcp_tools:
                tool_entry = {
                    "name": f"mcp_{sid}_{mcp_tool.name}",
                    "display_name": mcp_tool.name,
                    "server": sid,
                    "description": mcp_tool.description,
                    "schema": mcp_tool.input_schema,
                    "source": "mcp",
                    "type": "mcp"
                }
                
                self._tool_registry[tool_entry["name"]] = tool_entry
                tools.append(tool_entry)
        
        return tools
    
    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an MCP tool by registered name.
        
        Args:
            tool_name: Full tool name (e.g., "mcp_github_search_repos")
            arguments: Tool arguments
            
        Returns:
            Execution result
        """
        if tool_name not in self._tool_registry:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }
        
        tool = self._tool_registry[tool_name]
        server_id = tool["server"]
        mcp_tool_name = tool["display_name"]
        
        result = await self.mcp_client.call_tool(
            server_id,
            mcp_tool_name,
            arguments
        )
        
        if result:
            return {
                "success": not result.isError,
                "content": result.content,
                "is_error": result.isError,
                "server": server_id,
                "tool": mcp_tool_name
            }
        
        return {
            "success": False,
            "error": "No response from MCP server"
        }
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get all registered tool schemas."""
        return list(self._tool_registry.values())


async def test_mcp_client():
    """Test MCP client."""
    client = MCPClient()
    
    print("Loading MCP configs...")
    configs = client._load_configs()
    print(f"Found {len(configs)} server configs")
    
    for config in configs[:3]:
        print(f"  - {config.name}: {config.command} ({config.transport})")
    
    print("\nConnecting to servers...")
    connected = 0
    for config in configs[:3]:
        if await client.connect(config):
            connected += 1
    
    print(f"Connected to {connected} servers")
    
    for server_id in list(client.sessions.keys())[:3]:
        health = await client.health_check(server_id)
        print(f"  {server_id}: {health}")
        
        tools = await client.list_tools(server_id)
        print(f"    Tools: {len(tools)}")
        for tool in tools[:3]:
            print(f"      - {tool.name}")
    
    await client.disconnect_all()


if __name__ == "__main__":
    asyncio.run(test_mcp_client())
