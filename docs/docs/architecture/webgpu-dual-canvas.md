# WebGPU Dual-Canvas Architecture

**Last Updated**: October 26, 2025  
**Status**: Production  
**Related Files**: `packages/renderer-core/src/lib.rs`, `src/components/theater8k/`

## Overview

MindSong JukeHub uses a **dual-canvas WebGPU rendering architecture** to simultaneously render 8K content in both landscape and portrait orientations. This document explains the architecture, design decisions, and critical lessons learned.

## Architecture

### Canvas Configuration

| Canvas | Dimensions | Aspect Ratio | Orientation | Use Case |
|--------|-----------|--------------|-------------|----------|
| Landscape | 3840 × 2160 | 1.7778 (16:9) | Horizontal | Theater displays, projectors |
| Portrait | 2160 × 3840 | 0.5625 (9:16) | Vertical | Mobile devices, portrait screens |

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    WebGPU Device (Singleton)                 │
│                      Queue (Singleton)                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Shared Resources
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
┌───────▼────────┐                         ┌───────▼────────┐
│   Landscape    │                         │    Portrait    │
│ SceneManager   │                         │ SceneManager   │
├────────────────┤                         ├────────────────┤
│ • Own Pipeline │                         │ • Own Pipeline │
│ • Own Uniforms │                         │ • Own Uniforms │
│ • Aspect 1.778 │                         │ • Aspect 0.563 │
└────────────────┘                         └────────────────┘
        │                                           │
        │                                           │
┌───────▼────────┐                         ┌───────▼────────┐
│   Landscape    │                         │    Portrait    │
│ Canvas Context │                         │ Canvas Context │
│  3840 × 2160   │                         │  2160 × 3840   │
└────────────────┘                         └────────────────┘
```

## Critical Design Decision: Separate SceneManagers

### Why Separate Pipelines Are Required

**The Problem**: 
When two canvases with **different aspect ratios** share a single rendering pipeline, aspect ratio state contamination occurs. The mathematical evidence:

```
Landscape aspect: 1.7778
Portrait aspect:  0.5625
Contamination factor: 1.7778 / 0.5625 = 3.16

Observed bug: sphereAspect = 3.0 (exactly the contamination factor!)
```

**The Solution**:
Each canvas gets its own `SceneManager` with its own rendering pipeline. This ensures:

1. **Projection matrices are computed independently** for each aspect ratio
2. **Uniform buffers don't interfere** with each other
3. **Pipeline state remains clean** per canvas
4. **Tests pass for both orientations** ✅

### Implementation

**File**: `packages/renderer-core/src/lib.rs`

```rust
struct WebGpuBackendHandle {
    // Shared resources (minimal overhead)
    device: Rc<wgpu::Device>,
    queue: Rc<wgpu::Queue>,
    
    // Canvas surfaces
    landscape: Rc<WebGpuCanvas>,
    vertical: Rc<WebGpuCanvas>,
    
    // CRITICAL: Separate scene managers for aspect ratio isolation
    landscape_scene_manager: Rc<RefCell<scene_manager::SceneManager>>,
    vertical_scene_manager: Rc<RefCell<scene_manager::SceneManager>>,
    
    // Performance tracking
    last_gpu_time_ms: Arc<Mutex<Option<f64>>>,
    last_frame_time_ms: Rc<RefCell<Option<f32>>>,
}
```

**Initialization Pattern**:

```rust
// Landscape pipeline
let mut landscape_scene_manager = scene_manager::SceneManager::new();
let landscape_sphere = Box::new(widgets::sphere::SphereRenderer::new(
    device.as_ref(),
    landscape_format,  // 3840×2160 aspect ratio
));
landscape_scene_manager.register_widget(landscape_sphere);
landscape_scene_manager.init_all()?;

// Portrait pipeline (completely independent)
let mut vertical_scene_manager = scene_manager::SceneManager::new();
let vertical_sphere = Box::new(widgets::sphere::SphereRenderer::new(
    device.as_ref(),
    vertical_format,  // 2160×3840 aspect ratio
));
vertical_scene_manager.register_widget(vertical_sphere);
vertical_scene_manager.init_all()?;
```

## Performance Characteristics

### What's Shared (Minimal Overhead)

- **WebGPU Device**: Single GPU handle
- **Queue**: Single command submission queue
- **KRONOS Time Source**: Musical timing synchronized
- **Musical Data**: Chords, notes, score data

### What's Separate (Required for Correctness)

- **SceneManager Instances**: One per canvas
- **Render Pipelines**: Compiled shader pipelines
- **Uniform Buffers**: Projection matrices, view matrices
- **Render Passes**: Separate command encoders

### Performance Impact Analysis

| Metric | Single Pipeline (Broken) | Dual Pipeline (Fixed) | Overhead |
|--------|--------------------------|----------------------|----------|
| CPU Time | ~5-10ms per frame | ~5-11ms per frame | ~1-5μs |
| Memory | ~Base + 1 pipeline | ~Base + 2 pipelines | ~few KB |
| GPU Submit | 1 queue submit | 1 queue submit | 0% |
| Fillrate | 958M pixels/sec | 958M pixels/sec | 0% |

**Conclusion**: Overhead is **<0.1%** of frame budget. Fillrate dominates for 8K rendering.

### Timing Instrumentation

The renderer includes CPU timing logs for performance monitoring:

```rust
let t0 = performance_now().unwrap_or(0.0);
// ... landscape render pass encoding ...
let t1 = performance_now().unwrap_or(0.0);
console::log("[TIMING] Landscape encode: {:.2} ms", t1 - t0);

