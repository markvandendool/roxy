#!/usr/bin/env python3
"""
ROXY Task Performance Metrics - Track task performance
"""
import logging
import time
from typing import Dict, List
from datetime import datetime
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.scheduler.metrics')

class TaskMetrics:
    """Track task performance metrics"""
    
    def __init__(self):
        self.execution_times: Dict[str, List[float]] = defaultdict(list)
        self.success_counts: Dict[str, int] = defaultdict(int)
        self.failure_counts: Dict[str, int] = defaultdict(int)
        self.last_execution: Dict[str, datetime] = {}
    
    def record_execution(self, task_id: str, duration: float, success: bool):
        """Record task execution"""
        self.execution_times[task_id].append(duration)
        if success:
            self.success_counts[task_id] += 1
        else:
            self.failure_counts[task_id] += 1
        self.last_execution[task_id] = datetime.now()
        
        # Keep only last 100 executions
        if len(self.execution_times[task_id]) > 100:
            self.execution_times[task_id] = self.execution_times[task_id][-100:]
    
    def get_task_metrics(self, task_id: str) -> Dict:
        """Get metrics for a specific task"""
        times = self.execution_times.get(task_id, [])
        if not times:
            return {}
        
        return {
            'execution_count': len(times),
            'average_duration': sum(times) / len(times),
            'min_duration': min(times),
            'max_duration': max(times),
            'success_count': self.success_counts.get(task_id, 0),
            'failure_count': self.failure_counts.get(task_id, 0),
            'success_rate': self.success_counts.get(task_id, 0) / len(times) if times else 0,
            'last_execution': self.last_execution.get(task_id).isoformat() if self.last_execution.get(task_id) else None
        }
    
    def get_all_metrics(self) -> Dict[str, Dict]:
        """Get metrics for all tasks"""
        return {task_id: self.get_task_metrics(task_id) 
                for task_id in self.execution_times.keys()}










