#!/usr/bin/env python3
"""
Memory Consolidation Module - "REM Sleep" for ROXY

Implements nightly memory consolidation to:
1. Remove low-value memories (importance < threshold, never accessed)
2. Boost frequently accessed memories
3. Archive old but important memories
4. Maintain memory quality and relevance

Based on research: Memory consolidation is critical for long-term AI assistants
(Synthetic Memory, Mem0 architecture patterns)
"""
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger("roxy.memory_consolidation")

# Database connection settings
DB_HOST = os.getenv("ROXY_DB_HOST", "localhost")
DB_PORT = os.getenv("ROXY_DB_PORT", "5432")
DB_NAME = os.getenv("ROXY_DB_NAME", "roxy")
DB_USER = os.getenv("ROXY_DB_USER", "roxy")
DB_PASSWORD = os.getenv("ROXY_DB_PASSWORD", "")

# Consolidation thresholds
IMPORTANCE_THRESHOLD_DELETE = 0.25  # Delete if importance < this AND never accessed
ACCESS_COUNT_THRESHOLD_BOOST = 3     # Boost importance if accessed >= this many times
DAYS_THRESHOLD_OLD = 30            # Consider memories old after this many days
DAYS_THRESHOLD_ARCHIVE = 90        # Archive memories older than this
MAX_MEMORIES_TO_KEEP = 5000        # Maximum memories to keep in active table

# Importance adjustments
IMPORTANCE_BOOST_AMOUNT = 0.1       # Add this much to frequently accessed memories
IMPORTANCE_DECAY_RATE = 0.01       # Decay per day for old memories


class MemoryConsolidator:
    """
    Memory consolidation orchestrator.
    Run nightly via cron or systemd timer.
    """
    
    def __init__(self):
        self._conn = None
        self._psycopg2 = None
        self._connect()
    
    def _connect(self):
        """Establish database connection."""
        try:
            import psycopg2
            self._psycopg2 = psycopg2
            self._conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                connect_timeout=5,
            )
            self._conn.autocommit = False
            logger.info(f"Connected to PostgreSQL at {DB_HOST}:{DB_PORT}/{DB_NAME}")
        except ImportError:
            logger.warning("psycopg2 not installed - using SQLite fallback")
            self._conn = None
        except Exception as e:
            logger.warning(f"Database connection failed: {e}")
            self._conn = None
    
    def consolidate(self) -> Dict[str, Any]:
        """
        Run full memory consolidation.
        
        Returns:
            Dict with consolidation results and statistics
        """
        stats = {
            "started_at": datetime.now().isoformat(),
            "memories_removed": 0,
            "memories_boosted": 0,
            "memories_archived": 0,
            "memories_trimmed": 0,
            "errors": [],
        }
        
        if not self._conn:
            stats["errors"].append("No database connection")
            return stats
        
        try:
            # Step 1: Remove low-value garbage memories
            removed = self._remove_garbage()
            stats["memories_removed"] = removed
            logger.info(f"Removed {removed} garbage memories")
            
            # Step 2: Boost frequently accessed memories
            boosted = self._boost_frequent_access()
            stats["memories_boosted"] = boosted
            logger.info(f"Boosted {boosted} frequently accessed memories")
            
            # Step 3: Decay old memories
            decayed = self._decay_old_memories()
            stats["memories_decayed"] = decayed
            logger.info(f"Decayed {decayed} old memories")
            
            # Step 4: Archive very old but important memories
            archived = self._archive_old_memories()
            stats["memories_archived"] = archived
            logger.info(f"Archived {archived} old important memories")
            
            # Step 5: Trim to max size if needed
            trimmed = self._trim_to_max_size()
            stats["memories_trimmed"] = trimmed
            logger.info(f"Trimmed {trimmed} memories to fit max size")
            
            self._conn.commit()
            
        except Exception as e:
            stats["errors"].append(str(e))
            logger.error(f"Consolidation failed: {e}")
            if self._conn:
                self._conn.rollback()
        
        stats["completed_at"] = datetime.now().isoformat()
        return stats
    
    def _remove_garbage(self) -> int:
        """Remove memories that are low value and never accessed."""
        if not self._conn:
            return 0
        
        cursor = self._conn.cursor()
        
        # Delete low importance AND never accessed AND older than 7 days
        cursor.execute("""
            DELETE FROM conversations
            WHERE id IN (
                SELECT id FROM conversations
                WHERE importance < %s
                AND access_count = 0
                AND created_at < NOW() - INTERVAL '7 days'
            )
        """, (IMPORTANCE_THRESHOLD_DELETE,))
        
        deleted = cursor.rowcount
        self._conn.commit()
        cursor.close()
        return deleted
    
    def _boost_frequent_access(self) -> int:
        """Boost importance of frequently accessed memories."""
        if not self._conn:
            return 0
        
        cursor = self._conn.cursor()
        
        # Boost importance for memories accessed many times
        cursor.execute("""
            UPDATE conversations
            SET importance = LEAST(importance + %s, 1.0)
            WHERE access_count >= %s
            AND importance < 1.0
            AND created_at > NOW() - INTERVAL '%s days'
        """, (IMPORTANCE_BOOST_AMOUNT, ACCESS_COUNT_THRESHOLD_BOOST, DAYS_THRESHOLD_OLD))
        
        updated = cursor.rowcount
        self._conn.commit()
        cursor.close()
        return updated
    
    def _decay_old_memories(self) -> int:
        """Apply time-based decay to old memories."""
        if not self._conn:
            return 0
        
        cursor = self._conn.cursor()
        
        # Decay importance of old memories that haven't been accessed recently
        cursor.execute("""
            UPDATE conversations
            SET importance = GREATEST(importance - %s, 0.1)
            WHERE created_at < NOW() - INTERVAL '%s days'
            AND access_count < %s
            AND importance > 0.1
        """, (IMPORTANCE_DECAY_RATE * 7, DAYS_THRESHOLD_OLD, ACCESS_COUNT_THRESHOLD_BOOST))
        
        updated = cursor.rowcount
        self._conn.commit()
        cursor.close()
        return updated
    
    def _archive_old_memories(self) -> int:
        """Move very old but important memories to archive."""
        if not self._conn:
            return 0
        
        cursor = self._conn.cursor()
        
        # Check if archive table exists, create if not
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations_archive (
                LIKE conversations INCLUDING ALL
            )
        """)
        
        # Move very old memories that are important
        cursor.execute("""
            WITH archived AS (
                DELETE FROM conversations
                WHERE importance >= 0.7
                AND created_at < NOW() - INTERVAL '%s days'
                RETURNING *
            )
            INSERT INTO conversations_archive
            SELECT * FROM archived
        """, (DAYS_THRESHOLD_ARCHIVE,))
        
        archived = cursor.rowcount
        self._conn.commit()
        cursor.close()
        return archived
    
    def _trim_to_max_size(self) -> int:
        """Ensure we don't exceed max memory count."""
        if not self._conn:
            return 0
        
        cursor = self._conn.cursor()
        
        # Count current memories
        cursor.execute("SELECT COUNT(*) FROM conversations")
        count = cursor.fetchone()[0]
        
        trimmed = 0
        if count > MAX_MEMORIES_TO_KEEP:
            # Remove lowest importance memories to fit within limit
            excess = count - MAX_MEMORIES_TO_KEEP
            cursor.execute("""
                DELETE FROM conversations
                WHERE id IN (
                    SELECT id FROM conversations
                    ORDER BY importance ASC, access_count ASC, created_at ASC
                    LIMIT %s
                )
            """, (excess,))
            trimmed = cursor.rowcount
            self._conn.commit()
        
        cursor.close()
        return trimmed
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current memory statistics."""
        if not self._conn:
            return {"error": "No database connection"}
        
        cursor = self._conn.cursor()
        
        stats = {}
        
        # Total memories
        cursor.execute("SELECT COUNT(*) FROM conversations")
        stats["total_memories"] = cursor.fetchone()[0]
        
        # Archived memories
        try:
            cursor.execute("SELECT COUNT(*) FROM conversations_archive")
            stats["archived_memories"] = cursor.fetchone()[0]
        except:
            stats["archived_memories"] = 0
        
        # Importance distribution
        cursor.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE importance < 0.3) as low,
                COUNT(*) FILTER (WHERE importance >= 0.3 AND importance < 0.7) as medium,
                COUNT(*) FILTER (WHERE importance >= 0.7) as high
            FROM conversations
        """)
        row = cursor.fetchone()
        stats["importance_distribution"] = {
            "low": row[0] or 0,
            "medium": row[1] or 0,
            "high": row[2] or 0,
        }
        
        # Average access count
        cursor.execute("SELECT AVG(access_count) FROM conversations WHERE access_count > 0")
        stats["avg_access_count"] = float(cursor.fetchone()[0] or 0)
        
        # Oldest memory
        cursor.execute("SELECT MIN(created_at) FROM conversations")
        stats["oldest_memory"] = str(cursor.fetchone()[0] or "N/A")
        
        # Newest memory
        cursor.execute("SELECT MAX(created_at) FROM conversations")
        stats["newest_memory"] = str(cursor.fetchone()[0] or "N/A")
        
        cursor.close()
        return stats
    
    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


