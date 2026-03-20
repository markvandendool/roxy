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
import re
import math
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger("roxy.memory_postgres")

ROXY_ROOT = Path(os.environ.get("ROXY_ROOT", str(Path.home() / ".roxy")))
DEFAULT_SQLITE_PATH = ROXY_ROOT / "data" / "roxy_memory.db"
LEGACY_ROOT = Path(os.environ.get("ROXY_LEGACY_ROOT", "/opt/roxy"))
OPT_SQLITE_PATH = LEGACY_ROOT / "data" / "roxy_memory.db"
ENV_FILES = [
    ROXY_ROOT / ".env",
    ROXY_ROOT / "etc" / "roxy.env",
    LEGACY_ROOT / ".env",
]

_TOKEN_PATTERN = re.compile(r"[a-z0-9']+")
_MEMORY_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "by", "for",
    "from", "had", "has", "have", "he", "her", "his", "i", "if", "in",
    "is", "it", "its", "me", "my", "of", "on", "or", "our", "she",
    "that", "the", "their", "them", "there", "they", "this", "to",
    "was", "we", "were", "what", "when", "where", "who", "why", "with",
    "you", "your",
}
_USER_ID_SANITIZE = re.compile(r"[^a-zA-Z0-9_.:-]+")
DEFAULT_MEMORY_RECORD_TYPES = {
    "conversation",
    "decision",
    "bug",
    "fix_recipe",
    "verification_recipe",
    "failure_event",
    "repo_fact",
    "content_rule",
}


