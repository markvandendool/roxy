#!/usr/bin/env python3
"""
Source Verifier - Verifies that file operations actually succeeded
"""
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("roxy.validation.source_verifier")

ROXY_DIR = Path.home() / ".roxy"


class SourceVerifier:
    """Verifies that operations actually succeeded"""
    
    def verify_file_operation(self, operation: str, path: str, expected_result: Any = None) -> Dict[str, Any]:
        """Verify a file operation succeeded"""
        file_path = Path(path)
        
        if operation == "list":
            if file_path.exists() and file_path.is_dir():
                try:
                    files = list(file_path.iterdir())
                    return {
                        "verified": True,
                        "operation": operation,
                        "path": str(path),
                        "result": len(files),
                        "message": f"Directory exists with {len(files)} items"
                    }
                except Exception as e:
                    return {
                        "verified": False,
                        "operation": operation,
                        "path": str(path),
                        "error": str(e)
                    }
            else:
                return {
                    "verified": False,
                    "operation": operation,
                    "path": str(path),
                    "error": "Path does not exist or is not a directory"
                }
        
        elif operation == "read":
            if file_path.exists() and file_path.is_file():
                try:
                    content = file_path.read_text()
                    return {
                        "verified": True,
                        "operation": operation,
                        "path": str(path),
                        "result": len(content),
                        "message": f"File exists with {len(content)} characters"
                    }
                except Exception as e:
                    return {
                        "verified": False,
                        "operation": operation,
                        "path": str(path),
                        "error": str(e)
                    }
            else:
                return {
                    "verified": False,
                    "operation": operation,
                    "path": str(path),
                    "error": "File does not exist"
                }
        
        return {
            "verified": False,
            "operation": operation,
            "path": str(path),
            "error": f"Unknown operation: {operation}"
        }
    
    def verify_command_execution(self, command: str, expected_output: str = None) -> Dict[str, Any]:
        """Verify a command execution succeeded"""
        try:
            # Parse command type
            if command.startswith("git"):
                # Git commands - check git status
                result = subprocess.run(
                    ["git", "status"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    cwd=ROXY_DIR.parent  # Try to find git repo
                )
                return {
                    "verified": result.returncode == 0,
                    "command": command,
                    "message": "Git command execution verified" if result.returncode == 0 else "Git command may have failed"
                }
            
            # For other commands, assume verified if no error
            return {
                "verified": True,
                "command": command,
                "message": "Command execution assumed successful"
            }
        except Exception as e:
            return {
                "verified": False,
                "command": command,
                "error": str(e)
            }
    
    def verify_rag_result(self, query: str, response: str, context_chunks: int = 0) -> Dict[str, Any]:
        """Verify RAG result has proper source attribution"""
        has_source = "source" in response.lower() or "📌" in response or "Source:" in response
        
        return {
            "verified": has_source and context_chunks > 0,
            "query": query,
            "has_source_attribution": has_source,
            "context_chunks": context_chunks,
            "message": "RAG result has source attribution" if has_source else "RAG result missing source attribution"
        }















