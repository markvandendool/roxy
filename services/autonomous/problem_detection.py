#!/usr/bin/env python3
"""
ROXY Proactive Problem Detection - Detect problems before they occur
"""
import logging
from typing import Dict, List
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.autonomous.problem_detection')

class ProblemDetector:
    """Detect problems proactively"""
    
    def __init__(self):
        self.detected_problems = []
        self.patterns = []
    
    def detect_system_problems(self) -> List[Dict]:
        """Detect system-level problems"""
        problems = []
        
        try:
            import psutil
            
            # Check disk space
            disk = psutil.disk_usage('/')
            if disk.percent > 90:
                problems.append({
                    'type': 'disk_space',
                    'severity': 'high',
                    'message': f'Disk usage at {disk.percent}%',
                    'timestamp': datetime.now().isoformat()
                })
            
            # Check memory
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                problems.append({
                    'type': 'memory',
                    'severity': 'high',
                    'message': f'Memory usage at {memory.percent}%',
                    'timestamp': datetime.now().isoformat()
                })
            
            # Check CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 95:
                problems.append({
                    'type': 'cpu',
                    'severity': 'medium',
                    'message': f'CPU usage at {cpu_percent}%',
                    'timestamp': datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"Problem detection error: {e}")
        
        return problems










