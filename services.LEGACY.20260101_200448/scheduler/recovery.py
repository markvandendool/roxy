#!/usr/bin/env python3
"""
ROXY Task Failure Recovery - Automatic retry and recovery
"""
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.scheduler.recovery')

class RetryStrategy(Enum):
    IMMEDIATE = "immediate"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_INTERVAL = "fixed_interval"
    NO_RETRY = "no_retry"

class TaskRecovery:
    """Handle task failure recovery"""
    
    def __init__(self, max_retries: int = 3, 
                 retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF):
        self.max_retries = max_retries
        self.retry_strategy = retry_strategy
        self.task_attempts: Dict[str, int] = {}
        self.task_failures: Dict[str, List[datetime]] = {}
    
    def should_retry(self, task_id: str) -> bool:
        """Check if task should be retried"""
        attempts = self.task_attempts.get(task_id, 0)
        return attempts < self.max_retries
    
    def record_attempt(self, task_id: str, success: bool):
        """Record task attempt"""
        if task_id not in self.task_attempts:
            self.task_attempts[task_id] = 0
        
        if success:
            self.task_attempts[task_id] = 0
            if task_id in self.task_failures:
                del self.task_failures[task_id]
        else:
            self.task_attempts[task_id] += 1
            if task_id not in self.task_failures:
                self.task_failures[task_id] = []
            self.task_failures[task_id].append(datetime.now())
    
    def get_retry_delay(self, task_id: str) -> float:
        """Get delay before retry"""
        attempts = self.task_attempts.get(task_id, 0)
        
        if self.retry_strategy == RetryStrategy.IMMEDIATE:
            return 0
        elif self.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            return min(2 ** attempts, 3600)  # Max 1 hour
        elif self.retry_strategy == RetryStrategy.FIXED_INTERVAL:
            return 300  # 5 minutes
        else:
            return 0
    
    def get_failure_stats(self, task_id: str) -> Dict:
        """Get failure statistics for a task"""
        failures = self.task_failures.get(task_id, [])
        return {
            'total_failures': len(failures),
            'recent_failures': [f.isoformat() for f in failures[-5:]],
            'attempts': self.task_attempts.get(task_id, 0)
        }










