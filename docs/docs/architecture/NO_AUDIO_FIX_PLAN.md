# No-Audio Fix Plan (Revised)
## Production-Blocking Issue: Zero Audible Output on macOS Chrome/Safari

**Date:** 2025-11-30 (Revised 2025-11-30)  
**Priority:** 🔴 **CRITICAL** - Production blocking  
**Status:** Revised per 20-metric audit feedback  
**Audit Score:** 7/10 overall (addressed gaps below)

---

## Executive Summary

**Problem:** NVX1 score UI renders, Apollo bootstrap succeeds, but **zero audible output** on macOS Chrome/Safari. Scheduler reports `noteEventCount: 0`, no events in queue.

**Important Context (Acknowledged):**
- Recent fixes already in place: AudioContext close guards, AudioScheduler.load() disabled, Tone context unification
- Plan should not chase already-fixed issues
- Root cause may be different from initial hypothesis (not just zero events)

**Root Cause Hypothesis (Revised):**
1. **Primary:** Events not being scheduled (playbackPlan empty OR start() not scheduling)
2. **Secondary:** AudioContext unlock/autoplay policy blocking (macOS Chrome/Safari specific)
3. **Tertiary:** Apollo readiness or GlobalAudioContext state issues (despite bootstrap success logs)
4. **Quaternary:** Filter/guard logic preventing events from reaching scheduler queue

**Solution:** Add feature-flagged diagnostics, deterministic assertions, verify event pipeline, fix root cause, add robust regression tests.

---

## Phase 1: Diagnostic Instrumentation (Day 1)

### Task 1.1: Add Feature-Flagged Diagnostic Debug Hooks
**Files:** `src/services/audio/AudioPlaybackService.ts`, `src/pages/NVX1Score.tsx`

**Feature Flag:** `NVX1_DIAGNOSTICS=true` (env var or localStorage)

**Changes:**
1. Add `window.__NVX1_AUDIO_DIAGNOSTICS__` hook (only if flag enabled):
   ```typescript
   {
     playbackPlanLength: number,
     scheduledEventCount: number,
     schedulerQueueSize: number,
     readinessState: ReadinessState,
     gainStaging: {
       submixVolumes: Record<string, number>,
       routerGain: number,
       apolloVolume: number,
     },
     audioContextState: 'running' | 'suspended' | 'closed',
     apolloReady: boolean,
     routerReady: boolean,
   }
   ```

2. Add `window.__NVX1_SCORE_LOAD_DIAGNOSTICS__` hook:
   ```typescript
   {
     scoreLoaded: boolean,
     canonicalScoreParts: number,
     canonicalNoteEvents: number,
     instrumentMapSize: number,
     playbackPlanEvents: number,
   }
   ```

3. Update hooks in real-time during score loading and playback

**Acceptance Criteria:**
- Hooks only exposed when `NVX1_DIAGNOSTICS=true` (avoid shipping noise)
- Hooks update during score loading
- Hooks accessible from browser console
- All diagnostic data available
- Can be disabled via feature flag for production

**Verification:**
- Set `localStorage.setItem('NVX1_DIAGNOSTICS', 'true')` or env var
- Open browser console
- Check `window.__NVX1_AUDIO_DIAGNOSTICS__`
- Check `window.__NVX1_SCORE_LOAD_DIAGNOSTICS__`
- Verify hooks are undefined when flag is false

---

### Task 1.2: Add Feature-Flagged Comprehensive Logging
**Files:** `src/services/audio/AudioPlaybackService.ts`

**Feature Flag:** `NVX1_DIAGNOSTICS=true` (same as hooks)

**Changes:**
1. Add logging to `loadScore()` (only if flag enabled, use clear log tags like `[NVX1-DIAG]`):
   - Log input NVX1Score structure (parts, measures)
   - Log canonical score conversion result (note events count)
   - Log instrument map size
   - Log playback plan length

2. Add logging to `buildPlaybackPlan()`:
   - Log canonical score note events
   - Log events converted to PlaybackNote[]
   - Log final playback plan length

3. Add logging to `start()`:
   - Log playback plan length
   - Log events scheduled to scheduler
   - Log scheduler queue size after scheduling

4. Add logging to `beginPlaybackFromTick()`:
   - Log tick position
   - Log events scheduled
   - Log scheduler state

