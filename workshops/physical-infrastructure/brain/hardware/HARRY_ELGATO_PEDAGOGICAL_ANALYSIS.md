# Harry_Elgato Scene Collection: Comprehensive Pedagogical Analysis

## Academic Report on Guitar Music Theory Visualization Architecture
**Author:** Copilot Analysis Engine  
**Date:** January 2026  
**Subject:** Forensic examination of OBS scene architecture for guitar education  
**Collection:** Harry_Elgato_Fall_Freeze_fkup.json (238 scenes, 787 sources, 220 unique image assets)

---

## Executive Summary

The Harry_Elgato scene collection represents a **pioneering multimedia pedagogical system** for guitar music theory education. This analysis documents the architectural design patterns, animation systems, and source code integration that enabled real-time, multi-dimensional music theory visualization during live instruction.

### Key Findings

| Metric | Value |
|--------|-------|
| Total Scenes | 238 |
| Total Sources | 787 |
| Unique Image Assets | 220 |
| Maximum Items per Scene | 198 (Scale Scene) |
| Maximum Filters per Scene | 102 (Scale Scene) |
| Primary Web App | NovaXe SEB (Angular 10/11) |
| Secondary Visualization | Braid Tonal System (React TSX) |
| Input Devices | MIDI guitar, USB cameras, NDI network video |

---

## Part I: Scene Taxonomy

### 1.1 Hierarchical Classification

The scene collection follows a **compositional nesting** architecture where complex pedagogical scenes embed simpler functional scenes:

```
LEVEL 1: Master Teaching Scenes (5-10)
├── LEVEL 2: Compositional Scenes (30-50)
│   ├── LEVEL 3: Functional Modules (100+)
│   │   ├── LEVEL 4: Camera/Source Scenes (50+)
│   │   └── LEVEL 4: Overlay/Effect Scenes (50+)
```

### 1.2 Scene Categories

#### A. **Master Pedagogical Scenes** (The "Teaching Stations")

| Scene Name | Items | Filters | Purpose |
|------------|-------|---------|---------|
| `Scale Scene` | 198 | 102 | **Primary scale theory instruction** - displays interval notation, scale degrees, note letters with animated key shifts |
| `BRAID STUDY` | 197 | 34 | **Harmonic relationship visualization** - shows chord function, applied chords, dominant relationships |
| `BRAID STUDY 2` | 135 | 34 | **Simplified braid view** for focused chord progression work |
| `BRAID STUDY 2 FRET` | 132 | 34 | **Braid + Fretboard combination** for simultaneous harmonic/melodic instruction |
| `COF` | ~30 | varies | **Circle of Fifths** with toggleable mode overlays |
| `NewBraid 2` | 67 | 21 | **Updated braid system** with vortex animations |

#### B. **Fretboard Visualization Scenes**

| Scene Name | Items | Purpose |
|------------|-------|---------|
| `Roku Fretboard` | 18 | **Primary fretboard view** - captures NovaXe web app via screen capture |
| `5a. Left Hand Alone FretBoard` | 44 | **Position-specific fretboard** - focuses on one CAGED position |
| `5a. Left Hand Alone FretBoard 3` | 45 | Enhanced version with additional filters |
| `New Vertical Fretboard` | 19 | **Portrait orientation** for vertical streaming |
| `Both Long Frets` | 7 | Dual fretboard view |

#### C. **Camera/Video Source Scenes**

| Scene Name | Type | Purpose |
|------------|------|---------|
| `Canon Main 1` | Primary | Main performance camera (4K DSLR) |
| `Nikon` | Secondary | Alternative angle |
| `GoPro New` | Action cam | Close-up hand shots |
| `NDI iMac GoPro` | NDI | Network video from iMac |
| `NDI Dice` | NDI | Dice-mounted camera (KIT-3) |
| `iPhone 11 Camera RH` | iOS | Right hand close-up |

