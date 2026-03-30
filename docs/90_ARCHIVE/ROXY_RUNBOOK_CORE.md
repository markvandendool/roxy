# ROXY Core Runbook

Essential operations for running and maintaining ROXY.

## Starting ROXY

### Full Stack Start
```bash
~/.roxy/start-universe.sh full
```

### Minimal Start (Core Only)
```bash
~/.roxy/start-universe.sh minimal
```

### Status Check
```bash
~/.roxy/start-universe.sh status
```

## Service Management

### roxy-core (Main Daemon)
```bash
# Start
sudo systemctl start roxy-core

# Stop
sudo systemctl stop roxy-core

# Restart
sudo systemctl restart roxy-core

# Check status
sudo systemctl status roxy-core

# View logs
journalctl -u roxy-core -f
```

### Ollama Pools
```bash
# BIG pool (W5700X)
sudo systemctl start ollama-w5700x
sudo systemctl status ollama-w5700x

# FAST pool (6900XT)
sudo systemctl start ollama-6900xt
sudo systemctl status ollama-6900xt
```

## Health Checks

### roxy-core Health
```bash
curl http://127.0.0.1:8766/health
curl http://127.0.0.1:8766/health/ready
curl http://127.0.0.1:8766/info
```

### Pool Health
```bash
# List models on BIG pool
curl http://127.0.0.1:11434/api/tags

# List models on FAST pool
curl http://127.0.0.1:11435/api/tags
```

## API Endpoints (Chief Directive H)

| Endpoint | Method | Auth | Response | Notes |
|----------|--------|------|----------|-------|
| `/stream` | GET | X-ROXY-Token | SSE | Primary streaming endpoint; emits `routing_meta` event |
| `/run` | POST | X-ROXY-Token | JSON | Non-streaming (legacy-friendly) |
| `/health` | GET | None | JSON | Health check |

**SSE Endpoint: `/stream`**
- Token via `X-ROXY-Token` header
- Emits `event: routing_meta` with pool/model/confidence data
- Example: `curl -sN "http://127.0.0.1:8766/stream?command=hello" -H "X-ROXY-Token: $TOKEN"`

**JSON Endpoint: `/run`**
- Non-streaming JSON response
- Use for scripts/automation that don't need SSE

**routing_meta event fields:**
- `query_type`: time_date | repo | ops | code | summary | technical | general
- `routed_mode`: truth_only | rag | command
- `selected_pool`: fast | big
- `selected_endpoint`: http://127.0.0.1:11435 (fast) or :11434 (big)
- `skip_rag`: true/false
- `rag_sources_top3`: deduplicated top sources

## RAG Index Management

### Rebuild Index
```bash
cd ~/.roxy
python3 rag/rebuild_index_clean.py
```

### Verify Index
```bash
python3 scripts/rag_audit.py
```

### Check Index Manifest
```bash
cat ~/.roxy/rag/index_manifest.json | jq '.total_chunks, .manifest_hash'
```

## Brain Verification

Run gateBRAIN to verify brain components:
```bash
bash ~/.roxy/scripts/gateBRAIN.sh
```

Expected output: 6 passed, 0 failed

## Troubleshooting

### GPU Idling
1. Check if queries are routing correctly:
   - Look for `routing_meta` in SSE stream
   - Verify `selected_pool` matches expected
2. Check Ollama pool status
3. Run benchmark to warm up models

### RAG Returns Irrelevant Results
1. Check index manifest for unexpected files
2. Rebuild with clean allowlist
3. Add query-specific docs if needed

### TruthPacket Issues
1. Verify truth_packet.py exists
2. Check git repository state
3. Run gateBRAIN.sh

## Log Locations

| Log | Location |
|-----|----------|
| roxy-core | journalctl -u roxy-core |
| Ollama BIG | journalctl -u ollama-w5700x |
| Ollama FAST | journalctl -u ollama-6900xt |
| Artifacts | ~/.roxy/artifacts/ |

## Emergency Procedures

### Full Restart
```bash
~/.roxy/start-universe.sh stop
sleep 5
~/.roxy/start-universe.sh full
```

### Clear RAG Cache
```bash
rm -rf ~/.roxy/chroma_db
python3 ~/.roxy/rag/rebuild_index_clean.py
```

### Reset to Known Good
```bash
git checkout 584c83d -- roxy_core.py streaming.py
sudo systemctl restart roxy-core
```
