#!/usr/bin/env python3
"""
ROXY Self-Correction and Validation Loop
Industry Standard: Self-consistency, chain-of-thought verification
Reduces hallucinations, improves accuracy
"""
import logging
from typing import Dict, Any, Optional, List
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.validation')

class ValidationLoop:
    """Self-correction and validation for ROXY responses"""
    
    def __init__(self):
        self.llm_service = None
        self._init_llm()
    
    def _init_llm(self):
        """Initialize LLM service"""
        try:
            from llm_wrapper import get_llm_service_safe
            self.llm_service = get_llm_service_safe()
        except Exception as e:
            logger.warning(f"LLM service unavailable: {e}")
    
    async def validate_response(self, user_input: str, response: str, 
                               context: Dict = None) -> Dict[str, Any]:
        """Validate response for accuracy and truthfulness"""
        validation_result = {
            'valid': True,
            'confidence': 1.0,
            'issues': [],
            'corrected_response': None
        }
        
        # 1. Fact-check against filesystem
        filesystem_check = await self._check_filesystem_facts(response)
        if not filesystem_check['valid']:
            validation_result['valid'] = False
            validation_result['issues'].extend(filesystem_check['issues'])
            validation_result['confidence'] *= 0.5
        
        # 2. Self-consistency check
        consistency_check = await self._check_consistency(response)
        if not consistency_check['valid']:
            validation_result['valid'] = False
            validation_result['issues'].extend(consistency_check['issues'])
            validation_result['confidence'] *= 0.7
        
        # 3. Source verification
        source_check = await self._verify_sources(response, context)
        if not source_check['valid']:
            validation_result['issues'].extend(source_check['issues'])
            validation_result['confidence'] *= 0.8
        
        # 4. If invalid, attempt correction
        if not validation_result['valid'] and self.llm_service:
            corrected = await self._correct_response(user_input, response, validation_result['issues'])
            if corrected:
                validation_result['corrected_response'] = corrected
                validation_result['valid'] = True
                validation_result['confidence'] = 0.8  # Lower confidence for corrected responses
        
        return validation_result
    
    async def _check_filesystem_facts(self, response: str) -> Dict:
        """Check if response mentions files/paths that actually exist"""
        issues = []
        
        # Extract file paths from response
        import re
        file_paths = re.findall(r'["\']([^"\']+\.(?:py|ts|tsx|js|jsx|md|json|yaml|yml))["\']', response)
        file_paths.extend(re.findall(r'/(?:opt|home|usr)/[^\s\)]+', response))
        
        for path in file_paths:
            # Check if absolute path
            if path.startswith('/'):
                if not os.path.exists(path):
                    issues.append(f"Response mentions non-existent file: {path}")
            else:
                # Check common locations
                common_paths = [
                    f"/home/mark/.roxy/{path}",
                    f"/home/mark/mindsong-juke-hub/{path}",
                    f"/home/mark/mindsong-juke-hub/mindsong-juke-hub/{path}"
                ]
                if not any(os.path.exists(p) for p in common_paths):
                    issues.append(f"Response mentions file that may not exist: {path}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }
    
    async def _check_consistency(self, response: str) -> Dict:
        """Check response for internal consistency"""
        issues = []
        
        # Check for contradictory statements
        contradictions = [
            ('does not exist', 'exists'),
            ('is not', 'is'),
            ('cannot', 'can'),
        ]
        
        response_lower = response.lower()
        for neg, pos in contradictions:
            if neg in response_lower and pos in response_lower:
                # Check if they refer to the same thing (simple heuristic)
                issues.append(f"Possible contradiction detected: mentions both '{neg}' and '{pos}'")
        
        # Check for vague statements
        vague_phrases = ['might be', 'could be', 'possibly', 'maybe', 'perhaps']
        vague_count = sum(1 for phrase in vague_phrases if phrase in response_lower)
        if vague_count > 3:
            issues.append(f"Response contains {vague_count} vague statements")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }
    
    async def _verify_sources(self, response: str, context: Dict = None) -> Dict:
        """Verify that response sources are valid"""
        issues = []
        
        # Check if response claims to use tools/files but doesn't indicate source
        if 'list' in response.lower() or 'file' in response.lower():
            if 'source:' not in response.lower() and '📌' not in response:
                issues.append("Response mentions files but lacks source attribution")
        
        # Check if response claims RAG but context not provided
        if 'rag' in response.lower() or 'retrieval' in response.lower():
            if not context or 'repo' not in str(context):
                issues.append("Response claims RAG but no repository context provided")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }
    
    async def _correct_response(self, user_input: str, original_response: str, 
                               issues: List[str]) -> Optional[str]:
        """Attempt to correct response based on validation issues"""
        if not self.llm_service or not self.llm_service.is_available():
            return None
        
        prompt = f"""You are ROXY, an AI assistant. Your previous response had validation issues.

Original User Query: {user_input}

Your Previous Response:
{original_response}

Validation Issues Found:
{chr(10).join(f'- {issue}' for issue in issues)}

Please provide a corrected response that:
1. Fixes all validation issues
2. Only mentions files/paths that actually exist
3. Is internally consistent
4. Includes proper source attribution
5. Is truthful and accurate

Corrected Response:"""

        try:
            corrected = await self.llm_service.generate_response(
                user_input=prompt,
                context={'mode': 'correction'},
                history=[],
                facts=[]
            )
            return corrected
        except Exception as e:
            logger.error(f"Response correction error: {e}")
            return None

