# 🎬 SKOREQ Scene Collection Architecture Guide

> **Version:** 1.0.0  
> **EPIC:** SKOREQ-OBS-DREAM  
> **Story:** STORY-004  
> **Author:** ROXY AI Orchestrator

---

## Overview

The SKOREQ Scene Collection implements a **hierarchical nested scene architecture** that reduces scene count from 238+ to ~85 while maintaining full functionality and enabling powerful composition.

### Key Principles

1. **Atomic Sources** → Single-purpose sources (cameras, NDI widgets, captures)
2. **Nested Modules** → Reusable grouped sources for common arrangements
3. **Composition Scenes** → Multi-widget layouts with positioning
4. **Master Scenes** → Final broadcast-ready scenes with all elements

---

## Scene Hierarchy

```
📌 ==== CAMERAS ====
├── 📷 Sony A7IV (Main)
├── 📷 Sony FX30 (Overhead)
├── 📷 Elgato Facecam Pro (Face)
└── ...

📌 ==== NDI WIDGETS ====
├── 🎹 PianoWidget (NDI)
├── 🎸 FretboardWidget (NDI)
├── 🔵 CircleOfFifths (NDI)
└── ...

📌 ==== MODULES ====
├── 📦 Camera 3-Way
├── 📦 Piano + Fret Combo
├── 📦 Full Theory Display
└── ...

📌 ==== MASTERS ====
├── 📺 M1: Full Teaching Studio
├── 📺 M2: Close-Up Piano
├── 📺 M3: Guitar Focus
└── ...

📌 ==== VERTICAL ====
├── 📱 V1: TikTok Piano
├── 📱 V2: YouTube Shorts Guitar
└── ...
```

---

## Category Reference

### Separators (Type: `separator`)

Non-source entries used for visual organization in OBS scene list.

| Scene Name | Purpose |
|------------|---------|
| `📌 ==== CAMERAS ====` | Camera sources section |
| `📌 ==== NDI WIDGETS ====` | 8K Theater widget section |
| `📌 ==== CAPTURES ====` | Screen/window captures |
| `📌 ==== MODULES ====` | Nested scene modules |
| `📌 ==== COMPOSITION ====` | Multi-source layouts |
| `📌 ==== MASTERS ====` | Horizontal broadcast scenes |
| `📌 ==== VERTICAL ====` | Vertical format scenes |
| `📌 ==== UTILITY ====` | Overlays, backgrounds, utility |

### Cameras (Type: `dshow_input` / `v4l2_input`)

| Scene Name | Device | Resolution | Notes |
|------------|--------|------------|-------|
| `📷 Sony A7IV (Main)` | Decklink | 1080p60 | Main teaching camera |
| `📷 Sony FX30 (Overhead)` | Decklink | 1080p60 | Overhead keyboard/fretboard |
| `📷 Elgato Facecam Pro` | USB | 4K30 | Face cam for reactions |
| `📷 GoPro Hero 12 (Wide)` | USB | 1080p60 | Wide room shot |
| `📷 OAK-D Lite (AI)` | USB | 1080p30 | Hand tracking camera |
| `📷 Decklink 8K Pro Input 1` | Decklink | 4K60 | Primary capture |
| `📷 Decklink 8K Pro Input 2` | Decklink | 4K60 | Secondary capture |
| `📷 Decklink 8K Pro Input 3` | Decklink | 4K60 | Tertiary capture |

### NDI Widgets (Type: `ndi_source`)

| Scene Name | NDI Name | Widget URL | Purpose |
|------------|----------|------------|---------|
| `🎹 PianoWidget` | `MINDSONG-Piano` | `:5173/widgets/piano?ndi=true` | Virtual piano visualization |
| `🎸 FretboardWidget` | `MINDSONG-Fretboard` | `:5173/widgets/fretboard?ndi=true` | Guitar fretboard display |
| `🔵 CircleOfFifths` | `MINDSONG-COF` | `:5173/widgets/cof?ndi=true` | Circle of fifths |
| `📊 HarmonicProfile` | `MINDSONG-Harmonic` | `:5173/widgets/harmonic?ndi=true` | Chord analysis |
| `🎵 ScoreTab` | `MINDSONG-Score` | `:5173/widgets/score?ndi=true` | Sheet music/tab |
| `⏱️ Metronome` | `MINDSONG-Metronome` | `:5173/widgets/metronome?ndi=true` | Visual metronome |
| `🌀 BraidWidget` | `MINDSONG-Braid` | `:5173/widgets/braid?ndi=true` | Tonnetz visualization |
| `📐 TempoGeometry` | `MINDSONG-Tempo` | `:5173/widgets/tempo?ndi=true` | Tempo visualization |

