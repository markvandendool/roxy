# SKOREQ OBS DREAM COLLECTION — Cursor Plan Mode Document

**Status:** PLAN MODE (NOT EXECUTABLE — Must translate to swarm tickets)  
**Epic ID:** SKOREQ-OBS-EPIC-001  
**Date Created:** 2026-01-09  
**Author:** Copilot Analysis Engine  
**Purpose:** Industry-shattering OBS scene collection integrating 8K Theater, AI plugins, NDI widgets, and NovaXe pedagogical system

---

## 🎯 EPIC VISION

Create the **most sophisticated music education streaming infrastructure ever built** — a unified OBS scene collection that:

1. **Integrates 8K Theater widgets** as independent NDI sources
2. **Leverages all AI plugins** (LocalVocal, Background Removal, obs-mcp)
3. **Preserves Harry_Elgato pedagogical architecture** while reducing complexity 66%
4. **Enables Claude/ROXY voice control** of scenes via MCP
5. **Supports dual H/V canvases** for multi-platform streaming
6. **Achieves real-time MIDI visualization** synced with KRONOS

---

## 📐 ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SKOREQ OBS DREAM COLLECTION                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    8K THEATER WIDGET NDI SOURCES                     │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  🎹 PianoWidget (NDI)    │  🎸 FretboardWidget (NDI)                │   │
│  │  🔗 BraidWidget (NDI)     │  ⭕ COFWidget (NDI)                      │   │
│  │  📊 HarmonicProfile (NDI) │  🎵 ScoreTabWidget (NDI)                 │   │
│  │  ⏱️ MetronomeWidget (NDI) │  🌀 TempoGeometryWidget (NDI)            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    AI PROCESSING LAYER                               │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  🗣️ LocalVocal (Whisper)  │  Real-time captions + translation       │   │
│  │  🧠 obs-mcp (Claude)       │  Voice/text scene control               │   │
│  │  👤 Background Removal     │  AI green screen                        │   │
│  │  🎬 Advanced Scene Switch  │  Intelligent macro automation           │   │
│  │  🔊 CleanStream           │  AI audio cleanup                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    COMPOSITION SCENES                                │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  📺 MASTER - Full Theory  │  Camera + Fret + Braid + COF            │   │
│  │  📺 MASTER - Scale Lesson │  Fretboard focus + interval overlays    │   │
│  │  📺 MASTER - Braid Study  │  Harmonic analysis mode                  │   │
│  │  📺 MASTER - Performance  │  Clean camera + minimal overlay          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    OUTPUT CANVASES                                   │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  🖥️ Horizontal (2560×1440) │  YouTube, Twitch                        │   │
│  │  📱 Vertical (1080×1920)   │  TikTok, Shorts, Reels                  │   │
│  │  🎬 8K Master (7680×4320)  │  Archive/Post-production                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 STORIES BREAKDOWN

### STORY 001: NDI Widget Bridge Infrastructure
**ID:** SKOREQ-OBS-EPIC-001-STORY-001  
**Points:** 5 (free-tier)  
**Priority:** critical  

**Problem:**  
8K Theater widgets (Piano, Fretboard, Braid, COF, etc.) currently render inside the browser. To use them in OBS as independent sources with transparency and animation, they need to be exposed as NDI streams.

**Scope:**
- Create NDI output wrapper for each 8K Theater widget
- Configure DistroAV/NDI Tools for Linux
- Establish NDI naming convention for widget discovery
- Test latency and sync with KRONOS

**Files in Scope:**
```
~/.roxy/obs-portable/config/ndi-widget-bridge.json
~/.roxy/mcp-servers/obs/ndi_bridge.py
docs/obs/NDI_WIDGET_ARCHITECTURE.md
```

**Acceptance Criteria:**
- [ ] Each widget visible as independent NDI source in OBS
- [ ] Alpha channel preserved for transparency
- [ ] Latency < 50ms from MIDI input to visual update
- [ ] NDI sources auto-discoverable on local network
- [ ] Documentation complete

---

### STORY 002: AI Plugin Configuration
**ID:** SKOREQ-OBS-EPIC-001-STORY-002  
**Points:** 3 (free-tier)  
**Priority:** high  

**Problem:**  
AI plugins (LocalVocal, Background Removal, Advanced Scene Switcher) are downloaded but not configured for the pedagogical use case.

**Scope:**
- Configure LocalVocal with music-optimized Whisper model
- Set up background removal with studio lighting profile
- Create Advanced Scene Switcher macros for common lesson patterns
- Configure CleanStream for verbal tic removal

**Files in Scope:**
```
~/.config/obs-studio/basic/profiles/SKOREQ/basic.ini
~/.config/obs-studio/plugin_config/obs-localvocal/config.json
~/.config/obs-studio/plugin_config/obs-backgroundremoval/config.json
~/.roxy/obs-portable/macros/advanced-scene-switcher.json
docs/obs/AI_PLUGIN_CONFIGURATION.md
```

