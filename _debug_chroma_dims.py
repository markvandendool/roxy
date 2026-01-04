#!/usr/bin/env python3
"""Debug script to diagnose embedding dimension mismatch"""
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
import sys

DB = Path("~/.roxy/chroma_db").expanduser()
print("DB path:", DB)
print("DB exists:", DB.exists())

if not DB.exists():
    print("ERROR: ChromaDB directory does not exist!")
    sys.exit(1)

try:
    client = chromadb.PersistentClient(path=str(DB))
    print("✓ Client created")
except Exception as e:
    print(f"ERROR creating client: {e}")
    sys.exit(1)

# List collections
try:
    cols = client.list_collections()
    print(f"Collections found: {len(cols)}")
    for c in cols:
        print(f"  - {c.name}")
except Exception as e:
    print(f"ERROR listing collections: {e}")
    sys.exit(1)

if not cols:
    print("No collections found.")
    sys.exit(0)

# Pick the collection ROXY uses (check what name roxy_commands.py uses)
NAME = None
for c in cols:
    if "mindsong" in c.name.lower() or "roxy" in c.name.lower():
        NAME = c.name
        break
if not NAME and cols:
    NAME = cols[0].name

print(f"\n=== Testing collection: {NAME} ===")

# Test with DefaultEmbeddingFunction (384 dim)
print("\n--- DefaultEmbeddingFunction (384 dim) ---")
try:
    ef_384 = embedding_functions.DefaultEmbeddingFunction()
    vec_384 = ef_384(["ping"])[0]
    print(f"Vector dimension: {len(vec_384)}")
    
    # Try to get collection with this embedder
    col_384 = client.get_collection(name=NAME, embedding_function=ef_384)
    print("✓ Collection retrieved with DefaultEmbeddingFunction")
    
    # Try a query
    r = col_384.query(query_texts=["ping"], n_results=1)
    print(f"✓ Query succeeded. Returned keys: {list(r.keys())}")
    print(f"  Results: {r['ids']}")
except Exception as e:
    print(f"✗ FAILED: {e}")

# Test with SentenceTransformer (768 dim) - if this is what's being used
print("\n--- SentenceTransformerEmbeddingFunction (768 dim) ---")
try:
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    ef_768 = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    vec_768 = ef_768(["ping"])[0]
    print(f"Vector dimension: {len(vec_768)}")
    
    # Try to get collection with this embedder
    col_768 = client.get_collection(name=NAME, embedding_function=ef_768)
    print("✓ Collection retrieved with SentenceTransformerEmbeddingFunction")
    
    # Try a query
    r = col_768.query(query_texts=["ping"], n_results=1)
    print(f"✓ Query succeeded. Returned keys: {list(r.keys())}")
    print(f"  Results: {r['ids']}")
except Exception as e:
    print(f"✗ FAILED: {e}")

print("\n=== Diagnosis Complete ===")
