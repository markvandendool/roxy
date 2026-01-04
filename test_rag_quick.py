#!/usr/bin/env python3
"""Quick RAG test - verify embedding dimensions match"""
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from pathlib import Path

CHROMA_PATH = Path.home() / ".roxy" / "chroma_db"
embedding_fn = DefaultEmbeddingFunction()

print("Testing RAG embedding configuration...")
print(f"1. ChromaDB path: {CHROMA_PATH}")

# Test embedding function
test_vec = embedding_fn(["test"])[0]
print(f"2. DefaultEmbeddingFunction dimension: {len(test_vec)}")

# Connect to DB
client = chromadb.PersistentClient(path=str(CHROMA_PATH))
collections = client.list_collections()
print(f"3. Collections: {[c.name for c in collections]}")

if collections:
    # Get collection WITH embedding function
    col = client.get_collection("mindsong_docs", embedding_function=embedding_fn)
    print(f"4. Collection count: {col.count()}")
    
    # Try a query
    try:
        results = col.query(query_texts=["test"], n_results=1)
        print(f"5. Query test: ✅ SUCCESS")
        print(f"   Results: {len(results['documents'][0])} docs")
    except Exception as e:
        print(f"5. Query test: ❌ FAILED - {e}")
else:
    print("4. No collections found (rebuild in progress)")
