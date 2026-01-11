#!/usr/bin/env python3
"""
RAG Index Rebuild - Clean Allowlist-Based Indexing
Chief's P0 Directive #5: Rebuild mindsong_docs with ALLOWLIST, not denylist.

This script:
1. Uses an allowlist of approved paths
2. Excludes node_modules, dist, build, venv, cache, logs
3. Saves index manifest for reproducibility
4. Adds poisoning guards during retrieval
"""

import os
import sys
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Tuple

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

ROXY_DIR = Path.home() / ".roxy"
CHROMA_DB_PATH = ROXY_DIR / "chroma_db"
MANIFEST_PATH = ROXY_DIR / "rag" / "index_manifest.json"

# ============================================================================
# ALLOWLIST CONFIGURATION
# ============================================================================

# Directories to include (relative to ROXY_DIR)
INCLUDE_DIRS = [
    "docs",
    "scripts",
    "prompts",
    "services",
    "mcp",
    "mcp-servers",
    "adapters",
    "rag",
    "tests",
    "tools",
]

# File patterns to include (in root)
INCLUDE_ROOT_FILES = [
    "*.py",
    "*.md",
    "*.json",
    "*.yaml",
    "*.yml",
    "*.sh",
]

# Explicit includes (high-value files)
EXPLICIT_INCLUDES = [
    "README.md",
    "README_CORE.md",
    "README_DAEMON.md",
    "ROXY_IDENTITY.md",
    "ROXY_BRAIN_CONTRACT.md",
    "roxy_core.py",
    "roxy_commands.py",
    "streaming.py",
    "truth_packet.py",
    "expert_router.py",
    "llm_router.py",
]

# ============================================================================
# DENYLIST (explicit exclusions)
# ============================================================================

EXCLUDE_PATTERNS = [
    "node_modules",
    "dist",
    "build",
    ".git",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "test-results",
    "evidence",
    "benchmarks",
    "logs",
    "archive",
    ".cache",
    "chroma_db",
    "whisper_models",
    "piper-voices",
    "chatterbox",
]

# File patterns to always exclude
EXCLUDE_FILE_PATTERNS = [
    "LICENSE",
    "LICENCE",
    "CHANGELOG",
    "HISTORY",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    ".log",
    ".bak",
    ".tmp",
    ".pyc",
    ".onnx",
    ".bin",
    ".gguf",
    # Additional boilerplate
    "third_party",
    "third-party",
    "NOTICE",
    "AUTHORS",
    "CONTRIBUTORS",
    "PATENTS",
]

# ============================================================================
# POISONING GUARDS
# ============================================================================

def is_poisoning_risk(file_path: str, content: str) -> Tuple[bool, str]:
    """
    Check if content is a poisoning risk (should be excluded or filtered).

    Returns:
        (is_risk, reason)
    """
    path_lower = file_path.lower()

    # node_modules is always poison
    if "node_modules" in path_lower:
        return True, "node_modules content"

    # License files are low-signal
    if "license" in path_lower or "licence" in path_lower:
        return True, "license file"

    # Changelog/version history has too many dates
    if "changelog" in path_lower or "history" in path_lower:
        return True, "changelog/history file"

    # Check for excessive date mentions (>5 dates suggests log/changelog)
    import re
    date_pattern = r'\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b'
    date_count = len(re.findall(date_pattern, content))
    if date_count > 5 and len(content) < 5000:
        return True, f"excessive dates ({date_count})"

    return False, ""


def should_include_file(file_path: Path) -> bool:
    """Check if file should be included in index."""
    path_str = str(file_path)

    # Check explicit excludes
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path_str:
            return False

    for pattern in EXCLUDE_FILE_PATTERNS:
        if path_str.endswith(pattern) or pattern in file_path.name:
            return False

    return True


def get_files_to_index() -> List[Path]:
    """Get list of files to index using allowlist approach."""
    files = []

    # Include explicit files from root
    for filename in EXPLICIT_INCLUDES:
        path = ROXY_DIR / filename
        if path.exists() and path.is_file():
            files.append(path)

    # Include files from allowed directories
    for dir_name in INCLUDE_DIRS:
        dir_path = ROXY_DIR / dir_name
        if dir_path.exists():
            for ext in ["*.py", "*.md", "*.json", "*.yaml", "*.yml", "*.sh", "*.txt"]:
                for file_path in dir_path.rglob(ext):
                    if should_include_file(file_path):
                        files.append(file_path)

    # Include root-level files matching patterns
    for pattern in INCLUDE_ROOT_FILES:
        for file_path in ROXY_DIR.glob(pattern):
            if file_path.is_file() and should_include_file(file_path):
                if file_path not in files:
                    files.append(file_path)

    return sorted(set(files))


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # Try to break at paragraph or sentence
        if end < len(text):
            for sep in ["\n\n", "\n", ". ", " "]:
                last_sep = chunk.rfind(sep)
                if last_sep > chunk_size // 2:
                    chunk = chunk[:last_sep + len(sep)]
                    end = start + len(chunk)
                    break

        chunks.append(chunk.strip())
        start = end - overlap

    return [c for c in chunks if c]


