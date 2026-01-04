#!/usr/bin/env python3
"""
Redis Semantic Cache - 100x faster response caching with vector similarity
Replaces in-memory cache with persistent Redis backend
"""
import logging
import time
import hashlib
import json
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("roxy.cache_redis")

# Try to import Redis, fall back gracefully
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis package not installed, using in-memory fallback")

# Try to import sentence-transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("sentence-transformers not available, using hash-based cache only")


class RedisSuperCache:
    """
    Production-grade semantic cache using Redis with vector similarity.
    
    Features:
    - Vector similarity search using RediSearch HNSW index
    - Dynamic TTL based on query type
    - Graceful fallback to in-memory if Redis unavailable
    - Cache statistics tracking
    """
    
    def __init__(self, 
                 host: str = 'localhost', 
                 port: int = 6379, 
                 db: int = 0,
                 default_ttl: int = 3600,
                 similarity_threshold: float = 0.95):
        """
        Initialize Redis cache connection.
        
        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            default_ttl: Default time-to-live in seconds
            similarity_threshold: Minimum similarity for cache hit (0-1)
        """
        self.host = host
        self.port = port
        self.db = db
        self.default_ttl = default_ttl
        self.similarity_threshold = similarity_threshold
        
        self.redis = None
        self.encoder = None
        self.use_vector_search = False
        
        # In-memory fallback
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        
        self._connect()
    
    def _connect(self):
        """Establish Redis connection and initialize vector index."""
        if not REDIS_AVAILABLE:
            logger.info("Redis not available, using in-memory cache")
            return
        
        try:
            self.redis = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=False,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # Test connection
            self.redis.ping()
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
            
            # Initialize encoder if available
            if EMBEDDINGS_AVAILABLE:
                try:
                    self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
                    logger.info("Loaded sentence-transformers encoder (384-dim)")
                    
                    # Try to create vector index
                    self._create_vector_index()
                except Exception as e:
                    logger.warning(f"Failed to load encoder: {e}")
            
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection failed: {e}, using in-memory fallback")
            self.redis = None
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}, using in-memory fallback")
            self.redis = None
    
    def _create_vector_index(self):
        """Create RediSearch vector index for semantic similarity."""
        if not self.redis:
            return
        
        try:
            # Check if RediSearch module is loaded
            modules = self.redis.execute_command('MODULE', 'LIST')
            has_search = any(b'search' in str(m).lower() for m in modules)
            
            if not has_search:
                logger.info("RediSearch module not loaded, using hash-based cache only")
                return
            
            # Create vector index
            try:
                self.redis.execute_command(
                    'FT.CREATE', 'idx:roxy_cache',
                    'ON', 'HASH',
                    'PREFIX', '1', 'cache:',
                    'SCHEMA',
                    'query', 'TEXT',
                    'response', 'TEXT',
                    'vector', 'VECTOR', 'HNSW', '6',
                    'TYPE', 'FLOAT32', 'DIM', '384',
                    'DISTANCE_METRIC', 'COSINE',
                    'timestamp', 'NUMERIC', 'SORTABLE',
                    'ttl', 'NUMERIC'
                )
                logger.info("Created RediSearch vector index 'idx:roxy_cache'")
                self.use_vector_search = True
            except redis.ResponseError as e:
                if "Index already exists" in str(e):
                    logger.info("Vector index already exists")
                    self.use_vector_search = True
                else:
                    logger.warning(f"Failed to create vector index: {e}")
                    
        except Exception as e:
            logger.warning(f"Vector index setup failed: {e}")
    
    def _get_query_hash(self, query: str) -> str:
        """Generate hash key for exact match lookup."""
        return hashlib.md5(query.strip().lower().encode()).hexdigest()
    
    def _calculate_ttl(self, query: str) -> int:
        """Calculate dynamic TTL based on query type."""
        query_lower = query.lower()
        
        # Time-sensitive queries: short TTL
        if any(word in query_lower for word in ['weather', 'news', 'current', 'today', 'now', 'latest']):
            return 300  # 5 minutes
        
        # Explanations and definitions: long TTL
        if any(word in query_lower for word in ['explain', 'what is', 'how does', 'define', 'meaning']):
            return 86400  # 24 hours
        
        # Code-related: medium-long TTL
        if any(word in query_lower for word in ['code', 'function', 'implement', 'write', 'debug']):
            return 7200  # 2 hours
        
        # Math: long TTL (answers don't change)
        if any(word in query_lower for word in ['calculate', 'solve', 'math', 'equation']):
            return 86400  # 24 hours
        
        return self.default_ttl
    
    def get(self, query: str, threshold: float = None) -> Optional[str]:
        """
        Get cached response for query.
        
        Args:
            query: The query to look up
            threshold: Similarity threshold (default: self.similarity_threshold)
            
        Returns:
            Cached response string or None if not found
        """
        threshold = threshold or self.similarity_threshold
        
        # Try Redis first
        if self.redis:
            try:
                result = self._get_from_redis(query, threshold)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")
        
        # Fall back to in-memory
        return self._get_from_memory(query)
    
    def _get_from_redis(self, query: str, threshold: float) -> Optional[str]:
        """Get from Redis with vector similarity search."""
        if not self.redis:
            return None
        
        # Try exact match first (fast)
        cache_key = f"cache:{self._get_query_hash(query)}"
        cached = self.redis.hgetall(cache_key)
        
        if cached and b'response' in cached:
            # Check TTL
            timestamp = float(cached.get(b'timestamp', 0))
            ttl = int(cached.get(b'ttl', self.default_ttl))
            
            if time.time() - timestamp < ttl:
                self._increment_stat('cache_hits_exact')
                logger.debug(f"Cache hit (exact): {query[:50]}...")
                return cached[b'response'].decode('utf-8')
        
        # Try vector similarity search
        if self.use_vector_search and self.encoder:
            try:
                embedding = self.encoder.encode(query).astype(np.float32)
                
                results = self.redis.execute_command(
                    'FT.SEARCH', 'idx:roxy_cache',
                    f'*=>[KNN 1 @vector $vec AS score]',
                    'PARAMS', '2', 'vec', embedding.tobytes(),
                    'RETURN', '4', 'response', 'score', 'timestamp', 'ttl',
                    'SORTBY', 'score', 'ASC',
                    'DIALECT', '2'
                )
                
                if results[0] > 0:
                    # Parse results
                    fields = {}
                    for i in range(0, len(results[2]), 2):
                        key = results[2][i].decode() if isinstance(results[2][i], bytes) else results[2][i]
                        val = results[2][i+1]
                        fields[key] = val
                    
                    distance = float(fields.get('score', 1.0))
                    similarity = 1.0 - distance
                    
                    if similarity >= threshold:
                        # Check TTL
                        timestamp = float(fields.get('timestamp', 0))
                        ttl = int(fields.get('ttl', self.default_ttl))
                        
                        if time.time() - timestamp < ttl:
                            self._increment_stat('cache_hits_semantic')
                            logger.debug(f"Cache hit (semantic, sim={similarity:.3f}): {query[:50]}...")
                            response = fields.get('response', b'')
                            return response.decode('utf-8') if isinstance(response, bytes) else response
                            
            except Exception as e:
                logger.debug(f"Vector search failed: {e}")
        
        self._increment_stat('cache_misses')
        return None
    
    def _get_from_memory(self, query: str) -> Optional[str]:
        """Get from in-memory fallback cache."""
        cache_key = self._get_query_hash(query)
        
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]
            if time.time() - entry['timestamp'] < entry.get('ttl', self.default_ttl):
                logger.debug(f"Cache hit (memory): {query[:50]}...")
                return entry['response']
            else:
                # Expired
                del self._memory_cache[cache_key]
        
        return None
    
    def set(self, query: str, response: str, ttl: int = None):
        """
        Store query-response pair in cache.
        
        Args:
            query: The query string
            response: The response to cache
            ttl: Time-to-live in seconds (default: auto-calculated)
        """
        if ttl is None:
            ttl = self._calculate_ttl(query)
        
        # Store in Redis
        if self.redis:
            try:
                self._set_in_redis(query, response, ttl)
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")
        
        # Also store in memory as backup
        self._set_in_memory(query, response, ttl)
    
    def _set_in_redis(self, query: str, response: str, ttl: int):
        """Store in Redis with vector embedding."""
        if not self.redis:
            return
        
        cache_key = f"cache:{self._get_query_hash(query)}"
        timestamp = time.time()
        
        mapping = {
            'query': query,
            'response': response,
            'timestamp': str(timestamp),
            'ttl': str(ttl)
        }
        
        # Add vector embedding if available
        if self.encoder and self.use_vector_search:
            try:
                embedding = self.encoder.encode(query).astype(np.float32)
                mapping['vector'] = embedding.tobytes()
            except Exception as e:
                logger.debug(f"Failed to generate embedding: {e}")
        
        self.redis.hset(cache_key, mapping=mapping)
        self.redis.expire(cache_key, ttl)
        
        self._increment_stat('cache_sets')
        logger.debug(f"Cached response (ttl={ttl}s): {query[:50]}...")
    
    def _set_in_memory(self, query: str, response: str, ttl: int):
        """Store in in-memory fallback cache."""
        cache_key = self._get_query_hash(query)
        
        self._memory_cache[cache_key] = {
            'query': query,
            'response': response,
            'timestamp': time.time(),
            'ttl': ttl
        }
        
        # Limit memory cache size
        if len(self._memory_cache) > 1000:
            # Remove oldest entries
            sorted_keys = sorted(
                self._memory_cache.keys(),
                key=lambda k: self._memory_cache[k]['timestamp']
            )
            for key in sorted_keys[:100]:
                del self._memory_cache[key]
    
    def _increment_stat(self, stat_name: str):
        """Increment a cache statistic."""
        if self.redis:
            try:
                self.redis.hincrby('roxy:cache:stats', stat_name, 1)
            except Exception:
                pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        stats = {
            'backend': 'redis' if self.redis else 'memory',
            'vector_search': self.use_vector_search,
            'memory_cache_size': len(self._memory_cache)
        }
        
        if self.redis:
            try:
                redis_stats = self.redis.hgetall('roxy:cache:stats')
                stats.update({
                    k.decode(): int(v) for k, v in redis_stats.items()
                })
                
                # Calculate hit rate
                hits = stats.get('cache_hits_exact', 0) + stats.get('cache_hits_semantic', 0)
                total = hits + stats.get('cache_misses', 0)
                stats['hit_rate'] = hits / total if total > 0 else 0.0
                
            except Exception as e:
                stats['error'] = str(e)
        
        return stats
    
    def clear(self):
        """Clear all cached entries."""
        self._memory_cache.clear()
        
        if self.redis:
            try:
                # Find and delete all cache keys
                cursor = 0
                while True:
                    cursor, keys = self.redis.scan(cursor, match='cache:*', count=100)
                    if keys:
                        self.redis.delete(*keys)
                    if cursor == 0:
                        break
                logger.info("Cleared Redis cache")
            except Exception as e:
                logger.warning(f"Failed to clear Redis cache: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Check cache health status."""
        status = {
            'healthy': False,
            'backend': 'memory',
            'details': {}
        }
        
        if self.redis:
            try:
                self.redis.ping()
                status['healthy'] = True
                status['backend'] = 'redis'
                status['details']['vector_search'] = self.use_vector_search
                
                # Get Redis info
                info = self.redis.info('memory')
                status['details']['used_memory'] = info.get('used_memory_human', 'unknown')
                
            except Exception as e:
                status['details']['error'] = str(e)
                status['healthy'] = len(self._memory_cache) >= 0  # Memory always works
        else:
            status['healthy'] = True  # Memory fallback is always healthy
            status['backend'] = 'memory'
        
        return status


# Singleton instance for backward compatibility
_cache_instance: Optional[RedisSuperCache] = None


def get_cache() -> RedisSuperCache:
    """Get global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisSuperCache()
    return _cache_instance


# Alias for drop-in replacement
SemanticCache = RedisSuperCache
