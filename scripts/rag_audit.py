#!/usr/bin/env python3
"""
RAG Audit Script - ROXY Reliability Sweep Part B
Tests RAG retrieval quality and identifies poisoning sources.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

ROXY_DIR = Path.home() / ".roxy"
CHROMA_DB_PATH = ROXY_DIR / "chroma_db"
ARTIFACTS_DIR = ROXY_DIR / "artifacts"

# Test queries organized by category
TEST_QUERIES = {
    "repo_awareness": [
        "what is ROXY?",
        "where is roxy_core.py?",
        "how do pools work?",
        "what is KHRONOS?",
        "how to start Command Center?",
    ],
    "operations": [
        "how to restart roxy-core?",
        "what ports do we use?",
        "how do tokens/auth work?",
        "what models are available?",
        "how does streaming work?",
    ],
    "identity": [
        "what is your job?",
        "what are your rules?",
        "who created you?",
        "what is MindSong?",
        "are you ROXY or Rocky?",
    ],
    "technical": [
        "what is TruthPacket?",
        "how does ChromaDB indexing work?",
        "what is the prompt layout?",
        "how does voice recognition work?",
        "what is the expert router?",
    ],
}


def get_collection_stats() -> Dict[str, Any]:
    """Get statistics for all ChromaDB collections."""
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        collections = client.list_collections()

        stats = {}
        for coll in collections:
            collection = client.get_collection(coll.name)
            count = collection.count()

            # Get sample metadata
            sample = collection.peek(limit=5)
            metadata_fields = set()
            for meta in sample.get("metadatas", []):
                if meta:
                    metadata_fields.update(meta.keys())

            stats[coll.name] = {
                "count": count,
                "metadata_fields": list(metadata_fields),
                "sample_ids": sample.get("ids", [])[:3],
            }

        return stats
    except Exception as e:
        return {"error": str(e)}


def run_retrieval_test(query: str, collection_name: str = "mindsong_docs", n_results: int = 3) -> Dict[str, Any]:
    """Run a single retrieval test and return results."""
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        ef = DefaultEmbeddingFunction()
        collection = client.get_collection(collection_name, embedding_function=ef)

        # Get embedding and query
        embedding = ef([query])[0]
        results = collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

        chunks = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results["distances"] else None

            # Check for date mentions (potential poisoning)
            import re
            date_matches = re.findall(r'\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? 20\d{2}\b', doc, re.IGNORECASE)

            chunks.append({
                "rank": i + 1,
                "source": meta.get("source", "unknown"),
                "distance": round(distance, 4) if distance else None,
                "preview": doc[:200] + "..." if len(doc) > 200 else doc,
                "full_length": len(doc),
                "date_mentions": date_matches[:5],  # First 5 date mentions
            })

        return {
            "query": query,
            "chunks": chunks,
            "error": None
        }
    except Exception as e:
        return {
            "query": query,
            "chunks": [],
            "error": str(e)
        }


def score_retrieval(query: str, chunks: List[Dict]) -> Tuple[str, str]:
    """Score a retrieval result: PASS/WEAK/FAIL with reason."""
    if not chunks:
        return "FAIL", "No chunks retrieved"

    query_lower = query.lower()

    # Check if top chunk seems relevant
    top_chunk = chunks[0]
    preview_lower = top_chunk["preview"].lower()

    # Simple relevance heuristics
    query_words = set(query_lower.split())
    chunk_words = set(preview_lower.split())
    overlap = query_words & chunk_words

    # Check for obvious irrelevance
    irrelevant_indicators = [
        "changelog", "version history", "release notes",
        "git log", "commit", "merge pull request"
    ]

    is_irrelevant = any(ind in preview_lower for ind in irrelevant_indicators)

    # Score based on multiple factors
    if top_chunk["distance"] and top_chunk["distance"] > 1.5:
        return "WEAK", f"High distance ({top_chunk['distance']}) - weak semantic match"

    if is_irrelevant and len(top_chunk["date_mentions"]) > 2:
        return "FAIL", "Retrieved changelog/log content with many dates (poisoning risk)"

    if len(overlap) >= 2:
        return "PASS", "Good keyword overlap with query"

    if top_chunk["distance"] and top_chunk["distance"] < 0.8:
        return "PASS", "Strong semantic match (low distance)"

    return "WEAK", "Moderate relevance, verify manually"


def find_poisoning_sources(collection_name: str = "mindsong_docs") -> List[Dict]:
    """Find documents with lots of dates that could poison time-related answers."""
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        collection = client.get_collection(collection_name)

        # Sample documents
        sample = collection.peek(limit=100)

        import re
        date_heavy_docs = []

        for i, doc in enumerate(sample.get("documents", [])):
            if not doc:
                continue

            # Count date patterns
            date_matches = re.findall(
                r'\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? 20\d{2}\b',
                doc, re.IGNORECASE
            )

            if len(date_matches) >= 3:
                meta = sample["metadatas"][i] if sample.get("metadatas") else {}
                date_heavy_docs.append({
                    "source": meta.get("source", "unknown"),
                    "date_count": len(date_matches),
                    "sample_dates": date_matches[:5],
                    "preview": doc[:150] + "..."
                })

        # Sort by date count
        date_heavy_docs.sort(key=lambda x: x["date_count"], reverse=True)
        return date_heavy_docs[:20]  # Top 20

    except Exception as e:
        return [{"error": str(e)}]


def main():
    """Run full RAG audit."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("ROXY RAG AUDIT")
    print("=" * 60)
    print()

    # 1. Collection inventory
    print("[1/4] Collecting ChromaDB inventory...")
    collection_stats = get_collection_stats()
    print(f"  Found {len(collection_stats)} collections")
    for name, stats in collection_stats.items():
        if "error" not in stats:
            print(f"    - {name}: {stats['count']} documents, fields: {stats['metadata_fields']}")
    print()

    # 2. Retrieval tests
    print("[2/4] Running retrieval sanity tests...")
    test_results = {}
    pass_count = 0
    weak_count = 0
    fail_count = 0

    for category, queries in TEST_QUERIES.items():
        test_results[category] = []
        for query in queries:
            result = run_retrieval_test(query)
            score, reason = score_retrieval(query, result["chunks"])
            result["score"] = score
            result["score_reason"] = reason
            test_results[category].append(result)

            if score == "PASS":
                pass_count += 1
                status = "\033[32mPASS\033[0m"
            elif score == "WEAK":
                weak_count += 1
                status = "\033[33mWEAK\033[0m"
            else:
                fail_count += 1
                status = "\033[31mFAIL\033[0m"

            print(f"  [{status}] {query[:40]:<40} - {reason[:30]}")

    print()
    print(f"  Summary: {pass_count} PASS, {weak_count} WEAK, {fail_count} FAIL")
    print()

    # 3. Poisoning sources
    print("[3/4] Scanning for date-heavy documents (poisoning risk)...")
    poisoning_sources = find_poisoning_sources()
    print(f"  Found {len(poisoning_sources)} documents with 3+ date mentions")
    for src in poisoning_sources[:5]:
        if "error" not in src:
            print(f"    - {src['source']}: {src['date_count']} dates")
    print()

    # 4. Save artifacts
    print("[4/4] Saving artifacts...")

    report = {
        "timestamp": timestamp,
        "collection_stats": collection_stats,
        "test_results": test_results,
        "poisoning_sources": poisoning_sources,
        "summary": {
            "pass": pass_count,
            "weak": weak_count,
            "fail": fail_count,
            "total": pass_count + weak_count + fail_count
        }
    }

    json_path = ARTIFACTS_DIR / f"rag_audit_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  Saved: {json_path}")

    # Generate markdown summary
    md_path = ARTIFACTS_DIR / f"rag_audit_{timestamp}.md"
    with open(md_path, "w") as f:
        f.write(f"# RAG Audit Report\n\n")
        f.write(f"**Generated:** {timestamp}\n\n")

        f.write("## Collection Inventory\n\n")
        for name, stats in collection_stats.items():
            if "error" not in stats:
                f.write(f"- **{name}**: {stats['count']} documents\n")
                f.write(f"  - Metadata fields: {', '.join(stats['metadata_fields'])}\n")

        f.write("\n## Retrieval Test Results\n\n")
        f.write(f"**Summary:** {pass_count} PASS, {weak_count} WEAK, {fail_count} FAIL\n\n")

        for category, results in test_results.items():
            f.write(f"### {category.replace('_', ' ').title()}\n\n")
            f.write("| Query | Score | Reason | Top Source |\n")
            f.write("|-------|-------|--------|------------|\n")
            for r in results:
                top_source = r["chunks"][0]["source"][:30] if r["chunks"] else "N/A"
                f.write(f"| {r['query'][:35]} | {r['score']} | {r['score_reason'][:25]} | {top_source} |\n")
            f.write("\n")

        f.write("## Potential Poisoning Sources\n\n")
        f.write("Documents with many date mentions (could confuse time-related queries):\n\n")
        for src in poisoning_sources[:10]:
            if "error" not in src:
                f.write(f"- **{src['source']}**: {src['date_count']} dates\n")
                f.write(f"  - Sample: {', '.join(src['sample_dates'][:3])}\n")

    print(f"  Saved: {md_path}")
    print()
    print("=" * 60)
    print("AUDIT COMPLETE")
    print("=" * 60)

    return report


if __name__ == "__main__":
    main()
