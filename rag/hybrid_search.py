#!/usr/bin/env python3
"""
Hybrid Search - Combines dense vectors, BM25 sparse vectors, and keyword matching
Enhances RAG retrieval quality by combining semantic and exact matching
"""
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger("roxy.rag.hybrid_search")

ROXY_DIR = Path.home() / ".roxy"


class HybridSearch:
    """Hybrid search combining dense, sparse, and keyword matching"""
    
    def __init__(self):
        self.bm25_available = False
        self._init_bm25()
    
    def _init_bm25(self):
        """Initialize BM25 if available"""
        try:
            import rank_bm25
            self.bm25_available = True
            logger.debug("BM25 available for sparse vector search")
        except ImportError:
            logger.debug("rank-bm25 not available, using simple keyword matching")
    
    def _simple_bm25_score(self, query: str, document: str) -> float:
        """Simple BM25-like scoring without external library"""
        query_terms = set(re.findall(r'\w+', query.lower()))
        doc_terms = re.findall(r'\w+', document.lower())
        
        if not query_terms or not doc_terms:
            return 0.0
        
        # Term frequency
        term_freqs = {}
        for term in doc_terms:
            term_freqs[term] = term_freqs.get(term, 0) + 1
        
        # Calculate score
        k1 = 1.5
        b = 0.75
        avg_doc_length = 100  # Approximate
        
        score = 0.0
        for term in query_terms:
            if term in term_freqs:
                tf = term_freqs[term]
                # Simple IDF approximation
                idf = 1.0 / (1.0 + tf)
                # BM25 formula
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (len(doc_terms) / avg_doc_length))
                score += idf * (numerator / denominator)
        
        return score
    
    def _bm25_score(self, query: str, document: str) -> float:
        """Get BM25 score for query-document pair"""
        if self.bm25_available:
            try:
                import rank_bm25
                query_terms = re.findall(r'\w+', query.lower())
                doc_terms = re.findall(r'\w+', document.lower())
                
                if not query_terms or not doc_terms:
                    return 0.0
                
                bm25 = rank_bm25.BM25Okapi([doc_terms])
                scores = bm25.get_scores(query_terms)
                return float(sum(scores))
            except Exception as e:
                logger.debug(f"BM25 library failed: {e}, using simple scoring")
        
        return self._simple_bm25_score(query, document)
    
    def _keyword_match_score(self, query: str, text: str) -> float:
        """Simple keyword matching score"""
        query_lower = query.lower()
        text_lower = text.lower()
        
        # Exact phrase match
        if query_lower in text_lower:
            return 1.0
        
        # Word overlap
        query_words = set(re.findall(r'\w+', query_lower))
        text_words = set(re.findall(r'\w+', text_lower))
        
        if not query_words:
            return 0.0
        
        overlap = len(query_words & text_words)
        return overlap / len(query_words)
    
    def combine_scores(self, 
                      dense_score: float,
                      sparse_score: float,
                      keyword_score: float,
                      dense_weight: float = 0.5,
                      sparse_weight: float = 0.3,
                      keyword_weight: float = 0.2) -> float:
        """Combine dense, sparse, and keyword scores"""
        # Normalize scores to [0, 1] range
        dense_norm = min(dense_score, 1.0)
        sparse_norm = min(sparse_score / 10.0, 1.0) if sparse_score > 0 else 0.0  # BM25 scores can be > 1
        keyword_norm = keyword_score
        
        # Weighted combination
        combined = (
            dense_norm * dense_weight +
            sparse_norm * sparse_weight +
            keyword_norm * keyword_weight
        )
        
        return combined
    
    def rerank_results(self,
                      query: str,
                      results: List[Dict[str, Any]],
                      top_k: int = 5) -> List[Dict[str, Any]]:
        """Rerank results using hybrid scoring"""
        if not results:
            return []
        
        # Calculate hybrid scores for each result
        scored_results = []
        for result in results:
            document = result.get("document", "") or result.get("text", "")
            dense_score = 1.0 - result.get("distance", 1.0)  # Convert distance to similarity
            
            # Calculate sparse scores
            sparse_score = self._bm25_score(query, document)
            keyword_score = self._keyword_match_score(query, document)
            
            # Combine scores
            hybrid_score = self.combine_scores(
                dense_score,
                sparse_score,
                keyword_score
            )
            
            scored_results.append({
                **result,
                "hybrid_score": hybrid_score,
                "dense_score": dense_score,
                "sparse_score": sparse_score,
                "keyword_score": keyword_score
            })
        
        # Sort by hybrid score
        scored_results.sort(key=lambda x: x["hybrid_score"], reverse=True)
        
        return scored_results[:top_k]
    
    def expand_query(self, query: str) -> str:
        """Expand query with synonyms and related terms"""
        # Simple query expansion - can be enhanced with synonym dictionaries
        query_lower = query.lower()
        
        # Add common synonyms
        expansions = {
            "how": ["how", "what", "explain"],
            "what": ["what", "which", "describe"],
            "where": ["where", "location", "path"],
            "why": ["why", "reason", "cause"],
        }
        
        # For now, return original query
        # Future: Use word embeddings or synonym dictionary
        return query


def get_hybrid_search() -> HybridSearch:
    """Get global hybrid search instance"""
    global _hybrid_search_instance
    if '_hybrid_search_instance' not in globals():
        _hybrid_search_instance = HybridSearch()
    return _hybrid_search_instance














