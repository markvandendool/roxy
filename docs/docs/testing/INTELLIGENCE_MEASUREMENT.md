# Rocky Intelligence Measurement System

**Tags:** `rocky-governance`, `intelligence`, `diagnostic`, `trend-analysis`

**Purpose:** Track Rocky's intelligence profile over time using the Magnificent Diagnostic and governance integration.

---

## Executive Summary

Rocky's intelligence is now **scientifically measurable, trackable, and governed**.

**Three-Way Triangulation:**
1. **Cognitive Contract** → What Rocky is *allowed* to do
2. **Runtime Enforcement** → What Rocky *tries* to do
3. **Magnificent Diagnostic** → What Rocky *can actually* do under pressure

---

## Intelligence Score

**Formula:** Weighted average of 7 capability dimensions (0-100 scale)

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| Basic Q&A | 20% | Foundation model grounding |
| Complex Reasoning | 15% | Planning + multi-step coherence |
| Tool Usage | 25% | Agency correctness (choosing *how*, not just *what*) |
| Memory & Context | 15% | Working memory integrity |
| Widget Control | 10% | Embodied cognition (thought → action) |
| Error Handling | 10% | Boundary awareness + refusal quality |
| Performance | 5% | Stability under human concurrency |

**Interpretation:**
- 90-100: Excellent - All capabilities performing optimally
- 80-89: Good - Minor issues in some categories
- 70-79: Fair - Notable gaps, review recommended
- <70: Poor - Significant capability regression

---

## Diagnostic → Governance Bridge

When the Magnificent Diagnostic fails, failures are automatically classified:

| Diagnostic Category | Contract Category | Violation Type |
|---------------------|-------------------|----------------|
| BasicQA | knowledge_base | KNOWLEDGE_GAP |
| ComplexReasoning | skill_authority | REASONING_FAILURE |
| ToolUsage | tool_authority | TOOL_MISUSE |
| MemoryContext | skill_authority | CONTEXT_LOSS |
| WidgetControl | tool_authority | WIDGET_CONTROL_FAILURE |
| ErrorHandling | refusal_contract | ERROR_HANDLING_FAILURE |
| Performance | graph_integrity | PERFORMANCE_DEGRADATION |

**Service:** `src/services/rocky/DiagnosticGovernanceBridge.ts`

---

## Intelligence Snapshots

Snapshots track Rocky's intelligence over time:

```typescript
interface IntelligenceSnapshot {
  timestamp: number;
  runId: string;
  passRate: number;          // 0-100%
  avgLatency: number;        // ms
  categoryScores: Record<Category, number>;
  intelligenceScore: number; // 0-100
  comparisonToPrevious?: {
    passRateDelta: number;
    latencyDelta: number;
    scoreDelta: number;
    trend: 'improving' | 'stable' | 'degrading';
  };
}
```

**Storage:** `tests/artifacts/rocky-intelligence-snapshots/`

---

## Commands

### Run Diagnostic
```bash
pnpm rocky:diagnostic
```

### Persist Snapshot
```bash
pnpm intelligence:snapshot --input=tests/artifacts/rocky-magnificent/report.json
```

### View Trend Analysis
```bash
pnpm intelligence:trend
```

### List All Snapshots
```bash
pnpm intelligence:list
```

---

## Trend Analysis

After 3+ diagnostic runs, trend analysis becomes available:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║   ROCKY INTELLIGENCE TREND REPORT                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

Total Diagnostic Runs: 5
First Score: 72.3/100
Latest Score: 85.1/100
Total Improvement: +12.8 points

TREND ANALYSIS
═══════════════════════════════════════════════════════════════════════════════

Overall Trend: IMPROVING 📈
Avg Score Change: +3.2 per run
Slope: +2.56 (linear regression)

SCORE HISTORY
═══════════════════════════════════════════════════════════════════════════════

Run 1: 72.3/100 (baseline)
Run 2: 75.1/100 (+2.8 ↑)
Run 3: 78.9/100 (+3.8 ↑)
Run 4: 82.4/100 (+3.5 ↑)
Run 5: 85.1/100 (+2.7 ↑)

INTERPRETATION
═══════════════════════════════════════════════════════════════════════════════

