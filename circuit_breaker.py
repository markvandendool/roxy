"""
Circuit Breaker pattern implementation
Prevents cascading failures by stopping calls to failing services
"""
import time
import logging
from enum import Enum
from typing import Callable, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger("roxy.circuit_breaker")


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking calls due to failures
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures
    
    States:
    - CLOSED: Normal operation, calls go through
    - OPEN: Too many failures, all calls blocked
    - HALF_OPEN: After timeout, try one call to test recovery
    
    Example:
        breaker = CircuitBreaker(failure_threshold=5, timeout=60.0)
        result = breaker.call(some_risky_function, arg1, arg2)
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        success_threshold: int = 2
    ):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting recovery (half-open)
            success_threshold: Consecutive successes needed to close from half-open
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        
        self.failures = 0
        self.successes = 0
        self.last_failure_time: Optional[float] = None
        self.last_attempt_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        
        self.total_calls = 0
        self.failed_calls = 0
        self.blocked_calls = 0
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call a function through the circuit breaker
        
        Args:
            func: Function to call
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Result of function call
            
        Raises:
            Exception: If circuit is OPEN or function fails
        """
        self.total_calls += 1
        self.last_attempt_time = time.time()
        
        # Check if circuit should transition to HALF_OPEN
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                logger.info(
                    f"Circuit breaker {func.__name__} transitioning to HALF_OPEN"
                )
                self.state = CircuitState.HALF_OPEN
                self.successes = 0
            else:
                self.blocked_calls += 1
                raise CircuitBreakerError(
                    f"Circuit breaker is OPEN for {func.__name__}. "
                    f"Retry after {self.timeout - (time.time() - self.last_failure_time):.1f}s"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call"""
        self.failures = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.successes += 1
            if self.successes >= self.success_threshold:
                logger.info("Circuit breaker CLOSED (recovered)")
                self.state = CircuitState.CLOSED
                self.successes = 0
        else:
            self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failed call"""
        self.failures += 1
        self.failed_calls += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                logger.warning(
                    f"Circuit breaker OPENED after {self.failures} failures"
                )
            self.state = CircuitState.OPEN
        
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker HALF_OPEN test failed, returning to OPEN")
            self.state = CircuitState.OPEN
            self.successes = 0
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        return {
            "state": self.state.value,
            "total_calls": self.total_calls,
            "failed_calls": self.failed_calls,
            "blocked_calls": self.blocked_calls,
            "current_failures": self.failures,
            "failure_threshold": self.failure_threshold,
            "last_failure": datetime.fromtimestamp(self.last_failure_time).isoformat() 
                           if self.last_failure_time else None
        }
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state"""
        logger.info("Circuit breaker manually reset to CLOSED")
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        self.last_failure_time = None


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open"""
    pass


# Global circuit breakers for common services
_circuit_breakers = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    timeout: float = 60.0
) -> CircuitBreaker:
    """
    Get or create a named circuit breaker
    
    Args:
        name: Unique name for the circuit breaker
        failure_threshold: Number of failures before opening
        timeout: Seconds before attempting recovery
        
    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            failure_threshold=failure_threshold,
            timeout=timeout
        )
    return _circuit_breakers[name]
