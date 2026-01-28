#!/usr/bin/env python3
"""
Context Manager - Conversation context compression and management
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger("roxy.context_manager")


class ContextManager:
    """Manages conversation context with compression"""
    
    def __init__(self, max_context_length: int = 4000, max_history: int = 10):
        self.max_context_length = max_context_length
        self.max_history = max_history
        self.conversation_history: List[Dict[str, Any]] = []
    
    def add_to_history(self, query: str, response: str):
        """Add query/response to history"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response": response,
            "query_length": len(query),
            "response_length": len(response)
        }
        
        self.conversation_history.append(entry)
        
        # Keep only last N entries
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def get_context(self, current_query: str, include_recent: int = 5) -> str:
        """Get compressed context from history"""
        if not self.conversation_history:
            return ""
        
        # Get recent entries
        recent = self.conversation_history[-include_recent:]
        
        context_parts = []
        total_length = 0
        
        for entry in reversed(recent):  # Most recent first
            entry_text = f"Q: {entry['query']}\nA: {entry['response'][:200]}"
            entry_length = len(entry_text)
            
            if total_length + entry_length > self.max_context_length:
                break
            
            context_parts.insert(0, entry_text)
            total_length += entry_length
        
        return "\n\n".join(context_parts)
    
    def compress_old_history(self):
        """Compress old history entries"""
        if len(self.conversation_history) <= self.max_history:
            return
        
        # Keep recent entries, summarize old ones
        recent_count = self.max_history // 2
        old_entries = self.conversation_history[:-recent_count]
        recent_entries = self.conversation_history[-recent_count:]
        
        # Simple summarization: just keep query, truncate response
        compressed = []
        for entry in old_entries:
            compressed.append({
                "timestamp": entry["timestamp"],
                "query": entry["query"],
                "response": entry["response"][:100] + "..." if len(entry["response"]) > 100 else entry["response"],
                "compressed": True
            })
        
        self.conversation_history = compressed + recent_entries
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
    
    def get_history_summary(self) -> Dict[str, Any]:
        """Get summary of conversation history"""
        return {
            "total_entries": len(self.conversation_history),
            "total_length": sum(e["query_length"] + e["response_length"] for e in self.conversation_history),
            "oldest_entry": self.conversation_history[0]["timestamp"] if self.conversation_history else None,
            "newest_entry": self.conversation_history[-1]["timestamp"] if self.conversation_history else None
        }


# Global context manager
_context_manager = None


def get_context_manager() -> ContextManager:
    """Get global context manager"""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager
















