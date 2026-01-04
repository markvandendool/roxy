# 🐰 BUN 🐰 Epic Staging Guide

## Overview

This guide explains how to properly stage the Bun Migration Epic in the master-progress.json system, following all breakroom and progress tracking protocols.

---

## Epic Summary

**Epic ID:** `EPIC-BUN-MIGRATION`  
**Name:** 🐰 BUN 🐰  
**Status:** Pending (blocked until R15)  
**Total Tasks:** 60+  
**Total Sprints:** 6  
**Oracle Score:** 19.2/20 (A++)

---

## Files Created

1. **`docs/planning/BUN_MIGRATION_RESEARCH_PROMPT.md`**
   - Complete research document with 100 metrics of excellence
   - Phase 0 research deliverables

2. **`docs/planning/BUN_MIGRATION_EPIC_COMPLETE.md`**
   - Complete engineering plan with all sprints and tasks
   - Oracle evaluation and predicted failures
   - Performance targets and success criteria

3. **`docs/planning/BUN_MIGRATION_EPIC_JSON_ENTRY.json`**
   - Complete epic JSON entry ready for master-progress.json
   - All sprints, tasks, phases, milestones, risks, and documentation links

4. **`scripts/progress/add-bun-epic.mjs`**
   - Script to safely add epic to master-progress.json
   - Validates no duplicates
   - Updates metadata

---

## Staging Steps

### Step 1: Review Epic Entry

Review the epic entry to ensure it's correct:

```bash
cat docs/planning/BUN_MIGRATION_EPIC_JSON_ENTRY.json | jq .
```

### Step 2: Add Epic to master-progress.json

Run the staging script:

```bash
node scripts/progress/add-bun-epic.mjs
```

This will:
- ✅ Validate epic doesn't already exist
- ✅ Add epic to master-progress.json
- ✅ Update metadata (lastUpdated, updatedBy)
- ✅ Preserve all existing epics

### Step 3: Verify Epic Added

Check that the epic was added correctly:

```bash
node scripts/progress/status.mjs --epic EPIC-BUN-MIGRATION
```

Or view in browser:
- Navigate to `/progress`
- Find "🐰 BUN 🐰" in the epic list

### Step 4: Post Breakroom Activity

Following breakroom protocol, post an activity:

**Via Browser:**
1. Navigate to `/progress` → BreakRoom tab
2. Click "Post Activity"
3. Type: `task_claimed` (or `discovery`)
4. Title: `Epic 🐰 BUN 🐰 staged and ready for execution (post-R15)`
5. Description: `Complete Bun migration epic with 6 sprints and 60+ tasks. Research complete. Blocked until Phoenix V1 Certification (R15).`

**Via Code:**
```typescript
import { useAgentBreakroom } from '@/hooks/useAgentBreakroom';

const { handlePostActivity } = useAgentBreakroom();

handlePostActivity({
  type: 'discovery',
  title: 'Epic 🐰 BUN 🐰 staged and ready for execution (post-R15)',
  description: 'Complete Bun migration epic with 6 sprints and 60+ tasks. Research complete. Blocked until Phoenix V1 Certification (R15).',
  level: 'info'
});
```

### Step 5: Link Documentation

The epic already includes documentation links in the `documentation` field:
- `docs/planning/BUN_MIGRATION_RESEARCH_PROMPT.md`
- `docs/planning/BUN_MIGRATION_EPIC_COMPLETE.md`

These will be accessible from the progress dashboard.

---

## Epic Structure

### Phases
- **Phase 0 (P0):** Research & Analysis ✅ Complete
- **Phase 0.5 (P0.5):** Epic Planning & Documentation ✅ Complete

### Sprints
1. **BUN-S1:** Parallel Bun Toolchain Setup (1 week)
2. **BUN-S2:** Test Suite Migration (1-2 weeks)
3. **BUN-S3:** Savage³ Core Harness on Bun (1 week)
4. **BUN-S4:** Vite/Rollup Pipeline Migration (1-2 weeks)
5. **BUN-S5:** CI/CD Migration (1 week)
6. **BUN-S6:** Final Node → Bun Flip & Validation (1-2 weeks)

