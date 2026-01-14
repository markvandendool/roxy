#!/usr/bin/env python3
"""
ROXY CI/CD Agent - Run CI/CD tasks
"""
import logging
import os
import subprocess
from typing import Dict
from agents.framework.base_agent import BaseAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.agents.repo.ci')

class CIAgent(BaseAgent):
    """Agent for CI/CD operations"""
    
    def __init__(self):
        super().__init__('ci', 'CI/CD Agent')
        self.task_types = ['ci', 'cd', 'pipeline']
    
    async def execute(self, task: Dict) -> Dict:
        """Run CI/CD pipeline"""
        pipeline = task.get('pipeline', 'test')
        _default_repo = os.environ.get('ROXY_ROOT', os.path.expanduser('~/.roxy'))
        repo_path = task.get('repo_path', _default_repo)
        
        try:
            if pipeline == 'test':
                result = subprocess.run(['pytest'], cwd=repo_path,
                                      capture_output=True, text=True, timeout=600)
            elif pipeline == 'lint':
                result = subprocess.run(['flake8', '.'], cwd=repo_path,
                                      capture_output=True, text=True, timeout=300)
            elif pipeline == 'build':
                result = subprocess.run(['python', 'setup.py', 'build'], cwd=repo_path,
                                      capture_output=True, text=True, timeout=600)
            else:
                return {'error': f'Unknown pipeline: {pipeline}'}
            
            return {
                'pipeline': pipeline,
                'repo_path': repo_path,
                'returncode': result.returncode,
                'output': result.stdout[:1000],  # Limit output
                'status': 'passed' if result.returncode == 0 else 'failed'
            }
        except Exception as e:
            return {'error': str(e)}









