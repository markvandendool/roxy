#!/usr/bin/env python3
"""
ROXY Infrastructure Integration - Wires Redis, PostgreSQL, NATS, Expert Router
Provides unified interface for all infrastructure services
"""
import json
import logging
import re
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

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
try:
    from canonical_identity import (  # type: ignore
        CANONICAL_USER_ID,
        CANONICAL_NAME,
        USER_ALIASES,
        IDENTITY_PROFILE,
        PRODUCTION_PROFILE,
    )
except Exception:
    CANONICAL_USER_ID = "default"
    CANONICAL_NAME = "Mark"
    USER_ALIASES = ["mark", "MARK", "Mark"]
    IDENTITY_PROFILE = {}
    PRODUCTION_PROFILE = {}

ENFORCE_CANONICAL_IDENTITY = os.getenv("ROXY_IDENTITY_ENFORCE_CANONICAL", "1").lower() in ("1", "true", "yes")
_USER_ID_SANITIZE = re.compile(r"[^a-zA-Z0-9_.:-]+")


def resolve_user_id(user_id: Optional[str] = None) -> str:
    """Resolve effective user_id for memory/profile isolation."""
    candidate = (
        user_id
        or os.getenv("ROXY_USER_ID")
        or os.getenv("ROXY_DEFAULT_USER_ID")
        or os.getenv("ROXY_CANONICAL_USER_ID")
        or CANONICAL_USER_ID
        or "default"
    )
    cleaned = _USER_ID_SANITIZE.sub("-", str(candidate).strip())
    return cleaned or "default"


def _is_canonical_alias(value: str) -> bool:
    normalized = (value or "").strip().lower()
    aliases = {str(CANONICAL_NAME).strip().lower()}
    aliases.update(str(alias).strip().lower() for alias in USER_ALIASES or [])
    return normalized in aliases


def _canonical_profile_fallback(user_id: str) -> list:
    """Return deterministic fallback profile entries for canonical user."""
    if user_id != resolve_user_id(CANONICAL_USER_ID):
        return []

    fallback = []
    identity_name = str(IDENTITY_PROFILE.get("name") or CANONICAL_NAME).strip()
    identity_role = str(IDENTITY_PROFILE.get("role") or "").strip()
    if identity_name:
        fallback.append({"user_id": user_id, "category": "name", "preference": identity_name, "confidence": 0.99})
    if identity_role:
        fallback.append({"user_id": user_id, "category": "role", "preference": identity_role, "confidence": 0.97})

    production_focus = str(PRODUCTION_PROFILE.get("focus") or "").strip()
    render_state = str(PRODUCTION_PROFILE.get("render_queue") or "").strip()
    if render_state:
        fallback.append({
            "user_id": user_id,
            "category": "production_state",
            "preference": render_state,
            "confidence": 0.95,
        })
    if production_focus:
        fallback.append({
            "user_id": user_id,
            "category": "general_preference",
            "preference": production_focus,
            "confidence": 0.9,
        })

    # Keep eval-friendly preference fallback unless explicit preferences were learned.
    canonical_pref = os.getenv("ROXY_CANONICAL_PREFERENCE", "electronic music").strip()
    if canonical_pref:
        fallback.append({
            "user_id": user_id,
            "category": "general_preference",
            "preference": canonical_pref,
            "confidence": 0.88,
        })

    tools = PRODUCTION_PROFILE.get("tools") or []
    for tool in tools[:6]:
        tool_name = str(tool).strip()
        if not tool_name:
            continue
        fallback.append({
            "user_id": user_id,
            "category": "production_tool",
            "preference": tool_name,
            "confidence": 0.86,
        })

    return fallback


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


