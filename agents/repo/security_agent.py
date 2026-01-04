#!/usr/bin/env python3
"""
ROXY Security Scanning Agent - Security vulnerability scanning
"""
import logging
import re
from typing import Dict, List
from agents.framework.base_agent import BaseAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.agents.repo.security')

class SecurityAgent(BaseAgent):
    """Agent for security scanning"""
    
    def __init__(self):
        super().__init__('security', 'Security Scanning Agent')
        self.task_types = ['security', 'scan', 'vulnerability']
        self.vulnerability_patterns = [
            (r'eval\(', 'Use of eval() - code injection risk'),
            (r'exec\(', 'Use of exec() - code injection risk'),
            (r'pickle\.loads\(', 'Unsafe pickle deserialization'),
            (r'subprocess\.call\(.*shell=True', 'Shell injection risk'),
            (r'password\s*=\s*["\']', 'Hardcoded password detected'),
            (r'api_key\s*=\s*["\']', 'Hardcoded API key detected'),
        ]
    
    async def execute(self, task: Dict) -> Dict:
        """Scan for security vulnerabilities"""
        file_path = task.get('file_path')
        if not file_path:
            return {'error': 'file_path required'}
        
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            
            vulnerabilities = []
            for pattern, description in self.vulnerability_patterns:
                matches = re.finditer(pattern, code, re.IGNORECASE)
                for match in matches:
                    line_num = code[:match.start()].count('\n') + 1
                    vulnerabilities.append({
                        'type': 'security',
                        'description': description,
                        'line': line_num,
                        'severity': 'high' if 'injection' in description.lower() else 'medium'
                    })
            
            return {
                'file_path': file_path,
                'vulnerabilities_found': len(vulnerabilities),
                'vulnerabilities': vulnerabilities,
                'status': 'completed'
            }
        except Exception as e:
            return {'error': str(e)}










