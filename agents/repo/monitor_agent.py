#!/usr/bin/env python3
"""
ROXY Repository Monitor Agent - Monitor repo 24/7
"""
import logging
import os
import asyncio
from typing import Dict
from agents.framework.base_agent import BaseAgent
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.agents.repo.monitor')

class MonitorAgent(BaseAgent):
    """Agent for continuous repository monitoring"""
    
    def __init__(self):
        super().__init__('repo-monitor', 'Repository Monitor Agent')
        self.task_types = ['monitor', 'watch', 'continuous']
        self.monitoring = False
    
    async def execute(self, task: Dict) -> Dict:
        """Monitor repository"""
        _default_repo = os.environ.get('ROXY_ROOT', os.path.expanduser('~/.roxy'))
        repo_path = task.get('repo_path', _default_repo)
        check_interval = task.get('interval', 300)  # 5 minutes
        
        if not self.monitoring:
            self.monitoring = True
            asyncio.create_task(self._monitor_loop(repo_path, check_interval))
            return {'status': 'monitoring_started', 'repo_path': repo_path}
        else:
            return {'status': 'already_monitoring'}
    
    async def _monitor_loop(self, repo_path: str, interval: int):
        """Continuous monitoring loop"""
        while self.running and self.monitoring:
            try:
                # Check for changes
                import subprocess
                result = subprocess.run(['git', 'status', '--porcelain'], cwd=repo_path,
                                      capture_output=True, text=True)
                if result.stdout.strip():
                    logger.info(f"Repository changes detected: {result.stdout[:100]}")
                
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(interval)









