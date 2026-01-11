# 📺 Horizontal Layout Guide

> **Version:** 1.0.0  
> **EPIC:** SKOREQ-OBS-DREAM  
> **Story:** STORY-005  
> **Canvas:** 2560×1440 @ 60fps

---

## Overview

The SKOREQ collection provides **8 master horizontal scenes** optimized for 16:9 broadcast to YouTube, Twitch, and professional recording. Each scene is designed for a specific teaching scenario with instant F-key switching.

---

## Master Scene Reference

### 📺 M1: Full Teaching Studio (F1)

**Default teaching layout** - The go-to scene for most lessons.

```
┌─────────────────────────────┬──────────┐
│                             │  Piano   │
│                             ├──────────┤
│     Main Camera             │ Fretboard│
│     (Sony A7IV)             ├─────┬────┤
│                             │ COF │Harm│
├─────────────────────────────┴─────┴────┤
│            Caption Region              │
└────────────────────────────────────────┘
```

**Use Cases:**
- General music lessons
- Theory explanations
- Default streaming layout

**Sources:** Main camera (1920×1440), 4 widgets in sidebar (640×360 each)

---

### 📺 M2: Close-Up Piano (F2)

**Piano technique focus** - Overhead camera with large piano widget.

```
┌──────────────────────────────────┬─────┐
│    Overhead Camera (Hands)       │Face │
│         (Sony FX30)              │ PiP │
├──────────────────────────────────┴─────┤
│                                        │
│           Piano Widget (Full)          │
│                                        │
└────────────────────────────────────────┘
```

**Use Cases:**
- Piano technique lessons
- Fingering demonstrations
- Chord voicing explanations

**Sources:** Overhead cam (top), Large piano widget (bottom), Face cam PiP

---

### 📺 M3: Guitar Focus (F3)

**Guitar lesson layout** - Main camera with fretboard visualization.

```
┌────────────────────────────────────────┐
│                                        │
│          Main Camera                   │
│          (Sony A7IV)                   │
│                                        │
├────────────────────────────────────────┤
│         Fretboard Widget (Full)        │
└────────────────────────────────────────┘
```

**Use Cases:**
- Guitar lessons
- Scale patterns
- Chord shapes
- Key transposition demonstrations

**Sources:** Main cam (top 2/3), Fretboard widget (bottom 1/3)

**Special Features:**
- Key transposition animation (Ctrl+Up/Down)
- 1300ms smooth slide for key changes

---

### 📺 M4: Theory Breakdown (F4)

**Music theory focus** - 2×2 grid for comprehensive analysis.

```
┌───────────────────┬───────────────────┐
│                   │                   │
│   Main Camera     │ Circle of Fifths  │
│                   │                   │
├───────────────────┼───────────────────┤
│                   │                   │
│ Harmonic Profile  │   Braid/Tonnetz   │
│                   │                   │
└───────────────────┴───────────────────┘
```

**Use Cases:**
- Chord progression analysis
- Key relationships
- Modal theory
- Harmonic function explanation

**Sources:** 4 equal quadrants (1280×720 each)

---

### 📺 M5: Multi-Instrument (F5)

**Comparison layout** - Piano and guitar side by side.

```
┌───────────┬───────────┬───────────┐
│           │           │           │
│  Piano    │   Main    │ Fretboard │
│  Widget   │  Camera   │  Widget   │
│           │           │           │
└───────────┴───────────┴───────────┘
```

**Use Cases:**
- Comparing instrument voicings
- "Same chord, different instrument"
- Multi-instrumentalist lessons

**Sources:** 3 vertical columns (853×1440 each)

---

### 📺 M6: Full Widget Array (F6)

**Analysis mode** - Small camera with all 8 widgets.

```
┌──────┬──────┬──────┬──────┐
│ Face │Piano │Fret  │ COF  │
│ Cam  │Widget│board │      │
├──────┼──────┼──────┼──────┤
│Harmon│Score │Metro │Braid │
│  ic  │ Tab  │ nome │Tempo │
└──────┴──────┴──────┴──────┘
```

**Use Cases:**
- Comprehensive musical analysis
- "Everything on screen" demonstrations
- Complex theory breakdowns

**Sources:** Face cam (640×480) + 8 widgets in 4×2 grid

---

### 📺 M7: DAW Production (F7)

**Production focus** - DAW screen capture with overlays.