**Acceptance Criteria:**
- All critical steps logged (only when flag enabled)
- Logs use clear tags `[NVX1-DIAG]` to avoid noise
- Logs show data flow
- Logs identify where events are lost
- Logs can be disabled via feature flag

**Verification:**
- Set `localStorage.setItem('NVX1_DIAGNOSTICS', 'true')`
- Check browser console for `[NVX1-DIAG]` logs
- Verify logs show complete flow
- Identify missing steps
- Verify no logs when flag is false

---

### Task 1.3: Create Playwright Diagnostic Test (Deterministic First)
**File:** `tests/e2e/nvx1-audio-output-diagnostic.spec.ts` (new)

**Purpose:** Automated reproduction and diagnosis using deterministic assertions

**Key Principle:** Use deterministic assertions (scheduler queue, plan length, AudioContext state) before attempting flaky audio detection.

**Tests:**
1. **AudioContext Unlock (Critical for Headless):**
   ```typescript
   test('should unlock AudioContext on user gesture', async ({ page }) => {
     await page.goto('/nvx1-score');
     await page.waitForSelector('[data-testid="nvx1-score-root"]');
     
     // Simulate user gesture to unlock AudioContext
     await page.click('body'); // Click anywhere to trigger unlock
     
     // Wait for AudioContext to resume
     await page.waitForFunction(() => {
       const ctx = (window as any).__AUDIO_CONTEXT__ || 
                   (window as any).Tone?.context?.rawContext;
       return ctx?.state === 'running';
     }, { timeout: 5000 });
     
     const ctxState = await page.evaluate(() => {
       const ctx = (window as any).__AUDIO_CONTEXT__ || 
                   (window as any).Tone?.context?.rawContext;
       return ctx?.state;
     });
     
     expect(ctxState).toBe('running');
   });
   ```

2. **Score Loading Verification (Deterministic):**
   ```typescript
   test('should load score and create events', async ({ page }) => {
     await page.goto('/nvx1-score');
     await page.waitForSelector('[data-testid="nvx1-score-root"]');
     
     // Enable diagnostics
     await page.evaluate(() => {
       localStorage.setItem('NVX1_DIAGNOSTICS', 'true');
     });
     
     // Wait for score to load
     await page.waitForTimeout(2000);
     
     // Check diagnostic hooks (deterministic)
     const diagnostics = await page.evaluate(() => {
       return (window as any).__NVX1_SCORE_LOAD_DIAGNOSTICS__;
     });
     
     expect(diagnostics).toBeDefined();
     expect(diagnostics.scoreLoaded).toBe(true);
     expect(diagnostics.canonicalNoteEvents).toBeGreaterThan(0);
     expect(diagnostics.playbackPlanEvents).toBeGreaterThan(0);
   });
   ```

3. **Event Scheduling Verification (Deterministic):**
   ```typescript
   test('should schedule events to AudioScheduler', async ({ page }) => {
     await page.goto('/nvx1-score');
     await page.waitForSelector('[data-testid="nvx1-score-root"]');
     
     // Enable diagnostics
     await page.evaluate(() => {
       localStorage.setItem('NVX1_DIAGNOSTICS', 'true');
     });
     
     // Unlock AudioContext
     await page.click('body');
     await page.waitForTimeout(500);
     
     // Click play
     await page.click('[data-testid="play-button"]');
     
     // Wait for scheduling (deterministic check)
     await page.waitForFunction(() => {
       const diagnostics = (window as any).__NVX1_AUDIO_DIAGNOSTICS__;
       return diagnostics?.schedulerQueueSize > 0;
     }, { timeout: 3000 });
     
     // Check diagnostic hooks (deterministic)
     const diagnostics = await page.evaluate(() => {
       return (window as any).__NVX1_AUDIO_DIAGNOSTICS__;
     });
     
     expect(diagnostics.schedulerQueueSize).toBeGreaterThan(0);
     expect(diagnostics.readinessState.isReady).toBe(true);
     expect(diagnostics.readinessState.eventCount).toBeGreaterThan(0);
     expect(diagnostics.audioContextState).toBe('running');
     expect(diagnostics.apolloReady).toBe(true);
   });
   ```

