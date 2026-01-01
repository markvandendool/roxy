#!/usr/bin/env python3
"""
ROXY Agent Monitoring System - Monitor agent health and performance
"""
import logging
from typing import Dict, List
from datetime import datetime, timedelta
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.agents.monitoring')

class AgentMonitor:
    """Monitor agent health and performance"""
    
    def __init__(self):
        self.agent_metrics: Dict[str, Dict] = defaultdict(dict)
        self.health_checks: Dict[str, datetime] = {}
    
    def record_metric(self, agent_id: str, metric_name: str, value: float):
        """Record agent metric"""
        if 'metrics' not in self.agent_metrics[agent_id]:
            self.agent_metrics[agent_id]['metrics'] = {}
        
        if metric_name not in self.agent_metrics[agent_id]['metrics']:
            self.agent_metrics[agent_id]['metrics'][metric_name] = []
        
        self.agent_metrics[agent_id]['metrics'][metric_name].append({
            'value': value,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 1000 measurements
        if len(self.agent_metrics[agent_id]['metrics'][metric_name]) > 1000:
            self.agent_metrics[agent_id]['metrics'][metric_name] = \
                self.agent_metrics[agent_id]['metrics'][metric_name][-1000:]
    
    def record_health_check(self, agent_id: str, healthy: bool):
        """Record agent health check"""
        self.health_checks[agent_id] = datetime.now()
        self.agent_metrics[agent_id]['last_health_check'] = datetime.now().isoformat()
        self.agent_metrics[agent_id]['healthy'] = healthy
    
    def get_agent_health(self, agent_id: str) -> Dict:
        """Get agent health status"""
        metrics = self.agent_metrics.get(agent_id, {})
        last_check = self.health_checks.get(agent_id)
        
        return {
            'agent_id': agent_id,
            'healthy': metrics.get('healthy', True),
            'last_health_check': last_check.isoformat() if last_check else None,
            'metrics': metrics.get('metrics', {})
        }
    
    def get_all_health(self) -> Dict[str, Dict]:
        """Get health status for all agents"""
        return {agent_id: self.get_agent_health(agent_id) 
                for agent_id in self.agent_metrics.keys()}










