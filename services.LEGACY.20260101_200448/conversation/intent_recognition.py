#!/usr/bin/env python3
"""
ROXY Intent Recognition - Understand user intent from natural language
"""
import logging
import re
from typing import Dict, List, Any, Optional
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.conversation.intent')

class IntentType(Enum):
    QUESTION = "question"
    COMMAND = "command"
    INFORMATION = "information"
    CONVERSATION = "conversation"
    UNKNOWN = "unknown"

class IntentRecognizer:
    """Recognize user intent"""
    
    def __init__(self):
        self.patterns = {
            IntentType.QUESTION: [
                r'^(what|when|where|who|why|how|which|is|are|can|could|will|would|do|does|did)\s+',
                r'\?$',
                r'^tell me',
                r'^explain',
            ],
            IntentType.COMMAND: [
                r'^(run|execute|start|stop|open|close|create|delete|move|copy|send|read|write)',
                r'^(show|display|list|get|set|change|update)',
                r'^(please|can you|could you)',
            ],
            IntentType.INFORMATION: [
                r'^(my name is|i am|i like|i prefer|i have|i need)',
                r'^(remember|save|store)',
            ],
        }
    
    def recognize(self, text: str) -> Dict[str, Any]:
        """Recognize intent from text"""
        text_lower = text.lower().strip()
        
        # Check patterns
        for intent_type, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return {
                        'intent': intent_type.value,
                        'confidence': 0.8,
                        'text': text
                    }
        
        # Default to conversation
        return {
            'intent': IntentType.CONVERSATION.value,
            'confidence': 0.5,
            'text': text
        }
    
    def extract_entities(self, text: str, intent: str) -> Dict[str, Any]:
        """Extract entities from text"""
        entities = {}
        
        # Extract names
        name_match = re.search(r'(?:my name is|i am|call me)\s+([A-Z][a-z]+)', text)
        if name_match:
            entities['name'] = name_match.group(1)
        
        # Extract preferences
        pref_match = re.search(r'(?:i like|i prefer|i love)\s+(.+)', text)
        if pref_match:
            entities['preference'] = pref_match.group(1).strip()
        
        # Extract commands
        cmd_match = re.search(r'^(run|execute|start|stop|open|close)\s+(.+)', text, re.IGNORECASE)
        if cmd_match:
            entities['command'] = cmd_match.group(1)
            entities['target'] = cmd_match.group(2)
        
        return entities










