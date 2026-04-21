#!/usr/bin/env python3
"""
Hybrid RAG Engine - Production-Grade Retrieval
===============================================
Implements 3-stage RAG pipeline:
1. Hybrid Retrieval (Dense + Sparse)
2. Re-ranking (Cross-encoder)
3. Context Assembly

Replaces basic pgvector/ChromaDB with Qdrant + BM25 + BGE-reranker
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
import numpy as np

logger = logging.getLogger("roxy.hybrid_rag")


@dataclass
class RetrievedChunk:
    """A chunk retrieved from the knowledge base"""
    content: str
    source: str
    score: float
    metadata: Dict[str, Any]
    retrieval_method: str  # "dense", "sparse", "hybrid"


@dataclass
class RAGResult:
    """Final RAG result with context and sources"""
    context: str
    sources: List[RetrievedChunk]
    query_time_ms: float
    total_chunks: int


class HybridRAGEngine:
    """
    Production RAG with hybrid search and re-ranking.
    
    Architecture:
    - Qdrant: Dense vector storage (HNSW index)
    - BM25: Sparse lexical matching
    - BGE-reranker: Cross-encoder re-ranking
    """
    
    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        embedding_model: str = "BAAI/bge-large-en-v1.5",
        reranker_model: str = "BAAI/bge-reranker-v2-m3",
        collection_name: str = "roxy_knowledge",
        top_k_retrieve: int = 20,
        top_k_rerank: int = 5
    ):
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.embedding_model = embedding_model
        self.reranker_model = reranker_model
        self.collection_name = collection_name
        self.top_k_retrieve = top_k_retrieve
        self.top_k_rerank = top_k_rerank
        
        # Lazy-loaded components
        self._qdrant_client = None
        self._embedding_fn = None
        self._reranker = None
        self._bm25_index = None
        
    async def initialize(self):
        """Initialize all RAG components"""
        await asyncio.gather(
            self._init_qdrant(),
            self._init_embedding_model(),
            self._init_reranker(),
            self._init_bm25()
        )
        logger.info("Hybrid RAG engine initialized")
    
    async def _init_qdrant(self):
        """Initialize Qdrant client"""
        try:
            from qdrant_client import QdrantClient
            self._qdrant_client = QdrantClient(
                host=self.qdrant_host,
                port=self.qdrant_port,
                prefer_grpc=True
            )
            logger.info(f"Connected to Qdrant at {self.qdrant_host}:{self.qdrant_port}")
        except ImportError:
            logger.error("qdrant-client not installed. Run: pip install qdrant-client")
            raise
    
    async def _init_embedding_model(self):
        """Load embedding model for dense retrieval"""
        try:
            from sentence_transformers import SentenceTransformer
            self._embedding_fn = SentenceTransformer(self.embedding_model)
            logger.info(f"Loaded embedding model: {self.embedding_model}")
        except ImportError:
            logger.error("sentence-transformers not installed")
            raise
    
    async def _init_reranker(self):
        """Load cross-encoder re-ranker"""
        try:
            from sentence_transformers import CrossEncoder
            self._reranker = CrossEncoder(self.reranker_model)
            logger.info(f"Loaded reranker: {self.reranker_model}")
        except ImportError:
            logger.error("CrossEncoder not available")
            raise
    
    async def _init_bm25(self):
        """Initialize BM25 sparse index"""
        try:
            from rank_bm25 import BM25Okapi
            # Will be populated from Qdrant on first query
            self._bm25_index = None
            self._bm25_corpus = []
            self._bm25_doc_ids = []
            logger.info("BM25 index initialized (empty)")
        except ImportError:
            logger.error("rank-bm25 not installed. Run: pip install rank-bm25")
            raise
    
    async def query(self, query_text: str, filters: Optional[Dict] = None) -> RAGResult:
        """
        Execute hybrid RAG query.
        
        Pipeline:
        1. Dense retrieval (vector similarity)
        2. Sparse retrieval (BM25 lexical)
        3. Fusion (RRF - Reciprocal Rank Fusion)
        4. Re-ranking (cross-encoder)
        5. Context assembly
        """
        import time
        start_time = time.time()
        
        # Stage 1: Parallel dense and sparse retrieval
        dense_results, sparse_results = await asyncio.gather(
            self._dense_retrieve(query_text, filters),
            self._sparse_retrieve(query_text, filters)
        )
        
        # Stage 2: Fusion (RRF)
        fused_results = self._reciprocal_rank_fusion(
            dense_results, 
            sparse_results,
            k=60  # RRF constant
        )
        
        # Stage 3: Re-ranking
        reranked_results = await self._rerank(query_text, fused_results[:self.top_k_retrieve])
        
        # Stage 4: Context assembly
        context = self._assemble_context(reranked_results[:self.top_k_rerank])
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return RAGResult(
            context=context,
            sources=reranked_results[:self.top_k_rerank],
            query_time_ms=elapsed_ms,
            total_chunks=len(reranked_results)
        )
    
    async def _dense_retrieve(
        self, 
        query: str, 
        filters: Optional[Dict]
    ) -> List[RetrievedChunk]:
        """Dense vector retrieval via Qdrant"""
        if not self._embedding_fn or not self._qdrant_client:
            return []
        
        # Embed query
        query_vector = self._embedding_fn.encode(query).tolist()
        
        # Search Qdrant
        results = self._qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=self.top_k_retrieve,
            query_filter=self._build_qdrant_filter(filters) if filters else None
        )
        
        chunks = []
        for result in results:
            chunks.append(RetrievedChunk(
                content=result.payload.get("content", ""),
                source=result.payload.get("source", "unknown"),
                score=result.score,
                metadata=result.payload,
                retrieval_method="dense"
            ))
        
        return chunks
    
    async def _sparse_retrieve(
        self, 
        query: str, 
        filters: Optional[Dict]
    ) -> List[RetrievedChunk]:
        """Sparse BM25 lexical retrieval"""
        if not self._bm25_index:
            # Lazy load BM25 from Qdrant
            await self._load_bm25_from_qdrant()
        
        if not self._bm25_index:
            return []
        
        # Tokenize query
        query_tokens = query.lower().split()
        
        # BM25 scoring
        scores = self._bm25_index.get_scores(query_tokens)
        
        # Get top-k
        top_indices = np.argsort(scores)[-self.top_k_retrieve:][::-1]
        
        chunks = []
        for idx in top_indices:
            if scores[idx] > 0:
                doc_id = self._bm25_doc_ids[idx]
                # Fetch full document from Qdrant
                doc = self._qdrant_client.retrieve(
                    collection_name=self.collection_name,
                    ids=[doc_id]
                )[0]
                
                chunks.append(RetrievedChunk(
                    content=doc.payload.get("content", ""),
                    source=doc.payload.get("source", "unknown"),
                    score=float(scores[idx]),
                    metadata=doc.payload,
                    retrieval_method="sparse"
                ))
        
        return chunks
    
    async def _load_bm25_from_qdrant(self):
        """Load BM25 index from Qdrant collection"""
        try:
            from rank_bm25 import BM25Okapi
            
            # Scroll all documents
            all_docs = []
            next_offset = None
            
            while True:
                response = self._qdrant_client.scroll(
                    collection_name=self.collection_name,
                    offset=next_offset,
                    limit=1000
                )
                
                for doc in response[0]:
                    content = doc.payload.get("content", "")
                    tokens = content.lower().split()
                    all_docs.append(tokens)
                    self._bm25_doc_ids.append(doc.id)
                
                next_offset = response[1]
                if next_offset is None:
                    break
            
            if all_docs:
                self._bm25_index = BM25Okapi(all_docs)
                self._bm25_corpus = all_docs
                logger.info(f"Loaded BM25 index with {len(all_docs)} documents")
            
        except Exception as e:
            logger.error(f"Failed to load BM25: {e}")
    
    def _reciprocal_rank_fusion(
        self,
        dense_results: List[RetrievedChunk],
        sparse_results: List[RetrievedChunk],
        k: int = 60
    ) -> List[RetrievedChunk]:
        """
        Reciprocal Rank Fusion (RRF) of dense and sparse results.
        
        Formula: score = sum(1 / (k + rank)) for each list containing the doc
        """
        # Create unified scoring
        doc_scores = {}
        doc_objects = {}
        
        # Score dense results
        for rank, chunk in enumerate(dense_results):
            doc_key = hash(chunk.content + chunk.source)
            doc_scores[doc_key] = doc_scores.get(doc_key, 0) + 1 / (k + rank + 1)
            doc_objects[doc_key] = chunk
        
        # Score sparse results
        for rank, chunk in enumerate(sparse_results):
            doc_key = hash(chunk.content + chunk.source)
            doc_scores[doc_key] = doc_scores.get(doc_key, 0) + 1 / (k + rank + 1)
            if doc_key not in doc_objects:
                doc_objects[doc_key] = chunk
        
        # Sort by fused score
        sorted_docs = sorted(
            doc_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Return re-scored chunks
        result = []
        for doc_key, score in sorted_docs:
            chunk = doc_objects[doc_key]
            # Update score and method
            new_chunk = RetrievedChunk(
                content=chunk.content,
                source=chunk.source,
                score=score,
                metadata={**chunk.metadata, "rrf_score": score},
                retrieval_method="hybrid"
            )
            result.append(new_chunk)
        
        return result
    
    async def _rerank(
        self, 
        query: str, 
        candidates: List[RetrievedChunk]
    ) -> List[RetrievedChunk]:
        """Re-rank candidates using cross-encoder"""
        if not self._reranker or not candidates:
            return candidates
        
        # Prepare pairs for cross-encoder
        pairs = [(query, chunk.content) for chunk in candidates]
        
        # Score pairs
        scores = self._reranker.predict(pairs)
        
        # Re-sort by reranker score
        scored_chunks = list(zip(candidates, scores))
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # Return re-scored chunks
        result = []
        for chunk, score in scored_chunks:
            new_chunk = RetrievedChunk(
                content=chunk.content,
                source=chunk.source,
                score=float(score),
                metadata={**chunk.metadata, "reranker_score": float(score)},
                retrieval_method=f"{chunk.retrieval_method}+reranked"
            )
            result.append(new_chunk)
        
        return result
    
    def _assemble_context(self, chunks: List[RetrievedChunk]) -> str:
        """Assemble final context from ranked chunks"""
        if not chunks:
            return ""
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source_tag = f"[{i}] {chunk.source}"
            context_parts.append(f"{source_tag}\n{chunk.content}\n")
        
        return "\n---\n".join(context_parts)
    
    def _build_qdrant_filter(self, filters: Dict) -> Optional[Any]:
        """Build Qdrant filter from dict"""
        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue
            
            conditions = []
            for key, value in filters.items():
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
            
            return Filter(must=conditions) if conditions else None
        except:
            return None


class RAGPipeline:
    """
    High-level RAG pipeline integration for ROXY Core.
    Drop-in replacement for current RAG implementation.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.engine = HybridRAGEngine(
            qdrant_host=self.config.get("qdrant_host", "localhost"),
            qdrant_port=self.config.get("qdrant_port", 6333),
            embedding_model=self.config.get("embedding_model", "BAAI/bge-large-en-v1.5"),
            reranker_model=self.config.get("reranker_model", "BAAI/bge-reranker-v2-m3")
        )
        self._initialized = False
    
    async def ensure_initialized(self):
        """Lazy initialization"""
        if not self._initialized:
            await self.engine.initialize()
            self._initialized = True
    
    async def retrieve_context(
        self, 
        query: str, 
        context_type: str = "general",
        filters: Optional[Dict] = None
    ) -> str:
        """
        Main entry point for ROXY Core integration.
        
        Args:
            query: User query
            context_type: Type of context needed (code, docs, general)
            filters: Optional metadata filters
        
        Returns:
            Formatted context string for LLM consumption
        """
        await self.ensure_initialized()
        
        # Add context type to filters
        if filters is None:
            filters = {}
        filters["context_type"] = context_type
        
        result = await self.engine.query(query, filters)
        
        logger.info(
            f"RAG query: {query[:50]}... | "
            f"Retrieved {result.total_chunks} chunks in {result.query_time_ms:.1f}ms"
        )
        
        return result.context


# CLI for testing
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    async def test():
        pipeline = RAGPipeline()
        
        # Test queries
        queries = [
            "How does the ROXY Core IPC work?",
            "What are the mission supervisor capabilities?",
            "Explain the dual-GPU setup"
        ]
        
        for query in queries:
            print(f"\n{'='*60}")
            print(f"Query: {query}")
            print(f"{'='*60}")
            
            context = await pipeline.retrieve_context(query)
            print(f"\nRetrieved Context:\n{context[:1000]}...")
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(test())
    else:
        print("Usage: hybrid_rag_engine.py test")
