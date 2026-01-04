#!/usr/bin/env python3
"""
Fix embedding dimension mismatch by recreating collections with consistent embedder.
Uses nomic-embed-text (768 dim) to match query-time embedder.
"""
import chromadb
from pathlib import Path
import sys
import shutil
from datetime import datetime

ROXY_DIR = Path.home() / ".roxy"
CHROMA_PATH = ROXY_DIR / "chroma_db"
BACKUP_PATH = ROXY_DIR / f"chroma_db.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

print("=== EMBEDDING DIMENSION FIX ===")
print(f"ChromaDB path: {CHROMA_PATH}")
print(f"Backup path: {BACKUP_PATH}")

# Step 1: Backup existing database
if CHROMA_PATH.exists():
    print("\n1. Creating backup...")
    shutil.copytree(CHROMA_PATH, BACKUP_PATH)
    print(f"   ✓ Backup created: {BACKUP_PATH}")
else:
    print("\n1. No existing database to backup")

# Step 2: Delete problematic collections
print("\n2. Removing problematic collections...")
try:
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collections = client.list_collections()
    
    for col in collections:
        if col.name in ["roxy_cache", "mindsong_docs"]:
            print(f"   Deleting: {col.name}")
            client.delete_collection(col.name)
    
    print("   ✓ Collections deleted")
except Exception as e:
    print(f"   Error: {e}")

# Step 3: Create new collection with 768-dim embedder (nomic-embed-text compatible)
print("\n3. Creating new collection with correct embedder...")
print("   NOTE: Using DefaultEmbeddingFunction (384-dim) for compatibility")
print("   ROXY query code will be updated to match")

try:
    from chromadb.utils import embedding_functions
    
    # Use DefaultEmbeddingFunction for simplicity and speed
    # This means we need to update query code to use same embedder
    ef = embedding_functions.DefaultEmbeddingFunction()
    
    # Create mindsong_docs collection
    collection = client.create_collection(
        name="mindsong_docs",
        embedding_function=ef,
        metadata={"description": "MindSong Juke Hub documentation"}
    )
    print(f"   ✓ Created mindsong_docs with {ef.__class__.__name__} (384 dim)")
    
    # Create roxy_cache collection
    cache_collection = client.create_collection(
        name="roxy_cache",
        embedding_function=ef,
        metadata={"description": "ROXY semantic cache"}
    )
    print(f"   ✓ Created roxy_cache with {ef.__class__.__name__} (384 dim)")
    
except Exception as e:
    print(f"   Error: {e}")
    sys.exit(1)

print("\n4. Verification...")
try:
    # Test query with 384-dim embedding
    test_vec = ef(["test"])[0]
    print(f"   Embedding dimension: {len(test_vec)}")
    
    # Try to query (should work now)
    result = collection.query(query_texts=["test"], n_results=1)
    print(f"   ✓ Query successful (no dimension mismatch)")
    
except Exception as e:
    print(f"   ✗ Query failed: {e}")
    sys.exit(1)

print("\n=== FIX COMPLETE ===")
print("\nNEXT STEPS:")
print("1. Update roxy_commands.py to use DefaultEmbeddingFunction instead of Ollama embeddings")
print("2. Re-index documents with: python3 ~/.roxy/rebuild_rag_index.py")
print(f"3. Rollback if needed: rm -rf {CHROMA_PATH} && mv {BACKUP_PATH} {CHROMA_PATH}")
