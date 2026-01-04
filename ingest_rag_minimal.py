#!/usr/bin/env python3
"""
RAG Ingestion (Minimal) - Index only onboarding docs for Chief acceptance test
"""

import sys
from pathlib import Path
import chromadb

ROXY_DIR = Path.home() / ".roxy"
CHROMA_PATH = ROXY_DIR / "chroma_db"
REPO_ROOT = Path.home() / "mindsong-juke-hub"

def chunk_text(text: str, max_chars: int = 1000) -> list[str]:
    """Split text into chunks"""
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
    
    return chunks if chunks else [text[:max_chars]]

def ingest_minimal():
    """Ingest only onboarding docs (fast)"""
    print(f"[INGEST] Minimal ingestion for acceptance testing")
    
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    
    try:
        client.delete_collection(name="mindsong_docs")
    except:
        pass
    
    collection = client.create_collection(
        name="mindsong_docs",
        metadata={"description": "ROXY RAG (minimal onboarding)"}
    )
    
    # Index only onboarding directory
    onboarding_dir = REPO_ROOT / "docs" / "onboarding"
    if not onboarding_dir.exists():
        print(f"[ERROR] {onboarding_dir} not found")
        return 0
    
    md_files = list(onboarding_dir.rglob("*.md"))
    print(f"[INGEST] Found {len(md_files)} onboarding markdown files")
    
    all_docs = []
    all_metas = []
    all_ids = []
    
    for md_file in md_files:
        text = md_file.read_text(encoding='utf-8', errors='ignore')
        if len(text) < 50:
            continue
        
        chunks = chunk_text(text)
        relative_path = md_file.relative_to(REPO_ROOT)
        
        for i, chunk in enumerate(chunks):
            all_docs.append(chunk)
            all_metas.append({
                "source": str(relative_path),
                "chunk": i
            })
            all_ids.append(f"{relative_path}_{i}")
    
    if all_docs:
        collection.add(
            documents=all_docs,
            metadatas=all_metas,
            ids=all_ids
        )
        print(f"[INGEST] Indexed {len(all_docs)} chunks")
    
    count = collection.count()
    print(f"[VERIFY] Collection count: {count}")
    return count

if __name__ == "__main__":
    try:
        count = ingest_minimal()
        if count > 0:
            print(f"\n✅ Minimal RAG ready: {count} documents")
            sys.exit(0)
        else:
            print("\n❌ Ingestion failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
