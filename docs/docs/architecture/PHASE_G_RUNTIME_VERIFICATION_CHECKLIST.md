# Phase G Runtime Verification Checklist
**Status:** Pre-Unfreeze Preparation  
**Last Updated:** 2025-11-30

---

## Overview

This checklist provides step-by-step verification procedures for Phase G unfreeze. All items should be verified after unfreezing and before release.

---

## Pre-Verification Setup

### 1. Environment Preparation

- [ ] Start dev server: `pnpm dev`
- [ ] Open browser console (F12)
- [ ] Enable debug mode:
  ```javascript
  window.__KHRONOS_DEBUG = true;
  window.__KHRONOS_DEBUG_DRIFT = true;
  ```
- [ ] Clear browser cache
- [ ] Use Chrome DevTools Performance tab (for timing analysis)

---

## Core System Verification

### 2. AudioWorklet Clock

**Goal:** Verify AudioWorklet clock loads and runs correctly.

- [ ] **Check Console for Errors**
  - Open browser console
  - Look for: `[KhronosEngine] Failed to load AudioWorklet clock`
  - ✅ **Pass:** No errors
  - ❌ **Fail:** Error loading AudioWorklet

- [ ] **Verify Clock Loads**
  - Check Network tab: `/worklets/khronos-clock.js` loads successfully
  - Check console: `[KhronosEngine] Created singleton AudioContext`
  - ✅ **Pass:** Clock loads, AudioContext created
  - ❌ **Fail:** Clock fails to load

- [ ] **Verify Beat Calculation**
  - Start playback
  - Check console for AudioWorklet messages (if debug enabled)
  - Verify beats increment correctly
  - ✅ **Pass:** Beats increment smoothly
  - ❌ **Fail:** Beats don't increment or jump erratically

**Expected Behavior:**
- AudioWorklet loads without errors
- Beats increment at correct tempo
- No console errors

---

### 3. KhronosBus Tick Verification

**Goal:** Verify KhronosBus publishes ticks at correct frequency.

- [ ] **Check Tick Frequency**
  - Start playback
  - Monitor `KhronosBus.getTelemetry().ticksPublished`
  - Should increment ~60 times per second (60Hz)
  - ✅ **Pass:** ~60 ticks/second
  - ❌ **Fail:** Too few or too many ticks

- [ ] **Check Tick Timestamps**
  - Verify `tick.timestamp` is `performance.now()`
  - Check for timestamp gaps or regressions
  - ✅ **Pass:** Timestamps are valid and increasing
  - ❌ **Fail:** Timestamps are invalid or regress

- [ ] **Check Position Updates**
  - Verify `tick.position` updates correctly
  - Check `measureIndex`, `beatInMeasure`, `ticks` increment
  - ✅ **Pass:** Position updates correctly
  - ❌ **Fail:** Position doesn't update or jumps

- [ ] **Check Telemetry**
  ```javascript
  const telemetry = window.__khronosBus.getTelemetry();
  console.log('Jitter Max:', telemetry.jitterMaxMs);
  console.log('Drift Heat:', telemetry.driftHeat);
  console.log('Integrity Score:', telemetry.positionalIntegrityScore);
  ```
- ✅ **Pass:** Jitter < 50ms, Integrity Score > 80
  - ❌ **Fail:** High jitter or low integrity score

**Expected Behavior:**
- Ticks publish at ~60Hz during playback
- Position updates smoothly
- Low jitter (<50ms)
- High integrity score (>80)

**Verification Run (2025-11-30)**
- [x] Jitter < 50ms (Port p95: 4.05ms, max: 4.15ms; Audio p95: 0ms)
- [x] Integrity > 80 (ticks captured: 160/160, dropped: 0)
- [x] Shared buffer enabled; cross-origin isolated: true

---

### 4. Basic Audio Playback

**Goal:** Verify audio actually plays.

- [ ] **Load a Score**
  - Load a test score (e.g., simple MIDI file)
  - Verify score loads without errors
  - ✅ **Pass:** Score loads successfully
  - ❌ **Fail:** Score fails to load

- [ ] **Press Play**
  - Click play button
  - Verify transport state changes to "playing"
  - ✅ **Pass:** State changes to playing
  - ❌ **Fail:** State doesn't change

- [ ] **Verify Audio Output**
  - Listen for audio output
  - Check for clicks, pops, or artifacts
  - ✅ **Pass:** Audio plays clearly
  - ❌ **Fail:** No audio or audio has artifacts

- [ ] **Verify Timing Accuracy**
  - Play a known score (e.g., 120 BPM)
  - Verify timing matches expected tempo
  - ✅ **Pass:** Timing is accurate
  - ❌ **Fail:** Timing is off

**Expected Behavior:**
- Audio plays when play is pressed
- No clicks, pops, or artifacts
- Timing is accurate

---

### 5. Metronome Click

**Goal:** Verify metronome clicks on beat.

- [ ] **Enable Metronome**
  - Enable metronome in UI
  - Verify metronome is enabled
  - ✅ **Pass:** Metronome enables
  - ❌ **Fail:** Metronome doesn't enable

- [ ] **Verify Click Timing**
  - Start playback
  - Listen for metronome clicks
  - Verify clicks align with beat
  - ✅ **Pass:** Clicks align with beat
  - ❌ **Fail:** Clicks are off-beat

- [ ] **Verify Tempo Changes**
  - Change tempo (e.g., 120 → 140 BPM)
  - Verify metronome adjusts
  - ✅ **Pass:** Metronome adjusts to new tempo
  - ❌ **Fail:** Metronome doesn't adjust

**Expected Behavior:**
- Metronome clicks on beat
- Clicks align with transport position
- Tempo changes work correctly

---

## UI Sync Verification

### 6. Widget Sync

**Goal:** Verify UI widgets sync to transport.

- [ ] **Playhead Movement**
  - Start playback
  - Watch playhead move
  - Verify smooth movement
  - ✅ **Pass:** Playhead moves smoothly
  - ❌ **Fail:** Playhead stutters or doesn't move

- [ ] **Widget Updates**
  - Check various widgets (score, fretboard, etc.)
  - Verify they update with transport position
  - ✅ **Pass:** Widgets update correctly
  - ❌ **Fail:** Widgets don't update

- [ ] **Visual Lag**
  - Check for visual lag between transport and UI
  - Should be < 50ms
  - ✅ **Pass:** Visual lag < 50ms
  - ❌ **Fail:** Visual lag > 50ms

**Expected Behavior:**
- Widgets sync to transport
- Smooth visual updates
- Low visual lag

---

## Advanced Features

### 7. Seek Operations

**Goal:** Verify seek works correctly.

- [ ] **Seek to Position**
  - Seek to measure 4, beat 2
  - Verify position updates
  - ✅ **Pass:** Position updates correctly
  - ❌ **Fail:** Position doesn't update

- [ ] **Seek During Playback**
  - Start playback
  - Seek to different position
  - Verify playback continues from new position
  - ✅ **Pass:** Playback continues correctly
  - ❌ **Fail:** Playback stops or jumps incorrectly

**Expected Behavior:**
- Seek updates position correctly
- Playback continues from new position

---

### 8. Tempo Changes

**Goal:** Verify tempo changes work.

- [ ] **Change Tempo**
  - Change tempo from 120 to 140 BPM
  - Verify tempo updates
  - ✅ **Pass:** Tempo updates correctly
  - ❌ **Fail:** Tempo doesn't update

- [ ] **Tempo During Playback**
  - Start playback
  - Change tempo
  - Verify playback adjusts to new tempo
  - ✅ **Pass:** Playback adjusts correctly
  - ❌ **Fail:** Playback doesn't adjust

**Expected Behavior:**
- Tempo changes work
- Playback adjusts to new tempo

---

### 9. Loop Regions

**Goal:** Verify loop regions work.

- [ ] **Set Loop**
  - Set loop from measure 0 to measure 4
  - Verify loop is set
  - ✅ **Pass:** Loop is set correctly
  - ❌ **Fail:** Loop doesn't set

- [ ] **Loop Playback**
  - Start playback
  - Verify playback loops at loop end
  - ✅ **Pass:** Playback loops correctly
  - ❌ **Fail:** Playback doesn't loop

- [ ] **Clear Loop**
  - Clear loop
  - Verify loop is cleared
  - ✅ **Pass:** Loop is cleared
  - ❌ **Fail:** Loop doesn't clear

**Expected Behavior:**
- Loop regions work correctly
- Playback loops at loop boundaries
- Loop can be cleared

---

## Performance Verification

### 10. EventSpine Query Performance

**Goal:** Verify EventSpine queries are fast enough.

- [ ] **Query Latency**
  - Load large score (1000+ measures)
  - Query events at current position
  - Verify query latency < 100ms
  - ✅ **Pass:** Query latency < 100ms
  - ❌ **Fail:** Query latency > 100ms

- [ ] **Memory Usage**
  - Monitor memory usage during playback
  - Verify no memory leaks
  - ✅ **Pass:** Memory usage stable
  - ❌ **Fail:** Memory leaks detected

**Expected Behavior:**
- Query latency < 100ms
- No memory leaks

---

### 11. VGMEngine Latency

**Goal:** Verify VGMEngine meets latency target.

- [ ] **Live MIDI Input**
  - Send MIDI input
  - Measure latency from input to audio output
  - Target: < 15ms
  - ✅ **Pass:** Latency < 15ms
  - ❌ **Fail:** Latency > 15ms

- [ ] **Scheduled Playback**
  - Schedule notes
  - Verify scheduling accuracy
  - ✅ **Pass:** Scheduling is accurate
  - ❌ **Fail:** Scheduling is inaccurate

**Expected Behavior:**
- Live MIDI latency < 15ms
- Scheduled playback is accurate

---

## Error Handling

### 12. Error Scenarios

**Goal:** Verify error handling works.

- [ ] **Invalid Commands**
  - Send invalid command
  - Verify error is handled gracefully
  - ✅ **Pass:** Error handled gracefully
  - ❌ **Fail:** Error crashes or breaks system

- [ ] **Audio Context Suspension**
  - Suspend audio context (e.g., switch tabs)
  - Verify system handles suspension
  - ✅ **Pass:** System handles suspension
  - ❌ **Fail:** System breaks on suspension

**Expected Behavior:**
- Errors are handled gracefully
- System recovers from errors

---

## Browser Compatibility

### 13. Cross-Browser Testing

**Goal:** Verify compatibility across browsers.

- [ ] **Chrome**
  - Test all verification items in Chrome
  - ✅ **Pass:** All items pass
  - ❌ **Fail:** Some items fail

- [ ] **Firefox**
  - Test all verification items in Firefox
  - ✅ **Pass:** All items pass
  - ❌ **Fail:** Some items fail

- [ ] **Safari**
  - Test all verification items in Safari
  - ✅ **Pass:** All items pass
  - ❌ **Fail:** Some items fail

**Expected Behavior:**
- Works in all major browsers
- No browser-specific issues

---

## Summary

### Pass Criteria

**Release is ready when:**
- ✅ All Core System Verification items pass
- ✅ All Basic Audio Playback items pass
- ✅ All UI Sync Verification items pass
- ✅ All Advanced Features items pass
- ✅ Performance is acceptable
- ✅ Error handling works
- ✅ Cross-browser compatibility verified

### Fail Criteria

**Do not release if:**
- ❌ AudioWorklet clock fails to load
- ❌ KhronosBus ticks are not publishing
- ❌ Audio doesn't play
- ❌ Critical performance issues
- ❌ Critical bugs

---

## Next Steps After Verification

1. **Document Issues**
   - Log all failures
   - Prioritize fixes
   - Create bug tickets

2. **Fix Issues**
   - Fix critical issues first
   - Test fixes
   - Re-verify

3. **Release**
   - All critical items pass
   - Performance is acceptable
   - Documentation updated

---

**Last Updated:** 2025-11-30  
**Status:** Pre-Unfreeze Preparation







