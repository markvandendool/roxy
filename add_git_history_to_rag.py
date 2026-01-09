#!/usr/bin/env python3
"""
Add Git History to ROXY RAG
Indexes recent commits for codebase awareness

Usage:
  python3 add_git_history_to_rag.py /path/to/repo [--days 30]
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

import chromadb
from chromadb.utils import embedding_functions

EMBEDDING_FN = embedding_functions.DefaultEmbeddingFunction()

def get_embedding(text: str) -> list:
    """Get embedding using DefaultEmbeddingFunction (384-dim)"""
    return EMBEDDING_FN([text])[0]

def get_git_log(repo_path: str, days: int = 30) -> list:
    """Get git log entries from repo"""
    since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    result = subprocess.run(
        ["git", "-C", repo_path, "log", f"--since={since_date}",
         "--pretty=format:%H|%an|%ad|%s", "--date=short"],
        capture_output=True, text=True
    )

    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|", 3)
        if len(parts) >= 4:
            commits.append({
                "hash": parts[0][:8],
                "author": parts[1],
                "date": parts[2],
                "message": parts[3]
            })

    return commits

def get_commit_details(repo_path: str, commit_hash: str) -> str:
    """Get detailed commit info including changed files"""
    result = subprocess.run(
        ["git", "-C", repo_path, "show", "--stat", "--pretty=format:%B", commit_hash],
        capture_output=True, text=True
    )
    return result.stdout[:2000]  # Limit size

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 add_git_history_to_rag.py /path/to/repo [--days N]")
        sys.exit(1)

    repo_path = sys.argv[1]
    days = 30

    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])

    print(f"[GIT-RAG] Scanning {repo_path} for commits from last {days} days")

    # Get commits
    commits = get_git_log(repo_path, days)
    print(f"[GIT-RAG] Found {len(commits)} commits")

    if not commits:
        print("[GIT-RAG] No commits found")
        return

    # Connect to ChromaDB
    client = chromadb.PersistentClient(path=str(Path.home() / ".roxy" / "chroma_db"))

    try:
        collection = client.get_collection("mindsong_docs", embedding_function=EMBEDDING_FN)
    except:
        collection = client.create_collection(
            "mindsong_docs",
            embedding_function=EMBEDDING_FN,
            metadata={"description": "MindSong documentation for ROXY RAG"}
        )

    # Index commits
    indexed = 0
    for i, commit in enumerate(commits[:100]):  # Limit to 100 most recent
        try:
            # Create document text
            doc_text = f"""Git Commit: {commit['hash']}
Author: {commit['author']}
Date: {commit['date']}
Message: {commit['message']}
"""
            # Get details for significant commits (not just "fix typo" etc)
            if len(commit['message']) > 20:
                details = get_commit_details(repo_path, commit['hash'])
                doc_text += f"\nDetails:\n{details}"

            # Get embedding and add
            embedding = get_embedding(doc_text)
            doc_id = f"git_commit_{commit['hash']}"

            collection.upsert(
                ids=[doc_id],
                documents=[doc_text],
                embeddings=[embedding],
                metadatas=[{
                    "source": "git",
                    "type": "commit",
                    "hash": commit["hash"],
                    "author": commit["author"],
                    "date": commit["date"]
                }]
            )
            indexed += 1

            if (i + 1) % 10 == 0:
                print(f"  Indexed {i + 1}/{len(commits)} commits")

        except Exception as e:
            print(f"  Error indexing {commit['hash']}: {e}")

    print(f"\n[GIT-RAG] Indexed {indexed} commits")
    print(f"[GIT-RAG] Collection now has {collection.count()} documents")

if __name__ == "__main__":
    main()
