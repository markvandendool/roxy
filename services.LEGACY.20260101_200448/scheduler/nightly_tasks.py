#!/usr/bin/env python3
"""
ROXY Nightly Tasks - Dedicated nightly task execution
"""
import asyncio
import logging
from typing import List, Dict, Callable
from datetime import datetime, time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.scheduler.nightly')

class NightlyTask:
    """Nightly task definition"""
    
    def __init__(self, name: str, handler: Callable, run_time: time = time(2, 0)):
        self.name = name
        self.handler = handler
        self.run_time = run_time
        self.last_run = None
    
    def is_due(self) -> bool:
        """Check if task should run"""
        now = datetime.now()
        current_time = now.time()
        
        # Check if it's past the run time today and hasn't run yet
        if current_time >= self.run_time:
            if self.last_run is None or self.last_run.date() < now.date():
                return True
        return False

class NightlyTaskSystem:
    """System for nightly tasks"""
    
    def __init__(self):
        self.tasks: List[NightlyTask] = []
        self._register_default_tasks()
    
    def _register_default_tasks(self):
        """Register default nightly tasks"""
        self.add_task("backup", self._backup_task)
        self.add_task("cleanup", self._cleanup_task)
        self.add_task("health_check", self._health_check_task)
        self.add_task("memory_consolidation", self._memory_consolidation_task)
    
    def add_task(self, name: str, handler: Callable, run_time: time = time(2, 0)):
        """Add a nightly task"""
        task = NightlyTask(name, handler, run_time)
        self.tasks.append(task)
        logger.info(f"Added nightly task: {name} (runs at {run_time})")
    
    async def run_due_tasks(self):
        """Run all due nightly tasks"""
        for task in self.tasks:
            if task.is_due():
                logger.info(f"Running nightly task: {task.name}")
                try:
                    if asyncio.iscoroutinefunction(task.handler):
                        await task.handler()
                    else:
                        task.handler()
                    task.last_run = datetime.now()
                    logger.info(f"Nightly task {task.name} completed")
                except Exception as e:
                    logger.error(f"Nightly task {task.name} failed: {e}")
    
    async def _backup_task(self):
        """Backup ROXY data"""
        try:
            from backup_service import get_backup_service
            backup = get_backup_service()
            backup.backup_all()
        except Exception as e:
            logger.error(f"Backup task failed: {e}")
    
    async def _cleanup_task(self):
        """Cleanup old files and logs"""
        try:
            from backup_service import get_backup_service
            backup = get_backup_service()
            backup.cleanup_old_backups()
        except Exception as e:
            logger.error(f"Cleanup task failed: {e}")
    
    async def _health_check_task(self):
        """Run health checks"""
        try:
            from health_monitor import HealthMonitor
            monitor = HealthMonitor()
            results = await monitor.check_all()
            logger.info(f"Health check results: {results}")
        except Exception as e:
            logger.error(f"Health check task failed: {e}")
    
    async def _memory_consolidation_task(self):
        """Consolidate memories"""
        try:
            from roxy_core import RoxyMemory
            from memory.consolidation import MemoryConsolidator
            memory = RoxyMemory()
            consolidator = MemoryConsolidator()
            consolidator.consolidate(memory)
        except Exception as e:
            logger.error(f"Memory consolidation task failed: {e}")









