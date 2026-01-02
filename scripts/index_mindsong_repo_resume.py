#!/usr/bin/env python3
"""
Index mindsong-juke-hub repository for ROXY - RESUME CAPABLE
This script can safely resume after interruption (power outage, etc.)
ChromaDB upsert ensures no duplicates and handles updates automatically.
"""
import sys
import asyncio
import os
from pathlib import Path
sys.path.insert(0, '/opt/roxy/services.LEGACY.20260101_200448')

from repository_indexer import get_repo_indexer

async def main(auto_confirm=False):
    repo_path = "/opt/roxy/mindsong-juke-hub"
    
    print("=" * 70)
    print("🔍 ROXY Repository Indexer - RESUME CAPABLE")
    print("=" * 70)
    print(f"Repository: {repo_path}")
    print("")
    
    # Check if repo exists
    if not os.path.exists(repo_path):
        print(f"❌ Repository not found at {repo_path}")
        return
    
    indexer = get_repo_indexer(repo_path)
    
    # Check current status
    print("📊 Checking current index status...")
    stats = indexer.get_stats()
    
    if stats.get('error'):
        print(f"❌ Error: {stats['error']}")
        print("   Make sure ChromaDB is running: docker ps | grep chroma")
        return
    
    current_chunks = stats.get('total_chunks', 0)
    current_files = stats.get('unique_files', 0)
    
    print(f"✅ Current Index Status:")
    print(f"   📚 Chunks indexed: {current_chunks:,}")
    print(f"   📁 Files indexed: {current_files:,}")
    print("")
    
    if current_chunks > 0:
        print("💡 RESUME MODE: Indexing will resume automatically!")
        print("   - Existing files will be updated if changed")
        print("   - New files will be added")
        print("   - No duplicates will be created (ChromaDB upsert)")
        print("")
        if not auto_confirm:
            try:
                response = input("Continue indexing? (Y/n): ").strip().lower()
                if response == 'n':
                    print("Skipping.")
                    return
            except EOFError:
                # Non-interactive mode, auto-confirm
                print("⏩ Non-interactive mode: Auto-confirming...")
        else:
            print("⏩ Auto-confirmed: Starting indexing...")
    else:
        print("🆕 Starting fresh index...")
        print("")
    
    # Count total files to index (for progress estimation)
    print("📊 Counting files to index...")
    total_files = 0
    for root, dirs, files in os.walk(repo_path):
        # Filter skip directories
        dirs[:] = [d for d in dirs if d not in indexer.skip_dirs]
        for file in files:
            file_path = Path(root) / file
            if indexer._should_index_file(file_path):
                total_files += 1
    
    print(f"   Found ~{total_files:,} files to process")
    print("")
    
    # Start indexing
    print("🚀 Starting repository index...")
    print("   (This will update existing chunks and add new ones)")
    print("   (Progress logged every 100 files)")
    print("")
    
    try:
        result = indexer.index_repository()
        
        print("")
        print("=" * 70)
        print("✅ INDEXING COMPLETE!")
        print("=" * 70)
        print(f"   📁 Files processed: {result.get('total_files', 0):,}")
        print(f"   ✅ Files indexed: {result.get('indexed_files', 0):,}")
        print(f"   ⏭️  Files skipped: {result.get('skipped_files', 0):,}")
        print(f"   📚 Total chunks: {result.get('total_chunks', 0):,}")
        print(f"   ❌ Errors: {len(result.get('errors', []))}")
        print("")
        
        # Final stats
        final_stats = indexer.get_stats()
        print(f"📊 Final Index Status:")
        print(f"   📚 Total chunks: {final_stats.get('total_chunks', 0):,}")
        print(f"   📁 Unique files: {final_stats.get('unique_files', 0):,}")
        print("")
        print("🎉 ROXY now has full knowledge of the repository!")
        
    except KeyboardInterrupt:
        print("")
        print("⚠️  Indexing interrupted by user")
        print("💡 You can safely resume by running this script again!")
        print("   ChromaDB upsert will handle resuming automatically.")
        
        # Show current progress
        current_stats = indexer.get_stats()
        print(f"   Current progress: {current_stats.get('total_chunks', 0):,} chunks indexed")
        
    except Exception as e:
        print("")
        print(f"❌ Error during indexing: {e}")
        print("💡 You can safely resume by running this script again!")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check for --yes or -y flag for non-interactive mode
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv
    asyncio.run(main(auto_confirm=auto_confirm))

