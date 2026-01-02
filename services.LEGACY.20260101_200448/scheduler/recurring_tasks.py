#!/usr/bin/env python3
"""
ROXY Recurring Task Manager - Manage recurring tasks
"""
import logging
from typing import List, Dict
from datetime import datetime, timedelta
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.scheduler.recurring')

class RecurrenceType(Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"

class RecurringTask:
    """Recurring task definition"""
    
    def __init__(self, task_id: str, name: str, recurrence: RecurrenceType,
                 handler: str, interval: int = 1):
        self.task_id = task_id
        self.name = name
        self.recurrence = recurrence
        self.handler = handler
        self.interval = interval
        self.last_run = None
        self.next_run = self._calculate_next_run()
    
    def _calculate_next_run(self) -> datetime:
        """Calculate next run time"""
        now = datetime.now()
        
        if self.recurrence == RecurrenceType.HOURLY:
            return now + timedelta(hours=self.interval)
        elif self.recurrence == RecurrenceType.DAILY:
            return now + timedelta(days=self.interval)
        elif self.recurrence == RecurrenceType.WEEKLY:
            return now + timedelta(weeks=self.interval)
        elif self.recurrence == RecurrenceType.MONTHLY:
            # Approximate month as 30 days
            return now + timedelta(days=30 * self.interval)
        else:
            return now + timedelta(hours=1)  # Default
    
    def is_due(self) -> bool:
        """Check if task is due"""
        return datetime.now() >= self.next_run
    
    def mark_run(self):
        """Mark task as run and calculate next run"""
        self.last_run = datetime.now()
        self.next_run = self._calculate_next_run()

class RecurringTaskManager:
    """Manage recurring tasks"""
    
    def __init__(self):
        self.tasks: Dict[str, RecurringTask] = {}
    
    def add_task(self, task_id: str, name: str, recurrence: RecurrenceType,
                 handler: str, interval: int = 1):
        """Add a recurring task"""
        task = RecurringTask(task_id, name, recurrence, handler, interval)
        self.tasks[task_id] = task
        logger.info(f"Added recurring task: {name} ({recurrence.value}, every {interval})")
    
    def get_due_tasks(self) -> List[RecurringTask]:
        """Get tasks that are due"""
        return [task for task in self.tasks.values() if task.is_due()]
    
    def run_task(self, task: RecurringTask):
        """Execute a recurring task"""
        logger.info(f"Running recurring task: {task.name}")
        try:
            # Import and call handler
            module_name, function_name = task.handler.rsplit('.', 1)
            module = __import__(module_name, fromlist=[function_name])
            handler_func = getattr(module, function_name)
            handler_func()
            task.mark_run()
        except Exception as e:
            logger.error(f"Recurring task {task.name} failed: {e}")










