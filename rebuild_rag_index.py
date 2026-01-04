#!/usr/bin/env python3
"""
ROXY RAG Index Rebuild - Deterministic ingestion script
Chief requirement: Single command to rebuild vector store from repo roots
"""

import chromadb
import requests
import sys
from pathlib import Path
import json
from typing import List, Dict

ROXY_DIR = Path.home() / ".roxy"
CHROMA_PATH = ROXY_DIR / "chroma_db"
COLLECTION_NAME = "mindsong_docs"

# Repo roots to index
REPO_ROOTS = [
    Path.home() / "mindsong-juke-hub" / "docs",
    Path.home() / "jarvis-docs",
]

# File extensions to index
INDEXED_EXTENSIONS = {'.md', '.txt', '.py', '.js', '.ts', '.json', '.yaml', '.yml'}

def get_embedding(text: str) -> List[float]:
    """Get embedding using DefaultEmbeddingFunction (384-dim)"""
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
    embedding_fn = DefaultEmbeddingFunction()
    return embedding_fn([text])[0]

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += (chunk_size - overlap)
    return chunks

def ingest_file(file_path: Path, collection, doc_id_base: int) -> int:
    """Ingest a single file into ChromaDB"""
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        # Skip empty files
        if not content.strip():
            return 0
        
        # Chunk the content
        chunks = chunk_text(content)
        
        # Add each chunk
        added = 0
        for i, chunk in enumerate(chunks):
            doc_id = f"doc_{doc_id_base}_{i}"
            embedding = get_embedding(chunk)
            
            metadata = {
                "source": str(file_path),
                "chunk_index": i,
                "total_chunks": len(chunks),
                "file_type": file_path.suffix
            }
            
            collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[metadata]
            )
            added += 1
        
        return added
    except Exception as e:
        print(f"  ⚠️  Failed to ingest {file_path}: {e}")
        return 0

def rebuild_index():
    """Rebuild the RAG index from scratch"""
    print("=== ROXY RAG INDEX REBUILD ===\n")
    
    # Initialize ChromaDB
    print(f"1. Connecting to ChromaDB: {CHROMA_PATH}")
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    
    # Delete existing collection if it exists
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"   Deleted existing collection: {COLLECTION_NAME}")
    except Exception:
        pass
    
    # Create new collection with DefaultEmbeddingFunction (384-dim)
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
    embedding_fn = DefaultEmbeddingFunction()
    
    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"description": "ROXY knowledge base - mindsong-juke-hub docs"}
    )
    print(f"   Created collection: {COLLECTION_NAME} (384-dim embeddings)\n")
    
    # Ingest files
    print("2. Ingesting files:")
    total_files = 0
    total_chunks = 0
    doc_id_counter = 0
    
    for root in REPO_ROOTS:
        if not root.exists():
            print(f"   ⚠️  Skipping non-existent root: {root}")
            continue
        
        print(f"   Indexing: {root}")
        
        for file_path in root.rglob("*"):
            if file_path.is_file() and file_path.suffix in INDEXED_EXTENSIONS:
                print(f"     • {file_path.relative_to(root)}", end="", flush=True)
                chunks_added = ingest_file(file_path, collection, doc_id_counter)
                if chunks_added > 0:
                    print(f" → {chunks_added} chunks")
                    total_files += 1
                    total_chunks += chunks_added
                    doc_id_counter += 1
                else:
                    print(" (skipped)")
    
    print(f"\n3. Ingestion complete:")
    print(f"   Files indexed: {total_files}")
    print(f"   Total chunks: {total_chunks}")
    print(f"   Collection count: {collection.count()}")
    
    # Verify with test query
    print("\n4. Verification test:")
    test_query = "onboarding documentation"
    test_embedding = get_embedding(test_query)
    print(f"   Embedding dimension: {len(test_embedding)}")
    results = collection.query(
        query_embeddings=[test_embedding],
        n_results=3,
        include=["documents", "metadatas"]
    )
    
    if results['documents'] and results['documents'][0]:
        print(f"   ✅ Query '{test_query}' returned {len(results['documents'][0])} results")
        print(f"   Sample: {results['metadatas'][0][0]['source']}")
    else:
        print("   ⚠️  No results for test query")
    
    print("\n=== RAG INDEX READY ===")

if __name__ == "__main__":
    rebuild_index()