**Acceptance Criteria:**
- [ ] LocalVocal producing captions with < 2s latency
- [ ] Background removal working without green screen
- [ ] At least 10 ASS macros for common transitions
- [ ] CleanStream configured for lesson-appropriate filtering
- [ ] Documentation with troubleshooting guide

---

### STORY 003: obs-mcp ROXY Integration
**ID:** SKOREQ-OBS-EPIC-001-STORY-003  
**Points:** 5 (free-tier)  
**Priority:** critical  

**Problem:**  
ROXY voice commands need to control OBS scenes seamlessly. The existing `mcp/mcp_obs.py` needs enhancement to match `obs-mcp` feature parity.

**Scope:**
- Upgrade ROXY MCP server with full OBS WebSocket API coverage
- Add voice command intents for scene switching
- Implement source visibility toggles
- Add filter trigger commands
- Create hotword detection for hands-free control

**Files in Scope:**
```
~/.roxy/mcp/mcp_obs.py
~/.roxy/mcp-servers/obs/server.py
~/.roxy/obs_skill.py
~/.roxy/voice_intents/obs_commands.yaml
docs/obs/ROXY_OBS_VOICE_CONTROL.md
```

**Acceptance Criteria:**
- [ ] "Hey ROXY, switch to scale scene" working
- [ ] "Show the braid" / "Hide the braid" toggles source
- [ ] "Start recording" / "Stop streaming" commands functional
- [ ] Filter triggers via voice ("Animate key shift up")
- [ ] Full WebSocket API coverage documented

---

### STORY 004: Scene Collection Architecture
**ID:** SKOREQ-OBS-EPIC-001-STORY-004  
**Points:** 8 (paid-tier)  
**Priority:** critical  

**Problem:**  
The Harry_Elgato collection has 238 scenes with significant duplication. Need to reduce to ~80 modular scenes while preserving all pedagogical functionality.

**Scope:**
- Create scene hierarchy following DREAM_SCENE_COLLECTION_RECOMMENDATION.md
- Implement emoji naming convention
- Build nested scenes for reusability
- Create groups for toggle states
- Migrate move_source_filters to new architecture

**Files in Scope:**
```
~/.config/obs-studio/basic/scenes/SKOREQ_Dream.json
~/.roxy/obs-portable/config/scene-manifest.json
~/.roxy/obs-portable/filters/key-transposition.json
~/.roxy/obs-portable/filters/animation-presets.json
docs/obs/SCENE_ARCHITECTURE_GUIDE.md
```

**Acceptance Criteria:**
- [ ] Total scene count ≤ 85
- [ ] All Harry_Elgato pedagogical features preserved
- [ ] Emoji naming convention applied consistently
- [ ] Nested scenes for fretboard, braid, COF working
- [ ] Move filters migrated and tested
- [ ] 66% reduction in duplicate sources

---

### STORY 005: Horizontal Canvas Master Scenes
**ID:** SKOREQ-OBS-EPIC-001-STORY-005  
**Points:** 5 (free-tier)  
**Priority:** high  

**Problem:**  
Need optimized master scenes for horizontal streaming (YouTube, Twitch) at 2560×1440.

**Scope:**
- Create 8 master scenes for different lesson types
- Configure optimal source arrangements
- Set up transition animations
- Create hotkey map

**Files in Scope:**
```
~/.config/obs-studio/basic/scenes/SKOREQ_Dream.json (master scenes section)
~/.roxy/obs-portable/layouts/horizontal-masters.json
~/.roxy/obs-portable/hotkeys/master-scene-hotkeys.json
docs/obs/HORIZONTAL_LAYOUT_GUIDE.md
```

**Master Scenes:**
1. 📺 MASTER - Full Theory (Camera + Fret + Braid + COF)
2. 📺 MASTER - Scale Lesson (Fretboard focus)
3. 📺 MASTER - Chord Study (Braid focus)
4. 📺 MASTER - Circle Study (COF focus)
5. 📺 MASTER - Performance (Clean camera)
6. 📺 MASTER - Song Analysis (Score + Fretboard)
7. 📺 MASTER - Countdown/BRB
8. 📺 MASTER - Calibration

**Acceptance Criteria:**
- [ ] All 8 master scenes functional
- [ ] Hotkeys F1-F8 assigned
- [ ] Transitions smooth (< 1300ms)
- [ ] No orphan sources
- [ ] Performance < 30% CPU at 60fps

---

### STORY 006: Vertical Canvas Scenes
**ID:** SKOREQ-OBS-EPIC-001-STORY-006  
**Points:** 3 (free-tier)  
**Priority:** medium  

