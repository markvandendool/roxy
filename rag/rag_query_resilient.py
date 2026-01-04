#!/usr/bin/env python3
"""
RAG Query with resilience (retry + circuit breaker)
Wraps ChromaDB queries with retry logic and circuit breaker
"""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb

logger = logging.getLogger("roxy.rag.query")

# Import resilience utilities
try:
    from retry_utils import retry
    from circuit_breaker import get_circuit_breaker
    RESILIENCE_AVAILABLE = True
except ImportError:
    RESILIENCE_AVAILABLE = False
    logger.warning("Resilience utilities not available - no retry/circuit breaker")

ROXY_DIR = Path.home() / ".roxy"

# Global circuit breaker for ChromaDB
chromadb_breaker = None
if RESILIENCE_AVAILABLE:
    chromadb_breaker = get_circuit_breaker(
        name="chromadb",
        failure_threshold=5,
        timeout=60.0
    )


@retry(max_attempts=3, delay=0.5, backoff=2.0)
def query_chromadb_with_retry(
    collection_name: str,
    query_embeddings: List[List[float]],
    n_results: int = 3,
    where: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Query ChromaDB with retry logic
    
    Args:
        collection_name: Name of the ChromaDB collection
        query_embeddings: Query embedding vectors
        n_results: Number of results to return
        where: Optional metadata filter
        
    Returns:
        ChromaDB query results
        
    Raises:
        Exception: If all retry attempts fail
    """
    def _do_query():
        client = chromadb.PersistentClient(path=str(ROXY_DIR / "chroma_db"))
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        ef = DefaultEmbeddingFunction()
        
        collection = client.get_collection(collection_name, embedding_function=ef)
        
        results = collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        return results
    
    # Use circuit breaker if available
    if RESILIENCE_AVAILABLE and chromadb_breaker:
        return chromadb_breaker.call(_do_query)
    else:
        return _do_query()


def get_chromadb_stats() -> Dict[str, Any]:
    """Get ChromaDB circuit breaker statistics"""
    if RESILIENCE_AVAILABLE and chromadb_breaker:
        return chromadb_breaker.get_stats()
    else:
        return {"error": "Circuit breaker not available"}
