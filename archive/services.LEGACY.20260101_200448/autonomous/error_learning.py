#!/usr/bin/env python3
"""
ROXY Learning from Mistakes - Learn from failures
"""
import logging
from typing import Dict, List
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.autonomous.error_learning')

class ErrorLearning:
    """Learn from errors and failures"""
    
    def __init__(self, error_log: str = '/home/mark/.roxy/data/error-learning.json'):
        self.error_log = Path(error_log)
        self.error_log.parent.mkdir(parents=True, exist_ok=True)
        self.errors = self._load_errors()
    
    def _load_errors(self) -> List[Dict]:
        """Load error history"""
        if self.error_log.exists():
            try:
                with open(self.error_log, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def record_error(self, error_type: str, context: Dict, solution: str = None):
        """Record an error for learning"""
        from datetime import datetime
        error_entry = {
            'type': error_type,
            'context': context,
            'solution': solution,
            'timestamp': datetime.now().isoformat()
        }
        self.errors.append(error_entry)
        self._save_errors()
    
    def _save_errors(self):
        """Save error history"""
        try:
            with open(self.error_log, 'w') as f:
                json.dump(self.errors, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save errors: {e}")
    
    def find_similar_errors(self, error_type: str) -> List[Dict]:
        """Find similar past errors"""
        return [e for e in self.errors if e['type'] == error_type]










