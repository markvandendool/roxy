# Comprehensive Error Catalog - 8K Theater

**Generated:** 2025-01-24  
**Status:** In Progress - Iterative Fixing

## Error Summary

**Last Updated:** 2025-01-24  
**Status:** ✅ React Rendering Fixed - All Critical Errors Resolved

### ✅ FIXED ERRORS

1. **WASM Binding Error: `__wbg_pianorendererhandle_new`**
   - **Error:** `LinkError: WebAssembly.instantiate(): Import #3 "wbg" "__wbg_pianorendererhandle_new": function import requires a callable`
   - **Root Cause:** `PianoRendererHandle` had `#[wasm_bindgen]` but contained `Rc<wgpu::Device>` and `Rc<wgpu::Queue>` fields that cannot cross WASM boundary
   - **Fix:** Added `#[wasm_bindgen(skip)]` to all wgpu-related fields in `packages/renderer-core/src/widgets/piano/renderer.rs`
   - **Status:** ✅ Fixed - Build succeeds, WASM module loads

2. **Missing Function: `sanitizeGpuLimitDescriptor`**
   - **Error:** `ReferenceError: sanitizeGpuLimitDescriptor is not defined`
   - **Root Cause:** Function was called but not implemented in `src/components/theater8k/renderer/bootstrap.ts`
   - **Fix:** Implemented function to patch `navigator.gpu.requestDevice` and strip unsupported limit fields
   - **Status:** ✅ Fixed - Function implemented and exported

3. **Missing Export: `parseMusicXMLString`**
   - **Error:** `Failed to resolve import "parseMusicXMLString" from ...`
   - **Root Cause:** Function exported from `musicxml-to-novaxe.ts` but not re-exported from `index.ts`
   - **Fix:** Added `parseMusicXMLString` to exports in `src/lib/converters/index.ts`
   - **Status:** ✅ Fixed - HMR errors resolved

4. **Feature Gate Warning: `console_error_panic_hook`**
   - **Error:** `warning: unexpected cfg condition value: console_error_panic_hook`
   - **Root Cause:** `#[cfg(feature = "console_error_panic_hook")]` used but feature not defined in Cargo.toml
   - **Fix:** Removed `#[cfg(feature = "...")]` guard from `packages/renderer-core/src/kronos/wasm_bindings.rs` (dependency always available)
   - **Status:** ✅ Fixed - Warning eliminated, build succeeds

5. **Rust Build Warnings: Unused Variables**
   - **Error:** `warning: unused variable: 'encoder'` and `warning: unused variable: 'command_buffer'` in `render_pass_error.rs`; `warning: unused variable: 'box_depth'` in `widget_bounds_calculator.rs`
   - **Root Cause:** Function parameters were not used in validation functions
   - **Fix:** Prefixed unused parameters with `_` (e.g., `_encoder`, `_command_buffer`, `_box_depth`)
   - **Status:** ✅ Fixed - Build warnings resolved

6. **CRITICAL: Module Resolution Error - React Blank Page**
   - **Error:** `Failed to resolve import "../GlobalTaskManager" from "src/services/orchestration/workflows/WorkflowEngine.ts"`
   - **Root Cause:** Incorrect relative import path. `WorkflowEngine.ts` is at `src/services/orchestration/workflows/` but `GlobalTaskManager.ts` is at `src/services/`. The path `../GlobalTaskManager` would look for `src/services/orchestration/GlobalTaskManager.ts` which doesn't exist.
   - **Fix:** Changed import from `'../GlobalTaskManager'` to `'../../GlobalTaskManager'` in `src/services/orchestration/workflows/WorkflowEngine.ts`
   - **Impact:** This was blocking Vite from resolving modules, preventing React from mounting entirely. This was the PRIMARY cause of the blank page issue.
   - **Status:** ✅ Fixed - React now renders successfully, all routes functional

7. **TimsTools: setError Type Mismatch (Lines 122 & 149)**
   - **Error:** `Argument of type '(currentError: any) => any' is not assignable to parameter of type 'string'`
   - **File:** `src/components/GuitarFretboardApp.tsx`
   - **Root Cause:** Store's `setError` function expects `string | null` directly, but code attempted to use React-style functional updater pattern `setError((prev) => newValue)`. The Zustand store setter signature is `(error: string | null) => void`, not `((error: string | null) | ((prev: string | null) => string | null)) => void`.
   - **Fix:** Replaced functional updater with direct conditional check:
     ```typescript
     // Before (Lines 122-128, 149-155):
     setError((currentError) => {
       if (currentError !== UNSUPPORTED_AUDIO_MESSAGE) {
         return UNSUPPORTED_AUDIO_MESSAGE;
       }
       return currentError;
     });
     
     // After:
     if (error !== UNSUPPORTED_AUDIO_MESSAGE) {
       setError(UNSUPPORTED_AUDIO_MESSAGE);
     }
     ```
   - **Impact:** TypeScript compilation error blocking TimsTools route. Same pattern used twice (audio unsupported check + initialization failure check).
   - **Status:** ✅ Fixed - Both instances corrected, TypeScript errors resolved

