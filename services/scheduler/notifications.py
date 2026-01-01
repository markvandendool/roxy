#!/usr/bin/env python3
"""
ROXY Task Notification System - Notify on task completion/failure
"""
import logging
from typing import Dict, List, Callable
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.scheduler.notifications')

class NotificationType(Enum):
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_STARTED = "task_started"

class TaskNotificationSystem:
    """Task notification system"""
    
    def __init__(self):
        self.subscribers: Dict[NotificationType, List[Callable]] = {
            NotificationType.TASK_COMPLETED: [],
            NotificationType.TASK_FAILED: [],
            NotificationType.TASK_STARTED: []
        }
    
    def subscribe(self, notification_type: NotificationType, callback: Callable):
        """Subscribe to notifications"""
        self.subscribers[notification_type].append(callback)
        logger.info(f"Subscribed to {notification_type.value}")
    
    async def notify(self, notification_type: NotificationType, task_id: str, 
                    details: Dict = None):
        """Send notification"""
        callbacks = self.subscribers.get(notification_type, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task_id, details or {})
                else:
                    callback(task_id, details or {})
            except Exception as e:
                logger.error(f"Notification callback failed: {e}")
    
    async def notify_task_completed(self, task_id: str, duration: float):
        """Notify task completion"""
        await self.notify(NotificationType.TASK_COMPLETED, task_id, {
            'duration': duration,
            'status': 'success'
        })
    
    async def notify_task_failed(self, task_id: str, error: str):
        """Notify task failure"""
        await self.notify(NotificationType.TASK_FAILED, task_id, {
            'error': error,
            'status': 'failed'
        })










