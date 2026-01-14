#!/usr/bin/env python3
"""
ROXY Episodic Memory - Store and recall specific events and experiences
"""
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.memory.episodic')

class EpisodicMemory:
    """Episodic memory for specific events and experiences"""
    
    def __init__(self, db_path: str = '/home/mark/.roxy/data/roxy_memory.db'):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize episodic memory tables"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                context TEXT,
                participants TEXT,
                location TEXT,
                emotional_valence REAL,
                importance REAL DEFAULT 1.0,
                tags TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_episodes_timestamp ON episodes(timestamp);
            CREATE INDEX IF NOT EXISTS idx_episodes_type ON episodes(event_type);
            CREATE INDEX IF NOT EXISTS idx_episodes_tags ON episodes(tags);
        """)
        conn.commit()
        conn.close()
    
    def store_episode(self, event_type: str, description: str, 
                     context: Dict = None, participants: List[str] = None,
                     location: str = None, emotional_valence: float = 0.0,
                     importance: float = 1.0, tags: List[str] = None):
        """Store an episodic memory"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO episodes 
            (timestamp, event_type, description, context, participants, location, 
             emotional_valence, importance, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            event_type,
            description,
            json.dumps(context or {}),
            json.dumps(participants or []),
            location,
            emotional_valence,
            importance,
            json.dumps(tags or [])
        ))
        conn.commit()
        conn.close()
        logger.info(f"Stored episode: {event_type} - {description[:50]}...")
    
    def recall_episodes(self, event_type: str = None, tags: List[str] = None,
                       limit: int = 10) -> List[Dict]:
        """Recall episodic memories"""
        conn = sqlite3.connect(self.db_path)
        query = "SELECT * FROM episodes WHERE 1=1"
        params = []
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        if tags:
            for tag in tags:
                query += " AND tags LIKE ?"
                params.append(f'%{tag}%')
        
        query += " ORDER BY importance DESC, timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        episodes = []
        for row in cursor.fetchall():
            episodes.append({
                'id': row[0],
                'timestamp': row[1],
                'event_type': row[2],
                'description': row[3],
                'context': json.loads(row[4] or '{}'),
                'participants': json.loads(row[5] or '[]'),
                'location': row[6],
                'emotional_valence': row[7],
                'importance': row[8],
                'tags': json.loads(row[9] or '[]')
            })
        conn.close()
        return episodes










