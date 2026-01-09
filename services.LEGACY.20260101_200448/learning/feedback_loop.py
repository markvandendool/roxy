#!/usr/bin/env python3
"""
ROXY Feedback Loop - Explicit feedback for continuous improvement
"""
import logging
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.learning.feedback')

class FeedbackLoop:
    """Learning from explicit feedback"""
    
    def __init__(self, db_path: str = '/home/mark/.roxy/data/roxy_memory.db'):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize feedback tables"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                interaction_id INTEGER,
                feedback_type TEXT NOT NULL,
                rating INTEGER,
                comment TEXT,
                improvements TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def record_feedback(self, interaction_id: int, feedback_type: str,
                       rating: int = None, comment: str = None,
                       improvements: List[str] = None):
        """Record user feedback"""
        import json
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO feedback 
            (timestamp, interaction_id, feedback_type, rating, comment, improvements)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            interaction_id,
            feedback_type,
            rating,
            comment,
            json.dumps(improvements or [])
        ))
        conn.commit()
        conn.close()
        logger.info(f"Feedback recorded: {feedback_type} (rating: {rating})")
    
    def get_feedback_stats(self) -> Dict:
        """Get feedback statistics"""
        conn = sqlite3.connect(self.db_path)
        
        total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        avg_rating = conn.execute("SELECT AVG(rating) FROM feedback WHERE rating IS NOT NULL").fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_feedback': total,
            'average_rating': round(avg_rating, 2) if avg_rating else None
        }










