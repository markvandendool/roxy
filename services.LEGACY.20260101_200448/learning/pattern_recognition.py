#!/usr/bin/env python3
"""
ROXY Pattern Recognition Engine - Recognize patterns in behavior
"""
import logging
from typing import Dict, List
from collections import Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.learning.pattern_recognition')

class PatternRecognizer:
    """Recognize patterns in user behavior"""
    
    def __init__(self):
        self.patterns = {}
    
    def recognize_patterns(self, data: List[Dict]) -> Dict:
        """Recognize patterns in data"""
        patterns = {}
        
        # Time-based patterns
        times = [item.get('timestamp', '')[:2] for item in data if 'timestamp' in item]
        if times:
            time_counter = Counter(times)
            patterns['peak_hours'] = [hour for hour, count in time_counter.most_common(3)]
        
        # Action patterns
        actions = [item.get('action') for item in data if 'action' in item]
        if actions:
            action_counter = Counter(actions)
            patterns['common_actions'] = [action for action, count in action_counter.most_common(5)]
        
        return patterns