#### D. **Vertical Canvas (VERT) Scenes**

| Scene Name | Items | Purpose |
|------------|-------|---------|
| `VERT Braid` | 4 | Portrait braid for social media |
| `VERT COF Vert` | varies | Portrait Circle of Fifths |
| `VERT Canon Main 1` | varies | Portrait main camera |
| `Vertical Canvas PROXY` | varies | Window capture of OBS vertical canvas |

---

## Part II: Pedagogical Content Analysis

### 2.1 Music Theory Concepts Visualized

The scene collection teaches these hierarchical music theory concepts:

#### **Level 1: Foundational Intervals**
Image assets demonstrate complete interval notation system:

```
Root  b2nd  2nd  #2nd  b3rd  3rd  4th  #4th/b5th  5th  #5th  b6th  6th  b7th  7th
```

Extended intervals for jazz voicings:
```
b9th  9th  #9th  11th  #11th  b13th  13th  bb3rd  bb7th
```

**Pedagogical Purpose:** Students see interval relationships as geometric shapes on the fretboard. The "z" prefix items (e.g., `z Root`, `z 3rd`, `z 7th`) are toggleable overlays.

#### **Level 2: Scale Systems**
Text sources enumerate all scale types covered:

```typescript
// From BnB Scale Text source
"Major
Minor
Dorian
Phrygian
Lydian
Mixolydian
Locrian
Major/Minor Pentatonic
Major/Minor Blues
Harmonic Minor"
```

Each scale type has corresponding:
- **Interval overlay images** (highlighting scale degrees)
- **COF overlay** (showing key relationships)
- **Fretboard highlighting** (via NovaXe web app)

#### **Level 3: Chord Theory**
Text sources for chord types:

| Source Name | Content | Category |
|-------------|---------|----------|
| `Major Chord` | "Major" | Triad |
| `Minor Chord` | "Minor" | Triad |
| `Diminished Chord` | "Diminished" | Triad |
| `Augmented Chord` | "Augmented" | Triad |
| `Major 7th Chord` | "Major 7th" | Seventh |
| `Minor 7th Chord` | "Minor 7th" | Seventh |
| `Dom 7th Chord` | "Dominant 7th" | Seventh |
| `Half Diminished Chord` | "Half Diminished" | Seventh |
| `Fully Diminished Chord` | "Fully Diminished" | Seventh |
| `Sus2 Chord`, `Sus4 Chord`, `Sus9 Chord` | Suspended | Extensions |

#### **Level 4: Harmonic Function (The Braid)**
The braid visualization system shows chord relationships in tonal context:

```typescript
// From braid.component.ts - chord type mappings
public chord_type_notes = {
  fifth_left:  {up: '7b5', down: 'german'},      // Augmented 6th family
  left:        {up: '7',   down: 'm7b5'},        // Dominant / Half-diminished
  center:      {up: '7',   left: 'M', right: 'm'}, // Tonic major/minor
  right:       {up: '7',   down: 'dim'},         // Leading tone / Diminished
  fifth_right: {up: '7b5', down: 'german'},      // Augmented 6th family
}
```

**Scene Items for Braid Pedagogy:**
- `KeyCenterColor` - Visual marker for tonal center
- `DomMajor`, `DomMinor`, `DomMinor 2` - Dominant function groups
- `Applied Text` - "Applied Chords" label
- `Vof text` - "(Directional) V of ..." secondary dominant indicator
- `Aug 6th Group` - Augmented sixth chord family
- `Soft Tension Group` - Pre-dominant function
- `Motion Group` - Transitional harmonies

#### **Level 5: Applied/Secondary Dominants**
Key pedagogical concept emphasized:

```
"(Directional)
      V of ..."
```

This teaches students to identify secondary dominants (e.g., V/V, V/ii, V/vi) and understand their voice-leading implications.

### 2.2 Emotional/Kinesthetic Learning Elements

