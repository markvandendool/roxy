# Unified Fretboard Architecture

**Date:** November 3, 2025  
**Status:** DESIGN DOCUMENT (Implementation Deferred)  
**Purpose:** Consolidate 7 fretboard implementations into 1 unified widget

---

## Executive Summary

Currently we have **7 different fretboard implementations** scattered across the codebase, leading to code duplication, inconsistent behavior, and maintenance nightmares. This document proposes a unified architecture where a single `FretboardCore` component serves all use cases through configuration.

**Implementation Status:** DEFERRED until after Orchestra rail is stable.

---

## The Problem: 7 Implementations, 7 Problems

| # | Implementation | Location | Lines | Status | Issues |
|---|---|---|---|---|---|
| **1** | **Novaxe SEB (Angular)** | `/Novaxe SEB/src/app/components/fretboard/` | 2,361 | ✅ **GOLD STANDARD** | None - This is the source! |
| **2** | **8K Theater WebGPU (Rust)** | `packages/renderer-core/src/widgets/fretboard/` | 2,024 | 🔥 **BROKEN** | WASM issues, needs debugging |
| **3** | **Legacy Theater (SVG)** | `src/components/theater/widgets/fretboard/FretboardWidget.tsx` | ~800 | 🟡 **PARTIAL** | SVG only, no MIDI, no CAGED |
| **4** | **Fretboard V2 (MSOS)** | `src/components/theater/widgets/fretboard/FretboardWidgetV2.tsx` | ~600 | 🟡 **PARTIAL** | MSOS integration attempt, incomplete |
| **5** | **3D Renderer (Three.js)** | `src/components/fretboard/renderers/Fretboard3DRenderer.tsx` | ~400 | 🔥 **BROKEN** | Three.js, abandoned |
| **6** | **SVG Enhanced** | `src/components/theater/widgets/fretboard/components/FretboardSVGEnhanced.tsx` | ~300 | 🟡 **PARTIAL** | Enhanced SVG, incomplete |
| **7** | **NVX1 Visualization** | `packages/nvx1-score/src/components/FretboardVisualization.tsx` | ~200 | 🟡 **PARTIAL** | Score integration only |

**Total wasted code:** ~7,000 lines across 7 implementations!

---

## The Solution: Unified FretboardCore Component

### Architecture: Single Component with Modes

```typescript
<FretboardCore
  // Display Mode
  mode="full" | "chord" | "magic18"
  orientation="horizontal" | "vertical"
  fretRange={[0, 24]} | [startFret, endFret] // Sliding 4-fret mask
  
  // Visual Systems (Toggle any combination - from Novaxe SEB)
  showLosanges={true}      // Scale diamonds
  showFingers={true}        // Chord positions
  showBubbles={true}        // Interval labels (R, 3, 5, 7)
  showGlow={true}           // Glow effects
  showMidiInput={true}      // MIDI highlights
  
  // Follow Modes (from Novaxe SEB)
  scoreFollow={true|false|'both'}
  chordFollowScore={true}
  scaleFollowScore={true}
  
  // CAGED Filter
  cagedPositions={['E', 'A']}
  
  // Animation
  animation="Misty-time" | "Summertime" | "Off"
  animationSpeed={5}
  
  // Interaction
  clickable={true}
  onClick={(string, fret) => apollo.playNote(...)}
  
  // Audio
  audio={apollo}  // Global Apollo instance
  
  // Theme (Rocky's Style Control Power)
  theme={{
    bubbleColor: '#FFD700',
    glowColor: 'rgba(255, 215, 0, 0.6)',
    fingerColor: '#FFF',
    backgroundColor: 'Dark' | 'Classic'
  }}
  
  // MIDI Routing
  midiInput={midiService}
  midiControlMap={configModel.getAssignedControls()}
/>
```

### Use Cases

**Use Case 1: Full Fretboard Widget (8K Theater)**
```typescript
<FretboardCore
  mode="full"
  orientation="horizontal"
  fretRange={[0, 24]}
  showLosanges={true}
  showBubbles={true}
  showCAGED={true}
  midiEnabled={true}
/>
```

**Use Case 2: Chord Diagram (NVX1 Score)**
```typescript
<FretboardCore
  mode="chord"
  orientation="vertical"
  fretRange={[0, 3]} // 4-fret mask
  showFingers={true}
  showBubbles={true}
  clickable={true}
  showVoicingArrows={true}
/>
```

