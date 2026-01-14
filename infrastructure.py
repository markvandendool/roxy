#!/usr/bin/env python3
"""
ROXY Infrastructure Integration - Wires Redis, PostgreSQL, NATS, Expert Router
Provides unified interface for all infrastructure services
"""
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("roxy.infrastructure")

ROXY_DIR = Path.home() / ".roxy"
sys.path.insert(0, str(ROXY_DIR))

# Infrastructure availability flags
REDIS_CACHE = None
POSTGRES_MEMORY = None
EXPERT_ROUTER = None
EVENT_STREAM = None
FEEDBACK_COLLECTOR = None

# Initialize flags
_initialized = False


def initialize_infrastructure() -> Dict[str, bool]:
    """
    Initialize all infrastructure components.
    
    Returns:
        Dict of component -> availability
    """
    global REDIS_CACHE, POSTGRES_MEMORY, EXPERT_ROUTER, EVENT_STREAM, FEEDBACK_COLLECTOR, _initialized
    
    if _initialized:
        return get_infrastructure_status()
    
    status = {}
    
    # Initialize Redis Cache
    try:
        from cache_redis import RedisSuperCache
        REDIS_CACHE = RedisSuperCache()
        status['redis_cache'] = REDIS_CACHE.health_check().get('healthy', False)
        logger.info(f"✅ Redis cache initialized (backend: {REDIS_CACHE.health_check().get('backend')})")
    except Exception as e:
        logger.warning(f"⚠️ Redis cache unavailable: {e}")
        status['redis_cache'] = False
    
    # Initialize PostgreSQL Memory
    try:
        from memory_postgres import PostgresMemory
        POSTGRES_MEMORY = PostgresMemory()
        status['postgres_memory'] = POSTGRES_MEMORY.health_check().get('healthy', False)
        logger.info(f"✅ PostgreSQL memory initialized (backend: {POSTGRES_MEMORY.health_check().get('backend')})")
    except Exception as e:
        logger.warning(f"⚠️ PostgreSQL memory unavailable: {e}")
        status['postgres_memory'] = False
    
    # Initialize Expert Router
    try:
        from expert_router import ExpertRouterSync
        EXPERT_ROUTER = ExpertRouterSync()
        status['expert_router'] = True
        logger.info("✅ Expert router initialized")
    except Exception as e:
        logger.warning(f"⚠️ Expert router unavailable: {e}")
        status['expert_router'] = False
    
    # Initialize Event Stream
    try:
        from event_stream import EventStreamSync
        EVENT_STREAM = EventStreamSync()
        connected = EVENT_STREAM.connect()
        status['event_stream'] = connected
        if connected:
            logger.info("✅ NATS event stream connected")
        else:
            logger.info("⚠️ NATS unavailable, using event buffer")
    except Exception as e:
        logger.warning(f"⚠️ Event stream unavailable: {e}")
        status['event_stream'] = False
    
    # Initialize Feedback Collector
    try:
        from feedback import FeedbackCollector
        FEEDBACK_COLLECTOR = FeedbackCollector()
        status['feedback'] = True
        logger.info("✅ Feedback collector initialized")
    except Exception as e:
        logger.warning(f"⚠️ Feedback collector unavailable: {e}")
        status['feedback'] = False
    
    _initialized = True
    return status


def get_infrastructure_status() -> Dict[str, Any]:
    """Get detailed infrastructure status."""
    status = {
        'initialized': _initialized,
        'components': {}
    }
    
    if REDIS_CACHE:
        status['components']['redis_cache'] = REDIS_CACHE.health_check()
    else:
        status['components']['redis_cache'] = {'healthy': False, 'error': 'Not initialized'}
    
    if POSTGRES_MEMORY:
        status['components']['postgres_memory'] = POSTGRES_MEMORY.health_check()
    else:
        status['components']['postgres_memory'] = {'healthy': False, 'error': 'Not initialized'}
    
    if EXPERT_ROUTER:
        status['components']['expert_router'] = EXPERT_ROUTER.health_check()
    else:
        status['components']['expert_router'] = {'healthy': False, 'error': 'Not initialized'}
    
    if EVENT_STREAM:
        status['components']['event_stream'] = EVENT_STREAM.health_check()
    else:
        status['components']['event_stream'] = {'healthy': False, 'error': 'Not initialized'}
    
    if FEEDBACK_COLLECTOR:
        status['components']['feedback'] = {
            'healthy': True,
            'stats': FEEDBACK_COLLECTOR.get_feedback_stats()
        }
    else:
        status['components']['feedback'] = {'healthy': False, 'error': 'Not initialized'}
    
    return status


