# Dream Scene Collection Architecture

## Optimal OBS Scene Design for Guitar Music Theory Instruction
**Companion Document to:** HARRY_ELGATO_PEDAGOGICAL_ANALYSIS.md  
**Purpose:** Define the ideal scene collection based on forensic analysis  
**Target Platform:** OBS Studio 31.x on Linux (with macOS compatibility)

---

## Design Principles

### 1. Naming Convention

```
[EMOJI] [CATEGORY] - [NAME] ([VARIANT])
```

**Category Prefixes:**
| Prefix | Category | Example |
|--------|----------|---------|
| `📷` | Camera Sources | `📷 CAM - Canon Main` |
| `🎸` | Fretboard Scenes | `🎸 FRET - Full Board` |
| `🔗` | Braid Scenes | `🔗 BRAID - Study Mode` |
| `⭕` | Circle of Fifths | `⭕ COF - Major Keys` |
| `📊` | Theory Overlays | `📊 THEORY - Intervals` |
| `🖥️` | Screen Captures | `🖥️ APP - NovaXe Fret` |
| `📺` | Master Scenes | `📺 MASTER - Full Lesson` |
| `📱` | Vertical Scenes | `📱 VERT - Braid` |
| `🔧` | Utility Scenes | `🔧 UTIL - Black Fill` |
| `---` | Separators | `--- 📁 CAMERAS ---` |

### 2. Scene Hierarchy

```
LAYER 0: Separators (organizational only, never go live)
LAYER 1: Master Scenes (what goes live)
LAYER 2: Composition Scenes (building blocks)
LAYER 3: Module Scenes (reusable components)
LAYER 4: Source Scenes (raw inputs)
```

---

## The Dream Collection Structure

### Section 1: Separators (Organizational)

```
--- 📁 CAMERAS ---
--- 📁 COMPOSITIONS ---
--- 📁 FRETBOARD ---
--- 📁 BRAID ---
--- 📁 CIRCLE OF FIFTHS ---
--- 📁 OVERLAYS ---
--- 📁 VERTICAL ---
--- 📁 UTILITIES ---
```

### Section 2: Camera Sources (Layer 4)

```
📷 CAM - Canon Main (4K)
📷 CAM - Canon Close-Up
📷 CAM - GoPro Right Hand
📷 CAM - GoPro Left Hand
📷 CAM - Overhead
📷 CAM - NDI iMac
📷 CAM - NDI Kit3
📷 CAM - iPhone RH
```

### Section 3: Screen Capture Sources (Layer 4)

```
🖥️ APP - NovaXe Fretboard
🖥️ APP - NovaXe Braid
🖥️ APP - Chordie
🖥️ APP - Synthesia Piano
🖥️ APP - Guitar Pro
```

### Section 4: Fretboard Scenes (Layer 3)

```
🎸 FRET - Full Board (H)
🎸 FRET - Full Board (V)
🎸 FRET - Position 1 (C Form)
🎸 FRET - Position 2 (A Form)
🎸 FRET - Position 3 (G Form)
🎸 FRET - Position 4 (E Form)
🎸 FRET - Position 5 (D Form)
🎸 FRET - Capo Overlay
🎸 FRET - Interval Labels
🎸 FRET - Scale Degrees
```

#### Fretboard Scene Contents

**🎸 FRET - Full Board (H):**
```
Sources:
- 🔧 UTIL - Black Background
- 🖥️ APP - NovaXe Fretboard
- (Group) Capo Overlays [toggleable 1-10]
- (Group) Position Masks [toggleable C/A/G/E/D]

Filters:
- Home Position
- Pan Left
- Pan Right
- Zoom Frets 0-5
- Zoom Frets 5-12
- Zoom Frets 12-17
```

### Section 5: Braid Scenes (Layer 3)

```
🔗 BRAID - Full Study (H)
🔗 BRAID - Full Study (V)
🔗 BRAID - Key Center Focus
🔗 BRAID - Dominant Family
🔗 BRAID - Applied Chords
🔗 BRAID - Aug6 Family
🔗 BRAID - Roman Numerals
```

#### Braid Scene Contents

**🔗 BRAID - Full Study (H):**
```
Sources:
- 🔧 UTIL - Black Background
- 🖥️ APP - NovaXe Braid
- (Group) Key Center Labels [toggleable]
- (Group) Dominant Indicators [toggleable]
- (Group) Applied Chord Labels [toggleable]
- (Group) Vortex Animation [toggleable]

Filters:
- Braid Center Position
- Braid Left Position
- Zoom In
- Zoom Out
```

### Section 6: Circle of Fifths Scenes (Layer 3)