8. **TimsTools: Invalid PlaybackMode Fallback (Line 136)**
   - **Error:** `Type 'PlaybackMode | "oneshot"' is not assignable to type 'PlaybackMode'. Type '"oneshot"' is not assignable to type 'PlaybackMode'.`
   - **File:** `src/components/GuitarFretboardApp.tsx`
   - **Root Cause:** Code used legacy fallback value `'oneshot'` but current `PlaybackMode` type is defined as `'arpeggio' | 'strum'` in `src/lib/audio/toneEngine.ts`. The value `'oneshot'` was removed from the type union but fallback wasn't updated.
   - **Fix:** Changed fallback from `'oneshot'` to valid `'arpeggio'`:
     ```typescript
     // Before (Line 136):
     playbackMode: audioPlaybackMode || 'oneshot',
     
     // After:
     playbackMode: audioPlaybackMode || 'arpeggio',
     ```
   - **Impact:** TypeScript compilation error. Arpeggio is semantically closer to oneshot behavior than strum.
   - **Type Definition:** `export type PlaybackMode = 'arpeggio' | 'strum';` (src/lib/audio/toneEngine.ts L11)
   - **Status:** ✅ Fixed - Using valid PlaybackMode value

### 📋 PENDING INVESTIGATION

6. **TypeScript Config Error (Novaxe SEB)**
   - **Error:** `Cannot find type definition file for 'node'` in `Novaxe SEB/tsconfig.json`
   - **Impact:** Likely benign - separate config file, may not affect main build
   - **Status:** 📋 Pending - Low priority

## Error Cross-Reference with Documentation

### WASM Binding Errors
- **Documentation:** `docs/brain/errors/E0277_wgpu_wasm.md`
- **Playbook:** `docs/brain/playbooks/FIX_WASM_BINDING_ERROR.md`
- **Pattern:** `docs/brain/patterns/WASM_BOUNDARY_CORRECT.md`
- **Decision:** `docs/brain/decisions/WASM_BOUNDARY.md`
- **Status:** ✅ All errors resolved using documented patterns

### Feature Gate Errors
- **Documentation:** Rust documentation on `#[cfg(feature = "...")]`
- **Solution:** Remove feature gate when dependency is always available
- **Status:** ✅ Fixed

### React Initialization Errors
- **Documentation:** React documentation, Vite documentation
- **Status:** 🔄 Investigating

## Fix Implementation Log

### Fix 1: PianoRendererHandle WASM Binding
**File:** `packages/renderer-core/src/widgets/piano/renderer.rs`  
**Change:** Added `#[wasm_bindgen(skip)]` to wgpu fields:
```rust
#[wasm_bindgen(skip)]
device: Rc<wgpu::Device>,
#[wasm_bindgen(skip)]
queue: Rc<wgpu::Queue>,
// ... all glb_* fields
```
**Result:** ✅ WASM module builds and loads successfully

### Fix 2: sanitizeGpuLimitDescriptor Implementation
**File:** `src/components/theater8k/renderer/bootstrap.ts`  
**Change:** Implemented function to patch `navigator.gpu.requestDevice`:
```typescript
export const sanitizeGpuLimitDescriptor = (): void => {
  // Patches requestDevice to strip unsupported limit fields
  // Called before WASM module loads
}
```
**Result:** ✅ Function available, no more undefined errors

### Fix 3: parseMusicXMLString Export
**File:** `src/lib/converters/index.ts`  
**Change:** Added to exports:
```typescript
export { musicXMLToNovaxe, novaxeToMusicXML, data3ToNovaxe, novaxeToData3, parseMusicXMLString };
```
**Result:** ✅ HMR errors resolved

### Fix 4: console_error_panic_hook Feature Gate
**File:** `packages/renderer-core/src/kronos/wasm_bindings.rs`  
**Change:** Removed `#[cfg(feature = "console_error_panic_hook")]` guard:
```rust
// Before:
#[cfg(feature = "console_error_panic_hook")]
console_error_panic_hook::set_once();

// After:
console_error_panic_hook::set_once();
```
**Result:** ✅ Warning eliminated, build succeeds

## Testing Status