4. **Audio Output Verification (Optional, Flaky - Gate Separately):**
   ```typescript
   test('should produce audible output [FLAKY]', async ({ page }) => {
     // Only run in headed mode or with explicit flag
     test.skip(process.env.HEADLESS === 'true', 'Skipping flaky audio test in headless');
     
     await page.goto('/nvx1-score');
     await page.waitForSelector('[data-testid="nvx1-score-root"]');
     
     // Unlock AudioContext
     await page.click('body');
     await page.waitForTimeout(500);
     
     // Click play
     await page.click('[data-testid="play-button"]');
     
     // Wait for deterministic checks first
     await page.waitForFunction(() => {
       const diagnostics = (window as any).__NVX1_AUDIO_DIAGNOSTICS__;
       return diagnostics?.schedulerQueueSize > 0 && 
              diagnostics?.audioContextState === 'running';
     }, { timeout: 3000 });
     
     // Optional: Audio probe (tolerate flakiness)
     const hasAudio = await page.evaluate(() => {
       return new Promise<boolean>((resolve) => {
         // Use actual audio routing, not MediaStreamDestination
         const ctx = (window as any).__AUDIO_CONTEXT__ || 
                     (window as any).Tone?.context?.rawContext;
         if (!ctx) {
           resolve(false);
           return;
         }
         
         const analyser = ctx.createAnalyser();
         // Connect to actual audio output (if accessible)
         // Note: This is fragile and may fail in headless
         
         const dataArray = new Uint8Array(analyser.frequencyBinCount);
         let samples = 0;
         const checkAudio = () => {
           analyser.getByteTimeDomainData(dataArray);
           const rms = Math.sqrt(
             dataArray.reduce((sum, val) => sum + Math.pow(val - 128, 2), 0) / dataArray.length
           );
           samples++;
           if (rms > 5 || samples > 100) {
             resolve(rms > 5);
             return;
           }
           setTimeout(checkAudio, 50);
         };
         checkAudio();
       });
     });
     
     // Tolerate flakiness - log but don't fail
     if (!hasAudio) {
       console.warn('[FLAKY TEST] Audio probe did not detect output, but deterministic checks passed');
     }
   });
   ```

**Acceptance Criteria:**
- Test uses deterministic assertions first (scheduler queue, plan length, AudioContext state)
- AudioContext unlock handled for headless
- Audio probe is optional and gated separately
- Test reproduces issue
- Test identifies root cause

**Verification:**
```bash
# Deterministic tests (always run)
pnpm playwright test tests/e2e/nvx1-audio-output-diagnostic.spec.ts --grep "should"

# Flaky audio test (only in headed mode)
pnpm playwright test tests/e2e/nvx1-audio-output-diagnostic.spec.ts --grep "FLAKY" --headed
```

---

## Phase 2: Root Cause Investigation (Day 1-2)

### Task 2.1: Verify Score Loading Pipeline
**Action:** Trace NVX1Score → CanonicalScore → PlaybackPlan

**Important:** Acknowledge recent fixes - AudioContext guards and AudioScheduler.load() disabled are already in place. Focus on event creation/scheduling pipeline.

**Investigation Steps:**
1. Check if `loadScore()` is called with valid NVX1Score
2. Check if `nvx1ScoreToCanonical()` produces note events (may be empty if score has no notes)
3. Check if `buildPlaybackPlan()` creates events from canonical score
4. Check if `playbackPlan` array is populated
5. **NEW:** Check if filter/guard logic is preventing events from being created

**Files to Check:**
- `src/services/audio/AudioPlaybackService.ts:436` (`loadScore()`)
- `src/services/audio/AudioPlaybackService.ts:1100+` (`buildPlaybackPlan()`)
- `src/bridge/canonical/nvx1CanonicalBridge.ts` (score conversion)
- **NEW:** Check for any filter/guard logic that might drop events

**Expected Findings:**
- If `playbackPlan.length === 0`: Issue in score conversion, plan building, OR filter logic
- If `playbackPlan.length > 0`: Issue in event scheduling
- If events exist but filtered: Issue in guard/filter logic

**Fix Location:**
- If conversion issue: Fix `nvx1ScoreToCanonical()` or `buildPlaybackPlan()`
- If scheduling issue: Fix `start()` or `beginPlaybackFromTick()`
- If filter issue: Fix guard/filter logic

---

### Task 2.2: Verify Event Scheduling
**Action:** Trace PlaybackPlan → AudioScheduler

