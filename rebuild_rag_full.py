#!/usr/bin/env python3
"""
ROXY Full RAG Index Builder - Crash-Resistant Version
Indexes ALL markdown files from mindsong-juke-hub AND ~/.roxy/docs

Features:
- Batch processing to avoid memory issues
- Progress saving (can resume)
- Skips already-indexed files
- Uses ChromaDB's default embedding (384-dim)
"""

import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime
import chromadb
from chromadb.config import Settings

ROXY_DIR = Path.home() / ".roxy"
CHROMA_PATH = ROXY_DIR / "chroma_db"
PROGRESS_FILE = ROXY_DIR / "rag_index_progress.json"

# Sources to index
SOURCES = [
    Path.home() / "mindsong-juke-hub" / "docs",
    Path.home() / "mindsong-juke-hub",  # Top-level .md files
    ROXY_DIR / "docs",
    ROXY_DIR,  # Top-level .md files in .roxy
]

# Batch size to avoid memory issues
BATCH_SIZE = 100
MAX_FILE_SIZE = 200_000  # 200KB max per file
CHUNK_SIZE = 800  # Smaller chunks for better retrieval
CHUNK_OVERLAP = 100


def get_file_hash(path: Path) -> str:
    """Get hash of file for deduplication"""
    try:
        content = path.read_bytes()
        return hashlib.md5(content).hexdigest()[:12]
    except:
        return "error"


def chunk_text(text: str, max_chars: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    """Split text into overlapping chunks at paragraph boundaries"""
    # Clean the text
    text = text.strip()
    if not text:
        return []
    
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        # If adding this paragraph exceeds limit, save current and start new
        if len(current_chunk) + len(para) > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"
        else:
            current_chunk += para + "\n\n"
    
    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # Filter out tiny chunks
    return [c for c in chunks if len(c) > 50]


def load_progress() -> dict:
    """Load indexing progress"""
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text())
        except:
            pass
    return {"indexed_files": [], "last_run": None, "total_chunks": 0}


def save_progress(progress: dict):
    """Save indexing progress"""
    progress["last_run"] = datetime.now().isoformat()
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))


def find_all_markdown_files() -> list:
    """Find all markdown files from all sources"""
    all_files = []
    seen_paths = set()
    
    for source in SOURCES:
        if not source.exists():
            print(f"[SKIP] Source not found: {source}")
            continue
        
        # For directories, recurse into them
        if source.is_dir():
            # Get .md files recursively
            for md_file in source.rglob("*.md"):
                abs_path = str(md_file.resolve())
                if abs_path not in seen_paths:
                    seen_paths.add(abs_path)
                    all_files.append(md_file)
            
            # Also get top-level .md files if this is a repo root
            for md_file in source.glob("*.md"):
                abs_path = str(md_file.resolve())
                if abs_path not in seen_paths:
                    seen_paths.add(abs_path)
                    all_files.append(md_file)
    
    return sorted(all_files, key=lambda p: str(p))