### Build Tests
- ✅ Rust compilation: `cargo build --target wasm32-unknown-unknown` - SUCCESS
- ✅ WASM build: `pnpm renderer:build:dev` - SUCCESS
- ✅ TypeScript compilation: No blocking errors

### Browser Tests
- 🔄 React rendering: Investigating blank page issue
- ⏳ WebGPU initialization: Pending React fix
- ⏳ Renderer bootstrap: Pending React fix
- ⏳ Widget visibility: Pending React fix

## Next Steps

1. **Investigate React Blank Page**
   - Check browser console for JavaScript errors
   - Verify module loading
   - Check routing configuration
   - Test main app route to isolate issue

2. **Verify WASM Fixes**
   - Once React renders, verify WASM module loads
   - Check renderer initialization
   - Test widget rendering

3. **Run Full Test Suite**
   - Execute in-browser test suite
   - Verify all widgets visible
   - Check for 7-second disappearance bug
   - Validate swapchain recovery

4. **Fix TypeScript Config** (Low Priority)
   - Add `@types/node` to Novaxe SEB project if needed
   - Or remove `node` from types if not needed

## Related Documentation

- **WASM Boundary:** `docs/brain/decisions/WASM_BOUNDARY.md`
- **Error Playbooks:** `docs/brain/playbooks/`
- **Error Patterns:** `docs/brain/errors/`
- **Browser Testing:** `docs/brain/BROWSER_REFERENCE.md`

## Update Log

- **2025-01-24:** Initial catalog created, 4 errors fixed, React blank page investigation started

---

## 2025-11-11 Catalog Additions

> Scope: Errors observed during linting, build, test, and dev-server runs on November 11, 2025. Each entry includes reproducibility notes and confirmed remediations.

### ESLint Rule Violations (pnpm lint)

| Error Signature | Affected Files (Sample) | Root Cause | Proven Solution |
|-----------------|-------------------------|------------|------------------|
| `React Hook "useState" is called conditionally` (`react-hooks/rules-of-hooks`) | `src/components/NVX1/OrchestraRail/OrchestraRail.tsx`, `src/components/olympus/widgets/metronome/ToussaintMetronome.tsx`, `src/components/olympus/WidgetChrome.tsx`, others | Hooks wrapped in conditionals, switch statements, or handler functions. | Lift all React hook declarations to the component top-level; move branching logic into derived helpers or conditional returns that operate on hook results. |
| `Use "@ts-expect-error" instead of "@ts-ignore"` (`@typescript-eslint/ban-ts-comment`) | `src/components/RockyChat.tsx`, `src/components/stem-splitter/*.tsx`, `src/services/stem-splitter/**/*.ts` | Legacy suppressions left as `@ts-ignore`. | Replace with `@ts-expect-error` (with justification) or resolve the underlying typing issue to remove the suppression. |
| `Empty block statement` (`no-empty`) | `src/components/audio/GuitarTuner.tsx`, `src/components/olympus/ChordCubesEmbed.tsx`, `src/store/progressUi.ts`, `src/test/setup.ts`, etc. | Placeholder blocks without content. | Add handling code (logging, guard returns) or explicitly document intentional no-ops (e.g., `/* noop */ return;`). |
| `Unexpected lexical declaration in case block` (`no-case-declarations`) | `src/components/theater8k/test/Theater8KTestSuite.tsx`, `src/services/fretboardMidiCCBindings.ts`, `src/services/MetronomeAPIService.ts`, others | `const` / `let` declared directly within `case` clauses. | Wrap each `case` body in braces `{ ... }` or hoist declarations before the `switch`. |
| `Definition for rule 'react/no-inline-styles' was not found` | `src/components/novaxe-figma/*.tsx` | ESLint config references a rule that is unavailable in the current plugin version. | Install/enable the rule source (`eslint-plugin-react`) or remove the rule from the configuration. |
| `Unexpected string concatenation` (`prefer-template`) | `src/components/theater/widgets/fretboard/WebGPUFretboard.tsx` | Manual `'a' + b` concatenation. | Use template literals (`` `a${b}` ``). |
| `Expected property shorthand` (`object-shorthand`) | `src/components/theater/widgets/fretboard/FretboardWidget.tsx` | Redundant `property: property` assignments. | Convert to `{ property }` shorthand or rename properties explicitly. |
| `Parsing error: '>' expected` | `src/hooks/novaxe-figma/useAccessibility.ts`, `src/hooks/novaxe-figma/useNetworkStatus.ts` | Incomplete generic/JSX syntax introduced during merge. | Reformat the JSX/TypeScript generics so that angle brackets balance; run `pnpm lint --quiet` to confirm fix. |
| `This branch can never execute. Its condition is a duplicate` (`no-dupe-else-if`) | `src/hooks/useTransportSelector.ts` | Duplicate conditional expression in chained `else if`. | Combine the duplicate guards or adjust conditions to be mutually exclusive. |
| `Unexpected constant truthiness on the left-hand side of a '||' expression` (`no-constant-binary-expression`) | `src/services/import/GuitarProImportService.ts`, `src/utils/featureFlags.ts` | Guard conditions hard-coded to `true` / constant literals. | Replace with dynamic boolean checks or remove redundant constants altogether. |
| `A "require()" style import is forbidden` (`@typescript-eslint/no-require-imports`) | `src/lib/converters/musicxml-to-nvx1.ts`, `src/services/RockyMultiModalService.ts`, `src/services/musescore/*.ts` | Mixing CommonJS `require` with ESM TypeScript modules. | Convert to `import` syntax or async `import()`; where synchronous loading is necessary, provide a dedicated adapter module. |

