#!/usr/bin/env python3
"""
ROXY Conversation History - Efficient conversation storage and retrieval
"""
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.conversation.history')

class ConversationHistory:
    """Manage conversation history"""
    
    def __init__(self, db_path: str = '/home/mark/.roxy/data/roxy_memory.db'):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize conversation history tables"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                session_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                message_count INTEGER DEFAULT 0,
                context TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session ON conversation_messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON conversation_messages(timestamp);
        """)
        conn.commit()
        conn.close()
    
    def save_message(self, session_id: str, role: str, content: str, 
                    metadata: Dict = None):
        """Save conversation message"""
        import json
        conn = sqlite3.connect(self.db_path)
        
        # Ensure session exists
        conn.execute("""
            INSERT OR IGNORE INTO conversation_sessions 
            (session_id, started_at, message_count)
            VALUES (?, ?, 0)
        """, (session_id, datetime.now().isoformat()))
        
        # Insert message
        conn.execute("""
            INSERT INTO conversation_messages 
            (session_id, timestamp, role, content, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session_id,
            datetime.now().isoformat(),
            role,
            content,
            json.dumps(metadata or {})
        ))
        
        # Update message count
        conn.execute("""
            UPDATE conversation_sessions 
            SET message_count = message_count + 1
            WHERE session_id = ?
        """, (session_id,))
        
        conn.commit()
        conn.close()
    
    def get_session_messages(self, session_id: str, limit: int = 100) -> List[Dict]:
        """Get messages for a session"""
        import json
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT timestamp, role, content, metadata
            FROM conversation_messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
        """, (session_id, limit))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'timestamp': row[0],
                'role': row[1],
                'content': row[2],
                'metadata': json.loads(row[3] or '{}')
            })
        conn.close()
        return messages
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """Get recent conversation sessions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT session_id, started_at, ended_at, message_count
            FROM conversation_sessions
            ORDER BY started_at DESC
            LIMIT ?
        """, (limit,))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                'session_id': row[0],
                'started_at': row[1],
                'ended_at': row[2],
                'message_count': row[3]
            })
        conn.close()
        return sessions