**Use Case 3: Magic 18 Widget**
```typescript
<FretboardCore
  mode="magic18"
  orientation="vertical"
  fretRange={cagedFretRange} // Slides with CAGED forms
  showBubbles={true}
  showRootButton={true}
  showVoicingArrows={true}
  clickableNotes={true}
  clickableStrings={true}
/>
```

---

## Novaxe SEB Architecture (Gold Standard Reference)

### Data Structure

The original Novaxe SEB uses a genius 2D array structure:

```typescript
// fb_struct[string][fret]
fb_struct: Array<Array<{
  display_los: boolean,      // Diamond shape (scale visualization)
  display_fing: boolean,     // Finger position (LH chord)
  display_bub: boolean,      // Bubble with interval (R, 3, 5, 7)
  display_glow: boolean,     // Glow effect
  display_midi: boolean,     // MIDI input highlight
  bubble_img: string,        // Interval image ("R.png", "3.png", etc.)
  midi_img: string          // MIDI indicator
}>> = [];
```

### Three Visual Systems

1. **Losanges (Diamonds)** - Scale/mode visualization (all scale degrees)
2. **Fingers** - Chord positions (specific chord fingerings)
3. **Bubbles** - Interval labels (chord tone functions: R, 3, 5, 7)

### Display Modes & Toggles

```typescript
// Display Modes (from ConfigModel):
- score_follow: true|false|'both'  // Follow score vs MIDI
- chord_follow_score: boolean      // Sync chords with score
- scale_follow_score: boolean      // Sync scale with score
- displayNotesMode: boolean        // Letters vs Intervals
- rotated: boolean                 // Flip fretboard orientation
- right_handed: boolean            // Left vs right handed
- activeBubbles: boolean           // Show interval bubbles
- activeLosanges: boolean          // Show scale diamonds
- glowingBubbles: boolean          // Animated glow effect

// Animation Presets:
- 'Misty', 'Summertime', 'Fever', 'Misty-time', 'Off'
- animationTime: number (5 = default)

// Visual Styles (Rocky's Theme Power):
- bg: ['Classic', 'Dark']
- selected_bg: string
```

### MIDI Integration (RxJS Observables)

```typescript
// Subscriptions:
1. cd.cur_midi_chord → Chord detection from MIDI guitar (Tonal.js, zero lag)
2. transport.beatChange → Sync with score playback
3. midi.controlTabSubject → MIDI control surface (CC messages)
4. midi.notesTabSubject → Individual note tracking

// MIDI Control Example:
// CC64 → toggle_midi("both")
// CC65 → change_animation("Misty")
// CC66 → toggle_bubbles()
```

### CAGED System

```typescript
caged_position: Array<'C'|'A'|'G'|'E'|'D'> = [];
caged_filter: Array<number> = [];

// Filters chord shapes by CAGED position
// Click CAGED symbol → rotate through forms → update fretRange
```

---

## Chord Diagram Requirements (from InDesign Interactive PDF)

### Interactive Elements

1. **Root Symbol (Circular, Green)**
   - Button with playback
   - Active state with glow animation
   - Clicking plays root note

2. **Voicing Arrows (Underneath Diagram)**
   - Left arrow (←): Previous voicing
   - Right arrow (→): Next voicing
   - Cycles through 336+ voicings from jtab-chord-library.ts
   - Updates diagram in real-time

3. **Individual Note Circles (R, 3, 5, 7)**
   - Each circle is a button
   - Clicking plays that specific note
   - Shows interval/function (Root, 3rd, 5th, 7th, etc.)
   - Color-coded: R=green, 3=red, 5=blue, 7=grey

4. **Strings (Vertical Lines)**
   - Clickable along their entire length
   - Play the note on that string
   - Simulates strumming (like iPad app for kids)

5. **Finger Indicators (Black Frames with White Notches)**
   - Black square frame around note circle
   - White notches indicate finger number:
     - 1 notch = Index finger
     - 2 notches = Index + Middle
     - 3 notches = Index + Middle + Ring
     - 4 notches = Full hand (barre!)

6. **Open/Muted Indicators**
   - 'O' (green circle) = Open string (clickable, plays open note)
   - 'X' (red X) = Muted string (clickable, plays muted/damped sound - TODO)

7. **Diagram Background**
   - Clicking empty space → ChordCubes plays full chord (voice leading via Apollo)

