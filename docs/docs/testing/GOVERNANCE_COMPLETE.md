# Rocky Governance System - Complete

**Tags:** `rocky-governance`, `cognitive-contract`, `tool-authority`, `knowledge-graph`

**Status:** ✅ Infrastructure Complete, Entering Listening Phase  
**Date:** 2025-12-12  
**Lock-In:** ✅ Constitutional layer active - See [GOVERNANCE_LOCK_IN_MOMENT.md](GOVERNANCE_LOCK_IN_MOMENT.md)

---

## Executive Summary

Rocky now has a **complete governance pipeline** spanning four connected layers:

1. **Law** - Cognitive Contract specification
2. **Proof** - Forensic + contract tests
3. **Observation** - Runtime soft enforcement
4. **Insight** - Governance dashboard schema

This is a **governed AI system**, not just a tested one.

---

## What Was Built

### Layer 1: Law (Cognitive Contract)

**Files:**
- `docs/testing/ROCKY_COGNITIVE_CONTRACT_SPEC.md` - Complete specification
- `src/types/rocky/CognitiveContract.ts` - Violation schema

**Principles:**
- Authority Before Execution
- Tool-Skill Grounding
- Knowledge Base Authority
- Refusal Contract
- Gap-Driven Tests

---

### Layer 2: Proof (Test-Time Enforcement)

**Files:**
- `tests/forensic/rocky-cognitive-contract.spec.ts` - Core contract tests
- `tests/forensic/rocky-tool-authority.spec.ts` - Tool authority tests
- `tests/forensic/rocky-refusal.spec.ts` - Refusal contract tests
- `src/services/rocky/CognitiveContractReporter.ts` - Violation reporter

**Coverage:**
- Skill authority (planned/missing not claimable)
- Tool authority (must connect to active skills)
- Knowledge legitimacy (canonical only)
- Graph integrity (valid edges, unique IDs)
- Gap analysis (disconnected tools, orphaned knowledge)
- Metadata completeness

**CI Integration:**
- `.github/workflows/cognitive-contract.yml` - Runs on every commit/PR
- Strict mode: Fails build on violations
- Artifacts: JSON + human-readable reports

---

### Layer 3: Observation (Runtime Soft Enforcement)

**Files:**
- `src/services/rocky/RuntimeEnforcementService.ts` - Runtime enforcement
- `src/types/rocky/RuntimeViolation.ts` - Runtime violation schema
- `src/utils/rockyTools.ts` - Integration point

