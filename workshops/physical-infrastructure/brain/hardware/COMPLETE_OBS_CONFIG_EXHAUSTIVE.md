# COMPLETE OBS STUDIO CONFIGURATION - EXHAUSTIVE REBUILD BLUEPRINT
## Harry Elgato Fall Freeze fkup.json - Comprehensive Technical Specification

**Source File:** `Harry_Elgato_Fall_Freeze_fkup.json` (13.9 MB)  
**Export Date:** June 1, 2025 (macOS backup)  
**Purpose:** Complete studio ecosystem specification for AI-driven rebuild  
**Status:** ✅ PRODUCTION CONFIGURATION - TESTED & OPERATIONAL

---

## 📊 MASTER STATISTICS

| Metric | Value |
|--------|-------|
| **Total Scenes** | 238 |
| **Landscape Scenes** | 214 |
| **Vertical (VERT) Scenes** | 24 |
| **Total Sources** | 400+ (cameras, audio, overlays) |
| **Audio Input Devices** | 3 (Aux1, Aux3, Desktop) |
| **Audio Output Devices** | 1+ (NDI broadcast) |
| **Transitions Defined** | 3 base + 17 context rules |
| **Video Resolution** | 2560×1440 (2K) |
| **Default Transition** | "Move" (1300ms) |
| **Current Scene** | "1. All Left" |

---

## 🎤 AUDIO INPUT DEVICES (3 TOTAL)

### AUX1: "Logic Loop" - M-AUDIO AIR 192 4
**Function:** DAW audio from Apple Logic Pro  
**Hardware:** M-Audio AIR 192 4 USB audio interface (channel 1-2)  
**Device ID:** `AppleUSBAudioEngine:M-Audio:AIR 192 4:2200000:1,2`  
**Volume:** 0.78 (-2.1 dB)  
**Status:** ✅ ENABLED  

**Filter Chain (6 filters):**
1. Noise Suppression (rnnoise) - ❌ DISABLED
2. Compressor (output_gain: 0.8dB) - ❌ DISABLED
3. **Noise Gate** ✅ ENABLED (open: -40dB, close: -69dB, hold: 206ms, release: 202ms)
4. 3-Band EQ (low: +6.8dB, mid: +2.2dB, high: +5.1dB) - ❌ DISABLED
5. Limiter (threshold: -4dB, release: 788ms) - ❌ DISABLED
6. **NDI Audio Output** ✅ ENABLED → broadcasts as **"Logic Looper"**

---

### AUX3: "Mic/Aux 3" - M-AUDIO AIR 192 4 (YOUR MAIN MIC)
**Function:** Primary microphone input  
**Hardware:** M-Audio AIR 192 4 USB (same device, same channel)  
**Device ID:** `AppleUSBAudioEngine:M-Audio:AIR 192 4:2200000:1,2`  
**Volume:** 0.71 (-3.0 dB)  
**Balance:** 0.0 (left-heavy for mono mic)  
**Status:** ✅ ENABLED  

**Filter Chain (6 filters) - FULL BROADCAST CHAIN:**
1. **Noise Suppression** ✅ ENABLED (RNNoise v2)
2. **Compressor** ✅ ENABLED (output_gain: **17.4 dB** - HUGE BOOST)
3. Noise Gate (open: -29dB, close: -39dB) - ❌ DISABLED
4. **3-Band EQ** ✅ ENABLED (low: +6.8dB, mid: +2.2dB, high: +5.1dB)
5. **Limiter** ✅ ENABLED (threshold: -4dB, release: 788ms)
6. **NDI Audio Output** ✅ ENABLED → broadcasts as **"mic2 NDI"**

---

### DESKTOP AUDIO: "Desktop Audio" - iShow USB Audio
**Function:** System audio capture  
**Device ID:** `iShowUAudioEngine:0`  
**Volume:** 0.45 (-6.9 dB) - LOW  
**Status:** ✅ ENABLED  

**Filter Chain (1 filter):**
1. **NDI Audio Output** ✅ ENABLED → broadcasts as **"NDI Desktop Output"**

---

## 📹 VIDEO CAPTURE SOURCES (7 CAMERAS)

| # | Source Name | Type | Filters | Purpose |
|---|---|---|---|---|
| 1 | Sony TOP Blackmagic | decklink-input | 4 | Main overhead 4K |
| 2 | SonySide Blackmagic | decklink-input | 9 | Side angle 1080p |
| 3 | Canon TopRight Blackmagic | decklink-input | 2-4 | DSLR closeup |
| 4 | Nikon3000 RAW | macos-avcapture | 2 | USB CamLink |
| 5 | iPhone Clean Feed | av_capture_input | 0 | iPhone camera |
| 6 | OverHead | av_capture_input | 5 | Generic overhead |
| 7 | Camo RH | camo/screen | varies | MacBook iSight macro |

