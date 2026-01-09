#!/usr/bin/env python3
"""
ROXY Log Analysis Agent - Analyze system logs
"""
import logging
from typing import Dict, List
from pathlib import Path
from collections import Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.system.log_analyzer')

class LogAnalyzer:
    """Analyze system logs"""
    
    def analyze_logs(self, log_path: str = '/home/mark/.roxy/logs/roxy.log', 
                     lines: int = 1000) -> Dict:
        """Analyze log file"""
        log_file = Path(log_path)
        if not log_file.exists():
            return {'error': 'Log file not found'}
        
        try:
            with open(log_file, 'r') as f:
                log_lines = f.readlines()[-lines:]
            
            errors = [line for line in log_lines if 'ERROR' in line or 'error' in line.lower()]
            warnings = [line for line in log_lines if 'WARNING' in line or 'warning' in line.lower()]
            
            # Count error types
            error_types = Counter()
            for error in errors:
                if ':' in error:
                    error_type = error.split(':')[0].strip()
                    error_types[error_type] += 1
            
            return {
                'total_lines': len(log_lines),
                'errors': len(errors),
                'warnings': len(warnings),
                'error_types': dict(error_types),
                'recent_errors': errors[-10:] if errors else []
            }
        except Exception as e:
            return {'error': str(e)}










