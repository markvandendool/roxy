#!/usr/bin/env python3
"""
Streaming Tools - Read/Write/Edit/Glob/Grep as native tool calls
Part of ROXY-AUTONOMOUS-CODING-AGENT-V1 (RCA-002)
"""
import asyncio
import difflib
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Dict, Any, List, Optional, Tuple

logger = logging.getLogger("roxy.streaming_tools")

MAX_FILE_SIZE = 1024 * 1024
MAX_SEARCH_RESULTS = 100


@dataclass
class ToolResponse:
    success: bool
    data: Any = None
    error: str = ""
    tool_name: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class StreamingTools:
    """Collection of file operations as async tools."""
    
    def __init__(self, workdir: Optional[str] = None):
        self.workdir = workdir or os.getcwd()
    
    async def read_file(
        self,
        file_path: str,
        offset: int = 0,
        limit: int = None,
        stream_callback=None
    ) -> ToolResponse:
        """
        Read file content with optional streaming.
        
        Args:
            file_path: Path to file (absolute or relative to workdir)
            offset: Line number to start from (1-indexed)
            limit: Maximum lines to read (None = all)
            stream_callback: Optional async callback for streaming
            
        Returns:
            ToolResponse with file content
        """
        try:
            path = self._resolve_path(file_path)
            
            if not path.exists():
                return ToolResponse(
                    success=False,
                    error=f"File not found: {file_path}",
                    tool_name="read"
                )
            
            if not path.is_file():
                return ToolResponse(
                    success=False,
                    error=f"Not a file: {file_path}",
                    tool_name="read"
                )
            
            file_size = path.stat().st_size
            if file_size > MAX_FILE_SIZE:
                return ToolResponse(
                    success=False,
                    error=f"File too large: {file_size} bytes (max {MAX_FILE_SIZE})",
                    tool_name="read"
                )
            
            content = path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            if offset > 0:
                lines = lines[offset - 1:]
            
            if limit is not None:
                lines = lines[:limit]
            
            result_lines = []
            for i, line in enumerate(lines, start=offset or 1):
                line_content = f"{i}: {line}\n"
                result_lines.append(line_content)
                if stream_callback:
                    await stream_callback(line_content)
            
            final_content = ''.join(result_lines)
            
            return ToolResponse(
                success=True,
                data=final_content,
                tool_name="read",
                metadata={
                    "file_path": str(path),
                    "lines_read": len(result_lines),
                    "total_lines": len(content.split('\n')),
                    "offset": offset,
                    "limit": limit,
                    "size_bytes": file_size
                }
            )
            
        except PermissionError:
            return ToolResponse(
                success=False,
                error=f"Permission denied: {file_path}",
                tool_name="read"
            )
        except UnicodeDecodeError:
            return ToolResponse(
                success=False,
                error=f"Cannot decode file as UTF-8: {file_path}",
                tool_name="read"
            )
        except Exception as e:
            logger.error(f"Read error: {e}")
            return ToolResponse(
                success=False,
                error=str(e),
                tool_name="read"
            )
    
    async def write_file(
        self,
        file_path: str,
        content: str,
        create_parents: bool = True
    ) -> ToolResponse:
        """
        Write content to file (creates if not exists, overwrites if exists).
        
        Args:
            file_path: Path to file (absolute or relative to workdir)
            content: Content to write
            create_parents: Create parent directories if needed
            
        Returns:
            ToolResponse with write result
        """
        try:
            path = self._resolve_path(file_path)
            
            if create_parents:
                path.parent.mkdir(parents=True, exist_ok=True)
            
            path.write_text(content, encoding='utf-8')
            
            return ToolResponse(
                success=True,
                data={"path": str(path), "bytes_written": len(content.encode('utf-8'))},
                tool_name="write",
                metadata={"file_path": str(path), "size": len(content)}
            )
            
        except PermissionError:
            return ToolResponse(
                success=False,
                error=f"Permission denied: {file_path}",
                tool_name="write"
            )
        except Exception as e:
            logger.error(f"Write error: {e}")
            return ToolResponse(
                success=False,
                error=str(e),
                tool_name="write"
            )
    
    async def edit_file(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        create_backup: bool = True
    ) -> ToolResponse:
        """
        Edit file by replacing old_string with new_string.
        
        Args:
            file_path: Path to file
            old_string: String to replace
            new_string: Replacement string
            create_backup: Create .bak backup before edit
            
        Returns:
            ToolResponse with diff and result
        """
        try:
            path = self._resolve_path(file_path)
            
            if not path.exists():
                return ToolResponse(
                    success=False,
                    error=f"File not found: {file_path}",
                    tool_name="edit"
                )
            
            original_content = path.read_text(encoding='utf-8')
            
            if old_string not in original_content:
                return ToolResponse(
                    success=False,
                    error=f"old_string not found in file. Check for exact match including whitespace.",
                    tool_name="edit",
                    metadata={
                        "old_string_length": len(old_string),
                        "file_content_length": len(original_content)
                    }
                )
            
            if create_backup:
                backup_path = path.with_suffix(path.suffix + '.bak')
                backup_path.write_text(original_content, encoding='utf-8')
            
            new_content = original_content.replace(old_string, new_string, 1)
            
            diff = list(difflib.unified_diff(
                original_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=str(path),
                tofile=str(path),
                lineterm=''
            ))
            
            path.write_text(new_content, encoding='utf-8')
            
            return ToolResponse(
                success=True,
                data={
                    "path": str(path),
                    "diff": ''.join(diff),
                    "backup_created": str(path.with_suffix('.bak')) if create_backup else None
                },
                tool_name="edit",
                metadata={
                    "file_path": str(path),
                    "bytes_changed": len(new_content) - len(original_content)
                }
            )
            
        except PermissionError:
            return ToolResponse(
                success=False,
                error=f"Permission denied: {file_path}",
                tool_name="edit"
            )
        except Exception as e:
            logger.error(f"Edit error: {e}")
            return ToolResponse(
                success=False,
                error=str(e),
                tool_name="edit"
            )
    
    async def glob(
        self,
        pattern: str,
        base_path: Optional[str] = None,
        recursive: bool = True
    ) -> ToolResponse:
        """
        Find files matching glob pattern.
        
        Args:
            pattern: Glob pattern (e.g., "**/*.py", "src/*.ts")
            base_path: Base directory to search (defaults to workdir)
            recursive: Search recursively
            
        Returns:
            ToolResponse with list of matching files
        """
        try:
            base = self._resolve_path(base_path) if base_path else Path(self.workdir)
            
            if recursive and '**' not in pattern:
                pattern = '**/' + pattern
            
            matches = list(base.glob(pattern))[:MAX_SEARCH_RESULTS]
            
            return ToolResponse(
                success=True,
                data=[str(m) for m in matches],
                tool_name="glob",
                metadata={
                    "pattern": pattern,
                    "base_path": str(base),
                    "matches_count": len(matches),
                    "truncated": len(matches) >= MAX_SEARCH_RESULTS
                }
            )
            
        except Exception as e:
            logger.error(f"Glob error: {e}")
            return ToolResponse(
                success=False,
                error=str(e),
                tool_name="glob"
            )
    
    async def grep(
        self,
        pattern: str,
        path: Optional[str] = None,
        file_pattern: str = "*",
        case_sensitive: bool = True,
        context_lines: int = 0
    ) -> ToolResponse:
        """
        Search for pattern in files.
        
        Args:
            pattern: Regex or string pattern to search
            path: Directory to search (defaults to workdir)
            file_pattern: File glob pattern (e.g., "*.py", "*.{ts,tsx}")
            case_sensitive: Case-sensitive search
            context_lines: Lines of context before/after match
            
        Returns:
            ToolResponse with search results
        """
        try:
            search_path = self._resolve_path(path) if path else Path(self.workdir)
            
            if not search_path.exists():
                return ToolResponse(
                    success=False,
                    error=f"Path not found: {path or self.workdir}",
                    tool_name="grep"
                )
            
            flags = 0 if case_sensitive else re.IGNORECASE
            compiled_pattern = re.compile(pattern, flags)
            
            results = []
            file_patterns = file_pattern.replace(',', ' ').split()
            
            for fp in file_patterns:
                for file_path in search_path.rglob(fp):
                    if not file_path.is_file():
                        continue
                    
                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        lines = content.split('\n')
                        
                        for i, line in enumerate(lines, 1):
                            if compiled_pattern.search(line):
                                match_data = {
                                    "file": str(file_path),
                                    "line": i,
                                    "content": line.strip(),
                                    "column": line.find(compiled_pattern.search(line).group())
                                }
                                
                                if context_lines > 0:
                                    start = max(0, i - context_lines - 1)
                                    end = min(len(lines), i + context_lines)
                                    match_data["context"] = [
                                        f"{j}: {lines[j]}" 
                                        for j in range(start, end)
                                    ]
                                
                                results.append(match_data)
                                
                                if len(results) >= MAX_SEARCH_RESULTS:
                                    return ToolResponse(
                                        success=True,
                                        data=results,
                                        tool_name="grep",
                                        metadata={
                                            "pattern": pattern,
                                            "path": str(search_path),
                                            "files_searched": "multiple",
                                            "truncated": True,
                                            "total_matches": len(results)
                                        }
                                    )
                                
                    except Exception:
                        continue
            
            return ToolResponse(
                success=True,
                data=results,
                tool_name="grep",
                metadata={
                    "pattern": pattern,
                    "path": str(search_path),
                    "matches_count": len(results),
                    "truncated": len(results) >= MAX_SEARCH_RESULTS
                }
            )
            
        except re.error as e:
            return ToolResponse(
                success=False,
                error=f"Invalid regex: {e}",
                tool_name="grep"
            )
        except Exception as e:
            logger.error(f"Grep error: {e}")
            return ToolResponse(
                success=False,
                error=str(e),
                tool_name="grep"
            )
    
    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> ToolResponse:
        """Execute a tool by name with arguments."""
        tool_map = {
            "read": self.read_file,
            "write": self.write_file,
            "edit": self.edit_file,
            "glob": self.glob,
            "grep": self.grep
        }
        
        if tool_name not in tool_map:
            return ToolResponse(
                success=False,
                error=f"Unknown tool: {tool_name}",
                tool_name=tool_name
            )
        
        return await tool_map[tool_name](**arguments)
    
    def _resolve_path(self, file_path: str) -> Path:
        """Resolve a path relative to workdir or as absolute."""
        path = Path(file_path)
        if path.is_absolute():
            return path
        return Path(self.workdir) / path


