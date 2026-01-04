#!/usr/bin/env python3
"""
ROXY Base Agent - Base framework for autonomous agents
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from abc import ABC, abstractmethod
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.agents.base')

class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"

class BaseAgent(ABC):
    """Base class for all ROXY agents"""
    
    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name
        self.status = AgentStatus.IDLE
        self.running = False
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.last_task_time = None
        self.state = {}
    
    @abstractmethod
    async def execute(self, task: Dict) -> Dict:
        """Execute a task - must be implemented by subclasses"""
        pass
    
    async def start(self):
        """Start the agent"""
        self.running = True
        self.status = AgentStatus.RUNNING
        logger.info(f"Agent {self.name} started")
    
    async def stop(self):
        """Stop the agent"""
        self.running = False
        self.status = AgentStatus.IDLE
        logger.info(f"Agent {self.name} stopped")
    
    def get_status(self) -> Dict:
        """Get agent status"""
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'status': self.status.value,
            'running': self.running,
            'tasks_completed': self.tasks_completed,
            'tasks_failed': self.tasks_failed,
            'last_task_time': self.last_task_time.isoformat() if self.last_task_time else None
        }
    
    def update_state(self, key: str, value: Any):
        """Update agent state"""
        self.state[key] = value
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get agent state"""
        return self.state.get(key, default)










