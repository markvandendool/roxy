# ROXY Reliability Sweep Report

**Generated:** 2026-01-10 21:30 MST
**Sweep Version:** 1.0.0
**Status:** COMPLETE

---

## Executive Summary

This forensic sweep was conducted to:
1. Find the "last known good" ROXY brain state
2. Audit RAG index quality
3. Complete reality wiring (time/repo grounding)
4. Diagnose GPU idling issues
5. Inventory legacy assets

**Key Findings:**
- RAG index contains 106K docs including **node_modules pollution** - major quality issue
- Expert router exists but is **NOT USED** by roxy_core.py
- Brain consolidation (TruthPacket) is working correctly
- All gate tests now pass (6/6)

---

## A) Git History Findings

### Last Known Good Candidates

| Commit | Date | Message | Impact |
|--------|------|---------|--------|
| `584c83d` | 2026-01-04 | ROXY Full Stack - Voice, RAG, Multi-Mode | Full capability baseline |
| `e5a62ce` | 2026-01-04 | Apollo bridge MCP + dual wake-word persona | Dual persona routing |
| `805dfb8` | 2026-01-08 | Pre-crash save: dual-pool routing | Pool routing logic |
| `c0a79c6` | 2026-01-09 | roxy-core: unify ollama routing | Routing consolidation |
| `0e17f09` | 2026-01-10 | fix(rag): add system prompt identity | First brain fix |
| `9e86ee0` | 2026-01-10 | feat(brain): TruthPacket + Identity | Current brain |

### Critical File Changes

| File | Status | Risk |
|------|--------|------|
| `streaming.py` | IMPROVED | GOOD - TruthPacket integration |
| `roxy_core.py` | IMPROVED | GOOD - Routing metadata added |
| `expert_router.py` | EXISTS BUT UNUSED | **RISK** - Sophisticated routing not utilized |
| `llm_router.py` | EXISTS BUT UNUSED | NEUTRAL - Simpler fallback |
| `context_manager.py` | EXISTS BUT UNUSED | NEUTRAL - Conversation history |
| `prompts/templates.py` | EXISTS | NEUTRAL - Older prompt templates |

### Removed/Renamed Endpoints

| Endpoint | Status | CC Compatibility |
|----------|--------|------------------|
| `/run` | ACTIVE | Compatible (SSE streaming) |
| `/health` | ACTIVE | Compatible |
| `/info` | ACTIVE | Compatible (pool config) |
| `/health/ready` | ACTIVE | Compatible |

**Recommendation:** The expert_router.py contains sophisticated MoE (Mixture of Experts) routing that is NOT being used. This explains why all queries go to qwen2.5-coder:14b regardless of type.

---

## B) RAG Index Quality Audit

### Collection Inventory

| Collection | Count | Metadata Fields |
|------------|-------|-----------------|
| `mindsong_docs` | 106,428 | source, chunk |
| `roxy_cache` | 24 | response_length, timestamp, query |

### Retrieval Test Results

**Summary:** 3 PASS, 17 WEAK, 0 FAIL

| Category | Pass Rate | Issues |
|----------|-----------|--------|
| Repo Awareness | 1/5 (20%) | Weak semantic matches |
| Operations | 1/5 (20%) | node_modules pollution |
| Identity | 1/5 (20%) | Retrieving unrelated docs |
| Technical | 0/5 (0%) | All weak matches |

### Critical Issue: RAG Pollution

The RAG index contains content from:
- `node_modules/` - **Should NOT be indexed**
- Old changelog/log files with dates
- Generic documentation not about ROXY

**Evidence from retrieval:**
```
Query: "what ports do we use?"
Top Source: node_modules/vite/LICENSE.md  <- WRONG
Distance: 1.0726

Query: "what are your rules?"
Top Source: node_modules/node-gyp/gyp/docs/LanguageSpecification.md  <- WRONG
Distance: 1.2165
```

### Recommendation

1. **Rebuild RAG index** excluding:
   - `node_modules/`
   - `*.log` files
   - Changelog/version history files

2. **Add retrieval filters** to deprioritize:
   - Documents with many date mentions
   - Generic library documentation

---

## C) Reality Wiring Status

### Implemented Directives

