#!/usr/bin/env python3
"""
RAG Ingestion Script - Deterministic ChromaDB Rebuild
Indexes markdown files from mindsong-juke-hub into ChromaDB for RAG queries
"""

import sys
from pathlib import Path
import chromadb
from chromadb.config import Settings

ROXY_DIR = Path.home() / ".roxy"
CHROMA_PATH = ROXY_DIR / "chroma_db"
REPO_ROOT = Path.home() / "mindsong-juke-hub"

# CHIEF FIX: Index only key documentation, not entire repo
KEY_PATHS = [
    "docs",  # Primary documentation
    "README.md",
    "*.md"  # Top-level markdown only
]

def chunk_text(text: str, max_chars: int = 1000) -> list[str]:
    """Split text into chunks at paragraph boundaries"""
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) < max_chars:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def ingest_documents():
    """Ingest markdown files from repo into ChromaDB"""
    print(f"[INGEST] Starting RAG ingestion from {REPO_ROOT}")
    
    # Initialize ChromaDB
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    
    # Delete existing collection if present
    try:
        client.delete_collection(name="mindsong_docs")
        print("[INGEST] Deleted existing collection")
    except:
        pass
    
    # Create collection
    collection = client.create_collection(
        name="mindsong_docs",
        metadata={"description": "ROXY RAG knowledge base"}
    )
    
    # Find markdown files in key paths only (faster, more relevant)
    print("[INGEST] Scanning key paths for markdown files...")
    md_files = []
    
    # Docs directory
    docs_dir = REPO_ROOT / "docs"
    if docs_dir.exists():
        md_files.extend(docs_dir.rglob("*.md"))
    
    # Top-level markdown
    md_files.extend(REPO_ROOT.glob("*.md"))
    
    print(f"[INGEST] Found {len(md_files)} markdown files in key paths")
    
    # Batch processing to avoid collection lifecycle issues
    all_documents = []
    all_metadatas = []
    all_ids = []
    
    total_chunks = 0
    processed = 0
    
    for md_file in md_files:
        try:
            # Read file
            text = md_file.read_text(encoding='utf-8', errors='ignore')
            
            # Skip if empty or too small
            if len(text) < 50:
                continue
            
            # Chunk the text
            chunks = chunk_text(text)
            
            # Prepare batch data
            relative_path = md_file.relative_to(REPO_ROOT)
            for i, chunk in enumerate(chunks):
                all_documents.append(chunk)
                all_metadatas.append({
                    "source": str(relative_path),
                    "chunk": i,
                    "total_chunks": len(chunks)
                })
                all_ids.append(f"{relative_path}_{i}")
            
            total_chunks += len(chunks)
            processed += 1
            
            # Batch add every 5000 chunks to balance memory and speed
            if len(all_documents) >= 5000:
                collection.add(
                    documents=all_documents,
                    metadatas=all_metadatas,
                    ids=all_ids
                )
                print(f"[INGEST] Progress: {processed}/{len(md_files)} files, {total_chunks} chunks")
                all_documents = []
                all_metadatas = []
                all_ids = []
            
        except Exception as e:
            print(f"[WARN] Failed to ingest {md_file}: {e}")
    
    # Add remaining chunks
    if all_documents:
        collection.add(
            documents=all_documents,
            metadatas=all_metadatas,
            ids=all_ids
        )
        print(f"[INGEST] Final batch: {len(all_documents)} chunks")
    
    print(f"[INGEST] Complete: {total_chunks} chunks from {processed} files")
    
    # Verify by getting collection again (avoid stale reference)
    collection = client.get_collection(name="mindsong_docs")
    count = collection.count()
    print(f"[VERIFY] Collection count: {count}")
    
    return count

if __name__ == "__main__":
    try:
        count = ingest_documents()
        if count > 0:
            print(f"\n✅ RAG ingestion successful: {count} documents")
            sys.exit(0)
        else:
            print("\n❌ RAG ingestion failed: 0 documents")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ RAG ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
