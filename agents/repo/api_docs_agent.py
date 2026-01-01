#!/usr/bin/env python3
"""
ROXY API Documentation Agent - Generate API documentation
"""
import logging
import ast
from typing import Dict, List
from agents.framework.base_agent import BaseAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.agents.repo.api_docs')

class APIDocsAgent(BaseAgent):
    """Agent for API documentation"""
    
    def __init__(self):
        super().__init__('api-docs', 'API Documentation Agent')
        self.task_types = ['api_docs', 'documentation']
    
    async def execute(self, task: Dict) -> Dict:
        """Generate API documentation"""
        file_path = task.get('file_path')
        if not file_path:
            return {'error': 'file_path required'}
        
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            
            # Parse and extract functions/classes
            tree = ast.parse(code)
            api_endpoints = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    api_endpoints.append({
                        'name': node.name,
                        'args': [arg.arg for arg in node.args.args],
                        'docstring': ast.get_docstring(node)
                    })
            
            return {
                'file_path': file_path,
                'endpoints': api_endpoints,
                'status': 'completed'
            }
        except Exception as e:
            return {'error': str(e)}










