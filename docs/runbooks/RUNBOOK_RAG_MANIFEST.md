# ROXY RAG Manifest Runbook

**Purpose:** Generate a deterministic manifest for RAG indexing (counts/bytes/config/hash)

## Generate manifest (no indexing)
```
/home/mark/.roxy/scripts/rag_manifest.py --repo /home/mark/mindsong-juke-hub
```

Output: `/home/mark/.roxy/artifacts/rag-manifest-YYYYMMDD_HHMMSS.json`

## Run repo indexing (resume capable)
```
/home/mark/.roxy/venv/bin/python /home/mark/.roxy/scripts/index_mindsong_repo_resume.py --repo /home/mark/mindsong-juke-hub --yes
```

## Validation gate
- Verify manifest file exists and includes:
  - `filesystem.total_files`
  - `filesystem.total_bytes`
  - `index.stats.total_chunks`
  - `manifest_sha256`

## Notes
- Use `ROXY_RAG_REPO` env to override repo path.
- Indexing uses ChromaDB upsert and can be resumed safely.

