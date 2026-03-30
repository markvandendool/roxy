#!/usr/bin/env python3
"""
Index ROXY Documentation to RAG Brain

Indexes all markdown documentation from ~/.roxy/docs/ into ChromaDB
for semantic search via /memory/recall endpoint.

Usage:
    python index_docs_to_rag.py           # Index all docs
    python index_docs_to_rag.py --dry-run # Preview without indexing
    python index_docs_to_rag.py --clear   # Clear and reindex
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("[ERROR] ChromaDB not installed. Run: pip install chromadb", file=sys.stderr)
    sys.exit(1)

# Constants
ROXY_ROOT = Path.home() / ".roxy"
DOCS_DIR = ROXY_ROOT / "docs"
CHROMA_PATH = ROXY_ROOT / "chroma_db"

# Collection configuration
COLLECTIONS = {
    "roxy_onboarding": {
        "path": DOCS_DIR / "00_ONBOARDING",
        "description": "Agent onboarding documentation",
        "priority": "critical",
        "chunk_size": 1000,
    },
    "roxy_api": {
        "path": DOCS_DIR / "10_API_REFERENCE",
        "description": "API endpoint documentation",
        "priority": "critical",
        "chunk_size": 500,
    },
    "roxy_systems": {
        "path": DOCS_DIR / "20_SYSTEMS",
        "description": "System architecture documentation",
        "priority": "high",
        "chunk_size": 1000,
    },
    "roxy_protocols": {
        "path": DOCS_DIR / "30_PROTOCOLS",
        "description": "Protocol documentation (breakroom, SKOREQ)",
        "priority": "high",
        "chunk_size": 800,
    },
}


def chunk_markdown(text: str, max_chars: int = 1000) -> List[str]:
    """
    Split markdown text into chunks at paragraph/section boundaries.

    Preserves:
    - Headers with their content
    - Code blocks intact
    - Paragraph boundaries
    """
    chunks = []
    current_chunk = ""
    in_code_block = False

    lines = text.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        # Track code blocks
        if line.startswith('```'):
            in_code_block = not in_code_block

        # Check if this is a header
        is_header = line.startswith('#') and not in_code_block

        # If we're at a header and have content, might need to split
        if is_header and current_chunk and len(current_chunk) > max_chars // 2:
            chunks.append(current_chunk.strip())
            current_chunk = ""

        # Add line to current chunk
        current_chunk += line + "\n"

        # Check if we need to split (but not in code block)
        if not in_code_block and len(current_chunk) >= max_chars:
            # Try to find a good split point
            split_point = current_chunk.rfind('\n\n')
            if split_point > max_chars // 2:
                chunks.append(current_chunk[:split_point].strip())
                current_chunk = current_chunk[split_point:].strip() + "\n"
            else:
                chunks.append(current_chunk.strip())
                current_chunk = ""

        i += 1

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return [c for c in chunks if c and len(c) > 20]


def compute_hash(content: str) -> str:
    """Compute SHA256 hash for deduplication."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def index_document(
    collection,
    file_path: Path,
    chunk_size: int,
    priority: str,
    dry_run: bool = False
) -> int:
    """Index a single markdown document into the collection."""
    content = file_path.read_text(encoding='utf-8', errors='ignore')

    if len(content) < 50:
        print(f"  [SKIP] {file_path.name} (too short)", file=sys.stderr)
        return 0

    chunks = chunk_markdown(content, max_chars=chunk_size)

    if dry_run:
        print(f"  [DRY-RUN] {file_path.name} -> {len(chunks)} chunks", file=sys.stderr)
        return len(chunks)

    documents = []
    metadatas = []
    ids = []

    doc_hash = compute_hash(content)[:16]

    for i, chunk in enumerate(chunks):
        # Add context to first chunk (filename as title)
        if i == 0:
            doc = f"# {file_path.stem}\n\n{chunk}"
        else:
            doc = chunk

        documents.append(doc)

        metadatas.append({
            "source": str(file_path),
            "filename": file_path.name,
            "directory": file_path.parent.name,
            "priority": priority,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "indexed_at": datetime.now().isoformat(),
            "doc_hash": doc_hash,
        })

        ids.append(f"doc_{doc_hash}_{i}")

    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids,
    )

    print(f"  [INDEXED] {file_path.name} -> {len(chunks)} chunks", file=sys.stderr)
    return len(chunks)


