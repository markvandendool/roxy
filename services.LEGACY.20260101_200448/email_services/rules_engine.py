#!/usr/bin/env python3
"""
ROXY Email Rules Engine - Automated email rules and filters
"""
import logging
import re
from typing import Dict, List, Callable, Any
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.email.rules')

class EmailRule:
    """Email rule definition"""
    
    def __init__(self, name: str, conditions: Dict, actions: List[str]):
        self.name = name
        self.conditions = conditions
        self.actions = actions
    
    def matches(self, email: Dict) -> bool:
        """Check if email matches rule conditions"""
        # Check subject
        if 'subject_contains' in self.conditions:
            if self.conditions['subject_contains'].lower() not in email.get('subject', '').lower():
                return False
        
        # Check sender
        if 'from_contains' in self.conditions:
            if self.conditions['from_contains'].lower() not in email.get('from', '').lower():
                return False
        
        # Check body
        if 'body_contains' in self.conditions:
            if self.conditions['body_contains'].lower() not in email.get('body', '').lower():
                return False
        
        return True

class EmailRulesEngine:
    """Execute email rules"""
    
    def __init__(self, rules_file: str = '/home/mark/.roxy/config/email-rules.json'):
        self.rules_file = Path(rules_file)
        self.rules_file.parent.mkdir(parents=True, exist_ok=True)
        self.rules = self._load_rules()
    
    def _load_rules(self) -> List[EmailRule]:
        """Load email rules"""
        if self.rules_file.exists():
            try:
                with open(self.rules_file, 'r') as f:
                    rules_data = json.load(f)
                    return [EmailRule(**rule) for rule in rules_data]
            except Exception as e:
                logger.error(f"Failed to load rules: {e}")
        return []
    
    def _save_rules(self):
        """Save email rules"""
        try:
            rules_data = [
                {
                    'name': rule.name,
                    'conditions': rule.conditions,
                    'actions': rule.actions
                }
                for rule in self.rules
            ]
            with open(self.rules_file, 'w') as f:
                json.dump(rules_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save rules: {e}")
    
    def add_rule(self, name: str, conditions: Dict, actions: List[str]):
        """Add a new email rule"""
        rule = EmailRule(name, conditions, actions)
        self.rules.append(rule)
        self._save_rules()
        logger.info(f"Added email rule: {name}")
    
    def apply_rules(self, email: Dict) -> List[str]:
        """Apply all matching rules to an email"""
        applied_actions = []
        for rule in self.rules:
            if rule.matches(email):
                applied_actions.extend(rule.actions)
                logger.info(f"Rule '{rule.name}' matched, applying actions: {rule.actions}")
        return applied_actions