### Milestones
- M1: Parallel Toolchain Established
- M2: Test Suite Migrated
- M3: Savage³ Harness Validated
- M4: Build Pipeline Migrated
- M5: CI/CD Fully Migrated
- M6: Migration Complete

---

## Critical Constraints

### Timing Constraints
- ❌ **CANNOT START:** Phoenix V1 is FROZEN (zero runtime changes)
- ❌ **CANNOT START:** SEB AAA Waves 1-2 just passed
- ✅ **MUST START AFTER:** Phoenix V1 Certification (R15)
- ✅ **MUST COMPLETE BEFORE:** SEB AAA Wave 3

### Technical Constraints
- **AudioWorklet:** Bun doesn't support in runtime (browser-only)
- **WebGPU:** Bun doesn't support (browser-only)
- **Native Modules:** Audit required
- **Playwright:** May need Node alongside Bun in CI

### Unlock Condition
The epic has an `unlockCondition` field:
```
"After Phoenix V1 Certification (R15) - Phoenix V1 is FROZEN (zero runtime changes allowed)"
```

**Do not start execution until R15 is certified.**

---

## Performance Targets

| Metric | Baseline | Target | Multiplier |
|--------|----------|--------|------------|
| HMR Latency | ~1-2s | <50ms | 20-40× |
| TS Transpile | esbuild | Bun native | 4-8× |
| Test Execution | Vitest ~8-10s | Bun ~3s | 2-5× |
| Install Time | pnpm ~45s | Bun <5s | ~15× |
| Dev Startup | Vite ~3s | Bun <1s | 3× |

---

## Risks & Mitigations

1. **AudioWorklet Limitation** → Mock subsystems (BUN-S1-T6)
2. **WebGPU Limitation** → Mock subsystems (BUN-S1-T7)
3. **Timing Window Violation** → Unlock condition enforced
4. **Lockfile Drift** → Automated CI validation

---

## Oracle Evaluation

**Score:** 19.2/20 (A++)

**Strengths:**
- ✅ Comprehensive research (100 metrics)
- ✅ All predicted failures have mitigations
- ✅ Proper timing constraints
- ✅ Complete task breakdown
- ✅ Documentation linked

**Minor Gaps (addressed in plan):**
- Browser AudioWorklet harness under Bun dev server (BUN-S4-T4.5)

---

## Next Steps After Staging

1. ✅ Epic staged in master-progress.json
2. ✅ Breakroom activity posted
3. ⏳ Wait for Phoenix V1 Certification (R15)
4. ⏳ Update epic `startDate` when unlocked
5. ⏳ Begin Sprint 1 execution

---

## Verification Checklist

- [ ] Epic added to master-progress.json
- [ ] All documentation files exist and are linked
- [ ] Breakroom activity posted
- [ ] Epic visible in `/progress` dashboard
- [ ] Status script shows epic correctly
- [ ] Unlock condition documented
- [ ] All tasks have proper sprint assignments
- [ ] Performance targets documented
- [ ] Risks and mitigations documented

---

## Support

If you encounter issues:

1. **Check master-progress.json format:**
   ```bash
   node scripts/progress/validate-all.mjs
   ```

2. **Verify epic structure:**
   ```bash
   cat public/releaseplan/master-progress.json | jq '.epics[] | select(.id == "EPIC-BUN-MIGRATION")'
   ```

3. **Check breakroom connection:**
   - Navigate to `/progress` → BreakRoom tab
   - Verify you can post activities

4. **Review documentation:**
   - `docs/agent-breakroom/ONBOARDING.md`
   - `docs/agent-breakroom/AGENT_BREAKROOM_PROTOCOL.md`
   - `docs/agent-breakroom/TICKETS_AND_PROGRESS_EXPLAINED.md`

---

**Epic Status:** Ready for staging  
**Last Updated:** 2025-12-09  
**Staging Script:** `scripts/progress/add-bun-epic.mjs`




