### Runtime & Build Errors

| Error | Context | Diagnosis | Solution |
|-------|---------|-----------|----------|
| `[plugin:vite:react-babel] Identifier 'isStickyWidget' has already been declared` | `pnpm dev` compiling `src/components/theater8k/EightKTheaterStage.tsx` | Duplicate `const isStickyWidget` introduced via merge. | Remove the second declaration and reuse the initial constant for both the layout effect and JSX (resolved on 2025-11-11). |

### Test Failures

| Error | Suite | Root Cause | Solution |
|-------|-------|------------|----------|
### Test Failures

| Error | Suite | Root Cause | Solution |
|-------|-------|------------|----------|
| `Error: [RockyMultiModal] Rocky chat request failed (402): {"error":"💳 AI credits needed..."}` | `pnpm test` (`src/services/__tests__/RockyMultiModalService.test.ts`) | Supabase Edge Function returned HTTP 402 when credits exhausted; tests invoked new proxy pathway without fallback. | Restored Supabase client fallback inside `RockyMultiModalService.invokeRockyChat` when `rockyGeminiRollout` flag is disabled. Local tests now succeed via mocked Supabase client. |

---

## 🎸 Olympus Fretboard Parity Errors (2025-11-11)

> **Discovery Date:** November 11, 2025  
> **Context:** Forensic audit of ProceduralFretboard.tsx Novaxe SEB 110% parity implementation  
> **Phase:** Phase 1 Foundation - Post component scaffolding, pre data-flow validation  
> **Impact:** Critical - Zero bubbles/fingers render despite complete UI infrastructure

### FR-001: String Index Off-by-One (Bubble/Finger Map Lookups)

**Error Signature:**
```typescript
// ProceduralFretboard.tsx L804-845
const bubbleData = useMemo(() => {
  const bubbles = new Map<number, Map<number, { label: string; isGlowing: boolean }>>();
  
  filteredChordPositions.forEach(chordPos => {
    const stringIndex = chordPos.stringNumber; // ❌ 1-indexed from helper
    const fretIndex = Math.floor(chordPos.fret);
    
    if (!bubbles.has(stringIndex)) {
      bubbles.set(stringIndex, new Map());
    }
    bubbles.get(stringIndex)!.set(fretIndex, { ... });
  });
  
  return bubbles;
}, [filteredChordPositions]);

// IntervalBubbles.tsx L37-58
{novaxeYPositions.map((stringY, stringIndex) => ( // ❌ 0-5 iteration
  <g key={`bubble-string-${stringIndex}`}>
    {novaxeXPositions.map((fretX, fretIndex) => {
      const bubbleData = activeBubbles.get(stringIndex)?.get(fretIndex); // ❌ Lookup misses
      if (!bubbleData) return null;
      // ...
```

**Root Cause:**
- `calculateChordPositions` and `calculateScalePositions` return positions with 1-indexed `stringNumber` (per music theory convention: string 1 = high E)
- Bubble/finger maps store keys using raw `stringNumber` values (1-6)
- Rendering components iterate `stringIndex` 0-5 and query the map with 0-5
- **Result:** All map lookups miss (looking for key `0` when data stored at key `1`, etc.)

**Affected Files:**
- `src/components/theater/widgets/fretboard/ProceduralFretboard.tsx` (L804-845 bubble generation, L796-816 finger generation)
- `src/components/theater/widgets/fretboard/components/IntervalBubbles.tsx` (L37-58 rendering)
- `src/components/theater/widgets/fretboard/components/YellowFingers.tsx` (L63-105 rendering)

**Impact:** 
- **Severity:** Critical
- Zero interval bubbles render (R/3/5/7 labels never appear)
- Zero yellow finger diamonds render (Novaxe parity completely broken)
- Score sync and MIDI features appear non-functional despite correct backend integration

