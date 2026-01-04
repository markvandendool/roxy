#!/usr/bin/env python3
"""
MCP Tool Adapter - Discovers and wraps ~/.roxy/mcp/* servers
"""
import logging
from pathlib import Path
from typing import Dict, List
from .adapter import MCPToolAdapter, BaseTool

logger = logging.getLogger("roxy.tools.mcp")

ROXY_DIR = Path.home() / ".roxy"
MCP_DIR = ROXY_DIR / "mcp"


def discover_mcp_tools() -> List[BaseTool]:
    """Discover all MCP tools from ~/.roxy/mcp/*"""
    tools = []
    
    if not MCP_DIR.exists():
        logger.debug(f"MCP directory not found: {MCP_DIR}")
        return tools
    
    # Load each mcp_*.py file
    for mcp_file in MCP_DIR.glob("mcp_*.py"):
        if mcp_file.name == "mcp_server.py":
            continue
        
        module_name = mcp_file.stem.replace("mcp_", "")
        
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(module_name, mcp_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check if module has TOOLS definition
            if hasattr(module, "TOOLS"):
                for tool_name, tool_def in module.TOOLS.items():
                    adapter = MCPToolAdapter(tool_name, module_name, MCP_DIR)
                    tools.append(adapter)
                    logger.debug(f"Discovered MCP tool: {tool_name} from {module_name}")
        except Exception as e:
            logger.warning(f"Failed to load MCP module {module_name}: {e}")
    
    return tools













