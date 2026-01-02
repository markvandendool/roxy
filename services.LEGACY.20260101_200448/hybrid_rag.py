#!/usr/bin/env python3
"""
ROXY Hybrid RAG - Advanced RAG with Hybrid Search
Industry Standard: Dense + Sparse + Keyword + Reranking
Combines semantic understanding with exact keyword matching
"""
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from repository_indexer import get_repo_indexer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.hybrid_rag')

class HybridRAG:
    """Advanced RAG with hybrid search (dense + sparse + keyword)"""
    
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.indexer = get_repo_indexer(repo_path)
        self.llm_service = None
        self._init_llm()
    
    def _init_llm(self):
        """Initialize LLM service"""
        try:
            from llm_wrapper import get_llm_service_safe
            self.llm_service = get_llm_service_safe()
        except Exception as e:
            logger.warning(f"LLM service unavailable: {e}")
    
    def _bm25_score(self, query: str, document: str) -> float:
        """BM25 sparse vector scoring (keyword matching)"""
        # Simple BM25 implementation
        query_terms = query.lower().split()
        doc_terms = document.lower().split()
        
        k1 = 1.5
        b = 0.75
        avg_doc_length = 100  # Approximate
        
        score = 0.0
        for term in query_terms:
            term_freq = doc_terms.count(term)
            if term_freq > 0:
                idf = np.log((len(doc_terms) + 1) / (term_freq + 0.5))
                numerator = term_freq * (k1 + 1)
                denominator = term_freq + k1 * (1 - b + b * (len(doc_terms) / avg_doc_length))
                score += idf * (numerator / denominator)
        
        return score
    
    def _keyword_match(self, query: str, text: str) -> float:
        """Simple keyword matching score"""
        query_lower = query.lower()
        text_lower = text.lower()
        
        # Exact phrase match
        if query_lower in text_lower:
            return 1.0
        
        # Word overlap
        query_words = set(query_lower.split())
        text_words = set(text_lower.split())
        
        if not query_words:
            return 0.0
        
        overlap = len(query_words & text_words)
        return overlap / len(query_words)
    
    async def hybrid_search(self, query: str, n_results: int = 10, 
                           file_filter: str = None) -> List[Dict]:
        """Hybrid search combining dense, sparse, and keyword"""
        results = []
        
        # 1. Dense vector search (semantic similarity)
        dense_results = self.indexer.search(query, n_results=n_results * 2, file_filter=file_filter)
        
        # 2. Keyword search (BM25 + exact match)
        keyword_scores = {}
        for result in dense_results:
            text = result.get('text', '')
            metadata = result.get('metadata', {})
            
            # BM25 score
            bm25_score = self._bm25_score(query, text)
            
            # Keyword match score
            keyword_score = self._keyword_match(query, text)
            
            # Combined sparse score
            sparse_score = (bm25_score * 0.6) + (keyword_score * 0.4)
            
            keyword_scores[result.get('id')] = sparse_score
        
        # 3. Combine dense and sparse scores
        combined_results = []
        for result in dense_results:
            result_id = result.get('id')
            dense_score = 1.0 - (result.get('distance', 1.0) if result.get('distance') else 1.0)
            sparse_score = keyword_scores.get(result_id, 0.0)
            
            # Hybrid score: 60% dense, 40% sparse
            hybrid_score = (dense_score * 0.6) + (sparse_score * 0.4)
            
            combined_results.append({
                **result,
                'hybrid_score': hybrid_score,
                'dense_score': dense_score,
                'sparse_score': sparse_score
            })
        
        # 4. Rerank by hybrid score
        combined_results.sort(key=lambda x: x['hybrid_score'], reverse=True)
        
        # 5. Return top N results
        return combined_results[:n_results]
    
    async def answer_question(self, question: str, context_limit: int = 5) -> str:
        """Answer question using hybrid RAG"""
        # Use hybrid search
        search_results = await self.hybrid_search(question, n_results=context_limit * 2)
        
        if not search_results:
            return f"I don't have information about that in the {self.repo_path} repository. The repository may not be indexed yet."
        
        # Build context from top results
        context_parts = []
        for i, result in enumerate(search_results[:context_limit], 1):
            metadata = result.get('metadata', {})
            file_path = metadata.get('file_path', 'unknown')
            text = result.get('text', '')
            hybrid_score = result.get('hybrid_score', 0.0)
            
            context_parts.append(f"[Context {i} from {file_path} (score: {hybrid_score:.2f})]\n{text[:500]}\n")
        
        context = "\n".join(context_parts)
        
        # Generate response with LLM
        if self.llm_service and self.llm_service.is_available():
            prompt = f"""You are ROXY, an AI assistant with deep knowledge of the {self.repo_path} repository.

Based on the following context retrieved using hybrid search (semantic + keyword matching), answer the user's question accurately.

Repository Context:
{context}

User Question: {question}

Provide a detailed, accurate answer based on the repository context."""
            
            try:
                response = await self.llm_service.generate_response(
                    user_input=prompt,
                    context={'repo': str(self.repo_path)},
                    history=[],
                    facts=[]
                )
                if response:
                    return f"{response}\n\n📌 Source: Hybrid RAG (Dense + Sparse + Keyword) from {self.repo_path}\n📚 Context chunks: {context_limit}, Hybrid search used"
                return response or ""
            except Exception as e:
                logger.error(f"LLM generation error: {e}")
        
        # Fallback: return context directly
        return f"Based on the {self.repo_path} repository (hybrid search):\n\n{context}\n\n(Note: LLM not available for enhanced response)"