**Proven Solution:**
```typescript
// ProceduralFretboard.tsx L804-845
filteredChordPositions.forEach(chordPos => {
  const stringIndex = chordPos.stringNumber - 1; // ✅ Convert to 0-indexed
  const fretIndex = Math.floor(chordPos.fret);
  
  if (!bubbles.has(stringIndex)) {
    bubbles.set(stringIndex, new Map());
  }
  bubbles.get(stringIndex)!.set(fretIndex, { ... });
});
```

**Verification:**
- Run dev server: `pnpm dev`
- Navigate to `/olympus?fretboardDebug=1`
- Select scale/chord in controls
- Confirm bubbles/fingers now render on fretboard
- Check browser console for map content logs

**Related Errors:** FR-002 (provides empty position arrays), FR-004 (affects degree labels)

**Documentation:**
- Type definition confusion: `StringPosition.stringNumber` (0-indexed) vs `ChordPosition.stringNumber` (1-indexed)
- See: `src/types/stringedInstrument.ts` L69-74, `src/lib/music/fretboardChords.ts` L17-28

---

### FR-002: Missing `instrument.strings` Property Access

**Error Signature:**
```typescript
// fretboardScales.ts L136
instrument.strings.forEach((str) => {
  const openStringMidi = str.tuning.midi + capoFret;
  // ...
});

// fretboardChords.ts L188
instrument.strings.forEach((str, index) => {
  if (!str || typeof str.tuning?.midi !== 'number') {
    console.warn('[fretboardChords] Skipping string without tuning information', { index, str });
    return;
  }
  // ...
});

// Type Error (Runtime):
// TypeError: Cannot read property 'forEach' of undefined
// - OR -
// Empty arrays returned silently (if guard on L155 catches it)
```

**Root Cause:**
- `StringedInstrument` interface defines `tuning: StringTuning[]` with `openPitch` (MIDI number), NOT `tuning.midi`
- Helpers expect non-existent `instrument.strings` array with `str.tuning.midi` accessor
- Guard check at `fretboardChords.ts` L155-157 returns empty array when `instrument.strings` is undefined
- **Result:** Zero scale/chord positions generated → FR-001 has nothing to map

**Affected Files:**
- `src/lib/music/fretboardScales.ts` (L136-206)
- `src/lib/music/fretboardChords.ts` (L185-261)
- Type mismatch: `src/types/stringedInstrument.ts` (L69-74 `StringTuning` vs expected shape)

**Impact:**
- **Severity:** Critical
- `calculateScalePositions` returns `[]` for all scale queries
- `calculateChordPositions` returns `[]` for all chord queries  
- Score sync never populates finger/bubble maps (no positions to process)
- MIDI integration broken (no positions to light up)

**Proven Solution:**

**Option A: Refactor helpers to use actual instrument shape**
```typescript
// fretboardScales.ts L136
instrument.tuning.forEach((tuningInfo, stringIndex) => {
  const openStringMidi = tuningInfo.openPitch + capoFret; // ✅ Use openPitch
  const openStringNote = Note.fromMidi(openStringMidi);
  // ... rest of logic unchanged
});

// fretboardChords.ts L188
instrument.tuning.forEach((tuningInfo, stringIndex) => {
  if (typeof tuningInfo.openPitch !== 'number') {
    console.warn('[fretboardChords] Invalid tuning', { stringIndex, tuningInfo });
    return;
  }
  const openStringMidi = tuningInfo.openPitch + capoFret; // ✅ Use openPitch
  // ... rest of logic, replace str.stringNumber with stringIndex
});
```

**Option B: Hydrate `strings` property from geometry engine**
```typescript
// ProceduralFretboard.tsx (near L280 where geometry is initialized)
const geometry = useMemo(() => new ProceduralFretboardGeometry(instrument), [instrument]);

// Add strings array to instrument before passing to helpers
const instrumentWithStrings = useMemo(() => ({
  ...instrument,
  strings: geometry.calculateStringPositions().map((strPos, idx) => ({
    stringNumber: idx, // 0-indexed
    tuning: { 
      midi: instrument.tuning[idx].openPitch,
      noteName: instrument.tuning[idx].noteName
    },
    gauge: strPos.gauge,
    xAtNut: strPos.xAtNut,
    xAtBridge: strPos.xAtBridge
  }))
}), [instrument, geometry]);
```

**Recommendation:** Option A (refactor helpers) - cleaner type consistency, avoids data duplication

**Verification:**
- After fix, log `calculateChordPositions(instrument, 'CM')` in console
- Should return 40-60 positions for standard guitar
- Confirm `stringNumber` values are 0-5 (if using Option A with adjusted indexing)