Text sources reveal affective learning approach:

| Source Name | Content | Purpose |
|-------------|---------|---------|
| `More Flats 2 2` | "Feels Higher, Uplifting" | Associate sharps with brightness |
| `More Flats 2 2 2` | "Feels Lower, Depressing" | Associate flats with darkness |
| `freedom` | "FREEDOM: Passing Notes, Multiple Chord Tones, Neighbors, Licks, Shred etc." | Liberation from strict chord tones |
| `feeling at rest` | "(Name of the Key)" | Tonic function = home/rest |
| `Motion Text` | "Motion" | Dominant function = tension/movement |
| `SOFTTension Text` | "Soft Tension" | Pre-dominant = gentle pull |

---

## Part III: Animation & Toggle System Architecture

### 3.1 Move Source Filter System

The scene collection uses OBS's `move_source_filter` plugin extensively for animated transitions between pedagogical states.

#### **Scale Scene Filters (102 total)**

| Filter Category | Count | Function |
|-----------------|-------|----------|
| `Letters Key of C Home` | 1 | Reset letter names to C position |
| `Shift 1` - `Shift 12` | 12 | Animate letter transposition through 12 keys |
| `Scale Degrees Home` | 1 | Reset scale degree numbers |
| `Scale Degree Shift 1` - `Shift 12` | 12 | Animate degree overlay through keys |
| Additional filters | ~76 | Various animated states |

**Example Filter Settings:**
```json
{
  "source": "Letters on Scale",
  "pos": {"x": 108, "y": 645},
  "duration": 1300,
  "simultaneous_move": "Highlights"
}
```

The `simultaneous_move` property links multiple sources to animate together - when "Letters" move, "Highlights" move in sync. Duration of 1300ms provides smooth, readable transitions.

#### **BRAID STUDY Filters (34 total)**

| Filter Name | Purpose |
|-------------|---------|
| `Chords IN/OUT` | Slide chord list into/out of view |
| `Braid Left/Center` | Position braid visualization |
| `Canon In/Out/Up` | Animate camera views |
| `BraidChords Left/Out` | Chord overlay positioning |
| `CUBES IN/OUT` | 3D cube visualization toggle |
| `Syntax IN/OUT` | Roman numeral syntax overlay |
| `Key Center Line 1/2 Start/Finish` | Animated key center indicators |
| `Scales Line 1/2 Start/Finish` | Scale degree overlay animation |
| `Chord Tones Line 1/2 Start/Finish` | Chord tone highlight animation |
| `Piano IN/OUT` | Synthesia piano view toggle |
| `FretHome`, `Fret P1/P2/P3` | Fretboard position states |
| `Vortrex Home/Up/Down` | Vortex animation positions |

### 3.2 Hotkey-Triggered Pedagogical States

The filters enable rapid toggling between teaching modes:

**State Machine Example (BRAID STUDY):**
```
[HOME STATE] ──Hotkey1──> [CHORDS VISIBLE]
     │                          │
     │                    Hotkey2
     │                          ▼
Hotkey3               [SCALES VISIBLE]
     │                          │
     ▼                    Hotkey4
[BRAID CENTERED]              ▼
     │                [CHORD TONES VISIBLE]
     │                          │
     └────────Hotkey5───────────┘
                    ▼
           [COMBINED VIEW]
```

---

## Part IV: NovaXe/Seb Source Code Integration

### 4.1 Angular Legacy Application (Novaxe SEB)

**Repository:** `/home/mark/mindsong-juke-hub/Novaxe SEB/`

The Angular application provides the primary real-time visualization captured by OBS.

#### **Fretboard Component** (`fretboard.component.ts` - 1207 lines)

Key pedagogical features:

