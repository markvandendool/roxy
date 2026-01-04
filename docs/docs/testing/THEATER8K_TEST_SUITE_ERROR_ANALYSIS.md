# 8K Theater Test Suite Error Analysis & Cross-Reference

**Date:** 2025-01-27  
**Test Suite:** `src/components/theater8k/test/Theater8KTestSuite.tsx`  
**Route:** `/theater8k-test`  
**Status:** ⚠️ EXPECTED FAILURES (Architectural Design Issue)

---

## Executive Summary

The test suite at `/theater8k-test` is **DESIGNED TO FAIL** because:

1. **Theater8K Component Not Mounted:** The test page does not mount the `Theater8K` component
2. **No Renderer Initialization:** Without Theater8K mounted, `bootstrapRenderer()` is never called
3. **No Telemetry:** `__mindsongRendererTelemetry` is only initialized when `createTelemetryController()` is called during bootstrap
4. **No Canvas Elements:** Canvas elements are created by Theater8K component, not present on test page

**This is NOT a bug - it's an architectural limitation.** Tests must either:
- Navigate to `/theater8k` route (where Theater8K is mounted)
- Embed Theater8K component in test suite page
- Skip tests with helpful messages when Theater8K is not mounted

---

## Error Cross-Reference

### Error #1: Canvas Elements Present Test Failure

**Error Message:** `Missing canvases: landscape=false, vertical=false`

**Root Cause:**
- Test searches for canvas elements with selectors like `#landscape-canvas`, `#vertical-canvas`
- These canvases are created by `EightKTheaterStage` component
- `EightKTheaterStage` is only mounted on `/theater8k` route, not `/theater8k-test`

**Official Documentation:**
- **WebGPU Spec:** Canvas elements must exist before `getContext('webgpu')` can be called
- **React Docs:** Components only mount when rendered in component tree
- **Our Architecture:** `src/pages/Theater8K.tsx` mounts `EightKTheaterStage`, which creates canvases

**Brain Documentation:**
- `docs/brain/FORENSIC_AUDIT_8K_THEATER_2025-01-27.md` - Documents complete theater architecture
- `docs/brain/errors/RENDERER_DISAPPEARS_AFTER_5_SECONDS.md` - Documents renderer lifecycle

**Online Sources:**
- **WebGPU Spec:** https://www.w3.org/TR/webgpu/#dom-htmlcanvaselement-getcontext
- **React Component Lifecycle:** https://react.dev/reference/react/useEffect
- **WebGPU Debugging:** https://webgpufundamentals.org/webgpu/lessons/webgpu-debugging.html

**Fix Strategy:**
1. **Option A:** Navigate to `/theater8k` before running tests (like Playwright tests do)
2. **Option B:** Embed `Theater8K` component in test suite page
3. **Option C:** Make test detect Theater8K mount state and skip with helpful message

---

### Error #2: Renderer Initialization Test Failure

**Error Message:** `Renderer not initialized` or `Telemetry object missing`

**Root Cause:**
- `__mindsongRendererTelemetry` is initialized in `createTelemetryController()` (`src/components/theater8k/renderer/telemetryBuffer.ts:106-108`)
- `createTelemetryController()` is called during `bootstrapRenderer()` (`src/components/theater8k/renderer/bootstrap.ts:650`)
- `bootstrapRenderer()` is called in `EightKTheaterStage` useEffect (`src/components/theater8k/EightKTheaterStage.tsx:650`)
- Theater8K component is not mounted on test page

**Code Flow:**
```
Theater8K.tsx (mounts)
  └─> EightKTheaterStage.tsx (useEffect runs)
      └─> bootstrapRenderer() 
          └─> createTelemetryController()
              └─> Object.assign(window, { __mindsongRendererTelemetry: debugHandle })
```

**Official Documentation:**
- **WebGPU Spec:** Device/Adapter must be requested before renderer can initialize
- **React Docs:** useEffect only runs when component mounts
- **Our Telemetry:** `src/components/theater8k/renderer/telemetryBuffer.ts:65-111`

