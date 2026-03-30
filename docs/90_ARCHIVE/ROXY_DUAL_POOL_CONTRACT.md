# ROXY Dual Pool Contract

This document defines the contract for ROXY's dual-GPU pool architecture.

## Pool Definitions

### BIG Pool (W5700X)
- **Port:** 11434
- **Canonical Name:** w5700x
- **Legacy Alias:** big
- **GPU:** AMD Radeon Pro W5700X
- **Purpose:** Heavy inference workloads requiring quality

**Models:**
- qwen2.5-coder:14b (primary code model)
- deepseek-coder:6.7b (backup)

**Use Cases:**
- Code generation and analysis
- Technical documentation
- Complex reasoning tasks
- Creative writing

### FAST Pool (6900XT)
- **Port:** 11435
- **Canonical Name:** 6900xt
- **Legacy Alias:** fast
- **GPU:** AMD Radeon RX 6900XT
- **Purpose:** Quick responses, summaries, triage

**Models:**
- llama3:8b (primary fast model)

**Use Cases:**
- Summarization
- Quick Q&A
- Secretary/triage tasks
- Low-latency responses

## Routing Contract

The expert router (`router_integration.py`) makes routing decisions based on query classification:

| Query Type | Pool | Model | Reason |
|------------|------|-------|--------|
| CODE | BIG | qwen2.5-coder:14b | Quality code generation |
| TECHNICAL | BIG | qwen2.5-coder:14b | Technical accuracy |
| CREATIVE | BIG | llama3:8b | Narrative quality |
| OPS | FAST | llama3:8b | Ops queries (port/service/restart) - fast + boosted docs |
| SUMMARY | FAST | llama3:8b | Speed over depth |
| GENERAL | FAST | llama3:8b | Default to speed (cost-efficient) |

### Special Query Types (RAG-Skipped)

These queries skip RAG retrieval and use TruthPacket for grounding:

| Query Type | Pool | Skip RAG | Reason |
|------------|------|----------|--------|
| time_date | FAST | Yes | Time/date queries use TruthPacket |
| repo | FAST | Yes | Git state queries use TruthPacket |

### Classifier Precedence

When multiple query types match, precedence order is:
1. SUMMARY (always wins)
2. CODE
3. OPS
4. TECHNICAL
5. CREATIVE
6. GENERAL (fallback)

## Force Deep Mode

Users can force BIG pool with `/deep` prefix:
```
/deep explain roxy-core architecture
```

This bypasses the router's classification and uses BIG pool regardless of query type.

## Routing Metadata

Every SSE response on `/stream` includes `event: routing_meta` with:

| Field | Values | Description |
|-------|--------|-------------|
| `query_type` | time_date, repo, ops, code, technical, creative, summary, general | Classified query type |
| `routed_mode` | truth_only, rag, command | How the query was processed |
| `selected_pool` | big, fast | Which GPU pool was used |
| `selected_endpoint` | http://127.0.0.1:11434 or :11435 | Ollama endpoint URL |
| `selected_model` | qwen2.5-coder:14b, llama3:8b | Model used for inference |
| `reason` | skip_rag:*, classified:*, fallback:*, force_deep:* | Routing explanation |
| `confidence` | 0.0-1.0 | Classifier confidence score |
| `skip_rag` | true, false | Whether RAG was skipped |
| `skip_rag_reason` | time_date_query, repo_query, null | Why RAG was skipped |
| `latency_ms` | integer | Routing decision latency |
| `rag_sources_top3` | array | Top 3 RAG sources (deduplicated) |

### Example routing_meta Events

**Time query (skip RAG):**
```json
{"query_type": "time_date", "routed_mode": "truth_only", "selected_pool": "fast", "reason": "skip_rag:time_date_query", "skip_rag": true}
```

**Code query (use RAG + BIG pool):**
```json
{"query_type": "code", "routed_mode": "rag", "selected_pool": "big", "reason": "classified:code:0.67", "skip_rag": false}
```

## Pool Health

Check pool health:
```bash
curl http://127.0.0.1:11434/api/tags  # BIG pool
curl http://127.0.0.1:11435/api/tags  # FAST pool
```

## Canonical Pool Names

The `pool_identity.py` module is the single source of truth for pool definitions:
- Use canonical names (w5700x, 6900xt) in new code
- Legacy aliases (big, fast) are supported but deprecated
