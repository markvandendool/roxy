#!/usr/bin/env python3
"""
Fact Checker - Validates responses against filesystem and knowledge base
"""
import logging
import re
from pathlib import Path
import os
from typing import Dict, Any, List, Optional

logger = logging.getLogger("roxy.validation.fact_checker")

ROXY_DIR = Path.home() / ".roxy"


class FactChecker:
    """Checks facts against filesystem and knowledge base"""
    
    def __init__(self):
        self.chroma_client = None
        self._init_chroma()
    
    def _init_chroma(self):
        """Initialize ChromaDB client for fact checking"""
        try:
            import chromadb
            chroma_path = ROXY_DIR / "chroma_db"
            if chroma_path.exists():
                self.chroma_client = chromadb.PersistentClient(path=str(chroma_path))
        except Exception as e:
            logger.debug(f"ChromaDB not available for fact checking: {e}")
    
    def check_file_claims(self, response: str, repo_path: Path = None) -> Dict[str, Any]:
        """Check if response mentions files that actually exist
        CHIEF FIX: Don't warn if response explicitly says 'no files found'
        """
        if not repo_path:
            # Default to mindsong repo
            roxy_root = Path(os.environ.get('ROXY_ROOT', str(Path.home() / '.roxy')))
            repo_path = Path(os.environ.get('ROXY_MINDSONG_PATH', str(roxy_root / 'mindsong-juke-hub')))
        
        if not repo_path.exists():
            return {"valid": True, "reason": "Repo path not available for checking"}
        
        # CHIEF FIX: If response says "no matches/files found", suppress file warnings
        explicit_no_match = any(phrase in response.lower() for phrase in [
            "no files found", "no matching files", "no matches found",
            "cannot answer questions about non-existent files",
            "did not find any file"
        ])
        
        if explicit_no_match:
            return {
                "valid": True,
                "verified_files": [],
                "invalid_files": [],
                "total_mentioned": 0,
                "reason": "Response explicitly reports no files found (expected behavior)"
            }
        
        # Extract file mentions from response
        file_patterns = [
            r'`([^`]+\.(py|js|ts|tsx|jsx|md|json|yaml|yml))`',  # Code blocks
            r'([a-zA-Z0-9_/]+\.(py|js|ts|ts|jsx|tsx|md|json|yaml|yml))',  # File names
            r'file[:\s]+([a-zA-Z0-9_/]+\.(py|js|ts|md|json))',  # "file: name.ext"
        ]
        
        mentioned_files = set()
        for pattern in file_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    file_name = match[0]
                else:
                    file_name = match
                mentioned_files.add(file_name)
        
        # Check if files exist
        verified_files = []
        invalid_files = []
        
        for file_name in mentioned_files:
            # Try different path combinations
            possible_paths = [
                repo_path / file_name,
                repo_path / "src" / file_name,
                repo_path / file_name.lstrip("/"),
            ]
            
            found = False
            for path in possible_paths:
                if path.exists() and path.is_file():
                    verified_files.append(str(path.relative_to(repo_path)))
                    found = True
                    break
            
            if not found:
                invalid_files.append(file_name)
        
        result = {
            "valid": len(invalid_files) == 0,
            "verified_files": verified_files,
            "invalid_files": invalid_files,
            "total_mentioned": len(mentioned_files)
        }
        
        if invalid_files:
            result["reason"] = f"Response mentions {len(invalid_files)} non-existent files: {', '.join(invalid_files[:3])}"
        else:
            result["reason"] = "All file mentions verified"
        
        return result
    
    def check_code_claims(self, response: str, repo_path: Path = None) -> Dict[str, Any]:
        """Check if response mentions code patterns that exist"""
        if not repo_path:
            roxy_root = Path(os.environ.get('ROXY_ROOT', str(Path.home() / '.roxy')))
            repo_path = Path(os.environ.get('ROXY_MINDSONG_PATH', str(roxy_root / 'mindsong-juke-hub')))
        
        if not repo_path.exists():
            return {"valid": True, "reason": "Repo path not available for checking"}
        
        # Extract function/class mentions
        code_patterns = [
            r'function\s+([a-zA-Z0-9_]+)',
            r'class\s+([a-zA-Z0-9_]+)',
            r'def\s+([a-zA-Z0-9_]+)',
            r'const\s+([a-zA-Z0-9_]+)\s*=',
        ]
        
        mentioned_code = set()
        for pattern in code_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            mentioned_code.update(matches)
        
        # For now, just return that we checked
        # Future: Actually search codebase for these patterns
        return {
            "valid": True,
            "mentioned_code": list(mentioned_code),
            "reason": "Code pattern checking not yet implemented"
        }
    
    def validate_response(self, response: str, query: str = None, repo_path: Path = None) -> Dict[str, Any]:
        """Comprehensive validation of response"""
        results = {
            "file_check": self.check_file_claims(response, repo_path),
            "code_check": self.check_code_claims(response, repo_path),
            "confidence": 1.0,
            "warnings": []
        }
        
        # Calculate confidence
        if not results["file_check"]["valid"]:
            results["confidence"] *= 0.5
            results["warnings"].append(results["file_check"]["reason"])
        
        if not results["code_check"]["valid"]:
            results["confidence"] *= 0.7
            results["warnings"].append(results["code_check"]["reason"])
        
        # Check for hallucination indicators
        hallucination_phrases = [
            "I don't have access to",
            "I cannot verify",
            "based on my training",
            "I'm not sure",
            "I don't know",
        ]
        
        has_uncertainty = any(phrase.lower() in response.lower() for phrase in hallucination_phrases)
        if has_uncertainty:
            results["confidence"] *= 0.8
            results["warnings"].append("Response contains uncertainty indicators")
        
        results["overall_valid"] = results["confidence"] >= 0.7
        
        return results
















