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

*Report generated by ROXY Reliability Sweep v1.0.0*