async def test_streaming_tools():
    """Test streaming tools."""
    tools = StreamingTools(workdir="/home/mark/.roxy")
    
    print("Test 1: Read file")
    result = await tools.read_file("tool_executor.py", limit=20)
    print(f"  Success: {result.success}")
    print(f"  Lines: {result.metadata.get('lines_read')}")
    
    print("\nTest 2: Write file")
    result = await tools.write_file(
        "/tmp/roxy_test.txt",
        "Hello from ROXY streaming tools!"
    )
    print(f"  Success: {result.success}")
    print(f"  Data: {result.data}")
    
    print("\nTest 3: Edit file")
    result = await tools.edit_file(
        "/tmp/roxy_test.txt",
        "Hello",
        "Hello World!"
    )
    print(f"  Success: {result.success}")
    print(f"  Diff: {result.data.get('diff')[:100] if result.data else 'N/A'}")
    
    print("\nTest 4: Glob")
    result = await tools.glob("*.py", base_path="/home/mark/.roxy", recursive=False)
    print(f"  Success: {result.success}")
    print(f"  Matches: {len(result.data) if result.data else 0} files")
    
    print("\nTest 5: Grep")
    result = await tools.grep(
        "ToolExecutor",
        path="/home/mark/.roxy",
        file_pattern="tool_executor.py"
    )
    print(f"  Success: {result.success}")
    print(f"  Matches: {len(result.data) if result.data else 0}")


if __name__ == "__main__":
    asyncio.run(test_streaming_tools())