def rebuild_index(dry_run: bool = False) -> Dict:
    """Rebuild the RAG index from scratch."""
    print("=" * 60)
    print("ROXY RAG Index Rebuild (Clean Allowlist)")
    print("=" * 60)
    print()

    # Get files to index
    files = get_files_to_index()
    print(f"[1/5] Found {len(files)} files to index")

    # Show sample
    print("  Sample files:")
    for f in files[:10]:
        print(f"    - {f.relative_to(ROXY_DIR)}")
    if len(files) > 10:
        print(f"    ... and {len(files) - 10} more")
    print()

    if dry_run:
        print("[DRY RUN] Would rebuild index with these files")
        return {"files": len(files), "dry_run": True}

    # Initialize ChromaDB
    print("[2/5] Initializing ChromaDB...")
    client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
    ef = DefaultEmbeddingFunction()

    # Delete existing collection
    try:
        client.delete_collection("mindsong_docs")
        print("  Deleted existing collection")
    except Exception:
        pass

    collection = client.create_collection(
        name="mindsong_docs",
        embedding_function=ef,
        metadata={"description": "ROXY knowledge base (clean rebuild)"}
    )
    print("  Created new collection")
    print()

    # Process files
    print("[3/5] Processing files...")
    documents = []
    metadatas = []
    ids = []
    skipped = []

    for file_path in files:
        try:
            content = file_path.read_text(errors="ignore")

            # Check for poisoning
            is_risk, reason = is_poisoning_risk(str(file_path), content)
            if is_risk:
                skipped.append((file_path, reason))
                continue

            # Chunk the content
            chunks = chunk_text(content)
            rel_path = str(file_path.relative_to(ROXY_DIR))

            for i, chunk in enumerate(chunks):
                doc_id = hashlib.md5(f"{rel_path}:{i}".encode()).hexdigest()[:16]
                documents.append(chunk)
                metadatas.append({
                    "source": rel_path,
                    "chunk": i,
                    "total_chunks": len(chunks),
                })
                ids.append(doc_id)

        except Exception as e:
            skipped.append((file_path, str(e)))

    print(f"  Processed: {len(documents)} chunks from {len(files)} files")
    print(f"  Skipped: {len(skipped)} files")
    for path, reason in skipped[:5]:
        print(f"    - {path.name}: {reason}")
    print()

    # Add to collection in batches
    print("[4/5] Adding to ChromaDB...")
    batch_size = 500
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i:i + batch_size]
        batch_meta = metadatas[i:i + batch_size]
        batch_ids = ids[i:i + batch_size]

        collection.add(
            documents=batch_docs,
            metadatas=batch_meta,
            ids=batch_ids
        )
        print(f"  Added batch {i // batch_size + 1}/{(len(documents) + batch_size - 1) // batch_size}")
    print()

    # Save manifest
    print("[5/5] Saving manifest...")
    files_indexed = sorted([str(f.relative_to(ROXY_DIR)) for f in files if f not in [s[0] for s in skipped]])

    # Create deterministic hash for reproducibility
    content_hash = hashlib.sha256()
    for f in files_indexed:
        content_hash.update(f.encode())
    manifest_hash = content_hash.hexdigest()[:16]

    manifest = {
        "timestamp": datetime.now().isoformat(),
        "manifest_hash": manifest_hash,
        "total_files": len(files),
        "total_chunks": len(documents),
        "skipped_count": len(skipped),
        "include_dirs": sorted(INCLUDE_DIRS),
        "exclude_patterns": sorted(EXCLUDE_PATTERNS),
        "files_indexed": files_indexed,
        "skipped_files": sorted([(str(p.relative_to(ROXY_DIR)), r) for p, r in skipped]),
    }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  Saved: {MANIFEST_PATH}")
    print()

    print("=" * 60)
    print(f"REBUILD COMPLETE: {len(documents)} chunks from {len(files)} files")
    print("=" * 60)

    return manifest


def add_retrieval_filter(chunks: List[Dict], query: str) -> List[Dict]:
    """
    Filter retrieved chunks to remove poisoning sources.
    Apply this BEFORE passing to prompt.
    """
    filtered = []
    for chunk in chunks:
        source = chunk.get("metadata", {}).get("source", "")
        content = chunk.get("document", "")

        is_risk, _ = is_poisoning_risk(source, content)
        if not is_risk:
            filtered.append(chunk)

    return filtered


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Rebuild ROXY RAG index")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be indexed")
    args = parser.parse_args()

    rebuild_index(dry_run=args.dry_run)
