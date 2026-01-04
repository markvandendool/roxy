#!/usr/bin/env python3
"""
Tool Registry - Discovers and manages all available tools
"""
import logging
from typing import Dict, List, Optional
from .adapter import BaseTool
from .mcp_adapter import discover_mcp_tools
from .commands_adapter import discover_command_tools

logger = logging.getLogger("roxy.tools.registry")


class ToolRegistry:
    """Registry for all available tools"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self._discover_tools()
    
    def _discover_tools(self):
        """Discover all available tools"""
        logger.info("Discovering tools...")
        
        # Discover MCP tools
        mcp_tools = discover_mcp_tools()
        for tool in mcp_tools:
            self.tools[tool.name] = tool
            logger.info(f"  ✓ {tool.name} (MCP)")
        
        # Discover command tools
        cmd_tools = discover_command_tools()
        for tool in cmd_tools:
            self.tools[tool.name] = tool
            logger.info(f"  ✓ {tool.name} (command)")
        
        logger.info(f"Total tools discovered: {len(self.tools)}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get tool by name"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[BaseTool]:
        """List all tools"""
        return list(self.tools.values())
    
    def get_function_schemas(self) -> List[Dict]:
        """Get all tools as OpenAI function calling schemas"""
        return [tool.to_function_schema() for tool in self.tools.values()]
    
    def execute_tool(self, name: str, **kwargs) -> Dict:
        """Execute a tool by name"""
        tool = self.get_tool(name)
        if not tool:
            return {"success": False, "error": f"Tool {name} not found"}
        
        try:
            return tool.execute(**kwargs)
        except Exception as e:
            logger.error(f"Tool {name} execution failed: {e}")
            return {"success": False, "error": str(e)}


# Global registry instance
_registry_instance = None


def get_tool_registry() -> ToolRegistry:
    """Get global tool registry instance"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry()
    return _registry_instance














