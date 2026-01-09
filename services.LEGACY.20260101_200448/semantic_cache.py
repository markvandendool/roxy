#!/usr/bin/env python3
"""
ROXY Semantic Cache - 10-100x faster responses for similar queries
Industry Standard: GPTCache, Semantic Kernel caching
Vector similarity search for cached responses
"""
import logging
import hashlib
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import chromadb
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.cache')

class SemanticCache:
    """Semantic caching layer for ROXY responses"""
    
    def __init__(self, cache_dir: str = "/home/mark/.roxy/data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.client = None
        self.collection = None
        self.ttl_hours = 24  # Cache TTL
        self.similarity_threshold = 0.85  # Minimum similarity to use cache
        self._init_chromadb()
    
    def _init_chromadb(self):
        """Initialize ChromaDB for semantic cache"""
        try:
            cache_db_path = str(self.cache_dir / "semantic_cache")
            self.client = chromadb.PersistentClient(path=cache_db_path)
            self.collection = self.client.get_or_create_collection(
                name="roxy_cache",
                metadata={"description": "ROXY semantic response cache"}
            )
            logger.info("✅ Semantic cache initialized")
        except Exception as e:
            logger.warning(f"Semantic cache unavailable: {e}")
            self.client = None
    
    def _get_cache_key(self, query: str, context: Dict = None) -> str:
        """Generate cache key from query and context"""
        key_data = {
            'query': query.lower().strip(),
            'context': context or {}
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def get(self, query: str, context: Dict = None) -> Optional[str]:
        """Get cached response if similar query exists"""
        if not self.client:
            return None
        
        try:
            # Search for similar queries
            results = self.collection.query(
                query_texts=[query],
                n_results=1
            )
            
            if results['ids'] and len(results['ids'][0]) > 0:
                # Check similarity
                if 'distances' in results and results['distances']:
                    distance = results['distances'][0][0]
                    similarity = 1.0 - distance
                    
                    if similarity >= self.similarity_threshold:
                        # Get cached response
                        cached_id = results['ids'][0][0]
                        cached_data = self.collection.get(ids=[cached_id])
                        
                        if cached_data['metadatas']:
                            metadata = cached_data['metadatas'][0]
                            
                            # Check TTL
                            cached_time = datetime.fromisoformat(metadata.get('timestamp', '2000-01-01'))
                            if datetime.now() - cached_time < timedelta(hours=self.ttl_hours):
                                response = metadata.get('response', '')
                                logger.info(f"✅ Cache hit: similarity={similarity:.2f}")
                                return response
                            else:
                                # Expired, remove from cache
                                self.collection.delete(ids=[cached_id])
                                logger.debug(f"Cache expired for query: {query[:50]}")
            
            return None
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
            return None
    
    async def set(self, query: str, response: str, context: Dict = None):
        """Cache a response"""
        if not self.client:
            return
        
        try:
            cache_key = self._get_cache_key(query, context)
            
            # Store in cache
            self.collection.add(
                documents=[query],
                ids=[cache_key],
                metadatas=[{
                    'response': response,
                    'query': query,
                    'timestamp': datetime.now().isoformat(),
                    'context': json.dumps(context or {})
                }]
            )
            
            logger.debug(f"Cached response for query: {query[:50]}")
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
    
    def clear_expired(self):
        """Clear expired cache entries"""
        if not self.client:
            return
        
        try:
            # Get all entries
            all_data = self.collection.get()
            
            expired_ids = []
            for i, metadata in enumerate(all_data.get('metadatas', [])):
                timestamp_str = metadata.get('timestamp', '2000-01-01')
                try:
                    cached_time = datetime.fromisoformat(timestamp_str)
                    if datetime.now() - cached_time >= timedelta(hours=self.ttl_hours):
                        expired_ids.append(all_data['ids'][i])
                except:
                    expired_ids.append(all_data['ids'][i])
            
            if expired_ids:
                self.collection.delete(ids=expired_ids)
                logger.info(f"Cleared {len(expired_ids)} expired cache entries")
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        if not self.client:
            return {'enabled': False}
        
        try:
            count = self.collection.count()
            return {
                'enabled': True,
                'cached_queries': count,
                'ttl_hours': self.ttl_hours,
                'similarity_threshold': self.similarity_threshold
            }
        except:
            return {'enabled': False}


# Global cache instance
_cache: Optional[SemanticCache] = None

def get_semantic_cache() -> SemanticCache:
    """Get global semantic cache instance"""
    global _cache
    if _cache is None:
        _cache = SemanticCache()
    return _cache

