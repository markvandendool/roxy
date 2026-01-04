# Rail Audit Checklist

**Purpose:** Systematic audit of all rail renderers against Rail Rendering Contract  
**Usage:** Answer all questions for each rail to determine compliance status  
**Output:** `docs/forensic/RAIL_AUDIT_RESULTS.md`

---

## Audit Questions (Per Rail)

For each rail, answer these 8 questions:

### Q1: Does it mount/unmount during playback?
- **Check:** React component lifecycle, conditional rendering, DOM creation/destruction
- **Expected:** NO - DOM structure must be static during playback
- **Violation:** Component mounts/unmounts based on `isPlaying` or other playback state

### Q2: Does it own its own transform?
- **Check:** Single parent element with transform, children are static
- **Expected:** YES - One parent element owns the transform
- **Violation:** Multiple elements updating transforms, or no clear transform owner

### Q3: Does it contain fixed/sticky descendants?
- **Check:** Any `position: fixed` or `position: sticky` elements inside the rail
- **Expected:** NO - Fixed/sticky inside transformed containers causes compositor issues
- **Violation:** Fixed/sticky elements are descendants of transformed rail

### Q4: Does React re-render it during playback?
- **Check:** React DevTools Profiler, useState/useEffect hooks, props changes
- **Expected:** NO - Zero React re-renders during playback
- **Violation:** React re-renders triggered by time updates, state changes, or effects

### Q5: Does it use contain: layout/style?
- **Check:** CSS `contain: layout` or `contain: layout style` properties
- **Expected:** NO - Only `will-change: transform` allowed
- **Violation:** `contain: layout style` causes 4.7s Layerize spikes

### Q6: Does it read layout properties (getBoundingClientRect, clientWidth)?
- **Check:** Calls to `getBoundingClientRect()`, `clientWidth`, `offsetTop`, etc.
- **Expected:** NO - All layout reads must be cached before playback
- **Violation:** Layout reads in RAF loop or during playback

### Q7: Does it update className during playback?
- **Check:** `element.className` or `element.classList` updates
- **Expected:** NO - No className toggles during playback
- **Violation:** Classes changed based on playback state or time

### Q8: Does it conditionally render children during playback?
- **Check:** Conditional rendering (`{condition && <Component />}`)
- **Expected:** NO - All children must be pre-rendered
- **Violation:** Children mount/unmount based on conditions

---

## Rails to Audit

### Core Renderers (src/utils/novaxe-figma/)

1. **PlayheadRenderer**
   - File: `src/utils/novaxe-figma/performanceEngine.ts`
   - Class: `PlayheadRenderer`
   - Purpose: Visual playhead indicator

2. **BassLineRenderer**
   - File: `src/utils/novaxe-figma/layerRenderers.ts`
   - Class: `BassLineRenderer`
   - Purpose: Bass note rendering

3. **ChordLayerRenderer**
   - File: `src/utils/novaxe-figma/layerRenderers.ts`
   - Class: `ChordLayerRenderer`
   - Purpose: Chord block rendering

4. **ChordDiagramRenderer**
   - File: `src/utils/novaxe-figma/layerRenderers.ts`
   - Class: `ChordDiagramRenderer`
   - Purpose: Chord diagram rendering

5. **All other renderers in layerRenderers.ts**
   - File: `src/utils/novaxe-figma/layerRenderers.ts`
   - Check: All classes implementing `RenderableElement`

### React Components (src/components/)

6. **OrchestraRail**
   - File: `src/components/NVX1/OrchestraRail/OrchestraRail.tsx`
   - Component: `OrchestraRailComponent`
   - Purpose: Full MusicXML rendering with OSMD

7. **DrumsRail**
   - File: `src/components/NVX1/DrumsRail/DrumsRail.tsx`
   - Component: `DrumsRailComponent`
   - Purpose: DAW-style drum/percussion grid

8. **BridgeLayer**
   - File: `src/components/novaxe-figma/BridgeLayer.tsx`
   - Component: `BridgeLayer`
   - Purpose: Right-hand events bridge layer

---

## Audit Process

### Step 1: Read Component Code
- Read the full component/renderer file
- Identify all DOM operations
- Identify all React hooks and state
- Identify all CSS properties

### Step 2: Check During Playback
- Set `__PERFORMANCE_MODE = true` mentally
- Trace code paths that execute during playback
- Identify any operations that violate contract

### Step 3: Answer Questions
- Answer each of the 8 questions
- Provide evidence (line numbers, code snippets)
- Mark as PASS/FAIL/NEEDS_REVIEW

### Step 4: Document Results
- Create entry in `RAIL_AUDIT_RESULTS.md`
- Include compliance status
- List violations (if any)
- Recommend fixes (if needed)

---

## Compliance Status

### PASS
- All 8 questions answered NO (for negative questions) or YES (for positive questions)
- Rail fully compliant with contract
- No violations found

### FAIL
- One or more questions answered incorrectly
- Rail violates contract
- Requires fixes before production

### NEEDS_REVIEW
- Ambiguous answers or unclear code paths
- Requires deeper investigation
- May need code refactoring to clarify

---

## Example Audit Entry

```markdown
## PlayheadRenderer

**File:** `src/utils/novaxe-figma/performanceEngine.ts`  
**Class:** `PlayheadRenderer`  
**Status:** ✅ PASS

### Answers:
1. **Mount/unmount during playback?** NO - Element created once, never destroyed
2. **Owns its own transform?** YES - Single parent element with transform
3. **Contains fixed/sticky descendants?** NO - No fixed/sticky elements
4. **React re-renders during playback?** NO - Not a React component
5. **Uses contain: layout/style?** NO - Only `will-change: transform` (fixed in Phase 0)
6. **Reads layout properties?** NO - No layout reads in update()
7. **Updates className during playback?** NO - No className changes
8. **Conditionally renders children?** NO - Static DOM structure

### Evidence:
- Line 934: `will-change: transform` (no contain)
- Line 977: `element.style.transform` (only DOM write)
- No React hooks or state

### Verdict: ✅ COMPLIANT
```

---

## Next Steps After Audit

1. **If PASS:** Document compliance, no action needed
2. **If FAIL:** Create fix plan, prioritize by impact
3. **If NEEDS_REVIEW:** Deeper investigation, may require code refactoring

---

**Checklist Version:** 1.0  
**Last Updated:** 2025-12-22