def _resolve_default_user_id() -> str:
    """Resolve the fallback user_id used for memory/profile isolation."""
    configured = (
        os.getenv("ROXY_USER_ID")
        or os.getenv("ROXY_DEFAULT_USER_ID")
        or os.getenv("ROXY_CANONICAL_USER_ID")
    )
    if configured:
        cleaned = _USER_ID_SANITIZE.sub("-", configured.strip())
        if cleaned:
            return cleaned
    try:
        from canonical_identity import CANONICAL_USER_ID  # type: ignore
        cleaned = _USER_ID_SANITIZE.sub("-", str(CANONICAL_USER_ID).strip())
        if cleaned:
            return cleaned
    except Exception:
        pass
    return "default"


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
        self.default_user_id = _resolve_default_user_id()
        
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
        self._typed_records_store: List[Dict[str, Any]] = []
        self.hot_memory_limit = max(25, int(os.getenv("ROXY_MEMORY_HOT_LIMIT", "500")))
        self._hot_memory_cache: List[Dict[str, Any]] = []
        
        # In-memory fallback
        self._memory_store: List[Dict[str, Any]] = []
        self._max_memory_size = 1000
        try:
            self.recall_fetch_multiplier = max(
                1, int(os.getenv("ROXY_MEMORY_RECALL_FETCH_MULTIPLIER", "4"))
            )
        except Exception:
            self.recall_fetch_multiplier = 4
        try:
            self.recall_max_candidates = max(
                10, int(os.getenv("ROXY_MEMORY_MAX_CANDIDATES", "40"))
            )
        except Exception:
            self.recall_max_candidates = 40
        try:
            self.recall_min_score = float(os.getenv("ROXY_MEMORY_MIN_SCORE", "0.18"))
        except Exception:
            self.recall_min_score = 0.18
        try:
            self.recall_min_similarity = float(
                os.getenv("ROXY_MEMORY_MIN_SIMILARITY", "0.20")
            )
        except Exception:
            self.recall_min_similarity = 0.20
        try:
            self.recall_min_lexical = float(os.getenv("ROXY_MEMORY_MIN_LEXICAL", "0.12"))
        except Exception:
            self.recall_min_lexical = 0.12
        
        if self.require_postgres and not POSTGRES_AVAILABLE:
            raise RuntimeError("PostgreSQL adapter required but psycopg2 is unavailable")

        self._connect()
        if not self.conn and self.require_postgres:
            raise RuntimeError("PostgreSQL required but connection failed")
        if not self.conn and self.sqlite_fallback_enabled:
            self._init_sqlite_fallback()
        if self.require_persistent and not self.conn and not self._sqlite_enabled:
            raise RuntimeError("Persistent memory required but no backend available")
        self._refresh_hot_memory_cache()

    def _normalize_user_id(self, user_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> str:
        """Return a stable, sanitized user identifier for memory isolation."""
        source = user_id
        if not source and isinstance(context, dict):
            source = context.get("user_id")
        cleaned = _USER_ID_SANITIZE.sub("-", str(source or "").strip())
        if cleaned:
            return cleaned
        return self.default_user_id
    
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
    
    def _ensure_cross_encoder(self):
        """Lazy-load cross-encoder for precise reranking."""
        if hasattr(self, '_cross_encoder') and self._cross_encoder is not None:
            return
        try:
            from sentence_transformers import CrossEncoder
            self._cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', device='cpu')
            self._cross_encoder_loaded = True
            logger.info("Loaded cross-encoder for memory reranking (CPU mode)")
        except Exception as e:
            logger.warning(f"Failed to load cross-encoder: {e}")
            self._cross_encoder = None
            self._cross_encoder_loaded = False
    
    def _rerank_with_cross_encoder(
        self, 
        query: str, 
        memories: List[Dict[str, Any]], 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Rerank memories using cross-encoder for precise relevance scoring.
        Cross-encoder scores query-document pairs directly for better precision.
        """
        if not memories:
            return []
        
        # Ensure cross-encoder is loaded
        self._ensure_cross_encoder()
        
        if not self._cross_encoder:
            # Fallback to current scoring
            return memories[:top_k]
        
        try:
            # Prepare query-document pairs
            pairs = [
                (query, f"{m.get('query', '')} {str(m.get('response', ''))[:240]}")
                for m in memories
            ]
            
            # Get cross-encoder scores
            scores = self._cross_encoder.predict(pairs)
            
            # Attach scores and sort
            for m, score in zip(memories, scores):
                m['cross_encoder_score'] = float(score)
            
            memories.sort(key=lambda x: x['cross_encoder_score'], reverse=True)
            
            logger.debug(f"Cross-encoder reranked {len(memories)} memories")
            return memories[:top_k]
            
        except Exception as e:
            logger.debug(f"Cross-encoder reranking failed: {e}")
            return memories[:top_k]
    
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
                            user_id TEXT DEFAULT 'default',
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
                            user_id TEXT DEFAULT 'default',
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
                        user_id TEXT DEFAULT 'default',
                        category TEXT NOT NULL,
                        preference TEXT NOT NULL,
                        confidence FLOAT DEFAULT 0.5,
                        evidence JSONB DEFAULT '[]',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(user_id, category, preference)
                    )
                """)

                if self.use_pgvector:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS memory_records (
                            id SERIAL PRIMARY KEY,
                            user_id TEXT DEFAULT 'default',
                            record_type TEXT NOT NULL,
                            content TEXT NOT NULL,
                            scope TEXT DEFAULT '',
                            provenance TEXT DEFAULT '',
                            confidence FLOAT DEFAULT 0.5,
                            metadata JSONB DEFAULT '{}',
                            verified_at TIMESTAMP NULL,
                            embedding vector(384),
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW()
                        )
                    """)
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_memory_records_embedding
                        ON memory_records USING ivfflat (embedding vector_cosine_ops)
                        WITH (lists = 100)
                    """)
                else:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS memory_records (
                            id SERIAL PRIMARY KEY,
                            user_id TEXT DEFAULT 'default',
                            record_type TEXT NOT NULL,
                            content TEXT NOT NULL,
                            scope TEXT DEFAULT '',
                            provenance TEXT DEFAULT '',
                            confidence FLOAT DEFAULT 0.5,
                            metadata JSONB DEFAULT '{}',
                            verified_at TIMESTAMP NULL,
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW()
                        )
                    """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_memory_records_user_type
                    ON memory_records(user_id, record_type, updated_at DESC)
                """)

                # Schema migrations for older databases
                cur.execute("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS user_id TEXT")
                cur.execute("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS memory_type TEXT DEFAULT 'conversation'")
                cur.execute("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS provenance TEXT")
                cur.execute("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP NULL")
                cur.execute(
                    "UPDATE conversations SET user_id = %s WHERE user_id IS NULL OR user_id = ''",
                    (self.default_user_id,),
                )
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conv_user_session
                    ON conversations(user_id, session_id, created_at DESC)
                """)
                cur.execute("ALTER TABLE learned_preferences ADD COLUMN IF NOT EXISTS user_id TEXT")
                cur.execute(
                    "UPDATE learned_preferences SET user_id = %s WHERE user_id IS NULL OR user_id = ''",
                    (self.default_user_id,),
                )
                cur.execute(
                    "ALTER TABLE learned_preferences DROP CONSTRAINT IF EXISTS learned_preferences_category_preference_key"
                )
                cur.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_lp_user_category_preference
                    ON learned_preferences(user_id, category, preference)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_lp_user_category
                    ON learned_preferences(user_id, category, confidence DESC)
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
                        user_id TEXT,
                        query TEXT NOT NULL,
                        response TEXT NOT NULL,
                        importance REAL DEFAULT 0.5,
                        emotional_valence REAL DEFAULT 0.0,
                        context TEXT,
                        query_embedding TEXT,
                        memory_type TEXT DEFAULT 'conversation',
                        provenance TEXT,
                        verified_at TEXT,
                        access_count INTEGER DEFAULT 0,
                        created_at TEXT NOT NULL,
                        accessed_at TEXT NOT NULL
                    )
                """)
                tables.add("conversations")
            else:
                conv_cols = [row[1] for row in conn.execute("PRAGMA table_info(conversations)").fetchall()]
                if "user_id" not in conv_cols:
                    conn.execute("ALTER TABLE conversations ADD COLUMN user_id TEXT")
                if "query_embedding" not in conv_cols:
                    conn.execute("ALTER TABLE conversations ADD COLUMN query_embedding TEXT")
                if "memory_type" not in conv_cols:
                    conn.execute("ALTER TABLE conversations ADD COLUMN memory_type TEXT DEFAULT 'conversation'")
                if "provenance" not in conv_cols:
                    conn.execute("ALTER TABLE conversations ADD COLUMN provenance TEXT")
                if "verified_at" not in conv_cols:
                    conn.execute("ALTER TABLE conversations ADD COLUMN verified_at TEXT")
                conn.execute(
                    "UPDATE conversations SET user_id = ? WHERE user_id IS NULL OR user_id = ''",
                    (self.default_user_id,),
                )

            if "user_preferences" not in tables:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                tables.add("user_preferences")

            if "memory_records" not in tables:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memory_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        record_type TEXT NOT NULL,
                        content TEXT NOT NULL,
                        scope TEXT,
                        provenance TEXT,
                        confidence REAL DEFAULT 0.5,
                        metadata TEXT,
                        verified_at TEXT,
                        embedding TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                tables.add("memory_records")

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
            "user_id": "user_id" if "user_id" in cols else None,
            "query": "query" if "query" in cols else ("user_input" if "user_input" in cols else None),
            "response": "response" if "response" in cols else ("jarvis_response" if "jarvis_response" in cols else None),
            "context": "context" if "context" in cols else None,
            "importance": "importance" if "importance" in cols else None,
            "emotional_valence": "emotional_valence" if "emotional_valence" in cols else None,
            "access_count": "access_count" if "access_count" in cols else None,
            "created_at": "created_at" if "created_at" in cols else ("timestamp" if "timestamp" in cols else None),
            "accessed_at": "accessed_at" if "accessed_at" in cols else None,
            "query_embedding": "query_embedding" if "query_embedding" in cols else None,
            "memory_type": "memory_type" if "memory_type" in cols else None,
            "provenance": "provenance" if "provenance" in cols else None,
            "verified_at": "verified_at" if "verified_at" in cols else None,
        }

    def _get_sqlite_conn(self):
        if not self._sqlite_path:
            return None
        conn = sqlite3.connect(self._sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _serialize_embedding(self, embedding: Optional[List[float]]) -> Optional[str]:
        if not embedding:
            return None
        try:
            return json.dumps([float(value) for value in embedding])
        except Exception:
            return None

    def _deserialize_embedding(self, raw_value: Any) -> Optional[List[float]]:
        if raw_value in (None, "", []):
            return None
        if isinstance(raw_value, list):
            try:
                return [float(value) for value in raw_value]
            except Exception:
                return None
        try:
            decoded = json.loads(raw_value)
            if isinstance(decoded, list):
                return [float(value) for value in decoded]
        except Exception:
            return None
        return None

    def _encode_text(self, text: str) -> Optional[List[float]]:
        if not text:
            return None
        self._ensure_encoder()
        if not self.encoder:
            return None
        try:
            encoded = self.encoder.encode(text)
            return encoded.tolist() if hasattr(encoded, "tolist") else list(encoded)
        except Exception as e:
            logger.debug(f"Embedding generation failed: {e}")
            return None

    def _cosine_similarity(
        self,
        query_embedding: Optional[List[float]],
        candidate_embedding: Optional[List[float]],
    ) -> float:
        if not query_embedding or not candidate_embedding:
            return 0.0
        try:
            if not EMBEDDINGS_AVAILABLE:
                return 0.0
            query_vec = np.array(query_embedding, dtype=float)
            candidate_vec = np.array(candidate_embedding, dtype=float)
            if query_vec.shape != candidate_vec.shape:
                return 0.0
            query_norm = float(np.linalg.norm(query_vec))
            candidate_norm = float(np.linalg.norm(candidate_vec))
            if query_norm == 0.0 or candidate_norm == 0.0:
                return 0.0
            score = float(np.dot(query_vec, candidate_vec) / (query_norm * candidate_norm))
            return max(0.0, min(score, 1.0))
        except Exception:
            return 0.0

    def _refresh_hot_memory_cache(self):
        """Prewarm the most important recent memories into a hot in-process cache."""
        combined = list(self._memory_store)
        combined.sort(
            key=lambda item: (
                float(item.get("importance", 0.0)),
                self._coerce_datetime(item.get("created_at")).timestamp(),
            ),
            reverse=True,
        )
        self._hot_memory_cache = combined[: self.hot_memory_limit]

    def _load_sqlite_cache(self):
        """Load recent SQLite memories into in-memory cache for recall."""
        if not self._sqlite_enabled:
            return
        query_col = self._sqlite_cols.get("query")
        response_col = self._sqlite_cols.get("response")
        created_col = self._sqlite_cols.get("created_at")
        context_col = self._sqlite_cols.get("context")
        session_col = self._sqlite_cols.get("session_id")
        user_col = self._sqlite_cols.get("user_id")
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
            if user_col:
                sql += f", {user_col} AS user_id"
            if self._sqlite_cols.get("query_embedding"):
                sql += f", {self._sqlite_cols.get('query_embedding')} AS query_embedding"
            if self._sqlite_cols.get("memory_type"):
                sql += f", {self._sqlite_cols.get('memory_type')} AS memory_type"
            if self._sqlite_cols.get("provenance"):
                sql += f", {self._sqlite_cols.get('provenance')} AS provenance"
            if self._sqlite_cols.get("verified_at"):
                sql += f", {self._sqlite_cols.get('verified_at')} AS verified_at"
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
                    "user_id": row["user_id"] if "user_id" in row_keys else self.default_user_id,
                    "query": row["query"],
                    "response": row["response"],
                    "importance": self.calculate_importance(row["query"], row["response"], context),
                    "emotional_valence": self.detect_emotion(row["query"], row["response"]),
                    "context": context,
                    "query_embedding": self._deserialize_embedding(row["query_embedding"]) if "query_embedding" in row_keys else None,
                    "memory_type": row["memory_type"] if "memory_type" in row_keys and row["memory_type"] else "conversation",
                    "provenance": row["provenance"] if "provenance" in row_keys else "",
                    "verified_at": row["verified_at"] if "verified_at" in row_keys else None,
                    "access_count": 0,
                    "created_at": row["created_at"],
                    "accessed_at": row["created_at"]
                }
                self._memory_store.append(memory)
            self._refresh_hot_memory_cache()
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
                context: Dict = None,
                user_id: Optional[str] = None) -> Optional[int]:
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
        effective_user_id = self._normalize_user_id(user_id, context=context)
        context.setdefault("user_id", effective_user_id)
        
        # Calculate importance and emotion
        importance = self.calculate_importance(query, response, context)
        emotional_valence = self.detect_emotion(query, response)
        embedding = self._encode_text(query) if self.embeddings_enabled else None
        memory_type = str(context.get("memory_type") or "conversation").strip() or "conversation"
        provenance = str(context.get("provenance") or "").strip()
        verified_at = context.get("verified_at")

        # Store in PostgreSQL if available
        if self.conn:
            try:
                return self._remember_postgres(
                    query, response, session_id, 
                    importance, emotional_valence, context, effective_user_id,
                    embedding=embedding,
                    memory_type=memory_type,
                    provenance=provenance,
                    verified_at=verified_at,
                )
            except Exception as e:
                logger.warning(f"PostgreSQL remember failed: {e}")
        
        # Fall back to SQLite persistence if available
        if self._sqlite_enabled:
            try:
                row_id = self._remember_sqlite(
                    query, response, session_id,
                    importance, emotional_valence, context, effective_user_id,
                    embedding=embedding,
                    memory_type=memory_type,
                    provenance=provenance,
                    verified_at=verified_at,
                )
                return row_id
            except Exception as e:
                logger.warning(f"SQLite remember failed: {e}")

        # Fall back to in-memory
        return self._remember_memory(
            query, response, session_id,
            importance, emotional_valence, context, effective_user_id,
            embedding=embedding,
            memory_type=memory_type,
            provenance=provenance,
            verified_at=verified_at,
        )

    def _remember_postgres(self, query, response, session_id, 
                          importance, emotional_valence, context, user_id: str,
                          embedding: Optional[List[float]] = None,
                          memory_type: str = "conversation",
                          provenance: str = "",
                          verified_at: Optional[str] = None) -> int:
        """Store conversation in PostgreSQL."""
        with self.conn.cursor() as cur:
            if embedding:
                cur.execute("""
                    INSERT INTO conversations 
                    (session_id, user_id, query, response, query_embedding, importance, emotional_valence, context, memory_type, provenance, verified_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (session_id, user_id, query, response, embedding, importance, emotional_valence, Json(context), memory_type, provenance, verified_at))
            else:
                cur.execute("""
                    INSERT INTO conversations 
                    (session_id, user_id, query, response, importance, emotional_valence, context, memory_type, provenance, verified_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (session_id, user_id, query, response, importance, emotional_valence, Json(context), memory_type, provenance, verified_at))
            
            memory_id = cur.fetchone()[0]
            self.conn.commit()
            
            logger.debug(f"Stored memory {memory_id} (importance={importance:.2f})")
            return memory_id
    
    def _remember_memory(self, query, response, session_id,
                        importance, emotional_valence, context, user_id: str,
                        embedding: Optional[List[float]] = None,
                        memory_type: str = "conversation",
                        provenance: str = "",
                        verified_at: Optional[str] = None) -> None:
        """Store conversation in in-memory fallback."""
        memory = {
            'id': len(self._memory_store) + 1,
            'session_id': session_id,
            'user_id': user_id,
            'query': query,
            'response': response,
            'importance': importance,
            'emotional_valence': emotional_valence,
            'context': context,
            'query_embedding': embedding,
            'memory_type': memory_type,
            'provenance': provenance,
            'verified_at': verified_at,
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
        self._refresh_hot_memory_cache()
        
        return None

    def _remember_sqlite(self, query, response, session_id,
                         importance, emotional_valence, context, user_id: str,
                         embedding: Optional[List[float]] = None,
                         memory_type: str = "conversation",
                         provenance: str = "",
                         verified_at: Optional[str] = None) -> Optional[int]:
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
        if self._sqlite_cols.get("user_id"):
            cols.append(self._sqlite_cols["user_id"])
            vals.append(user_id)
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
        if self._sqlite_cols.get("query_embedding"):
            cols.append(self._sqlite_cols["query_embedding"])
            vals.append(self._serialize_embedding(embedding))
        if self._sqlite_cols.get("memory_type"):
            cols.append(self._sqlite_cols["memory_type"])
            vals.append(memory_type)
        if self._sqlite_cols.get("provenance"):
            cols.append(self._sqlite_cols["provenance"])
            vals.append(provenance)
        if self._sqlite_cols.get("verified_at"):
            cols.append(self._sqlite_cols["verified_at"])
            vals.append(verified_at)
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
        self._remember_memory(
            query,
            response,
            session_id,
            importance,
            emotional_valence,
            context,
            user_id,
            embedding=embedding,
            memory_type=memory_type,
            provenance=provenance,
            verified_at=verified_at,
        )
        return row_id
    
    def _tokenize_for_overlap(self, text: str) -> set[str]:
        if not text:
            return set()
        tokens = _TOKEN_PATTERN.findall(text.lower())
        return {
            token for token in tokens
            if len(token) > 1 and token not in _MEMORY_STOPWORDS
        }

    def _lexical_overlap(self, query: str, candidate: str) -> float:
        query_tokens = self._tokenize_for_overlap(query)
        candidate_tokens = self._tokenize_for_overlap(candidate)
        if not query_tokens or not candidate_tokens:
            return 0.0
        overlap = len(query_tokens & candidate_tokens)
        query_recall = overlap / max(len(query_tokens), 1)
        jaccard = overlap / max(len(query_tokens | candidate_tokens), 1)
        return max(0.0, min((0.75 * query_recall) + (0.25 * jaccard), 1.0))
    
    def _bm25_score(self, query: str, candidate: str, avg_doc_len: float = 50.0, k1: float = 1.5, b: float = 0.75) -> float:
        """
        Calculate BM25 score for query vs candidate document.
        BM25 is a ranking function used by search engines.
        """
        query_tokens = self._tokenize_for_overlap(query)
        candidate_tokens = self._tokenize_for_overlap(candidate)
        
        if not query_tokens:
            return 0.0
        
        # Tokenize and count
        cand_lower = candidate.lower()
        cand_words = cand_lower.split()
        doc_len = len(cand_words)
        
        # Calculate BM25 for each query term
        score = 0.0
        for token in query_tokens:
            if len(token) < 2:
                continue
            # Term frequency in candidate
            tf = cand_words.count(token)
            if tf == 0:
                continue
            # IDF approximation (simplified - in production, calculate from corpus)
            idf = 1.0  # Simplified IDF
            # BM25 formula
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * (doc_len / max(avg_doc_len, 1)))
            score += idf * (numerator / max(denominator, 0.1))
        
        # Normalize to 0-1 range
        return min(score / max(len(query_tokens), 1), 1.0)
    
    def _reciprocal_rank_fusion(self, rankings: List[List[tuple]], k: int = 60) -> List[tuple]:
        """
        Reciprocal Rank Fusion (RRF) combines multiple rankings.
        
        For each ranking, RRF assigns a score based on position.
        Final score = sum of 1/(k + position) for each ranking.
        This is the gold standard for fusing multiple retrieval methods.
        """
        scores: Dict[int, float] = {}
        
        for ranking in rankings:
            for position, item in enumerate(ranking):
                item_id = item[0] if isinstance(item, tuple) else item
                if isinstance(item, dict):
                    item_id = item.get('id', id(item))
                else:
                    item_id = item
                # RRF formula
                rrf_score = 1.0 / (k + position + 1)
                scores[item_id] = scores.get(item_id, 0.0) + rrf_score
        
        # Sort by fused score
        fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return fused
    
    def _hybrid_recall(
        self,
        query: str,
        k: int,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        time_window_days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval combining vector similarity + BM25 + lexical overlap.
        Uses Reciprocal Rank Fusion to combine rankings.
        """
        if not self.conn:
            return []
        
        fetch_limit = min(k * 4, self.recall_max_candidates)
        effective_user_id = self._normalize_user_id(user_id)
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get all candidate memories
            sql = """
                SELECT 
                    id, session_id, user_id, query, response, context, 
                    importance, emotional_valence, access_count,
                    created_at, accessed_at,
                    0.0 as vector_similarity
                FROM conversations
                WHERE 1=1
            """
            params = []
            
            if session_id:
                sql += " AND session_id = %s"
                params.append(session_id)
            if effective_user_id:
                sql += " AND user_id = %s"
                params.append(effective_user_id)
            
            if time_window_days:
                sql += " AND created_at > NOW() - (%s * INTERVAL '1 day')"
                params.append(int(time_window_days))
            
            sql += f" ORDER BY importance DESC, created_at DESC LIMIT {fetch_limit}"
            cur.execute(sql, params)
            candidates = [dict(row) for row in cur.fetchall()]
        
        if not candidates:
            return []
        
        # Score each candidate with multiple methods
        scored_candidates = []
        for mem in candidates:
            cand_text = f"{mem.get('query', '')} {str(mem.get('response', ''))[:240]}"
            
            # Vector similarity (if available)
            vector_sim = float(mem.get('vector_similarity', 0.0))
            
            # BM25 score
            bm25 = self._bm25_score(query, cand_text)
            
            # Lexical overlap
            lexical = self._lexical_overlap(query, cand_text)
            
            # Composite score with weights
            composite = (0.4 * vector_sim) + (0.4 * bm25) + (0.2 * lexical)
            
            mem['vector_similarity'] = vector_sim
            mem['bm25'] = bm25
            mem['lexical_overlap'] = lexical
            mem['hybrid_score'] = composite
            mem['score'] = composite
            mem['similarity'] = vector_sim
            
            scored_candidates.append(mem)
        
        # Sort by hybrid score
        scored_candidates.sort(key=lambda x: x['hybrid_score'], reverse=True)
        
        return scored_candidates[:k]

    def _coerce_datetime(self, value) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception:
                pass
        return datetime.now()

    # MindSong/SkyBeam production keywords - boosted for CEO role
    _MINESONG_PRODUCTION_KEYWORDS = {
        'skybeam', 'skydream', 'shotcaller', 'stackkraft', 'mimiq', 'mqqc',
        'luno', 'pixel', 'rocky', 'mindsong', 'render', 'rendering', 'export',
        'monetization', 'master', 'mastering', 'orchestration', 'orchestrate',
        'queue', 'gpu', '6900xt', 'w5700x', 'ollama', 'pipeline', 'content',
        'video', 'audio', 'music', 'song', 'beat', 'track', 'arrangement',
        'production', 'deadline', 'shot', 'takes', 'stems', 'bounce', 'compress',
        'eq', 'mix', 'studio', 'creative', 'workflow'
    }
    _MINESONG_BOOST_WEIGHT = 0.15

    def _composite_recall_score(self, query: str, memory: Dict[str, Any], same_session: bool) -> Dict[str, float]:
        similarity = float(memory.get("similarity") or 0.0)
        candidate_text = f"{memory.get('query', '')} {str(memory.get('response', ''))[:240]}"
        lexical = self._lexical_overlap(query, candidate_text)
        importance = float(memory.get("importance") or 0.5)
        created_at = self._coerce_datetime(memory.get("created_at"))
        days_old = max((datetime.now(created_at.tzinfo) - created_at).total_seconds() / 86400.0, 0.0)
        recency = math.exp(-0.02 * days_old)
        session_boost = 0.08 if same_session else 0.0
        
        # MindSong/SkyBeam production boost - CEO priority
        query_lower = query.lower()
        candidate_lower = candidate_text.lower()
        combined_lower = query_lower + " " + candidate_lower
        
        production_boost = 0.0
        query_hits = sum(1 for kw in self._MINESONG_PRODUCTION_KEYWORDS if kw in query_lower)
        candidate_hits = sum(1 for kw in self._MINESONG_PRODUCTION_KEYWORDS if kw in candidate_lower)
        
        # Boost if query mentions production terms AND candidate contains them
        if query_hits > 0 and candidate_hits > 0:
            production_boost = min(self._MINESONG_BOOST_WEIGHT * (query_hits + candidate_hits) / 4.0, 0.25)
        
        composite = (
            (0.50 * max(0.0, min(similarity, 1.0)))
            + (0.20 * lexical)
            + (0.12 * max(0.0, min(importance, 1.0)))
            + (0.05 * recency)
            + session_boost
            + production_boost
        )
        return {
            "similarity": max(0.0, min(similarity, 1.0)),
            "lexical_overlap": lexical,
            "composite_score": max(0.0, min(composite, 1.2)),
            "production_boost": production_boost,
        }

    def _rerank_and_filter_memories(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        k: int,
        session_id: Optional[str] = None,
        min_score: Optional[float] = None,
        min_similarity: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        if not memories:
            return []

        score_gate = self.recall_min_score if min_score is None else float(min_score)
        similarity_gate = self.recall_min_similarity if min_similarity is None else float(min_similarity)
        lexical_gate = self.recall_min_lexical

        scored: List[Dict[str, Any]] = []
        for memory in memories:
            same_session = bool(session_id and memory.get("session_id") == session_id)
            score_parts = self._composite_recall_score(query, memory, same_session=same_session)
            memory_view = dict(memory)
            memory_view["raw_score"] = float(memory.get("score") or 0.0)
            memory_view["similarity"] = score_parts["similarity"]
            memory_view["lexical_overlap"] = score_parts["lexical_overlap"]
            memory_view["score"] = score_parts["composite_score"]
            scored.append(memory_view)

        scored.sort(
            key=lambda m: (
                float(m.get("score", 0.0)),
                float(m.get("similarity", 0.0)),
                self._coerce_datetime(m.get("created_at")).timestamp(),
            ),
            reverse=True,
        )

        filtered = [
            m for m in scored
            if (
                float(m.get("score", 0.0)) >= score_gate
                or float(m.get("similarity", 0.0)) >= similarity_gate
                or float(m.get("lexical_overlap", 0.0)) >= lexical_gate
            )
        ]
        minimum_keep = min(k, 2)
        if len(filtered) < minimum_keep:
            filtered = scored[:k]
        else:
            filtered = filtered[:k]
        return filtered

    def recall(self, 
              query: str, 
              k: int = 5, 
              session_id: str = None,
              user_id: Optional[str] = None,
              time_window_days: int = None,
              min_score: Optional[float] = None,
              min_similarity: Optional[float] = None,
              use_cross_encoder: bool = True) -> List[Dict[str, Any]]:
        """
        Recall relevant memories for a query.
        
        Args:
            query: Query to find relevant memories for
            k: Number of memories to return
            session_id: Optional session to filter by
            time_window_days: Optional time window filter
            min_score: Optional minimum composite score threshold
            min_similarity: Optional minimum semantic similarity threshold
            use_cross_encoder: Whether to use cross-encoder reranking (default True)
            
        Returns:
            List of relevant memories with similarity scores
        """
        k = max(int(k or 5), 1)
        effective_user_id = self._normalize_user_id(user_id)

        # Try hybrid retrieval first (BM25 + vector + lexical)
        try:
            hybrid_memories = self._hybrid_recall(
                query,
                k=k,
                session_id=session_id,
                user_id=effective_user_id,
                time_window_days=time_window_days,
            )
            if hybrid_memories:
                # Apply cross-encoder reranking for better precision
                if use_cross_encoder and len(hybrid_memories) > 1:
                    hybrid_memories = self._rerank_with_cross_encoder(query, hybrid_memories, top_k=k)
                # Apply final filtering with scoring
                return self._rerank_and_filter_memories(
                    query,
                    hybrid_memories,
                    k,
                    session_id=session_id,
                    min_score=min_score,
                    min_similarity=min_similarity,
                )
        except Exception as e:
            logger.debug(f"Hybrid recall failed, falling back: {e}")
        
        # Fall back to vector-only if hybrid fails
        try:
            memories = self._recall_postgres(
                query,
                k,
                session_id,
                effective_user_id,
                time_window_days,
                min_score=min_score,
                min_similarity=min_similarity,
            )
            # Apply cross-encoder reranking for better precision
            if use_cross_encoder and len(memories) > 1:
                memories = self._rerank_with_cross_encoder(query, memories, top_k=k)
            return memories
        except Exception as e:
            logger.warning(f"PostgreSQL recall failed: {e}")

        # Ensure SQLite cache is loaded if available
        if self._sqlite_enabled and not self._memory_store:
            self._load_sqlite_cache()
        
        # Fall back to in-memory
        return self._recall_memory(
            query,
            k,
            session_id,
            effective_user_id,
            time_window_days,
            min_score=min_score,
            min_similarity=min_similarity,
        )
    
    def _recall_postgres(
        self,
        query,
        k,
        session_id,
        user_id,
        time_window_days,
        min_score: Optional[float] = None,
        min_similarity: Optional[float] = None,
    ) -> List[Dict]:
        """Recall from PostgreSQL with semantic search and temporal decay."""
        memories = []
        fetch_limit = min(
            max(k, k * self.recall_fetch_multiplier),
            self.recall_max_candidates,
        )
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Build query based on available features
            if self.use_pgvector:
                self._ensure_encoder()
            if self.encoder and self.use_pgvector:
                embedding = self.encoder.encode(query).tolist()
                
                # Candidate retrieval by semantic similarity, then rerank in Python.
                sql = """
                        SELECT 
                            id, session_id, user_id, query, response, context, 
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
                if user_id:
                    sql += " AND user_id = %s"
                    params.append(user_id)
                
                if time_window_days:
                    sql += " AND created_at > NOW() - (%s * INTERVAL '1 day')"
                    params.append(int(time_window_days))
                
                sql += " ORDER BY similarity DESC NULLS LAST, created_at DESC LIMIT %s"
                params.append(fetch_limit)
                
                cur.execute(sql, params)
            else:
                # Fall back to recency-based retrieval
                sql = """
                    SELECT 
                        id, session_id, user_id, query, response, context,
                        importance, emotional_valence, access_count,
                        created_at, accessed_at,
                        0.0 as similarity,
                        importance * exp(-0.01 * EXTRACT(EPOCH FROM (NOW() - created_at))/86400) as score
                    FROM conversations
                    WHERE 1=1
                """
                params = []
                
                if session_id:
                    sql += " AND session_id = %s"
                    params.append(session_id)
                if user_id:
                    sql += " AND user_id = %s"
                    params.append(user_id)
                
                if time_window_days:
                    sql += " AND created_at > NOW() - (%s * INTERVAL '1 day')"
                    params.append(int(time_window_days))
                
                sql += " ORDER BY created_at DESC LIMIT %s"
                params.append(fetch_limit)
                
                cur.execute(sql, params)
            
            raw_memories = [dict(m) for m in cur.fetchall()]
            memories = self._rerank_and_filter_memories(
                query,
                raw_memories,
                k,
                session_id=session_id,
                min_score=min_score,
                min_similarity=min_similarity,
            )
            
            # Update access times for recalled memories
            if memories:
                memory_ids = [m['id'] for m in memories]
                cur.execute("""
                    UPDATE conversations 
                    SET accessed_at = NOW(), access_count = access_count + 1
                    WHERE id = ANY(%s)
                """, (memory_ids,))
                self.conn.commit()
        
        return memories
    
    def _recall_memory(
        self,
        query,
        k,
        session_id,
        user_id,
        time_window_days,
        min_score: Optional[float] = None,
        min_similarity: Optional[float] = None,
    ) -> List[Dict]:
        """Recall from in-memory store with embedding-aware fallback matching."""
        query_lower = query.lower()
        query_words = set(query_lower.split())
        query_embedding = self._encode_text(query) if getattr(self, "embeddings_enabled", False) else None
        candidate_memories = getattr(self, "_hot_memory_cache", None) or self._memory_store
        
        scored_memories = []
        for memory in candidate_memories:
            # Filter by session if specified
            if session_id and memory.get('session_id') != session_id:
                continue
            memory_user_id = memory.get('user_id') or self.default_user_id
            if user_id and memory_user_id != user_id:
                continue
            
            # Filter by time window if specified
            if time_window_days:
                created = self._coerce_datetime(memory['created_at'])
                if datetime.now() - created > timedelta(days=time_window_days):
                    continue
            
            semantic_similarity = self._cosine_similarity(
                query_embedding,
                memory.get("query_embedding"),
            )

            # Simple word overlap similarity
            memory_words = set(memory['query'].lower().split())
            overlap = len(query_words & memory_words)
            lexical_similarity = overlap / max(len(query_words), 1)
            similarity = max(semantic_similarity, lexical_similarity)
            
            # Apply importance and temporal decay
            created = self._coerce_datetime(memory['created_at'])
            days_old = (datetime.now() - created).days
            decay = math.exp(-0.01 * days_old)
            
            score = memory['importance'] * decay * (0.35 + 0.45 * similarity + 0.20 * semantic_similarity)
            
            scored_memories.append({
                **memory,
                'similarity': semantic_similarity,
                'semantic_similarity': semantic_similarity,
                'lexical_overlap': lexical_similarity,
                'score': score
            })
        
        ranked = self._rerank_and_filter_memories(
            query,
            scored_memories,
            k,
            session_id=session_id,
            min_score=min_score,
            min_similarity=min_similarity,
        )
        
        # Update access counts
        for m in ranked:
            m['access_count'] = m.get('access_count', 0) + 1
            m['accessed_at'] = datetime.now().isoformat()
        
        return ranked
    
    def get_session_history(self, session_id: str, limit: int = 20, user_id: Optional[str] = None) -> List[Dict]:
        """Get conversation history for a specific session."""
        effective_user_id = self._normalize_user_id(user_id)
        if self.conn:
            try:
                with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT id, query, response, importance, created_at
                        FROM conversations
                        WHERE session_id = %s AND user_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (session_id, effective_user_id, limit))
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
                        user_col = self._sqlite_cols.get("user_id")
                        if user_col:
                            sql = f"""
                                SELECT {query_col} AS query, {response_col} AS response, {created_col} AS created_at
                                FROM conversations
                                WHERE {self._sqlite_cols.get("session_id")} = ?
                                  AND ({user_col} = ? OR {user_col} IS NULL)
                                ORDER BY {created_col} DESC
                                LIMIT ?
                            """
                            rows = conn.execute(sql, (session_id, effective_user_id, limit)).fetchall()
                        else:
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
            and (m.get('user_id') or self.default_user_id) == effective_user_id
        ][-limit:]
    
    def learn_preference(
        self,
        category: str,
        preference: str,
        confidence: float = 0.5,
        user_id: Optional[str] = None,
    ):
        """Learn a user preference."""
        effective_user_id = self._normalize_user_id(user_id)
        if self.conn:
            try:
                with self.conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO learned_preferences (user_id, category, preference, confidence)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (user_id, category, preference) DO UPDATE
                        SET confidence = (learned_preferences.confidence + %s) / 2,
                            updated_at = NOW()
                    """, (effective_user_id, category, preference, confidence, confidence))
                    self.conn.commit()
                    logger.debug(f"Learned preference: user_id={effective_user_id} {category}={preference}")
            except Exception as e:
                logger.warning(f"Learn preference failed: {e}")
        elif self._sqlite_enabled and "user_preferences" in self._sqlite_tables:
            try:
                key = f"{effective_user_id}::{category}:{preference}"
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
    
    def get_preferences(self, category: str = None, user_id: Optional[str] = None) -> List[Dict]:
        """Get learned preferences."""
        effective_user_id = self._normalize_user_id(user_id)
        if self.conn:
            try:
                with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if category:
                        cur.execute("""
                            SELECT user_id, category, preference, confidence, updated_at
                            FROM learned_preferences
                            WHERE user_id = %s AND category = %s
                            ORDER BY confidence DESC
                        """, (effective_user_id, category))
                    else:
                        cur.execute("""
                            SELECT user_id, category, preference, confidence, updated_at
                            FROM learned_preferences
                            WHERE user_id = %s
                            ORDER BY category, confidence DESC
                        """, (effective_user_id,))
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
                        uid = self.default_user_id
                        remainder = key
                        if "::" in key:
                            uid, remainder = key.split("::", 1)
                        if ":" in remainder:
                            cat, pref = remainder.split(":", 1)
                        else:
                            cat, pref = "general", remainder
                        if uid != effective_user_id:
                            continue
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
                            "user_id": uid,
                            "category": cat,
                            "preference": pref,
                            "confidence": confidence,
                            "updated_at": row["updated_at"]
                        })
                    return prefs
            except Exception as e:
                logger.warning(f"SQLite get preferences failed: {e}")

        return []

    def remember_record(
        self,
        record_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        *,
        scope: str = "",
        provenance: str = "",
        confidence: float = 0.5,
        verified_at: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[int]:
        """Store a typed memory record for durable bug/fix/decision recall."""
        record_type = (record_type or "repo_fact").strip().lower()
        if record_type not in DEFAULT_MEMORY_RECORD_TYPES:
            record_type = "repo_fact"
        content = (content or "").strip()
        if not content:
            return None

        effective_user_id = self._normalize_user_id(user_id)
        metadata = metadata or {}
        embedding = self._encode_text(content) if self.embeddings_enabled else None
        now_iso = datetime.now().isoformat()

        if self.conn:
            try:
                with self.conn.cursor() as cur:
                    if embedding and self.use_pgvector:
                        cur.execute("""
                            INSERT INTO memory_records
                            (user_id, record_type, content, scope, provenance, confidence, metadata, verified_at, embedding)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                        """, (
                            effective_user_id,
                            record_type,
                            content,
                            scope,
                            provenance,
                            confidence,
                            Json(metadata),
                            verified_at,
                            embedding,
                        ))
                    else:
                        cur.execute("""
                            INSERT INTO memory_records
                            (user_id, record_type, content, scope, provenance, confidence, metadata, verified_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                        """, (
                            effective_user_id,
                            record_type,
                            content,
                            scope,
                            provenance,
                            confidence,
                            Json(metadata),
                            verified_at,
                        ))
                    record_id = cur.fetchone()[0]
                    self.conn.commit()
                    return int(record_id)
            except Exception as e:
                logger.warning(f"PostgreSQL typed memory write failed: {e}")

        record = {
            "id": len(self._typed_records_store) + 1,
            "user_id": effective_user_id,
            "record_type": record_type,
            "content": content,
            "scope": scope,
            "provenance": provenance,
            "confidence": float(confidence),
            "metadata": metadata,
            "verified_at": verified_at,
            "embedding": embedding,
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        if self._sqlite_enabled and "memory_records" in self._sqlite_tables:
            try:
                conn = self._get_sqlite_conn()
                if conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO memory_records
                        (user_id, record_type, content, scope, provenance, confidence, metadata, verified_at, embedding, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        effective_user_id,
                        record_type,
                        content,
                        scope,
                        provenance,
                        float(confidence),
                        json.dumps(metadata),
                        verified_at,
                        self._serialize_embedding(embedding),
                        now_iso,
                        now_iso,
                    ))
                    conn.commit()
                    record["id"] = cur.lastrowid
                    conn.close()
            except Exception as e:
                logger.warning(f"SQLite typed memory write failed: {e}")

        self._typed_records_store.append(record)
        return int(record["id"])

    def get_records(
        self,
        record_type: Optional[str] = None,
        *,
        query: Optional[str] = None,
        scope: Optional[str] = None,
        limit: int = 10,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve typed memory records with optional query reranking."""
        effective_user_id = self._normalize_user_id(user_id)
        limit = max(1, int(limit or 10))
        query_embedding = self._encode_text(query) if (query and self.embeddings_enabled) else None
        records: List[Dict[str, Any]] = []

        if self.conn:
            try:
                with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                    params: List[Any] = [effective_user_id]
                    if query_embedding and self.use_pgvector:
                        sql = """
                            SELECT id, user_id, record_type, content, scope, provenance, confidence, metadata, verified_at, created_at, updated_at,
                                   1 - (embedding <=> %s::vector) AS similarity
                            FROM memory_records
                            WHERE user_id = %s
                        """
                        params = [query_embedding, effective_user_id]
                    else:
                        sql = """
                            SELECT id, user_id, record_type, content, scope, provenance, confidence, metadata, verified_at, created_at, updated_at,
                                   0.0 AS similarity
                            FROM memory_records
                            WHERE user_id = %s
                        """
                    if record_type:
                        sql += " AND record_type = %s"
                        params.append(record_type)
                    if scope:
                        sql += " AND scope = %s"
                        params.append(scope)
                    sql += " ORDER BY updated_at DESC LIMIT %s"
                    params.append(max(limit * 3, 25))
                    cur.execute(sql, params)
                    records = [dict(row) for row in cur.fetchall()]
            except Exception as e:
                logger.warning(f"PostgreSQL typed memory read failed: {e}")

        if not records and self._sqlite_enabled and "memory_records" in self._sqlite_tables:
            try:
                conn = self._get_sqlite_conn()
                if conn:
                    sql = """
                        SELECT id, user_id, record_type, content, scope, provenance, confidence, metadata, verified_at, embedding, created_at, updated_at
                        FROM memory_records
                        WHERE user_id = ?
                    """
                    params: List[Any] = [effective_user_id]
                    if record_type:
                        sql += " AND record_type = ?"
                        params.append(record_type)
                    if scope:
                        sql += " AND scope = ?"
                        params.append(scope)
                    sql += " ORDER BY updated_at DESC LIMIT ?"
                    params.append(max(limit * 3, 25))
                    rows = conn.execute(sql, params).fetchall()
                    conn.close()
                    for row in rows:
                        metadata = {}
                        if row["metadata"]:
                            try:
                                metadata = json.loads(row["metadata"])
                            except Exception:
                                metadata = {}
                        records.append({
                            "id": row["id"],
                            "user_id": row["user_id"],
                            "record_type": row["record_type"],
                            "content": row["content"],
                            "scope": row["scope"],
                            "provenance": row["provenance"],
                            "confidence": row["confidence"],
                            "metadata": metadata,
                            "verified_at": row["verified_at"],
                            "embedding": self._deserialize_embedding(row["embedding"]),
                            "created_at": row["created_at"],
                            "updated_at": row["updated_at"],
                        })
            except Exception as e:
                logger.warning(f"SQLite typed memory read failed: {e}")

        if not records:
            records = [
                dict(record) for record in self._typed_records_store
                if record.get("user_id") == effective_user_id
                and (not record_type or record.get("record_type") == record_type)
                and (not scope or record.get("scope") == scope)
            ]

        if query:
            query_lower = query.lower()
            for record in records:
                text = f"{record.get('content', '')} {json.dumps(record.get('metadata', {}), sort_keys=True)}"
                semantic_similarity = float(record.get("similarity") or 0.0)
                if semantic_similarity <= 0.0:
                    semantic_similarity = self._cosine_similarity(query_embedding, record.get("embedding"))
                lexical_overlap = self._lexical_overlap(query_lower, text.lower())
                record["similarity"] = semantic_similarity
                record["score"] = (0.65 * semantic_similarity) + (0.25 * lexical_overlap) + (0.10 * float(record.get("confidence", 0.5)))
            records.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        else:
            records.sort(
                key=lambda item: (
                    float(item.get("confidence", 0.0)),
                    self._coerce_datetime(item.get("updated_at")).timestamp(),
                ),
                reverse=True,
            )

        return records[:limit]

    def remember_decision(self, content: str, rationale: str = "", **kwargs) -> Optional[int]:
        metadata = dict(kwargs.pop("metadata", {}) or {})
        if rationale:
            metadata["rationale"] = rationale
        return self.remember_record("decision", content, metadata=metadata, **kwargs)

    def remember_bug(self, symptom: str, **kwargs) -> Optional[int]:
        metadata = dict(kwargs.pop("metadata", {}) or {})
        return self.remember_record("bug", symptom, metadata=metadata, **kwargs)

    def remember_fix(self, failure_signature: str, fix_command: str, **kwargs) -> Optional[int]:
        metadata = dict(kwargs.pop("metadata", {}) or {})
        metadata.setdefault("failure_signature", failure_signature)
        metadata.setdefault("fix_command", fix_command)
        content = f"{failure_signature}\n{fix_command}".strip()
        return self.remember_record("fix_recipe", content, metadata=metadata, **kwargs)

    def remember_verification_recipe(self, task_type: str, proof_commands: List[str], **kwargs) -> Optional[int]:
        metadata = dict(kwargs.pop("metadata", {}) or {})
        metadata.setdefault("task_type", task_type)
        metadata.setdefault("proof_commands", proof_commands)
        content = f"{task_type}: {'; '.join(proof_commands)}"
        return self.remember_record("verification_recipe", content, metadata=metadata, **kwargs)

    def remember_failure_event(
        self,
        tool_name: str,
        error_message: str,
        *,
        command: str = "",
        exit_code: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Optional[int]:
        payload = dict(metadata or {})
        payload.update({
            "tool_name": tool_name,
            "command": command,
            "exit_code": exit_code,
        })
        content = f"{tool_name}: {error_message}".strip()
        return self.remember_record(
            "failure_event",
            content,
            metadata=payload,
            provenance="tool_runtime",
            user_id=user_id,
        )
    
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

                    cur.execute("SELECT COUNT(*) FROM memory_records")
                    stats['typed_records'] = cur.fetchone()[0]
                    
            except Exception as e:
                stats['error'] = str(e)
        elif self._sqlite_enabled:
            try:
                conn = self._get_sqlite_conn()
                if conn:
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) FROM conversations")
                    stats['total_memories'] = cur.fetchone()[0]
                    if "memory_records" in self._sqlite_tables:
                        cur.execute("SELECT COUNT(*) FROM memory_records")
                        stats['typed_records'] = cur.fetchone()[0]
                    conn.close()
            except Exception as e:
                stats['error'] = str(e)
        else:
            stats['total_memories'] = len(self._memory_store)
            stats['avg_importance'] = sum(m['importance'] for m in self._memory_store) / max(len(self._memory_store), 1)
            stats['typed_records'] = len(self._typed_records_store)
        stats['hot_memory_cache'] = len(self._hot_memory_cache)
        
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
                    status['details']['hot_memory_cache'] = len(self._hot_memory_cache)
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
                    status['details']['hot_memory_cache'] = len(self._hot_memory_cache)
            except Exception as e:
                status['details']['error'] = str(e)
        else:
            status['healthy'] = True
            status['backend'] = 'memory'
            status['details']['memory_count'] = len(self._memory_store)
            status['details']['hot_memory_cache'] = len(self._hot_memory_cache)
        
        return status


# Singleton instance
_memory_instance: Optional[PostgresMemory] = None


def get_memory() -> PostgresMemory:
    """Get global memory instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = PostgresMemory()
    return _memory_instance