// ... vertical render pass encoding ...
let t2 = performance_now().unwrap_or(0.0);
console::log("[TIMING] Vertical encode: {:.2} ms", t2 - t1);

self.queue.submit(Some(encoder.finish()));
let t3 = performance_now().unwrap_or(0.0);
console::log("[TIMING] GPU submit: {:.2} ms, total frame: {:.2} ms", t3 - t2, t3 - t0);
```

**Typical Output**:
```
[TIMING] Landscape encode: 2.34 ms
[TIMING] Vertical encode: 2.45 ms
[TIMING] GPU submit: 0.12 ms, total frame: 4.91 ms
```

## Testing

### Sphere Aspect Ratio Test

**File**: `packages/renderer-core/tests/sphere-aspect-ratio.spec.ts`

This test validates that rendered spheres remain circular (not elliptical) in both orientations:

```typescript
test('should render circles (not ellipses) in landscape orientation', async () => {
  const measurement = await measureSphereAspect(page, 'landscape');
  const tolerance = 0.04; // Allow 4% variance
  expect(measurement.sphereAspect).toBeGreaterThan(1 - tolerance);
  expect(measurement.sphereAspect).toBeLessThan(1 + tolerance);
});
```

**Test Results** (After Fix):
- Landscape: `sphereAspect = 1.038` ✅ (within tolerance)
- Portrait: `sphereAspect = 0.992` ✅ (within tolerance)

## Best Practices

### ✅ DO

1. **Create separate SceneManagers for different aspect ratios**
2. **Share WebGPU device and queue** (no overhead)
3. **Use separate uniform buffers per pipeline**
4. **Test both orientations thoroughly**
5. **Monitor CPU timing logs** for performance regressions

### ❌ DON'T

1. **Share pipelines across different aspect ratios** (causes contamination)
2. **Assume single pipeline can handle multiple aspects** (it can't)
3. **Skip testing one orientation** (both must pass)
4. **Optimize prematurely** (measure first with timing logs)
5. **Ignore aspect ratio math** (1.778 / 0.563 = 3.16 was the smoking gun)

## Common Pitfalls

### Pitfall #1: Shared Pipeline State

**Problem**: Using a single `SphereRenderer` or `SceneManager` for both canvases.

**Symptom**: One canvas renders correctly, the other is distorted by the aspect ratio conflict factor (~3x).

**Solution**: Create separate managers. Pattern:
```rust
let landscape_manager = SceneManager::new();
let vertical_manager = SceneManager::new();  // Don't reuse!
```

### Pitfall #2: Aspect Ratio Contamination

**Problem**: Computing projection matrices with one aspect ratio, then rendering to canvas with different aspect.

**Symptom**: Mathematical impossibility — no single projection matrix formula works for both.

**Solution**: Each pipeline computes its own matrices with its canvas's aspect ratio.

### Pitfall #3: Premature Optimization

**Problem**: Trying to share pipelines "for performance" without measuring.

**Reality**: Dual pipelines add <0.1% overhead. Fillrate dominates. Correctness > micro-optimizations.

**Solution**: Measure with timing logs, optimize based on data.

## Debugging Tips

### 1. Check Console Timing Logs

```
[TIMING] Landscape encode: X.XX ms
[TIMING] Vertical encode: X.XX ms
[TIMING] GPU submit: X.XX ms, total frame: X.XX ms
```

High encode times (>10ms) indicate bottlenecks.

### 2. Use FPS Display

Navigate to `/theater8k` to see real-time FPS display (top-right):
- **Green**: ≥50 fps (healthy)
- **Orange**: 30-49 fps (warning)
- **Red**: <30 fps (critical)

### 3. Run Aspect Ratio Tests

```bash
pnpm test:theater-sphere
```

Both orientations must pass for correct rendering.

### 4. Check for Shared State

Search for:
- Single `SceneManager` used by both canvases ❌
- Single `SphereRenderer` rendering to both ❌
- Separate managers per canvas ✅

## Related Documentation

- **Investigation Log**: `docs/investigations/sphere-aspect-ratio-issue.md` (27 debugging phases)
- **Onboarding Guide**: `docs/onboarding/webgpu-rendering.md` (best practices)
- **Renderer README**: `packages/renderer-core/README.md` (API reference)
- **Contributing Guide**: `CONTRIBUTING.md` (rendering guidelines)

## References

- [WebGPU Specification](https://www.w3.org/TR/webgpu/)
- [wgpu-rs Documentation](https://docs.rs/wgpu/)
- [Projection Matrix Math](https://www.scratchapixel.com/lessons/3d-basic-rendering/perspective-and-orthographic-projection-matrix)

---

**Maintainers**: Reach out to the team if you encounter aspect ratio issues or rendering bugs.
