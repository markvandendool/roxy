#!/usr/bin/env python3
"""
ROXY Task Scheduler - Cron-like task scheduling
"""
import asyncio
import logging
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json
import croniter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.scheduler')

class ScheduledTask:
    """Scheduled task definition"""
    
    def __init__(self, task_id: str, name: str, cron_expr: str, 
                 handler: str, enabled: bool = True):
        self.task_id = task_id
        self.name = name
        self.cron_expr = cron_expr
        self.handler = handler
        self.enabled = enabled
        self.last_run = None
        self.next_run = None
        self.run_count = 0
        self._update_next_run()
    
    def _update_next_run(self):
        """Calculate next run time"""
        if not self.enabled:
            self.next_run = None
            return
        
        try:
            cron = croniter.croniter(self.cron_expr, datetime.now())
            self.next_run = cron.get_next(datetime)
        except Exception as e:
            logger.error(f"Invalid cron expression {self.cron_expr}: {e}")
            self.next_run = None
    
    def is_due(self) -> bool:
        """Check if task is due to run"""
        if not self.enabled or not self.next_run:
            return False
        return datetime.now() >= self.next_run
    
    def mark_run(self):
        """Mark task as run"""
        self.last_run = datetime.now()
        self.run_count += 1
        self._update_next_run()

class TaskScheduler:
    """Task scheduler service"""
    
    def __init__(self, tasks_file: str = '/home/mark/.roxy/config/tasks.json'):
        self.tasks_file = Path(tasks_file)
        self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self._load_tasks()
    
    def _load_tasks(self):
        """Load tasks from file"""
        if self.tasks_file.exists():
            try:
                with open(self.tasks_file, 'r') as f:
                    tasks_data = json.load(f)
                    for task_data in tasks_data:
                        task = ScheduledTask(**task_data)
                        self.tasks[task.task_id] = task
                logger.info(f"Loaded {len(self.tasks)} scheduled tasks")
            except Exception as e:
                logger.error(f"Failed to load tasks: {e}")
    
    def _save_tasks(self):
        """Save tasks to file"""
        try:
            tasks_data = [
                {
                    'task_id': task.task_id,
                    'name': task.name,
                    'cron_expr': task.cron_expr,
                    'handler': task.handler,
                    'enabled': task.enabled,
                    'last_run': task.last_run.isoformat() if task.last_run else None,
                    'run_count': task.run_count
                }
                for task in self.tasks.values()
            ]
            with open(self.tasks_file, 'w') as f:
                json.dump(tasks_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")
    
    def add_task(self, task_id: str, name: str, cron_expr: str, handler: str):
        """Add a new scheduled task"""
        task = ScheduledTask(task_id, name, cron_expr, handler)
        self.tasks[task_id] = task
        self._save_tasks()
        logger.info(f"Added scheduled task: {name} ({cron_expr})")
    
    def get_due_tasks(self) -> List[ScheduledTask]:
        """Get tasks that are due to run"""
        return [task for task in self.tasks.values() if task.is_due()]
    
    async def run_task(self, task: ScheduledTask):
        """Execute a task"""
        logger.info(f"Running task: {task.name}")
        try:
            # Import and call handler
            # Handler format: "module.function"
            module_name, function_name = task.handler.rsplit('.', 1)
            module = __import__(module_name, fromlist=[function_name])
            handler_func = getattr(module, function_name)
            
            if asyncio.iscoroutinefunction(handler_func):
                await handler_func()
            else:
                handler_func()
            
            task.mark_run()
            self._save_tasks()
            logger.info(f"Task {task.name} completed")
        except Exception as e:
            logger.error(f"Task {task.name} failed: {e}")
    
    async def run_scheduler_loop(self):
        """Main scheduler loop"""
        self.running = True
        logger.info("Task scheduler started")
        
        while self.running:
            due_tasks = self.get_due_tasks()
            for task in due_tasks:
                await self.run_task(task)
            
            await asyncio.sleep(60)  # Check every minute
    
    def stop(self):
        """Stop scheduler"""
        self.running = False










