#!/usr/bin/env python3
"""
ROXY Email Summarizer - AI-powered email summaries
"""
import logging
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.email.summarizer')

class EmailSummarizer:
    """Generate email summaries"""
    
    def __init__(self):
        self.llm_service = None
        self._init_llm()
    
    def _init_llm(self):
        """Initialize LLM for summarization"""
        try:
            from llm_service import get_llm_service
            self.llm_service = get_llm_service()
        except Exception as e:
            logger.warning(f"LLM service unavailable: {e}")
    
    async def summarize(self, email: Dict, max_length: int = 200) -> str:
        """Generate email summary"""
        if self.llm_service and self.llm_service.is_available():
            prompt = f"Summarize this email in {max_length} characters or less:\n\nSubject: {email.get('subject', '')}\n\nBody: {email.get('body', '')[:1000]}"
            try:
                summary = await self.llm_service.generate_response(prompt)
                return summary[:max_length]
            except Exception as e:
                logger.error(f"LLM summarization failed: {e}")
        
        # Fallback: simple extraction
        body = email.get('body', '')
        if len(body) > max_length:
            return body[:max_length] + "..."
        return body
    
    def extract_key_points(self, email: Dict) -> List[str]:
        """Extract key points from email"""
        body = email.get('body', '')
        # Simple extraction - would use NLP in production
        sentences = body.split('.')
        key_points = [s.strip() for s in sentences[:5] if len(s.strip()) > 20]
        return key_points