def get_cache():
    """Get cache instance (Redis with fallback)."""
    global REDIS_CACHE
    
    if REDIS_CACHE is None:
        try:
            from cache_redis import RedisSuperCache
            REDIS_CACHE = RedisSuperCache()
        except Exception as e:
            logger.warning(f"Cache initialization failed: {e}")
            # Return a minimal fallback
            from cache import SemanticCache
            return SemanticCache()
    
    return REDIS_CACHE


def get_memory():
    """Get memory instance (PostgreSQL with fallback)."""
    global POSTGRES_MEMORY
    
    if POSTGRES_MEMORY is None:
        try:
            from memory_postgres import PostgresMemory
            POSTGRES_MEMORY = PostgresMemory()
        except Exception as e:
            logger.warning(f"Memory initialization failed: {e}")
            return None
    
    return POSTGRES_MEMORY


def get_router():
    """Get expert router instance."""
    global EXPERT_ROUTER
    
    if EXPERT_ROUTER is None:
        try:
            from expert_router import ExpertRouterSync
            EXPERT_ROUTER = ExpertRouterSync()
        except Exception as e:
            logger.warning(f"Router initialization failed: {e}")
            return None
    
    return EXPERT_ROUTER


def get_event_stream():
    """Get event stream instance."""
    global EVENT_STREAM
    
    if EVENT_STREAM is None:
        try:
            from event_stream import EventStreamSync
            EVENT_STREAM = EventStreamSync()
            EVENT_STREAM.connect()
        except Exception as e:
            logger.warning(f"Event stream initialization failed: {e}")
            return None
    
    return EVENT_STREAM


def get_feedback():
    """Get feedback collector instance."""
    global FEEDBACK_COLLECTOR
    
    if FEEDBACK_COLLECTOR is None:
        try:
            from feedback import FeedbackCollector
            FEEDBACK_COLLECTOR = FeedbackCollector()
        except Exception as e:
            logger.warning(f"Feedback initialization failed: {e}")
            return None
    
    return FEEDBACK_COLLECTOR


# High-level convenience functions

def cache_query(query: str, response: str, metadata: Optional[Dict[str, Any]] = None, ttl: int = None):
    """Cache a query-response pair with metadata preserved."""
    cache = get_cache()
    if cache:
        try:
            payload = {
                "response": response,
                "metadata": metadata or {},
                "cached_at": datetime.utcnow().isoformat()
            }
            cache.set(query, json.dumps(payload))
        except Exception as e:
            logger.debug(f"Cache set failed: {e}")


def _normalize_cached_payload(raw_value: Any) -> Optional[Dict[str, Any]]:
    """Normalize cache backend return values into a structured payload."""
    if raw_value is None:
        return None

    if isinstance(raw_value, dict):
        payload = {
            "response": raw_value.get("response", ""),
            "metadata": raw_value.get("metadata", {}),
            "similarity": raw_value.get("similarity"),
            "cached_query": raw_value.get("cached_query"),
        }
        if "cached_at" in raw_value:
            payload["cached_at"] = raw_value["cached_at"]
        return payload

    if isinstance(raw_value, str):
        try:
            decoded = json.loads(raw_value)
            if isinstance(decoded, dict) and "response" in decoded:
                return {
                    "response": decoded.get("response", ""),
                    "metadata": decoded.get("metadata", {}),
                    "cached_at": decoded.get("cached_at"),
                    "similarity": decoded.get("similarity"),
                    "cached_query": decoded.get("cached_query"),
                }
        except json.JSONDecodeError:
            pass
        return {"response": raw_value, "metadata": {}}

    return {"response": str(raw_value), "metadata": {}}


