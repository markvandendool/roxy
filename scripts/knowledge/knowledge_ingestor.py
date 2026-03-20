#!/usr/bin/env python3
"""
Knowledge Ingestor - Store extracted knowledge into existing RAG brain.

Part of ROXY-CHAT-EXTRACTION-V1 (EXTRACT-003)

Uses existing infrastructure:
- PostgresMemory.remember() for conversation storage with embeddings
- ChromaDB for vector search
- ingest_rag.py chunking patterns (1000 chars, paragraph boundaries)
"""

import json
import sys
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator, Set
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("[WARN] ChromaDB not available, vector search disabled", file=sys.stderr)

# Add parent directories to path for imports
ROXY_ROOT = Path.home() / ".roxy"
sys.path.insert(0, str(ROXY_ROOT))

try:
    from memory_postgres import PostgresMemory
except ImportError:
    PostgresMemory = None
    print("[WARN] PostgresMemory not available", file=sys.stderr)


# Constants
CHROMA_PATH = ROXY_ROOT / "chroma_db"
KNOWLEDGE_DIR = ROXY_ROOT / "knowledge"
COLLECTION_NAME = "extracted_knowledge"


def chunk_text(text: str, max_chars: int = 1000) -> List[str]:
    """
    Split text into chunks at paragraph boundaries.

    Reuses the exact pattern from ingest_rag.py for consistency.
    """
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


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash for deduplication."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


