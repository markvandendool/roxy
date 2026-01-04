#!/usr/bin/env python3
"""
ROXY Testing Agent - Generate and run tests
"""
import logging
import subprocess
from typing import Dict
from agents.framework.base_agent import BaseAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.agents.repo.testing')

class TestingAgent(BaseAgent):
    """Agent for testing"""
    
    def __init__(self):
        super().__init__('testing', 'Testing Agent')
        self.task_types = ['test', 'testing', 'run_tests']
    
    async def execute(self, task: Dict) -> Dict:
        """Run tests"""
        test_path = task.get('test_path', '/opt/roxy')
        test_type = task.get('test_type', 'all')
        
        try:
            if test_type == 'pytest':
                result = subprocess.run(['pytest', test_path], 
                                      capture_output=True, text=True, timeout=300)
            elif test_type == 'unittest':
                result = subprocess.run(['python', '-m', 'unittest', 'discover', test_path],
                                      capture_output=True, text=True, timeout=300)
            else:
                return {'error': f'Unknown test type: {test_type}'}
            
            return {
                'test_type': test_type,
                'test_path': test_path,
                'returncode': result.returncode,
                'output': result.stdout,
                'status': 'passed' if result.returncode == 0 else 'failed'
            }
        except Exception as e:
            return {'error': str(e)}










