# 8K Theater Regression Prevention Guide

## Overview

This document outlines the regression prevention strategy for the 8K Theater, ensuring critical bugs never resurface.

## Critical Bugs Never to Regress

### 1. 7-Second Disappearance Bug

**Description:** Content disappears after ~7 seconds due to swapchain invalidation.

**Prevention:**
- ✅ Swapchain state machine tracks invalidation
- ✅ Automatic recovery with exponential backoff
- ✅ 7-second timeout detection
- ✅ Continuous monitoring in regression tests

**Test:** `tests/e2e/theater8k.regression.spec.ts` - "content remains visible after 7 seconds"

**Key Code:**
- `packages/renderer-core/src/swapchain_state.rs` - State tracking
- `packages/renderer-core/src/swapchain_recovery.rs` - Recovery logic
- `packages/renderer-core/src/lib.rs` - Integration in render loop

### 2. Piano Visibility

**Description:** Piano widget not visible on load or after camera changes.

**Prevention:**
- ✅ Widget bounds validation
- ✅ Frustum culling checks
- ✅ Camera preset system
- ✅ Visibility tests on every load

**Test:** `tests/e2e/theater8k.visibility.spec.ts` - "piano is visible on load"

**Key Code:**
- `packages/renderer-core/src/widget_bounds.rs` - Bounds calculation
- `packages/renderer-core/src/scene_camera.rs` - Camera positioning
- `packages/renderer-core/src/camera_presets.rs` - Preset system

### 3. Camera Positioning

**Description:** Camera positions incorrect for landscape/vertical orientations.

**Prevention:**
- ✅ Orientation-specific cameras
- ✅ Aspect ratio validation
- ✅ View frustum calculations
- ✅ Camera preset tests

**Test:** `tests/e2e/theater8k.regression.spec.ts` - "camera positions are correct"

**Key Code:**
- `packages/renderer-core/src/scene_camera.rs` - Camera setup
- `packages/renderer-core/src/lib.rs` - Dual canvas initialization

### 4. Swapchain Recovery

**Description:** Swapchain recovery fails or doesn't trigger.

**Prevention:**
- ✅ State machine tracks recovery attempts
- ✅ Exponential backoff prevents overload
- ✅ Retry logic with max attempts
- ✅ Recovery tests verify functionality

**Test:** `tests/e2e/theater8k.regression.spec.ts` - "recovery system handles failures"

**Key Code:**
- `packages/renderer-core/src/swapchain_recovery.rs` - Recovery implementation
- `packages/renderer-core/src/lib.rs` - Recovery integration

## Test Suite Structure

### Visibility Tests (`theater8k.visibility.spec.ts`)
- Initial load visibility
- 30-second persistence (detects 7s bug)
- Resize handling
- Device loss recovery
- Frustum culling
- Camera presets

### Performance Tests (`theater8k.performance.spec.ts`)
- 60fps target
- Frame time variance
- Memory usage
- GPU timing
- Widget draw times

### Regression Tests (`theater8k.regression.spec.ts`)
- 7-second bug
- Piano visibility
- Camera positioning
- Swapchain recovery

## Continuous Testing

### GitHub Actions Workflow

**File:** `.github/workflows/theater8k-regression.yml`

**Triggers:**
- Push to main/develop (renderer-core or theater8k changes)
- Pull requests
- Nightly schedule (2 AM UTC)
- Manual dispatch

**Test Execution:**
1. Build renderer-core (WASM)
2. Build frontend
3. Start dev server
4. Run visibility tests
5. Run performance tests
6. Run regression tests
7. Upload results and screenshots

### Local Testing

```bash
# Run all 8K Theater tests
pnpm exec playwright test tests/e2e/theater8k.*.spec.ts

# Run specific suite
pnpm exec playwright test tests/e2e/theater8k.visibility.spec.ts
pnpm exec playwright test tests/e2e/theater8k.performance.spec.ts
pnpm exec playwright test tests/e2e/theater8k.regression.spec.ts

# Run with UI
pnpm exec playwright test tests/e2e/theater8k.*.spec.ts --ui

# Run with debug
pnpm exec playwright test tests/e2e/theater8k.*.spec.ts --debug
```

## Pre-Commit Checklist

Before committing changes to renderer-core or theater8k:

- [ ] Run visibility tests locally
- [ ] Run performance tests locally
- [ ] Run regression tests locally
- [ ] Verify no console errors
- [ ] Check swapchain recovery logs
- [ ] Verify camera positioning
- [ ] Confirm piano visibility

## Code Review Checklist

When reviewing PRs affecting 8K Theater:

- [ ] Do changes affect swapchain management?
- [ ] Do changes affect camera positioning?
- [ ] Do changes affect widget visibility?
- [ ] Are new tests added for regressions?
- [ ] Do tests pass in CI?
- [ ] Are screenshots updated if visual changes?

## Monitoring

### Key Metrics

1. **Swapchain Invalidation Rate**
   - Track `SwapchainState::Invalidated` occurrences
   - Should be <1% of frames

2. **Recovery Success Rate**
   - Track successful recovery attempts
   - Should be >95%

3. **Frame Time Consistency**
   - Track frame time variance
   - Should be <5% coefficient of variation

4. **Memory Usage**
   - Track JS heap size
   - Should be <500MB

5. **Visibility Failures**
   - Track widget visibility test failures
   - Should be 0%

### Alerting

Set up alerts for:
- Test failures in CI
- Swapchain invalidation >5%
- Frame time variance >10%
- Memory usage >600MB

## Documentation Updates

When fixing regressions:

1. Document the bug in this file
2. Add prevention measures
3. Add test cases
4. Update code comments
5. Update related documentation

## Related Documentation

- `docs/brain/playbooks/BULLETPROOF_WEBGPU.md` - WebGPU best practices
- `docs/brain/patterns/RENDER_PASS_SETUP.md` - Render pass patterns
- `docs/brain/decisions/WASM_BOUNDARY.md` - WASM boundary rules
- `docs/brain/playbooks/WIDGET_INTEGRATION_CHECKLIST.md` - Widget integration

## Historical Context

### 7-Second Bug Timeline

1. **Initial Discovery:** Content disappeared after ~7 seconds
2. **Workaround:** Periodic reconfiguration every 420 frames
3. **Root Cause:** Swapchain invalidation without recovery
4. **Solution:** State machine + automatic recovery
5. **Prevention:** Continuous regression testing

### Piano Visibility Timeline

1. **Initial Issue:** Piano not visible on load
2. **Root Cause:** Incorrect camera positioning/scaling
3.100x → 500x → 275x scaling adjustments
4. **Solution:** Widget bounds + camera presets
5. **Prevention:** Visibility tests + frustum validation

## Questions?

If you encounter a regression:

1. Check this document for prevention measures
2. Review test suite for coverage
3. Check CI test results
4. Review recent changes to related code
5. Add new test case if needed
6. Update this document