def get_cached_response(query: str) -> Optional[Dict[str, Any]]:
    """Get cached response for query."""
    cache = get_cache()
    if cache:
        try:
            raw_value = cache.get(query)
            return _normalize_cached_payload(raw_value)
        except Exception as e:
            logger.debug(f"Cache get failed: {e}")
    return None


def remember_conversation(query: str, response: str, session_id: str = None, context: Dict = None):
    """Store conversation in episodic memory."""
    memory = get_memory()
    if memory:
        try:
            memory.remember(query, response, session_id, context)
        except Exception as e:
            logger.debug(f"Memory store failed: {e}")


def recall_conversations(query: str, k: int = 5) -> list:
    """Recall relevant conversations from memory."""
    memory = get_memory()
    if memory:
        try:
            return memory.recall(query, k)
        except Exception as e:
            logger.debug(f"Memory recall failed: {e}")
    return []


def route_query(query: str, context: Dict = None, system: str = None) -> str:
    """Route query through expert router."""
    router = get_router()
    if router:
        try:
            return router.route(query, context, system)
        except Exception as e:
            logger.warning(f"Expert routing failed: {e}")
    return ""


def classify_query(query: str) -> tuple:
    """Classify query type for routing."""
    router = get_router()
    if router:
        try:
            return router.classify_query(query)
        except Exception as e:
            logger.debug(f"Query classification failed: {e}")
    return ('general', 0.5)


def publish_event(event_type: str, data: Dict, session_id: str = None):
    """Publish event to stream."""
    stream = get_event_stream()
    if stream:
        try:
            stream.publish(event_type, data, session_id=session_id)
        except Exception as e:
            logger.debug(f"Event publish failed: {e}")


def publish_query_event(query: str, session_id: str = None, metadata: Dict = None):
    """Publish query event."""
    stream = get_event_stream()
    if stream:
        try:
            stream.publish_query(query, session_id, metadata)
        except Exception as e:
            logger.debug(f"Query event failed: {e}")


def publish_response_event(query: str, response: str, elapsed: float, model: str = None, 
                          session_id: str = None, cached: bool = False):
    """Publish response event."""
    stream = get_event_stream()
    if stream:
        try:
            stream.publish_response(query, response, elapsed, model, session_id, cached)
        except Exception as e:
            logger.debug(f"Response event failed: {e}")


def record_feedback(query: str, response: str, feedback_type: str, 
                   correction: str = None, metadata: Dict = None):
    """Record user feedback."""
    fb = get_feedback()
    if fb:
        try:
            fb.record_feedback(query, response, feedback_type, correction, metadata)
            
            # Also publish as event
            stream = get_event_stream()
            if stream:
                stream.publish_feedback(query, response, feedback_type, correction)
        except Exception as e:
            logger.debug(f"Feedback recording failed: {e}")


def get_feedback_stats() -> Dict:
    """Get feedback statistics."""
    fb = get_feedback()
    if fb:
        return fb.get_feedback_stats()
    return {}


def get_all_stats() -> Dict[str, Any]:
    """Get statistics from all infrastructure components."""
    stats = {
        'timestamp': datetime.now().isoformat()
    }
    
    cache = get_cache()
    if cache:
        stats['cache'] = cache.get_stats()
    
    memory = get_memory()
    if memory:
        stats['memory'] = memory.get_stats()
    
    router = get_router()
    if router:
        stats['router'] = router.get_stats()
    
    stream = get_event_stream()
    if stream:
        stats['events'] = stream.get_stats()
    
    fb = get_feedback()
    if fb:
        stats['feedback'] = fb.get_feedback_stats()
    
    return stats
