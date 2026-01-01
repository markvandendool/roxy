#!/usr/bin/env python3
"""
ROXY Agent Orchestrator - Coordinate multiple agents
"""
import logging
import asyncio
from typing import Dict, List, Any, Optional
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.agents.orchestrator')

class AgentOrchestrator:
    """Orchestrate multiple autonomous agents"""
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.task_queue = []
        self.running = False
    
    def register_agent(self, agent):
        """Register an agent"""
        self.agents[agent.agent_id] = agent
        logger.info(f"Registered agent: {agent.name} ({agent.agent_id})")
    
    def get_agent(self, agent_id: str) -> Optional[Any]:
        """Get agent by ID"""
        return self.agents.get(agent_id)
    
    def list_agents(self) -> List[Dict]:
        """List all registered agents"""
        return [agent.get_status() for agent in self.agents.values()]
    
    async def assign_task(self, task: Dict, agent_id: str = None) -> Dict:
        """Assign task to an agent"""
        if agent_id:
            agent = self.agents.get(agent_id)
            if not agent:
                return {'error': f'Agent {agent_id} not found'}
        else:
            # Find best agent for task
            agent = self._find_best_agent(task)
            if not agent:
                return {'error': 'No suitable agent found'}
        
        try:
            result = await agent.execute(task)
            agent.tasks_completed += 1
            agent.last_task_time = datetime.now()
            return result
        except Exception as e:
            agent.tasks_failed += 1
            logger.error(f"Task execution failed: {e}")
            return {'error': str(e)}
    
    def _find_best_agent(self, task: Dict) -> Optional[Any]:
        """Find best agent for a task"""
        # Simple implementation - would use more sophisticated matching
        task_type = task.get('type', 'general')
        
        # Try to find agent by task type
        for agent in self.agents.values():
            if hasattr(agent, 'task_types') and task_type in agent.task_types:
                return agent
        
        # Return first available agent
        for agent in self.agents.values():
            if agent.status == AgentStatus.IDLE:
                return agent
        
        return None
    
    async def start_all_agents(self):
        """Start all registered agents"""
        for agent in self.agents.values():
            await agent.start()
        self.running = True
        logger.info(f"Started {len(self.agents)} agents")
    
    async def stop_all_agents(self):
        """Stop all agents"""
        for agent in self.agents.values():
            await agent.stop()
        self.running = False
        logger.info("All agents stopped")
    
    def get_orchestrator_status(self) -> Dict:
        """Get orchestrator status"""
        return {
            'total_agents': len(self.agents),
            'running_agents': sum(1 for a in self.agents.values() if a.running),
            'total_tasks_completed': sum(a.tasks_completed for a in self.agents.values()),
            'total_tasks_failed': sum(a.tasks_failed for a in self.agents.values()),
            'agents': self.list_agents()
        }










