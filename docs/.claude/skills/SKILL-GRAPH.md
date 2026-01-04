# Claude Skills Dependency Graph

> **Version:** 2.0.0
> **Last Updated:** 2025-12-10
> **Total Skills:** 33
> **Total Edges:** 87

---

## Graph Legend

```
→   : depends on (hard dependency)
⟷   : bidirectional (mutual)
∷   : shares data with
⊃   : contains/encompasses
┄   : optional dependency
```

---

## Core Dependency Map

```
                                    ┌─────────────────────────────────────┐
                                    │         MDF2030-MASTER              │
                                    │   (15 Laws, Widget Slave Pattern)   │
                                    └─────────────────┬───────────────────┘
                                                      │
                    ┌─────────────────────────────────┼─────────────────────────────────┐
                    │                                 │                                 │
                    ▼                                 ▼                                 ▼
        ┌───────────────────────┐       ┌───────────────────────┐       ┌───────────────────────┐
        │    KHRONOS-TIMING     │       │    WIDGET-ARCHITECTURE │       │    APOLLO-AUDIO       │
        │  (Single Time Auth)   │       │    (Slave Pattern)     │       │  (Audio Router)       │
        └───────────┬───────────┘       └───────────┬───────────┘       └───────────┬───────────┘
                    │                               │                               │
    ┌───────────────┼───────────────┐       ┌───────┴───────┐       ┌───────────────┼───────────────┐
    │               │               │       │               │       │               │               │
    ▼               ▼               ▼       ▼               ▼       ▼               ▼               ▼
┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
│ QUANTUM   │ │ NVX1      │ │ 8K        │ │ CHORD     │ │ BRAID     │ │ APOLLO    │ │ VGM       │ │ PROF      │
│ RAILS     │ │ SCORE     │ │ THEATER   │ │ CUBES     │ │ VIS       │ │ CONSOL    │ │ SOUNDFONT │ │ MIXER     │
└─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
      │             │             │             │             │             │             │             │
      │             │             │             └──────┬──────┘             │             │             │
      │             │             │                    │                    │             │             │
      ▼             ▼             ▼                    ▼                    ▼             ▼             ▼
┌─────────────────────────────────────┐ ┌───────────────────────┐ ┌─────────────────────────────────────┐
│          RENDERING CLUSTER          │ │    MUSIC-THEORY       │ │          AUDIO CLUSTER              │
│  olympus-3d, webgpu, threejs, braid │ │    voice-leading      │ │  apollo-*, vgm, mixer, chordcubes   │
└─────────────────────────────────────┘ │    chord-engine       │ │                audio                │
                                        └───────────┬───────────┘ └─────────────────────────────────────┘
                                                    │
                                                    ▼
                                        ┌───────────────────────┐
                                        │   NOTAGEN-PIPELINE    │
                                        │   (45,682 patterns)   │
                                        └───────────────────────┘
```

---

## Domain Clusters

