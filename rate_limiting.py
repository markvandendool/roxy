#!/usr/bin/env python3
"""
Rate Limiting - Token bucket and circuit breakers
"""
import logging
import time
import threading
from typing import Dict, Any, Optional, Callable, TypeVar
from collections import defaultdict

logger = logging.getLogger("roxy.rate_limiting")


class TokenBucket:
    """Token bucket rate limiter"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens, returns True if successful"""
        with self.lock:
            now = time.time()
            # Refill tokens
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


class CircuitBreaker:
    """Circuit breaker for external services"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
        self.lock = threading.Lock()
    
    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Call function with circuit breaker protection"""
        with self.lock:
            if self.state == "open":
                # Check if timeout has passed
                if self.last_failure_time and time.time() - self.last_failure_time > self.timeout:
                    self.state = "half_open"
                    logger.info("Circuit breaker: moving to half-open state")
                else:
                    raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            # Success
            with self.lock:
                if self.state == "half_open":
                    self.state = "closed"
                    self.failures = 0
                    logger.info("Circuit breaker: moving to closed state")
            return result
        except Exception as e:
            # Failure
            with self.lock:
                self.failures += 1
                self.last_failure_time = time.time()
                if self.failures >= self.failure_threshold:
                    self.state = "open"
                    logger.warning(f"Circuit breaker: OPEN after {self.failures} failures")
            raise


class RateLimiter:
    """Rate limiter with per-IP and per-endpoint limits"""
    
    def __init__(self):
        # Per-IP rate limiters (10 requests per second, burst of 20)
        self.ip_limiters: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(capacity=20, refill_rate=10.0)
        )
        
        # Per-endpoint rate limiters
        self.endpoint_limiters: Dict[str, TokenBucket] = {
            "/run": TokenBucket(capacity=30, refill_rate=15.0),
            "/health": TokenBucket(capacity=100, refill_rate=50.0),
        }
        
        # Circuit breaker for Ollama
        self.ollama_circuit = CircuitBreaker(failure_threshold=5, timeout=60)
    
    def check_rate_limit(self, ip: str, endpoint: str = "/run") -> bool:
        """Check if request is within rate limit"""
        # Check IP limit
        if not self.ip_limiters[ip].consume():
            logger.warning(f"Rate limit exceeded for IP: {ip}")
            return False
        
        # Check endpoint limit
        if endpoint in self.endpoint_limiters:
            if not self.endpoint_limiters[endpoint].consume():
                logger.warning(f"Rate limit exceeded for endpoint: {endpoint}")
                return False
        
        return True
    
    def get_ollama_circuit(self) -> CircuitBreaker:
        """Get circuit breaker for Ollama"""
        return self.ollama_circuit


# Global rate limiter
_rate_limiter = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter









