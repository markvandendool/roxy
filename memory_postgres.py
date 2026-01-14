#!/usr/bin/env python3
"""
PostgreSQL Episodic Memory - Persistent conversation memory with semantic search
Uses pgvector for similarity search and temporal decay for natural recall
"""
import logging
import json
import os
import time
import sqlite3
import shutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger("roxy.memory_postgres")

ROXY_DIR = Path.home() / ".roxy"
DEFAULT_SQLITE_PATH = ROXY_DIR / "data" / "roxy_memory.db"
OPT_SQLITE_PATH = Path("/opt/roxy/data/roxy_memory.db")
ENV_FILES = [
    ROXY_DIR / ".env",
    Path("/opt/roxy/.env")
]


def _load_env_file(path: Path) -> Dict[str, str]:
    """Load a .env-style file (key=value). Returns only POSTGRES_* keys."""
    data: Dict[str, str] = {}
    try:
        if not path.exists():
            return data
        for line in path.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key:
                continue
            if not (key.startswith("POSTGRES_") or key.startswith("ROXY_POSTGRES_") or key in ("DATABASE_URL", "ROXY_DATABASE_URL")):
                continue
            value = value.strip().strip('"').strip("'")
            data[key] = value
    except Exception:
        # Silent: never leak secrets or fail on env parsing
        return data
    return data


