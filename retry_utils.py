"""
Retry utilities with exponential backoff
Provides decorators and utilities for resilient service calls
"""
import time
import functools
import logging
from typing import Callable, Any, Type, Tuple

logger = logging.getLogger("roxy.retry")


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Retry decorator with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch and retry
        
    Example:
        @retry(max_attempts=3, delay=1.0, backoff=2.0)
        def call_api():
            # API call that may fail transiently
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            current_delay = delay
            last_exception = None
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    last_exception = e
                    
                    if attempt >= max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"{func.__name__} attempt {attempt} failed: {e}. "
                        f"Retrying in {current_delay}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator


def retry_with_timeout(
    max_attempts: int = 3,
    delay: float = 1.0,
    timeout: float = 30.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Retry decorator with total timeout
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay between retries (seconds)
        timeout: Total timeout for all attempts (seconds)
        exceptions: Tuple of exception types to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            attempt = 0
            last_exception = None
            
            while attempt < max_attempts:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    logger.error(
                        f"{func.__name__} timed out after {elapsed:.1f}s"
                    )
                    raise TimeoutError(
                        f"Total retry timeout ({timeout}s) exceeded"
                    )
                
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    last_exception = e
                    
                    if attempt >= max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts"
                        )
                        raise
                    
                    # Sleep but respect total timeout
                    remaining = timeout - (time.time() - start_time)
                    sleep_time = min(delay, remaining)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
            
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator
