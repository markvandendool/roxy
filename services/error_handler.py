#!/usr/bin/env python3
"""
ROXY Error Handler - Centralized error handling and recovery
Provides graceful degradation and retry mechanisms
"""
import logging
import asyncio
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.error_handler')

class ErrorHandler:
    """Centralized error handling with retry and fallback"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.error_history = []
    
    async def execute_with_retry(self, func: Callable, *args, 
                                fallback: Optional[Callable] = None,
                                error_context: str = "",
                                **kwargs) -> Any:
        """
        Execute function with exponential backoff retry
        
        Args:
            func: Function to execute
            *args: Positional arguments
            fallback: Fallback function if all retries fail
            error_context: Context for error logging
            **kwargs: Keyword arguments
        
        Returns:
            Result of function or fallback
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Success - log if retried
                if attempt > 0:
                    logger.info(f"✅ {error_context} succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_error = e
                self.error_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'context': error_context,
                    'attempt': attempt + 1,
                    'error': str(e)
                })
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"⚠️ {error_context} failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                    logger.info(f"   Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ {error_context} failed after {self.max_retries} attempts: {e}")
        
        # All retries failed - try fallback
        if fallback:
            try:
                logger.info(f"🔄 Trying fallback for {error_context}")
                if asyncio.iscoroutinefunction(fallback):
                    return await fallback(*args, **kwargs)
                else:
                    return fallback(*args, **kwargs)
            except Exception as e:
                logger.error(f"❌ Fallback also failed for {error_context}: {e}")
        
        # Return error response
        return self._error_response(error_context, last_error)
    
    def _error_response(self, context: str, error: Exception) -> str:
        """Generate user-friendly error response"""
        error_msg = str(error)
        
        # Provide helpful error messages
        if "Connection" in error_msg or "timeout" in error_msg.lower():
            return f"I'm having trouble connecting to services. Please check if ChromaDB and Ollama are running. (Error: {context})"
        
        if "not found" in error_msg.lower() or "FileNotFoundError" in error_msg:
            return f"I couldn't find the requested resource. Please check the path or try a different query. (Error: {context})"
        
        if "permission" in error_msg.lower():
            return f"I don't have permission to access that resource. Please check file permissions. (Error: {context})"
        
        # Generic error
        return f"I encountered an error while processing your request: {context}. Please try again or rephrase your question."
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        if not self.error_history:
            return {'total_errors': 0, 'recent_errors': []}
        
        recent = self.error_history[-10:]  # Last 10 errors
        
        return {
            'total_errors': len(self.error_history),
            'recent_errors': recent,
            'last_error': self.error_history[-1] if self.error_history else None
        }

# Global error handler instance
_error_handler: Optional[ErrorHandler] = None

def get_error_handler() -> ErrorHandler:
    """Get or create error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler













