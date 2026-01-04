# No-Audio Diagnostic & Fix Plan
## Production-Blocking Issue: Zero Audible Output on macOS Chrome/Safari

**Date:** 2025-11-30  
**Priority:** 🔴 **CRITICAL** - Production blocking  
**Environment:** macOS Chrome/Safari, `http://localhost:9135/nvx1-score`  
**Status:** Apollo bootstrap succeeds, but no audible output

---

## Problem Statement

**Symptoms:**
- ✅ UI renders correctly
- ✅ Apollo bootstrap succeeds (Tone.js context running)
- ✅ `playChord` is called with mapped instruments (guitar-acoustic, piano)
- ❌ Scheduler reports **zero note events** (`noteEventCount: 0`)
- ❌ No audible output (chords, metronome, click)
- ⚠️ Transport reportedly worked earlier in Edge

**Console Evidence:**
- `[DEV] ⚠️ NVX1 not fully ready - initialization may still be in progress`
- `⚠️ No events in scheduler queue`
- `noteEventCount: 0`
- Metronome widget registered but no ticks
- Cutoff logic preserving notes (but no notes exist)

---

## Root Cause Hypotheses

### Hypothesis 1: Score Not Loading Events (HIGH PROBABILITY)
**Theory:** NVX1 score data exists but `buildPlaybackPlan()` returns empty array

**Evidence:**
- `noteEventCount: 0` in scheduler
- `⚠️ No events in scheduler queue`
- Playback blocked by readiness check (`eventCount === 0`)

**Investigation:**
1. Check if `loadScore()` is called with valid NVX1Score
2. Check if `nvx1ScoreToCanonical()` produces note events
3. Check if `buildPlaybackPlan()` creates events from canonical score
4. Check if `playbackPlan` array is populated

**Files to Check:**
- `src/services/audio/AudioPlaybackService.ts:436` (`loadScore()`)
- `src/services/audio/AudioPlaybackService.ts:1100+` (`buildPlaybackPlan()`)
- `src/bridge/canonical/nvx1CanonicalBridge.ts` (score conversion)

---

### Hypothesis 2: Events Not Scheduled (HIGH PROBABILITY)
**Theory:** `playbackPlan` has events but `start()` doesn't schedule them

**Evidence:**
- `playbackPlan` may contain events
- But scheduler queue is empty
- `start()` may not be called or may fail silently

**Investigation:**
1. Check if `AudioPlaybackService.start()` is called
2. Check if `start()` schedules events to `AudioScheduler`
3. Check if `scheduler.schedule()` is called for each event
4. Check for errors in scheduling path

**Files to Check:**
- `src/services/audio/AudioPlaybackService.ts:700+` (`start()` method)
- `src/services/audio/AudioScheduler.ts:140+` (`schedule()` method)

---

### Hypothesis 3: Readiness Check Blocking (MEDIUM PROBABILITY)
**Theory:** Playback blocked because `eventCount: 0` fails readiness check

**Evidence:**
- `PlaybackController.play()` checks `readiness.isReady`
- If `eventCount === 0`, playback is blocked
- This prevents `start()` from being called

**Investigation:**
1. Check `getReadinessState()` implementation
2. Check if readiness check is too strict
3. Check if events exist but readiness check fails for other reasons

**Files to Check:**
- `src/services/audio/AudioPlaybackService.ts:880+` (`getReadinessState()`)
- `src/services/playback/PlaybackController.ts:136` (readiness check)

---

### Hypothesis 4: Gain Staging Issue (MEDIUM PROBABILITY)
**Theory:** Events scheduled but all audio paths muted or at zero gain

**Evidence:**
- Events may exist in scheduler
- But no audible output
- SubmixManager or router volume may be at zero

**Investigation:**
1. Check SubmixManager volume levels
2. Check UniversalAudioRouter gain staging
3. Check Apollo backend volume
4. Check master gain/mute states

**Files to Check:**
- `src/audio/routing/SubmixManager.ts`
- `src/audio/UniversalAudioRouter.ts`
- `src/services/globalApollo.ts` (Apollo volume)

---

### Hypothesis 5: Browser Autoplay Restrictions (LOW PROBABILITY)
**Theory:** macOS Chrome/Safari autoplay policies blocking audio

**Evidence:**
- Worked in Edge (different autoplay policy)
- Fails in Chrome/Safari
- AudioContext may be suspended

**Investigation:**
1. Check AudioContext state (`running` vs `suspended`)
2. Check if user interaction required
3. Check autoplay policy handling

**Files to Check:**
- `src/services/audio/bootstrapAudio.ts`
- `src/utils/toneUnlock.ts`
- `src/audio/core/GlobalAudioContext.ts`

---

## Diagnostic Plan

### Phase 1: Automated Browser Diagnostics (Day 1)

#### Task 1.1: Create Playwright Diagnostic Test
**File:** `tests/e2e/nvx1-audio-output-diagnostic.spec.ts` (new)

**Purpose:** Automated reproduction and diagnosis of no-audio issue

**Tests:**
1. **Audio Output Verification:**
   - Load NVX1 score
   - Click play button
   - Use AnalyserNode to detect audio output
   - Assert RMS > 0 within 500ms of chord click
   - Fail if silence persists

2. **Event Scheduling Verification:**
   - Check `window.__audioPlaybackService.playbackPlan.length`
   - Check `window.__audioScheduler.queue.length`
   - Verify events are scheduled after `start()`

3. **Readiness State Verification:**
   - Check `getReadinessState()` values
   - Verify `eventCount`, `instrumentCount`, `schedulerQueueSize`
   - Check readiness reasons if not ready

4. **Gain Staging Verification:**
   - Check SubmixManager volume levels
   - Check UniversalAudioRouter gain
   - Check Apollo backend volume
   - Verify no paths are muted

5. **Metronome Verification:**
   - Check if metronome events fire
   - Verify metronome produces audible buffer
   - Check AnalyserNode for metronome output

**Acceptance Criteria:**
- Test reproduces no-audio issue
- Test identifies root cause
- Test provides actionable diagnostics

**Verification:**
```bash
pnpm playwright test tests/e2e/nvx1-audio-output-diagnostic.spec.ts --headed
```

---

#### Task 1.2: Add Diagnostic Debug Hooks
**Files:** `src/services/audio/AudioPlaybackService.ts`, `src/pages/NVX1Score.tsx`

**Purpose:** Expose diagnostic information to browser console

**Hooks to Add:**
1. `window.__NVX1_AUDIO_DIAGNOSTICS__`:
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

2. `window.__NVX1_SCORE_LOAD_DIAGNOSTICS__`:
   ```typescript
   {
     scoreLoaded: boolean,
     canonicalScoreParts: number,
     canonicalNoteEvents: number,
     instrumentMapSize: number,
     playbackPlanEvents: number,
   }
   ```

**Acceptance Criteria:**
- All diagnostic hooks exposed
- Hooks update in real-time
- Console accessible for debugging

---

### Phase 2: Root Cause Investigation (Day 1-2)

#### Task 2.1: Verify Score Loading Pipeline
**Action:** Trace NVX1Score → CanonicalScore → PlaybackPlan

**Steps:**
1. Add logging to `loadScore()`:
   - Log input NVX1Score structure
   - Log canonical score conversion result
   - Log instrument map size
   - Log playback plan length

2. Verify `nvx1ScoreToCanonical()`:
   - Check if parts exist
   - Check if measures exist
   - Check if note events are extracted
   - Verify canonical score structure

3. Verify `buildPlaybackPlan()`:
   - Check if canonical score has note events
   - Check if events are converted to PlaybackNote[]
   - Verify playback plan is populated

**Files to Modify:**
- `src/services/audio/AudioPlaybackService.ts:436` (add logging)
- `src/services/audio/AudioPlaybackService.ts:1100+` (add logging)

**Acceptance Criteria:**
- Logging shows score loading pipeline
- Identifies where events are lost
- Provides actionable fix location

---

#### Task 2.2: Verify Event Scheduling
**Action:** Trace PlaybackPlan → AudioScheduler

**Steps:**
1. Check if `start()` is called:
   - Add logging to `PlaybackController.play()`
   - Verify `audioPlaybackService.start()` is invoked
   - Check for errors in `start()` method

2. Check if events are scheduled:
   - Add logging to `start()` method
   - Verify `scheduler.schedule()` is called for each event
   - Check scheduler queue after scheduling

3. Check scheduler state:
   - Verify scheduler is running
   - Check if events are in queue
   - Verify events are processed

**Files to Modify:**
- `src/services/audio/AudioPlaybackService.ts:700+` (add logging)
- `src/services/playback/PlaybackController.ts:173` (add logging)

**Acceptance Criteria:**
- Logging shows event scheduling flow
- Identifies if events are scheduled
- Provides actionable fix location

---

#### Task 2.3: Verify Readiness Check
**Action:** Check if readiness check is blocking playback

**Steps:**
1. Check `getReadinessState()` implementation:
   - Verify `eventCount` calculation
   - Check if `playbackPlan` is checked
   - Verify other readiness criteria

2. Check readiness check logic:
   - Verify if check is too strict
   - Check if events exist but check fails
   - Verify readiness reasons

**Files to Check:**
- `src/services/audio/AudioPlaybackService.ts:880+` (`getReadinessState()`)

**Acceptance Criteria:**
- Readiness check logic understood
- Identifies if check is blocking
- Provides actionable fix

---

#### Task 2.4: Verify Gain Staging
**Action:** Check all audio paths for mute/zero gain

**Steps:**
1. Check SubmixManager:
   - Verify submix volumes
   - Check if any submix is muted
   - Verify routing is correct

2. Check UniversalAudioRouter:
   - Verify router gain
   - Check per-layer volume
   - Verify no paths are muted

3. Check Apollo backend:
   - Verify Apollo volume
   - Check instrument volumes
   - Verify output is connected

**Files to Check:**
- `src/audio/routing/SubmixManager.ts`
- `src/audio/UniversalAudioRouter.ts`
- `src/services/globalApollo.ts`

**Acceptance Criteria:**
- All gain staging verified
- Identifies muted paths
- Provides actionable fix

---

### Phase 3: Targeted Fixes (Day 2-3)

#### Task 3.1: Fix Score Loading (if Hypothesis 1)
**Action:** Ensure score loading creates events

**Potential Fixes:**
1. Fix `nvx1ScoreToCanonical()` if it's not extracting note events
2. Fix `buildPlaybackPlan()` if it's not creating events
3. Fix score data structure if it's missing note data

**Files to Modify:**
- `src/bridge/canonical/nvx1CanonicalBridge.ts` (if conversion issue)
- `src/services/audio/AudioPlaybackService.ts:1100+` (if plan building issue)

**Acceptance Criteria:**
- Score loading creates events
- `playbackPlan.length > 0` after `loadScore()`
- Events are valid and schedulable

---

#### Task 3.2: Fix Event Scheduling (if Hypothesis 2)
**Action:** Ensure events are scheduled to AudioScheduler

**Potential Fixes:**
1. Fix `start()` method if it's not scheduling events
2. Fix `scheduler.schedule()` if it's failing
3. Fix event timing if events are scheduled but at wrong time

**Files to Modify:**
- `src/services/audio/AudioPlaybackService.ts:700+` (`start()` method)

**Acceptance Criteria:**
- Events are scheduled to scheduler
- `scheduler.queue.length > 0` after `start()`
- Events are processed correctly

---

#### Task 3.3: Fix Readiness Check (if Hypothesis 3)
**Action:** Adjust readiness check if too strict

**Potential Fixes:**
1. Relax readiness check if events exist but check fails
2. Fix `getReadinessState()` if it's not calculating correctly
3. Add fallback if readiness check is blocking valid playback

**Files to Modify:**
- `src/services/audio/AudioPlaybackService.ts:880+` (`getReadinessState()`)
- `src/services/playback/PlaybackController.ts:136` (readiness check)

**Acceptance Criteria:**
- Readiness check allows valid playback
- Events are not blocked unnecessarily
- Playback starts when ready

---

#### Task 3.4: Fix Gain Staging (if Hypothesis 4)
**Action:** Ensure audio paths are not muted

**Potential Fixes:**
1. Fix SubmixManager if volumes are zero
2. Fix UniversalAudioRouter if gain is zero
3. Fix Apollo backend if volume is zero
4. Ensure master gain is not zero

**Files to Modify:**
- `src/audio/routing/SubmixManager.ts` (if volume issue)
- `src/audio/UniversalAudioRouter.ts` (if gain issue)
- `src/services/globalApollo.ts` (if Apollo volume issue)

**Acceptance Criteria:**
- All audio paths have non-zero gain
- Audio routing is correct
- Output is audible

---

#### Task 3.5: Fix Browser Autoplay (if Hypothesis 5)
**Action:** Handle macOS Chrome/Safari autoplay restrictions

**Potential Fixes:**
1. Ensure AudioContext is resumed on user interaction
2. Add autoplay policy handling
3. Ensure Tone.js context is unlocked

**Files to Modify:**
- `src/services/audio/bootstrapAudio.ts` (autoplay handling)
- `src/utils/toneUnlock.ts` (context unlocking)

**Acceptance Criteria:**
- AudioContext is running
- Autoplay policies handled
- Audio works on macOS Chrome/Safari

---

### Phase 4: Automated Regression Tests (Day 3)

#### Task 4.1: Create Audio Output Test
**File:** `tests/e2e/nvx1-audio-output.spec.ts` (new)

**Tests:**
1. **Chord Click Audio:**
   - Click chord in NVX1 score
   - Verify AnalyserNode detects audio output (RMS > 0)
   - Assert output within 500ms

2. **Transport Playback:**
   - Start playback
   - Verify continuous audio for >2 beats
   - Assert audio persists during playback

3. **Metronome Audio:**
   - Start metronome
   - Verify metronome events fire
   - Assert audible metronome clicks

**Acceptance Criteria:**
- All tests pass
- Tests detect audio output
- Tests fail if silence persists

**Verification:**
```bash
pnpm playwright test tests/e2e/nvx1-audio-output.spec.ts
```

---

#### Task 4.2: Create Event Scheduling Test
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

## Implementation Order

### Day 1: Diagnostics
1. Create Playwright diagnostic test
2. Add diagnostic debug hooks
3. Run diagnostic test to identify root cause

### Day 2: Investigation
1. Verify score loading pipeline
2. Verify event scheduling
3. Verify readiness check
4. Verify gain staging

### Day 3: Fixes
1. Apply targeted fixes based on root cause
2. Test fixes in browser
3. Verify audio output works

### Day 4: Regression Tests
1. Create automated regression tests
2. Run full test suite
3. Verify all tests pass

---

## Success Criteria

### Immediate (Day 1)
- [ ] Diagnostic test reproduces issue
- [ ] Root cause identified
- [ ] Diagnostic hooks provide actionable data

### Short-term (Day 2-3)
- [ ] Root cause fixed
- [ ] Audio output works on macOS Chrome/Safari
- [ ] All diagnostic tests pass

### Long-term (Day 4)
- [ ] Automated regression tests created
- [ ] Full test suite passes
- [ ] Issue documented and resolved

---

## Risk Mitigation

### High-Risk Areas

1. **Score Loading:**
   - Risk: Score data structure changed, breaking conversion
   - Mitigation: Add comprehensive logging, verify data structure

2. **Event Scheduling:**
   - Risk: Timing issues cause events to be scheduled incorrectly
   - Mitigation: Verify event timing, check scheduler state

3. **Readiness Check:**
   - Risk: Check is too strict, blocking valid playback
   - Mitigation: Relax check if needed, add fallback

4. **Browser Compatibility:**
   - Risk: macOS Chrome/Safari have different behavior
   - Mitigation: Test on all browsers, handle autoplay policies

---

**End of Diagnostic Plan**