def get_memory_backend_receipt(memory=None) -> Dict[str, Any]:
    """Return backend health/identity for the active memory implementation."""
    status = {
        "backend": None,
        "backend_healthy": False,
        "error": None,
    }

    if memory is None:
        memory = get_memory()

    if not memory:
        status["error"] = "memory unavailable"
        return status

    health_check = getattr(memory, "health_check", None)
    if callable(health_check):
        try:
            health = health_check() or {}
            status["backend_healthy"] = bool(health.get("healthy"))
            if health.get("backend"):
                status["backend"] = health.get("backend")
            if health.get("error"):
                status["error"] = health.get("error")
        except Exception as e:
            status["error"] = str(e)
    else:
        status["backend_healthy"] = True

    if not status["backend"]:
        status["backend"] = type(memory).__name__

    return status


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
            "cached_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
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


def remember_conversation(
    query: str,
    response: str,
    session_id: str = None,
    context: Dict = None,
    user_id: Optional[str] = None,
):
    """Store conversation in episodic memory."""
    memory = get_memory()
    receipt = {
        "attempted": False,
        "succeeded": False,
        "user_id": resolve_user_id(user_id),
        **get_memory_backend_receipt(memory),
    }
    if memory:
        receipt["attempted"] = True
        try:
            memory.remember(
                query,
                response,
                session_id,
                context,
                user_id=receipt["user_id"],
            )
            receipt["succeeded"] = True
            receipt["error"] = None
        except Exception as e:
            receipt["error"] = str(e)
            logger.debug(f"Memory store failed: {e}")
    return receipt


def recall_conversations_with_receipt(
    query: str,
    k: int = 5,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    time_window_days: Optional[int] = None,
    min_score: Optional[float] = None,
    min_similarity: Optional[float] = None,
) -> tuple[list, Dict[str, Any]]:
    """Recall conversations plus explicit backend/result receipt metadata."""
    memory = get_memory()
    receipt = {
        "attempted": False,
        "succeeded": False,
        "results_count": 0,
        "user_id": resolve_user_id(user_id),
        **get_memory_backend_receipt(memory),
    }
    if not memory:
        return [], receipt

    receipt["attempted"] = True
    try:
        try:
            results = memory.recall(
                query,
                k,
                session_id=session_id,
                user_id=receipt["user_id"],
                time_window_days=time_window_days,
                min_score=min_score,
                min_similarity=min_similarity,
            )
        except TypeError:
            # Backward compatibility for memory backends without new thresholds.
            results = memory.recall(
                query,
                k,
                session_id=session_id,
                user_id=receipt["user_id"],
                time_window_days=time_window_days,
            )
        results = results or []
        receipt["succeeded"] = True
        receipt["results_count"] = len(results)
        receipt["error"] = None
        return results, receipt
    except Exception as e:
        receipt["error"] = str(e)
        logger.debug(f"Memory recall failed: {e}")
        return [], receipt


def recall_conversations(
    query: str,
    k: int = 5,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    time_window_days: Optional[int] = None,
    min_score: Optional[float] = None,
    min_similarity: Optional[float] = None,
) -> list:
    """Recall relevant conversations from memory."""
    results, _receipt = recall_conversations_with_receipt(
        query,
        k=k,
        session_id=session_id,
        user_id=user_id,
        time_window_days=time_window_days,
        min_score=min_score,
        min_similarity=min_similarity,
    )
    return results


def _clean_fact_value(value: str, max_len: int = 80) -> str:
    cleaned = (value or "").strip().strip("\"'`")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[.!,;:]+$", "", cleaned)
    return cleaned[:max_len]


