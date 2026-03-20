# EXECUTION TICKET: ULTRAMAX Phase 4 - Deduplicated Top 20

**Status:** DRAFT  
**Date:** 2026-03-20  
**Law 0 Compliance:** EXHAUSTIVE REUSE VERIFIED

---

## EXECUTIVE SUMMARY

After exhaustive sweep of Luno Orchestrator (`/luno-orchestrator/`) and ROXY (`~/.roxy/`), this ticket identifies **what exists, what needs enhancement, and what's genuinely new**. 

**Reality Check:** Luno + ROXY already have ~70% of proposed infrastructure. This ticket focuses on the **30% gap** that adds real leverage.

---

## INFRASTRUCTURE INVENTORY: LAW 0 REUSE MAP

### ✅ ALREADY EXISTS IN LUNO ORCHESTRATOR (REUSE, DON'T DUPLICATE)

| Category | Files | Maturity | Notes |
|----------|-------|----------|-------|
| **Secret Management** | `src/config/key-registry.ts`, `key-validator.ts`, `supabase-secrets-manager.ts` | HIGH | Centralized key registry, zero-trust pattern |
| **Circuit Breakers** | `src/safety/circuit-breaker.ts` | HIGH | Per-story + global, configurable thresholds |
| **Provider Fallback** | `src/llm/smart-router.ts` (1441 lines) | HIGH | Cascading fallback, free→paid chain |
| **Tool Governance** | `src/governance/ticket-gate.ts`, `bible-validator.ts` | HIGH | Forbidden ops, dangerous command blocks |
| **Mission Contracts** | `src/types/execution-spec.schema.ts` | HIGH | Typed schema with validation |
| **Spawn Briefing** | `src/prompts/unified-prompt-builder.ts` | HIGH | Context injection, skill loading |
| **Model Routing** | `src/llm/smart-router.ts`, `routing-rules.ts` | HIGH | Task analysis, cost/latency aware |
| **Preflight Checks** | `src/safety/pre-flight.ts` (482 lines) | HIGH | 9 pre-flight checks, 6 readiness gates |
| **Memory System** | `src/memory/unified-memory-manager.ts` | HIGH | 5 memory systems integrated |
| **Incident Recovery** | `src/execution/execution-recovery.ts` | HIGH | Git time-travel, explicit abort logging |
| **Telemetry** | `src/telemetry/telemetry-bus.ts` | MED-HIGH | Event bus, structured logging |
| **Evaluation** | `tests/unit/` (50+ files), `tests/chaos/` | MED-HIGH | ARES validation, chaos tests |
| **Skill Registry** | `src/skills/skill-loader.ts`, `skill-registry.ts` | HIGH | YAML frontmatter, token tracking |

### ✅ ALREADY EXISTS IN ROXY (REUSE, DON'T DUPLICATE)

| Category | Files | Maturity | Notes |
|----------|-------|----------|-------|
| **Secret Token** | `secret.token`, `rotate_token.sh` | HIGH | Auth token with rotation script |
| **Infisical Integration** | `scripts/004-deploy-infisical.sh` | HIGH | Secrets manager deployment ready |
| **Tool Retry** | `tool_retry.py` | HIGH | Root cause classifier, strategy rotation |
| **Circuit Breaker** | `circuit_breaker.py` | HIGH | ChromaDB circuit breaker |
| **ULTRAMAX Fallback** | `tools/streaming_tools.py` | HIGH | OpenCode fallback chain |
| **Eval Harness** | `tests/test_opencode_ultramax.py` | MED | 15+ tests, 100% pass |
| **Bootstrap Context** | `tools/streaming_tools.py:546` | HIGH | Luno/SKOREQ injection before spawn |
| **Secret Scanning** | `scripts/security_scan.sh` | MED | Pattern scanning for secrets |

---

## 🔴 GENUINELY NEW ITEMS (Priority Order)

### GAP 1: Secret Scanning Gate (P0 - Security Critical)
**Status:** EXISTS but NOT INTEGRATED into every run
- ROXY has `scripts/security_scan.sh` but it's not a pre-run gate
- Luno has `.luno/rulesets/forbidden-operations.json` but not blocking
- **Action:** Create `~/.roxy/secret_scanner.py` as pre-flight gate

### GAP 2: Cross-Model Verification (P0 - Quality)
**Status:** NOT EXISTS anywhere
- No dual-pass consensus for high-risk outputs
- **Action:** Add verification mode to OpenCode tool in ROXY

### GAP 3: Benchmark Leaderboard (P1 - Observability)
**Status:** NOT EXISTS anywhere
- No rolling history of model performance
- **Action:** Create `~/.roxy/benchmark_tracker.py`

### GAP 4: Incident Learning Loop (P1 - Reliability)
**Status:** PARTIALLY EXISTS
- Luno has `failure-taxonomy.ts`
- ROXY has `tool_retry.py` with fix recipes
- **Gap:** No automatic pattern→fix mapping and tracking
- **Action:** Extend `tool_retry.py` with learning registry

### GAP 5: Typed Mission Contract Enforcement (P1 - Governance)
**Status:** EXISTS IN LUNO, REUSE ONLY
- Luno `execution-spec.schema.ts` is complete
- **Action:** Bridge Luno mission contract into ROXY OpenCode spawns

### GAP 6: Release Qualification Pipeline (P1 - Process)
**Status:** NOT EXISTS as formal pipeline
- Individual components exist but not unified
- **Action:** Create `~/.roxy/qualification_pipeline.py`

### GAP 7: Distributed Tracing (P2 - Observability)
**Status:** PARTIAL in both
- Luno: uses `executionId`
- ROXY: has trace IDs in some places
- **Gap:** No unified trace spanning prompt→retrieval→tool→model→verifier
- **Action:** Create unified trace schema in `roxy_core.py`