def index_collection(
    client,
    name: str,
    config: Dict[str, Any],
    clear: bool = False,
    dry_run: bool = False
) -> Dict[str, int]:
    """Index all documents in a collection."""
    path = config["path"]

    if not path.exists():
        print(f"[SKIP] {name}: directory not found ({path})", file=sys.stderr)
        return {"files": 0, "chunks": 0}

    # Get or create collection
    if dry_run:
        print(f"\n[DRY-RUN] Would index to collection: {name}", file=sys.stderr)
        collection = None
    else:
        if clear:
            try:
                client.delete_collection(name=name)
                print(f"[CLEARED] Collection: {name}", file=sys.stderr)
            except Exception:
                pass

        collection = client.get_or_create_collection(
            name=name,
            metadata={
                "description": config["description"],
                "priority": config["priority"],
                "source_path": str(path),
            }
        )
        print(f"\n[COLLECTION] {name}: {config['description']}", file=sys.stderr)

    # Find all markdown files
    md_files = list(path.glob("**/*.md"))

    if not md_files:
        print(f"  [WARN] No markdown files found in {path}", file=sys.stderr)
        return {"files": 0, "chunks": 0}

    total_chunks = 0
    for md_file in sorted(md_files):
        if collection or dry_run:
            chunks = index_document(
                collection,
                md_file,
                config["chunk_size"],
                config["priority"],
                dry_run=dry_run
            )
            total_chunks += chunks

    return {"files": len(md_files), "chunks": total_chunks}


def main():
    parser = argparse.ArgumentParser(
        description='Index ROXY documentation to ChromaDB'
    )
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Preview without indexing')
    parser.add_argument('--clear', '-c', action='store_true',
                        help='Clear collections before indexing')
    parser.add_argument('--collection', '-C', type=str,
                        help='Index specific collection only')

    args = parser.parse_args()

    print("=" * 60, file=sys.stderr)
    print("ROXY Documentation Indexer", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"Docs directory: {DOCS_DIR}", file=sys.stderr)
    print(f"ChromaDB path: {CHROMA_PATH}", file=sys.stderr)
    print(f"Dry run: {args.dry_run}", file=sys.stderr)
    print(f"Clear: {args.clear}", file=sys.stderr)

    if not args.dry_run:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    else:
        client = None

    stats = {
        "total_files": 0,
        "total_chunks": 0,
        "collections": {}
    }

    collections_to_index = COLLECTIONS
    if args.collection:
        if args.collection in COLLECTIONS:
            collections_to_index = {args.collection: COLLECTIONS[args.collection]}
        else:
            print(f"[ERROR] Unknown collection: {args.collection}", file=sys.stderr)
            print(f"Available: {', '.join(COLLECTIONS.keys())}", file=sys.stderr)
            sys.exit(1)

    for name, config in collections_to_index.items():
        result = index_collection(
            client,
            name,
            config,
            clear=args.clear,
            dry_run=args.dry_run
        )
        stats["total_files"] += result["files"]
        stats["total_chunks"] += result["chunks"]
        stats["collections"][name] = result

    print("\n" + "=" * 60, file=sys.stderr)
    print("INDEXING SUMMARY", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"Total files indexed: {stats['total_files']}", file=sys.stderr)
    print(f"Total chunks created: {stats['total_chunks']}", file=sys.stderr)
    print("\nPer collection:", file=sys.stderr)
    for name, result in stats["collections"].items():
        print(f"  {name}: {result['files']} files, {result['chunks']} chunks", file=sys.stderr)

    # Output JSON stats
    print(json.dumps(stats))

    if not args.dry_run:
        print("\n[SUCCESS] Documentation indexed to RAG brain", file=sys.stderr)
        print("Query with: curl -X POST http://127.0.0.1:8766/memory/recall -d '{\"query\": \"...\"}'\n", file=sys.stderr)


if __name__ == '__main__':
    main()