### Captures (Type: `window_capture` / `xcomposite_input`)

| Scene Name | Target | Purpose |
|------------|--------|---------|
| `🖥️ Ableton Live` | Ableton Live window | DAW display |
| `🖥️ Logic Pro` | Logic Pro window | DAW display |
| `🖥️ MuseScore` | MuseScore window | Score editing |
| `🖥️ Browser (Theory)` | Firefox/Chrome | Theory references |
| `🖥️ Full Desktop` | Desktop capture | Fallback |

### Modules (Type: `scene` - nested)

Reusable building blocks that can be referenced by composition and master scenes.

| Module Name | Contains | Use Case |
|-------------|----------|----------|
| `📦 Camera 3-Way` | 3 cameras in split | Multi-angle view |
| `📦 Camera PiP` | Main + corner overlay | Picture-in-picture |
| `📦 Piano + Fret Combo` | Piano + Fretboard stacked | Multi-instrument |
| `📦 Theory Triad` | COF + Harmonic + Braid | Theory analysis |
| `📦 Full Theory Display` | All 8 theory widgets | Complete theory |
| `📦 Hands Close-Up` | OAK-D + Overhead | Hand technique |
| `📦 Score + DAW` | MuseScore + Ableton | Composition view |
| `📦 Widget Carousel` | Rotating widget display | Auto-cycling |
| `📦 Caption Region` | LocalVocal subtitle area | Live captions |
| `📦 Lower Third` | Name/topic overlay | Broadcast graphics |

---

## Composition Scenes

These scenes arrange modules into specific teaching layouts:

| Scene Name | Layout | Components |
|------------|--------|------------|
| `🎼 Piano Lesson` | 60/40 split | Camera + PianoWidget |
| `🎸 Guitar Lesson` | 60/40 split | Camera + FretboardWidget |
| `🎼 Theory Deep Dive` | Grid | Camera + Theory Triad |
| `📝 Score Study` | Vertical split | Score + Camera + Piano |
| `🎬 Full Production` | Complex | All cameras + all widgets |

---

## Master Scenes (Horizontal 📺)

Final broadcast-ready scenes with hotkey assignments:

| Scene | Hotkey | Layout | Use Case |
|-------|--------|--------|----------|
| `📺 M1: Full Teaching Studio` | F1 | Main cam + widget sidebar | Default teaching |
| `📺 M2: Close-Up Piano` | F2 | Overhead + large piano | Piano technique |
| `📺 M3: Guitar Focus` | F3 | Main + large fretboard | Guitar lessons |
| `📺 M4: Theory Breakdown` | F4 | Camera + theory triad | Music theory |
| `📺 M5: Multi-Instrument` | F5 | Split piano + guitar | Comparison |
| `📺 M6: Full Widget Array` | F6 | Small cam + all widgets | Analysis mode |
| `📺 M7: DAW Production` | F7 | Screen capture focus | Production |
| `📺 M8: Interview Mode` | F8 | Dual camera split | Guest/collab |

---

## Vertical Scenes (📱)

9:16 aspect ratio scenes for mobile platforms:

| Scene | Platform | Layout |
|-------|----------|--------|
| `📱 V1: TikTok Piano` | TikTok | Center piano + top face |
| `📱 V2: YouTube Shorts Guitar` | Shorts | Fretboard + bottom face |
| `📱 V3: Instagram Reels Theory` | Reels | COF focus + overlay |
| `📱 V4: Mobile Full Teaching` | General | Vertical full production |
| `📱 V5: Vertical Multi-Cam` | General | 3-way vertical split |

---

## Utility Scenes

Support scenes for overlays and backgrounds:

| Scene | Type | Purpose |
|-------|------|---------|
| `🎨 Background - Dark Studio` | Color source | Dark bg |
| `🎨 Background - Gradient` | Image | Professional gradient |
| `🎨 Background - Transparent` | None | For compositing |
| `🏷️ Branding Overlay` | Image + text | Logo/watermark |
| `📝 Caption Display` | Text | LocalVocal output |
| `⏸️ BRB Screen` | Image | Break screen |

---

## Overlay Groups

Educational overlays managed as groups:

### Scale Overlays (12 keys × 7 modes = 84 images)

