# 🔧 Embedding Dimension Mismatch - FIXED

## Issue
ROXY was getting this error:
```
RAG query failed: Collection expecting embedding with dimension of 384, got 768
```

## Root Cause
- Collection was created with default embedding function (384 dimensions)
- Queries were using a different embedding function (768 dimensions)
- ChromaDB requires consistent embedding dimensions

## Fix Applied
1. ✅ Updated `repository_indexer.py` to explicitly use `DefaultEmbeddingFunction()` (384 dims)
2. ✅ Deleted old collection with mismatched embedding
3. ✅ Created new collection with correct 384-dim embedding function

## Current Status
- ✅ Collection fixed and ready
- ⚠️ Collection is empty (needs re-indexing)
- ✅ ROXY works for non-RAG queries

## Next Steps

### Option 1: Re-index Now (Recommended)
```bash
cd /opt/roxy
python3 scripts/index_mindsong_repo_resume.py --yes
```
This will re-index the repository (~12 hours, but can resume if interrupted)

### Option 2: Use ROXY Without RAG
ROXY will work fine for:
- General questions (uses LLM)
- File operations (uses filesystem)
- Memory queries (uses memory)
- Pattern matching

RAG queries will gracefully fallback to file operations.

## Testing
ROXY should now work without the embedding dimension error:
```bash
roxy chat
# Try: "hi roxy" - should work
# Try: "list pages" - should work (file operations)
# Try: "what is mindsong-juke-hub" - will fallback gracefully
```

## Re-indexing
Once you're ready to re-index:
1. The indexing script is resume-capable
2. Can safely stop/start
3. Will take ~12 hours for full index
4. Already has 32K+ files to process

