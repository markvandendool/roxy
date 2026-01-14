#!/usr/bin/env python3
"""
ROXY Conversation Engine - Bidirectional conversation with context
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.conversation')

class ConversationEngine:
    """Bidirectional conversation engine"""
    
    def __init__(self):
        self.active_conversations = {}
        self.conversation_history = {}
    
    def start_conversation(self, session_id: str, context: Dict = None) -> Dict:
        """Start a new conversation"""
        self.active_conversations[session_id] = {
            'started_at': datetime.now().isoformat(),
            'messages': [],
            'context': context or {},
            'turn_count': 0
        }
        return self.active_conversations[session_id]
    
    def add_message(self, session_id: str, role: str, content: str, 
                   metadata: Dict = None) -> Dict:
        """Add message to conversation"""
        if session_id not in self.active_conversations:
            self.start_conversation(session_id)
        
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        self.active_conversations[session_id]['messages'].append(message)
        self.active_conversations[session_id]['turn_count'] += 1
        
        return message
    
    def get_conversation(self, session_id: str) -> Optional[Dict]:
        """Get conversation history"""
        return self.active_conversations.get(session_id)
    
    def get_context(self, session_id: str) -> Dict:
        """Get conversation context"""
        conv = self.active_conversations.get(session_id)
        if conv:
            return {
                'session_id': session_id,
                'started_at': conv['started_at'],
                'turn_count': conv['turn_count'],
                'recent_messages': conv['messages'][-5:],
                'context': conv['context']
            }
        return {}
    
    def end_conversation(self, session_id: str):
        """End conversation and archive"""
        if session_id in self.active_conversations:
            self.conversation_history[session_id] = self.active_conversations[session_id]
            del self.active_conversations[session_id]










