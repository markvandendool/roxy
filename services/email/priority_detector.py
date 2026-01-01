#!/usr/bin/env python3
"""
ROXY Email Priority Detector - Identify urgent emails
"""
import logging
import re
from typing import Dict
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.email.priority')

class EmailPriorityDetector:
    """Detect email priority"""
    
    def __init__(self):
        self.urgent_keywords = [
            'urgent', 'asap', 'immediately', 'emergency', 'critical',
            'deadline', 'due today', 'expires', 'action required'
        ]
        self.important_keywords = [
            'important', 'please review', 'attention', 'meeting',
            'appointment', 'conference', 'call'
        ]
    
    def detect_priority(self, email: Dict) -> Dict:
        """Detect email priority level"""
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        sender = email.get('from', '').lower()
        
        text = f"{subject} {body}"
        
        # Check for urgent keywords
        urgent_score = sum(1 for keyword in self.urgent_keywords if keyword in text)
        important_score = sum(1 for keyword in self.important_keywords if keyword in text)
        
        # Check sender (known important contacts)
        sender_priority = self._check_sender_priority(sender)
        
        # Calculate priority
        if urgent_score > 0:
            priority = 'urgent'
            score = min(urgent_score * 0.3 + sender_priority, 1.0)
        elif important_score > 0:
            priority = 'important'
            score = min(important_score * 0.2 + sender_priority, 1.0)
        else:
            priority = 'normal'
            score = sender_priority
        
        return {
            'priority': priority,
            'score': score,
            'urgent_keywords_found': urgent_score,
            'important_keywords_found': important_score
        }
    
    def _check_sender_priority(self, sender: str) -> float:
        """Check if sender is in priority contacts"""
        # Would check against contact list
        # For now, return base priority
        return 0.1