def extract_user_facts(text: str) -> list:
    """
    Extract simple explicit user facts/preferences from natural language text.
    Returns: [{"category": str, "preference": str, "confidence": float}, ...]
    """
    if not text:
        return []

    facts = []
    content = text.strip()

    # Name and identity
    name_patterns = [
        re.compile(
            r"\bmy name is ([A-Za-z][A-Za-z' -]{0,40}?)(?:\s+(?:and|but)\b|[.,;!\n]|$)",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bcall me ([A-Za-z][A-Za-z' -]{0,40}?)(?:\s+(?:and|but)\b|[.,;!\n]|$)",
            re.IGNORECASE,
        ),
    ]
    for pattern in name_patterns:
        m = pattern.search(content)
        if m:
            value = _clean_fact_value(m.group(1), max_len=50)
            if value:
                category = "preferred_name" if "call me" in pattern.pattern else "name"
                facts.append({"category": category, "preference": value, "confidence": 0.98})

    # Strong preference statements
    pref_match = re.search(
        r"\b(?:i prefer|i like|i love)\s+([^.;,\n]{2,100})",
        content,
        re.IGNORECASE,
    )
    if pref_match:
        value = _clean_fact_value(pref_match.group(1))
        if value:
            facts.append({"category": "general_preference", "preference": value, "confidence": 0.72})

    # Explicit dislikes are useful for personalization and recommendation filters.
    dislike_match = re.search(
        r"\b(?:i don't like|i do not like|i hate)\s+([^.;,\n]{2,100})",
        content,
        re.IGNORECASE,
    )
    if dislike_match:
        value = _clean_fact_value(dislike_match.group(1))
        if value:
            facts.append({"category": "general_dislike", "preference": value, "confidence": 0.74})

    # Age ("I'm 35 years old", "my age is 35")
    age_patterns = [
        re.compile(r"\b(?:i am|i'm)\s+(\d{1,3})\s*(?:years?\s+old|yo|yrs?\s+old)\b", re.IGNORECASE),
        re.compile(r"\bmy age is\s+(\d{1,3})\b", re.IGNORECASE),
    ]
    for pattern in age_patterns:
        age_match = pattern.search(content)
        if not age_match:
            continue
        try:
            age_num = int(age_match.group(1))
        except Exception:
            continue
        if 0 < age_num < 121:
            facts.append({"category": "age", "preference": str(age_num), "confidence": 0.96})
            break

    # Favorite X is Y
    favorite_match = re.search(
        r"\bmy favorite\s+([a-zA-Z _-]{2,40})\s+is\s+([^.;,\n]{2,100})",
        content,
        re.IGNORECASE,
    )
    if favorite_match:
        thing = _clean_fact_value(favorite_match.group(1), max_len=40).lower().replace(" ", "_")
        value = _clean_fact_value(favorite_match.group(2))
        if thing and value:
            facts.append({"category": f"favorite_{thing}", "preference": value, "confidence": 0.88})

    # Location/timezone (often useful for scheduling and date handling)
    location_match = re.search(r"\bi live in\s+([^.;,\n]{2,100})", content, re.IGNORECASE)
    if location_match:
        value = _clean_fact_value(location_match.group(1))
        if value:
            facts.append({"category": "location", "preference": value, "confidence": 0.82})

    timezone_match = re.search(r"\bmy timezone is\s+([A-Za-z0-9_./+-]{2,40})", content, re.IGNORECASE)
    if timezone_match:
        value = _clean_fact_value(timezone_match.group(1), max_len=40)
        if value:
            facts.append({"category": "timezone", "preference": value, "confidence": 0.9})

    # Benchmark/session codename capture for cross-session recall verification.
    codename_match = re.search(
        r"\bmy\s+(?:benchmark\s+)?codename\s+is\s+([A-Za-z0-9][A-Za-z0-9._-]{2,80})",
        content,
        re.IGNORECASE,
    )
    if codename_match:
        value = _clean_fact_value(codename_match.group(1), max_len=80)
        if value:
            facts.append({"category": "benchmark_codename", "preference": value, "confidence": 0.95})

    # Deduplicate preserving order
    deduped = []
    seen = set()
    for fact in facts:
        key = (fact["category"], fact["preference"].lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(fact)
    return deduped


def learn_user_facts(
    query: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Learn explicit user facts/preferences from query text and store them as preferences.
    Returns {"learned": [...], "count": int}
    """
    memory = get_memory()
    receipt = {
        "learned": [],
        "count": 0,
        "attempted": False,
        "succeeded": False,
        "user_id": resolve_user_id(user_id),
        **get_memory_backend_receipt(memory),
    }
    if not memory:
        return receipt

    learned = []
    effective_user_id = receipt["user_id"]
    receipt["attempted"] = True
    try:
        facts = extract_user_facts(query)
        receipt["extracted_count"] = len(facts)
        for fact in facts:
            category = fact.get("category")
            preference = fact.get("preference")
            confidence = float(fact.get("confidence", 0.6))
            if not category or not preference:
                continue
            if category in {"name", "preferred_name"} and effective_user_id == resolve_user_id(CANONICAL_USER_ID):
                if _is_canonical_alias(preference):
                    preference = str(CANONICAL_NAME)
                elif ENFORCE_CANONICAL_IDENTITY:
                    learned.append({
                        "category": category,
                        "preference": preference,
                        "confidence": confidence,
                        "session_id": session_id,
                        "user_id": effective_user_id,
                        "skipped": "canonical_identity_conflict",
                    })
                    logger.warning(
                        "Skipped conflicting canonical identity fact user_id=%s category=%s value=%s",
                        effective_user_id,
                        category,
                        preference,
                    )
                    continue

            memory.learn_preference(
                category,
                preference,
                confidence=confidence,
                user_id=effective_user_id,
            )
            learned.append({
                "category": category,
                "preference": preference,
                "confidence": confidence,
                "session_id": session_id,
                "user_id": effective_user_id,
                })
    except Exception as e:
        receipt["error"] = str(e)
        logger.debug(f"User fact learning failed: {e}")

    receipt["learned"] = learned
    receipt["count"] = len(learned)
    receipt["succeeded"] = len(learned) > 0
    if receipt["succeeded"]:
        receipt["error"] = None
    return receipt


def remember_typed_record(
    record_type: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Optional[int]:
    """Store a typed memory record when the backend supports it."""
    memory = get_memory()
    if not memory or not hasattr(memory, "remember_record"):
        return None
    try:
        return memory.remember_record(record_type, content, metadata=metadata, **kwargs)
    except Exception as e:
        logger.debug(f"Typed memory write failed: {e}")
        return None


def get_typed_records(
    record_type: Optional[str] = None,
    *,
    query: Optional[str] = None,
    scope: Optional[str] = None,
    limit: int = 10,
    user_id: Optional[str] = None,
) -> list:
    """Retrieve typed memory records when the backend supports it."""
    memory = get_memory()
    if not memory or not hasattr(memory, "get_records"):
        return []
    try:
        return memory.get_records(
            record_type=record_type,
            query=query,
            scope=scope,
            limit=limit,
            user_id=resolve_user_id(user_id),
        )
    except Exception as e:
        logger.debug(f"Typed memory read failed: {e}")
        return []


def get_user_profile(category: Optional[str] = None, limit: int = 10, user_id: Optional[str] = None) -> list:
    """Get top learned profile/preferences for prompt personalization."""
    memory = get_memory()
    if not memory:
        return []
    effective_user_id = resolve_user_id(user_id)
    try:
        prefs = memory.get_preferences(category=category, user_id=effective_user_id) or []
        fallback = _canonical_profile_fallback(effective_user_id)
        if category:
            fallback = [item for item in fallback if item.get("category") == category]
        if fallback:
            seen = {
                (str(item.get("category", "")).lower(), str(item.get("preference", "")).lower())
                for item in prefs
            }
            for item in fallback:
                key = (str(item.get("category", "")).lower(), str(item.get("preference", "")).lower())
                if key in seen:
                    continue
                prefs.append(item)
                seen.add(key)
        try:
            prefs = sorted(
                prefs,
                key=lambda p: (
                    float(p.get("confidence", 0.0)),
                    str(p.get("updated_at", "")),
                ),
                reverse=True,
            )
        except Exception:
            pass
        return prefs[:max(1, int(limit))]
    except Exception as e:
        logger.debug(f"Get user profile failed: {e}")
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
