#!/usr/bin/env python3
"""
Semantic Cache - Caches responses using vector similarity
Uses existing ChromaDB if available, else simple in-memory cache
"""
import logging
import time
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger("roxy.cache")

ROXY_DIR = Path.home() / ".roxy"
CACHE_DIR = ROXY_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# In-memory cache
_memory_cache: Dict[str, Dict[str, Any]] = {}
_cache_ttl = 3600  # 1 hour default TTL


class SemanticCache:
    """Semantic cache using ChromaDB or in-memory fallback"""
    
    def __init__(self, ttl: int = 3600):
        self.ttl = ttl
        self.chroma_client = None
        self.chroma_collection = None
        self._init_chroma()
    
    def _init_chroma(self):
        """Initialize ChromaDB for semantic caching"""
        try:
            import chromadb
            chroma_path = ROXY_DIR / "chroma_db"
            if chroma_path.exists():
                self.chroma_client = chromadb.PersistentClient(path=str(chroma_path))
                try:
                    self.chroma_collection = self.chroma_client.get_or_create_collection(
                        name="roxy_cache",
                        metadata={"description": "ROXY response cache"}
                    )
                    logger.debug("Using ChromaDB for semantic caching")
                except Exception as e:
                    logger.debug(f"ChromaDB collection creation failed: {e}")
        except ImportError:
            logger.debug("ChromaDB not available, using in-memory cache")
        except Exception as e:
            logger.debug(f"ChromaDB initialization failed: {e}, using in-memory cache")
    
    def _get_query_hash(self, query: str) -> str:
        """Get hash of query for exact match lookup"""
        return hashlib.md5(query.encode()).hexdigest()
    
    def _get_cache_key(self, query: str) -> str:
        """Get cache key for query"""
        return f"cache_{self._get_query_hash(query)}"
    
    def get(self, query: str, similarity_threshold: float = 0.85) -> Optional[Dict[str, Any]]:
        """Get cached response for query"""
        # First try exact match
        cache_key = self._get_cache_key(query)
        
        # Check in-memory cache
        if cache_key in _memory_cache:
            entry = _memory_cache[cache_key]
            if time.time() - entry["timestamp"] < self.ttl:
                logger.debug(f"Cache hit (exact match): {query[:50]}")
                return entry["response"]
            else:
                # Expired
                del _memory_cache[cache_key]
        
        # Try semantic similarity if ChromaDB available
        if self.chroma_collection:
            try:
                # Get embedding for query using DefaultEmbeddingFunction (384-dim, matches collection)
                from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
                ef = DefaultEmbeddingFunction()
                embedding = ef([query])[0]
                    
                    # Query cache collection
                    results = self.chroma_collection.query(
                        query_embeddings=[embedding],
                        n_results=1
                    )
                    
                    if results and results["documents"] and results["distances"]:
                        distance = results["distances"][0][0]
                        similarity = 1.0 - distance
                        
                        if similarity >= similarity_threshold:
                            cached_query = results["metadatas"][0][0].get("query", "")
                            cached_response = results["documents"][0][0]
                            cached_timestamp = results["metadatas"][0][0].get("timestamp", 0)
                            
                            # Check TTL
                            if time.time() - cached_timestamp < self.ttl:
                                logger.debug(f"Cache hit (semantic, similarity={similarity:.2f}): {query[:50]}")
                                return {
                                    "response": cached_response,
                                    "similarity": similarity,
                                    "cached_query": cached_query
                                }
            except Exception as e:
                logger.debug(f"Semantic cache lookup failed: {e}")
        
        return None
    
    def set(self, query: str, response: str):
        """Cache response for query"""
        cache_key = self._get_cache_key(query)
        timestamp = time.time()
        
        # Store in memory
        _memory_cache[cache_key] = {
            "response": response,
            "timestamp": timestamp,
            "query": query
        }
        
        # Store in ChromaDB if available
        if self.chroma_collection:
            try:
                # Get embedding using DefaultEmbeddingFunction (384-dim, matches collection)
                from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
                ef = DefaultEmbeddingFunction()
                embedding = ef([query])[0]
                    
                    # Store in cache collection
                    doc_id = f"cache_{self._get_query_hash(query)}_{int(timestamp)}"
                    self.chroma_collection.add(
                        ids=[doc_id],
                        embeddings=[embedding],
                        documents=[response],
                        metadatas=[{
                            "query": query,
                            "timestamp": timestamp,
                            "response_length": len(response)
                        }]
                    )
                    logger.debug(f"Cached response: {query[:50]}")
            except Exception as e:
                logger.debug(f"ChromaDB cache storage failed: {e}")
    
    def clear(self, older_than: int = None):
        """Clear cache entries"""
        if older_than:
            # Clear expired entries
            current_time = time.time()
            expired_keys = [
                key for key, entry in _memory_cache.items()
                if current_time - entry["timestamp"] > older_than
            ]
            for key in expired_keys:
                del _memory_cache[key]
            logger.info(f"Cleared {len(expired_keys)} expired cache entries")
        else:
            # Clear all
            _memory_cache.clear()
            logger.info("Cleared all cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "memory_entries": len(_memory_cache),
            "ttl": self.ttl,
            "chromadb_available": self.chroma_collection is not None
        }


# Global cache instance
_cache_instance = None


def get_cache(ttl: int = 3600) -> SemanticCache:
    """Get global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SemanticCache(ttl=ttl)
    return _cache_instance