✅ Rocky is getting SMARTER over time. Continue current development approach.
🎉 Significant improvement detected! Rocky has gained 12.8 intelligence points.
```

---

## Constitutional Requirement

From `docs/DOCTRINE.md`:

> **Rule 2:** Any claim of Rocky capability must be demonstrated by:
> - The Magnificent Diagnostic (`pnpm rocky:diagnostic`)
> - Or an equivalent governed test
> - This is constitutional law, not optional.

---

## Operating Schedule

**Recommended Usage:**
- **Pre-release:** Run before major releases
- **Post-major-change:** Run after significant capability changes
- **Monthly:** Run as periodic health check
- **Quarterly:** Full intelligence audit with trend analysis

**NOT Recommended:**
- Running on every commit (too expensive)
- Chasing 100% pass rate blindly
- Weakening expectations to "greenwash" results

---

## Integration Points

### Governance Dashboard
Diagnostic results feed into the Governance Dashboard:
- Failed tests → Contract violations
- Intelligence score → Compliance metrics
- Trend analysis → Dashboard trends

### CI/CD
Can be integrated as a release gate:
```yaml
- name: Run Intelligence Diagnostic
  run: pnpm rocky:diagnostic
  
- name: Persist Snapshot
  run: pnpm intelligence:snapshot --input=latest-report.json
  
- name: Check Intelligence Score
  run: |
    SCORE=$(jq '.intelligenceScore' latest-report.json)
    if [ "$SCORE" -lt "80" ]; then
      echo "Intelligence score below threshold: $SCORE"
      exit 1
    fi
```

---

## Files Reference

**Test:** `tests/e2e/rocky-magnificent-diagnostic.spec.ts`
**Bridge:** `src/services/rocky/DiagnosticGovernanceBridge.ts`
**Snapshot Script:** `scripts/governance/persist-intelligence-snapshot.mjs`
**Artifacts:** `tests/artifacts/rocky-magnificent/`
**Snapshots:** `tests/artifacts/rocky-intelligence-snapshots/`
**Spec:** `docs/testing/ROCKY_MAGNIFICENT_DIAGNOSTIC_SPEC.md`

---

## What This Enables

1. **Evidence-Based Claims** - Capability claims backed by data
2. **Regression Detection** - Catch intelligence degradation early
3. **Trend Tracking** - See Rocky getting smarter/dumber over time
4. **Failure Classification** - Map failures to contract categories
5. **Strategic Insight** - Data-driven development priorities

---

## Three-Way Triangulation Report

The ultimate governance view combines all three layers:

```bash
pnpm governance:triangulation
```

**Sample Output:**

```
╔══════════════════════════════════════════════════════════════════════════════╗
║   GOVERNANCE TRIANGULATION REPORT                                             ║
║   Strategy meets Data meets Policy                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

THREE-WAY TRIANGULATION

                                 ┌──────────────────┐
                                 │ CONTRACT (Law)   │
                                 │   2 violations   │
                                 └────────┬─────────┘
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              │                           │                           │
              ▼                           ▼                           ▼
┌─────────────────────┐      ┌──────────────────────┐     ┌─────────────────────┐
│ RUNTIME (Behavior)  │◄────►│ GOVERNANCE HEALTH    │◄───►│ DIAGNOSTIC (Proof)  │
│   1 violations      │      │                      │     │   3 failures       │
└─────────────────────┘      │  SCORE: 82/100       │     └─────────────────────┘
                             └──────────────────────┘

GOVERNANCE HEALTH: 82/100
👍 GOOD: Rocky is well-governed with minor issues to address.

Formula: 40% Compliance + 35% Intelligence + 25% Consistency = 82/100
```

**What Triangulation Enables:**

When something fails, you can immediately classify it as:
- ❌ Contract violation (wrong behavior)
- ❌ Capability gap (can't do it)
- ❌ Reasoning degradation (could do it before)
- ❌ Tool misuse (wrong approach)
- ❌ Performance regression (too slow)

**No guessing. No debates. Just evidence.**

---

## Artifacts Location

| Artifact Type | Directory |
|---------------|-----------|
| Diagnostic Reports | `tests/artifacts/rocky-magnificent/` |
| Intelligence Snapshots | `tests/artifacts/rocky-intelligence-snapshots/` |
| Triangulation Reports | `tests/artifacts/governance-triangulation/` |
| Governance Snapshots | `tests/artifacts/governance-snapshots/` |

---

**Rocky is no longer a black box.**  
**He is a measurable, inspectable, evolving intelligence system with institutional memory.**

---

**End of Document**