**Features:**
- Pre-execution authority checks
- Soft mode (observes, doesn't block)
- Violation event emission
- Unified reporting with test-time

**Status:** Active, collecting data

---

### Layer 4: Insight (Governance Dashboard)

**Files:**
- `src/types/rocky/GovernanceDashboard.ts` - Dashboard schema
- `src/services/rocky/GovernanceDashboardService.ts` - Dashboard service
- `scripts/governance/generate-dashboard-snapshot.mjs` - Snapshot generator

**Capabilities:**
- Compliance metrics
- Violation aggregations
- Trend analysis
- Test vs runtime comparison
- Tool health monitoring
- Quick wins identification

**Status:** Schema complete, UI pending

---

## Current Operating Mode

### Phase: Listening (7-14 days)

**Active:**
- ✅ Test-time violations (CI/CD)
- ✅ Runtime violations (soft mode)
- ✅ Violation reporting

**Frozen:**
- 🔒 Cognitive Contract spec
- 🔒 Violation schema
- 🔒 Enforcement logic
- 🔒 Dashboard aggregation

**Daily Routine:**
- Morning check (2 min): Verify collection
- Weekly snapshot (after 7 days): Generate dashboard
- Review (after 14 days): Analyze trends

**Commands:**
```bash
# Generate 7-day snapshot
pnpm governance:dashboard:7d

# Generate 14-day snapshot
pnpm governance:dashboard:14d
```

---

## What This Enables

### Data-Driven Decisions

**Before:**
- "Rocky seems weird"
- "Maybe we should fix X"
- "I think Y is broken"

**After:**
- "Violation rate: 0.5 per 1000 invocations"
- "Top violation: DISCONNECTED_TOOL (15 occurrences)"
- "Consistency score: 85% (test vs runtime)"
- "Tool health: analyzeImage (warning, 3 violations/1000)"

### Measurable Progress

- Compliance percentage (0-100%)
- Trend direction (improving/stable/degrading)
- Consistency score (test vs runtime)
- Tool health scores

### Actionable Insights

- Quick wins (high impact, low effort)
- Top violations (fix these first)
- Problematic tools (focus here)
- Contract gaps (test-only or runtime-only violations)

---

## Success Metrics

### Infrastructure Complete ✅

- [x] Cognitive Contract spec
- [x] Test-time enforcement
- [x] Runtime soft enforcement
- [x] Violation artifacts
- [x] Dashboard schema
- [x] CI integration
- [x] Snapshot generator

### Listening Phase (Next 7-14 Days)

- [ ] Violations collected consistently
- [ ] First snapshot generated (day 7)
- [ ] Trends identified (day 14)
- [ ] Consistency score calculated
- [ ] Ready for policy decisions

### Future Phases

- [ ] Dashboard UI built
- [ ] Selective hard mode enabled
- [ ] Auto-ticketing from violations
- [ ] Refusal UX integrated

---

## Key Files Reference

### Specifications
- `docs/testing/ROCKY_COGNITIVE_CONTRACT_SPEC.md` - Contract spec
- `docs/testing/GOVERNANCE_DASHBOARD_SPEC.md` - Dashboard spec
- `docs/testing/SOFT_TO_HARD_ENFORCEMENT_CRITERIA.md` - Transition criteria

### Implementation
- `src/types/rocky/CognitiveContract.ts` - Violation types
- `src/types/rocky/RuntimeViolation.ts` - Runtime violation types
- `src/types/rocky/GovernanceDashboard.ts` - Dashboard types
- `src/services/rocky/CognitiveContractReporter.ts` - Reporter service
- `src/services/rocky/RuntimeEnforcementService.ts` - Runtime enforcement
- `src/services/rocky/GovernanceDashboardService.ts` - Dashboard service

### Tests
- `tests/forensic/rocky-cognitive-contract.spec.ts` - Core tests
- `tests/forensic/rocky-tool-authority.spec.ts` - Tool tests
- `tests/forensic/rocky-refusal.spec.ts` - Refusal tests

### CI/CD
- `.github/workflows/cognitive-contract.yml` - CI workflow
- `tests/forensic/.ci-config.ts` - CI configuration

### Scripts
- `scripts/governance/generate-dashboard-snapshot.mjs` - Snapshot generator

### Guides
- `docs/testing/GOVERNANCE_OPERATING_MODE.md` - Operating mode
- `docs/testing/GOVERNANCE_LISTENING_PHASE.md` - Listening phase guide
- `docs/testing/RUNTIME_ENFORCEMENT_GUIDE.md` - Runtime enforcement guide

---

## What NOT to Do Yet

### ❌ Do NOT Build

- Auto-ticketing
- Hard enforcement
- User-facing refusal UX
- Dashboard animations
- Real-time streaming

**Why:** Need trust in signal first.

### ❌ Do NOT Change

- Cognitive Contract spec
- Violation schema
- Enforcement logic
- Dashboard aggregation

**Why:** Need stable baseline for trends.

### ❌ Do NOT Fix

- Violations (yet)
- Thresholds
- Severity levels

**Why:** Need to understand patterns first.

---

## Next Steps (In Order)

1. **✅ Infrastructure Complete** - Done
2. **⏳ Data Collection (7-14 days)** - Active
3. **⏳ First Snapshot Review** - After 7 days
4. **⏳ Trend Analysis** - After 14 days
5. **⏳ Policy Decisions** - After analysis
6. **⏳ Dashboard UI** - After data collection
7. **⏳ Selective Hard Mode** - After confidence built

---

## Impact Statement

**Rocky is now a governed AI system.**

From this point forward:
- Violations are **measurable signals**, not mysteries
- Compliance is **quantifiable**, not subjective
- Progress is **trackable**, not assumed
- Decisions are **data-driven**, not guesswork

**Rocky is no longer something you hope behaves.**
**He is something you observe, measure, and control.**

---

**End of Summary**