**Problem:**  
Vertical content for TikTok/Shorts/Reels requires separate 1080×1920 scenes.

**Scope:**
- Create vertical variants of master scenes
- Configure Vertical Canvas plugin
- Set up dual-canvas output

**Files in Scope:**
```
~/.config/obs-studio/basic/scenes/SKOREQ_Dream.json (vertical scenes section)
~/.roxy/obs-portable/layouts/vertical-masters.json
~/.config/obs-studio/plugin_config/vertical-canvas/config.json
docs/obs/VERTICAL_STREAMING_GUIDE.md
```

**Vertical Scenes:**
1. 📱 VERT - Camera Only
2. 📱 VERT - Camera + Fret
3. 📱 VERT - Camera + Braid
4. 📱 VERT - Braid Only
5. 📱 VERT - Full Lesson

**Acceptance Criteria:**
- [ ] All 5 vertical scenes functional
- [ ] Vertical Canvas plugin configured
- [ ] Dual output working (H + V simultaneous)
- [ ] Social media aspect ratios correct

---

### STORY 007: Pedagogical Overlay System
**ID:** SKOREQ-OBS-EPIC-001-STORY-007  
**Points:** 5 (free-tier)  
**Priority:** high  

**Problem:**  
The interval notation, text prompts, and theory overlays from Harry_Elgato need to be ported and organized.

**Scope:**
- Migrate 220 image assets with corrected paths
- Organize into toggleable groups
- Create interval overlay scene
- Create text prompt overlay scene

**Files in Scope:**
```
~/.roxy/obs-portable/assets/intervals/ (30 files)
~/.roxy/obs-portable/assets/cof/ (20 files)
~/.roxy/obs-portable/assets/overlays/ (50 files)
~/.roxy/obs-portable/groups/theory-overlays.json
docs/obs/OVERLAY_ASSET_MANIFEST.md
```

**Acceptance Criteria:**
- [ ] All 220 image assets migrated
- [ ] Path references updated to Linux
- [ ] Interval group toggleable via hotkey
- [ ] COF overlays toggleable via hotkey
- [ ] Text prompts in dedicated scene

---

### STORY 008: Move Transition Animation System
**ID:** SKOREQ-OBS-EPIC-001-STORY-008  
**Points:** 5 (free-tier)  
**Priority:** high  

**Problem:**  
The 102 move_source_filters for key transposition need to be ported and optimized.

**Scope:**
- Port key shift animation system
- Create reusable animation presets
- Optimize simultaneous_move chains
- Add new animation types (zoom, fade, rotate)

**Files in Scope:**
```
~/.roxy/obs-portable/filters/key-transposition.json
~/.roxy/obs-portable/filters/animation-library.json
~/.roxy/obs-portable/filters/simultaneous-move-chains.json
docs/obs/ANIMATION_SYSTEM_GUIDE.md
```

**Acceptance Criteria:**
- [ ] Key shift animations working (12 steps)
- [ ] Scale degree shift animations working
- [ ] Duration configurable (default 1300ms)
- [ ] simultaneous_move chains preserved
- [ ] New animation presets documented

---

### STORY 009: MIDI Integration Testing
**ID:** SKOREQ-OBS-EPIC-001-STORY-009  
**Points:** 3 (free-tier)  
**Priority:** medium  

**Problem:**  
MIDI input needs to trigger fretboard highlighting in real-time with < 50ms latency.

**Scope:**
- Test MIDI routing from guitar to NovaXe/8K Theater
- Verify KRONOS sync
- Test NDI widget latency
- Document MIDI setup

**Files in Scope:**
```
~/.roxy/obs-portable/config/midi-routing.json
docs/obs/MIDI_INTEGRATION_GUIDE.md
tests/obs/midi-latency-test.sh
```

**Acceptance Criteria:**
- [ ] MIDI input detected in OBS (via NovaXe)
- [ ] Fretboard highlights in < 50ms
- [ ] Braid updates on chord detection
- [ ] KRONOS beat sync verified
- [ ] Documentation with troubleshooting

---

### STORY 010: Documentation & Onboarding
**ID:** SKOREQ-OBS-EPIC-001-STORY-010  
**Points:** 2 (free-tier)  
**Priority:** low  

**Problem:**  
Comprehensive documentation needed for the dream collection.

**Scope:**
- Create quick start guide
- Document all hotkeys
- Create troubleshooting guide
- Update existing docs

**Files in Scope:**
```
docs/obs/SKOREQ_DREAM_QUICKSTART.md
docs/obs/HOTKEY_REFERENCE.md
docs/obs/TROUBLESHOOTING.md
docs/obs/README.md
```

**Acceptance Criteria:**
- [ ] Quick start guide < 5 minute read
- [ ] All hotkeys documented
- [ ] Common issues covered
- [ ] Screenshots included

---

