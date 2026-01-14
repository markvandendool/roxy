#!/usr/bin/env python3
"""
ROXY Working Memory - Short-term memory for active conversations
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.memory.working')

class WorkingMemory:
    """Short-term working memory buffer"""
    
    def __init__(self, max_size: int = 20, ttl_seconds: int = 3600):
        self.buffer = deque(maxlen=max_size)
        self.ttl = timedelta(seconds=ttl_seconds)
        self.current_context = {}
    
    def add(self, key: str, value: Any, metadata: Dict = None):
        """Add item to working memory"""
        item = {
            'key': key,
            'value': value,
            'metadata': metadata or {},
            'timestamp': datetime.now(),
            'access_count': 0
        }
        self.buffer.append(item)
        logger.debug(f"Added to working memory: {key}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from working memory"""
        now = datetime.now()
        for item in self.buffer:
            if item['key'] == key:
                # Check TTL
                if now - item['timestamp'] < self.ttl:
                    item['access_count'] += 1
                    return item['value']
                else:
                    # Expired, remove it
                    self.buffer.remove(item)
        return None
    
    def get_all(self) -> List[Dict]:
        """Get all items in working memory"""
        now = datetime.now()
        active_items = []
        expired_items = []
        
        for item in list(self.buffer):
            if now - item['timestamp'] < self.ttl:
                active_items.append(item)
            else:
                expired_items.append(item)
        
        # Remove expired items
        for item in expired_items:
            self.buffer.remove(item)
        
        return active_items
    
    def clear(self):
        """Clear working memory"""
        self.buffer.clear()
        self.current_context = {}
        logger.info("Working memory cleared")
    
    def set_context(self, context: Dict):
        """Set current conversation context"""
        self.current_context = context
    
    def get_context(self) -> Dict:
        """Get current conversation context"""
        return self.current_context.copy()










