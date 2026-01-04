#!/usr/bin/env python3
"""
ROXY Bug Detection Agent - Find bugs automatically
"""
import logging
import ast
from typing import Dict, List
from agents.framework.base_agent import BaseAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.agents.repo.bug_detection')

class BugDetectionAgent(BaseAgent):
    """Agent for bug detection"""
    
    def __init__(self):
        super().__init__('bug-detection', 'Bug Detection Agent')
        self.task_types = ['bug_detection', 'find_bugs']
    
    async def execute(self, task: Dict) -> Dict:
        """Detect bugs in code"""
        file_path = task.get('file_path')
        if not file_path:
            return {'error': 'file_path required'}
        
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            
            bugs = []
            
            # Check syntax
            try:
                ast.parse(code)
            except SyntaxError as e:
                bugs.append({
                    'type': 'syntax_error',
                    'message': str(e),
                    'severity': 'high'
                })
            
            # Check for common bugs
            if 'except:' in code:
                bugs.append({
                    'type': 'bare_except',
                    'message': 'Bare except clause - should specify exception type',
                    'severity': 'medium'
                })
            
            if 'assert ' in code and 'if __name__' not in code:
                bugs.append({
                    'type': 'assert_in_production',
                    'message': 'Assert statements in production code',
                    'severity': 'low'
                })
            
            return {
                'file_path': file_path,
                'bugs_found': len(bugs),
                'bugs': bugs,
                'status': 'completed'
            }
        except Exception as e:
            return {'error': str(e)}










