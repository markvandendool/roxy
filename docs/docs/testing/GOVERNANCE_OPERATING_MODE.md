# Governance Operating Mode

**Phase:** Data Collection & Listening  
**Duration:** 7-14 days  
**Goal:** Let the system speak before making policy changes

---

## Current Status: ✅ Governance Infrastructure Complete

**What's Built:**
- ✅ Cognitive Contract specification
- ✅ Test-time enforcement (forensic tests)
- ✅ Runtime soft-mode enforcement (observation only)
- ✅ Violation artifact schema
- ✅ Dashboard schema & service

**What's Active:**
- ✅ Test-time violations (CI/CD)
- ✅ Runtime violations (soft mode, logging only)
- ✅ Violation reporting (structured artifacts)

**What's Frozen:**
- 🔒 Cognitive Contract spec
- 🔒 Violation schema
- 🔒 Runtime enforcement logic
- 🔒 Dashboard aggregation logic

**Why Freeze:**
- Need stable baseline for trend analysis
- Churn invalidates trend data
- False movement looks like progress

---

## Daily Operating Mode (5-10 minutes)

### Morning Check (2 minutes)

**Command:**
```bash
# Check violation counts (if artifacts exist)
ls -lh tests/artifacts/cognitive-contract/*.json | tail -5

# View latest test report summary (if available)
cat tests/artifacts/cognitive-contract/cognitive-contract-report-*.txt | tail -20
```

**What to Look For:**
- ✅ Violations are being collected
- ✅ No errors in collection
- ⚠️ Sudden spikes (note but don't react yet)

**Do NOT:**
- ❌ Fix violations yet
- ❌ Change contract
- ❌ Tune thresholds
- ❌ Suppress noise

**Rationale:** We're in listening mode. Noise is signal.

---

### Weekly Snapshot (After 7 Days)

**Generate Dashboard Snapshot:**
```bash
# Run this after 7 days of data collection
pnpm test tests/forensic/rocky-cognitive-contract.spec.ts
# Then generate dashboard snapshot (see below)
```

**Focus Areas:**
1. **Top 3 Violation Types**
   - Which violations recur most?
   - Are they test-time or runtime?

2. **Top 3 Problematic Tools**
   - Which tools have highest violation rates?
   - Are violations consistent or sporadic?

3. **Test vs Runtime Consistency**
   - Consistency score (target: >80%)
   - Are test assumptions matching runtime reality?

**Questions to Answer:**
- Are violations stable, increasing, or decreasing?
- Are there patterns (time of day, specific tools, etc.)?
- Is the contract too strict or too loose?

---

## Data Collection Checklist

### Week 1 (Days 1-7)

- [ ] Day 1: Verify violations are being collected
- [ ] Day 2: Check for collection errors
- [ ] Day 3: Verify runtime enforcement is active
- [ ] Day 4: Check violation counts (no action)
- [ ] Day 5: Verify artifacts are being generated
- [ ] Day 6: Check for any system errors
- [ ] Day 7: Generate first dashboard snapshot

### Week 2 (Days 8-14)

- [ ] Day 8: Review first snapshot
- [ ] Day 9: Note patterns (don't fix yet)
- [ ] Day 10: Check trend direction
- [ ] Day 11: Verify consistency score
- [ ] Day 12: Identify top violations
- [ ] Day 13: Note quick wins (don't implement yet)
- [ ] Day 14: Generate second snapshot, compare with first

---

## What to Watch For

### ✅ Good Signs

- Violations are being collected consistently
- Test-time and runtime violations align (>80% consistency)
- Violation patterns are stable (not random spikes)
- Top violations are actionable (not noise)

### ⚠️ Warning Signs

- Violations spike suddenly (investigate cause)
- Test vs runtime consistency < 60% (contract may be wrong)
- Same violation repeats constantly (may indicate bug)
- No violations at all (may indicate broken detection)

### 🚨 Red Flags

- Runtime violations but no test violations (tests incomplete)
- Test violations but no runtime violations (enforcement broken)
- Violations increasing rapidly (system degrading)
- False positives > 5% (contract too strict)

---

## What NOT to Do Yet

### ❌ Do NOT Build

- Auto-ticketing
- Hard enforcement
- User-facing refusal UX
- Dashboard animations
- Real-time streaming

**Why:** All depend on trust in the signal. We're building that trust now.

### ❌ Do NOT Change

- Cognitive Contract spec
- Violation schema
- Enforcement logic
- Dashboard aggregation

**Why:** Need stable baseline for trend analysis.

### ❌ Do NOT Fix

- Violations (yet)
- Thresholds
- Severity levels
- Categories

**Why:** Need to understand patterns first. Fixes come after analysis.

---

## After 14 Days: Next Steps

### Review Session

1. **Generate Dashboard Snapshot**
   ```bash
   pnpm governance:dashboard --timeRange=14d
   ```

2. **Review Together**
   - Top violations
   - Trends (improving/degrading/stable)
   - Test vs runtime consistency
   - Tool health scores
   - Quick wins

3. **Decide Next Actions**
   - Fix top violations?
   - Adjust contract?
   - Enable selective hard mode?
   - Build dashboard UI?

---

## Commands Reference

### Generate Dashboard Snapshot

```bash
# After 7 days
pnpm governance:dashboard --timeRange=7d

# After 14 days
pnpm governance:dashboard --timeRange=14d

# Compare periods
pnpm governance:dashboard --timeRange=7d --compare=previous
```

### Check Violation Counts

```bash
# Count test violations
find tests/artifacts/cognitive-contract -name "*.json" -exec jq '.summary.totalViolations' {} \;

# Count runtime violations (if persisted)
# (Implementation depends on storage backend)
```

### View Latest Report

```bash
# Latest test report
cat tests/artifacts/cognitive-contract/cognitive-contract-report-*.txt | tail -50

# Latest JSON report
jq '.' tests/artifacts/cognitive-contract/cognitive-contract-report-*.json | tail -1
```

---

## Success Criteria

### After 7 Days

- ✅ Violations collected consistently
- ✅ No collection errors
- ✅ First snapshot generated
- ✅ Patterns identified

### After 14 Days

- ✅ Trend direction clear (improving/stable/degrading)
- ✅ Consistency score calculated (>80% target)
- ✅ Top violations identified
- ✅ Quick wins prioritized
- ✅ Ready for policy decisions

---

## Questions to Answer (After Data Collection)

1. **Are we improving or drifting?**
   - Trend analysis from dashboard

2. **Where do test assumptions diverge from runtime?**
   - Test vs runtime comparison

3. **Which tools are highest governance risk?**
   - Tool health metrics

4. **What can we fix this week that moves the needle?**
   - Quick wins analysis

5. **Are we ready for hard enforcement?**
   - Compliance metrics + trend

---

## Emergency Procedures

### If Violations Spike Suddenly

1. **Don't panic** - Check if it's real or collection error
2. **Investigate** - Review violation details
3. **Document** - Note cause and impact
4. **Don't suppress** - This is signal, not noise

### If Collection Stops

1. Check CI/CD status
2. Verify runtime enforcement is active
3. Check for errors in logs
4. Restart collection if needed

### If False Positives > 5%

1. Document false positives
2. Note which violations are false
3. Don't change contract yet
4. Wait for 14-day analysis

---

## Timeline Summary

**Week 1:** Collect data, verify collection  
**Week 2:** Analyze patterns, identify trends  
**After Week 2:** Review snapshot, decide next actions

---

**Remember:** We're in listening mode. Let the system speak.

---

**End of Operating Mode Guide**