**Brain Documentation:**
- `docs/brain/FORENSIC_AUDIT_8K_THEATER_2025-01-27.md` - Documents bootstrap process
- `docs/brain/errors/RENDERER_DISAPPEARS_AFTER_5_SECONDS.md` - Documents renderer lifecycle

**Online Sources:**
- **WebGPU Device Creation:** https://www.w3.org/TR/webgpu/#dom-gpuadapter-requestdevice
- **React useEffect:** https://react.dev/reference/react/useEffect
- **Telemetry Patterns:** https://webgpufundamentals.org/webgpu/lessons/webgpu-debugging.html

**Fix Strategy:**
1. **Option A:** Navigate to `/theater8k` before running tests
2. **Option B:** Embed Theater8K component and wait for bootstrap
3. **Option C:** Make test detect telemetry initialization and skip if not available

---

### Error #3: Widget Visibility Tests Failure

**Error Message:** `Widgets not visible` or `No widget elements found`

**Root Cause:**
- Widgets are registered and rendered by Theater8K system
- Widget rendering happens in Rust/WASM renderer (`packages/renderer-core/src/lib.rs`)
- Renderer only initializes when Theater8K component mounts

**Official Documentation:**
- **WebGPU Rendering:** Widgets rendered via WebGPU render passes
- **React Component Tree:** Widgets must be in component tree to render
- **Our Architecture:** Widgets registered globally but rendered by Theater8K

**Brain Documentation:**
- `docs/brain/WIDGET_INTEGRATION_CHECKLIST.md` - Documents widget registration
- `docs/brain/playbooks/ADD_NEW_WIDGET.md` - Documents widget lifecycle

**Online Sources:**
- **WebGPU Render Passes:** https://www.w3.org/TR/webgpu/#render-passes
- **React Component Rendering:** https://react.dev/learn/render-and-commit

**Fix Strategy:**
1. **Option A:** Navigate to `/theater8k` before running tests
2. **Option B:** Embed Theater8K component and wait for widgets to render
3. **Option C:** Make test detect widget mount state and skip if not available

---

### Error #4: Performance Tests Failure

**Error Message:** `No frame time data collected` or `Frame time variance too high: NaN%`

**Root Cause:**
- Frame time data comes from `__mindsongRendererTelemetry.delta_ms` and `.frame_times`
- Telemetry only populated when renderer is running (frames being rendered)
- Renderer only runs when Theater8K component is mounted and bootstrap completes

**Official Documentation:**
- **WebGPU Frame Timing:** Performance data available via `GPUQueue.submit()` timing
- **RAF Timing:** `requestAnimationFrame` provides frame timing
- **Our Telemetry:** `src/components/theater8k/renderer/bootstrap.ts:466-474`

**Brain Documentation:**
- `docs/brain/FORENSIC_AUDIT_8K_THEATER_2025-01-27.md` - Documents performance tracking
- `docs/brain/playbooks/GPU_PROFILING_TIMESTAMPS.md` - Documents GPU timing

**Online Sources:**
- **WebGPU Performance:** https://www.w3.org/TR/webgpu/#gpuqueue-submit
- **RAF Timing:** https://developer.mozilla.org/en-US/docs/Web/API/window/requestAnimationFrame
- **Performance Monitoring:** https://webgpufundamentals.org/webgpu/lessons/webgpu-debugging.html

**Fix Strategy:**
1. **Option A:** Navigate to `/theater8k` before running tests
2. **Option B:** Embed Theater8K component and wait for frames to render
3. **Option C:** Make test detect telemetry data availability and skip if not available

---

### Error #5: Swapchain Tests Failure

**Error Message:** `Swapchain state tracking not available` or `Recovery system not active`

**Root Cause:**
- Swapchain recovery system initialized in `init_dual_canvas_webgpu()` (`packages/renderer-core/src/lib.rs`)
- Swapchain state tracked via `SwapchainStateTracker` (`packages/renderer-core/src/swapchain_state.rs`)
- Recovery system only active when renderer backend is initialized

