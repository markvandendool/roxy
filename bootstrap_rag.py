#!/usr/bin/env python3
"""
RAG Bootstrap Script for ROXY
Initializes ChromaDB with MindSong documentation

Usage:
  python3 bootstrap_rag.py /path/to/docs
"""

import os
import sys
import hashlib
from pathlib import Path
from typing import List, Dict

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

EMBEDDING_FN = embedding_functions.DefaultEmbeddingFunction()

def get_embedding(text: str) -> List[float]:
    """Get embedding using DefaultEmbeddingFunction (384-dim)"""
    return EMBEDDING_FN([text])[0]

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
    return chunks

def get_file_hash(path: Path) -> str:
    """Get MD5 hash of file content"""
    return hashlib.md5(path.read_bytes()).hexdigest()[:8]

def process_file(path: Path) -> List[Dict]:
    """Process a single file into chunks with metadata"""
    text = path.read_text(errors='ignore')
    chunks = chunk_text(text)

    results = []
    for i, chunk in enumerate(chunks):
        doc_id = f"{path.stem}_{get_file_hash(path)}_{i}"
        results.append({
            "id": doc_id,
            "text": chunk,
            "metadata": {
                "source": str(path),
                "filename": path.name,
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
        })
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 bootstrap_rag.py /path/to/docs")
        sys.exit(1)

    docs_path = Path(sys.argv[1])
    if not docs_path.exists():
        print(f"Path not found: {docs_path}")
        sys.exit(1)

    # Initialize ChromaDB
    chroma_path = Path.home() / ".roxy" / "chroma_db"
    chroma_path.mkdir(parents=True, exist_ok=True)

    print(f"[RAG] Initializing ChromaDB at {chroma_path}")
    client = chromadb.PersistentClient(path=str(chroma_path))

    # Create or get collection
    try:
        collection = client.get_collection("mindsong_docs", embedding_function=EMBEDDING_FN)
        print(f"[RAG] Using existing collection: {collection.count()} docs")
    except:
        collection = client.create_collection(
            name="mindsong_docs",
            embedding_function=EMBEDDING_FN,
            metadata={"description": "MindSong documentation for ROXY RAG"}
        )
        print("[RAG] Created new collection")

    # Find all markdown files
    extensions = {'.md', '.txt', '.json'}
    files = []
    for ext in extensions:
        files.extend(docs_path.rglob(f"*{ext}"))

    print(f"[RAG] Found {len(files)} files to process")

    # Process files
    total_chunks = 0
    for i, file_path in enumerate(files):
        try:
            # Skip very large files
            if file_path.stat().st_size > 500000:
                print(f"  Skipping large file: {file_path.name}")
                continue

            chunks = process_file(file_path)
            if not chunks:
                continue

            # Get embeddings and add to collection
            for chunk in chunks:
                try:
                    embedding = get_embedding(chunk["text"])
                    collection.add(
                        ids=[chunk["id"]],
                        documents=[chunk["text"]],
                        embeddings=[embedding],
                        metadatas=[chunk["metadata"]]
                    )
                    total_chunks += 1
                except Exception as e:
                    print(f"  Chunk error: {e}")

            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1}/{len(files)} files, {total_chunks} chunks")

        except Exception as e:
            print(f"  Error processing {file_path}: {e}")

    print(f"\n[RAG] Complete! {total_chunks} chunks indexed")
    print(f"[RAG] Collection now has {collection.count()} documents")

if __name__ == "__main__":
    main()
