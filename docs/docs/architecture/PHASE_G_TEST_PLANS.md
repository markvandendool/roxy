# Phase G Test Plans
**Status:** Pre-Unfreeze Preparation  
**Last Updated:** 2025-11-30

---

## Overview

This document outlines test plans for Phase G unfreeze. Tests are organized by priority and system area.

---

## Test Priority Levels

- **P0 (Critical):** Must pass before release
- **P1 (High):** Should pass before release
- **P2 (Medium):** Nice to have before release
- **P3 (Low):** Can be deferred

---

## Unit Tests

### KhronosBus Tests

**Priority:** P0

**Test File:** `src/khronos/__tests__/khronos.integration.test.ts`

**Test Cases:**
- [ ] Subscribe/unsubscribe works
- [ ] Tick events publish correctly
- [ ] Command events publish correctly
- [ ] Telemetry updates correctly
- [ ] Validation works (dev mode)
- [ ] Multiple subscribers work
- [ ] Unsubscribe cleanup works

**Expected Results:**
- All subscriptions work
- Events publish correctly
- Telemetry is accurate
- No memory leaks

---

### KhronosEngine Tests

**Priority:** P0

**Test File:** `src/khronos/__tests__/khronos.engine.test.ts` (to be created)

**Test Cases:**
- [ ] Engine initializes correctly
- [ ] AudioWorklet loads successfully
- [ ] Commands are handled correctly
- [ ] Ticks publish at correct frequency
- [ ] Position updates correctly
- [ ] Tempo changes work
- [ ] Loop regions work
- [ ] Seek operations work
- [ ] Engine disposes correctly

**Expected Results:**
- Engine initializes without errors
- All commands work
- Ticks publish correctly
- No memory leaks

---

### AudioScheduler Tests

**Priority:** P0

**Test File:** `src/services/audio/__tests__/AudioScheduler.test.ts`

**Test Cases:**
- [ ] Events schedule correctly
- [ ] Events fire at correct time
- [ ] KhronosBus integration works
- [ ] Queue overflow handling works
- [ ] Lookahead scheduling works
- [ ] Cleanup works

**Expected Results:**
- Events schedule and fire correctly
- KhronosBus integration works
- No memory leaks

---

## Integration Tests

### Transport Integration

**Priority:** P0

**Test File:** `tests/khronos/khronos-loop-timing.spec.ts`

**Test Cases:**
- [ ] Play/pause/stop work
- [ ] Seek works correctly
- [ ] Tempo changes work
- [ ] Loop regions work
- [ ] Position updates correctly
- [ ] Multiple widgets sync correctly

**Expected Results:**
- All transport operations work
- Widgets sync correctly
- No timing issues

---

### Audio Playback Integration

**Priority:** P0

**Test File:** `tests/audio/nvx1-metronome-sync.spec.ts`

**Test Cases:**
- [ ] Audio plays correctly
- [ ] Metronome clicks on beat
- [ ] Timing is accurate
- [ ] No clicks/pops/artifacts
- [ ] Tempo changes work
- [ ] Loop regions work

**Expected Results:**
- Audio plays correctly
- Timing is accurate
- No audio artifacts

---

### EventSpine Integration

**Priority:** P1

**Test File:** `src/services/__tests__/EventSpineTransportSync.test.ts`

**Test Cases:**
- [ ] EventSpine syncs to transport
- [ ] Queries work at current position
- [ ] Performance is acceptable
- [ ] Large scores work
- [ ] Memory usage is acceptable

**Expected Results:**
- EventSpine syncs correctly
- Queries are fast (<100ms)
- No memory leaks

---

## E2E Tests

### Full Playback Flow

**Priority:** P0

**Test File:** `tests/e2e/transport.full-playback.spec.ts`

**Test Cases:**
- [ ] Load score
- [ ] Press play
- [ ] Audio plays
- [ ] Position updates
- [ ] Widgets sync
- [ ] Press pause
- [ ] Press stop
- [ ] Seek works
- [ ] Tempo changes work
- [ ] Loop regions work

**Expected Results:**
- Full flow works end-to-end
- No errors
- Performance is acceptable

---

### Theater Widget Sync

**Priority:** P1

**Test File:** `tests/e2e/theater8k.transport.spec.ts`