```typescript
// Real-time MIDI input processing
@Input() set cur_chord(chord) {
  this.unlight_all_glow();
  this.unlight_finger_on_fretboard();
  this.light_chord(chord);  // Highlights played chord on fretboard
  this.lit_chord = chord;
}

// Score-following mode
this.beat_selectionUpdate$ = this.transport.beatChange.subscribe(data => {
  if(this.scale_follow_score) this.set_scale_from_measure(m);
  if(this.chord_follow_score) {
    this.light_chord_from_measure(m, b);
    // Updates fretboard visualization in real-time
  }
});

// CAGED position system
public caged_position: Array<'C'|'A'|'G'|'E'|'D'> = [];
```

**Fretboard Structure:**
- 6 strings × 25 frets = 150 interactive positions
- Each position has: `display_los` (losange), `display_fing` (finger), `display_glow` (highlight), `display_midi` (MIDI)
- Losange = scale degree markers
- Finger = currently playing note
- Glow = emphasis/highlight
- MIDI = real-time input indication

#### **Braid Component** (`braid.component.ts` - 1196 lines)

Key pedagogical features:

```typescript
// Tonality arrays for all 12 keys
import Tonalites from '@assets/braid_tonalities.json';

public fifth_left_up = Tonalites["C"].outer_left_up;
public left_up = Tonalites["C"].left_up;
public center_left = Tonalites["C"].center_major;
public center_right = Tonalites["C"].center_minor;
public right_up = Tonalites["C"].right_up;
public fifth_right_up = Tonalites["C"].outer_right_up;

// Roman numeral mode with rotation
public center_right_roman = ([...Tonalites["roman"].center_minor_tonal] as any).rotate(-3);

// Score-following chord changes
this.chordChangeSub$ = this.curChordMod.current_chord$.subscribe((data) => {
  this.cur_score_chord = data.root + data.chordType;
  this.change_score_chord(this.cur_score_chord);
});
```

**Braid Structure:**
The braid visualizes harmonic relationships as a vertical lattice:
- **Center column:** Tonic major (left) and relative minor (right)
- **Left columns:** Subdominant family (IV, ii)
- **Right columns:** Dominant family (V, viidim)
- **Outer columns:** Extended relationships (secondary dominants, Aug6)

### 4.2 React Modern Application (mindsong-juke-hub)

**Repository:** `/home/mark/mindsong-juke-hub/`

#### **NovaxeBraid.tsx** (559 lines)

Modern React implementation with improved TypeScript:

```typescript
interface TonalSet {
  center_major: string[];
  center_minor: string[];
  left_up: string[];
  left_down: string[];
  right_up: string[];
  right_down: string[];
  outer_left_up: string[];
  outer_left_down: string[];
  outer_right_up: string[];
  outer_right_down: string[];
}

// SVG-based braid rendering
<svg viewBox="-10 40 320 1600" style={{ transform: `scale(${zoom})` }}>
  {/* Gradient definitions for chord quality colors */}
  <linearGradient id="greenGradient">...</linearGradient>
  
  {/* Comma shapes for chord bubbles */}
  <g id="leftCommaXL">...</g>
  <g id="rightCommaXL">...</g>
  
  {/* Arrow indicators for harmonic motion */}
  <g id="leftArrow">...</g>
  <g id="rightArrow">...</g>
</svg>
```

#### **Fretboard.tsx** (382 lines)

Modern React fretboard with virtualization:

```typescript
// Scale and chord highlighting
const highlights = useMemo(() => {
  const allHighlights: FretboardHighlight[] = [];
  
  // Scale highlights for current mode
  const scaleHighlights = getScaleHighlights(tonic, mode, ...);
  
  // Chord highlights for current harmony
  const chordHighlights = getChordHighlights(currentChord, ...);
  
  // 3NPS pattern highlights
  const patternHighlights = get3NPSPatternPositions(tonic, pattern, mode, ...);
  
  // Pentatonic shape highlights
  const shapeHighlights = getPentatonicShapePositions(tonic, shape, ...);
  
  return allHighlights;
}, [variant, tonic, mode, currentChord, ...]);
```

