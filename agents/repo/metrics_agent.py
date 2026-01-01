#!/usr/bin/env python3
"""
ROXY Code Metrics Agent - Track code metrics
"""
import logging
import ast
from typing import Dict
from agents.framework.base_agent import BaseAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.agents.repo.metrics')

class MetricsAgent(BaseAgent):
    """Agent for code metrics tracking"""
    
    def __init__(self):
        super().__init__('metrics', 'Code Metrics Agent')
        self.task_types = ['metrics', 'statistics', 'analyze']
    
    async def execute(self, task: Dict) -> Dict:
        """Calculate code metrics"""
        file_path = task.get('file_path')
        if not file_path:
            return {'error': 'file_path required'}
        
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            
            tree = ast.parse(code)
            
            metrics = {
                'lines_of_code': len(code.split('\n')),
                'functions': 0,
                'classes': 0,
                'imports': 0,
                'complexity': 0
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    metrics['functions'] += 1
                elif isinstance(node, ast.ClassDef):
                    metrics['classes'] += 1
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    metrics['imports'] += 1
            
            return {
                'file_path': file_path,
                'metrics': metrics,
                'status': 'completed'
            }
        except Exception as e:
            return {'error': str(e)}










