#!/usr/bin/env python3
"""
ROXY Self-Correction - Automatically detects and corrects incorrect responses
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.self_correction')

MINDSONG_HOME = Path.home() / "mindsong-juke-hub"

class SelfCorrection:
    """Self-correction mechanism for ROXY"""
    
    def __init__(self):
        self.correction_history = []
    
    async def detect_and_correct(self, user_input: str, response: str, 
                                validation_result: Dict[str, Any],
                                context: Dict = None) -> Optional[str]:
        """
        Detect if response needs correction and provide corrected version
        
        Returns:
            Corrected response if needed, None otherwise
        """
        if validation_result.get('valid', True):
            return None  # No correction needed
        
        issues = validation_result.get('issues', [])
        confidence = validation_result.get('confidence', 1.0)
        
        # If confidence is very low, try to correct
        if confidence < 0.5:
            logger.warning(f"🔧 Low confidence response detected ({confidence:.1%}), attempting correction...")
            
            # Try to get corrected response from validation
            corrected = validation_result.get('corrected_response')
            if corrected:
                self._log_correction(user_input, response, corrected, issues)
                return corrected
            
            # Try alternative methods
            corrected = await self._try_alternative_methods(user_input, response, context)
            if corrected:
                self._log_correction(user_input, response, corrected, issues)
                return corrected
        
        return None
    
    async def _try_alternative_methods(self, user_input: str, original_response: str,
                                      context: Dict = None) -> Optional[str]:
        """Try alternative methods to get correct response"""
        user_lower = user_input.lower()
        
        # If it's a file listing request, try file operations
        if "list" in user_lower and ("page" in user_lower or "file" in user_lower):
            try:
                from roxy_interface import RoxyInterface
                interface = RoxyInterface()
                
                repo_paths = [
                    str(MINDSONG_HOME),
                    str(MINDSONG_HOME / "mindsong-juke-hub")
                ]
                
                for repo_path in repo_paths:
                    import os
                    if os.path.exists(repo_path):
                        corrected = await interface._list_repository_files(repo_path, user_input)
                        if corrected and len(corrected) > 50:
                            logger.info("✅ Self-correction successful: Used file operations")
                            return corrected
            except Exception as e:
                logger.error(f"Self-correction via file ops failed: {e}")
        
        # If it's a repository question, try RAG
        if any(keyword in user_lower for keyword in ["mindsong", "juke", "repo", "repository"]):
            try:
                from repository_rag import get_repo_rag
                
                repo_paths = [
                    str(MINDSONG_HOME),
                    str(MINDSONG_HOME / "mindsong-juke-hub")
                ]
                
                for repo_path in repo_paths:
                    import os
                    if os.path.exists(repo_path):
                        rag = get_repo_rag(repo_path)
                        stats = rag.indexer.get_stats()
                        if stats.get('total_chunks', 0) > 0:
                            corrected = await rag.answer_question(user_input, context_limit=15)
                            if corrected and len(corrected) > 50:
                                logger.info("✅ Self-correction successful: Used RAG")
                                return corrected
            except Exception as e:
                logger.error(f"Self-correction via RAG failed: {e}")
        
        return None
    
    def _log_correction(self, user_input: str, original: str, corrected: str, issues: list):
        """Log correction for learning"""
        self.correction_history.append({
            'timestamp': datetime.now().isoformat(),
            'user_input': user_input,
            'original_response': original[:200],  # Truncate for storage
            'corrected_response': corrected[:200],
            'issues': issues
        })
        
        logger.info(f"📝 Correction logged: {len(issues)} issues fixed")
    
    def get_correction_stats(self) -> Dict[str, Any]:
        """Get correction statistics"""
        return {
            'total_corrections': len(self.correction_history),
            'recent_corrections': self.correction_history[-10:] if self.correction_history else []
        }

# Global self-correction instance
_self_correction: Optional[SelfCorrection] = None

def get_self_correction() -> SelfCorrection:
    """Get or create self-correction instance"""
    global _self_correction
    if _self_correction is None:
        _self_correction = SelfCorrection()
    return _self_correction