def run_consolidation() -> Dict[str, Any]:
    """Run consolidation and return results."""
    consolidator = MemoryConsolidator()
    try:
        stats = consolidator.consolidate()
        stats["memory_stats"] = consolidator.get_stats()
        return stats
    finally:
        consolidator.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Starting ROXY Memory Consolidation...")
    print("=" * 50)
    
    results = run_consolidation()
    
    print(f"\nConsolidation Results:")
    print(f"  Started: {results.get('started_at')}")
    print(f"  Completed: {results.get('completed_at')}")
    print(f"  Memories Removed: {results.get('memories_removed')}")
    print(f"  Memories Boosted: {results.get('memories_boosted')}")
    print(f"  Memories Decayed: {results.get('memories_decayed')}")
    print(f"  Memories Archived: {results.get('memories_archived')}")
    print(f"  Memories Trimmed: {results.get('memories_trimmed')}")
    
    if results.get('errors'):
        print(f"\nErrors: {results['errors']}")
    
    stats = results.get('memory_stats', {})
    print(f"\nCurrent Memory Stats:")
    print(f"  Total: {stats.get('total_memories', 'N/A')}")
    print(f"  Archived: {stats.get('archived_memories', 'N/A')}")
    print(f"  Importance: Low={stats.get('importance_distribution', {}).get('low', 0)}, "
          f"Medium={stats.get('importance_distribution', {}).get('medium', 0)}, "
          f"High={stats.get('importance_distribution', {}).get('high', 0)}")
    print(f"  Avg Access Count: {stats.get('avg_access_count', 0):.2f}")
    
    print("\n" + "=" * 50)
    print("Memory consolidation complete!")