```
⭕ COF - Base Circle (H)
⭕ COF - Base Circle (V)
⭕ COF - Major Key Mode
⭕ COF - Minor Key Mode
⭕ COF - Dorian Mode
⭕ COF - Phrygian Mode
⭕ COF - Lydian Mode
⭕ COF - Mixolydian Mode
⭕ COF - Pentatonic/Blues
⭕ COF - Relative Modes
⭕ COF - Parallel Modes
```

#### COF Scene Contents

**⭕ COF - Base Circle (H):**
```
Sources:
- 🔧 UTIL - Black Background
- 🖥️ APP - NovaXe COF
- Circle Border Image
- (Group) Mode Overlays [Major/Minor/Dorian/etc.]
- (Group) Quality Labels [toggleable]

Filters:
- Home Position
- Rotate Clockwise (5th)
- Rotate Counter-Clockwise (4th)
- Zoom In
```

### Section 7: Theory Overlay Scenes (Layer 3)

```
📊 THEORY - Interval Set (Root through 13th)
📊 THEORY - Scale Degree Numbers
📊 THEORY - Chord Type Labels
📊 THEORY - Roman Numerals
📊 THEORY - Lesson Titles
📊 THEORY - Practice Prompts
```

#### Theory Scene Contents

**📊 THEORY - Interval Set:**
```
Sources (all toggleable):
- Root, 2nd, b2nd, #2nd
- 3rd, b3rd, bb3rd, #3rd
- 4th, #4th
- 5th, b5th, #5th
- 6th, b6th
- 7th, b7th, bb7th
- 9th, b9th, #9th
- 11th, #11th
- 13th, b13th
```

### Section 8: Composition Scenes (Layer 2)

```
🎼 COMP - Camera + Fret (Split H)
🎼 COMP - Camera + Braid (Split H)
🎼 COMP - Fret + Braid (Split H)
🎼 COMP - Camera + Fret + Braid (Triple)
🎼 COMP - Camera + COF (Split H)
🎼 COMP - Full Theory Suite (Camera + Fret + Braid + COF)
🎼 COMP - Piano + Fret (Synthesia Mode)
```

#### Composition Scene Contents

**🎼 COMP - Camera + Fret + Braid (Triple):**
```
Layout: 2560x1440 canvas
┌─────────────────────────────────────┐
│  Camera (1280x1080)  │  Braid      │
│                      │  (640x1080) │
│                      │             │
├──────────────────────┴─────────────┤
│        Fretboard (2560x360)        │
└────────────────────────────────────┘

Sources:
- 📷 CAM - Canon Main (positioned top-left)
- 🔗 BRAID - Full Study (positioned top-right)
- 🎸 FRET - Full Board (positioned bottom, cropped height)
- 📊 THEORY - Lesson Titles (positioned as overlay)

Filters:
- Chords IN/OUT (animate braid visibility)
- Fret UP/DOWN (animate fretboard visibility)
- Camera FULL (expand camera to full canvas)
- Theory Labels IN/OUT
```

### Section 9: Master Scenes (Layer 1)

```
📺 MASTER - Scale Lesson
📺 MASTER - Chord Lesson
📺 MASTER - Braid Lesson
📺 MASTER - Song Analysis
📺 MASTER - Full Theory View
📺 MASTER - Performance Only
📺 MASTER - Countdown/Break
📺 MASTER - Calibration
```

#### Master Scene Contents

**📺 MASTER - Full Theory View:**
```
Sources:
- 🎼 COMP - Full Theory Suite (as nested scene)
- Logo Overlay
- Timer Text
- Song Title Text

Filters:
- (Inherited from composition scene)
- Master Volume Automation
- Stream Start Animation
```

### Section 10: Vertical Scenes (Layer 1-2)

```
📱 VERT - Camera Only
📱 VERT - Camera + Fret
📱 VERT - Camera + Braid
📱 VERT - Braid Only
📱 VERT - COF Only
📱 VERT - Full Lesson
```

#### Vertical Scene Contents

**📱 VERT - Full Lesson:**
```
Layout: 1080x1920 canvas
┌──────────────────┐
│   Camera (top)   │
│   1080x810       │
├──────────────────┤
│   Braid (mid)    │
│   1080x740       │
├──────────────────┤
│  Fretboard (bot) │
│   1080x370       │
└──────────────────┘
```

### Section 11: Utility Scenes (Layer 4)

```
🔧 UTIL - Black Background
🔧 UTIL - Transparent Fill
🔧 UTIL - Logo Watermark
🔧 UTIL - Countdown Timer
🔧 UTIL - Screen Calibration
🔧 UTIL - Audio Test
```

---

## Filter Architecture

### Global Filter Set (Per Scene)

Every pedagogical scene should have these standard filters:

