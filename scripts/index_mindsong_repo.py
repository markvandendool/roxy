#!/usr/bin/env python3
"""
Index mindsong-juke-hub repository for ROXY
Run this to build full semantic index
"""
import sys
import asyncio
sys.path.insert(0, '/opt/roxy/services')

from repository_indexer import get_repo_indexer

async def main():
    repo_path = "/opt/roxy/mindsong-juke-hub"
    
    print(f"🔍 Indexing {repo_path} repository...")
    print("This will create a full semantic index for instant retrieval.")
    print("")
    
    indexer = get_repo_indexer(repo_path)
    
    # Check if already indexed
    stats = indexer.get_stats()
    if stats.get('total_chunks', 0) > 0:
        print(f"✅ Repository already indexed: {stats['unique_files']} files, {stats['total_chunks']} chunks")
        response = input("Re-index? (y/N): ")
        if response.lower() != 'y':
            print("Skipping re-index.")
            return
    
    # Index repository
    print("Starting full repository index...")
    result = indexer.index_repository()
    
    print("")
    print("✅ Indexing complete!")
    print(f"   Files indexed: {result.get('indexed_files', 0)}/{result.get('total_files', 0)}")
    print(f"   Total chunks: {result.get('total_chunks', 0)}")
    print(f"   Errors: {len(result.get('errors', []))}")
    print("")
    print("ROXY now has full knowledge of the repository!")

if __name__ == "__main__":
    asyncio.run(main())



