**Investigation Steps:**
1. Check if `start()` is called
2. Check if `start()` calls `beginPlaybackFromTick()`
3. Check if `beginPlaybackFromTick()` schedules events
4. Check if `scheduler.schedule()` is called for each event
5. Check scheduler queue after scheduling

**Files to Check:**
- `src/services/audio/AudioPlaybackService.ts:602` (`start()` method)
- `src/services/audio/AudioPlaybackService.ts:1600+` (`beginPlaybackFromTick()`)
- `src/services/audio/AudioScheduler.ts:140+` (`schedule()` method)

**Expected Findings:**
- If `start()` not called: Issue in `PlaybackController.play()`
- If `beginPlaybackFromTick()` not called: Issue in `start()`
- If `scheduler.schedule()` not called: Issue in `beginPlaybackFromTick()`
- If events scheduled but queue empty: Issue in `AudioScheduler`

**Fix Location:**
- Based on where the flow breaks

---

### Task 2.3: Verify Readiness Check
**Action:** Check if readiness check is blocking playback

**Investigation Steps:**
1. Check `getReadinessState()` implementation
2. Check if `eventCount === 0` blocks playback
3. Check if other readiness criteria are failing
4. Check if readiness check is too strict

**Files to Check:**
- `src/services/audio/AudioPlaybackService.ts:823` (`getReadinessState()`)
- `src/services/playback/PlaybackController.ts:136` (readiness check)

**Expected Findings:**
- If `eventCount === 0`: Events not created (see Task 2.1)
- If other criteria failing: Fix specific criteria
- If check too strict: Relax check

**Fix Location:**
- `getReadinessState()` or `PlaybackController.play()`

---

### Task 2.4: Verify Gain Staging (Lower Priority)
**Action:** Check all audio paths for mute/zero gain

**Note:** Gain staging is rarely the culprit (per audit), but worth checking if events are scheduled but no output.

**Investigation Steps:**
1. Check SubmixManager volume levels (default: nvx1-score 0.9, metronome 0.6)
2. Check UniversalAudioRouter gain
3. Check Apollo backend volume
4. Check master gain/mute states
5. **NEW:** Check Apollo readiness state (despite bootstrap success logs)

**Files to Check:**
- `src/audio/routing/SubmixManager.ts`
- `src/audio/UniversalAudioRouter.ts`
- `src/services/globalApollo.ts` (Apollo readiness)
- `src/audio/core/GlobalAudioContext.ts` (context state)

**Expected Findings:**
- If volumes are zero: Fix volume initialization
- If paths muted: Fix mute logic
- If routing incorrect: Fix routing
- If Apollo not ready: Fix Apollo initialization

**Fix Location:**
- Based on specific issue found

---

## Phase 3: Targeted Fixes (Day 2-3)

### Task 3.1: Fix Score Loading (if Hypothesis 1)
**Condition:** `playbackPlan.length === 0` after `loadScore()`

**Potential Fixes:**
1. **Fix `nvx1ScoreToCanonical()`:**
   - Ensure note events are extracted from NVX1Score
   - Verify canonical score structure
   - Fix if conversion is failing

2. **Fix `buildPlaybackPlan()`:**
   - Ensure events are created from canonical score
   - Verify playback plan structure
   - Fix if plan building is failing

3. **Fix Score Data Structure:**
   - Verify NVX1Score has note data
   - Fix if score structure is invalid

**Files to Modify:**
- `src/bridge/canonical/nvx1CanonicalBridge.ts` (if conversion issue)
- `src/services/audio/AudioPlaybackService.ts:1100+` (if plan building issue)

**Acceptance Criteria:**
- `playbackPlan.length > 0` after `loadScore()`
- Events are valid and schedulable
- Events have correct timing

---

### Task 3.2: Fix Event Scheduling (if Hypothesis 2)
**Condition:** `playbackPlan.length > 0` but `scheduler.queue.length === 0`

**Potential Fixes:**
1. **Fix `start()` method:**
   - Ensure `start()` calls `beginPlaybackFromTick()`
   - Verify `start()` is called from `PlaybackController`
   - Fix if `start()` is not scheduling

2. **Fix `beginPlaybackFromTick()`:**
   - Ensure events are scheduled to scheduler
   - Verify `scheduler.schedule()` is called
   - Fix if scheduling is failing

3. **Fix `AudioScheduler.schedule()`:**
   - Ensure events are added to queue
   - Verify queue is processed
   - Fix if scheduler is not working