def main():
    print("=" * 60)
    print("ROXY Full RAG Index Builder")
    print("=" * 60)
    
    # Load progress
    progress = load_progress()
    indexed_set = set(progress.get("indexed_files", []))
    
    print(f"\n[PROGRESS] Previously indexed: {len(indexed_set)} files")
    
    # Find all files
    print("\n[SCAN] Finding all markdown files...")
    all_files = find_all_markdown_files()
    print(f"[SCAN] Found {len(all_files)} markdown files total")
    
    # Filter to only new files
    new_files = [f for f in all_files if str(f) not in indexed_set]
    print(f"[SCAN] New files to index: {len(new_files)}")
    
    if not new_files:
        print("\n✅ All files already indexed!")
        return
    
    # Initialize ChromaDB
    print(f"\n[CHROMA] Connecting to {CHROMA_PATH}...")
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    
    # Get or create collection
    try:
        collection = client.get_collection("mindsong_docs")
        print(f"[CHROMA] Existing collection: {collection.count()} documents")
    except:
        collection = client.create_collection(
            name="mindsong_docs",
            metadata={"description": "ROXY RAG knowledge base - full index"}
        )
        print("[CHROMA] Created new collection")
    
    # Process files in batches
    total_chunks = progress.get("total_chunks", collection.count())
    batch_docs = []
    batch_metas = []
    batch_ids = []
    files_processed = 0
    files_skipped = 0
    
    print(f"\n[INDEX] Starting indexing of {len(new_files)} files...")
    print(f"[INDEX] Batch size: {BATCH_SIZE}, Chunk size: {CHUNK_SIZE}")
    print("-" * 60)
    
    for i, md_file in enumerate(new_files):
        try:
            # Skip large files
            file_size = md_file.stat().st_size
            if file_size > MAX_FILE_SIZE:
                print(f"  [SKIP] Too large ({file_size/1024:.0f}KB): {md_file.name}")
                files_skipped += 1
                continue
            
            # Skip binary/non-text
            if file_size == 0:
                files_skipped += 1
                continue
            
            # Read file
            try:
                text = md_file.read_text(encoding='utf-8', errors='ignore')
            except:
                files_skipped += 1
                continue
            
            # Skip empty/tiny files
            if len(text.strip()) < 100:
                files_skipped += 1
                continue
            
            # Chunk the text
            chunks = chunk_text(text)
            if not chunks:
                files_skipped += 1
                continue
            
            # Get relative path for display
            try:
                if "mindsong-juke-hub" in str(md_file):
                    rel_path = md_file.relative_to(Path.home() / "mindsong-juke-hub")
                elif ".roxy" in str(md_file):
                    rel_path = md_file.relative_to(ROXY_DIR)
                else:
                    rel_path = md_file.name
            except:
                rel_path = md_file.name
            
            file_hash = get_file_hash(md_file)
            
            # Add chunks to batch
            for j, chunk in enumerate(chunks):
                doc_id = f"{rel_path}_{file_hash}_{j}"
                batch_docs.append(chunk)
                batch_metas.append({
                    "source": str(rel_path),
                    "file_path": str(md_file),
                    "chunk": j,
                    "total_chunks": len(chunks),
                    "file_hash": file_hash
                })
                batch_ids.append(doc_id)
            
            total_chunks += len(chunks)
            files_processed += 1
            indexed_set.add(str(md_file))
            
            # Process batch if full
            if len(batch_docs) >= BATCH_SIZE:
                try:
                    collection.add(
                        documents=batch_docs,
                        metadatas=batch_metas,
                        ids=batch_ids
                    )
                    print(f"  [BATCH] Added {len(batch_docs)} chunks ({files_processed} files, {total_chunks} total)")
                except Exception as e:
                    print(f"  [ERROR] Batch add failed: {e}")
                    # Try adding one by one
                    for doc, meta, doc_id in zip(batch_docs, batch_metas, batch_ids):
                        try:
                            collection.add(
                                documents=[doc],
                                metadatas=[meta],
                                ids=[doc_id]
                            )
                        except:
                            pass
                
                # Clear batch
                batch_docs = []
                batch_metas = []
                batch_ids = []
                
                # Save progress
                progress["indexed_files"] = list(indexed_set)
                progress["total_chunks"] = total_chunks
                save_progress(progress)
            
            # Progress update every 100 files
            if (i + 1) % 100 == 0:
                print(f"  [PROGRESS] {i + 1}/{len(new_files)} files, {total_chunks} chunks")
        
        except Exception as e:
            print(f"  [ERROR] {md_file.name}: {e}")
            files_skipped += 1
            continue
    
    # Add remaining batch
    if batch_docs:
        try:
            collection.add(
                documents=batch_docs,
                metadatas=batch_metas,
                ids=batch_ids
            )
            print(f"  [FINAL] Added {len(batch_docs)} chunks")
        except Exception as e:
            print(f"  [ERROR] Final batch: {e}")
    
    # Save final progress
    progress["indexed_files"] = list(indexed_set)
    progress["total_chunks"] = total_chunks
    save_progress(progress)
    
    # Final stats
    print("\n" + "=" * 60)
    print("INDEXING COMPLETE")
    print("=" * 60)
    print(f"Files processed: {files_processed}")
    print(f"Files skipped:   {files_skipped}")
    print(f"Total chunks:    {total_chunks}")
    
    # Verify
    final_count = collection.count()
    print(f"\n[VERIFY] Collection count: {final_count}")
    
    if final_count > 1000:
        print("\n✅ RAG index successfully rebuilt!")
    else:
        print(f"\n⚠️ Index may be incomplete (expected 10,000+, got {final_count})")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Progress saved. Run again to resume.")
    except Exception as e:
        print(f"\n[FATAL] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