### Audio Cluster (5 skills)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            AUDIO CLUSTER                                    │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                     APOLLO-AUDIO (Hub)                               │  │
│   │  SmartAudioRouter → Backend Selection → Gesture Gate → Play         │  │
│   └───────────────────────────────┬─────────────────────────────────────┘  │
│                                   │                                         │
│       ┌───────────────┬───────────┼───────────┬───────────────┐            │
│       │               │           │           │               │            │
│       ▼               ▼           ▼           ▼               ▼            │
│   ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐   │
│   │ APOLLO    │ │ VGM       │ │ PROF      │ │ CHORDCUBES│ │ MIDI      │   │
│   │ CONSOL    │ │ SOUNDFONT │ │ MIXER     │ │ AUDIO     │ │ HARDWARE  │   │
│   │           │ │           │ │           │ │           │ │           │   │
│   │ Dual arch │ │ 23 VGM    │ │ DAW mixer │ │ 19K mono  │ │ WebMIDI   │   │
│   │ merge     │ │ profiles  │ │ OpenDAW   │ │ AudioEng  │ │ <5ms      │   │
│   └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘   │
│                                                                             │
│   Data Flow:                                                               │
│   User Input → SmartAudioRouter → Backend Priority → Synth → WebAudio      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Music Theory Cluster (4 skills)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MUSIC THEORY CLUSTER                                 │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                     MUSIC-THEORY (Hub)                               │  │
│   │  HarmonyRail → EventSpine → Theory Calculations → Brain             │  │
│   └───────────────────────────────┬─────────────────────────────────────┘  │
│                                   │                                         │
│           ┌───────────────────────┼───────────────────────┐                │
│           │                       │                       │                │
│           ▼                       ▼                       ▼                │
│   ┌───────────────┐     ┌───────────────┐     ┌───────────────────────┐   │
│   │ VOICE-LEADING │     │ CHORD-ENGINE  │     │ NOTAGEN-PIPELINE      │   │
│   │               │     │               │     │                       │   │
│   │ VL1/VL2/VL3   │     │ 60+ types     │     │ 45,682 patterns       │   │
│   │ 9 rules       │     │ 100+ aliases  │     │ Baroque/Classical/    │   │
│   │ NotaGen int   │     │ 4 voicing     │     │ Romantic styles       │   │
│   └───────┬───────┘     └───────┬───────┘     └───────────┬───────────┘   │
│           │                     │                         │                │
│           └─────────────────────┴─────────────────────────┘                │
│                                 │                                          │
│                                 ▼                                          │
│                   ┌───────────────────────────────┐                       │
│                   │  EventSpine (Single Truth)    │                       │
│                   └───────────────────────────────┘                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Rendering Cluster (5 skills)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RENDERING CLUSTER                                   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                     OLYMPUS-3D (Hub)                                 │  │
│   │  WebGPU Context → Render Pipeline → Canvas → Display                │  │
│   └───────────────────────────────┬─────────────────────────────────────┘  │
│                                   │                                         │
│       ┌───────────────────────────┼───────────────────────────────────┐    │
│       │                           │                                   │    │
│       ▼                           ▼                                   ▼    │
│   ┌───────────────┐     ┌───────────────────┐     ┌───────────────────┐   │
│   │ WEBGPU-       │     │ THREEJS-RUNTIME   │     │ BRAID-            │   │
│   │ RENDERING     │     │                   │     │ VISUALIZATION     │   │
│   │               │     │                   │     │                   │   │
│   │ 18 WGSL       │     │ Native WebGPU     │     │ 62K lines         │   │
│   │ shaders       │     │ RailCompositor    │     │ Voice lines       │   │
│   │ 31K Rust      │     │ NO RAF            │     │ 12 presets        │   │
│   └───────────────┘     └───────────────────┘     └───────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│                     ┌───────────────────────────────┐                      │
│                     │  WASM-INTEGRATION             │                      │
│                     │  + RUST-BEVY                  │                      │
│                     │  (41K lines, 147 files)       │                      │
│                     └───────────────────────────────┘                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Coordination Cluster (5 skills)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       COORDINATION CLUSTER                                  │
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                   AGENT-BREAKROOM (Central)                        │    │
│   │  Activities → Locks → Discoveries → Sync → Consensus              │    │
│   └─────────────────────────────────┬─────────────────────────────────┘    │
│                                     │                                       │
│       ┌─────────────────┬───────────┼───────────┬─────────────────┐        │
│       │                 │           │           │                 │        │
│       ▼                 ▼           ▼           ▼                 ▼        │
│   ┌───────────┐   ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ │
│   │ EPIC      │   │ GHOST     │ │ PHOENIX   │ │ NOVAXE    │ │ RAG       │ │
│   │ TRACKER   │   │ PROTOCOL  │ │ PROTOCOL  │ │ SEB       │ │ BRAIN     │ │
│   │           │   │           │ │           │ │           │ │           │ │
│   │ 32 epics  │   │ AI handoff│ │ P0-P14    │ │ Event bus │ │ 3-tier    │ │
│   │ 6 states  │   │ 7 planets │ │ Recovery  │ │ TypedBus  │ │ fallback  │ │
│   └───────────┘   └───────────┘ └───────────┘ └───────────┘ └───────────┘ │
│                                                                             │
│   Protocol:                                                                │
│   1. Register presence → 2. Post activities → 3. Share discoveries         │
│   4. Use locks → 5. Never edit releaseplan directly                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Full Dependency Matrix