### Layout (Vertical Orientation, Top-Aligned)

```
    E A D G B E (strings, left to right)
    ┌─────────┐  ← Nut (if startFret=0) or Position marker
  0 │ O ● X ● O │  ← Open strings, some muted
  1 │ ┊ ┊ ┊ ● ┊ │  ← Fret 1
  2 │ ● ┊ ● ┊ ● │  ← Fret 2
  3 │ ┊ ● ┊ ┊ ┊ │  ← Fret 3
    └─────────┘
    
If chord is 5 frets wide:
    E A D G B E
    ┌─────────┐  
  7 │ ┊ ● ● ┊ ┊ │  
  8 │ ┊ ┊ ┊ ┊ ┊ │  
  9 │ ● ┊ ┊ ● ┊ │  
 10 │ ┊ ┊ ┊ ┊ ● │  
 11 │ ┊ ● ┊ ┊ ┊ │  ← Expands DOWNWARD (top-aligned)
    └─────────┘
```

---

## Global Apollo Integration

**Single Audio Engine for Everything:**

```typescript
// Global Apollo singleton
const apollo = await getApollo();

// All fretboard instances share the same Apollo
<FretboardCore audio={apollo} />
<ChordDiagram audio={apollo} />
<Magic18Widget audio={apollo} />

// Benefits:
// - Single AudioContext (no conflicts)
// - Shared instrument library (20 instruments)
// - Consistent voice leading (ChordCubes integration)
// - Unified effects chain
```

---

## ConfigModel → Zustand Store (Rocky's Theme Control)

**Centralized Style/Theme Management:**

```typescript
// Port Angular ConfigModel to React Zustand
interface FretboardConfigState {
  // Display toggles
  displayNoteMode: 'letters' | 'intervals';
  displayFretboard: boolean;
  activeBubbles: boolean;
  activeLosanges: boolean;
  glowingBubbles: boolean;
  
  // MIDI assignments
  assignedControls: Map<number, string>; // CC number → action
  
  // Theme (teacher customization)
  bubbleColor: string;
  glowColor: string;
  fingerColor: string;
  backgroundColor: 'Classic' | 'Dark';
  
  // Fonts
  labelFont: string;
  intervalFont: string;
  
  // Animation
  animationSpeed: number;
  visualEffects: boolean;
}
```

**This becomes Rocky's "style control power" for teachers to customize everything!**

---

## Migration Strategy

### Phase 1: Extract Core (No Breaking Changes)
- Extract `FretboardCore` from Novaxe SEB implementation
- Keep existing implementations as wrappers (backwards compatible)
- No changes to Theater or Score

### Phase 2: Build with Core
- New `InteractiveChordDiagram` uses `FretboardCore`
- Test in isolation
- Side-by-side comparison with old diagrams

### Phase 3: Replace Old Diagrams
- Swap old diagram rendering with new `InteractiveChordDiagram`
- Verify MIDI works
- Verify click interactions work

### Phase 4: Add Magic 18 Features
- Voicing arrows (implemented in current Interactive Chord Diagram)
- Root button with glow
- Individual note playback
- String strumming
- CAGED form rotation

### Phase 5: Migrate Other Implementations
- Replace Legacy Theater fretboard
- Replace MSOS integration
- Deprecate broken implementations (3D, Three.js)
- Single source of truth

---

## Technical Specifications

### Viewport System

```
Full Fretboard (Horizontal - 8K Theater):
┌─────────────────────────────────────────┐
│ E ●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │  (24 frets)
│ B ━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ G ━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ D ━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ A ━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ E ━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
└─────────────────────────────────────────┘

Chord Diagram (Vertical - NVX1 Score):
    E A D G B E
    ┌─────────┐  
  0 │ O ● X ● │  ← 4-fret mask (can slide up/down)
  1 │ ┊ ┊ ┊ ● │
  2 │ ● ┊ ● ┊ │
  3 │ ┊ ● ┊ ┊ │
    └─────────┘
```

### Data Structure (from Novaxe SEB)

Port the `fb_struct` 2D array:

