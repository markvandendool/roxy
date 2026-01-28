#!/usr/bin/env python3
"""
Error Recovery - Retry logic with exponential backoff
"""
import logging
import time
import random
from typing import Callable, Any, Optional, Dict
from functools import wraps

logger = logging.getLogger("roxy.error_recovery")


def retry_with_backoff(max_retries: int = 3, 
                      initial_delay: float = 1.0,
                      max_delay: float = 60.0,
                      exponential_base: float = 2.0,
                      jitter: bool = True):
    """Decorator for retry with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        # Add jitter
                        actual_delay = delay
                        if jitter:
                            actual_delay = delay * (0.5 + random.random())
                        
                        logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {actual_delay:.2f}s...")
                        time.sleep(actual_delay)
                        
                        # Exponential backoff
                        delay = min(delay * exponential_base, max_delay)
                    else:
                        logger.error(f"All {max_retries} attempts failed")
            
            raise last_exception
        return wrapper
    return decorator


class ErrorClassifier:
    """Classifies errors as transient or permanent"""
    
    TRANSIENT_ERRORS = [
        "timeout",
        "connection",
        "network",
        "temporary",
        "rate limit",
        "503",
        "502",
        "504"
    ]
    
    PERMANENT_ERRORS = [
        "not found",
        "404",
        "401",
        "403",
        "syntax error",
        "invalid"
    ]
    
    @classmethod
    def classify_error(cls, error: Exception) -> str:
        """Classify error as transient or permanent"""
        error_str = str(error).lower()
        
        for transient in cls.TRANSIENT_ERRORS:
            if transient in error_str:
                return "transient"
        
        for permanent in cls.PERMANENT_ERRORS:
            if permanent in error_str:
                return "permanent"
        
        # Default to transient (can retry)
        return "transient"
    
    @classmethod
    def should_retry(cls, error: Exception) -> bool:
        """Determine if error should be retried"""
        return cls.classify_error(error) == "transient"


class ErrorRecovery:
    """Error recovery with automatic fallback"""
    
    def __init__(self):
        self.error_history: Dict[str, int] = {}
    
    def execute_with_fallback(self, 
                            primary_func: Callable,
                            fallback_func: Callable = None,
                            *args, **kwargs) -> Any:
        """Execute function with fallback"""
        try:
            return primary_func(*args, **kwargs)
        except Exception as e:
            error_type = ErrorClassifier.classify_error(e)
            logger.warning(f"Primary function failed ({error_type}): {e}")
            
            if error_type == "transient" and fallback_func:
                try:
                    logger.info("Attempting fallback function...")
                    return fallback_func(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")
                    raise fallback_error
            
            raise e
    
    def record_error(self, error_type: str):
        """Record error for learning"""
        self.error_history[error_type] = self.error_history.get(error_type, 0) + 1
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics"""
        return self.error_history.copy()


# Global error recovery
_error_recovery = None


def get_error_recovery() -> ErrorRecovery:
    """Get global error recovery instance"""
    global _error_recovery
    if _error_recovery is None:
        _error_recovery = ErrorRecovery()
    return _error_recovery
