**Test Cases:**
- [ ] Widgets sync to transport
- [ ] Playhead moves correctly
- [ ] Visual updates are smooth
- [ ] No visual lag
- [ ] Multiple widgets work together

**Expected Results:**
- Widgets sync correctly
- Visual updates are smooth
- No visual lag

---

## Performance Tests

### Tick Frequency Test

**Priority:** P0

**Test:** Verify ticks publish at ~60Hz

**Test Steps:**
1. Start playback
2. Monitor `KhronosBus.getTelemetry().ticksPublished`
3. Measure over 1 second
4. Verify ~60 ticks/second

**Expected Results:**
- ~60 ticks/second
- No gaps
- Consistent frequency

---

### Jitter Test

**Priority:** P1

**Test:** Verify jitter is acceptable

**Test Steps:**
1. Start playback
2. Monitor `KhronosBus.getTelemetry().jitterMaxMs`
3. Run for 30 seconds
4. Verify jitter < 50ms

**Expected Results:**
- Jitter < 50ms
- Consistent timing

---

### EventSpine Query Performance

**Priority:** P1

**Test:** Verify query performance

**Test Steps:**
1. Load large score (1000+ measures)
2. Query events at current position
3. Measure query latency
4. Verify < 100ms

**Expected Results:**
- Query latency < 100ms
- Performance is acceptable

---

### VGMEngine Latency Test

**Priority:** P1

**Test:** Verify VGMEngine latency

**Test Steps:**
1. Send MIDI input
2. Measure latency to audio output
3. Verify < 15ms

**Expected Results:**
- Latency < 15ms
- Acceptable for live input

---

## Regression Tests

### Re-enable Skipped Tests

**Priority:** P1

**Test:** Re-enable and fix skipped tests

**Test Steps:**
1. Review ~191 skipped tests
2. Re-enable transport-related tests
3. Fix any broken tests
4. Verify all pass

**Expected Results:**
- All transport tests pass
- No regressions

---

## Browser Compatibility Tests

### Chrome

**Priority:** P0

**Test Cases:**
- [ ] All P0 tests pass
- [ ] Audio works
- [ ] Transport works
- [ ] No console errors

---

### Firefox

**Priority:** P0

**Test Cases:**
- [ ] All P0 tests pass
- [ ] Audio works
- [ ] Transport works
- [ ] No console errors

---

### Safari

**Priority:** P1

**Test Cases:**
- [ ] All P0 tests pass
- [ ] Audio works
- [ ] Transport works
- [ ] No console errors

---

## Test Execution Plan

### Phase 1: Core System Tests (Day 1)

1. Run KhronosBus unit tests
2. Run KhronosEngine tests
3. Run AudioScheduler tests
4. Fix any failures

**Success Criteria:**
- All P0 unit tests pass

---

### Phase 2: Integration Tests (Day 2)

1. Run transport integration tests
2. Run audio playback integration tests
3. Run EventSpine integration tests
4. Fix any failures

**Success Criteria:**
- All P0 integration tests pass

---

### Phase 3: E2E Tests (Day 3)

1. Run full playback flow test
2. Run theater widget sync test
3. Fix any failures

**Success Criteria:**
- All P0 E2E tests pass

---

### Phase 4: Performance Tests (Day 4)

1. Run tick frequency test
2. Run jitter test
3. Run EventSpine query performance test
4. Run VGMEngine latency test
5. Fix any performance issues

**Success Criteria:**
- All performance targets met

---

### Phase 5: Regression Tests (Day 5)

1. Re-enable skipped tests
2. Fix broken tests
3. Verify all pass

**Success Criteria:**
- All transport tests pass

---

## Test Automation

### CI/CD Integration

**Priority:** P1

**Test Steps:**
1. Add test scripts to CI/CD
2. Run tests on every commit
3. Block merge on test failures

**Expected Results:**
- Tests run automatically
- Failures block merge

---

## Test Reporting

### Test Results Dashboard

**Priority:** P2

**Features:**
- Test pass/fail rates
- Performance metrics
- Coverage reports
- Historical trends

---

## Success Criteria

### Release Ready When:

- ✅ All P0 tests pass
- ✅ All P1 tests pass (or documented known issues)
- ✅ Performance targets met
- ✅ No critical bugs
- ✅ Cross-browser compatibility verified

---

**Last Updated:** 2025-11-30  
**Status:** Pre-Unfreeze Preparation








