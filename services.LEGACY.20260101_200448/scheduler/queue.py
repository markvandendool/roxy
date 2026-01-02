#!/usr/bin/env python3
"""
ROXY Task Queue System - Priority-based task queue
"""
import logging
import heapq
from typing import List, Dict, Optional
from datetime import datetime
from enum import IntEnum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.scheduler.queue')

class TaskPriority(IntEnum):
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0

class QueuedTask:
    """Task in queue"""
    
    def __init__(self, task_id: str, handler: str, priority: TaskPriority = TaskPriority.NORMAL,
                 scheduled_time: datetime = None):
        self.task_id = task_id
        self.handler = handler
        self.priority = priority
        self.scheduled_time = scheduled_time or datetime.now()
        self.created_at = datetime.now()
    
    def __lt__(self, other):
        """Compare for priority queue (lower priority value = higher priority)"""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.scheduled_time < other.scheduled_time

class TaskQueue:
    """Priority-based task queue"""
    
    def __init__(self):
        self.queue: List[QueuedTask] = []
        self.processing: Dict[str, QueuedTask] = {}
    
    def enqueue(self, task_id: str, handler: str, 
               priority: TaskPriority = TaskPriority.NORMAL,
               scheduled_time: datetime = None):
        """Add task to queue"""
        task = QueuedTask(task_id, handler, priority, scheduled_time)
        heapq.heappush(self.queue, task)
        logger.info(f"Enqueued task {task_id} with priority {priority.name}")
    
    def dequeue(self) -> Optional[QueuedTask]:
        """Get next task from queue"""
        if not self.queue:
            return None
        
        task = heapq.heappop(self.queue)
        self.processing[task.task_id] = task
        return task
    
    def complete(self, task_id: str):
        """Mark task as complete"""
        if task_id in self.processing:
            del self.processing[task_id]
    
    def get_queue_size(self) -> int:
        """Get queue size"""
        return len(self.queue)
    
    def get_processing_count(self) -> int:
        """Get number of tasks being processed"""
        return len(self.processing)










