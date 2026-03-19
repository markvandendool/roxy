#!/usr/bin/env python3
"""
Query Rewriting Module for ROXY
Rewrites user queries before retrieval to improve recall robustness.

Based on research:
- Query expansion with synonyms
- Entity extraction and normalization
- Intent framing for retrieval
- Personal context injection

This helps when user phrasing changes but intent remains the same.
"""
import re
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger("roxy.query_rewriting")

# Entity patterns for MindSong/SkyBeam ecosystem
_ENTITY_PATTERNS = {
    r"\b(I|me|my|myself)\b": "user",
    r"\b(we|our|us)\b": "team",
    r"\broxy\b": "assistant",
    r"\b(mindsong|mind song)\b": "mindsong studios",
    r"\b(skybeam|sky beam|sky-beam)\b": "skybeam renderer",
    r"\b(skydream|sky dream)\b": "skydream pipeline",
    r"\b(stackkraft|stack kraft)\b": "stackkraft monetization",
    r"\b(shotcaller|shot caller)\b": "shotcaller scheduler",
    r"\b(mimiq|mimic)\b": "mimiq quality control",
    r"\b(mqqc)\b": "mqqc audio quality",
    r"\b(luno)\b": "luno orchestrator",
    r"\b(pixel)\b": "pixel agent",
    r"\b(rocky)\b": "rocky ai music",
    r"\b(render|rendering|rendered)\b": "video render",
    r"\b(gpu|cuda|6900xt|w5700x)\b": "gpu hardware",
}

# Expansion synonyms
_QUERY_EXPANSIONS = {
    "who am i": ["user name identity", "my identity name"],
    "what's my name": ["user name identity", "my name is"],
    "render status": ["video render queue status", "gpu render progress"],
    "gpu performance": ["gpu utilization speed", "graphics card performance"],
    "skybeam queue": ["skybeam render queue", "video rendering queue"],
    "production status": ["mindson studio status", "current production"],
    "monetization": ["revenue revenue", "stackkraft earnings"],
    "schedule": ["shotcaller schedule", "production timeline"],
}


def _extract_entities(query: str) -> List[str]:
    """Extract and normalize entities from query."""
    entities = []
    query_lower = query.lower()
    
    for pattern, normalized in _ENTITY_PATTERNS.items():
        if re.search(pattern, query_lower, re.IGNORECASE):
            entities.append(normalized)
    
    return entities


def _expand_query(query: str) -> List[str]:
    """Expand query with synonyms and related terms."""
    query_lower = query.lower().strip()
    expansions = [query_lower]
    
    # Check predefined expansions
    for pattern, expansions_list in _QUERY_EXPANSIONS.items():
        if pattern in query_lower:
            expansions.extend(expansions_list)
            break
    
    # Add entity-aware expansions
    entities = _extract_entities(query)
    if entities:
        expansions.append(query_lower + " " + " ".join(entities))
    
    return expansions


def _rewrite_for_memory(query: str, session_context: Optional[str] = None) -> str:
    """
    Rewrite query for optimal memory retrieval.
    
    Handles:
    - Pronoun resolution (I → "the user")
    - Temporal references (yesterday, last week)
    - Implicit references (it, that, this)
    """
    rewritten = query
    
    # Pronoun resolution
    rewritten = re.sub(r"\bI\b", "the user", rewritten, flags=re.IGNORECASE)
    rewritten = re.sub(r"\bmy\b", "the user's", rewritten, flags=re.IGNORECASE)
    rewritten = re.sub(r"\bme\b", "the user", rewritten, flags=re.IGNORECASE)
    
    # Temporal normalization (keep as-is but add explicit)
    # Note: Temporal queries should use TruthPacket for actual dates
    if re.search(r"\byesterday\b", rewritten, re.IGNORECASE):
        rewritten += " recent past conversation"
    if re.search(r"\blast week\b", rewritten, re.IGNORECASE):
        rewritten += " past week conversation"
    if re.search(r"\bbefore\b", rewritten, re.IGNORECASE):
        rewritten += " previous discussion"
    
    # Implicit reference expansion
    if re.search(r"\bit\b", rewritten, re.IGNORECASE):
        # Add context hint - the system should look at recent conversation
        rewritten += " related to the current topic"
    
    return rewritten


def rewrite_query_for_retrieval(
    query: str,
    session_context: Optional[str] = None,
    use_expansion: bool = True
) -> Tuple[str, Dict[str, List[str]]]:
    """
    Rewrite query for optimal retrieval.
    
    Args:
        query: Original user query
        session_context: Optional session context for pronoun resolution
        use_expansion: Whether to use query expansion
        
    Returns:
        (rewritten_query, metadata_dict)
    """
    metadata = {
        "original": query,
        "entities": [],
        "expansions": [],
        "rewritten": query,
    }
    
    # Step 1: Extract entities
    entities = _extract_entities(query)
    metadata["entities"] = entities
    
    # Step 2: Rewrite for memory (pronoun resolution, etc)
    rewritten = _rewrite_for_memory(query, session_context)
    metadata["rewritten"] = rewritten
    
    # Step 3: Generate expanded queries if enabled
    if use_expansion:
        expansions = _expand_query(query)
        metadata["expansions"] = expansions
        # Use the first expansion that adds value
        for exp in expansions[1:]:
            if len(exp) > len(rewritten) and exp != rewritten.lower():
                rewritten = exp
                break
    
    return rewritten, metadata


def multi_query_retrieval(query: str, top_k: int = 3) -> List[str]:
    """
    Generate multiple query variations for parallel retrieval.
    Uses RAG multi-query pattern from research.
    
    Returns:
        List of rewritten queries to use for parallel retrieval
    """
    rewritten, meta = rewrite_query_for_retrieval(query)
    
    queries = [rewritten]
    
    # Add entity-focused variations
    if meta["entities"]:
        entity_query = query + " " + " ".join(meta["entities"])
        queries.append(entity_query)
    
    # Add topic-only variation (removes pronouns, focuses on content)
    topic_only = re.sub(r"\b(I|me|my|we|our|us|you|your)\b", "", query, flags=re.IGNORECASE)
    topic_only = re.sub(r"\s+", " ", topic_only).strip()
    if topic_only and topic_only != query:
        queries.append(topic_only)
    
    # Deduplicate and limit
    seen = set()
    unique_queries = []
    for q in queries:
        q_lower = q.lower().strip()
        if q_lower not in seen and len(q_lower) > 3:
            seen.add(q_lower)
            unique_queries.append(q_lower)
    
    return unique_queries[:top_k]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test queries
    test_queries = [
        "Who am I?",
        "What's my name?",
        "Check the skybeam render queue",
        "How was the production yesterday?",
        "What's it doing?",
        "What did we discuss about the render?",
    ]
    
    print("Query Rewriting Tests")
    print("=" * 60)
    
    for query in test_queries:
        rewritten, meta = rewrite_query_for_retrieval(query)
        print(f"\nOriginal: {query}")
        print(f"Rewritten: {rewritten}")
        print(f"Entities: {meta['entities']}")
        print(f"Expansions: {meta['expansions']}")
