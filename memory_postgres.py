#!/usr/bin/env python3
"""
PostgreSQL Episodic Memory - Persistent conversation memory with semantic search
Uses pgvector for similarity search and temporal decay for natural recall
"""
import logging
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("roxy.memory_postgres")

# Try to import PostgreSQL adapter
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, Json
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logger.warning("psycopg2 not installed, using in-memory fallback")

# Try to import sentence-transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("sentence-transformers not available, semantic search disabled")


class PostgresMemory:
    """
    Episodic memory system using PostgreSQL with pgvector.
    
    Features:
    - Semantic similarity search for conversation recall
    - Importance scoring for memory consolidation
    - Temporal decay for natural forgetting
    - Knowledge graph for entity relationships
    - Graceful fallback to in-memory storage
    """
    
    def __init__(self,
                 host: str = 'localhost',
                 port: int = 5432,
                 database: str = 'roxy',
                 user: str = 'roxy',
                 password: str = 'b8BzulheJkevBjXxrmj1EJ3BQPlZ3JKF'):
        """
        Initialize PostgreSQL memory connection.
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        
        self.conn = None
        self.encoder = None
        self.use_pgvector = False
        
        # In-memory fallback
        self._memory_store: List[Dict[str, Any]] = []
        self._max_memory_size = 1000
        
        self._connect()
    
    def _connect(self):
        """Establish PostgreSQL connection and setup schema."""
        if not POSTGRES_AVAILABLE:
            logger.info("PostgreSQL adapter not available, using in-memory storage")
            return
        
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                connect_timeout=5
            )
            self.conn.autocommit = False
            logger.info(f"Connected to PostgreSQL at {self.host}:{self.port}/{self.database}")
            
            # Initialize encoder
            if EMBEDDINGS_AVAILABLE:
                try:
                    self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
                    logger.info("Loaded sentence-transformers encoder for memory embeddings")
                except Exception as e:
                    logger.warning(f"Failed to load encoder: {e}")
            
            # Setup schema
            self._setup_schema()
            
        except psycopg2.OperationalError as e:
            logger.warning(f"PostgreSQL connection failed: {e}")
            logger.info("Using in-memory storage fallback")
            self.conn = None
        except Exception as e:
            logger.warning(f"PostgreSQL initialization failed: {e}")
            self.conn = None
    
    def _setup_schema(self):
        """Create database schema with pgvector support."""
        if not self.conn:
            return
        
        try:
            with self.conn.cursor() as cur:
                # Try to enable pgvector extension
                try:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    self.use_pgvector = True
                    logger.info("pgvector extension enabled")
                except psycopg2.Error as e:
                    logger.warning(f"pgvector not available: {e}")
                    self.use_pgvector = False
                
                # Create conversations table
                if self.use_pgvector:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS conversations (
                            id SERIAL PRIMARY KEY,
                            session_id TEXT,
                            query TEXT NOT NULL,
                            response TEXT NOT NULL,
                            query_embedding vector(384),
                            importance FLOAT DEFAULT 0.5,
                            emotional_valence FLOAT DEFAULT 0.0,
                            context JSONB DEFAULT '{}',
                            access_count INTEGER DEFAULT 0,
                            created_at TIMESTAMP DEFAULT NOW(),
                            accessed_at TIMESTAMP DEFAULT NOW()
                        )
                    """)
                    
                    # Create vector index for fast similarity search
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_conv_embedding 
                        ON conversations USING ivfflat (query_embedding vector_cosine_ops)
                        WITH (lists = 100)
                    """)
                else:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS conversations (
                            id SERIAL PRIMARY KEY,
                            session_id TEXT,
                            query TEXT NOT NULL,
                            response TEXT NOT NULL,
                            importance FLOAT DEFAULT 0.5,
                            emotional_valence FLOAT DEFAULT 0.0,
                            context JSONB DEFAULT '{}',
                            access_count INTEGER DEFAULT 0,
                            created_at TIMESTAMP DEFAULT NOW(),
                            accessed_at TIMESTAMP DEFAULT NOW()
                        )
                    """)
                
                # Create indexes for efficient queries
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conv_session 
                    ON conversations(session_id, created_at DESC)
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conv_importance 
                    ON conversations(importance DESC)
                """)
                
                # Create knowledge graph table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_graph (
                        id SERIAL PRIMARY KEY,
                        entity TEXT UNIQUE NOT NULL,
                        entity_type TEXT,
                        properties JSONB DEFAULT '{}',
                        confidence FLOAT DEFAULT 0.5,
                        learned_from INTEGER REFERENCES conversations(id),
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                # Create knowledge edges table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_edges (
                        id SERIAL PRIMARY KEY,
                        from_entity INTEGER REFERENCES knowledge_graph(id),
                        to_entity INTEGER REFERENCES knowledge_graph(id),
                        relationship TEXT NOT NULL,
                        strength FLOAT DEFAULT 1.0,
                        evidence JSONB DEFAULT '[]',
                        created_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(from_entity, to_entity, relationship)
                    )
                """)
                
                # Create learned preferences table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS learned_preferences (
                        id SERIAL PRIMARY KEY,
                        category TEXT NOT NULL,
                        preference TEXT NOT NULL,
                        confidence FLOAT DEFAULT 0.5,
                        evidence JSONB DEFAULT '[]',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(category, preference)
                    )
                """)
                
                self.conn.commit()
                logger.info("PostgreSQL schema initialized")
                
        except Exception as e:
            logger.error(f"Schema setup failed: {e}")
            self.conn.rollback()
    
    def calculate_importance(self, 
                            query: str, 
                            response: str, 
                            context: Dict = None) -> float:
        """
        Calculate importance score for memory consolidation.
        
        Factors:
        - User feedback (positive = +0.2)
        - Follow-up questions (+0.1)
        - Task completion (+0.15)
        - Query complexity (+0.1)
        - Response detail (+0.1)
        - Important keywords (+0.2)
        """
        importance = 0.5  # Base score
        context = context or {}
        
        # User feedback
        if context.get('user_feedback') == 'positive':
            importance += 0.2
        elif context.get('user_feedback') == 'negative':
            importance -= 0.1
        
        # Follow-up questions indicate engagement
        if context.get('is_followup'):
            importance += 0.1
        
        # Task completion
        if context.get('task_completed'):
            importance += 0.15
        
        # Query complexity (longer queries usually more important)
        word_count = len(query.split())
        if word_count > 20:
            importance += 0.1
        elif word_count > 50:
            importance += 0.15
        
        # Response detail
        if len(response) > 500:
            importance += 0.1
        elif len(response) > 1000:
            importance += 0.15
        
        # Important keywords
        important_keywords = [
            'remember', 'important', 'always', 'never', 'preference',
            'my name', 'i like', 'i prefer', 'don\'t forget', 'note that'
        ]
        if any(kw in query.lower() for kw in important_keywords):
            importance += 0.2
        
        return min(max(importance, 0.0), 1.0)  # Clamp to [0, 1]
    
    def detect_emotion(self, query: str, response: str) -> float:
        """
        Detect emotional valence of conversation.
        Returns value from -1 (negative) to 1 (positive).
        """
        positive_words = [
            'thanks', 'great', 'awesome', 'perfect', 'excellent', 'love',
            'helpful', 'amazing', 'wonderful', 'fantastic', 'appreciate'
        ]
        negative_words = [
            'wrong', 'bad', 'terrible', 'hate', 'awful', 'useless',
            'frustrated', 'annoying', 'disappointing', 'confused', 'broken'
        ]
        
        text = (query + " " + response).lower()
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        total = positive_count + negative_count
        if total == 0:
            return 0.0
        
        return (positive_count - negative_count) / total
    
    def remember(self, 
                query: str, 
                response: str, 
                session_id: str = None,
                context: Dict = None) -> Optional[int]:
        """
        Store a conversation in memory.
        
        Args:
            query: User's query
            response: ROXY's response
            session_id: Optional session identifier
            context: Additional context metadata
            
        Returns:
            Memory ID if stored in PostgreSQL, None for memory fallback
        """
        context = context or {}
        
        # Calculate importance and emotion
        importance = self.calculate_importance(query, response, context)
        emotional_valence = self.detect_emotion(query, response)
        
        # Store in PostgreSQL if available
        if self.conn:
            try:
                return self._remember_postgres(
                    query, response, session_id, 
                    importance, emotional_valence, context
                )
            except Exception as e:
                logger.warning(f"PostgreSQL remember failed: {e}")
        
        # Fall back to in-memory
        return self._remember_memory(
            query, response, session_id,
            importance, emotional_valence, context
        )
    
    def _remember_postgres(self, query, response, session_id, 
                          importance, emotional_valence, context) -> int:
        """Store conversation in PostgreSQL."""
        with self.conn.cursor() as cur:
            # Generate embedding if available
            embedding = None
            if self.encoder and self.use_pgvector:
                try:
                    embedding = self.encoder.encode(query).tolist()
                except Exception as e:
                    logger.debug(f"Embedding generation failed: {e}")
            
            if embedding:
                cur.execute("""
                    INSERT INTO conversations 
                    (session_id, query, response, query_embedding, importance, emotional_valence, context)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (session_id, query, response, embedding, importance, emotional_valence, Json(context)))
            else:
                cur.execute("""
                    INSERT INTO conversations 
                    (session_id, query, response, importance, emotional_valence, context)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (session_id, query, response, importance, emotional_valence, Json(context)))
            
            memory_id = cur.fetchone()[0]
            self.conn.commit()
            
            logger.debug(f"Stored memory {memory_id} (importance={importance:.2f})")
            return memory_id
    
    def _remember_memory(self, query, response, session_id,
                        importance, emotional_valence, context) -> None:
        """Store conversation in in-memory fallback."""
        memory = {
            'id': len(self._memory_store) + 1,
            'session_id': session_id,
            'query': query,
            'response': response,
            'importance': importance,
            'emotional_valence': emotional_valence,
            'context': context,
            'access_count': 0,
            'created_at': datetime.now().isoformat(),
            'accessed_at': datetime.now().isoformat()
        }
        
        self._memory_store.append(memory)
        
        # Limit memory size
        if len(self._memory_store) > self._max_memory_size:
            # Remove least important old memories
            self._memory_store.sort(key=lambda m: (m['importance'], m['access_count']))
            self._memory_store = self._memory_store[100:]
        
        return None
    
    def recall(self, 
              query: str, 
              k: int = 5, 
              session_id: str = None,
              time_window_days: int = None) -> List[Dict[str, Any]]:
        """
        Recall relevant memories for a query.
        
        Args:
            query: Query to find relevant memories for
            k: Number of memories to return
            session_id: Optional session to filter by
            time_window_days: Optional time window filter
            
        Returns:
            List of relevant memories with similarity scores
        """
        # Try PostgreSQL first
        if self.conn:
            try:
                return self._recall_postgres(query, k, session_id, time_window_days)
            except Exception as e:
                logger.warning(f"PostgreSQL recall failed: {e}")
        
        # Fall back to in-memory
        return self._recall_memory(query, k, session_id, time_window_days)
    
    def _recall_postgres(self, query, k, session_id, time_window_days) -> List[Dict]:
        """Recall from PostgreSQL with semantic search and temporal decay."""
        memories = []
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Build query based on available features
            if self.encoder and self.use_pgvector:
                embedding = self.encoder.encode(query).tolist()
                
                # Semantic search with temporal decay
                sql = """
                    SELECT 
                        id, session_id, query, response, context, 
                        importance, emotional_valence, access_count,
                        created_at, accessed_at,
                        1 - (query_embedding <=> %s::vector) as similarity,
                        importance * exp(-0.01 * EXTRACT(EPOCH FROM (NOW() - created_at))/86400) as score
                    FROM conversations
                    WHERE 1=1
                """
                params = [embedding]
                
                if session_id:
                    sql += " AND session_id = %s"
                    params.append(session_id)
                
                if time_window_days:
                    sql += " AND created_at > NOW() - INTERVAL '%s days'"
                    params.append(time_window_days)
                
                sql += " ORDER BY score DESC LIMIT %s"
                params.append(k)
                
                cur.execute(sql, params)
            else:
                # Fall back to recency-based retrieval
                sql = """
                    SELECT 
                        id, session_id, query, response, context,
                        importance, emotional_valence, access_count,
                        created_at, accessed_at,
                        0.5 as similarity,
                        importance * exp(-0.01 * EXTRACT(EPOCH FROM (NOW() - created_at))/86400) as score
                    FROM conversations
                    WHERE 1=1
                """
                params = []
                
                if session_id:
                    sql += " AND session_id = %s"
                    params.append(session_id)
                
                if time_window_days:
                    sql += " AND created_at > NOW() - INTERVAL '%s days'"
                    params.append(time_window_days)
                
                sql += " ORDER BY created_at DESC LIMIT %s"
                params.append(k)
                
                cur.execute(sql, params)
            
            memories = cur.fetchall()
            
            # Update access times for recalled memories
            if memories:
                memory_ids = [m['id'] for m in memories]
                cur.execute("""
                    UPDATE conversations 
                    SET accessed_at = NOW(), access_count = access_count + 1
                    WHERE id = ANY(%s)
                """, (memory_ids,))
                self.conn.commit()
        
        return [dict(m) for m in memories]
    
    def _recall_memory(self, query, k, session_id, time_window_days) -> List[Dict]:
        """Recall from in-memory store with simple text matching."""
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_memories = []
        for memory in self._memory_store:
            # Filter by session if specified
            if session_id and memory.get('session_id') != session_id:
                continue
            
            # Filter by time window if specified
            if time_window_days:
                created = datetime.fromisoformat(memory['created_at'])
                if datetime.now() - created > timedelta(days=time_window_days):
                    continue
            
            # Simple word overlap similarity
            memory_words = set(memory['query'].lower().split())
            overlap = len(query_words & memory_words)
            similarity = overlap / max(len(query_words), 1)
            
            # Apply importance and temporal decay
            created = datetime.fromisoformat(memory['created_at'])
            days_old = (datetime.now() - created).days
            decay = np.exp(-0.01 * days_old) if EMBEDDINGS_AVAILABLE else 0.99 ** days_old
            
            score = memory['importance'] * decay * (0.5 + 0.5 * similarity)
            
            scored_memories.append({
                **memory,
                'similarity': similarity,
                'score': score
            })
        
        # Sort by score and return top k
        scored_memories.sort(key=lambda m: m['score'], reverse=True)
        
        # Update access counts
        for m in scored_memories[:k]:
            m['access_count'] = m.get('access_count', 0) + 1
            m['accessed_at'] = datetime.now().isoformat()
        
        return scored_memories[:k]
    
    def get_session_history(self, session_id: str, limit: int = 20) -> List[Dict]:
        """Get conversation history for a specific session."""
        if self.conn:
            try:
                with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT id, query, response, importance, created_at
                        FROM conversations
                        WHERE session_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (session_id, limit))
                    return [dict(r) for r in cur.fetchall()]
            except Exception as e:
                logger.warning(f"Session history failed: {e}")
        
        # In-memory fallback
        return [
            m for m in self._memory_store 
            if m.get('session_id') == session_id
        ][-limit:]
    
    def learn_preference(self, category: str, preference: str, confidence: float = 0.5):
        """Learn a user preference."""
        if self.conn:
            try:
                with self.conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO learned_preferences (category, preference, confidence)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (category, preference) DO UPDATE
                        SET confidence = (learned_preferences.confidence + %s) / 2,
                            updated_at = NOW()
                    """, (category, preference, confidence, confidence))
                    self.conn.commit()
                    logger.debug(f"Learned preference: {category} = {preference}")
            except Exception as e:
                logger.warning(f"Learn preference failed: {e}")
    
    def get_preferences(self, category: str = None) -> List[Dict]:
        """Get learned preferences."""
        if self.conn:
            try:
                with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if category:
                        cur.execute("""
                            SELECT category, preference, confidence, updated_at
                            FROM learned_preferences
                            WHERE category = %s
                            ORDER BY confidence DESC
                        """, (category,))
                    else:
                        cur.execute("""
                            SELECT category, preference, confidence, updated_at
                            FROM learned_preferences
                            ORDER BY category, confidence DESC
                        """)
                    return [dict(r) for r in cur.fetchall()]
            except Exception as e:
                logger.warning(f"Get preferences failed: {e}")
        
        return []
    
    def consolidate_memories(self) -> int:
        """
        Consolidate old memories (like REM sleep).
        Removes unimportant, old, unaccessed memories.
        
        Returns:
            Number of memories removed
        """
        if not self.conn:
            # In-memory consolidation
            before = len(self._memory_store)
            self._memory_store = [
                m for m in self._memory_store
                if m['importance'] > 0.3 or m['access_count'] > 0
            ]
            return before - len(self._memory_store)
        
        try:
            with self.conn.cursor() as cur:
                # Delete unimportant, old, unaccessed memories
                cur.execute("""
                    DELETE FROM conversations
                    WHERE importance < 0.3
                    AND access_count = 0
                    AND created_at < NOW() - INTERVAL '7 days'
                    RETURNING id
                """)
                deleted = cur.rowcount
                self.conn.commit()
                
                if deleted > 0:
                    logger.info(f"Consolidated {deleted} low-importance memories")
                
                return deleted
        except Exception as e:
            logger.warning(f"Consolidation failed: {e}")
            self.conn.rollback()
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        stats = {
            'backend': 'postgres' if self.conn else 'memory',
            'pgvector': self.use_pgvector
        }
        
        if self.conn:
            try:
                with self.conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM conversations")
                    stats['total_memories'] = cur.fetchone()[0]
                    
                    cur.execute("SELECT AVG(importance) FROM conversations")
                    stats['avg_importance'] = float(cur.fetchone()[0] or 0)
                    
                    cur.execute("SELECT COUNT(*) FROM knowledge_graph")
                    stats['knowledge_entities'] = cur.fetchone()[0]
                    
                    cur.execute("SELECT COUNT(*) FROM learned_preferences")
                    stats['learned_preferences'] = cur.fetchone()[0]
                    
            except Exception as e:
                stats['error'] = str(e)
        else:
            stats['total_memories'] = len(self._memory_store)
            stats['avg_importance'] = sum(m['importance'] for m in self._memory_store) / max(len(self._memory_store), 1)
        
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """Check memory system health."""
        status = {
            'healthy': False,
            'backend': 'memory',
            'details': {}
        }
        
        if self.conn:
            try:
                with self.conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    status['healthy'] = True
                    status['backend'] = 'postgres'
                    status['details']['pgvector'] = self.use_pgvector
            except Exception as e:
                status['details']['error'] = str(e)
        else:
            status['healthy'] = True
            status['backend'] = 'memory'
            status['details']['memory_count'] = len(self._memory_store)
        
        return status


# Singleton instance
_memory_instance: Optional[PostgresMemory] = None


def get_memory() -> PostgresMemory:
    """Get global memory instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = PostgresMemory()
    return _memory_instance