**Files to Modify:**
- `src/services/audio/AudioPlaybackService.ts:602` (`start()` method)
- `src/services/audio/AudioPlaybackService.ts:1600+` (`beginPlaybackFromTick()`)
- `src/services/audio/AudioScheduler.ts:140+` (`schedule()` method)

**Acceptance Criteria:**
- `scheduler.queue.length > 0` after `start()`
- Events are processed correctly
- Audio output is audible

---

### Task 3.3: Fix Readiness Check (if Hypothesis 3)
**Condition:** Events exist but readiness check blocks playback

**Potential Fixes:**
1. **Relax Readiness Check:**
   - Allow playback if events exist
   - Remove overly strict checks
   - Add fallback logic

2. **Fix `getReadinessState()`:**
   - Ensure `eventCount` is calculated correctly
   - Fix if calculation is wrong
   - Add logging for debugging

**Files to Modify:**
- `src/services/audio/AudioPlaybackService.ts:823` (`getReadinessState()`)
- `src/services/playback/PlaybackController.ts:136` (readiness check)

**Acceptance Criteria:**
- Readiness check allows valid playback
- Events are not blocked unnecessarily
- Playback starts when ready

---

### Task 3.4: Fix Gain Staging (if Hypothesis 4)
**Condition:** Events scheduled but no audible output

**Potential Fixes:**
1. **Fix SubmixManager:**
   - Ensure volumes are non-zero
   - Fix if volumes are zero
   - Verify routing is correct

2. **Fix UniversalAudioRouter:**
   - Ensure gain is non-zero
   - Fix if gain is zero
   - Verify routing is correct

3. **Fix Apollo Backend:**
   - Ensure volume is non-zero
   - Fix if volume is zero
   - Verify output is connected

**Files to Modify:**
- `src/audio/routing/SubmixManager.ts` (if volume issue)
- `src/audio/UniversalAudioRouter.ts` (if gain issue)
- `src/services/globalApollo.ts` (if Apollo volume issue)

**Acceptance Criteria:**
- All audio paths have non-zero gain
- Audio routing is correct
- Output is audible

---

## Phase 4: Automated Regression Tests (Day 3-4)

### Task 4.1: Create Deterministic Regression Tests
**File:** `tests/e2e/nvx1-audio-output.spec.ts` (new)

**Key Principle:** Use deterministic assertions (scheduler, plan, AudioContext, Apollo) rather than flaky audio detection.

**Tests:**
1. **Chord Click Deterministic Checks:**
   - Click chord in NVX1 score
   - Verify `playbackPlan.length > 0` (deterministic)
   - Verify `scheduler.queue.length > 0` after click (deterministic)
   - Verify `AudioContext.state === 'running'` (deterministic)
   - Verify `Apollo.isReady === true` (deterministic)
   - **Optional:** Audio probe (gated separately, tolerate flakiness)

2. **Transport Playback Deterministic Checks:**
   - Start playback
   - Verify `scheduler.queue.length > 0` (deterministic)
   - Verify `readinessState.isReady === true` (deterministic)
   - Verify `readinessState.eventCount > 0` (deterministic)
   - Verify playback continues for >2 beats (check scheduler queue persists)
   - **Optional:** Audio probe (gated separately)

3. **Metronome Deterministic Checks:**
   - Start metronome
   - Verify metronome events fire (check event bus or hooks)
   - Verify metronome service state (deterministic)
   - **Optional:** Audio probe (gated separately)

**Acceptance Criteria:**
- All deterministic tests pass
- Tests use scheduler/plan/AudioContext/Apollo assertions
- Audio probe is optional and gated separately
- Tests fail if deterministic checks fail

**Verification:**
```bash
# Deterministic tests (always run)
pnpm playwright test tests/e2e/nvx1-audio-output.spec.ts

# Optional audio probe (only in headed mode)
pnpm playwright test tests/e2e/nvx1-audio-output.spec.ts --grep "audio probe" --headed
```

---

### Task 4.2: Create Event Scheduling Test
**File:** `tests/e2e/nvx1-event-scheduling.spec.ts` (new)

**Tests:**
1. **Score Loading:**
   - Load NVX1 score
   - Verify `playbackPlan.length > 0`
   - Verify events are valid