### GAP 8: Memory Conflict Resolution (P2 - Memory)
**Status:** EXISTS in Luno but not ROXY
- **Action:** Bridge Luno conflict resolver into ROXY memory

---

## 🟡 ENHANCEMENT ITEMS (Extend Existing, Don't Create New)

| # | Enhancement | Extend | File | Priority |
|---|-------------|--------|------|----------|
| E1 | Add budget/latency to OpenCode fallback | ROXY `streaming_tools.py` | Add SLA constraints | P0 |
| E2 | Secret rotation automation | ROXY `rotate_token.sh` | Cron-based rotation | P1 |
| E3 | MCP auth diagnostics | Luno `provider-health.ts` | Per-server status | P1 |
| E4 | Preflight → ROXY bridge | Luno `pre-flight.ts` | Call pre-flight before OpenCode spawn | P1 |
| E5 | Eval harness → 40+ tests | ROXY `tests/test_opencode_ultramax.py` | Add adversarial, retrieval, continuity | P2 |
| E6 | Benchmark artifacts daily | Luno `reports/` | Daily diff report | P2 |

---

## ⏭️ DEFER (Already Covered)

| Proposed Item | Already Covered By |
|---------------|-------------------|
| Secret hygiene/rotation | Luno `key-registry.ts` + ROXY `Infisical` |
| MCP circuit breakers | Luno `circuit-breaker.ts` + ROXY `circuit_breaker.py` |
| Tool governance policy | Luno `bible-validator.ts`, `forbidden-operations.json` |
| Spawn briefing compiler | Luno `unified-prompt-builder.ts` + ROXY bootstrap context |
| Model routing engine | Luno `smart-router.ts` (1441 lines comprehensive) |
| Preflight gate | Luno `pre-flight.ts` (9 checks) |
| Skill loading | Luno `skill-loader.ts` |
| Telemetry/observability | Luno `telemetry-bus.ts` + ROXY structured logging |
| Memory freshness | Luno `unified-memory-manager.ts` |
| Incident recovery | Luno `execution-recovery.ts` + git time-travel |

---

## TOP 8 EXECUTION PRIORITIES (AAA QUALITY)

### 1. Secret Scanning Pre-Flight Gate
**File:** `~/.roxy/secret_scanner.py`  
**Reuses:** ROXY `scripts/security_scan.sh` patterns  
**Acceptance:** Every OpenCode spawn blocked if secrets detected  
**AAA Test:** `test_secret_scanner_blocks_leaked_key`

### 2. ULTRAMAX Fallback SLA Extension  
**File:** `~/.roxy/tools/streaming_tools.py`  
**Extends:** ROXY OpenCode tool  
**Acceptance:** Fallback respects budget + latency constraints  
**AAA Test:** `test_fallback_respects_sla_constraints`

### 3. Cross-Model Verification Layer
**File:** `~/.roxy/tools/streaming_tools.py`  
**New:** Verification pass for high-risk operations  
**Acceptance:** Dual-pass consensus required for infra changes  
**AAA Test:** `test_verification_blocks_unverified_infra`

### 4. Benchmark Tracker with Rolling History
**File:** `~/.roxy/benchmark_tracker.py`  
**New:** Daily model performance artifacts  
**Acceptance:** `benchmark-YYYY-MM-DD.json` produced daily  
**AAA Test:** `test_benchmark_artifact_generation`

### 5. Luno Preflight → ROXY Bridge
**File:** `~/.roxy/roxy_core.py`  
**Bridges:** Luno `src/safety/pre-flight.ts` → OpenCode spawns  
**Acceptance:** OpenCode denied if pre-flight fails  
**AAA Test:** `test_preflight_blocks_unready_spawn`

### 6. Learning Loop Registry Extension
**File:** `~/.roxy/tool_retry.py`  
**Extends:** ROXY retry with pattern→fix mapping  
**Acceptance:** Second encounter improves success rate  
**AAA Test:** `test_learning_loop_improves_retry`

### 7. Release Qualification Pipeline
**File:** `~/.roxy/qualification_pipeline.py`  
**Integrates:** Security scan + eval + preflight + MCP auth  
**Acceptance:** Single `QUALIFIED=YES/NO` artifact  
**AAA Test:** `test_pipeline_produces_qualified_artifact`

### 8. Mission Contract Bridge
**File:** `~/.roxy/streaming_tools.py`  
**Bridges:** Luno `execution-spec.schema.ts` → OpenCode context  
**Acceptance:** OpenCode spawns include typed mission contract  
**AAA Test:** `test_mission_contract_injected`

---

## AAA CODE QUALITY STANDARDS

All implementations will include:
- [ ] Type hints (Python `typing`, TypeScript `interfaces`)
- [ ] Comprehensive docstrings
- [ ] Unit tests with >85% coverage
- [ ] Integration tests in `tests/`
- [ ] Error handling with typed exceptions
- [ ] Logging with structured output
- [ ] Graceful degradation (never hard-fail mission)
- [ ] Audit trail entries for governance

---

## EXECUTION SEQUENCE

```
Week 1:
├── 1. Secret Scanner Pre-Flight Gate
└── 2. ULTRAMAX Fallback SLA Extension

Week 2:
├── 3. Cross-Model Verification Layer
└── 4. Benchmark Tracker

Week 3:
├── 5. Luno Preflight → ROXY Bridge
└── 6. Learning Loop Registry

Week 4:
├── 7. Release Qualification Pipeline
└── 8. Mission Contract Bridge

Final:
└── Full eval harness expansion to 40+ tests
```

---

**This ticket complies with Law 0: Zero duplication of existing Luno Orchestrator and ROXY infrastructure.**