| Skill | Depends On | Depended By |
|-------|-----------|-------------|
| mdf2030-master | — | ALL skills |
| khronos-timing | mdf2030-master | quantum-rails, nvx1-score, 8k-theater |
| apollo-audio | khronos-timing | chordcubes-audio, vgm-soundfont, prof-mixer |
| apollo-consolidation | apollo-audio | — |
| music-theory | mdf2030-master | voice-leading, chord-engine, notagen |
| voice-leading | music-theory | notagen-pipeline |
| chord-engine | music-theory | chord-cubes |
| notagen-pipeline | voice-leading | — |
| quantum-rails | khronos-timing | nvx1-score, olympus-3d |
| nvx1-score | quantum-rails, khronos | — |
| olympus-3d | quantum-rails | webgpu-rendering, threejs, braid |
| webgpu-rendering | olympus-3d | wasm-integration |
| threejs-runtime | olympus-3d | — |
| braid-visualization | olympus-3d, voice-leading | — |
| 8k-theater | khronos-timing, widget-arch | chord-cubes |
| widget-architecture | mdf2030-master | ALL widgets |
| chord-cubes | widget-arch, chord-engine | — |
| chordcubes-audio | apollo-audio, chord-cubes | — |
| agent-breakroom | — | epic-tracker, ghost-protocol |
| epic-tracker | agent-breakroom | — |
| ghost-protocol | agent-breakroom | — |
| phoenix-protocol | — | — |
| novaxe-seb | — | — |
| rag-brain | — | — |
| midi-hardware | — | apollo-audio |
| playwright-testing | — | — |
| audio-testing | apollo-audio | — |
| wasm-integration | webgpu-rendering | rust-bevy |
| rust-bevy | — | wasm-integration |
| figma-design-system | — | ALL UI |
| obs-ndi-streaming | — | — |
| vgm-soundfont | apollo-audio | — |
| professional-mixer | apollo-audio | — |

---

## Critical Path Analysis

### Shortest Path: User Click → Sound

```
User Click
    │
    ▼
Widget (chord-cubes)
    │ useAudioRouter()
    ▼
SmartAudioRouter (apollo-audio)
    │ selectBackend()
    ▼
ApolloWorkletBackend (apollo-consolidation)
    │ playNote()
    ▼
SpessaSynth (vgm-soundfont)
    │
    ▼
WebAudio Output
```

**Total hops:** 5
**Latency budget:** <10ms

### Longest Path: MIDI → Full Render

```
MIDI Input (midi-hardware)
    │
    ▼
GlobalMidiEventBus (novaxe-seb)
    │
    ▼
Brain Service (music-theory)
    │
    ├─→ VoiceLeadingService (voice-leading)
    │
    ├─→ ChordEngine (chord-engine)
    │
    ▼
EventSpine (quantum-rails)
    │
    ├─→ SmartAudioRouter (apollo-audio)
    │       │
    │       ▼
    │   WebAudio Output
    │
    └─→ RenderScheduler (khronos-timing)
            │
            ▼
        Olympus Renderer (olympus-3d)
            │
            ▼
        WebGPU Canvas
```

**Total hops:** 9
**Latency budget:** <16.7ms (60 FPS)

---

## GraphML Export

For visualization in Gephi or Neo4j, use:

```bash
node scripts/skills/export-graph.mjs --format graphml > skills-graph.graphml
```

---

## Graph Statistics

| Metric | Value |
|--------|-------|
| Total Nodes | 33 |
| Total Edges | 87 |
| Avg Degree | 2.6 |
| Max Out-Degree | mdf2030-master (33) |
| Max In-Degree | apollo-audio (8) |
| Diameter | 5 |
| Clustering Coeff | 0.42 |

---

**Generated by Claude Skills System v2.0**