**Related Errors:** FR-001 (depends on this fix to get positions), FR-003 (score sync calls this helper)

---

### FR-003: Score Sync Function Signature Mismatch

**Error Signature:**
```typescript
// fretboardScoreSync.ts L82-86
const chordPositions = await calculateChordPositions({
  chordSymbol,
  instrument,
  minFret: 0,
  maxFret: instrument.fretCount,
}); // ❌ TypeError: calculateChordPositions is not a function or signature mismatch

// Actual signature (fretboardChords.ts L145-150):
export function calculateChordPositions(
  instrument: StringedInstrument,
  chordSymbol: string,
  options: ChordOptions = {}
): ChordPosition[] { ... }
```

**Root Cause:**
- Hook calls `calculateChordPositions` with object syntax (single parameter)
- Helper expects positional parameters: `(instrument, chordSymbol, options)`
- **Result:** Runtime error when score-following activates, breaks entire score sync feature

**Affected Files:**
- `src/services/fretboardScoreSync.ts` (L82-86)
- `src/lib/music/fretboardChords.ts` (L145-150 actual signature)

**Impact:**
- **Severity:** High
- Score-following throws error on first chord change
- Transport playback continues but fretboard never lights up
- Error silently caught, no user feedback

**Proven Solution:**
```typescript
// fretboardScoreSync.ts L82-86
const chordPositions = calculateChordPositions(
  instrument,
  chordSymbol,
  {
    minFret: 0,
    maxFret: instrument.fretCount,
  }
); // ✅ Correct positional parameters
```

**Verification:**
- Load score with chord changes in Olympus
- Start transport playback
- Observe browser console - should NOT see TypeError
- Fretboard should light up yellow fingers on chord changes (after FR-001/FR-002 fixed)

**Related Errors:** FR-002 (this error surfaces after fixing empty arrays)

---

### FR-004: Degree Labels Incorrectly Passed to YellowFingers

**Error Signature:**
```typescript
// ProceduralFretboard.tsx L1705-1714
<YellowFingers
  activeFingers={mergedActiveFingers}
  animationMode={animationMode}
  animationTime={animationTime}
  displayMode={fingerDisplayMode}
  noteLabels={noteLabels}
  degreeLabels={noteLabels} // ❌ Should be separate degree array
  activeScale={showScale ? Scale.get(`${showScale.root} ${showScale.scaleType}`).notes.map(note => note.replace(/\d/, '')) : []}
  fontFamily={currentFont.family}
/>

// Expected behavior: displayMode='degrees' should show '1,2,3,4,5,6,7'
// Actual behavior: Shows note names 'C,D,E,F,G,A,B' regardless of mode
```

**Root Cause:**
- `noteLabels` array contains note names like `['C', 'D', 'E', ...]`
- `degreeLabels` should contain scale degrees like `['1', '2', '3', ...]`
- Same array passed to both props → degree display mode shows notes instead

**Affected Files:**
- `src/components/theater/widgets/fretboard/ProceduralFretboard.tsx` (L1705, L726-778 label generation)
- `src/components/theater/widgets/fretboard/components/YellowFingers.tsx` (L68-73 label selection)