```
Position Filters:
- Home (default position)
- Left/Right/Up/Down shifts
- Zoom In/Out

Visibility Filters:
- Fade In (500ms)
- Fade Out (500ms)
- Quick Reveal (100ms)

Animation Filters:
- Key Shift 1-12 (for transposition animations)
- Scale Degree Shift 1-12
```

### Filter Naming Convention

```
[TARGET] - [ACTION] ([VARIANT])
```

Examples:
- `Fretboard - Pan Left`
- `Braid - Zoom In`
- `Key Letters - Shift 5 (to F)`
- `Scale Degrees - Home`

---

## Hotkey Map

### Function Keys (F1-F12)

| Key | Function |
|-----|----------|
| F1 | 📺 MASTER - Full Theory View |
| F2 | 📺 MASTER - Scale Lesson |
| F3 | 📺 MASTER - Chord Lesson |
| F4 | 📺 MASTER - Braid Lesson |
| F5 | 📺 MASTER - Performance Only |
| F6 | Toggle Fretboard |
| F7 | Toggle Braid |
| F8 | Toggle COF |
| F9 | Toggle Intervals |
| F10 | Toggle Roman Numerals |
| F11 | Fullscreen |
| F12 | Start/Stop Stream |

### Number Keys (1-0)

| Key | Function |
|-----|----------|
| 1-9, 0 | Camera angles / Quick scenes |

### Letter Keys (with Ctrl)

| Key | Function |
|-----|----------|
| Ctrl+K | Key shift +1 (animate) |
| Ctrl+J | Key shift -1 (animate) |
| Ctrl+I | Interval overlay toggle |
| Ctrl+R | Roman numeral toggle |
| Ctrl+C | Capo overlay cycle |

---

## Migration Checklist

### Phase 1: Create Infrastructure
- [ ] Set up folder structure in OBS
- [ ] Create separator scenes
- [ ] Create utility scenes

### Phase 2: Import Sources
- [ ] Configure camera sources
- [ ] Configure NDI sources
- [ ] Configure screen captures
- [ ] Import image assets (update paths to Linux)

### Phase 3: Build Modules
- [ ] Create fretboard scenes with position filters
- [ ] Create braid scenes with animation filters
- [ ] Create COF scenes with mode overlays
- [ ] Create theory overlay groups

### Phase 4: Build Compositions
- [ ] Create horizontal compositions
- [ ] Create vertical compositions
- [ ] Add animation filters to compositions

### Phase 5: Build Masters
- [ ] Create master scenes
- [ ] Configure hotkeys
- [ ] Test all transitions

### Phase 6: Validate
- [ ] Test all animation filters
- [ ] Test MIDI input feedback
- [ ] Test all camera switching
- [ ] Test streaming output

---

## Asset Migration

### Image Path Updates

**Old (macOS):**
```
/Volumes/Orion/OBS Portable/assets/Root-01.png
```

**New (Linux):**
```
/home/mark/obs-assets/intervals/Root-01.png
```

### Recommended Asset Folder Structure

```
/home/mark/obs-assets/
├── intervals/
│   ├── Root-01.png
│   ├── 2nd-01.png
│   └── ...
├── cof/
│   ├── COF-Major-Key.png
│   ├── COF-Minor-Key.png
│   └── ...
├── overlays/
│   ├── Logo.png
│   ├── Borders/
│   └── ...
├── backgrounds/
│   └── ...
└── icons/
    └── ...
```

---

## Performance Optimization

### Source Deduplication

Instead of duplicating sources, use:
1. **Scene references** (embed scene as source)
2. **Source mirrors** (streamfx-source-mirror)
3. **Groups** (for multi-source toggles)

### Filter Optimization

- Use `simultaneous_move` to animate multiple sources together
- Pre-calculate animation positions (don't use real-time calculations)
- Disable filters when not in use (visibility toggles)

### Memory Management

- Limit total sources to ~300 (from 787)
- Remove orphan sources
- Use lower-resolution images for overlays (1080p max)
- Enable hardware encoding for screen captures

---

## Total Scene Count Estimate

| Category | Count |
|----------|-------|
| Separators | 8 |
| Camera Sources | 8 |
| Screen Captures | 5 |
| Fretboard Scenes | 10 |
| Braid Scenes | 7 |
| COF Scenes | 11 |
| Theory Scenes | 6 |
| Compositions | 7 |
| Masters | 8 |
| Verticals | 6 |
| Utilities | 6 |
| **TOTAL** | **~82** |

This is a 66% reduction from the original 238 scenes, achieved through:
- Consistent naming eliminates confusion
- Modular composition eliminates duplication
- Toggleable groups replace multiple versions
- Filter states replace scene variants

---

*This recommendation is based on the pedagogical analysis of the Harry_Elgato_Fall_Freeze_fkup.json collection and represents an optimized architecture for the same educational content delivery.*