def _parse_database_url(url: str) -> Dict[str, Optional[str]]:
    """Parse DATABASE_URL into connection components."""
    if not url:
        return {}
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("postgres", "postgresql"):
            return {}
        return {
            "host": parsed.hostname,
            "port": str(parsed.port) if parsed.port else None,
            "database": parsed.path.lstrip("/") if parsed.path else None,
            "user": parsed.username,
            "password": parsed.password
        }
    except Exception:
        return {}

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
        # Load .env overrides (no secrets logged)
        env_overrides: Dict[str, str] = {}
        for env_path in ENV_FILES:
            env_overrides.update(_load_env_file(env_path))
        self._env_overrides = env_overrides

        # Parse DATABASE_URL if provided
        db_url = (
            os.getenv("ROXY_DATABASE_URL")
            or os.getenv("DATABASE_URL")
            or env_overrides.get("ROXY_DATABASE_URL")
            or env_overrides.get("DATABASE_URL")
        )
        parsed_url = _parse_database_url(db_url) if db_url else {}

        env_host = os.getenv("ROXY_POSTGRES_HOST") or os.getenv("POSTGRES_HOST") or env_overrides.get("ROXY_POSTGRES_HOST") or env_overrides.get("POSTGRES_HOST") or parsed_url.get("host")
        env_port = os.getenv("ROXY_POSTGRES_PORT") or os.getenv("POSTGRES_PORT") or env_overrides.get("ROXY_POSTGRES_PORT") or env_overrides.get("POSTGRES_PORT") or parsed_url.get("port")
        env_db = os.getenv("ROXY_POSTGRES_DB") or os.getenv("POSTGRES_DB") or env_overrides.get("ROXY_POSTGRES_DB") or env_overrides.get("POSTGRES_DB") or parsed_url.get("database")
        env_user = os.getenv("ROXY_POSTGRES_USER") or os.getenv("POSTGRES_USER") or env_overrides.get("ROXY_POSTGRES_USER") or env_overrides.get("POSTGRES_USER") or parsed_url.get("user")
        env_password = os.getenv("ROXY_POSTGRES_PASSWORD") or os.getenv("POSTGRES_PASSWORD") or env_overrides.get("ROXY_POSTGRES_PASSWORD") or env_overrides.get("POSTGRES_PASSWORD") or parsed_url.get("password")

        self.host = env_host or host
        self.port = int(env_port) if env_port else port
        self.database = env_db or database
        self.user = env_user or user
        self.password = env_password or password
        
        self.conn = None
        self.encoder = None
        self.use_pgvector = False
        self.embeddings_enabled = EMBEDDINGS_AVAILABLE and os.getenv("ROXY_MEMORY_DISABLE_EMBEDDINGS", "").lower() not in ("1", "true", "yes")
        self._encoder_loaded = False

        # SQLite fallback
        self.sqlite_fallback_enabled = os.getenv("ROXY_MEMORY_SQLITE_FALLBACK", "1").lower() not in ("0", "false", "no")
        self.sqlite_path_override = os.getenv("ROXY_MEMORY_SQLITE_PATH") or os.getenv("ROXY_MEMORY_SQLITE")
        self.sqlite_prefer_opt = os.getenv("ROXY_MEMORY_SQLITE_PREFER_OPT", "0").lower() in ("1", "true", "yes")
        self.require_persistent = os.getenv("ROXY_MEMORY_REQUIRE_PERSISTENT", "0").lower() in ("1", "true", "yes")
        self.require_postgres = os.getenv("ROXY_MEMORY_REQUIRE_POSTGRES", "0").lower() in ("1", "true", "yes")
        if self.require_postgres:
            self.sqlite_fallback_enabled = False
        self._sqlite_enabled = False
        self._sqlite_path: Optional[Path] = None
        self._sqlite_cols: Dict[str, Optional[str]] = {}
        self._sqlite_tables: set = set()
        
        # In-memory fallback
        self._memory_store: List[Dict[str, Any]] = []
        self._max_memory_size = 1000
        
        if self.require_postgres and not POSTGRES_AVAILABLE:
            raise RuntimeError("PostgreSQL adapter required but psycopg2 is unavailable")

        self._connect()
        if not self.conn and self.require_postgres:
            raise RuntimeError("PostgreSQL required but connection failed")
        if not self.conn and self.sqlite_fallback_enabled:
            self._init_sqlite_fallback()
        if self.require_persistent and not self.conn and not self._sqlite_enabled:
            raise RuntimeError("Persistent memory required but no backend available")
    
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
                connect_timeout=5,
                options="-c statement_timeout=5000"
            )
            self.conn.autocommit = False
            logger.info(f"Connected to PostgreSQL at {self.host}:{self.port}/{self.database}")
            # Lazy-load encoder on demand unless explicitly eager
            if self.embeddings_enabled and os.getenv("ROXY_MEMORY_EAGER_ENCODER", "0").lower() in ("1", "true", "yes"):
                self._ensure_encoder()
            
            # Setup schema
            self._setup_schema()
            
        except psycopg2.OperationalError as e:
            logger.warning(f"PostgreSQL connection failed: {e}")
            self.conn = None
            if self.require_postgres:
                raise
        except Exception as e:
            logger.warning(f"PostgreSQL initialization failed: {e}")
            self.conn = None
            if self.require_persistent:
                raise

    def _ensure_encoder(self):
        """Lazy-load embeddings encoder when needed."""
        if self.encoder or not self.embeddings_enabled:
            return
        try:
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
            self._encoder_loaded = True
            logger.info("Loaded sentence-transformers encoder for memory embeddings (CPU mode)")
        except Exception as e:
            logger.warning(f"Failed to load encoder: {e}")
            self.embeddings_enabled = False
            self.encoder = None
    
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

    def _resolve_sqlite_path(self) -> Optional[Path]:
        """Resolve SQLite path for fallback persistence."""
        if self.sqlite_path_override:
            return Path(self.sqlite_path_override).expanduser()
        if self.sqlite_prefer_opt and OPT_SQLITE_PATH.exists():
            return OPT_SQLITE_PATH
        if DEFAULT_SQLITE_PATH.exists():
            return DEFAULT_SQLITE_PATH
        if OPT_SQLITE_PATH.exists():
            # Prefer local copy to keep canonical root in ~/.roxy
            return DEFAULT_SQLITE_PATH
        return DEFAULT_SQLITE_PATH

    def _init_sqlite_fallback(self):
        """Initialize SQLite fallback for persistent memory."""
        try:
            path = self._resolve_sqlite_path()
            if not path:
                return
            self._sqlite_path = path
            self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)

            # Optional import from legacy /opt/roxy if we are creating a new DB
            import_opt = os.getenv("ROXY_MEMORY_SQLITE_IMPORT_OPT", "1").lower() in ("1", "true", "yes")
            if import_opt and not self._sqlite_path.exists() and OPT_SQLITE_PATH.exists() and self._sqlite_path != OPT_SQLITE_PATH:
                try:
                    shutil.copy2(OPT_SQLITE_PATH, self._sqlite_path)
                    logger.info("SQLite memory imported from /opt/roxy into ~/.roxy")
                except Exception as e:
                    logger.warning(f"SQLite import failed: {e}")

            conn = sqlite3.connect(self._sqlite_path)
            conn.row_factory = sqlite3.Row

            # Discover tables
            tables = set(r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"))
            self._sqlite_tables = tables

            # Create schema if missing
            if "conversations" not in tables:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT,
                        query TEXT NOT NULL,
                        response TEXT NOT NULL,
                        importance REAL DEFAULT 0.5,
                        emotional_valence REAL DEFAULT 0.0,
                        context TEXT,
                        access_count INTEGER DEFAULT 0,
                        created_at TEXT NOT NULL,
                        accessed_at TEXT NOT NULL
                    )
                """)
                tables.add("conversations")

            if "user_preferences" not in tables:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                tables.add("user_preferences")

            conn.commit()

            # Detect schema columns
            self._sqlite_cols = self._detect_sqlite_schema(conn)
            conn.close()

            self._sqlite_enabled = True
            self._load_sqlite_cache()
            logger.info(f"SQLite fallback enabled at {self._sqlite_path}")
        except Exception as e:
            logger.warning(f"SQLite fallback init failed: {e}")
            self._sqlite_enabled = False

    def _detect_sqlite_schema(self, conn) -> Dict[str, Optional[str]]:
        """Detect column mapping for SQLite conversations table."""
        try:
            cols = [row[1] for row in conn.execute("PRAGMA table_info(conversations)").fetchall()]
        except Exception:
            return {}
        if not cols:
            return {}
        return {
            "id": "id" if "id" in cols else None,
            "session_id": "session_id" if "session_id" in cols else None,
            "query": "query" if "query" in cols else ("user_input" if "user_input" in cols else None),
            "response": "response" if "response" in cols else ("jarvis_response" if "jarvis_response" in cols else None),
            "context": "context" if "context" in cols else None,
            "importance": "importance" if "importance" in cols else None,
            "emotional_valence": "emotional_valence" if "emotional_valence" in cols else None,
            "access_count": "access_count" if "access_count" in cols else None,
            "created_at": "created_at" if "created_at" in cols else ("timestamp" if "timestamp" in cols else None),
            "accessed_at": "accessed_at" if "accessed_at" in cols else None,
        }

    def _get_sqlite_conn(self):
        if not self._sqlite_path:
            return None
        conn = sqlite3.connect(self._sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_sqlite_cache(self):
        """Load recent SQLite memories into in-memory cache for recall."""
        if not self._sqlite_enabled:
            return
        query_col = self._sqlite_cols.get("query")
        response_col = self._sqlite_cols.get("response")
        created_col = self._sqlite_cols.get("created_at")
        context_col = self._sqlite_cols.get("context")
        session_col = self._sqlite_cols.get("session_id")
        if not query_col or not response_col or not created_col:
            return

        try:
            conn = self._get_sqlite_conn()
            if not conn:
                return
            cur = conn.cursor()
            sql = f"SELECT {query_col} AS query, {response_col} AS response, {created_col} AS created_at"
            if context_col:
                sql += f", {context_col} AS context"
            if session_col:
                sql += f", {session_col} AS session_id"
            sql += f" FROM conversations ORDER BY {created_col} DESC LIMIT ?"
            rows = cur.execute(sql, (self._max_memory_size,)).fetchall()
            conn.close()

            # Rebuild in-memory store (oldest -> newest)
            self._memory_store = []
            for row in reversed(rows):
                context = {}
                if context_col and row["context"]:
                    try:
                        context = json.loads(row["context"])
                    except Exception:
                        context = {}
                row_keys = row.keys()
                memory = {
                    "id": len(self._memory_store) + 1,
                    "session_id": row["session_id"] if "session_id" in row_keys else None,
                    "query": row["query"],
                    "response": row["response"],
                    "importance": self.calculate_importance(row["query"], row["response"], context),
                    "emotional_valence": self.detect_emotion(row["query"], row["response"]),
                    "context": context,
                    "access_count": 0,
                    "created_at": row["created_at"],
                    "accessed_at": row["created_at"]
                }
                self._memory_store.append(memory)
        except Exception as e:
            logger.warning(f"SQLite cache load failed: {e}")
    
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
        
        # Fall back to SQLite persistence if available
        if self._sqlite_enabled:
            try:
                self._remember_sqlite(
                    query, response, session_id,
                    importance, emotional_valence, context
                )
            except Exception as e:
                logger.warning(f"SQLite remember failed: {e}")

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
            if self.use_pgvector:
                self._ensure_encoder()
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

    def _remember_sqlite(self, query, response, session_id,
                         importance, emotional_valence, context) -> Optional[int]:
        """Store conversation in SQLite fallback."""
        if not self._sqlite_enabled:
            return None
        query_col = self._sqlite_cols.get("query")
        response_col = self._sqlite_cols.get("response")
        created_col = self._sqlite_cols.get("created_at")
        if not query_col or not response_col or not created_col:
            return None

        now_iso = datetime.now().isoformat()
        cols = []
        vals = []

        if self._sqlite_cols.get("session_id"):
            cols.append(self._sqlite_cols["session_id"])
            vals.append(session_id)
        cols.append(query_col)
        vals.append(query)
        cols.append(response_col)
        vals.append(response)

        if self._sqlite_cols.get("importance"):
            cols.append(self._sqlite_cols["importance"])
            vals.append(importance)
        if self._sqlite_cols.get("emotional_valence"):
            cols.append(self._sqlite_cols["emotional_valence"])
            vals.append(emotional_valence)
        if self._sqlite_cols.get("context"):
            cols.append(self._sqlite_cols["context"])
            vals.append(json.dumps(context or {}))
        if self._sqlite_cols.get("access_count"):
            cols.append(self._sqlite_cols["access_count"])
            vals.append(0)
        if created_col:
            cols.append(created_col)
            vals.append(now_iso)
        if self._sqlite_cols.get("accessed_at"):
            cols.append(self._sqlite_cols["accessed_at"])
            vals.append(now_iso)

        placeholders = ",".join(["?"] * len(vals))
        sql = f"INSERT INTO conversations ({', '.join(cols)}) VALUES ({placeholders})"

        conn = self._get_sqlite_conn()
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute(sql, vals)
        conn.commit()
        row_id = cur.lastrowid
        conn.close()
        return row_id
    
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

        # Ensure SQLite cache is loaded if available
        if self._sqlite_enabled and not self._memory_store:
            self._load_sqlite_cache()
        
        # Fall back to in-memory
        return self._recall_memory(query, k, session_id, time_window_days)
    
    def _recall_postgres(self, query, k, session_id, time_window_days) -> List[Dict]:
        """Recall from PostgreSQL with semantic search and temporal decay."""
        memories = []
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Build query based on available features
            if self.use_pgvector:
                self._ensure_encoder()
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
            decay = np.exp(-0.01 * days_old) if self.embeddings_enabled else 0.99 ** days_old
            
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

        if self._sqlite_enabled:
            try:
                if self._sqlite_cols.get("session_id"):
                    conn = self._get_sqlite_conn()
                    if conn:
                        query_col = self._sqlite_cols.get("query")
                        response_col = self._sqlite_cols.get("response")
                        created_col = self._sqlite_cols.get("created_at")
                        sql = f"""
                            SELECT {query_col} AS query, {response_col} AS response, {created_col} AS created_at
                            FROM conversations
                            WHERE {self._sqlite_cols.get("session_id")} = ?
                            ORDER BY {created_col} DESC
                            LIMIT ?
                        """
                        rows = conn.execute(sql, (session_id, limit)).fetchall()
                        conn.close()
                        return [dict(r) for r in rows]
                # If session_id column doesn't exist, fall back to recent memory
                return self._memory_store[-limit:]
            except Exception as e:
                logger.warning(f"SQLite session history failed: {e}")
        
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
        elif self._sqlite_enabled and "user_preferences" in self._sqlite_tables:
            try:
                key = f"{category}:{preference}"
                value = json.dumps({"preference": preference, "confidence": confidence})
                now_iso = datetime.now().isoformat()
                conn = self._get_sqlite_conn()
                if conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO user_preferences (key, value, updated_at) VALUES (?, ?, ?)",
                        (key, value, now_iso)
                    )
                    conn.commit()
                    conn.close()
            except Exception as e:
                logger.warning(f"SQLite learn preference failed: {e}")
    
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
        elif self._sqlite_enabled and "user_preferences" in self._sqlite_tables:
            try:
                conn = self._get_sqlite_conn()
                if conn:
                    rows = conn.execute("SELECT key, value, updated_at FROM user_preferences").fetchall()
                    conn.close()
                    prefs = []
                    for row in rows:
                        key = row["key"]
                        if ":" in key:
                            cat, pref = key.split(":", 1)
                        else:
                            cat, pref = "general", key
                        if category and cat != category:
                            continue
                        confidence = 0.5
                        try:
                            payload = json.loads(row["value"])
                            pref = payload.get("preference", pref)
                            confidence = float(payload.get("confidence", confidence))
                        except Exception:
                            pass
                        prefs.append({
                            "category": cat,
                            "preference": pref,
                            "confidence": confidence,
                            "updated_at": row["updated_at"]
                        })
                    return prefs
            except Exception as e:
                logger.warning(f"SQLite get preferences failed: {e}")

        return []
    
    def consolidate_memories(self) -> int:
        """
        Consolidate old memories (like REM sleep).
        Removes unimportant, old, unaccessed memories.
        
        Returns:
            Number of memories removed
        """
        if not self.conn:
            # SQLite consolidation if schema supports it
            if self._sqlite_enabled:
                try:
                    importance_col = self._sqlite_cols.get("importance")
                    access_col = self._sqlite_cols.get("access_count")
                    created_col = self._sqlite_cols.get("created_at")
                    if importance_col and access_col and created_col:
                        conn = self._get_sqlite_conn()
                        if conn:
                            cur = conn.cursor()
                            cur.execute(f"""
                                DELETE FROM conversations
                                WHERE {importance_col} < 0.3
                                AND {access_col} = 0
                                AND {created_col} < ?
                            """, ((datetime.now() - timedelta(days=7)).isoformat(),))
                            deleted = cur.rowcount
                            conn.commit()
                            conn.close()
                            if deleted > 0:
                                logger.info(f"Consolidated {deleted} low-importance SQLite memories")
                            return deleted
                except Exception as e:
                    logger.warning(f"SQLite consolidation failed: {e}")

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
            'backend': 'postgres' if self.conn else ('sqlite' if self._sqlite_enabled else 'memory'),
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
        elif self._sqlite_enabled:
            try:
                conn = self._get_sqlite_conn()
                if conn:
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) FROM conversations")
                    stats['total_memories'] = cur.fetchone()[0]
                    conn.close()
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
        elif self._sqlite_enabled:
            try:
                conn = self._get_sqlite_conn()
                if conn:
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) FROM conversations")
                    count = cur.fetchone()[0]
                    conn.close()
                    status['healthy'] = True
                    status['backend'] = 'sqlite'
                    status['details']['memory_count'] = count
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
