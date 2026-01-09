#!/usr/bin/env python3
"""
ROXY Tool Caller - LLM-driven tool execution
LLM decides which tools to call, executes them, integrates results
"""
import logging
import json
import re
from typing import Dict, Any, List, Optional
from tool_registry import get_tool_registry, ToolType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.tool_caller')

class ToolCaller:
    """Handles LLM-driven tool calling"""
    
    def __init__(self):
        self.registry = get_tool_registry()
        self.llm_service = None
        self._init_llm()
    
    def _init_llm(self):
        """Initialize LLM service"""
        try:
            from llm_wrapper import get_llm_service_safe
            self.llm_service = get_llm_service_safe()
        except Exception as e:
            logger.warning(f"LLM service unavailable: {e}")
    
    async def process_with_tools(self, user_input: str) -> str:
        """Process user input with tool calling"""
        # Step 1: Detect if tools are needed
        if not self._needs_tools(user_input):
            return None  # Let normal flow handle it
        
        # Step 2: Get tool suggestions from LLM
        tool_calls = await self._decide_tools(user_input)
        
        if not tool_calls:
            return None
        
        # Step 3: Execute tools
        results = []
        for tool_call in tool_calls:
            result = await self.registry.execute_tool(
                tool_call['name'],
                tool_call.get('arguments', {})
            )
            results.append(result)
        
        # Step 4: Integrate results into response
        return await self._integrate_results(user_input, results)
    
    def _needs_tools(self, user_input: str) -> bool:
        """Detect if user input needs tools"""
        user_lower = user_input.lower()
        
        # File operation keywords
        file_keywords = ['list', 'read', 'show', 'file', 'directory', 'folder', 'page', 'component']
        
        # Code operation keywords
        code_keywords = ['search', 'find', 'grep', 'code', 'function', 'class', 'import']
        
        # System operation keywords
        system_keywords = ['run', 'execute', 'command', 'script', 'test']
        
        all_keywords = file_keywords + code_keywords + system_keywords
        
        return any(keyword in user_lower for keyword in all_keywords)
    
    async def _decide_tools(self, user_input: str) -> List[Dict]:
        """Use LLM to decide which tools to call"""
        if not self.llm_service or not self.llm_service.is_available():
            # Fallback: simple pattern matching
            return self._pattern_match_tools(user_input)
        
        # Get available tools
        tools = self.registry.get_tools_for_llm()
        
        # Create prompt for tool selection
        prompt = f"""You are ROXY, an AI assistant with access to tools.

User request: {user_input}

Available tools:
{json.dumps(tools, indent=2)}

IMPORTANT: When calling tools, you MUST provide ALL required arguments as specified in the tool's parameters.
For example, "read_file" requires "file_path" argument. "list_files" requires "path" argument.

Decide which tools to call to fulfill the user's request. Return a JSON array of tool calls.

Format:
[
  {{
    "name": "tool_name",
    "arguments": {{"required_arg1": "value1", "optional_arg2": "value2"}}
  }}
]

CRITICAL: Include ALL required arguments. If you cannot determine a required argument from the user's request, DO NOT call that tool.

Return ONLY the JSON array, no other text."""

        try:
            response = await self.llm_service.generate_response(
                user_input=prompt,
                context={'mode': 'tool_selection'},
                history=[],
                facts=[]
            )
            
            # Parse JSON from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                tool_calls = json.loads(json_match.group(0))
                return tool_calls
        except Exception as e:
            logger.error(f"Tool decision error: {e}")
        
        # Fallback to pattern matching
        return self._pattern_match_tools(user_input)
    
    def _pattern_match_tools(self, user_input: str) -> List[Dict]:
        """Pattern matching fallback for tool selection"""
        user_lower = user_input.lower()
        tools = []
        
        # List files - detect repository questions
        if "list" in user_lower and ("page" in user_lower or "file" in user_lower or "component" in user_lower or "repo" in user_lower):
            # Extract path - prioritize mindsong-juke-hub
            path = "/home/mark/mindsong-juke-hub"
            if "mindsong" in user_lower or "juke" in user_lower:
                path = "/home/mark/mindsong-juke-hub"
            elif "roxy" in user_lower:
                path = "/home/mark/.roxy"
            
            # Check if path exists
            import os
            if not os.path.exists(path):
                # Try nested path
                nested_path = "/home/mark/mindsong-juke-hub/mindsong-juke-hub"
                if os.path.exists(nested_path):
                    path = nested_path
            
            tools.append({
                "name": "list_files",
                "arguments": {
                    "path": path,
                    "recursive": True
                }
            })
        
        # Read file - only if explicit file path is provided
        if "read" in user_lower and "file" in user_lower:
            # Try to extract file path from quotes or explicit path
            import re
            path_match = re.search(r'["\']([^"\']+)["\']', user_input)
            if not path_match:
                # Try to find path after "read file" or "read"
                path_match = re.search(r'read\s+(?:file\s+)?([a-zA-Z0-9_/\.\-]+)', user_input, re.IGNORECASE)
            if path_match:
                file_path = path_match.group(1)
                tools.append({
                    "name": "read_file",
                    "arguments": {
                        "file_path": file_path
                    }
                })
            # Don't add read_file if no path found - let LLM or other methods handle it
        
        # Search code
        if "search" in user_lower or "find" in user_lower:
            # Extract query
            query = user_input.replace("search", "").replace("find", "").strip()
            tools.append({
                "name": "search_code",
                "arguments": {
                    "query": query,
                    "max_results": 10
                }
            })
        
        return tools
    
    async def _integrate_results(self, user_input: str, results: List[Dict]) -> str:
        """Integrate tool results into natural language response"""
        if not results:
            return None
        
        # Build response from results
        response_parts = []
        
        for result in results:
            if result.get('success'):
                tool_name = result.get('tool', 'unknown')
                tool_result = result.get('result', {})
                
                if tool_name == 'list_files':
                    files = tool_result.get('files', [])
                    count = tool_result.get('count', 0)
                    if count > 0:
                        response_parts.append(f"Found {count} files:\n" + "\n".join(f"  • {f}" for f in files[:50]))
                    else:
                        error_msg = tool_result.get('error', 'No files found')
                        response_parts.append(f"File listing result: {error_msg}")
                
                elif tool_name == 'read_file':
                    content = tool_result.get('content', '')
                    file_path = tool_result.get('file_path', '')
                    if content:
                        response_parts.append(f"📄 File: {file_path}\n\n{content[:2000]}{'...' if len(content) > 2000 else ''}")
                    else:
                        response_parts.append(f"⚠️ Could not read file: {file_path}")
                
                elif tool_name == 'search_code':
                    search_results = tool_result.get('results', [])
                    count = tool_result.get('count', 0)
                    if search_results:
                        response_parts.append(f"🔍 Found {count} code matches:\n\n" + "\n".join([
                            f"  • {r.get('metadata', {}).get('file_path', 'unknown')}" 
                            for r in search_results[:10]
                        ]))
                    else:
                        response_parts.append(f"🔍 No code matches found for query: {tool_result.get('query', 'unknown')}")
            else:
                error = result.get('error', 'Unknown error')
                tool_name = result.get('tool', 'unknown')
                logger.warning(f"Tool {tool_name} failed: {error}")
                # Don't add error to response if it's a missing argument - let other methods try
                if 'Missing required argument' not in error and 'missing 1 required positional argument' not in error:
                    response_parts.append(f"⚠️ Tool {tool_name} error: {error}")
        
        if response_parts:
            return "\n\n".join(response_parts)
        return None  # Return None if no successful results, let other methods handle it

