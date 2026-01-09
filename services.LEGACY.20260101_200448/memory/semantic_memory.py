#!/usr/bin/env python3
"""
ROXY Semantic Memory - Advanced semantic search with embeddings
"""
import logging
from typing import List, Dict, Any
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.memory.semantic')

class SemanticMemory:
    """Semantic memory with vector embeddings"""
    
    def __init__(self):
        self.chromadb = None
        self._init_chromadb()
    
    def _init_chromadb(self):
        """Initialize ChromaDB for semantic search"""
        try:
            import chromadb
            self.client = chromadb.HttpClient(host='localhost', port=8000)
            self.collection = self.client.get_or_create_collection(
                name='roxy_semantic_memory',
                metadata={'description': 'ROXY semantic memory with embeddings'}
            )
            logger.info("✅ Semantic memory (ChromaDB) initialized")
        except Exception as e:
            logger.warning(f"⚠️ ChromaDB unavailable: {e}")
            self.client = None
    
    def store_semantic(self, text: str, metadata: Dict = None, embedding_id: str = None):
        """Store semantic memory with embedding"""
        if not self.client:
            return
        
        import uuid
        doc_id = embedding_id or str(uuid.uuid4())
        
        self.collection.add(
            documents=[text],
            metadatas=[metadata or {}],
            ids=[doc_id]
        )
        logger.info(f"Stored semantic memory: {text[:50]}...")
    
    def search_semantic(self, query: str, n_results: int = 5) -> List[Dict]:
        """Search semantic memory"""
        if not self.client:
            return []
        
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        formatted = []
        for i in range(len(results['documents'][0])):
            formatted.append({
                'id': results['ids'][0][i],
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                'distance': results['distances'][0][i] if 'distances' in results else None
            })
        return formatted










