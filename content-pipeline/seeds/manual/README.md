# Manual Seeds Directory

**SKYBEAM Phase 7C — STORY-030/031**

This directory contains manually injected seed requests created via `skybeam inject`.

## Directory Structure

```
seeds/
├── manual/                    # CLI-injected seeds (this directory)
│   ├── .inject_index.json     # Deduplication index (24h window)
│   ├── inject_SEED_*.json     # Injected seed files
│   └── README.md              # This file
└── viral_short_*.json         # Auto-generated seeds from research
```

## Seed Format

Injected seeds follow this schema:

```json
{
  "seed_id": "SEED_YYYYMMDD_HHMMSS_xxxxxxxx",
  "created": "ISO-8601 timestamp",
  "type": "manual_inject",
  "priority": "low|normal|high",
  "source": "cli_inject",
  "url": "source video URL",
  "platform": "youtube|tiktok|instagram|twitter|unknown",
  "tags": ["tag1", "tag2"],
  "request": {
    "source_url": "...",
    "inject_priority": "...",
    "manual_injection": true
  },
  "meta": {
    "version": "1.0.0",
    "service": "skybeam_inject",
    "story_id": "SKYBEAM-STORY-030"
  }
}
```

## Usage

```bash
# Inject a video URL
skybeam inject "https://youtube.com/watch?v=VIDEO_ID"

# With priority and tags
skybeam inject "https://youtube.com/watch?v=VIDEO_ID" --priority high --tags "breaking,urgent"

# Preview without writing
skybeam inject "https://youtube.com/watch?v=VIDEO_ID" --dry-run
```

## Pipeline Integration

**Current Status:** Seeds are written but not yet auto-ingested.

**Integration Path:**
1. Script generator (`services/scripting/script_generator.py`) can be extended to scan `seeds/manual/`
2. Seeds should be processed in priority order (high > normal > low)
3. Processed seeds should be moved to `seeds/processed/` or marked with `processed: true`

**Future Work:**
- Add seed scanning to script generator
- Priority queue ordering
- Processed seed archiving
- Seed expiry (older than N days)

## Files

| File | Purpose |
|------|---------|
| `.inject_index.json` | Tracks recent injections for 24h dedup |
| `inject_SEED_*.json` | Individual seed files |
