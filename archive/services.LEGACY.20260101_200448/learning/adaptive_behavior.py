#!/usr/bin/env python3
"""
ROXY Adaptive Behavior System - Adapt to user preferences
"""
import logging
from typing import Dict, Any
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.learning.adaptive')

class AdaptiveBehavior:
    """Adapt behavior to user preferences"""
    
    def __init__(self, prefs_file: str = '/home/mark/.roxy/data/user-preferences.json'):
        self.prefs_file = Path(prefs_file)
        self.prefs_file.parent.mkdir(parents=True, exist_ok=True)
        self.preferences = self._load_preferences()
    
    def _load_preferences(self) -> Dict:
        """Load user preferences"""
        if self.prefs_file.exists():
            try:
                with open(self.prefs_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def update_preference(self, key: str, value: Any):
        """Update a preference"""
        self.preferences[key] = value
        self._save_preferences()
    
    def _save_preferences(self):
        """Save preferences"""
        try:
            with open(self.prefs_file, 'w') as f:
                json.dump(self.preferences, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a preference"""
        return self.preferences.get(key, default)
    
    def adapt_behavior(self, context: Dict) -> Dict:
        """Adapt behavior based on preferences and context"""
        adapted = {}
        
        # Adapt based on preferences
        if self.preferences.get('response_style') == 'concise':
            adapted['response_length'] = 'short'
        elif self.preferences.get('response_style') == 'detailed':
            adapted['response_length'] = 'long'
        
        return adapted










