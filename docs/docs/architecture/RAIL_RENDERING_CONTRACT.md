# Rail Rendering Contract (v1.0)

**Status:** Active  
**Enforcement:** Mandatory for all rail renderers  
**Violation Consequence:** Immediate FPS drop, compositor thrash, Layerize spikes

---

## Purpose

This contract defines the **inviolable rules** for rail rendering during playback. All rail renderers MUST comply to achieve stable 60 FPS and prevent compositor pressure.

**Inspired by:** Ableton Live, Logic Pro X rendering architecture

---

## Scope

**Applies during:** `__PERFORMANCE_MODE === true` (playback active)

**Applies to:**
- All rail renderers in `src/utils/novaxe-figma/`
- All rail components in `src/components/NVX1/`
- Any component that renders during playback

**Does NOT apply:**
- UI components outside playback path
- Diagnostic components (gated by `shouldRenderDiagnostics()`)
- Interaction layers (separate from render layers)

---

## RULE 1: Single Transform Surface

**Requirement:** Only ONE parent element moves per rail. All children are paint-only (static transforms).

**What this means:**
- One parent element owns the transform (e.g., `translateX(beat * beatWidth)`)
- All child elements have static transforms (or no transforms)
- No nested transforms during playback

**Violations:**
- Multiple elements updating transforms simultaneously
- Children with independent transforms
- Nested transform contexts

**Example (CORRECT):**
```typescript
// Parent moves, children static
parent.style.transform = `translateX(${beat * beatWidth}px)`;
child1.style.transform = 'translate3d(0, 0, 0)'; // Static
child2.style.transform = 'translate3d(0, 0, 0)'; // Static
```

**Example (WRONG):**
```typescript
// Multiple elements moving independently
parent.style.transform = `translateX(${beat * beatWidth}px)`;
child1.style.transform = `translateX(${someOtherValue}px)`; // Violation
```

---

## RULE 2: Zero Layout Participation

**Requirement:** No flex/grid layout calculations, no intrinsic sizing, no position: fixed/sticky interacting with transforms, no `contain: layout`.

**What this means:**
- Rails must be pre-laid-out before playback starts
- No CSS layout properties that trigger recalculation
- No `contain: layout` or `contain: layout style` (use only `will-change: transform`)
- No `position: fixed` or `position: sticky` descendants of transformed rails

**Violations:**
- `contain: layout style` (causes 4.7s Layerize spikes)
- Flex/grid layout during playback
- Position fixed/sticky inside transformed containers
- Intrinsic sizing calculations

**Example (CORRECT):**
```css
.rail {
  will-change: transform;
  transform: translate3d(0, 0, 0);
  /* No contain: layout */
}
```

**Example (WRONG):**
```css
.rail {
  will-change: transform;
  contain: layout style; /* Violation - causes Layerize */
}
```

---

## RULE 3: Static DOM Shape

**Requirement:** No mount/unmount during playback, no className toggles, no conditional rendering, only transform updates.

**What this means:**
- DOM structure is fixed during playback
- No React components mounting/unmounting
- No className changes
- No conditional rendering (`{condition && <Component />}`)
- Only `element.style.transform` updates allowed

**Violations:**
- Mounting/unmounting components during playback
- Toggling classes during playback
- Conditional rendering based on playback state
- Creating/destroying DOM elements

**Example (CORRECT):**
```typescript
// Pre-render all elements, only update transforms
elements.forEach(element => {
  element.style.transform = `translateX(${x}px)`;
});
```

**Example (WRONG):**
```typescript
// Conditional rendering during playback
{isPlaying && <NewComponent />} // Violation
```

---

## RULE 4: Time Flows One Way

**Requirement:** Clock → CSS var → transform (or direct transform). No React state updates in playback path, no useEffect firing on tick, no "helpful" effects.

**What this means:**
- Time authority (KhronosEngine) is the single source of truth
- Rails read time directly, not through React state
- No `useState` updates during playback
- No `useEffect` dependencies on playback state
- No React re-renders triggered by time updates

**Violations:**
- React state updates in 60Hz hot path
- useEffect hooks firing on every tick
- React context updates during playback
- Props changes triggering re-renders

**Example (CORRECT):**
```typescript
// Direct transform update, no React
rafLoop() {
  const beat = getPerformanceEngine().timeCursor.currentBeat;
  element.style.transform = `translateX(${beat * beatWidth}px)`;
}
```

**Example (WRONG):**
```typescript
// React state in hot path
useEffect(() => {
  KhronosBus.onTick((tick) => {
    setCurrentBeat(tick.beat); // Violation - React re-render
  });
}, []);
```

---

## RULE 5: No Layout Reads

**Requirement:** No getBoundingClientRect, no clientWidth/offsetTop reads, no style reads after writes, no DOM queries per tick.

**What this means:**
- All layout information must be cached before playback
- No synchronous layout reads during playback
- No style reads that trigger layout recalculation
- No DOM queries (querySelector, getElementById) in hot path

**Violations:**
- `getBoundingClientRect()` during playback
- `clientWidth`, `offsetTop`, `offsetLeft` reads
- Reading computed styles after writing
- DOM queries in RAF loop

**Example (CORRECT):**
```typescript
// Cache layout before playback
const beatWidth = element.clientWidth / beatsPerMeasure;
// During playback, only use cached value
element.style.transform = `translateX(${beat * beatWidth}px)`;
```

**Example (WRONG):**
```typescript
// Layout read in hot path
rafLoop() {
  const width = element.clientWidth; // Violation - layout read
  element.style.transform = `translateX(${beat * width}px)`;
}
```

---

## Enforcement

### Pre-Commit Checks
- All rail renderers must pass audit checklist
- CI must verify contract compliance
- Violations cause immediate FPS drop

### Audit Checklist
See `docs/architecture/RAIL_AUDIT_CHECKLIST.md` for detailed per-rail audit questions.

### Violation Consequences
- Immediate FPS regression
- Compositor thrash (Layerize spikes)
- Nondeterministic playback behavior
- Audio-visual desync

---

## Historical Context

**60 FPS State (f3e84932b4):**
- Used only `will-change: transform`
- No `contain: layout style`
- Single transform surface per rail
- Zero layout participation

**Regression (3f956927fd):**
- Added `contain: layout style` to fix "82ms style recalc"
- Caused 4.7s Layerize spikes (60.8% frame budget)
- This contract prevents future regressions

---

## References

- `docs/forensic/LAYERIZE_TOP_FINDINGS.md` - Investigation findings
- `docs/forensic/LAYERIZE_SUSPECTS_TOP_100.md` - Full suspect list
- `src/utils/novaxe-figma/performanceEngine.ts` - DOM_60FPS_LOCKED contract
- Historical commits: `f3e84932b4`, `418badf582`, `1efb48a1e2`

---

**Contract Version:** 1.0  
**Last Updated:** 2025-12-22  
**Status:** Active

