# Governance Listening Phase Guide

**Duration:** 7-14 days  
**Purpose:** Collect data before making policy changes  
**Status:** Active

---

## Phase Overview

We're entering the **listening phase** - collecting violation data to understand Rocky's actual behavior before making governance decisions.

**Key Principle:** Let the system speak. Don't react yet.

---

## What's Happening

### Active Systems

1. **Test-Time Enforcement**
   - Runs on every commit/PR
   - Generates violation reports
   - Fails CI on violations (strict mode)

2. **Runtime Soft Enforcement**
   - Observes tool invocations
   - Logs violations (doesn't block)
   - Emits violation events

3. **Violation Collection**
   - Test reports: `tests/artifacts/cognitive-contract/`
   - Runtime events: Logged to console (will persist later)

### What We're Measuring

- **Violation frequency** - How often do violations occur?
- **Violation patterns** - Which violations recur?
- **Test vs runtime consistency** - Do tests match reality?
- **Tool health** - Which tools are problematic?
- **Trend direction** - Are we improving or degrading?

---

## Daily Routine

### Morning Check (2 minutes)

```bash
# Check if violations are being collected
ls -lh tests/artifacts/cognitive-contract/*.json 2>/dev/null | tail -5

# View latest summary (if available)
cat tests/artifacts/cognitive-contract/cognitive-contract-report-*.txt 2>/dev/null | tail -20
```

**What to Look For:**
- ✅ Artifacts are being generated
- ✅ No collection errors
- ⚠️ Sudden spikes (note but don't react)

**What NOT to Do:**
- ❌ Fix violations
- ❌ Change thresholds
- ❌ Suppress noise

---

## Weekly Checkpoints

### After 7 Days

**Generate First Snapshot:**
```bash
pnpm governance:dashboard:7d
```

**Review:**
- Top 3 violation types
- Top 3 problematic tools
- Test vs runtime consistency score

**Questions:**
- Are violations stable or spiking?
- Are there clear patterns?
- Is consistency score > 80%?

### After 14 Days

**Generate Second Snapshot:**
```bash
pnpm governance:dashboard:14d
```

**Compare:**
- Trend direction (improving/stable/degrading)
- Consistency score trend
- Top violations (same or different?)

**Decide:**
- Ready for policy changes?
- Ready for selective hard mode?
- Need more data?

---

## What Success Looks Like

### Good Signals

- ✅ Violations collected consistently
- ✅ Test vs runtime consistency > 80%
- ✅ Violation patterns are stable
- ✅ Top violations are actionable

### Warning Signals

- ⚠️ Consistency score < 60% (contract may be wrong)
- ⚠️ Same violation repeats constantly (may be bug)
- ⚠️ Violations spiking suddenly (investigate)

### Red Flags

- 🚨 No violations at all (detection broken)
- 🚨 False positives > 5% (contract too strict)
- 🚨 Violations increasing rapidly (system degrading)

---

## Frozen Components

**Do NOT modify:**
- Cognitive Contract spec
- Violation schema
- Enforcement logic
- Dashboard aggregation

**Why:** Need stable baseline for trend analysis.

---

## After Listening Phase

**Review Session:**
1. Generate dashboard snapshot
2. Review together (top violations, trends, consistency)
3. Decide next actions:
   - Fix top violations?
   - Adjust contract?
   - Enable selective hard mode?
   - Build dashboard UI?

**Then:**
- Implement fixes based on data
- Adjust contract if needed
- Enable hard mode gradually (if ready)

---

## Commands Reference

```bash
# Generate 7-day snapshot
pnpm governance:dashboard:7d

# Generate 14-day snapshot
pnpm governance:dashboard:14d

# Custom time range
pnpm governance:dashboard -- --timeRange=30d

# Save to specific file
pnpm governance:dashboard -- --timeRange=7d --output=snapshot.json
```

---

**Remember:** We're listening. Let the system speak.

---

**End of Guide**