---

## 📡 NDI NETWORK VIDEO (2 SOURCES)

| Source Name | Type | Filters | Purpose |
|---|---|---|---|
| NDI iMac GoPro | ndi_source | 0 | Remote GoPro via iMac |
| NDI Dice | ndi_source | 1 | Unknown "Dice" device |

---

## 🎬 TRANSITIONS (3 + 17 RULES)

### Base Transitions
1. **Luma Wipe** - `/Volumes/Orion/OBS Portable/assets/linear-h.png` (softness: 0.35)
2. **Dr. Strange** - Stinger video `/Volumes/Orion/OBS Portable/assets/Dr Strange.mov`
3. **Move** - Smart transition (default, 1300ms, zoom out, EaseOutQuad)

### Scene Transition Rules (17 total)
| To Scene | Transition | Duration |
|---|---|---|
| 12. Charts Alone FADE | Fade | 400ms |
| 2. Legend | Panel16 | 900ms |
| Akaso Left/Right | Fade | 250ms |
| Braid Alone | CircleDiamond | instant |
| Canon Main Blur | Fade | 500ms |
| Challenge | Challenge Stinger | 500ms |
| Fade to Black | Fade | 900ms |
| Game Footage | Fade | 1400ms |
| Nikon | Cut | instant |
| SCALE SCENE REAL | Move | 1050ms |
| Syntax | Fade | 1000ms |
| + 6 more rules... | | |

---

## 🎭 ALL 238 SCENES (CATEGORIZED)

### By Orientation
- **Landscape:** 214 scenes
- **Vertical (VERT):** 24 scenes

### By Category
| Category | Count | Examples |
|---|---|---|
| Camera angles | 25 | Canon Main 1, Sony Overhead, Nikon Alone |
| Fretboard/Guitar | 20 | 5a Fretboard CC, Roku Fretboard 2-9 |
| Chord education | 35 | Chord Builder, Braid Study, COF Highlight |
| Scale/Mode | 30 | Scale Scene, SCALE SCENE REAL, Mode texts |
| Vertical mobile | 24 | VERT Canon Main 1, VERT Piano, VERT Braid |
| Notation/Theory | 25 | Notation Classic, Key Center, Intervals |
| Practice/Homework | 15 | Challenge, CAGED Positions, Homework |
| Timer/Countdown | 5 | FF CLOCK, Countdown Timer |
| Title/Intro | 15 | Title Scene, Logo, End Screen |
| Special effects | 15 | Vortex Animation, Dr. Strange |
| Replay/Archive | 5 | Replay Scene, Freeze Frame |
| Background | 10 | Pilars, Panel Slides, Cubes |
| Games/Interactive | 10 | Game Footage, Guitar Pro Capture |
| NDI/Remote | 5 | iPad NDI, iPhone 11 Camera |

---

## ⚙️ ADVANCED SCENE SWITCHER

### Downstream Keyers (1 configured)
- **DSK 1:** Scene "VERT Downstream Vert" (300ms transitions)

### Transition Table
- 17 context-aware rules (from ANY scene → specific scene)

---

## 📁 CRITICAL ASSET PATHS

**All on:** `/Volumes/Orion/OBS Portable/`

| Path | Contents |
|---|---|
| `assets/linear-h.png` | Luma wipe gradient |
| `assets/Dr Strange.mov` | Stinger video |
| `assets/[chord_images]/` | 50+ chord diagrams |
| `assets/[scale_images]/` | Scale visualizations |
| `assets/[fretboard]/` | Fretboard overlays |

---

## 🔧 CONFIG VALUES

| Setting | Value |
|---|---|
| Resolution | 2560×1440 |
| OBS Version | 28+ (format v2) |
| Virtual Camera | Enabled (type 3) |
| Current Scene | "1. All Left" |
| Default Transition | "Move" (1300ms) |
| Scaling | +87x, -1y offset |

---

## 🛠️ REBUILD REQUIREMENTS

1. **Audio:** M-Audio AIR 192 4 USB interface
2. **Video:** Blackmagic DeckLink (4 inputs)
3. **NDI:** NDI runtime + OBS plugin
4. **Plugins:** Advanced Scene Switcher, Move Transition
5. **Assets:** Mount `/Volumes/Orion/` for all media
6. **Control:** Loupedeck profiles (.lp5 on ORION)

---

**Source JSON:** `Harry_Elgato_Fall_Freeze_fkup.json` (13.9 MB)  
**Rebuild Time:** 2-4 weeks with full automation  
**Last Updated:** January 9, 2026
