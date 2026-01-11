#!/usr/bin/env python3
"""
Router Integration - Minimal wrapper for expert_router.py
Provides synchronous routing decisions for roxy_core.py

Chief's Directive #8: Integrate expert_router.py as the single routing authority.
"""
import os
import logging
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("roxy.router_integration")

# Pool configuration
POOL_CONFIG = {
    "big": {
        "url": os.getenv("OLLAMA_BIG_URL", "http://127.0.0.1:11434"),
        "port": 11434,
        "default_model": "qwen2.5-coder:14b",
    },
    "fast": {
        "url": os.getenv("OLLAMA_FAST_URL", "http://127.0.0.1:11435"),
        "port": 11435,
        "default_model": "llama3:8b",
    },
}

# Default pool for general queries (FAST for speed, BIG only when needed)
DEFAULT_POOL = "fast"


class QueryType(Enum):
    """Query types for routing."""
    CODE = "code"
    TECHNICAL = "technical"
    CREATIVE = "creative"
    SUMMARY = "summary"
    GENERAL = "general"


@dataclass
class RoutingDecision:
    """Full routing decision for observability."""
    query_type: str
    selected_pool: str
    selected_endpoint: str
    selected_model: str
    reason: str
    confidence: float


# Keyword patterns for fast classification
KEYWORD_PATTERNS = {
    QueryType.CODE: [
        'code', 'function', 'class', 'debug', 'implement', 'program',
        'python', 'javascript', 'typescript', 'rust', 'golang', 'java',
        'api', 'database', 'sql', 'git', 'docker', 'bug', 'error',
        'compile', 'build', 'syntax', 'fix', 'refactor'
    ],
    QueryType.TECHNICAL: [
        'explain', 'how does', 'what is', 'documentation', 'architecture',
        'system', 'design', 'protocol', 'configure', 'setup', 'install',
        'deploy', 'service', 'server', 'roxy', 'ollama', 'pool', 'gpu'
    ],
    QueryType.CREATIVE: [
        'write', 'story', 'poem', 'creative', 'imagine', 'fiction',
        'blog', 'article', 'essay', 'script', 'lyrics', 'narrative'
    ],
    QueryType.SUMMARY: [
        'summarize', 'summary', 'tl;dr', 'tldr', 'key points', 'highlights',
        'overview', 'gist', 'recap', 'condense', 'bullet'
    ],
}

# Query types that prefer FAST pool (quick responses, cheap inference)
FAST_POOL_TYPES = {QueryType.SUMMARY, QueryType.GENERAL}

# Query types that REQUIRE BIG pool (quality-critical)
BIG_POOL_TYPES = {QueryType.CODE, QueryType.TECHNICAL, QueryType.CREATIVE}


def classify_query(query: str) -> Tuple[QueryType, float]:
    """
    Classify query type using keyword matching with precedence ordering.

    Precedence (Chief directive): SUMMARY > CODE > TECHNICAL > CREATIVE > GENERAL
    Intent keywords (summarize, code, write) should beat domain keywords (roxy, pool).

    Returns:
        (query_type, confidence)
    """
    query_lower = query.lower()

    # Precedence order: intent types beat domain types
    PRECEDENCE = [
        QueryType.SUMMARY,   # "summarize" always wins
        QueryType.CODE,      # "code", "function", "implement"
        QueryType.TECHNICAL, # "explain", "how does"
        QueryType.CREATIVE,  # "write story", "poem"
        QueryType.GENERAL,   # fallback
    ]

    # Score each type
    scores = {}
    for qtype, keywords in KEYWORD_PATTERNS.items():
        matches = sum(1 for kw in keywords if kw in query_lower)
        if matches > 0:
            scores[qtype] = min(1.0, matches / 3.0)  # 3 keywords = 100% confidence

    if not scores:
        return QueryType.GENERAL, 0.0

    # Find highest score
    max_score = max(scores.values())

    # Among types with max score, pick by precedence
    for qtype in PRECEDENCE:
        if scores.get(qtype) == max_score:
            return qtype, max_score

    # Fallback (shouldn't reach here)
    best_type = max(scores, key=scores.get)
    return best_type, scores[best_type]


def get_pool_for_type(query_type: QueryType, force_deep: bool = False) -> str:
    """
    Get pool name for query type.

    Args:
        query_type: The classified query type
        force_deep: If True, always use BIG pool

    Returns:
        Pool name ("big" or "fast")
    """
    if force_deep:
        return "big"

    if query_type in BIG_POOL_TYPES:
        return "big"

    if query_type in FAST_POOL_TYPES:
        return "fast"

    return DEFAULT_POOL  # Default to FAST for speed


def get_model_for_type(query_type: QueryType, pool: str) -> str:
    """
    Get model name for query type and pool.
    """
    if pool == "fast":
        return POOL_CONFIG["fast"]["default_model"]

    # BIG pool - choose based on query type
    if query_type == QueryType.CODE:
        return "qwen2.5-coder:14b"
    elif query_type == QueryType.CREATIVE:
        return "llama3:8b"
    else:
        return POOL_CONFIG["big"]["default_model"]


def route_query(query: str, force_deep: bool = False) -> RoutingDecision:
    """
    Route a query to the appropriate pool and model.

    Args:
        query: The user query
        force_deep: Force use of BIG pool

    Returns:
        RoutingDecision with full routing metadata
    """
    # Classify
    query_type, confidence = classify_query(query)

    # Select pool
    pool = get_pool_for_type(query_type, force_deep)
    pool_config = POOL_CONFIG[pool]

    # Select model
    model = get_model_for_type(query_type, pool)

    # Build reason
    if force_deep:
        reason = f"force_deep:{query_type.value}"
    else:
        reason = f"classified:{query_type.value}:{confidence:.2f}"

    decision = RoutingDecision(
        query_type=query_type.value,
        selected_pool=pool,
        selected_endpoint=pool_config["url"],
        selected_model=model,
        reason=reason,
        confidence=confidence,
    )

    logger.info(
        "[ROUTER] %s -> pool=%s model=%s reason=%s",
        query[:50], pool, model, reason
    )

    return decision


def to_routing_meta(decision: RoutingDecision) -> Dict[str, Any]:
    """Convert RoutingDecision to routing_meta dict for SSE."""
    return {
        "query_type": decision.query_type,
        "selected_pool": decision.selected_pool,
        "selected_endpoint": decision.selected_endpoint,
        "selected_model": decision.selected_model,
        "reason": decision.reason,
        "confidence": decision.confidence,
    }


# Global router instance for lazy init
_router_initialized = False


def initialize_router():
    """Initialize router (called once on first use)."""
    global _router_initialized
    if not _router_initialized:
        logger.info("[ROUTER] Initialized with pools: %s", list(POOL_CONFIG.keys()))
        _router_initialized = True


if __name__ == "__main__":
    # Test the router
    test_queries = [
        "fix the bug in roxy_core.py",
        "what is ROXY?",
        "write me a poem about coding",
        "summarize this document",
        "how do pools work?",
    ]

    print("Router Integration Test")
    print("=" * 60)

    for query in test_queries:
        decision = route_query(query)
        print(f"\nQuery: {query}")
        print(f"  Type: {decision.query_type}")
        print(f"  Pool: {decision.selected_pool}")
        print(f"  Model: {decision.selected_model}")
        print(f"  Reason: {decision.reason}")
