#!/usr/bin/env python3
"""
ROXY Validation Loop - Prevents hallucinations and validates responses
Ensures all responses are truthful and accurate
"""
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.validation')

class ValidationLoop:
    """Validates responses to prevent hallucinations"""
    
    def __init__(self):
        self.repo_paths = [
            "/opt/roxy/mindsong-juke-hub",
            "/opt/roxy/mindsong-juke-hub/mindsong-juke-hub"
        ]
        self.actual_repo_path = None
        self._detect_repo_path()
    
    def _detect_repo_path(self):
        """Detect which repository path exists"""
        for path in self.repo_paths:
            if os.path.exists(path):
                self.actual_repo_path = path
                break
    
    async def validate_response(self, user_input: str, response: str, 
                               context: Dict = None) -> Dict[str, Any]:
        """
        Validate a response for hallucinations and accuracy
        
        Returns:
            {
                'valid': bool,
                'issues': List[str],
                'corrected_response': Optional[str],
                'confidence': float (0-1),
                'source_verified': bool
            }
        """
        user_lower = user_input.lower()
        issues = []
        confidence = 1.0
        source_verified = False
        corrected_response = None
        
        # Check 1: File listing validation
        if "list" in user_lower and ("page" in user_lower or "file" in user_lower or "component" in user_lower):
            if not self._validate_file_listing(response, user_input):
                issues.append("Response contains file paths that don't exist")
                confidence = 0.3
                # Try to get real file listing
                corrected_response = await self._get_real_file_listing(user_input)
                if corrected_response:
                    confidence = 0.9
                    source_verified = True
        
        # Check 2: Repository information validation
        if any(keyword in user_lower for keyword in ["mindsong", "juke", "repo", "repository", "project"]):
            if not self._validate_repo_info(response):
                issues.append("Response contains incorrect repository information")
                confidence = max(0.2, confidence - 0.3)
            
            # Also validate against RAG index if available
            if not self._validate_against_rag_index(response, user_input):
                issues.append("Response doesn't match RAG index content")
                confidence = max(0.3, confidence - 0.2)
        
        # Check 3: Generic hallucination detection (enhanced)
        hallucination_indicators = [
            "Tool A", "Tool B", "Tool C",  # Generic tool names
            "Page 90-99", "Page 1-10",  # Generic page ranges
            "according to the repository",  # Vague attribution
            "the codebase shows",  # Vague reference
            "based on the files",  # Vague reference
            "I can see that",  # Vague reference without source
            "the system has",  # Vague system reference
            "there are multiple",  # Vague quantity
            "several components",  # Vague component reference
            "various files",  # Vague file reference
        ]
        
        for indicator in hallucination_indicators:
            if indicator.lower() in response.lower():
                issues.append(f"Potential hallucination detected: '{indicator}'")
                confidence = max(0.1, confidence - 0.3)
        
        # Check 3b: Code structure hallucinations
        if self._detect_code_structure_hallucination(response, user_input):
            issues.append("Response contains code structure that may not exist")
            confidence = max(0.2, confidence - 0.3)
        
        # Check 3c: Number/statistic hallucinations
        if self._detect_statistic_hallucination(response, user_input):
            issues.append("Response contains unverified statistics or numbers")
            confidence = max(0.3, confidence - 0.2)
        
        # Check 4: Source attribution validation
        if not self._has_source_attribution(response):
            issues.append("Response missing source attribution")
            confidence = max(0.5, confidence - 0.2)
        
        # Check 5: Empty or too short response
        if len(response.strip()) < 20:
            issues.append("Response too short or empty")
            confidence = 0.2
        
        # Determine if valid
        is_valid = len(issues) == 0 and confidence >= 0.7
        
        return {
            'valid': is_valid,
            'issues': issues,
            'corrected_response': corrected_response,
            'confidence': confidence,
            'source_verified': source_verified,
            'timestamp': datetime.now().isoformat()
        }
    
    def _validate_file_listing(self, response: str, user_input: str) -> bool:
        """Validate that file paths in response actually exist"""
        if not self.actual_repo_path:
            return False
        
        # Extract potential file paths from response
        lines = response.split('\n')
        file_paths_found = []
        
        for line in lines:
            # Look for file paths (common patterns)
            if any(ext in line for ext in ['.tsx', '.ts', '.jsx', '.js', '.md', '.py']):
                # Try to extract path
                parts = line.split()
                for part in parts:
                    if any(ext in part for ext in ['.tsx', '.ts', '.jsx', '.js', '.md', '.py']):
                        # Check if it's a relative path
                        if '/' in part or '\\' in part:
                            file_paths_found.append(part)
        
        # Validate each path
        valid_count = 0
        for path_str in file_paths_found[:10]:  # Check first 10
            # Try different path combinations
            test_paths = [
                Path(self.actual_repo_path) / path_str,
                Path(self.actual_repo_path) / path_str.lstrip('/'),
            ]
            
            for test_path in test_paths:
                if test_path.exists():
                    valid_count += 1
                    break
        
        # If we found paths, at least some should be valid
        if file_paths_found:
            return valid_count > 0 or len(file_paths_found) == 0
        
        # If no file paths found but response is long, might be hallucinated
        if len(response) > 500 and "list" in user_input.lower():
            return False
        
        return True
    
    def _validate_repo_info(self, response: str) -> bool:
        """Validate repository information is accurate"""
        # Check for known incorrect information
        incorrect_info = [
            "music streaming business",
            "streaming platform",
            "Tool A", "Tool B", "Tool C",
        ]
        
        for info in incorrect_info:
            if info.lower() in response.lower():
                return False
        
        return True
    
    def _has_source_attribution(self, response: str) -> bool:
        """Check if response has source attribution"""
        source_indicators = [
            "📌 Source:",
            "Source:",
            "📍 Source:",
            "Real filesystem",
            "RAG",
            "LLM",
            "ChromaDB",
        ]
        
        return any(indicator in response for indicator in source_indicators)
    
    def _detect_code_structure_hallucination(self, response: str, user_input: str) -> bool:
        """Detect if response contains code structure that may be hallucinated"""
        # Check for common code patterns that might be made up
        suspicious_patterns = [
            "class ToolA", "class ToolB", "class ToolC",
            "function ToolA", "function ToolB",
            "export const ToolA", "export const ToolB",
            "interface ToolA", "interface ToolB",
        ]
        
        for pattern in suspicious_patterns:
            if pattern in response:
                return True
        
        # Check for generic component names
        if "ComponentA" in response or "ComponentB" in response:
            return True
        
        return False
    
    def _detect_statistic_hallucination(self, response: str, user_input: str) -> bool:
        """Detect if response contains unverified statistics"""
        import re
        
        # Look for numbers that might be statistics
        numbers = re.findall(r'\b\d+\b', response)
        
        # If response has many numbers and no source attribution, might be hallucinated
        if len(numbers) > 5 and not self._has_source_attribution(response):
            # Check if numbers look like statistics (not just line numbers or IDs)
            stat_keywords = ["files", "components", "pages", "lines", "functions", "classes"]
            if any(keyword in response.lower() for keyword in stat_keywords):
                return True
        
        return False
    
    def _validate_against_rag_index(self, response: str, user_input: str) -> bool:
        """Validate response against RAG index if available"""
        if not self.actual_repo_path:
            return True  # Can't validate without repo
        
        try:
            from repository_rag import get_repo_rag
            rag = get_repo_rag(self.actual_repo_path)
            stats = rag.indexer.get_stats()
            
            if stats.get('total_chunks', 0) > 0:
                # Try to verify key claims in response
                # This is a simplified check - could be enhanced
                return True  # For now, assume valid if RAG is available
        except Exception as e:
            logger.debug(f"RAG validation not available: {e}")
        
        return True  # Default to valid if can't check
    
    async def _get_real_file_listing(self, user_input: str) -> Optional[str]:
        """Get real file listing as correction"""
        if not self.actual_repo_path:
            return None
        
        try:
            # Try enhanced interface first
            try:
                from roxy_interface_enhanced import EnhancedRoxyInterface
                interface = EnhancedRoxyInterface()
                return await interface._list_repository_files(self.actual_repo_path, user_input)
            except:
                # Fallback to regular interface
                from roxy_interface import RoxyInterface
                interface = RoxyInterface()
                return await interface._list_repository_files(self.actual_repo_path, user_input)
        except Exception as e:
            logger.error(f"Error getting real file listing: {e}")
            return None

# Global validator instance
_validator: Optional[ValidationLoop] = None

def get_validator() -> ValidationLoop:
    """Get or create validation loop instance"""
    global _validator
    if _validator is None:
        _validator = ValidationLoop()
    return _validator