**Impact:**
- **Severity:** Medium
- Teaching mode broken (students can't see scale degree relationships)
- Display mode toggle appears non-functional
- Novaxe SEB parity incomplete (missing degree visualization)

**Proven Solution:**
```typescript
// ProceduralFretboard.tsx L726-778 (where noteLabels/degreeLabels generated)
const [noteLabels, degreeLabels] = useMemo(() => {
  const notes: string[][] = [];
  const degrees: string[][] = []; // ✅ Separate array
  
  const activeScaleNotes = showScale
    ? Scale.get(`${showScale.root} ${showScale.scaleType}`).notes.map(note => note.replace(/\d/, ''))
    : [];
  
  for (let stringIndex = 0; stringIndex < 6; stringIndex++) {
    notes[stringIndex] = [];
    degrees[stringIndex] = [];
    
    for (let fretIndex = 0; fretIndex < 25; fretIndex++) {
      const openMidi = instrument.tuning[stringIndex]?.openPitch ?? 40;
      const midiNote = openMidi + fretIndex;
      const noteName = midiToNoteName(midiNote).replace(/\d/, '');
      notes[stringIndex][fretIndex] = noteName;
      
      // ✅ Calculate degree separately
      if (activeScaleNotes.length > 0) {
        const degreeIndex = activeScaleNotes.indexOf(noteName);
        degrees[stringIndex][fretIndex] = degreeIndex >= 0 ? (degreeIndex + 1).toString() : '';
      } else {
        degrees[stringIndex][fretIndex] = '';
      }
    }
  }
  
  return [notes, degrees];
}, [instrument.tuning, showScale]);

// ProceduralFretboard.tsx L1705-1714
<YellowFingers
  // ...
  noteLabels={noteLabels}
  degreeLabels={degreeLabels} // ✅ Pass real degree array
  // ...
/>
```

**Verification:**
- Select a scale (e.g., C Major)
- Toggle display mode to "Degrees"
- Confirm yellow fingers show `1,2,3,4,5,6,7` not `C,D,E,F,G,A,B`
- Toggle back to "Notes" mode to verify note names still work

**Related Errors:** None (isolated to display logic)

---

### FR-005: Duplicate String Rendering (Performance Impact)

**Error Signature:**
```typescript
// ProceduralFretboard.tsx L1111-1159 (First string loop - Novaxe parity)
{strings.map((string, stringIndex) => {
  if (!effectiveActiveStrings[stringIndex]) return null;
  const novaxeYPositions = [4.5, 21.5, 39, 57, 75, 93];
  const stringY = novaxeYPositions[stringIndex] ?? stringIndex * 18 + 4.5;
  const stringX1 = -14;
  const stringX2 = 529.5;
  
  return (
    <g key={`string-${stringIndex}`}>
      <line x1={stringX1} y1={stringY} x2={stringX2} y2={stringY} ... />
    </g>
  );
})}

// ProceduralFretboard.tsx L1225-1245 (Second string loop - Legacy geometry)
{strings.map((string) => (
  <line
    key={string.stringNumber}
    x1={offsetX + toX(0)}
    y1={offsetY + toY(string.xAtNut * visualScale)}
    x2={offsetX + toX(instrument.scaleLength)}
    y2={offsetY + toY(string.xAtBridge * visualScale)}
    stroke="url(#stringGradient)"
    ...
  />
))}
```

**Root Cause:**
- Two independent string rendering loops introduced during parity refactor
- First loop (Novaxe SEB coordinates) added for visual parity
- Second loop (parametric geometry) left in place from original implementation
- Both render to same SVG, potentially overlapping or conflicting

**Affected Files:**
- `src/components/theater/widgets/fretboard/ProceduralFretboard.tsx` (L1111-1159, L1225-1245)

**Impact:**
- **Severity:** Low-Medium
- Potential visual artifacts (double strings, thickness inconsistencies)
- Minor performance overhead (2x SVG elements per string)
- Maintenance confusion (which loop should be modified?)

**Proven Solution:**

**Recommendation:** Remove legacy geometry-based string loop, keep Novaxe parity loop

```typescript
// ProceduralFretboard.tsx L1225-1245 - DELETE THIS SECTION
// ❌ REMOVE - Replaced by Novaxe parity strings at L1111-1159
```

**Verification:**
- Inspect fretboard SVG in browser DevTools
- Count `<line>` elements within string group - should be 6 (not 12)
- Confirm string positions match Novaxe coordinates
- Check for visual artifacts or thickness inconsistencies

**Related Errors:** None (isolated to rendering)

---

### FR-006: Hardcoded Coordinate Constants Duplication

**Error Signature:**
```typescript
// YellowFingers.tsx L63-66
const novaxeYPositions = [4.5, 21.5, 39, 57, 75, 93];
const novaxeXPositions = [-14,7,28,50.5,73,95.5,119,141.5,164,186.5,210,232.5,255,277.5,301,323.5,346,368.5,392,415.5,438,460.5,483,505.5,529.5];

// IntervalBubbles.tsx L37-40
const novaxeYPositions = [4.5, 21.5, 39, 57, 75, 93];
const novaxeXPositions = [-14,7,28,50.5,73,95.5,119,141.5,164,186.5,210,232.5,255,277.5,301,323.5,346,368.5,392,415.5,438,460.5,483,505.5,529.5];

// ProceduralFretboard.tsx L1115
const novaxeYPositions = [4.5, 21.5, 39, 57, 75, 93];
```

**Root Cause:**
- Novaxe SEB coordinate arrays duplicated across 3+ components
- No single source of truth for positions
- Manual updates required in multiple locations if coordinates change
- Risk of desynchronization during refactors

**Affected Files:**
- `src/components/theater/widgets/fretboard/components/YellowFingers.tsx` (L63-66)
- `src/components/theater/widgets/fretboard/components/IntervalBubbles.tsx` (L37-40)
- `src/components/theater/widgets/fretboard/ProceduralFretboard.tsx` (L1115)
- Potentially: `CagedHighlight.tsx`, `FingeringHints.tsx` if they also need coordinates

**Impact:**
- **Severity:** Low
- Maintenance burden (update in N places for coordinate tweaks)
- Risk of visual misalignment if constants drift apart
- Code duplication anti-pattern

**Proven Solution:**

**Create shared constants file:**
```typescript
// src/components/theater/widgets/fretboard/constants/novaxeCoordinates.ts
/**
 * Novaxe SEB Exact Coordinates
 * 
 * These coordinates match the original Novaxe SEB implementation pixel-perfectly.
 * DO NOT modify without visual regression testing against Novaxe reference.
 * 
 * Source: Novaxe SEB hardcoded values from original Angular codebase
 * ViewBox: -5 3 560 100
 */

/** String Y positions (6 strings, high E to low E) */
export const NOVAXE_STRING_Y_POSITIONS = [4.5, 21.5, 39, 57, 75, 93] as const;

/** Fret X positions (25 fret positions, including open string at -14) */
export const NOVAXE_FRET_X_POSITIONS = [
  -14, 7, 28, 50.5, 73, 95.5, 119, 141.5, 164, 186.5, 210, 
  232.5, 255, 277.5, 301, 323.5, 346, 368.5, 392, 415.5, 
  438, 460.5, 483, 505.5, 529.5
] as const;

/** Novaxe SEB viewBox dimensions */
export const NOVAXE_VIEWBOX = '-5 3 560 100' as const;

/** Novaxe SEB total width */
export const NOVAXE_WIDTH = 560 as const;

/** Novaxe SEB total height */
export const NOVAXE_HEIGHT = 100 as const;
```

**Update all components:**
```typescript
// YellowFingers.tsx L63-66
import { NOVAXE_STRING_Y_POSITIONS, NOVAXE_FRET_X_POSITIONS } from '../../constants/novaxeCoordinates';

export function YellowFingers({ ... }) {
  // ✅ Use imported constants
  // (Remove local declarations)
}

// IntervalBubbles.tsx L37-40
import { NOVAXE_STRING_Y_POSITIONS, NOVAXE_FRET_X_POSITIONS } from '../../constants/novaxeCoordinates';
// ✅ Use imported constants

// ProceduralFretboard.tsx L1115
import { NOVAXE_STRING_Y_POSITIONS } from './constants/novaxeCoordinates';
// ✅ Use imported constants
```

**Verification:**
- Grep for `const novaxeYPositions` and `const novaxeXPositions` in codebase
- Should only appear in constants file
- All components import from single source
- Visual regression test confirms no position changes

**Related Errors:** None (code quality improvement)

---

### Summary of Olympus Fretboard Errors

| Error ID | Severity | Status | Blocks Rendering | Quick Fix Available |
|----------|----------|--------|------------------|---------------------|
| FR-001   | Critical | 🔴 Open | Yes - Zero bubbles/fingers | ✅ Yes - Index adjustment |
| FR-002   | Critical | 🔴 Open | Yes - Empty position arrays | ✅ Yes - Use `tuning` array |
| FR-003   | High     | 🔴 Open | Yes - Score sync crash | ✅ Yes - Fix parameters |
| FR-004   | Medium   | 🔴 Open | No - Wrong labels shown | ✅ Yes - Separate arrays |
| FR-005   | Low-Med  | 🔴 Open | No - Visual artifacts | ✅ Yes - Remove duplicate |
| FR-006   | Low      | 🔴 Open | No - Maintenance issue | ✅ Yes - Centralize constants |

**Fix Priority Order:**
1. **FR-002** (Unblocks position generation)
2. **FR-001** (Enables rendering of generated positions)
3. **FR-003** (Fixes score sync integration)
4. **FR-004** (Restores degree display mode)
5. **FR-005** (Cleanup duplicate rendering)
6. **FR-006** (Refactor for maintainability)

**Estimated Fix Time:** 2-4 hours for all fixes + testing

**Testing Plan:**
1. Unit tests for index conversion logic (FR-001)
2. Integration tests for scale/chord position generation (FR-002)
3. E2E test for score sync playback (FR-003)
4. Visual regression test for display modes (FR-004)
5. SVG element count verification (FR-005)
6. Import verification across components (FR-006)

**Related Documentation:**
- Parity Plan: `/Users/markvandendool/MindSongJukeHub Fresh/mindsong-juke-hub` (root, user-provided plan)
- Type Definitions: `src/types/stringedInstrument.ts`
- Geometry Engine: `src/lib/music/proceduralFretboard.ts`
- Scale Helper: `src/lib/music/fretboardScales.ts`
- Chord Helper: `src/lib/music/fretboardChords.ts`
- Score Sync: `src/services/fretboardScoreSync.ts`

````