```
┌────────────────────────────────────────┐
│                                        │
│         DAW Screen Capture             │
│          (Ableton/Logic)               │
│                                        │
├──────────┐                   ┌─────────┤
│Piano PiP │                   │Face PiP │
└──────────┴───────────────────┴─────────┘
```

**Use Cases:**
- Music production tutorials
- DAW workflow demonstrations
- Sound design lessons
- Mixing/mastering education

**Sources:** DAW capture (fullscreen), Piano widget PiP (left), Face cam PiP (right)

---

### 📺 M8: Interview Mode (F8)

**Dual camera split** - For guests and collaborations.

```
┌───────────────────┬───────────────────┐
│                   │                   │
│   Host Camera     │   Guest Camera    │
│   (Sony A7IV)     │   (GoPro/NDI)     │
│                   │                   │
├───────────────────┴───────────────────┤
│            Lower Third                │
└────────────────────────────────────────┘
```

**Use Cases:**
- Interviews
- Collaborations
- Remote guests (via NDI)
- Duets

**Sources:** 2 cameras (1280×1440 each), Lower third overlay

---

## Quick Reference Card

| Hotkey | Scene | Use Case |
|--------|-------|----------|
| **F1** | Full Teaching Studio | Default/general |
| **F2** | Close-Up Piano | Piano technique |
| **F3** | Guitar Focus | Guitar lessons |
| **F4** | Theory Breakdown | Music theory |
| **F5** | Multi-Instrument | Comparison |
| **F6** | Full Widget Array | Analysis |
| **F7** | DAW Production | Production |
| **F8** | Interview Mode | Guests |

---

## Widget Toggle Hotkeys

While in any master scene, toggle individual widgets:

| Hotkey | Widget |
|--------|--------|
| Ctrl+1 | 🎹 Piano |
| Ctrl+2 | 🎸 Fretboard |
| Ctrl+3 | 🔵 Circle of Fifths |
| Ctrl+4 | 📊 Harmonic Profile |
| Ctrl+5 | 🎵 Score/Tab |
| Ctrl+6 | ⏱️ Metronome |
| Ctrl+7 | 🌀 Braid/Tonnetz |
| Ctrl+8 | 📐 Tempo Geometry |
| Ctrl+9 | 📦 Captions |
| Ctrl+0 | 🏷️ Branding |

---

## Key Transposition (Fretboard/Piano)

| Hotkey | Action |
|--------|--------|
| Ctrl+Up | Transpose up 1 semitone |
| Ctrl+Down | Transpose down 1 semitone |
| Ctrl+Shift+C | Reset to C |
| Ctrl+Shift+G | Jump to G |
| Ctrl+Shift+D | Jump to D |
| Ctrl+Shift+A | Jump to A |
| Ctrl+Shift+E | Jump to E |
| Ctrl+Shift+F | Jump to F |

---

## Recording & Streaming

| Hotkey | Action |
|--------|--------|
| Ctrl+R | Toggle recording |
| Ctrl+S | Toggle streaming |
| Ctrl+P | Pause recording |
| Ctrl+M | Mute audio |

---

## Layout Customization

### Adjusting Source Positions

Each master scene stores source positions in `horizontal-masters.json`. To customize:

1. Open OBS → Unlock sources
2. Drag/resize sources as needed
3. Lock sources when satisfied
4. Export scene collection for backup

### Creating Custom Masters

To add a custom master scene:

1. Duplicate an existing master scene
2. Rename with 📺 prefix and hotkey assignment
3. Modify sources and positions
4. Add hotkey in Settings → Hotkeys

---

## Transition Settings

| Transition | Duration | Use Case |
|------------|----------|----------|
| Fade | 300ms | Default smooth |
| Cut | 0ms | Instant switch |
| Slide | 500ms | Dramatic reveals |
| Stinger | 500ms | Branded transitions |

---

## Performance Notes

- **GPU Usage:** ~15-25% with all widgets active
- **Memory:** ~4GB for full scene collection
- **NDI Bandwidth:** ~200Mbps for all 8 widgets
- **Recommended:** 16GB RAM, RTX 3060+/RX 6700+ GPU

---

## Related Documentation

- [SCENE_ARCHITECTURE_GUIDE.md](SCENE_ARCHITECTURE_GUIDE.md) - Full architecture
- [VERTICAL_STREAMING_GUIDE.md](VERTICAL_STREAMING_GUIDE.md) - 9:16 scenes
- [ANIMATION_SYSTEM_GUIDE.md](ANIMATION_SYSTEM_GUIDE.md) - Move transitions

---

*Part of the SKOREQ OBS Dream Collection*
