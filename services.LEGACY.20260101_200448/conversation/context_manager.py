#!/usr/bin/env python3
"""
ROXY Context Manager - Intelligent context window handling
"""
import logging
from typing import List, Dict, Any
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.conversation.context')

class ContextManager:
    """Manage conversation context window"""
    
    def __init__(self, max_tokens: int = 8000, max_messages: int = 50):
        self.max_tokens = max_tokens
        self.max_messages = max_messages
    
    def build_context(self, messages: List[Dict], facts: List[Dict] = None,
                     history: List[Dict] = None) -> str:
        """Build context string from messages and history"""
        context_parts = []
        
        # Add system context
        context_parts.append("You are ROXY, a permanent, learning, resident AI assistant.")
        
        # Add relevant facts
        if facts:
            context_parts.append("\nRelevant facts:")
            for fact in facts[:10]:
                fact_text = fact.get('fact', fact) if isinstance(fact, dict) else fact
                context_parts.append(f"- {fact_text}")
        
        # Add conversation history
        if history:
            context_parts.append("\nPrevious conversation:")
            for conv in history[-5:]:
                context_parts.append(f"User: {conv.get('user_input', '')}")
                context_parts.append(f"ROXY: {conv.get('response', '')}")
        
        # Add recent messages
        if messages:
            context_parts.append("\nCurrent conversation:")
            for msg in messages[-self.max_messages:]:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                context_parts.append(f"{role.capitalize()}: {content}")
        
        return "\n".join(context_parts)
    
    def truncate_context(self, context: str, max_tokens: int = None) -> str:
        """Truncate context if too long"""
        max_tokens = max_tokens or self.max_tokens
        # Simple token estimation (4 chars per token)
        max_chars = max_tokens * 4
        
        if len(context) <= max_chars:
            return context
        
        # Truncate from the beginning, keeping the end
        truncated = context[-max_chars:]
        return "...[context truncated]...\n" + truncated










