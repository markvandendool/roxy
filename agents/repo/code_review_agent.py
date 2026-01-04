#!/usr/bin/env python3
"""
ROXY Code Review Agent - Automated code reviews
"""
import logging
from typing import Dict
from agents.framework.base_agent import BaseAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.agents.repo.code_review')

class CodeReviewAgent(BaseAgent):
    """Agent for automated code reviews"""
    
    def __init__(self):
        super().__init__('code-review', 'Code Review Agent')
        self.task_types = ['code_review', 'review']
    
    async def execute(self, task: Dict) -> Dict:
        """Review code"""
        file_path = task.get('file_path')
        if not file_path:
            return {'error': 'file_path required'}
        
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            
            review = {
                'file_path': file_path,
                'suggestions': [],
                'issues': [],
                'score': 100
            }
            
            # Check for common issues
            if 'import *' in code:
                review['issues'].append('Wildcard imports detected')
                review['score'] -= 10
            
            if 'eval(' in code or 'exec(' in code:
                review['issues'].append('Use of eval/exec detected - security risk')
                review['score'] -= 20
            
            return review
        except Exception as e:
            return {'error': str(e)}










