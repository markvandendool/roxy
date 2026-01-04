# Runtime Enforcement Guide

**Purpose:** Guide for runtime enforcement of cognitive contract (soft mode → hard mode transition).

---

## Overview

Runtime enforcement observes tool invocations and skill claims **in production** to validate the cognitive contract holds true at runtime, not just test-time.

**Current Status:** Soft mode (observation only, no blocking)

---

## Architecture

### Service: `RuntimeEnforcementService`

**Location:** `src/services/rocky/RuntimeEnforcementService.ts`

**Responsibilities:**
- Check tool authority before invocation
- Check skill claim authority
- Emit violation events
- Log violations (soft mode) or block execution (hard mode)

### Integration Points

#### 1. Tool Invocation (`src/utils/rockyTools.ts`)

**Hook:** Before `callRockyTool` executes

```ts
const checkResult = await runtimeEnforcementService.checkToolAuthority(
  toolName,
  args,
  context
);

if (checkResult.shouldBlock) {
  return { ok: false, error: checkResult.blockReason };
}
```

#### 2. Skill Claims (Future)

**Hook:** Before Rocky claims a skill in chat response

```ts
const checkResult = await runtimeEnforcementService.checkSkillClaim(
  skillId,
  context
);

if (checkResult.shouldBlock) {
  // Refuse skill claim
}
```

#### 3. Edge Function (Future)

**Hook:** In `supabase/functions/rocky-chat/index.ts` before tool execution

---

## Enforcement Modes

### Soft Mode (Current)

**Behavior:**
- ✅ Detects violations
- ✅ Logs violations
- ✅ Emits violation events
- ❌ Does NOT block execution

**Use Case:** Observation phase, building confidence

**Configuration:**
```ts
{
  mode: 'soft',
  blockThresholds: {
    critical: false,
    high: false,
    medium: false,
    low: false,
  },
  alwaysBlockCategories: [],
}
```

### Hard Mode (Future)

**Behavior:**
- ✅ Detects violations
- ✅ Logs violations
- ✅ Emits violation events
- ✅ **BLOCKS execution** based on severity thresholds

**Use Case:** Production enforcement after confidence built

**Configuration:**
```ts
{
  mode: 'hard',
  blockThresholds: {
    critical: true,  // Block critical violations
    high: true,      // Block high violations
    medium: false,   // Allow medium violations
    low: false,      // Allow low violations
  },
  alwaysBlockCategories: ['GRAPH_INTEGRITY'], // Always block these
}
```

### Disabled Mode

**Behavior:**
- ❌ No enforcement checks
- ❌ No violation detection

**Use Case:** Emergency bypass, debugging

---

## Violation Event Schema

```ts
interface RuntimeViolationEvent {
  violationId: string;
  type: ViolationType;
  category: ViolationCategory;
  severity: ViolationSeverity;
  source: 'runtime';
  context: {
    toolName: string;
    toolArgs: Record<string, any>;
    requestId: string;
    sessionId?: string;
    timestamp: string;
    userRequest?: string;
  };
  blocked: boolean;
  loggedOnly: boolean;
}
```

---

## Transition Criteria: Soft → Hard

### Prerequisites

1. ✅ **Runtime violations collected for 7+ days**
2. ✅ **Test-time violations < 5% of runtime violations** (contract is accurate)
3. ✅ **No false positives** (violations are real, not noise)
4. ✅ **Dashboard/alerting in place** (can monitor violations)
5. ✅ **Rollback plan defined** (can disable quickly if needed)

### Gradual Rollout

**Phase 1: Critical Only**
- Block only critical violations
- Monitor for 3 days
- Verify no user impact

**Phase 2: High Severity**
- Block critical + high violations
- Monitor for 3 days
- Verify no user impact

**Phase 3: Full Enforcement**
- Block based on configured thresholds
- Monitor continuously

---

## Monitoring

### Key Metrics

1. **Violation Rate**
   - Violations per 1000 tool invocations
   - Trend over time

2. **False Positive Rate**
   - Violations that were incorrectly flagged
   - Should be < 1%

3. **Block Rate** (hard mode)
   - Percentage of invocations blocked
   - Should be < 0.1% after stabilization

4. **Violation Categories**
   - Distribution by category
   - Identifies systemic issues

### Dashboard Queries

```ts
// Violations by category (last 24h)
const violations = await getRuntimeViolations({
  timeRange: '24h',
  groupBy: 'category',
});

// Violation rate trend (last 7 days)
const trend = await getViolationTrend({
  timeRange: '7d',
  metric: 'violationRate',
});
```

---

## Troubleshooting

### Too Many Violations

**Symptoms:**
- High violation rate (> 5%)
- Many false positives

**Actions:**
1. Review violation types
2. Check if graph is out of sync
3. Verify test-time vs runtime consistency
4. Consider adjusting severity thresholds

### Violations Not Detected

**Symptoms:**
- Expected violations not appearing
- Contract seems violated but no events

**Actions:**
1. Verify enforcement service initialized
2. Check integration points are hooked
3. Verify graph is loaded
4. Check console logs for errors

### Performance Impact

**Symptoms:**
- Tool invocations slower
- High latency

**Actions:**
1. Ensure graph is cached (singleton)
2. Consider async violation checks
3. Profile enforcement overhead
4. Optimize graph queries

---

## Best Practices

### 1. Start Soft, Stay Soft Until Confident

Don't enable hard mode until:
- Violations are predictable
- False positive rate is low
- Monitoring is in place

### 2. Monitor Violation Trends

Track violations over time:
- Sudden spikes indicate issues
- Gradual increases indicate drift
- Zero violations might indicate broken detection

### 3. Correlate with User Reports

If users report "Rocky acting weird":
- Check violation logs for that time period
- Look for patterns
- Use violations to diagnose issues

### 4. Keep Test-Time and Runtime in Sync

Ensure:
- Same graph used in tests and runtime
- Same authority logic
- Same violation detection

---

## Next Steps

1. ✅ Runtime enforcement service created
2. ✅ Soft mode integration complete
3. ⏳ Collect runtime violations (7+ days)
4. ⏳ Build violation dashboard
5. ⏳ Define hard mode criteria
6. ⏳ Enable hard mode (gradual rollout)

---

**End of Guide**





