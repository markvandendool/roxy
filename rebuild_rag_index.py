#!/usr/bin/env python3
"""
ROXY RAG Index Rebuild - Deterministic ingestion script
Chief requirement: Single command to rebuild vector store from repo roots
"""

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

import chromadb


ROXY_DIR = Path.home() / ".roxy"
CHROMA_PATH = ROXY_DIR / "chroma_db"
DEFAULT_COLLECTION = "mindsong_docs"
DEFAULT_EXTENSIONS = {".md", ".txt", ".py", ".js", ".ts", ".json", ".yaml", ".yml"}


@dataclass(frozen=True)
class CollectionConfig:
    name: str
    roots: tuple[Path, ...]
    extensions: frozenset[str]
    description: str
    sample_query: str


COLLECTIONS: Dict[str, CollectionConfig] = {
    "mindsong_docs": CollectionConfig(
        name="mindsong_docs",
        roots=(
            Path.home() / "mindsong-juke-hub" / "docs",
            Path.home() / "jarvis-docs",
        ),
        extensions=frozenset(DEFAULT_EXTENSIONS),
        description="ROXY knowledge base - mindsong-juke-hub docs",
        sample_query="onboarding documentation",
    ),
    "roxy_legacy": CollectionConfig(
        name="roxy_legacy",
        roots=(ROXY_DIR / "brain" / "06_legacy",),
        extensions=frozenset({".md"}),
        description="ROXY legacy brain archive",
        sample_query="legacy architecture troubleshooting",
    ),
}


def get_embedding(text: str) -> List[float]:
    """Get embedding using DefaultEmbeddingFunction (384-dim)."""
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

    embedding_fn = DefaultEmbeddingFunction()
    return embedding_fn([text])[0]


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks."""
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def discover_files(config: CollectionConfig) -> List[Path]:
    files: List[Path] = []
    for root in config.roots:
        if not root.exists():
            continue
        for file_path in root.rglob("*"):
            if file_path.is_file() and file_path.suffix in config.extensions:
                files.append(file_path)
    return sorted(files)


def count_chunks(file_path: Path) -> int:
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    if not content.strip():
        return 0
    return len(chunk_text(content))


def build_doc_id(collection_name: str, file_path: Path, chunk_index: int) -> str:
    digest = hashlib.sha1(f"{collection_name}:{file_path}:{chunk_index}".encode("utf-8")).hexdigest()
    return f"{collection_name}:{digest}:{chunk_index}"


def analyze_collection(config: CollectionConfig, files: Sequence[Path]) -> dict:
    existing_roots = [str(root) for root in config.roots if root.exists()]
    missing_roots = [str(root) for root in config.roots if not root.exists()]
    skipped_empty = 0
    total_chunks = 0

    for file_path in files:
        chunk_count = count_chunks(file_path)
        if chunk_count == 0:
            skipped_empty += 1
            continue
        total_chunks += chunk_count

    return {
        "collection": config.name,
        "description": config.description,
        "roots": existing_roots,
        "missingRoots": missing_roots,
        "extensions": sorted(config.extensions),
        "files": len(files),
        "chunks": total_chunks,
        "skippedEmptyFiles": skipped_empty,
    }


def create_collection(client: chromadb.PersistentClient, config: CollectionConfig):
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

    embedding_fn = DefaultEmbeddingFunction()
    return client.create_collection(
        name=config.name,
        embedding_function=embedding_fn,
        metadata={"description": config.description},
    )


def ingest_collection(client: chromadb.PersistentClient, config: CollectionConfig, files: Sequence[Path]) -> dict:
    try:
        collection = client.get_collection(config.name)
    except Exception:
        collection = create_collection(client, config)

    indexed_files = 0
    indexed_chunks = 0

    for file_path in files:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        if not content.strip():
            continue

        chunks = chunk_text(content)
        added = 0
        for index, chunk in enumerate(chunks):
            doc_id = build_doc_id(config.name, file_path, index)
            metadata = {
                "source": str(file_path),
                "chunk_index": index,
                "total_chunks": len(chunks),
                "file_type": file_path.suffix,
                "collection": config.name,
            }
            collection.add(
                ids=[doc_id],
                embeddings=[get_embedding(chunk)],
                documents=[chunk],
                metadatas=[metadata],
            )
            added += 1

        if added > 0:
            indexed_files += 1
            indexed_chunks += added

    verification = {
        "query": config.sample_query,
        "results": 0,
        "sampleSource": None,
        "embeddingDimension": 0,
    }

    if indexed_chunks > 0:
        query_embedding = get_embedding(config.sample_query)
        verification["embeddingDimension"] = len(query_embedding)
        query_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
            include=["documents", "metadatas"],
        )
        result_docs = query_results.get("documents", [[]])[0] if query_results else []
        result_meta = query_results.get("metadatas", [[]])[0] if query_results else []
        verification["results"] = len(result_docs)
        if result_meta:
            verification["sampleSource"] = result_meta[0].get("source")

    return {
        "indexedFiles": indexed_files,
        "indexedChunks": indexed_chunks,
        "collectionCount": collection.count(),
        "verification": verification,
    }


def rebuild_collection(config: CollectionConfig, clear: bool, dry_run: bool) -> dict:
    files = discover_files(config)
    summary = analyze_collection(config, files)

    if dry_run:
        summary.update({
            "mode": "dry-run",
            "cleared": False,
            "createdCollection": False,
            "collectionCount": None,
            "verification": None,
        })
        return summary

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    cleared = False
    if clear:
        try:
            client.delete_collection(config.name)
            cleared = True
        except Exception:
            cleared = False

    collection_result = ingest_collection(client, config, files)
    summary.update({
        "mode": "apply",
        "cleared": cleared,
        "createdCollection": True,
        **collection_result,
    })
    return summary


def print_human(summary: dict) -> None:
    print("=== ROXY RAG INDEX REBUILD ===\n")
    print(f"Collection: {summary['collection']}")
    print(f"Roots: {', '.join(summary['roots']) or '(none found)'}")
    if summary["missingRoots"]:
        print(f"Missing roots: {', '.join(summary['missingRoots'])}")
    print(f"Files discovered: {summary['files']}")
    print(f"Chunks planned: {summary['chunks']}")
    print(f"Skipped empty files: {summary['skippedEmptyFiles']}")
    print(f"Mode: {summary['mode']}")

    if summary["mode"] == "apply":
        print(f"Collection cleared: {summary['cleared']}")
        print(f"Indexed files: {summary['indexedFiles']}")
        print(f"Indexed chunks: {summary['indexedChunks']}")
        print(f"Collection count: {summary['collectionCount']}")
        verification = summary["verification"] or {}
        print("Verification:")
        print(f"  Query: {verification.get('query')}")
        print(f"  Results: {verification.get('results')}")
        if verification.get("sampleSource"):
            print(f"  Sample source: {verification['sampleSource']}")

    print("\n=== RAG INDEX READY ===")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild ROXY RAG collections.")
    parser.add_argument(
        "--collection",
        choices=sorted(COLLECTIONS.keys()),
        default=DEFAULT_COLLECTION,
        help="Collection to rebuild (default: mindsong_docs)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear the selected collection before rebuilding it",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report counts without mutating Chroma",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON summary output",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = COLLECTIONS[args.collection]
    clear = args.clear or (not args.dry_run and args.collection == DEFAULT_COLLECTION)
    summary = rebuild_collection(config, clear=clear, dry_run=args.dry_run)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print_human(summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