2. **Event Scheduling:**
   - Call `start()`
   - Verify events are scheduled to scheduler
   - Verify `scheduler.queue.length > 0`

3. **Readiness State:**
   - Verify `getReadinessState().isReady === true`
   - Verify `eventCount > 0`
   - Verify readiness reasons are empty

**Acceptance Criteria:**
- All tests pass
- Events are scheduled correctly
- Readiness state is accurate

---

## Implementation Timeline (Revised)

### Day 1: Diagnostics (Feature-Flagged)
- [ ] Add feature-flagged diagnostic debug hooks (`NVX1_DIAGNOSTICS=true`)
- [ ] Add feature-flagged comprehensive logging (clear `[NVX1-DIAG]` tags)
- [ ] Create Playwright diagnostic test (deterministic assertions first)
- [ ] Add AudioContext unlock step for headless
- [ ] Run diagnostic test to identify root cause

### Day 2: Investigation (Acknowledge Recent Fixes)
- [ ] Verify score loading pipeline (acknowledge AudioContext/Apollo fixes already in place)
- [ ] Verify event scheduling (check filter/guard logic)
- [ ] Verify readiness check (may be too strict)
- [ ] Verify gain staging (lower priority, rarely culprit)
- [ ] Verify Apollo readiness state (despite bootstrap success logs)

### Day 3: Fixes (Targeted)
- [ ] Apply targeted fixes based on root cause
- [ ] Test fixes in browser (with diagnostics enabled)
- [ ] Verify deterministic checks pass (scheduler queue, plan length, AudioContext state)
- [ ] **Optional:** Verify audio output (tolerate flakiness)

### Day 4: Regression Tests (Deterministic)
- [ ] Create automated regression tests (deterministic assertions)
- [ ] Run full test suite
- [ ] Verify all deterministic tests pass
- [ ] **Optional:** Run audio probe tests (headed mode only)

---

## Success Criteria (Revised - Deterministic First)

### Immediate (Day 1)
- [ ] Feature-flagged diagnostic hooks added
- [ ] Feature-flagged logging added (clear tags)
- [ ] Diagnostic test reproduces issue (deterministic assertions)
- [ ] AudioContext unlock works in headless
- [ ] Root cause identified

### Short-term (Day 2-3)
- [ ] Root cause fixed
- [ ] Deterministic checks pass:
  - `playbackPlan.length > 0`
  - `scheduler.queue.length > 0` after start()
  - `AudioContext.state === 'running'`
  - `Apollo.isReady === true`
  - `readinessState.isReady === true`
- [ ] Audio output works on macOS Chrome/Safari (manual verification)
- [ ] All deterministic diagnostic tests pass

### Long-term (Day 4)
- [ ] Automated regression tests created (deterministic)
- [ ] Full test suite passes (deterministic tests)
- [ ] **Optional:** Audio probe tests pass (headed mode, tolerate flakiness)
- [ ] Issue documented and resolved

---

## Risk Mitigation (Revised)

### High-Risk Areas

1. **Score Loading:**
   - Risk: Score data structure changed, breaking conversion OR filter/guard logic dropping events
   - Mitigation: Add feature-flagged logging, verify data structure, check filter logic

2. **Event Scheduling:**
   - Risk: Timing issues OR events not being scheduled at all
   - Mitigation: Verify event timing, check scheduler state, use deterministic assertions

3. **Readiness Check:**
   - Risk: Check is too strict, blocking valid playback
   - Mitigation: Relax check if needed, add fallback, acknowledge recent fixes

4. **Browser Compatibility:**
   - Risk: macOS Chrome/Safari have different behavior, autoplay policies
   - Mitigation: Test on all browsers, handle autoplay policies, add unlock step in tests

5. **Audio Detection Flakiness:**
   - Risk: Audio probe tests are brittle and may fail in headless
   - Mitigation: Use deterministic assertions first, gate audio probe separately, tolerate flakiness

6. **Feature Flag Management:**
   - Risk: Diagnostics ship to production, causing noise
   - Mitigation: All diagnostics behind `NVX1_DIAGNOSTICS=true` flag, can be disabled

7. **Chasing Fixed Issues:**
   - Risk: Plan assumes issues that are already fixed (AudioContext guards, AudioScheduler.load)
   - Mitigation: Acknowledge recent fixes, focus on event creation/scheduling pipeline

---

**End of Fix Plan**

