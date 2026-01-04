#!/usr/bin/env python3
"""
ROXY Release Management Agent - Manage releases
"""
import logging
import subprocess
from typing import Dict
from agents.framework.base_agent import BaseAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.agents.repo.release')

class ReleaseAgent(BaseAgent):
    """Agent for release management"""
    
    def __init__(self):
        super().__init__('release', 'Release Management Agent')
        self.task_types = ['release', 'version', 'deploy']
    
    async def execute(self, task: Dict) -> Dict:
        """Manage release"""
        action = task.get('action', 'check')
        version = task.get('version')
        repo_path = task.get('repo_path', '/opt/roxy')
        
        try:
            if action == 'check':
                result = subprocess.run(['git', 'tag', '--list'], cwd=repo_path,
                                      capture_output=True, text=True)
                return {
                    'action': 'check',
                    'tags': result.stdout.split('\n'),
                    'status': 'completed'
                }
            elif action == 'create' and version:
                result = subprocess.run(['git', 'tag', '-a', version, '-m', f'Release {version}'],
                                      cwd=repo_path, capture_output=True, text=True)
                return {
                    'action': 'create',
                    'version': version,
                    'status': 'completed' if result.returncode == 0 else 'failed'
                }
            else:
                return {'error': 'Invalid action or missing version'}
        except Exception as e:
            return {'error': str(e)}










