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
| SUMMARY | FAST | llama3:8b | Speed over depth |
| GENERAL | BIG | qwen2.5-coder:14b | Default to quality |

## Force Deep Mode

Users can force BIG pool with `/deep` prefix:
```
/deep explain roxy-core architecture
```

This bypasses the router's classification and uses BIG pool regardless of query type.

## Routing Metadata

Every response includes `routing_meta` SSE event with:
- `selected_pool`: big | fast
- `selected_endpoint`: http://127.0.0.1:11434 | http://127.0.0.1:11435
- `selected_model`: actual model name
- `query_type`: code | technical | creative | summary | general
- `reason`: routing explanation
- `confidence`: 0.0-1.0

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