class KnowledgeIngestor:
    """
    Ingests extracted knowledge into existing RAG infrastructure.

    Deduplication:
    - Content hash check against existing documents
    - Session ID tracking to avoid re-ingesting

    Storage:
    - PostgresMemory for conversation-style retrieval
    - ChromaDB for vector search with metadata filtering
    """

    def __init__(self,
                 dry_run: bool = False,
                 skip_postgres: bool = False,
                 skip_chroma: bool = False):
        """
        Initialize the ingestor.

        Args:
            dry_run: If True, don't actually store anything
            skip_postgres: Skip PostgresMemory storage
            skip_chroma: Skip ChromaDB storage
        """
        self.dry_run = dry_run
        self.skip_postgres = skip_postgres
        self.skip_chroma = skip_chroma

        # Track what we've already ingested (for deduplication)
        self.seen_hashes: Set[str] = set()
        self.ingested_count = 0
        self.skipped_count = 0
        self.error_count = 0

        # Initialize PostgresMemory
        self.memory = None
        if not skip_postgres and PostgresMemory is not None:
            try:
                self.memory = PostgresMemory()
                print("[INIT] PostgresMemory connected", file=sys.stderr)
            except Exception as e:
                print(f"[WARN] PostgresMemory init failed: {e}", file=sys.stderr)

        # Initialize ChromaDB
        self.chroma_client = None
        self.collection = None
        if not skip_chroma and CHROMA_AVAILABLE:
            try:
                self.chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
                # Get or create the knowledge collection
                self.collection = self.chroma_client.get_or_create_collection(
                    name=COLLECTION_NAME,
                    metadata={"description": "Extracted knowledge from chat logs"}
                )
                print(f"[INIT] ChromaDB collection '{COLLECTION_NAME}' ready", file=sys.stderr)

                # Load existing hashes for deduplication
                self._load_existing_hashes()
            except Exception as e:
                print(f"[WARN] ChromaDB init failed: {e}", file=sys.stderr)
        elif not CHROMA_AVAILABLE:
            print(f"[SKIP] ChromaDB not available", file=sys.stderr)

    def _load_existing_hashes(self):
        """Load content hashes from existing ChromaDB documents."""
        if not self.collection:
            return

        try:
            # Get all document IDs (they contain the hash)
            result = self.collection.get(include=[])
            if result and result.get('ids'):
                for doc_id in result['ids']:
                    # IDs are formatted as: {type}_{hash[:16]}_{chunk_idx}
                    parts = doc_id.split('_')
                    if len(parts) >= 2:
                        # Extract partial hash for dedup
                        self.seen_hashes.add(parts[1])
                print(f"[INIT] Loaded {len(self.seen_hashes)} existing hashes", file=sys.stderr)
        except Exception as e:
            print(f"[WARN] Failed to load existing hashes: {e}", file=sys.stderr)

    def _is_duplicate(self, content_hash: str) -> bool:
        """Check if content has already been ingested."""
        # Check partial hash (first 16 chars)
        return content_hash[:16] in self.seen_hashes

    def ingest_knowledge(self, knowledge: Dict[str, Any]) -> bool:
        """
        Ingest a single knowledge item into the RAG brain.

        Args:
            knowledge: Knowledge dict from knowledge_extractor.py

        Returns:
            True if ingested, False if skipped/error
        """
        content = knowledge.get('content', '')
        if not content or len(content) < 20:
            return False

        # Compute hash for deduplication
        content_hash = compute_content_hash(content)

        if self._is_duplicate(content_hash):
            self.skipped_count += 1
            return False

        # Mark as seen
        self.seen_hashes.add(content_hash[:16])

        if self.dry_run:
            print(f"[DRY-RUN] Would ingest: {knowledge.get('type', 'UNKNOWN')} - {knowledge.get('title', '')[:50]}", file=sys.stderr)
            self.ingested_count += 1
            return True

        success = True

        # Store in PostgresMemory
        if self.memory and not self.skip_postgres:
            try:
                self._store_postgres(knowledge)
            except Exception as e:
                print(f"[ERROR] PostgresMemory store failed: {e}", file=sys.stderr)
                success = False

        # Store in ChromaDB
        if self.collection and not self.skip_chroma:
            try:
                self._store_chroma(knowledge, content_hash)
            except Exception as e:
                print(f"[ERROR] ChromaDB store failed: {e}", file=sys.stderr)
                success = False

        if success:
            self.ingested_count += 1
        else:
            self.error_count += 1

        return success

    def _store_postgres(self, knowledge: Dict[str, Any]):
        """Store knowledge in PostgresMemory."""
        knowledge_type = knowledge.get('type', 'UNKNOWN').lower()
        content = knowledge.get('content', '')
        title = knowledge.get('title', '')

        # Create query (summary) and response (full content)
        query = f"[{knowledge_type.upper()}] {title}"
        response = content

        # Build context metadata
        context = {
            "memory_type": f"knowledge_{knowledge_type}",
            "knowledge_type": knowledge.get('type', 'UNKNOWN'),
            "confidence": knowledge.get('confidence', 0.5),
            "tags": knowledge.get('tags', []),
            "actionable": knowledge.get('actionable', False),
            "source_file": knowledge.get('source_file', ''),
            "source_session": knowledge.get('source_session', ''),
            "extraction_timestamp": knowledge.get('timestamp', ''),
            "provenance": "chat_extraction_v1",
        }

        # Use session_id from knowledge
        session_id = knowledge.get('source_session', 'extraction-batch')

        self.memory.remember(
            query=query,
            response=response,
            session_id=session_id,
            context=context,
        )

    def _store_chroma(self, knowledge: Dict[str, Any], content_hash: str):
        """Store knowledge in ChromaDB with chunking."""
        knowledge_type = knowledge.get('type', 'UNKNOWN')
        content = knowledge.get('content', '')
        title = knowledge.get('title', '')

        # Chunk the content
        chunks = chunk_text(content)

        # Prepare batch data
        documents = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            # Document is the chunk prefixed with title for context
            doc = f"{title}\n\n{chunk}" if i == 0 else chunk
            documents.append(doc)

            # Metadata for filtering
            metadatas.append({
                "knowledge_type": knowledge_type,
                "confidence": knowledge.get('confidence', 0.5),
                "importance": knowledge.get('importance', 0.5),
                "actionable": knowledge.get('actionable', False),
                "source_file": knowledge.get('source_file', ''),
                "source_session": knowledge.get('source_session', ''),
                "timestamp": knowledge.get('timestamp', ''),
                "tags": ','.join(knowledge.get('tags', [])),
                "chunk_index": i,
                "total_chunks": len(chunks),
            })

            # Unique ID
            ids.append(f"{knowledge_type}_{content_hash[:16]}_{i}")

        # Add to collection
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )

    def ingest_file(self, path: Path) -> int:
        """
        Ingest all knowledge items from a JSONL file.

        Args:
            path: Path to extracted_*.jsonl file

        Returns:
            Number of items ingested
        """
        if not path.exists():
            print(f"[SKIP] {path} not found", file=sys.stderr)
            return 0

        print(f"[INGEST] {path.name}", file=sys.stderr)
        count = 0

        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    knowledge = json.loads(line)
                    if self.ingest_knowledge(knowledge):
                        count += 1
                except json.JSONDecodeError as e:
                    print(f"[WARN] Line {line_num}: JSON error: {e}", file=sys.stderr)
                except Exception as e:
                    print(f"[WARN] Line {line_num}: {e}", file=sys.stderr)

        return count

    def ingest_all(self, knowledge_dir: Path = None) -> Dict[str, int]:
        """
        Ingest all extracted knowledge files.

        Args:
            knowledge_dir: Directory containing extracted_*.jsonl files

        Returns:
            Dict with ingestion statistics
        """
        knowledge_dir = knowledge_dir or KNOWLEDGE_DIR

        print(f"\n=== Knowledge Ingestor ===", file=sys.stderr)
        print(f"Source: {knowledge_dir}", file=sys.stderr)
        print(f"Dry run: {self.dry_run}", file=sys.stderr)

        # Find all extracted files
        extracted_files = list(knowledge_dir.glob("extracted_*.jsonl"))

        if not extracted_files:
            print(f"[WARN] No extracted_*.jsonl files found in {knowledge_dir}", file=sys.stderr)
            return {"total": 0, "ingested": 0, "skipped": 0, "errors": 0}

        print(f"[INFO] Found {len(extracted_files)} extraction files", file=sys.stderr)

        for path in sorted(extracted_files):
            self.ingest_file(path)

        return self.get_stats()

    def get_stats(self) -> Dict[str, int]:
        """Get ingestion statistics."""
        return {
            "total": self.ingested_count + self.skipped_count + self.error_count,
            "ingested": self.ingested_count,
            "skipped": self.skipped_count,
            "errors": self.error_count,
        }

    def close(self):
        """Clean up resources."""
        # PostgresMemory handles its own connection lifecycle
        pass