```
📁 overlays/scales/
├── C-major.png, C-minor.png, C-dorian.png...
├── D-major.png, D-minor.png, D-dorian.png...
└── ...
```

### Interval Overlays (12 intervals)

```
📁 overlays/intervals/
├── minor-2nd.png
├── major-2nd.png
├── minor-3rd.png
└── ...
```

### Circle of Fifths Overlays (Key highlighting)

```
📁 overlays/cof/
├── cof-C-highlight.png
├── cof-G-highlight.png
└── ...
```

---

## Key Transposition System

The fretboard widget uses the **move_source_filter** for animated key changes:

### Transposition Mechanics

- Each semitone shift = 160px horizontal movement
- Duration: 1300ms with cubic easing
- Direction: Left for sharps, Right for flats

### Hotkeys

| Hotkey | Action |
|--------|--------|
| `Ctrl+Up` | Transpose up 1 semitone |
| `Ctrl+Down` | Transpose down 1 semitone |
| `Ctrl+1` through `Ctrl+6` | Shift by interval |
| `Ctrl+0` | Reset to C |

### Simultaneous Move Chains

For coordinated animations across multiple widgets:

```json
{
  "simultaneous_move_chain": {
    "name": "Full Key Shift",
    "targets": [
      "🎸 FretboardWidget",
      "🎹 PianoWidget", 
      "🔵 CircleOfFifths"
    ],
    "animation": "key_transpose",
    "sync": true
  }
}
```

---

## Animation Presets

Reusable animations defined in `animation-presets.json`:

| Preset | Type | Duration | Use |
|--------|------|----------|-----|
| `fade_in` | Opacity | 300ms | Source reveal |
| `fade_out` | Opacity | 300ms | Source hide |
| `zoom_in` | Scale | 400ms | Focus attention |
| `zoom_pulse` | Scale | 300ms | Highlight change |
| `slide_left` | Position | 500ms | Lateral transition |
| `bounce_in` | Combined | 500ms | Energetic entry |
| `key_transpose` | Position | 1300ms | Key changes |

---

## Scene Import Process

### 1. Import Base Collection

```bash
# Copy scene collection to OBS
cp ~/.roxy/obs-portable/scenes/skoreq-scenes.json \
   ~/.config/obs-studio/basic/scenes/
```

### 2. Configure NDI Sources

For each NDI widget:
1. Open OBS → Sources
2. Find NDI source
3. Properties → Select NDI name (e.g., `MINDSONG-Piano`)
4. Set bandwidth to "Highest"

### 3. Configure Cameras

1. For Decklink sources: Select correct input
2. For USB cameras: Select device, set resolution
3. Apply color correction filters as needed

### 4. Import Overlays

```bash
# Copy overlay images
cp -r ~/.roxy/obs-portable/overlays/* \
      ~/.config/obs-studio/assets/overlays/
```

### 5. Configure Hotkeys

OBS → Settings → Hotkeys:
- F1-F8: Master scenes
- Ctrl+1-9: Quick widget toggles
- Ctrl+Up/Down: Key transposition

---

## Performance Considerations

### Memory Management

- Keep source count under 100 for smooth performance
- Use nested scenes to reduce duplicate source instances
- Disable unused NDI sources when not streaming

### GPU Optimization

- Enable hardware decoding for NDI
- Use "Lanczos" scaling for best quality
- Enable hardware encoding (NVENC/VAAPI)

### Network (NDI)

- Ensure 1Gbps+ connection between widget server and OBS
- Use "Lowest" latency setting for live performance
- Monitor NDI bandwidth in OBS stats

---

## Troubleshooting

### NDI Source Not Appearing

1. Check if widget server is running
2. Verify NDI name matches exactly
3. Restart NDI runtime: `sudo systemctl restart avahi-daemon`

### Scene Transition Lag

1. Reduce animation duration
2. Check GPU utilization
3. Disable filters on hidden sources

### Key Transposition Not Working

1. Verify move_source_filter is applied
2. Check hotkey bindings
3. Ensure filter parameters match documentation

---

## Related Documentation

- [NDI_WIDGET_ARCHITECTURE.md](NDI_WIDGET_ARCHITECTURE.md) - Widget bridge setup
- [AI_PLUGIN_CONFIGURATION.md](AI_PLUGIN_CONFIGURATION.md) - LocalVocal/Background removal
- [ROXY_OBS_VOICE_CONTROL.md](ROXY_OBS_VOICE_CONTROL.md) - Voice commands

---

*This documentation is part of the SKOREQ OBS Dream Collection EPIC*
