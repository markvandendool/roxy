#!/usr/bin/env python3
"""
ROXY Agent Communication Protocol - Inter-agent communication
"""
import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.agents.communication')

class AgentMessage:
    """Message between agents"""
    
    def __init__(self, from_agent: str, to_agent: str, message_type: str, 
                 payload: Dict, message_id: str = None):
        import uuid
        self.message_id = message_id or str(uuid.uuid4())
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.message_type = message_type
        self.payload = payload
        self.timestamp = datetime.now()
        self.delivered = False

class AgentCommunicationBus:
    """Communication bus for agents"""
    
    def __init__(self):
        self.message_queue: Dict[str, List[AgentMessage]] = defaultdict(list)
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.message_history: List[AgentMessage] = []
    
    def send_message(self, message: AgentMessage):
        """Send message to agent"""
        self.message_queue[message.to_agent].append(message)
        self.message_history.append(message)
        logger.info(f"Message {message.message_id} sent from {message.from_agent} to {message.to_agent}")
    
    def get_messages(self, agent_id: str) -> List[AgentMessage]:
        """Get messages for an agent"""
        messages = self.message_queue.get(agent_id, [])
        self.message_queue[agent_id] = []  # Clear after reading
        return messages
    
    def subscribe(self, message_type: str, callback: Callable):
        """Subscribe to message type"""
        self.subscribers[message_type].append(callback)
        logger.info(f"Subscribed to {message_type}")
    
    async def broadcast(self, message_type: str, payload: Dict, from_agent: str):
        """Broadcast message to all subscribers"""
        for callback in self.subscribers.get(message_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(from_agent, payload)
                else:
                    callback(from_agent, payload)
            except Exception as e:
                logger.error(f"Broadcast callback failed: {e}")

# Global communication bus
_communication_bus: Optional[AgentCommunicationBus] = None

def get_communication_bus() -> AgentCommunicationBus:
    """Get or create global communication bus"""
    global _communication_bus
    if _communication_bus is None:
        _communication_bus = AgentCommunicationBus()
    return _communication_bus