```typescript
interface FretboardCell {
  // Visual toggles
  showDiamond: boolean;     // Scale degree diamond
  showFinger: boolean;      // Chord finger position
  showBubble: boolean;      // Interval label bubble
  showGlow: boolean;        // Active glow effect
  showMidiHighlight: boolean; // MIDI input indicator
  
  // Content
  bubbleLabel: string;      // "R", "3", "5", "7", etc.
  bubbleColor: string;      // Green, red, blue, grey
  fingerNumber: number;     // 1-4
  
  // State
  isActive: boolean;        // Currently playing
  isMidi: boolean;          // Triggered by MIDI input
  isHovered: boolean;       // Mouse hover
}

type FretboardState = FretboardCell[][]; // [string][fret]
```

### Audio Integration

**Global Apollo Singleton:**

```typescript
// Single instance shared by all fretboard variants
const apollo = await getApollo();

// Click handler
const handleClick = (string: number, fret: number) => {
  const midiNote = stringFretToMidi(string, fret);
  apollo.playNote(midiNote, 'guitar', 0.5);
};

// MIDI input handler
midiService.notesTabSubject.subscribe((notes) => {
  // Update fretboard visualization
  updateFretboardState(notes);
  
  // No audio here - Apollo plays from MIDI directly
});
```

### ConfigModel → Zustand Store

**Port Angular services to React:**

```typescript
// Angular (Novaxe SEB)
ConfigModel {
  getDisplayNoteMode(): 'letters' | 'intervals'
  getAssignedControls(): Map<CCNumber, Action>
}

// React (new)
const useFretboardConfig = create<FretboardConfigState>(...);

// Usage
const config = useFretboardConfig();
<FretboardCore theme={config.theme} />
```

---

## Implementation Priority

### DEFER until after Orchestra Rail is complete

**Reasoning:**
1. Orchestra rail is user-facing, critical for NotaGen workflow
2. Fretboard consolidation is internal refactoring
3. Current SVG chord diagrams work "well enough" for now
4. Enhanced Interactive Chord Diagram (Phase 5) provides voicing arrows and clicking
5. Full consolidation can wait until architecture is stable

### When to implement:

- ✅ After Orchestra rail working and tested
- ✅ After Interactive Score click-to-play stable
- ✅ After Enhanced Chord Diagrams validated
- ✅ When user explicitly requests fretboard unification

---

## Benefits of Unified Architecture

### 1. Code Reuse (Massive Win)
- ✅ One rendering engine
- ✅ One MIDI handler
- ✅ One audio service integration
- ✅ One click/interaction system
- ✅ One set of tests
- ✅ ~5,000 lines of duplicate code eliminated

### 2. MIDI Integration
- ✅ MIDI guitar triggers notes on ALL fretboard variants simultaneously
- ✅ Real-time chord detection updates ALL displays
- ✅ One subscription, multiple views
- ✅ Consistent behavior across Theater and Score

### 3. Consistent UX
- ✅ Same interaction patterns everywhere
- ✅ Same visual language (bubbles, diamonds, fingers)
- ✅ Same animation presets
- ✅ Same theme/style control

### 4. Maintainability
- ✅ Fix bug once, fixed everywhere
- ✅ Add feature once, available everywhere
- ✅ Single documentation
- ✅ Easier onboarding for new developers

---

## Related Documentation

- **Novaxe SEB Fretboard:** `/Novaxe SEB/src/app/components/fretboard/fretboard.component.ts` (GOLD STANDARD)
- **Chord Voicing Service:** `src/services/chord/ChordVoicingService.ts` (Already implemented)
- **Interactive Chord Diagram:** `src/components/NVX1/ChordDiagram/InteractiveChordDiagram.tsx` (Phase 5)
- **JTAB Chord Library:** `src/lib/music/jtab-chord-library.ts` (336+ voicings)
- **Global Apollo:** `src/services/globalApollo.ts` (Unified audio engine)
- **8K Theater Fretboard (Rust):** `packages/renderer-core/src/widgets/fretboard/` (Needs debugging)

---

## Next Steps (When Implementing)

1. Read Novaxe SEB fretboard.component.ts completely
2. Extract core rendering logic to React/TypeScript
3. Port fb_struct data structure
4. Port three visual systems
5. Port animation system
6. Port MIDI integration (RxJS → Zustand/hooks)
7. Port ConfigModel (Angular → Zustand)
8. Create FretboardCore component
9. Test with all three use cases
10. Migrate existing implementations one by one

---

**Status:** DESIGN COMPLETE, IMPLEMENTATION DEFERRED

**Reason:** Focus on Orchestra rail first (user-facing, critical path)

**When to revisit:** After Orchestra rail is stable and tested