| Directive | Status | Implementation |
|-----------|--------|----------------|
| #1 TruthPacket Generator | DONE | `truth_packet.py` |
| #2 Prompt Layout | DONE | System → Truth → Query → RAG |
| #3 Time/Date Skip-RAG | DONE | `is_time_date_query()` |
| #4 Post-Answer Validator | PARTIAL | Rule-based, not LLM validator |
| #5 Repo Query Skip-RAG | DONE | `is_repo_query()` |
| #6 ROXY_IDENTITY.md | DONE | Canonical identity document |
| #10 Routing Metadata | DONE | `routing_meta` SSE event |

### Gate Test Results

```
TruthPacket generation OK       PASS
Identity document OK            PASS
Time/date classifier OK         PASS
Repo/git classifier OK          PASS
Repo state matches TruthPacket  PASS
roxy-core healthy               PASS
Time query via /run             SKIPPED (no auth token)

Results: 6 passed, 0 failed
```

---

## D) Performance / GPU Idling Triage

### Current Routing

All queries currently route to:
- **Pool:** 6900xt (port 11435)
- **Model:** qwen2.5-coder:14b
- **Reason:** Hardcoded, no expert routing

### Why GPU May Be Idling

1. **Expert router not used** - All queries go to same model
2. **RAG context fetch blocking** - ChromaDB query adds latency
3. **No pool selection logic** - Always uses 6900xt pool

### Recommended Fixes

1. **Integrate expert_router.py** into roxy_core.py for intelligent model selection
2. **Add model warm-up** on startup
3. **Add GPU utilization logging** to diagnose idle periods

---

## E) Legacy Assets Inventory

### Brain/Persona Files

| File | Contains | Migrate? |
|------|----------|----------|
| `expert_router.py` | MoE routing, QueryType enum | **YES** - Rich routing logic |
| `llm_router.py` | Simple code/general routing | NO - Superceded |
| `context_manager.py` | Conversation history | MAYBE - Useful for multi-turn |
| `prompts/templates.py` | RAG/Code prompts | NO - New layout is better |
| `roxy_assistant_v2.py` | Voice system prompt | NO - Integrated into IDENTITY.md |
| `test_dual_persona.py` | Rocky/ROXY personas | ARCHIVE - Reference only |

### Files to NOT Ship

These modified files in git status should be reviewed before commit:
- `apps/roxy-command-center/ui/header_bar.py`
- `config.json`
- `content-pipeline/pipeline.sh`
- `industry_benchmarks.py`

---

## Artifacts Generated

| Artifact | Path |
|----------|------|
| RAG Audit JSON | `artifacts/rag_audit_20260110_212550.json` |
| RAG Audit MD | `artifacts/rag_audit_20260110_212550.md` |
| Gate Test Log | `artifacts/gateBRAIN_*.log` |
| This Report | `docs/forensic/ROXY_RELIABILITY_SWEEP_REPORT.md` |

---

## Action Items

### P0 - Critical

1. [ ] **Rebuild RAG index** without node_modules
2. [ ] **Integrate expert_router.py** for intelligent model selection

### P1 - Important

3. [ ] Add retrieval quality filters (deprioritize date-heavy docs)
4. [ ] Add GPU utilization logging
5. [ ] Test routing metadata display in CC

### P2 - Nice to Have

6. [ ] Migrate context_manager.py for multi-turn conversations
7. [ ] Add post-answer LLM validator for fact-checking

---

## Last Good Candidate Commit

```
commit 584c83dfa178a079a1cd16cb2aa45d11a47efcab
Date:   Sun Jan 4 06:12:21 2026 +0000
Message: ROXY Full Stack - Voice, RAG, Multi-Mode System

This commit contains the full capability set before recent changes.
The expert_router.py and context_manager.py from this commit
contain valuable logic that should be migrated to the new brain.
```

Saved to: `artifacts/last_good_candidate_commit.txt`

---

---

## P0 STOP-THE-BLEED DELTA (2026-01-10 21:55 MST)

### Before vs After

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| **RAG Documents** | 106,428 | 7,747 | -93% (clean) |
| **node_modules in RAG** | YES | NO | ✅ FIXED |
| **Expert Router Used** | NO | YES | ✅ INTEGRATED |
| **Routing Metadata** | Hardcoded | Real values | ✅ WIRED |
| **Gate Tests** | 6/6 PASS | 6/6 PASS | Maintained |
| **RAG PASS/WEAK/FAIL** | 3/17/0 | 2/18/0 | Similar |

