#!/usr/bin/env python3
"""
Commands Tool Adapter - Wraps ~/.roxy/roxy_commands.py functions
"""
import logging
from typing import List
from .adapter import CommandsToolAdapter, BaseTool

logger = logging.getLogger("roxy.tools.commands")


def discover_command_tools() -> List[BaseTool]:
    """Discover all command tools from roxy_commands.py"""
    tools = []
    
    # Map command types to descriptions
    command_types = {
        "git": "Execute git operations (status, commit, push, pull, diff, log)",
        "obs": "Control OBS Studio (streaming, recording, scenes)",
        "health": "Check system health and status",
        "briefing": "Generate daily briefing",
        "rag": "Query ROXY knowledge base using RAG"
    }
    
    for cmd_type, description in command_types.items():
        adapter = CommandsToolAdapter(cmd_type, description)
        tools.append(adapter)
        logger.debug(f"Discovered command tool: {cmd_type}")
    
    return tools















