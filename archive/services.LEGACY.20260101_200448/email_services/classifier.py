#!/usr/bin/env python3
"""
ROXY Email Classifier - Categorize emails automatically
"""
import logging
import re
from typing import Dict, List
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.email.classifier')

class EmailCategory(Enum):
    IMPORTANT = "important"
    URGENT = "urgent"
    SOCIAL = "social"
    PROMOTIONAL = "promotional"
    NOTIFICATIONS = "notifications"
    SPAM = "spam"
    GENERAL = "general"

class EmailClassifier:
    """Classify emails into categories"""
    
    def __init__(self):
        self.patterns = {
            EmailCategory.URGENT: [
                r'\b(urgent|asap|immediately|emergency|critical)\b',
                r'\b(due today|deadline|expires today)\b',
            ],
            EmailCategory.IMPORTANT: [
                r'\b(important|action required|please review|attention)\b',
                r'\b(meeting|appointment|conference)\b',
            ],
            EmailCategory.SOCIAL: [
                r'\b(facebook|twitter|linkedin|instagram)\b',
                r'\b(friend|invitation|connection)\b',
            ],
            EmailCategory.PROMOTIONAL: [
                r'\b(sale|discount|offer|deal|promotion)\b',
                r'\b(unsubscribe|opt-out)\b',
            ],
            EmailCategory.NOTIFICATIONS: [
                r'\b(notification|alert|reminder|update)\b',
                r'\b(no-reply|noreply)\b',
            ],
            EmailCategory.SPAM: [
                r'\b(viagra|casino|lottery|winner|prize)\b',
                r'\b(click here|limited time|act now)\b',
            ],
        }
    
    def classify(self, email: Dict) -> Dict:
        """Classify an email"""
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        sender = email.get('from', '').lower()
        
        text = f"{subject} {body} {sender}"
        
        scores = {}
        for category, patterns in self.patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches
            scores[category] = score
        
        # Determine category
        if scores:
            max_category = max(scores.items(), key=lambda x: x[1])
            if max_category[1] > 0:
                return {
                    'category': max_category[0].value,
                    'confidence': min(max_category[1] / 5.0, 1.0),
                    'scores': {k.value: v for k, v in scores.items()}
                }
        
        return {
            'category': EmailCategory.GENERAL.value,
            'confidence': 0.5,
            'scores': {}
        }