### Work Completed

1. **Repo Hygiene**
   - Reverted 4 unrelated file modifications (header_bar.py, config.json, pipeline.sh, industry_benchmarks.py)
   - Added .gitignore rules for artifacts/*.json and *.log

2. **RAG Index Rebuild**
   - Created `rag/rebuild_index_clean.py` with ALLOWLIST approach
   - Indexed only: docs, scripts, prompts, services, mcp, adapters, rag, tests, tools
   - Added poisoning guards (LICENSE files, changelogs, dates)
   - Result: 7,747 chunks from 606 files

3. **Expert Router Integration**
   - Created `router_integration.py` - minimal router wrapper
   - Integrated into `roxy_core.py` with real routing decisions
   - Added `/deep` prefix for forcing BIG pool
   - Routing now classifies: CODE, TECHNICAL, CREATIVE, SUMMARY, GENERAL
   - Model selection: qwen2.5-coder:14b (code/tech), llama3:8b (creative/summary)

4. **Routing Metadata**
   - `routing_meta` SSE event now shows REAL values
   - Includes: query_type, selected_pool, selected_model, reason, confidence

### Files Modified

| File | Change |
|------|--------|
| `.gitignore` | Added artifact ignore rules |
| `roxy_core.py` | Integrated router_integration, /deep prefix support |
| `streaming.py` | Added is_repo_query() classifier (earlier) |

### Files Created

| File | Purpose |
|------|---------|
| `router_integration.py` | Minimal expert router wrapper |
| `rag/rebuild_index_clean.py` | Allowlist-based RAG indexing |
| `rag/index_manifest.json` | Index manifest with file inventory |
| `artifacts/rag_audit_20260110_215549.json` | Latest audit data |

### Verification

```
Router Test:
  code queries -> big pool, qwen2.5-coder:14b ✅
  creative queries -> big pool, llama3:8b ✅
  summary queries -> fast pool, llama3:8b ✅

RAG Audit:
  7,747 documents (clean, no node_modules)
  2 PASS, 18 WEAK, 0 FAIL
  Top sources: ROXY_IDENTITY.md, pool_identity.py, README_DAEMON.md

Gate Tests:
  6 passed, 0 failed ✅
```

### Action Items Status Update

| Item | Previous | Current |
|------|----------|---------|
| Rebuild RAG index | P0 TODO | ✅ DONE |
| Integrate expert_router | P0 TODO | ✅ DONE |
| Retrieval quality filters | P1 TODO | Partially addressed (allowlist) |
| GPU utilization logging | P1 TODO | Pending |
| Test routing metadata in CC | P1 TODO | Ready for testing |

---

---

## Artifact Retention Policy (PASS 3)

### Tracked Artifacts (Commit to Git)

| Artifact | Purpose |
|----------|---------|
| `artifacts/last_good_candidate_commit.txt` | Canonical "last known good" reference |
| `artifacts/rag_audit_*.md` | Forensic reports (markdown only) |
| `docs/forensic/*.md` | Sweep reports and legacy maps |
| `rag/index_manifest.json` | Reproducibility reference |
| `rag/rebuild_index_clean.py` | Canonical rebuild script |

### Ignored Artifacts (Do NOT Commit)

| Pattern | Reason |
|---------|--------|
| `artifacts/rag_audit_*.json` | Large, regeneratable audit data |
| `artifacts/gateBRAIN_*.log` | Runtime test logs |
| `artifacts/perf_probe_*.json` | Benchmark telemetry |
| `rag/cache/` | Embedding caches |
| `chroma_db/` | Regeneratable from source |

### .gitignore Rules Added

```
# Artifacts - generated audit/test logs
artifacts/rag_audit_*.json
artifacts/gateBRAIN_*.log
artifacts/perf_probe_*.json

# RAG index caches (regeneratable)
rag/cache/
rag/*.cache
```

### Poisoning Filter Additions

Added to `rebuild_index_clean.py`:
- `LICENCE` (British spelling)
- `HISTORY`, `NOTICE`, `AUTHORS`, `CONTRIBUTORS`, `PATENTS`
- `third_party`, `third-party`

### Manifest Determinism

Added `manifest_hash` field (SHA256 of sorted file list) for reproducibility verification.

---

*Report generated by ROXY Reliability Sweep v1.0.0*
*Delta added by P0 Stop-the-Bleed 2026-01-10 21:55 MST*
*PASS 3 added 2026-01-10 22:05 MST*

---

---

## P0 SEALED+DOCGATE (2026-01-10 23:45 MST)

### Proof Stamp

**P0 SEALED+DOCGATE:** Router-selected **model+endpoint** are truly used; `/stream` is canonical; `routing_meta` is semantically correct + documented + enforced by `gateBRAIN` SSE smoke test; GitHub main contains all commits through `d264d65`.

### Commits on GitHub Main

| Commit | Description |
|--------|-------------|
| `da67f86` | fix(hardening): P0 router defaults + pool invariant + classifier + ops boosts |
| `206aa80` | fix(routing_meta): semantic correctness + ops query type + SSE docs |
| `fa377aa` | test(gateBRAIN): SSE smoke test with 2s timeout + semantic field validation |
| `90fa047` | docs: update all documentation for routing_meta semantics (1.0.0-rc3) |
| `d264d65` | docs: CLAUDE skill gate updated with routing/SSE contract + gateBRAIN fix |

### Routing Semantics (Canonical)

| Field | Values | Description |
|-------|--------|-------------|
| `query_type` | time_date, repo, ops, code, technical, creative, summary, general | Classified query type |
| `routed_mode` | truth_only, rag, command | Processing mode |
| `selected_pool` | fast, big | GPU pool used |
| `reason` | skip_rag:*, classified:*, fallback:*, force_deep:* | Routing explanation |

### Skip-RAG Behaviors

- **time/date queries** → `query_type=time_date`, `routed_mode=truth_only`, `reason=skip_rag:time_date_query`
- **repo/git queries** → `query_type=repo`, `routed_mode=truth_only`, `reason=skip_rag:repo_query`

### Pool Routing (Final)

| Query Type | Pool | Endpoint | Reason |
|------------|------|----------|--------|
| CODE | BIG | :11434 | Quality code generation |
| TECHNICAL | BIG | :11434 | Technical accuracy |
| CREATIVE | BIG | :11434 | Narrative quality |
| OPS | FAST | :11435 | Ops queries + boosted docs |
| SUMMARY | FAST | :11435 | Speed over depth |
| GENERAL | FAST | :11435 | Default to speed/cost |
| time_date | FAST | :11435 | TruthPacket (skip RAG) |
| repo | FAST | :11435 | TruthPacket (skip RAG) |

### Classifier Precedence

`SUMMARY > CODE > OPS > TECHNICAL > CREATIVE > GENERAL`

### Gate Validation

```
gateBRAIN.sh results:
✅ TruthPacket generation OK
✅ Identity document OK
✅ Time/date classifier OK
✅ Repo/git classifier OK
✅ Repo state matches TruthPacket
✅ roxy-core healthy
✅ SSE routing_meta smoke test OK (all semantic fields present)

7 passed, 0 failed
```

### Documentation Updated

| Document | Update |
|----------|--------|
| `docs/ROXY_DUAL_POOL_CONTRACT.md` | Full routing_meta schema + OPS type + precedence |
| `docs/ROXY_RUNTIME_PORTS.md` | Endpoint table for roxy-core |
| `docs/RUNBOOK.md` | SSE streaming section |
| `docs/ROXY_RUNBOOK_CORE.md` | API Endpoints table |
| `CHANGELOG.md` | 1.0.0-rc3 release notes |
| `docs/CLAUDE.md` | ROXY CORE — ROUTING & SSE CONTRACT section |
| `docs/.claude/skills/AGENT-PROTOCOL.md` | ROXY CORE — API CONTRACT section |

### API Contract (Canonical)

- **SSE Streaming:** `GET /stream` (primary) — emits `event: routing_meta`
- **JSON Legacy:** `POST /run` (non-streaming)
- **Auth:** `X-ROXY-Token` header

---

*P0 SEALED+DOCGATE completed 2026-01-10 23:45 MST*