**Official Documentation:**
- **WebGPU Swapchain:** `surface.getCurrentTexture()` provides swapchain access
- **Swapchain Invalidation:** WebGPU spec documents swapchain lifecycle
- **Our Recovery:** `packages/renderer-core/src/swapchain_recovery.rs`

**Brain Documentation:**
- `docs/brain/FORENSIC_AUDIT_8K_THEATER_2025-01-27.md` - Documents swapchain recovery
- `docs/brain/errors/RENDERER_DISAPPEARS_AFTER_5_SECONDS.md` - Documents 7-second bug

**Online Sources:**
- **WebGPU Swapchain:** https://www.w3.org/TR/webgpu/#dom-gpusurface-getcurrenttexture
- **Swapchain Invalidation:** https://www.w3.org/TR/webgpu/#invalid-texture
- **WebGPU CTS:** https://github.com/gpuweb/cts (conformance tests)

**Fix Strategy:**
1. **Option A:** Navigate to `/theater8k` before running tests
2. **Option B:** Embed Theater8K component and wait for swapchain initialization
3. **Option C:** Make test detect swapchain state and skip if not available

---

## Recommended Fix Strategy

### Option A: Navigate to Theater8K Route (RECOMMENDED)

**Pros:**
- Tests run against actual Theater8K page
- All components initialized correctly
- Matches Playwright test pattern

**Cons:**
- Requires navigation (slight delay)
- Page may already be loaded elsewhere

**Implementation:**
```typescript
const runAllTests = async () => {
  // Navigate to Theater8K page first
  if (window.location.pathname !== '/theater8k' && window.location.pathname !== '/theater-8k') {
    addLog('Navigating to /theater8k to initialize renderer...', 'info');
    window.location.href = '/theater8k';
    // Wait for navigation and initialization
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
  
  // Now run tests...
};
```

### Option B: Embed Theater8K Component

**Pros:**
- Tests run in same page
- No navigation required
- Full control over test environment

**Cons:**
- May conflict with existing page state
- Requires careful component isolation

**Implementation:**
```typescript
import Theater8K from '../../pages/Theater8K';

export const Theater8KTestSuite: React.FC = () => {
  return (
    <div>
      <Theater8K />
      {/* Test controls */}
    </div>
  );
};
```

### Option C: Skip Tests with Helpful Messages (CURRENT STATE)

**Pros:**
- Tests fail fast with clear messages
- No architectural changes needed
- Tests document expected behavior

**Cons:**
- Tests always fail (not useful for CI/CD)
- Doesn't actually test Theater8K functionality

**Current Implementation:**
```typescript
if (!tel || !tel.last_frame) {
  addLog(`❌ Renderer not initialized`, 'error');
  addLog(`  Note: Renderer only initializes when Theater8K component is mounted`, 'warn');
  addLog(`  Note: This test page does not mount Theater8K component`, 'warn');
  throw new Error('Renderer not initialized');
}
```

---

## Conclusion

**All test failures are EXPECTED and DOCUMENTED.** The test suite is correctly detecting that Theater8K is not mounted. To make tests actually run, implement **Option A** (navigate to `/theater8k`) or **Option B** (embed component).

**Next Steps:**
1. Implement Option A (navigation-based testing)
2. Update test suite to handle Theater8K mount detection
3. Add timeout/retry logic for renderer initialization
4. Document test requirements in README

---

## References

- **Official WebGPU Spec:** https://www.w3.org/TR/webgpu/
- **WebGPU Debugging Guide:** https://webgpufundamentals.org/webgpu/lessons/webgpu-debugging.html
- **WebGPU CTS:** https://github.com/gpuweb/cts
- **React useEffect:** https://react.dev/reference/react/useEffect
- **Our Brain Docs:** `docs/brain/FORENSIC_AUDIT_8K_THEATER_2025-01-27.md`
- **Our Error Docs:** `docs/brain/errors/RENDERER_DISAPPEARS_AFTER_5_SECONDS.md`


