#!/usr/bin/env python3
"""
Base Tool Adapter - Wraps existing tools for LLM function calling
"""
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from abc import ABC, abstractmethod

logger = logging.getLogger("roxy.tools.adapter")

ROXY_DIR = Path.home() / ".roxy"


class BaseTool(ABC):
    """Base class for tool adapters"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters"""
        pass
    
    def to_function_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.get_parameters_schema()
        }
    
    @abstractmethod
    def get_parameters_schema(self) -> Dict[str, Any]:
        """Get JSON schema for parameters"""
        pass


class MCPToolAdapter(BaseTool):
    """Adapter for MCP server tools"""
    
    def __init__(self, tool_name: str, mcp_module_name: str, mcp_dir: Path = None):
        self.tool_name = tool_name
        self.mcp_module_name = mcp_module_name
        self.mcp_dir = mcp_dir or (ROXY_DIR / "mcp")
        self.mcp_module = None
        self._load_mcp_module()
        
        # Get description from module if available
        description = f"Execute {tool_name} via MCP server {mcp_module_name}"
        if self.mcp_module and hasattr(self.mcp_module, "TOOLS"):
            tool_def = self.mcp_module.TOOLS.get(tool_name, {})
            description = tool_def.get("description", description)
        
        super().__init__(tool_name, description)
    
    def _load_mcp_module(self):
        """Load MCP module"""
        try:
            import importlib.util
            mcp_file = self.mcp_dir / f"mcp_{self.mcp_module_name}.py"
            if mcp_file.exists():
                spec = importlib.util.spec_from_file_location(
                    self.mcp_module_name, mcp_file
                )
                self.mcp_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(self.mcp_module)
        except Exception as e:
            logger.warning(f"Failed to load MCP module {self.mcp_module_name}: {e}")
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute MCP tool"""
        try:
            if self.mcp_module and hasattr(self.mcp_module, "handle_tool"):
                result = self.mcp_module.handle_tool(self.tool_name, kwargs)
                return {"success": True, "result": result}
            else:
                return {"success": False, "error": "MCP module not loaded"}
        except Exception as e:
            logger.error(f"MCP tool {self.tool_name} execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        """Get parameters from MCP tool definition"""
        if self.mcp_module and hasattr(self.mcp_module, "TOOLS"):
            tool_def = self.mcp_module.TOOLS.get(self.tool_name, {})
            return tool_def.get("parameters", {
                "type": "object",
                "properties": {},
                "required": []
            })
        return {
            "type": "object",
            "properties": {},
            "required": []
        }


class CommandsToolAdapter(BaseTool):
    """Adapter for roxy_commands.py functions"""
    
    def __init__(self, command_type: str, description: str):
        self.command_type = command_type
        super().__init__(f"roxy_{command_type}", description)
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute roxy_commands.py command"""
        try:
            # Build command from kwargs
            command_parts = [self.command_type]
            
            # Add arguments based on command type
            if self.command_type == "git":
                if "action" in kwargs:
                    command_parts.append(kwargs["action"])
                if "message" in kwargs and kwargs.get("action") == "commit":
                    command_parts.append(kwargs["message"])
            elif self.command_type == "obs":
                if "command" in kwargs:
                    command_parts = [kwargs["command"]]
            elif self.command_type == "rag":
                if "query" in kwargs:
                    command_parts = [kwargs["query"]]
            
            # Execute via roxy_commands.py
            commands_script = ROXY_DIR / "roxy_commands.py"
            if not commands_script.exists():
                return {"success": False, "error": "roxy_commands.py not found"}
            
            result = subprocess.run(
                ["python3", str(commands_script)] + command_parts,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=ROXY_DIR
            )
            
            output = result.stdout or result.stderr or ""
            return {"success": True, "result": output.strip()}
        except Exception as e:
            logger.error(f"Command {self.command_type} execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        """Get parameters schema based on command type"""
        if self.command_type == "git":
            return {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["status", "commit", "push", "pull", "diff", "log"],
                        "description": "Git action to perform"
                    },
                    "message": {
                        "type": "string",
                        "description": "Commit message (required for commit action)"
                    }
                },
                "required": ["action"]
            }
        elif self.command_type == "obs":
            return {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "OBS command (e.g., 'start streaming', 'switch to game scene')"
                    }
                },
                "required": ["command"]
            }
        elif self.command_type == "rag":
            return {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Question to ask ROXY"
                    }
                },
                "required": ["query"]
            }
        elif self.command_type == "health":
            return {
                "type": "object",
                "properties": {},
                "required": []
            }
        elif self.command_type == "briefing":
            return {
                "type": "object",
                "properties": {},
                "required": []
            }
        else:
            return {
                "type": "object",
                "properties": {},
                "required": []
            }


class OptRoxyMCPToolAdapter(BaseTool):
    """Adapter for /opt/roxy/mcp-servers/* tools via mcp_registry"""
    
    def __init__(self, tool_name: str, server_name: str):
        self.tool_name = tool_name
        self.server_name = server_name
        self.server_path = None
        self._load_from_registry()
        
        description = f"Execute {tool_name} via {server_name} MCP server"
        super().__init__(tool_name, description)
    
    def _load_from_registry(self):
        """Load tool info from /opt/roxy/services/mcp_registry.py"""
        try:
            import sys
            opt_services = Path("/opt/roxy/services")
            if opt_services.exists():
                sys.path.insert(0, str(opt_services))
                from mcp_registry import MCPRegistry
                registry = MCPRegistry()
                tool_info = registry.find_tool(self.tool_name)
                if tool_info:
                    self.server_path = tool_info.get("path")
        except Exception as e:
            logger.debug(f"Failed to load from registry: {e}")
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute tool via MCP server"""
        # For now, return not implemented
        # In future, could call MCP server directly or via HTTP
        return {
            "success": False,
            "error": f"Tool {self.tool_name} from {self.server_name} - direct execution not yet implemented"
        }
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        """Get parameters schema"""
        return {
            "type": "object",
            "properties": {},
            "required": []
        }













