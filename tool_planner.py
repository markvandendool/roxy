#!/usr/bin/env python3
"""
Tool Planner - Deterministic tool selection before LLM execution
Prevents bad tool calls (like read_file without file_path)
"""
import re
from typing import List, Dict, Any, Tuple, Optional


class ToolPlanner:
    """
    Deterministic routing based on query patterns
    Prevents LLM from making invalid tool calls
    """
    
    def __init__(self, repo_roots: List[str] = None):
        self.repo_roots = repo_roots or [
            "/home/mark/mindsong-juke-hub",
            "/home/mark/jarvis-docs",
            "/home/mark/.roxy"
        ]
    
    def plan_tools(self, user_query: str) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Determine which tools to call based on query pattern
        
        Returns:
            List of (tool_name, args) tuples in execution order
        """
        query_lower = user_query.lower()
        
        # PATTERN 1: Explicit file path provided
        file_path_match = re.search(r'([/~][\w/.]+\.[\w]+)', user_query)
        if file_path_match and any(kw in query_lower for kw in ['read', 'show', 'display', 'cat']):
            file_path = file_path_match.group(1)
            return [('read_file', {'file_path': file_path})]
        
        # PATTERN 2: "Read the repo" or "Read this code" - NEEDS path discovery first
        if re.search(r'read (the |this )?(repo|code|codebase|project)', query_lower):
            # Don't call read_file yet - get file list first
            return [
                ('list_files', {'directory': self.repo_roots[0], 'recursive': True, 'limit': 20}),
                # Then LLM can decide which files to read
            ]
        
        # PATTERN 3: Search/find query
        search_keywords = ['find', 'search', 'where is', 'locate', 'look for']
        if any(kw in query_lower for kw in search_keywords):
            # Extract search term
            search_term = self._extract_search_term(user_query)
            return [
                ('search_code', {'query': search_term, 'root': self.repo_roots[0]}),
            ]
        
        # PATTERN 4: List files / browse
        if any(kw in query_lower for kw in ['list files', 'show files', 'browse', 'ls', 'dir']):
            directory = self._extract_directory(user_query) or self.repo_roots[0]
            return [('list_files', {'directory': directory, 'recursive': False})]
        
        # PATTERN 5: Explain/analyze specific file
        if re.search(r'explain|analyze|what (does|is)', query_lower) and file_path_match:
            file_path = file_path_match.group(1)
            return [
                ('read_file', {'file_path': file_path}),
                # Then LLM explains the content
            ]
        
        # PATTERN 6: Question about codebase - use RAG
        if any(kw in query_lower for kw in ['what', 'how', 'why', 'when', 'explain', '?']):
            return [('query_rag', {'query': user_query})]
        
        # PATTERN 7: Command execution (if explicitly requested)
        if any(kw in query_lower for kw in ['run', 'execute', 'start', 'launch']):
            # Extract command (if provided)
            command = self._extract_command(user_query)
            if command:
                return [('execute_command', {'command': command})]
            else:
                # Ambiguous - ask for clarification
                return [('query_rag', {'query': 'How to execute commands in ROXY'})]
        
        # DEFAULT: RAG only (no file operations)
        return [('query_rag', {'query': user_query})]
    
    def _extract_search_term(self, query: str) -> str:
        """Extract search term from query"""
        # Remove action words
        search_query = re.sub(r'\b(find|search|where is|locate|look for)\b', '', query, flags=re.IGNORECASE)
        return search_query.strip()
    
    def _extract_directory(self, query: str) -> Optional[str]:
        """Extract directory path from query"""
        dir_match = re.search(r'([/~][\w/.]+)/?', query)
        if dir_match:
            return dir_match.group(1)
        return None
    
    def _extract_command(self, query: str) -> Optional[str]:
        """Extract shell command from query"""
        # Look for quoted command
        quoted = re.search(r'["`]([^"`]+)["`]', query)
        if quoted:
            return quoted.group(1)
        
        # Look for command after "run" or "execute"
        cmd_match = re.search(r'(?:run|execute)\s+(.+)', query, re.IGNORECASE)
        if cmd_match:
            return cmd_match.group(1).strip()
        
        return None
    
    def validate_tool_call(self, tool_name: str, args: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate that a tool call has all required arguments
        
        Returns:
            (is_valid, error_message)
        """
        required_args = {
            'read_file': ['file_path'],
            'search_code': ['query'],
            'list_files': ['directory'],
            'execute_command': ['command'],
            'query_rag': ['query'],
        }
        
        if tool_name not in required_args:
            return False, f"Unknown tool: {tool_name}"
        
        missing = [arg for arg in required_args[tool_name] if arg not in args or not args[arg]]
        
        if missing:
            return False, f"Missing required arguments for {tool_name}: {missing}"
        
        return True, ""
    
    def get_safe_fallback(self, original_query: str, failed_tool: str) -> List[Tuple[str, Dict[str, Any]]]:
        """
        When a tool call fails, provide safe fallback
        """
        if failed_tool == 'read_file':
            # Fallback: List files first
            return [('list_files', {'directory': self.repo_roots[0], 'recursive': True})]
        
        elif failed_tool in ['search_code', 'list_files']:
            # Fallback: RAG query
            return [('query_rag', {'query': original_query})]
        
        else:
            # Ultimate fallback: Just query RAG
            return [('query_rag', {'query': f"How to {original_query}"})]


# Singleton instance
_tool_planner = None

def get_tool_planner(repo_roots: List[str] = None) -> ToolPlanner:
    """Get or create ToolPlanner instance"""
    global _tool_planner
    if _tool_planner is None:
        _tool_planner = ToolPlanner(repo_roots)
    return _tool_planner
