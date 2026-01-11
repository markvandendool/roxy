# 🎬 SKOREQ OBS Dream Collection

> **The Ultimate Music Education Streaming Setup**

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)]()
[![OBS](https://img.shields.io/badge/OBS-30%2B-green.svg)]()
[![NDI](https://img.shields.io/badge/NDI-5.x-purple.svg)]()

---

## 🌟 Overview

The SKOREQ OBS Dream Collection is a comprehensive streaming and recording setup designed for music education content creators. It integrates:

- **8K Theater Widgets** via NDI (Piano, Fretboard, Circle of Fifths, etc.)
- **AI-Powered Features** (LocalVocal captions, Background Removal)
- **Voice Control** via ROXY MCP integration
- **MIDI Control** for hands-free scene switching
- **Professional Animations** using move-transition

---

## 📁 Repository Structure

```
~/.roxy/obs-portable/
├── config/
│   ├── ndi-widget-bridge.json      # NDI widget configuration
│   ├── scene-manifest.json         # 85-scene architecture
│   ├── horizontal-masters.json     # 8 horizontal master scenes
│   ├── vertical-masters.json       # 5 vertical master scenes
│   ├── master-scene-hotkeys.json   # Hotkey bindings
│   ├── animation-library.json      # Animation presets
│   ├── simultaneous-move-chains.json
│   ├── interval-manifest.json      # Theory overlays
│   ├── cof-manifest.json           # Circle of Fifths overlays
│   ├── overlay-manifest.json       # Master overlay manifest
│   ├── theory-overlays.json        # Theory concept overlays
│   └── midi-routing.json           # MIDI configuration
├── filters/
│   ├── key-transposition.json      # Key shift animations
│   └── animation-presets.json      # Reusable animations
├── macros/
│   └── advanced-scene-switcher.json
├── overlays/
│   ├── intervals/                  # 12 interval images
│   ├── cof/                        # COF key highlights
│   ├── scales/                     # 84 scale diagrams
│   ├── chords/                     # 60 chord diagrams
│   └── theory/                     # Theory concepts
└── scenes/
    └── skoreq-scenes.json          # Importable scene collection

~/.roxy/docs/docs/obs/
├── NDI_WIDGET_ARCHITECTURE.md
├── AI_PLUGIN_CONFIGURATION.md
├── ROXY_OBS_VOICE_CONTROL.md
├── SCENE_ARCHITECTURE_GUIDE.md
├── HORIZONTAL_LAYOUT_GUIDE.md
├── VERTICAL_STREAMING_GUIDE.md
├── ANIMATION_SYSTEM_GUIDE.md
├── MIDI_INTEGRATION_GUIDE.md
├── SKOREQ_DREAM_QUICKSTART.md
├── HOTKEY_REFERENCE.md
├── TROUBLESHOOTING.md
└── README.md                       # This file
```

---

## 🚀 Quick Start

### Prerequisites

- OBS Studio 30+
- Theater 8K widget server
- NDI runtime (DistroAV)
- move-transition plugin

### Installation

```bash
# 1. Copy OBS profile
cp -r ~/.roxy/obs-portable/profiles/SKOREQ \
      ~/.config/obs-studio/basic/profiles/

# 2. Import scene collection
# OBS → Scene Collection → Import → skoreq-scenes.json

# 3. Configure NDI sources
# Each widget source → Properties → Select NDI name
```

See [SKOREQ_DREAM_QUICKSTART.md](SKOREQ_DREAM_QUICKSTART.md) for detailed setup.

---

## 🎹 Features

### Master Scenes

| Scene | Hotkey | Description |
|-------|--------|-------------|
| Full Teaching Studio | F1 | Camera + widget sidebar |
| Close-Up Piano | F2 | Overhead + large piano |
| Guitar Focus | F3 | Camera + fretboard |
| Theory Breakdown | F4 | 2×2 theory grid |
| Multi-Instrument | F5 | Piano + camera + guitar |
| Full Widget Array | F6 | All 8 widgets |
| DAW Production | F7 | Screen capture focus |
| Interview Mode | F8 | Dual camera |

### Key Transposition

Animated key changes across all instrument widgets:

- **Ctrl+Up/Down**: Transpose by semitone
- **Ctrl+Shift+G**: Jump to G major
- **Animation**: 1300ms smooth slide

### Voice Control

> "Hey ROXY, switch to guitar scene"

30+ voice commands for hands-free control.

### MIDI Integration

Map MIDI pads/faders to:
- Scene switching
- Source toggles
- Transport controls
- Audio levels

---

## 📊 Scene Architecture

85 scenes organized into:

- **Cameras** (8) - Sony A7IV, FX30, Decklink inputs
- **NDI Widgets** (8) - Piano, Fretboard, COF, etc.
- **Captures** (5) - DAW, browser, desktop
- **Modules** (15) - Reusable nested scenes
- **Composition** (10) - Multi-source layouts
- **Horizontal Masters** (8) - 16:9 broadcast
- **Vertical Masters** (5) - 9:16 TikTok/Shorts
- **Utility** (6) - Backgrounds, overlays
- **Overlay Groups** (12) - Theory teaching images

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [Quick Start](SKOREQ_DREAM_QUICKSTART.md) | Get running in 5 minutes |
| [Hotkey Reference](HOTKEY_REFERENCE.md) | All keyboard shortcuts |
| [Horizontal Guide](HORIZONTAL_LAYOUT_GUIDE.md) | 16:9 scene details |
| [Vertical Guide](VERTICAL_STREAMING_GUIDE.md) | 9:16 scene details |
| [Animation System](ANIMATION_SYSTEM_GUIDE.md) | Move transitions |
| [MIDI Integration](MIDI_INTEGRATION_GUIDE.md) | MIDI setup |
| [Voice Control](ROXY_OBS_VOICE_CONTROL.md) | ROXY commands |
| [NDI Architecture](NDI_WIDGET_ARCHITECTURE.md) | Widget bridge |
| [AI Plugins](AI_PLUGIN_CONFIGURATION.md) | LocalVocal, etc. |
| [Troubleshooting](TROUBLESHOOTING.md) | Common issues |

---

## 🛠️ Configuration Files

### OBS Profiles

- `~/.config/obs-studio/basic/profiles/SKOREQ/` - Horizontal 2560×1440
- `~/.config/obs-studio/basic/profiles/SKOREQ-Vertical/` - Vertical 1080×1920

### Plugin Configs

- `~/.config/obs-studio/plugin_config/obs-localvocal/`
- `~/.config/obs-studio/plugin_config/obs-backgroundremoval/`

### Voice Intents

- `~/.roxy/voice_intents/obs_commands.yaml`

---

## 🎯 EPIC Information

| Field | Value |
|-------|-------|
| **Epic ID** | SKOREQ-OBS-DREAM |
| **Stories** | 10 |
| **Total Points** | 35 |
| **Status** | Complete |

### Stories

1. ✅ NDI Widget Bridge Infrastructure
2. ✅ AI Plugin Configuration
3. ✅ ROXY MCP Integration
4. ✅ Scene Collection Architecture
5. ✅ Horizontal Canvas Master Scenes
6. ✅ Vertical Canvas Scenes
7. ✅ Pedagogical Overlay System
8. ✅ Move Transition Animation System
9. ✅ MIDI Integration Testing
10. ✅ Documentation & Onboarding

---

## 📝 License

Part of the MINDSONG ecosystem. Internal use.

---

## 🤝 Contributing

1. Follow governance docs in `~/.roxy/workshops/`
2. Create stories in SKOREQ epic format
3. Test thoroughly before merge

---

*Built with ❤️ by ROXY AI Orchestrator*
