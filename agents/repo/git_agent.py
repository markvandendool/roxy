#!/usr/bin/env python3
"""
ROXY Git Operations Agent - Automated git operations
"""
import logging
import os
import subprocess
from typing import Dict
from agents.framework.base_agent import BaseAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.agents.repo.git')

class GitAgent(BaseAgent):
    """Agent for git operations"""
    
    def __init__(self):
        super().__init__('git', 'Git Operations Agent')
        self.task_types = ['git', 'commit', 'push', 'pull']
    
    async def execute(self, task: Dict) -> Dict:
        """Execute git operation"""
        operation = task.get('operation', 'status')
        _default_repo = os.environ.get('ROXY_ROOT', os.path.expanduser('~/.roxy'))
        repo_path = task.get('repo_path', _default_repo)
        
        try:
            if operation == 'status':
                result = subprocess.run(['git', 'status'], cwd=repo_path,
                                      capture_output=True, text=True)
            elif operation == 'commit':
                message = task.get('message', 'Automated commit by ROXY')
                result = subprocess.run(['git', 'commit', '-am', message], cwd=repo_path,
                                      capture_output=True, text=True)
            elif operation == 'push':
                branch = task.get('branch', 'main')
                result = subprocess.run(['git', 'push', 'origin', branch], cwd=repo_path,
                                      capture_output=True, text=True)
            elif operation == 'pull':
                result = subprocess.run(['git', 'pull'], cwd=repo_path,
                                      capture_output=True, text=True)
            else:
                return {'error': f'Unknown operation: {operation}'}
            
            return {
                'operation': operation,
                'repo_path': repo_path,
                'returncode': result.returncode,
                'output': result.stdout,
                'status': 'completed' if result.returncode == 0 else 'failed'
            }
        except Exception as e:
            return {'error': str(e)}









