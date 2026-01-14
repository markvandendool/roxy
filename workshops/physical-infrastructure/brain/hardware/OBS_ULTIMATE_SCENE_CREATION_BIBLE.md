# 🎬 THE ULTIMATE OBS SCENE CREATION BIBLE
## Roxy's Definitive Guide to Scene Organization, Performance & Workflow Mastery
### Version 1.0 | January 2026

---

## 📋 TABLE OF CONTENTS

1. [Philosophy & Core Principles](#philosophy--core-principles)
2. [Naming Convention System](#naming-convention-system)
3. [Scene Architecture Patterns](#scene-architecture-patterns)
4. [Horizontal/Vertical Scene Harmony](#horizontalvertical-scene-harmony)
5. [Performance Optimization Secrets](#performance-optimization-secrets)
6. [Source Management Best Practices](#source-management-best-practices)
7. [Filter Chain Architecture](#filter-chain-architecture)
8. [Transition System Design](#transition-system-design)
9. [Plugin Integration Guide](#plugin-integration-guide)
10. [Scene Tree Organization](#scene-tree-organization)
11. [Multiview & Canvas Strategy](#multiview--canvas-strategy)
12. [Hotkey Architecture](#hotkey-architecture)
13. [Migration Checklist](#migration-checklist)

---

## 🧠 PHILOSOPHY & CORE PRINCIPLES

### The Three Laws of OBS Mastery

1. **Source Once, Reference Everywhere**
   - Create each source ONCE as a base scene
   - Nest that scene everywhere else you need it
   - Changes propagate automatically

2. **Naming Predicts Behavior**
   - Anyone should understand a scene's purpose from its name
   - Include canvas type, content type, and modifiers

3. **Performance is a Feature**
   - Invisible sources still consume resources
   - Every filter adds GPU load
   - Plan for scalability

### Mental Model: The Source Pyramid

```
                    ┌─────────────────┐
                    │  OUTPUT SCENES  │  ← What goes LIVE
                    │  (Horizontal)   │
                    └────────┬────────┘
                             │
               ┌─────────────┴─────────────┐
               │   COMPOSITE SCENES        │  ← Combines multiple
               │   (Mix of nested scenes)  │     nested scenes
               └─────────────┬─────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │          BUILDING BLOCK SCENES          │  ← Single purpose
        │  (Camera, Overlay, Widget, Background)  │     components
        └────────────────────┬────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              │       RAW SOURCES           │  ← Actual captures
              │  (NDI, Decklink, Browser)   │
              └─────────────────────────────┘
```

---

## 📝 NAMING CONVENTION SYSTEM

### The Standard Format

```
[PREFIX]_[TYPE]_[SUBJECT]_[MODIFIER]
```

### Prefixes (First Character/Word)

| Prefix | Meaning | Example |
|--------|---------|---------|
| `H_` | Horizontal (16:9) | `H_Canon_Main` |
| `V_` | Vertical (9:16) | `V_Canon_Main` |
| `SQ_` | Square (1:1) | `SQ_Promo_Clip` |
| `RAW_` | Unprocessed source | `RAW_Decklink_1` |
| `BASE_` | Foundation scene for nesting | `BASE_Camera_Canon` |
| `MIX_` | Composite/mix scene | `MIX_MultiCam_Guitar` |
| `UI_` | Interface element | `UI_Countdown_Timer` |
| `OVL_` | Overlay | `OVL_Logo_Watermark` |
| `BG_` | Background | `BG_Animated_Loop` |
| `DSK_` | Downstream keyer | `DSK_Lower_Third` |
| `---` | Folder separator | `--- CAMERAS ---` |

### Type Codes

| Code | Content Type | Example |
|------|--------------|---------|
| `CAM` | Camera | `H_CAM_Canon_Main` |
| `NDI` | NDI Source | `H_NDI_iPhone_Overhead` |
| `CAP` | Capture Card | `H_CAP_Decklink_1` |
| `SCR` | Screen Capture | `H_SCR_Mac_Display` |
| `BRW` | Browser Source | `H_BRW_Alerts_Stream` |
| `MED` | Media (Video/Audio) | `H_MED_Intro_Animation` |
| `TXT` | Text | `UI_TXT_Song_Title` |
| `IMG` | Image | `BG_IMG_Stage_Backdrop` |

### Subject Naming Rules

1. **Use Title Case** - `Canon_Main` not `canon_main`
2. **Be Specific** - `Canon_R5_Overhead` not just `Camera_2`
3. **Include Position** - `_TopLeft`, `_Center`, `_Overhead`
4. **Include Function** - `_Tutorial`, `_Performance`, `_CloseUp`

### Modifier Codes

| Modifier | Meaning |
|----------|---------|
| `_LIVE` | Currently active variation |
| `_PROXY` | Placeholder/proxy scene |
| `_FILTERED` | Has filter chain applied |
| `_CLEAN` | No overlays/filters |
| `_v2`, `_v3` | Version numbers |
| `_BACKUP` | Backup/fallback version |

### Examples in Practice

**From Harry_Elgato (Old Style):**
```
Canon Main 1                    → Unclear purpose
VERT Canon Main 1              → Vertical is good, but inconsistent
Roku Fretboard 9               → Version number unclear
```

**New Bible Style:**
```
H_CAM_Canon_Main_Performance   → Clear: Horizontal, Camera, Canon, for Performance
V_CAM_Canon_Main_Performance   → Its vertical partner
BASE_FRET_Roku_Display         → Base fretboard from Roku
H_MIX_Fret_Canon_Lesson        → Horizontal mix of fretboard + canon for lessons
```

---

## 🏗️ SCENE ARCHITECTURE PATTERNS

### Pattern 1: The Camera Block

Every camera gets a consistent treatment:

```
RAW_[Camera]           ← Actual capture, no processing
  └── BASE_[Camera]    ← With standard filters (color correction, crop)
        └── H_CAM_[Camera]_[Purpose]  ← Horizontal output version
        └── V_CAM_[Camera]_[Purpose]  ← Vertical output version
```

**Example:**
```
RAW_Canon_R5_Decklink
  └── BASE_Canon_R5_Corrected
        ├── H_CAM_Canon_Main_Performance
        ├── H_CAM_Canon_Main_Teaching  
        ├── V_CAM_Canon_Main_Performance
        └── V_CAM_Canon_Main_Teaching
```

### Pattern 2: The Composite Layer

For scenes that mix multiple sources:

```
MIX_[Purpose]_[Layout]
  ├── [Scene Reference: Camera 1]
  ├── [Scene Reference: Camera 2]
  ├── [Scene Reference: Overlay]
  └── [Scene Reference: Background]
```

**Why This Works:**
- Moving Camera 1 in its BASE scene moves it EVERYWHERE
- Changing the color grade propagates to all uses
- Swap cameras by changing one reference

### Pattern 3: The Downstream Keyer Pattern

Persistent overlays that appear over everything:

```
DSK_Master_Output
  ├── [Current Scene Reference]  ← This switches
  ├── OVL_Logo_Watermark         ← Always visible
  ├── OVL_Social_Handle          ← Always visible
  └── UI_Alert_Box               ← Triggered overlays
```

### Pattern 4: The Widget Library

Reusable UI components:

```
--- WIDGETS ---
  ├── UI_Countdown_5min
  ├── UI_Countdown_10min
  ├── UI_Song_Title_Display
  ├── UI_Chord_Diagram
  ├── UI_Scale_Visualizer
  └── UI_Chat_Box
```

---

## 🔄 HORIZONTAL/VERTICAL SCENE HARMONY

### The Twin Scene Principle

For EVERY horizontal scene intended for output, create a matching vertical scene.

### Naming Convention for Pairs

```
H_[Name]  →  V_[Name]
```

They share the same name, only the prefix changes.

### Implementation Strategy

**Method A: Separate Transforms (Recommended)**
```
H_CAM_Canon_Main
  └── [BASE_Canon_Corrected] + Transform for 16:9 crop/position

V_CAM_Canon_Main  
  └── [BASE_Canon_Corrected] + Transform for 9:16 crop/position
```

Same BASE, different transforms.

**Method B: Vertical Canvas Plugin**
```
H_CAM_Canon_Main          ← Main canvas (2560x1440)
[Vertical Canvas Plugin]  ← Renders to 1080x1920 automatically
```

### The Harmony Checklist

| Check | Description |
|-------|-------------|
| ✅ | Every H_ scene has a V_ partner |
| ✅ | Both reference the same BASE source |
| ✅ | Transforms are appropriate for each canvas |
| ✅ | Filters are on BASE, not individual H_/V_ |
| ✅ | Changes to BASE affect both H_ and V_ |

### Vertical Canvas Plugin Integration

```
Horizontal Output: 2560 x 1440 (Main Canvas)
Vertical Output:   1080 x 1920 (Via Vertical Canvas Plugin)

Scene Structure:
  H_MIX_Performance_Main
    ├── H_CAM_Canon_Main
    ├── H_CAM_Overhead_Fret
    └── OVL_Logo

  [Vertical Canvas Source]
    └── References: V_MIX_Performance_Main
          ├── V_CAM_Canon_Main
          ├── V_CAM_Overhead_Fret
          └── OVL_Logo_Vertical
```

---

## ⚡ PERFORMANCE OPTIMIZATION SECRETS

### The Hidden Resource Drains

1. **Invisible Scenes Still Render**
   - Nested scenes render even when parent is invisible
   - Solution: Use "Show/Hide" transitions or disable sources

2. **Browser Sources Are Expensive**
   - Each browser source = separate Chromium process
   - Consolidate multiple widgets into one HTML page
   - Use "Shutdown source when not visible" option

3. **Filter Accumulation**
   - Filters on nested scenes stack multiplicatively
   - 3 scenes with 3 filters each = 9 filter operations
   - Apply filters at the LOWEST level possible

### Performance Configuration

**Settings → Advanced:**
```
Process Priority: Above Normal (not High)
Color Format: NV12 (faster) or I444 (quality)
Color Space: 709 (standard) or Rec. 2100 (HDR)
```

**Settings → Video:**
```
Base Canvas: Match monitor (don't upscale)
Output: Can be lower than base
FPS: 30 for teaching, 60 for gaming
```

### The Performance Testing Protocol

1. Open **View → Stats**
2. Monitor these numbers:
   - **Encoding lag**: Should be 0%
   - **Rendering lag**: Should be < 1%
   - **Dropped frames**: Should be 0

3. Add scenes one at a time, check impact
4. Profile individual sources with Task Manager

### Source Optimization Checklist

| Source Type | Optimization |
|-------------|--------------|
| Browser | Enable "Shutdown when not visible" |
| Video Capture | Use lowest acceptable resolution |
| NDI | Enable "Low Bandwidth Mode" if distant |
| Media | Pre-render effects, don't use live filters |
| Text | Use GDI+ for simple, FreeType2 for complex |
| Image | Pre-scale to exact output size |

### The Rule of Hidden Sources

```
⚠️ WARNING: A hidden source STILL USES RESOURCES

Invisible ≠ Disabled ≠ Removed

Resource Usage:
  - Visible: 100%
  - Invisible: ~80% (still rendering)
  - Disabled: ~20% (still initialized)
  - Removed: 0%

Best Practice:
  - Use scenes as "pages" - switch don't layer
  - Disable sources you won't use for >5 minutes
  - Remove sources you won't use this stream
```

---

## 🎨 SOURCE MANAGEMENT BEST PRACTICES

### The Golden Rules

1. **Never Duplicate - Always Reference**
   ```
   BAD:  Create new camera source in each scene
   GOOD: Create one BASE scene, nest it everywhere
   ```

2. **Groups vs Nested Scenes**
   ```
   Groups:  Good for layout within ONE scene
   Nested:  Good for reuse across MULTIPLE scenes
   
   Use Groups for:
     - Temporary arrangements
     - One-off layouts
     - Quick experiments
   
   Use Nested Scenes for:
     - Camera sources
     - Recurring overlays
     - Shared components
   ```

3. **Source Naming Matches Scene Naming**
   ```
   Scene: BASE_Canon_R5_Corrected
   Source inside: NDI_Canon_R5_Raw (matches the camera)
   ```

### Source Hierarchy

```
Recommended Z-Order (bottom to top):
  1. Backgrounds (BG_)
  2. Main Content (CAM_, SCR_)
  3. Supporting Content (UI_, secondary cameras)
  4. Overlays (OVL_)
  5. Downstream Keys (DSK_)
  6. Alerts/Popups (ALERT_)
```

### The 30-Second Source Test

Before adding any source, ask:
1. Does this source already exist? (Check BASE scenes)
2. Will I need this in multiple scenes? (Make it a BASE)
3. Is this a temporary test? (Use Group, delete later)
4. What's the resource cost? (Check Stats panel)

---

## 🔧 FILTER CHAIN ARCHITECTURE

### Filter Order Matters

```
Recommended Filter Order (Effect Filters):
  1. Crop/Pad (shape the source first)
  2. Color Correction (adjust colors)
  3. Sharpen (if needed)
  4. LUT (color grading)
  5. Scaling (output size)
  6. Image Mask (if needed)

Audio Filter Order:
  1. Noise Suppression (clean first)
  2. Noise Gate (cut silence)
  3. Compressor (level dynamics)
  4. Limiter (prevent clipping)
  5. Gain (final level adjustment)
```

### The Filter Placement Principle

```
Apply filters at the LOWEST possible level:

❌ BAD:  Filters on H_CAM_Canon and V_CAM_Canon
✅ GOOD: Filters on BASE_Canon (inherited by both)

Why:
  - Less duplication
  - One place to adjust
  - Better performance
```

### Move Transition Filter Magic

The Move Transition plugin enables powerful animations:

```
Move Source Filter Setup:
  - Start: Transform at Scene A position
  - End: Transform at Scene B position
  - Curve: Cubic for smooth acceleration
  - Duration: 500-800ms for natural feel

Pro Tip: Add "Move Value" filter to animate filter properties:
  - Fade blur in/out
  - Color correction shifts
  - Scale changes
```

### Filter Presets System

Create saved filter chains for consistency:

```
Preset: "Standard Camera Grade"
  1. Color Correction: Contrast +0.1, Saturation +0.05
  2. Sharpen: 0.08
  3. LUT: Custom_Cinematic.cube

Preset: "Teaching Clarity"
  1. Color Correction: Brightness +0.15
  2. Sharpen: 0.12
  3. No LUT (maximum clarity)

Preset: "Performance Mood"
  1. Color Correction: Contrast +0.2, Saturation +0.15
  2. LUT: Moody_Performance.cube
  3. Vignette (via shader filter)
```

---

## 🔀 TRANSITION SYSTEM DESIGN

### Transition Types & Use Cases

| Transition | Best For | Duration |
|------------|----------|----------|
| Cut | Quick changes, multicam | 0ms |
| Fade | Soft mood changes | 300-500ms |
| Swipe | Revealing new content | 400-600ms |
| Stinger | Branded transitions | 500-1000ms |
| Move | Same source, new position | 500-800ms |

### Transition Table Setup

The Transition Table plugin (by Exeldro) lets you define:

```
From Scene          To Scene            Transition
H_CAM_Canon_Main    H_CAM_Overhead      Move (500ms)
H_CAM_Any           H_MIX_Teaching      Fade (400ms)  
H_MIX_Teaching      H_CAM_Any           Swipe Left (500ms)
*                   UI_Break_Screen     Stinger (800ms)
```

### Move Transition Best Practices

```
Source Matching Rules (in order of preference):
  1. Contains: "Camera" matches "Camera 1", "Guitar Camera"
  2. Numbers removed: "Cam 1" matches "Cam 2"
  3. Last word removed: "Main Cam" matches "Main View"

⚠️ For Move to work:
  - Sources must exist in BOTH scenes
  - Sources must have compatible bounding boxes
  - Transform types must match
```

### The Seamless Switch Pattern

For invisible transitions between similar scenes:

```
H_CAM_Canon_Main_A  →  H_CAM_Canon_Main_B

Both scenes contain same BASE camera, different overlays.
Move transition slides shared camera while fading overlays.
Result: Viewer sees overlay change, camera stays put.
```

---

## 🔌 PLUGIN INTEGRATION GUIDE

### Essential Plugin Stack (Installed)

| Plugin | Purpose | Key Feature |
|--------|---------|-------------|
| Move Transition | Animation | Source-aware transitions |
| Advanced Scene Switcher | Automation | Rule-based scene changes |
| Vertical Canvas | Multiplatform | 9:16 output from 16:9 |
| Source Dock | Organization | Quick source preview |
| obs-advanced-masks | Effects | Complex masking |
| obs-stroke-glow-shadow | Effects | Text/source effects |
| obs-retro-effects | Effects | VHS, CRT looks |
| obs-noise | Effects | Noise overlays |

### Scene Tree Plugin (TO BE INSTALLED)

**Plugin:** Scene Tree View v0.1.9
**Source:** https://github.com/TheThirdRail/scene-tree-view

**Features:**
- Hierarchical folder organization
- Drag-and-drop scene reordering
- Per-scene custom transitions
- Scene collection support

**Installation (Linux - Build from Source):**
```bash
# Dependencies
sudo apt install cmake ninja-build qt6-base-dev

# Build
cd /tmp/scene-tree-view
mkdir build && cd build
cmake -S .. -B . -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release
sudo cmake --install . --config Release

# Enable in OBS
View → Docks → Scene Tree View
```

### Advanced Scene Switcher Automations

```
Example Rules:

Rule 1: "Switch to Break on Idle"
  If: No scene change for 30 minutes
  Then: Switch to UI_Break_BRB

Rule 2: "Auto Vertical Mirror"
  If: Scene changed to H_*
  Then: Switch Vertical Canvas to matching V_*

Rule 3: "Audio Reactive"
  If: Audio level > -3dB for 10 seconds
  Then: Enable OVL_Audio_Peak_Warning
```

---

## 🗂️ SCENE TREE ORGANIZATION

### Folder Structure (Using Scene Tree Plugin)

```
📁 OUTPUT
  ├── H_LIVE_Main_Output
  ├── V_LIVE_Main_Output
  └── H_Clean_Feed

📁 CAMERAS
  ├── 📁 Canon
  │   ├── RAW_Canon_R5
  │   ├── BASE_Canon_R5
  │   ├── H_CAM_Canon_Main
  │   └── V_CAM_Canon_Main
  ├── 📁 Overhead
  │   ├── RAW_Overhead_Cam
  │   ├── BASE_Overhead
  │   ├── H_CAM_Overhead_Fret
  │   └── V_CAM_Overhead_Fret
  └── 📁 NDI
      ├── RAW_NDI_iPhone
      └── BASE_NDI_iPhone

📁 COMPOSITIONS
  ├── 📁 Teaching
  │   ├── H_MIX_Lesson_Standard
  │   ├── H_MIX_Lesson_Fretboard
  │   └── V_MIX_Lesson_Standard
  ├── 📁 Performance
  │   ├── H_MIX_Perform_MultiCam
  │   └── V_MIX_Perform_MultiCam
  └── 📁 Specialty
      ├── H_MIX_Scale_Builder
      └── H_MIX_Chord_Calendar

📁 OVERLAYS
  ├── OVL_Logo_Watermark
  ├── OVL_Social_Handles
  ├── OVL_Lower_Third
  └── OVL_Song_Title

📁 UI ELEMENTS
  ├── UI_Countdown_Timer
  ├── UI_Break_BRB
  ├── UI_Ending_Screen
  └── UI_Alert_Box

📁 BACKGROUNDS
  ├── BG_Studio_Default
  ├── BG_Animated_Loop
  └── BG_Color_Solid

📁 SYSTEM
  ├── DSK_Master
  ├── Vertical Canvas PROXY
  └── Calibration
```

### Folder Naming with Separators

Without Scene Tree plugin, use separator scenes:

```
----- CAMERAS -----
H_CAM_Canon_Main
V_CAM_Canon_Main
H_CAM_Overhead_Fret
----- COMPOSITIONS -----
H_MIX_Teaching_Standard
...
```

The `-----` prefix keeps separators at top when sorted.

---

## 📺 MULTIVIEW & CANVAS STRATEGY

### Multiview Setup

```
Multiview Layout (8-source):
┌─────────────────┬─────────────────┐
│  H_LIVE_Output  │  V_LIVE_Output  │
├────────┬────────┼────────┬────────┤
│  CAM1  │  CAM2  │  CAM3  │  CAM4  │
├────────┼────────┼────────┼────────┤
│  MIX1  │  MIX2  │  BREAK │ ENDING │
└────────┴────────┴────────┴────────┘
```

### Multi-Canvas Strategy

```
Canvas 1: Main Output (2560x1440 or 1920x1080)
  - All H_ scenes
  - Primary streaming canvas
  
Canvas 2: Vertical Output (1080x1920)
  - Via Vertical Canvas plugin
  - All V_ scenes
  - TikTok/Reels/Shorts output

Canvas 3: Recording Only (optional)
  - Higher resolution
  - Different crop for VOD
```

### Virtual Camera Outputs

```
Main Virtual Cam: H_LIVE_Output
  - For Zoom calls
  - For Discord streaming
  
Secondary Virtual Cam: Specific scene
  - Dedicated camera view
  - No overlays
```

---

## ⌨️ HOTKEY ARCHITECTURE

### Hotkey Categories

| Category | Keys | Example |
|----------|------|---------|
| Scene Switch | F1-F12 | F1 = Main, F2 = Teaching |
| Source Toggle | Ctrl+1-9 | Ctrl+1 = Toggle Logo |
| Transitions | Numpad | Num1 = Cut, Num2 = Fade |
| Filters | Alt+F1-F12 | Alt+F1 = Enable Blur |
| Recording | Ctrl+Shift | Ctrl+Shift+R = Record |

### Recommended Layout

```
SCENE SWITCHING (F-Keys):
  F1  = H_LIVE_Main_Output
  F2  = H_MIX_Teaching_Standard  
  F3  = H_MIX_Teaching_Fretboard
  F4  = H_MIX_Performance
  F5  = UI_Break_BRB
  F6  = UI_Ending

QUICK CAMERAS (Ctrl + Number):
  Ctrl+1 = H_CAM_Canon_Main
  Ctrl+2 = H_CAM_Overhead_Fret
  Ctrl+3 = H_CAM_Wide
  Ctrl+4 = H_CAM_Detail

TOGGLE OVERLAYS (Alt + Number):
  Alt+1 = Toggle OVL_Logo
  Alt+2 = Toggle OVL_Song_Title
  Alt+3 = Toggle OVL_Chord_Diagram
  Alt+4 = Toggle UI_Chat

TRANSITIONS (Numpad):
  Num1 = Cut Transition
  Num2 = Fade Transition
  Num3 = Move Transition
  Num* = Stinger Transition

STREAMING (Ctrl+Shift):
  Ctrl+Shift+S = Start/Stop Stream
  Ctrl+Shift+R = Start/Stop Recording
  Ctrl+Shift+V = Start Virtual Camera
```

---

## ✅ MIGRATION CHECKLIST

### Phase 1: Preparation
- [ ] Backup current scene collection
- [ ] Export all settings
- [ ] Document current hotkeys
- [ ] Screenshot current layout

### Phase 2: Foundation
- [ ] Create folder separator scenes
- [ ] Create RAW_ scenes for all capture sources
- [ ] Create BASE_ scenes with filters
- [ ] Verify sources work

### Phase 3: Horizontal Canvas
- [ ] Create H_CAM_ scenes from BASE_
- [ ] Create H_MIX_ composition scenes
- [ ] Create UI_ and OVL_ elements
- [ ] Test all H_ scene transitions

### Phase 4: Vertical Canvas
- [ ] Configure Vertical Canvas plugin
- [ ] Create V_CAM_ scenes from BASE_
- [ ] Create V_MIX_ compositions
- [ ] Verify H_/V_ parity

### Phase 5: Polish
- [ ] Configure Transition Table
- [ ] Set up all hotkeys
- [ ] Configure Advanced Scene Switcher
- [ ] Set up multiview
- [ ] Document final setup

### Phase 6: Testing
- [ ] Test all scene transitions
- [ ] Verify no dropped frames
- [ ] Test recording
- [ ] Test streaming
- [ ] Verify vertical output
- [ ] Test virtual camera

---

## 📚 APPENDIX: HARRY_ELGATO ANALYSIS

### Original Scene Count: 238
### Identified Issues:
1. Inconsistent naming ("VERT" vs "Vert" vs "Vertical")
2. No clear hierarchy
3. Duplicate sources
4. Version numbers unclear
5. Purpose often ambiguous

### Scene Categories Found:
- Camera scenes: ~40
- Vertical scenes: ~29
- Fretboard/Teaching: ~25
- Composition scenes: ~50
- UI elements: ~20
- System/utility: ~15
- Unknown/legacy: ~59

### Recommended New Structure:
- **Target: 80-100 organized scenes**
- Consolidate duplicate cameras
- Remove unused legacy scenes
- Establish clear H_/V_ pairs
- Create BASE_ layer for reuse

---

## 📎 QUICK REFERENCE CARD

```
PREFIXES        TYPES           MODIFIERS
H_  Horizontal  CAM Camera      _LIVE   Active
V_  Vertical    NDI NDI         _CLEAN  No filters
SQ_ Square      CAP Capture     _v2     Version
RAW_ Raw        SCR Screen      _BACKUP Fallback
BASE_ Base      BRW Browser     _PROXY  Placeholder
MIX_ Composite  MED Media
UI_  Interface  TXT Text
OVL_ Overlay    IMG Image
BG_  Background
DSK_ Downstream

FILTER ORDER (Video)           FILTER ORDER (Audio)
1. Crop/Pad                    1. Noise Suppression
2. Color Correction            2. Noise Gate
3. Sharpen                     3. Compressor
4. LUT                         4. Limiter
5. Scaling                     5. Gain
6. Image Mask
```

---

*Created by Roxy for Harry's Ultimate Scene Collection Rebuild*
*This document is part of the Roxy Ecosystem - ~/.roxy/*

---

## 🔧 SCENE TREE PLUGIN STATUS UPDATE

### Current Situation (January 2026)

**Plugin:** Scene Tree View v0.1.9 by John Titor (TheThirdRail)
**Source:** https://github.com/TheThirdRail/scene-tree-view

**Platform Availability:**
| Platform | Status | Notes |
|----------|--------|-------|
| Windows x64 | ✅ Ready | Pre-built binaries available |
| macOS | ⚠️ Requires build | Universal binary support in source |
| Linux x86_64 | ⚠️ Requires build | No pre-built release currently |

### Linux Installation Options

**Option A: Build from Source (Recommended)**
Requires OBS development headers (libobs-dev conflicts with PPA):
```bash
# This may require manual SDK setup - PPA users see note below
sudo apt install cmake ninja-build qt6-base-dev

cd /tmp/scene-tree-view
mkdir build && cd build
cmake -S .. -B . -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build .
sudo cmake --install .
```

**Option B: Alternative - Use Separator Scenes (No Plugin)**
Without the plugin, organize using separator scenes:
```
--- [📁 CAMERAS] ---
H_CAM_Canon_Main
V_CAM_Canon_Main
--- [📁 COMPOSITIONS] ---
H_MIX_Teaching_Main
```

**Option C: Request Linux Build**
File an issue at: https://github.com/TheThirdRail/scene-tree-view/issues
Request pre-built Linux x86_64 release

### PPA Users Note
The OBS Studio PPA (`ppa:obsproject/obs-studio`) conflicts with `libobs-dev`.
Solutions:
1. Build OBS from source to get development headers
2. Use Flatpak OBS with extension system
3. Wait for plugin author to provide Linux builds

