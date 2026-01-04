# Soft → Hard Enforcement Transition Criteria

**Purpose:** Define when and how to transition from soft-mode (observation) to hard-mode (blocking) enforcement.

---

## Prerequisites Checklist

Before enabling hard mode, **all** of these must be true:

### ✅ 1. Runtime Violations Collected (7+ Days)

**Requirement:** At least 7 days of runtime violation data collected.

**Verification:**
```bash
# Check violation collection period
grep -r "source.*runtime" tests/artifacts/cognitive-contract/ | wc -l
```

**Rationale:** Need sufficient data to understand violation patterns.

---

### ✅ 2. Test-Time vs Runtime Consistency (< 5% Variance)

**Requirement:** Test-time violations should be < 5% of runtime violations.

**Calculation:**
```
variance = |testViolations - runtimeViolations| / runtimeViolations
```

**Verification:**
- Compare test-time violation counts with runtime violation counts
- If test-time violations are significantly higher, contract may be too strict
- If runtime violations are significantly higher, contract may be incomplete

**Rationale:** Ensures contract is accurate and complete.

---

### ✅ 3. False Positive Rate (< 1%)

**Requirement:** False positive rate < 1% of all violations.

**Definition:** False positive = violation detected but tool/skill was actually authorized.

**Verification:**
- Review violation logs
- Manually verify a sample of violations
- Track false positive reports

**Rationale:** High false positive rate erodes trust and causes user frustration.

---

### ✅ 4. Dashboard/Alerting in Place

**Requirement:** 
- Violation dashboard operational
- Alerting configured for critical violations
- Trend tracking enabled

**Verification:**
- Dashboard accessible and showing data
- Alerts tested and working
- Trend charts displaying correctly

**Rationale:** Need visibility to monitor impact of hard mode.

---

### ✅ 5. Rollback Plan Defined

**Requirement:** 
- Can disable enforcement within 5 minutes
- Rollback procedure documented
- Team trained on rollback

**Verification:**
- Test rollback procedure
- Document in runbook
- Team knows how to disable

**Rationale:** Need safety net if hard mode causes issues.

---

## Gradual Rollout Plan

### Phase 1: Critical Only (Week 1)

**Configuration:**
```ts
{
  mode: 'hard',
  blockThresholds: {
    critical: true,  // ✅ Block critical
    high: false,     // ❌ Allow high
    medium: false,   // ❌ Allow medium
    low: false,      // ❌ Allow low
  },
  alwaysBlockCategories: [],
}
```

**Success Criteria:**
- ✅ No user-facing errors
- ✅ Violation rate stable
- ✅ No false positives reported
- ✅ Performance impact < 10ms per check

**Duration:** 3 days minimum

**Rollback Trigger:**
- User-facing errors
- False positive rate > 1%
- Performance degradation > 50ms

---

### Phase 2: High Severity (Week 2)

**Configuration:**
```ts
{
  mode: 'hard',
  blockThresholds: {
    critical: true,  // ✅ Block critical
    high: true,      // ✅ Block high (NEW)
    medium: false,   // ❌ Allow medium
    low: false,      // ❌ Allow low
  },
  alwaysBlockCategories: [],
}
```

**Success Criteria:**
- ✅ No user-facing errors
- ✅ Violation rate stable
- ✅ No false positives reported
- ✅ Block rate < 0.1% of invocations

**Duration:** 3 days minimum

**Rollback Trigger:**
- User-facing errors
- False positive rate > 1%
- Block rate > 0.5%

---

### Phase 3: Full Enforcement (Week 3+)

**Configuration:**
```ts
{
  mode: 'hard',
  blockThresholds: {
    critical: true,  // ✅ Block critical
    high: true,       // ✅ Block high
    medium: true,     // ✅ Block medium (NEW)
    low: false,       // ❌ Allow low (or true if desired)
  },
  alwaysBlockCategories: ['GRAPH_INTEGRITY'], // Always block these
}
```

**Success Criteria:**
- ✅ No user-facing errors
- ✅ Violation rate stable
- ✅ No false positives reported
- ✅ Block rate < 0.1% of invocations
- ✅ User satisfaction maintained

**Duration:** Ongoing

**Rollback Trigger:**
- User-facing errors
- False positive rate > 1%
- Block rate > 0.5%
- User complaints increase

---

## Monitoring During Transition

### Key Metrics to Track

1. **Violation Rate**
   - Target: < 1% of tool invocations
   - Alert if: > 5%

2. **Block Rate** (hard mode)
   - Target: < 0.1% of tool invocations
   - Alert if: > 0.5%

3. **False Positive Rate**
   - Target: < 1% of violations
   - Alert if: > 2%

4. **Performance Impact**
   - Target: < 10ms per check
   - Alert if: > 50ms

5. **User Impact**
   - Target: Zero user-facing errors
   - Alert if: Any user reports issues

### Dashboard Queries

```ts
// Violation rate (last 24h)
const violationRate = await getViolationRate({ timeRange: '24h' });

// Block rate (last 24h) - hard mode only
const blockRate = await getBlockRate({ timeRange: '24h' });

// False positive rate (last 7 days)
const falsePositiveRate = await getFalsePositiveRate({ timeRange: '7d' });

// Performance impact (p50, p95, p99)
const performance = await getPerformanceMetrics({ timeRange: '24h' });
```

---

## Rollback Procedure

### Immediate Rollback (< 5 minutes)

1. **Disable Enforcement**
   ```ts
   runtimeEnforcementService.updateConfig({ mode: 'disabled' });
   ```

2. **Verify Disabled**
   - Check logs for "enforcement disabled" message
   - Verify tool invocations succeed

3. **Notify Team**
   - Post in team channel
   - Update status page if public

### Investigation Rollback (< 1 hour)

1. **Collect Data**
   - Export violation logs
   - Capture user reports
   - Gather performance metrics

2. **Analyze Root Cause**
   - Review violation patterns
   - Check for false positives
   - Verify graph accuracy

3. **Fix Issues**
   - Update graph if needed
   - Adjust severity thresholds
   - Fix false positive detection

4. **Re-enable Gradually**
   - Start with soft mode
   - Monitor for 24h
   - Re-attempt hard mode if stable

---

## Success Indicators

### Ready for Hard Mode

- ✅ All prerequisites met
- ✅ Violation patterns understood
- ✅ False positive rate low
- ✅ Team confident in rollback

### Hard Mode Successful

- ✅ Block rate < 0.1%
- ✅ Zero user-facing errors
- ✅ False positive rate < 1%
- ✅ Performance impact acceptable
- ✅ User satisfaction maintained

---

## Risk Mitigation

### Risk: Too Aggressive Blocking

**Mitigation:**
- Start with critical only
- Gradual rollout
- Monitor block rate closely
- Quick rollback procedure

### Risk: False Positives

**Mitigation:**
- Track false positive rate
- Review violations manually
- Adjust detection logic
- User feedback loop

### Risk: Performance Impact

**Mitigation:**
- Cache graph (singleton)
- Async violation checks
- Profile enforcement overhead
- Optimize graph queries

---

## Timeline Estimate

- **Week 1:** Collect runtime violations (soft mode)
- **Week 2:** Analyze data, build dashboard
- **Week 3:** Phase 1 rollout (critical only)
- **Week 4:** Phase 2 rollout (high severity)
- **Week 5+:** Phase 3 rollout (full enforcement)

**Total:** ~5 weeks from soft mode to full enforcement

---

**End of Criteria**