def query_knowledge(query: str,
                    knowledge_type: str = None,
                    n_results: int = 5) -> List[Dict[str, Any]]:
    """
    Query the knowledge base.

    Args:
        query: Search query
        knowledge_type: Filter by type (PLAN, TODO, SCRIPT, etc.)
        n_results: Number of results to return

    Returns:
        List of matching knowledge chunks with metadata
    """
    if not CHROMA_AVAILABLE:
        print("[ERROR] ChromaDB not available for queries", file=sys.stderr)
        return []

    try:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        collection = client.get_collection(name=COLLECTION_NAME)

        # Build where filter
        where = None
        if knowledge_type:
            where = {"knowledge_type": knowledge_type}

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"]
        )

        # Format results
        formatted = []
        if results and results.get('documents'):
            for i, doc in enumerate(results['documents'][0]):
                formatted.append({
                    "content": doc,
                    "metadata": results['metadatas'][0][i] if results.get('metadatas') else {},
                    "distance": results['distances'][0][i] if results.get('distances') else 0,
                })

        return formatted

    except Exception as e:
        print(f"[ERROR] Query failed: {e}", file=sys.stderr)
        return []


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Ingest extracted knowledge into RAG brain')
    parser.add_argument('--input', '-i', default=str(KNOWLEDGE_DIR),
                        help='Directory containing extracted_*.jsonl files')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Show what would be ingested without storing')
    parser.add_argument('--skip-postgres', action='store_true',
                        help='Skip PostgresMemory storage')
    parser.add_argument('--skip-chroma', action='store_true',
                        help='Skip ChromaDB storage')
    parser.add_argument('--query', '-q', type=str,
                        help='Query the knowledge base instead of ingesting')
    parser.add_argument('--type', '-t', type=str,
                        help='Filter query by knowledge type')

    args = parser.parse_args()

    # Query mode
    if args.query:
        results = query_knowledge(args.query, knowledge_type=args.type)
        print(f"\n=== Query Results for: {args.query} ===\n")
        for i, result in enumerate(results, 1):
            print(f"[{i}] Type: {result['metadata'].get('knowledge_type', 'UNKNOWN')}")
            print(f"    Confidence: {result['metadata'].get('confidence', 0):.2f}")
            print(f"    Distance: {result['distance']:.4f}")
            print(f"    Content: {result['content'][:200]}...")
            print()
        return

    # Ingest mode
    ingestor = KnowledgeIngestor(
        dry_run=args.dry_run,
        skip_postgres=args.skip_postgres,
        skip_chroma=args.skip_chroma,
    )

    try:
        stats = ingestor.ingest_all(Path(args.input))

        print(f"\n=== Ingestion Summary ===", file=sys.stderr)
        print(f"Total processed: {stats['total']}", file=sys.stderr)
        print(f"Ingested: {stats['ingested']}", file=sys.stderr)
        print(f"Skipped (duplicates): {stats['skipped']}", file=sys.stderr)
        print(f"Errors: {stats['errors']}", file=sys.stderr)

        # Output JSON stats
        print(json.dumps(stats))

    finally:
        ingestor.close()


if __name__ == '__main__':
    main()