### 4.3 OBS Screen Capture Integration

The scene collection captures the web apps via:

| OBS Source | Target Application |
|------------|-------------------|
| `macOS ScreenCAP RCA NOVAXE` | NovaXe SEB (primary fretboard/braid) |
| `macOS ScreenCAP Chordie App` | ChordieApp (chord dictionary) |
| `macOS ScreenCap ROKU` | Roku integration |
| `SynthPiano Window` | Synthesia (piano visualization) |
| `macOS Guitar Pro Capture` | Guitar Pro (tablature) |

---

## Part V: Multi-Camera Architecture

### 5.1 Video Input Matrix

| Source | Resolution | Protocol | Purpose |
|--------|------------|----------|---------|
| Canon DSLR | 4K | USB/HDMI | Primary performance camera |
| Nikon | 1080p | USB | Secondary angle |
| GoPro | 1080p/60 | USB | Action shots, close-ups |
| NDI iMac GoPro | 1080p | NDI | Network video from iMac |
| NDI Dice (KIT-3) | 1080p | NDI | Dice-mounted perspective |
| iPhone 11 | 1080p | USB/NDI | Right hand close-up |
| Elgato (DeckLink) | 4K | DeckLink | Reference monitoring |

### 5.2 NDI Network Configuration

```
[Mac Studio]          [iMac]           [Kit-3 NDI Device]
    │                   │                    │
    │    NDI over LAN   │                    │
    └───────────────────┴────────────────────┘
              │
              ▼
    [OBS NDI Sources]
    - NDI iMac GoPro
    - NDI Dice
```

---

## Part VI: Capo System Implementation

### 6.1 Roku Fretboard Capo Overlays

The `Roku Fretboard` scene contains 10 capo position overlays:

```
Capo 1, Capo 2, Capo 3, Capo 4, Capo 5
Capo 6, Capo 7, Capo 8, Capo 9, Capo 10
```

**Pedagogical Purpose:**
- Toggleable overlays show effective key transposition
- Visual indication of "new nut" position
- Integration with fretboard highlighting (NovaXe adjusts positions)

### 6.2 Black Masking System

Multiple black color sources mask fretboard regions:
- `Fretboard Black`, `Fretboard Black 2`
- `BLACK 2 3 2`, `BLACK 2 5`
- `BLACK BACKGROUND`

These enable:
- Position isolation (show only one CAGED position)
- Focus attention on specific fret range
- Clean composition for streaming

---

## Part VII: Circle of Fifths (COF) Overlay System

### 7.1 COF Scene Architecture

The `COF` scene contains 30+ toggleable overlays representing different modal/tonal views:

| Overlay Name | Visualization |
|--------------|---------------|
| `COFMajorKey` | Major key highlighting |
| `COFMinorKey` | Relative minor highlighting |
| `COF DorianKey` | Dorian mode centers |
| `COF PhrygianKey` | Phrygian mode centers |
| `COF LydianKey` | Lydian mode centers |
| `COF MixolydianKey` | Mixolydian mode centers |
| `COF LocrianKey` | Locrian mode centers |
| `COF MajorPentBlues` | Pentatonic/blues overlay |
| `COF MinorPentBlues` | Minor pentatonic overlay |
| `COF HarmMinor` | Harmonic minor overlay |
| `COF Parallel Modes` | Parallel mode relationships |
| `COF Relative Modes` | Relative mode relationships |
| `COF Chord Quality` | Chord quality indicators |

### 7.2 Image Assets for COF

| Asset Path | Purpose |
|------------|---------|
| `COF Major Key.png` | Major key center highlight |
| `COF Minor Key.png` | Minor key center highlight |
| `COF Keys Transp-01.png` | Transposition guide |
| `COF Chord Qualities.png` | I, ii, iii, IV, V, vi, vii° labels |
| `COF MODS.png` | Mode modifications |
| `COF Triple Key.png` | Major/relative minor/parallel minor |