## 📊 STORY SUMMARY

| Story ID | Title | Points | Queue | Priority |
|----------|-------|--------|-------|----------|
| STORY-001 | NDI Widget Bridge Infrastructure | 5 | free-tier | critical |
| STORY-002 | AI Plugin Configuration | 3 | free-tier | high |
| STORY-003 | obs-mcp ROXY Integration | 5 | free-tier | critical |
| STORY-004 | Scene Collection Architecture | 8 | paid-tier | critical |
| STORY-005 | Horizontal Canvas Master Scenes | 5 | free-tier | high |
| STORY-006 | Vertical Canvas Scenes | 3 | free-tier | medium |
| STORY-007 | Pedagogical Overlay System | 5 | free-tier | high |
| STORY-008 | Move Transition Animation System | 5 | free-tier | high |
| STORY-009 | MIDI Integration Testing | 3 | free-tier | medium |
| STORY-010 | Documentation & Onboarding | 2 | free-tier | low |
| **TOTAL** | | **44** | | |

---

## 🔗 DEPENDENCIES

```
STORY-001 (NDI Bridge) ← STORY-004 (Scene Architecture)
STORY-002 (AI Plugins) ← STORY-005 (Horizontal Masters)
STORY-003 (ROXY MCP) ← STORY-004 (Scene Architecture)
STORY-004 (Scene Arch) ← STORY-005, STORY-006, STORY-007, STORY-008
STORY-007 (Overlays) ← STORY-008 (Animations)
```

**Execution Order:**
1. STORY-001, STORY-002, STORY-003 (parallel)
2. STORY-004
3. STORY-005, STORY-006, STORY-007 (parallel)
4. STORY-008
5. STORY-009
6. STORY-010

---

## 🎮 FINAL SCENE COUNT ESTIMATE

| Category | Count |
|----------|-------|
| Separators | 8 |
| Camera Sources | 8 |
| NDI Widget Sources | 8 |
| Screen Captures | 5 |
| Module Scenes (Fret/Braid/COF) | 15 |
| Composition Scenes | 10 |
| Horizontal Masters | 8 |
| Vertical Masters | 5 |
| Utility Scenes | 6 |
| Overlay Groups | 12 |
| **TOTAL** | **~85** |

**Reduction:** 238 → 85 scenes (64% reduction)  
**Preserved:** 100% of pedagogical functionality

---

## 🚀 INDUSTRY-SHATTERING FEATURES

### 1. **AI Voice-Controlled Teaching**
```
"Hey ROXY, show the circle of fifths"
"ROXY, animate key shift to G"
"Start recording the scale lesson"
```

### 2. **Real-Time MIDI Visualization**
- Play guitar → Fretboard lights up instantly
- Chord detected → Braid highlights harmonic function
- KRONOS sync → Perfect beat alignment

### 3. **Multi-Platform Simultaneous Streaming**
- 2560×1440 → YouTube Live
- 1080×1920 → TikTok Live
- 7680×4320 → Archive master

### 4. **AI-Powered Captions**
- LocalVocal transcribes in real-time
- Polyglot translates to 100+ languages
- CleanStream removes verbal tics

### 5. **8K Theater Widget Independence**
- Each widget is an NDI source
- Mix and match in any OBS composition
- WebGPU rendering at 60fps

---

## ⚠️ GOVERNANCE NOTES

**This document is a Cursor Plan Mode document.**

- ❌ NOT directly executable
- ❌ NOT a swarm ticket
- ✅ MUST be translated to JSON tickets
- ✅ MUST follow CURSOR_PLAN_TO_SWARM_TICKET.md contract
- ✅ MUST enqueue via `luno enqueue` command

**To add these tickets properly:**
1. Translate each STORY to JSON using the canonical shape
2. Validate against the checklist
3. Enqueue via `bun run src/cli/luno.ts enqueue --story=SKOREQ-OBS-EPIC-001-STORY-XXX --queue=free-tier`

---

## 📎 RELATED DOCUMENTS

- [HARRY_ELGATO_PEDAGOGICAL_ANALYSIS.md](./HARRY_ELGATO_PEDAGOGICAL_ANALYSIS.md)
- [DREAM_SCENE_COLLECTION_RECOMMENDATION.md](./DREAM_SCENE_COLLECTION_RECOMMENDATION.md)
- [OBS_ULTIMATE_SCENE_CREATION_BIBLE.md](./OBS_ULTIMATE_SCENE_CREATION_BIBLE.md)
- [CURSOR_PLAN_TO_SWARM_TICKET.md](~/.roxy/docs/docs/onboarding/CURSOR_PLAN_TO_SWARM_TICKET.md)

---

**Last Updated:** 2026-01-09  
**Status:** PLAN MODE (Ready for ticket translation)  
**Epic:** SKOREQ-OBS-EPIC-001