---

## Part VIII: Text-Based Pedagogical Content

### 8.1 Lesson Structure Labels

| Text Source | Content | Context |
|-------------|---------|---------|
| `1. Choose and Use` | "Choose and Use 1 Position" | CAGED introduction |
| `1. Choose and Use 2` | "CAGED Major and Minor" | Chord form study |
| `1. Choose and Use 2 2` | "The TRICK" | Pattern recognition |
| `1. Choose and Use 2 3` | "Full Vocab" | Extended vocabulary |
| `1. Subtext A` | "-Choose 1/5 Positions -Any Major/Minor Key -Play any Melody/Bassline" | Learning objectives |
| `1. Subtext B` | "-Demo and Checklist -Any Maj/Min Chord 5x -Challenge!" | Practice instructions |
| `1. Subtext D 2` | "-Diatonic Domination -The Magic 19 -CAGED Dominant -Applied/Directional" | Advanced concepts |

### 8.2 Interactive Prompts

| Text Source | Content | Purpose |
|-------------|---------|---------|
| `What Chord?` | "WHAT CHORD IS THIS?" | Student engagement |
| `Bass Text` | "1. BASS?" | Chord analysis prompt |
| `Bass Text 2` | "2. TOP NOTE?" | Voicing analysis |
| `Bass Text 2 2` | "3. EXTRAS?" | Extension identification |
| `How to Play` | "HOW TO PLAY" | Section header |
| `How to Play 2` | "and UNDERSTAND" | Theory emphasis |

### 8.3 Song Titles for Contextual Learning

| Text Source | Content |
|-------------|---------|
| `Song Title of the Day` | "Thinking Out Loud" |
| `TEXTTITLEOTD 2` | "The New Years Song - Auld Lang Syne" |
| `TEXTTITLEOTD 3` | "SUNNY" |
| `TEXTTITLEOTD` | "THE REAL HERO" |

---

## Part IX: Pedagogical Design Patterns

### 9.1 The "Reveal" Pattern

Scenes are structured to progressively reveal complexity:

```
STEP 1: Show fretboard alone
     ▼
STEP 2: Add scale degree overlays
     ▼
STEP 3: Add interval labels
     ▼
STEP 4: Add chord tone highlighting
     ▼
STEP 5: Add harmonic function (braid)
     ▼
STEP 6: Add Circle of Fifths context
```

Each step can be triggered by hotkey, allowing real-time adaptation to student comprehension.

### 9.2 The "Mirror" Pattern

Multiple representation formats for same concept:

| Concept | Visual 1 | Visual 2 | Visual 3 |
|---------|----------|----------|----------|
| Key of C | Fretboard highlighting | Braid "C" emphasis | COF position |
| Major Scale | Interval overlay | Roman numerals | Scale degree numbers |
| Dominant | Fret positions | Braid position | "V" label |

### 9.3 The "Context Toggle" Pattern

Switches between absolute and relative views:

**Absolute Mode:**
- Note names (C, D, E, F, G, A, B)
- Chord symbols (Cmaj7, Dm7, G7)
- Fret numbers

**Relative Mode:**
- Scale degrees (1, 2, 3, 4, 5, 6, 7)
- Roman numerals (I, ii, iii, IV, V, vi, viidim)
- Interval names (Root, 3rd, 5th, 7th)

Toggle implemented via:
```typescript
// From fretboard.component.ts
this.displayNotesMode_SUBJ_update$ = this.cm.displayNotesMode_SUBJ_update$.subscribe(data => {
  if(data == 'letters') {
    this.displayNotesMode = false;  // Show note names
  } else {
    this.displayNotesMode = true;   // Show intervals
  }
});
```

---

## Part X: Real-Time Feedback Loop

### 10.1 MIDI Guitar Integration

The system provides immediate visual feedback when the instructor plays:

```
[Guitar + MIDI Pickup]
         │
         ▼
    [MIDI Input]
         │
         ▼
[NovaXe Fretboard Component]
    light_chord(chord)
    light_finger(string, fret)
         │
         ▼
[OBS Screen Capture]
         │
         ▼
[Student Display/Stream]
```

**Fretboard Response Methods:**
```typescript
// Highlight specific note
light_finger(string: number, fret: number) {
  this.fb_struct[string][fret].display_fing = true;
  this.fb_struct[string][fret].display_glow = true;
}

// Highlight full chord voicing
light_chord(chord) {
  for(let note of chord.full_chord.midi_tab) {
    this.light_finger(note.string, note.fret);
  }
}
```

### 10.2 Braid Chord Detection

When instructor plays, braid highlights corresponding harmonic position:

```typescript
// From braid.component.ts
this.chordChangeSub$ = this.curChordMod.current_chord$.subscribe((data) => {
  this.cur_score_chord = data.root + data.chordType;
  this.change_score_chord(this.cur_score_chord);  // Updates braid highlighting
});
```

---

## Part XI: Conclusions & Recommendations

### 11.1 Architectural Strengths

1. **Modular Composition:** Scene nesting enables complex pedagogical states from simple components
2. **Animation System:** Move Source Filters provide smooth, professional transitions
3. **Multi-Modal Learning:** Same concept shown on fretboard, braid, and COF simultaneously
4. **Real-Time Feedback:** MIDI integration creates immediate visual response
5. **Scalability:** H/V canvas variants support multiple streaming platforms

### 11.2 Identified Challenges

1. **Naming Inconsistency:** Mix of numbered versions, typos, legacy names
2. **Orphan Sources:** ~100 sources not in active scenes
3. **Filter Duplication:** Similar animation states duplicated across scenes
4. **Path Dependencies:** Image assets hardcoded to `/Volumes/Orion/OBS Portable/`

### 11.3 Recommendations for "Dream Collection"

See companion document: **DREAM_SCENE_COLLECTION_RECOMMENDATION.md**

---

## Appendices

### Appendix A: Complete Source Type Inventory

| Type | Count | Purpose |
|------|-------|---------|
| `scene` | 238 | Compositional containers |
| `image_source` | ~180 | Static overlays |
| `text_ft2_source_v2` | ~80 | Labels and annotations |
| `color_source_v3` | ~40 | Background/masking |
| `screen_capture` | 7 | Web app captures |
| `window_capture` | 4 | Application windows |
| `ndi_source` | 2 | Network video |
| `display_capture` | 1 | Full display |
| `decklink-input` | 1 | Professional video I/O |
| `av_capture_input` | varies | USB cameras |

### Appendix B: Filter Types Used

| Filter | Purpose |
|--------|---------|
| `move_source_filter` | Position/scale/rotation animation |
| `move_value_filter` | Property value animation |
| `streamfx-source-mirror` | Source duplication with transforms |
| `color_key_filter_v2` | Chroma keying |
| `crop_filter` | Region isolation |

### Appendix C: Key Image Asset Categories

| Category | Example Files | Count |
|----------|---------------|-------|
| Intervals | `Root-01.png`, `3rd-01.png`, `b7th-01.png` | ~30 |
| COF Overlays | `COF Major Key.png`, `COF DorianKey.png` | ~20 |
| Chord Icons | `Chord Tones icon Braids.png` | ~10 |
| CAGED Forms | (referenced in code) | ~5 |
| Capo Markers | `Capo 1` through `Capo 10` | 10 |
| UI Elements | `Logo.png`, borders, backgrounds | ~20 |

---

*This report was generated through forensic analysis of the Harry_Elgato_Fall_Freeze_fkup.json scene collection and cross-reference with the NovaXe SEB (Angular) and mindsong-juke-hub (React) source code repositories.*
