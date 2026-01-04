# MindSong Juke Hub - Claude Code Master Context

> **Version:** 3.0 (MDF2030 + MOS2030 Deep Integration)
> **Status:** Production-Ready Master Knowledge Base
> **Last Updated:** 2025-12-09

---

## EXECUTIVE SUMMARY

**MindSong Juke Hub** is an enterprise-grade Musical Operating System with:
- **Architecture:** MOS2030 Engine (94.8/100 target) + MDF2030 Binary Format
- **Timing:** Khronos (Single Time Authority) + Time Lattice + ClockSync
- **Rendering:** Three.js WebGPU (SOLE runtime) + Rust/WASM (logic only)
- **Widgets:** EventSpine projections (SLAVES, not authorities)
- **Audio:** Apollo Router (swappable: Tone.js/VCO/Sonatina/MIDI)
- **Testing:** SAVAGE³ forensic suite + 356+ test files

---

# PART 1: THE 15 MDF2030 LAWS (INVIOLABLE)

These laws are NON-NEGOTIABLE. Violation = immediate code review rejection.

| # | Law | Description |
|---|-----|-------------|
| 1 | **Single Time Authority** | ONLY Khronos defines tick↔seconds. No other clock source. |
| 2 | **Flat Event Spine** | Timeline = ordered list of Events. NO hierarchy. |
| 3 | **Rails Are Queries** | Rails = semantic filters, NOT data containers. |
| 4 | **No Duplicated Truth** | Timing, pitch, lyrics, IDs → single canonical owner. |
| 5 | **Binary MDF2030 Core** | Event Spine in compact FlatBuffers format. |
| 6 | **Strict Payload Budget** | Every Event Type has max bytes budget enforced. |
| 7 | **Immutable Snapshots** | Playback from versioned snapshots only. |
| 8 | **Unified Microtiming** | Rational offset OR microseconds (never mix). |
| 9 | **Renderers Are Views** | TRAX, OSMD, AR/VR, 3D twins — all projections from Event Spine. |
| 10 | **Performance Budgets Enforced** | Hard caps per device tier (Mobile/Desktop/Theater). |
| 11 | **AI Edits Through Sandbox** | No AI touches canonical spine without merge/approval. |
| 12 | **ClockSync Service** | Registers all subsystems, monitors drift, enforces alignment. |
| 13 | **Hot Index Everything** | Tick index, type index, voice index, spatial index. |
| 14 | **Undo/Redo Is Diff-Based** | Operations, not blobs. |
| 15 | **Drift Tests Required** | 1-hour polyrhythm + rubato drift test required in CI. |

---

# PART 2: THE 15 CRITICAL INVARIANTS

These invariants MUST NEVER be violated. Machine-enforced where possible.

| # | Invariant | Enforcement |
|---|-----------|-------------|
| 1 | **Only Kronos emits `current_tick`** | No other clock source allowed |
| 2 | **Events immutable after insert** | No in-place edits |
| 3 | **All queries O(log n) or better** | BVH spatial index |
| 4 | **Zero GC during render loop** | Object pooling + typed arrays |
| 5 | **Tick positions are rational** | Never float until audio scheduling |
| 6 | **Rails never store events** | Only query spine |
| 7 | **All temporal data through ClockSync** | No direct time access |
| 8 | **Payloads within budget** | Max bytes enforced at compile time |
| 9 | **Harmony logic in HarmonyRail/EventSpine** | NEVER fix chord quality in audio layers |
| 10 | **Audio layers play what they receive** | NEVER modify harmony data |
| 11 | **Widgets are EventSpine projections** | Subscribe via hooks; NEVER consume external MIDI for score playback |
| 12 | **All timing subsystems register with ClockSync** | TimelineContext, TimeCursor, widget timelines |
| 13 | **No independent RAF loops** | Visual playback derives from Kronos snapshots |
| 14 | **Single audio-to-visual path** | TimeCursor → Unified Kernel → ScorePlaybackConductor → EventSpine → Widgets |
| 15 | **Bridge safeguards required** | External drivers must add play-state guards, beat tolerances, telemetry |

---

# PART 3: WIDGET ARCHITECTURE (CRITICAL)

## THE CARDINAL RULE: Widgets are SLAVES, NOT Authorities

```
┌─────────────────────────────────────────────────────────────────┐
│                   BRAIN (EventSpine + Services)                 │
│  • Voice Leading Logic    • Harmonic Analysis    • Key Detection│
│  • Tempo Authority        • Chord Quality        • Voicing Logic│
│                     (ALL MUSICAL INTELLIGENCE)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ useEventSpine*() hooks (READ ONLY)
    ┌───────────┬───────────┬───────────┬───────────┬───────────┐
    │ Metronome │ ChordCubes│   Braid   │ Fretboard │   Piano   │
    │  (SLAVE)  │  (SLAVE)  │  (SLAVE)  │  (SLAVE)  │  (SLAVE)  │
    │  DISPLAY  │  DISPLAY  │  DISPLAY  │  DISPLAY  │  DISPLAY  │
    │   ONLY    │   ONLY    │   ONLY    │   ONLY    │   ONLY    │
    └───────────┴───────────┴───────────┴───────────┴───────────┘
```

## FORBIDDEN PATTERNS (Immediate Rejection)

```typescript
// ❌ FORBIDDEN - Widget as authority
tempoAuthority: true       // NO - Khronos owns tempo
harmonicAuthority: true    // NO - Brain owns harmony
voicingAuthority: true     // NO - Brain owns voicings
analysisAuthority: true    // NO - Brain owns analysis
keyAuthority: true         // NO - Brain owns key

// ❌ FORBIDDEN - Widget-to-widget communication
widget1.emit('chord', data);  // NO
widget2.on('chord', handler); // NO

// ❌ FORBIDDEN - Widget owning musical state
const [currentChord, setCurrentChord] = useState(); // NO - use EventSpine hook
```

## CORRECT PATTERNS

```typescript
// ✅ CORRECT - Widget subscribes to EventSpine
const activeChord = useEventSpineActiveChord();
const currentKey = useEventSpineKey();
const tempo = useKhronosTempo();

// ✅ CORRECT - User input flows UP to Brain
const handleUserClick = (note) => {
  Brain.processUserInput(note);  // Brain updates EventSpine
  // All widgets auto-update via subscription
};

// ✅ CORRECT - MIDI input flows to Brain
GlobalMidiEventBus.on('note', (note) => {
  Brain.processUserInput(note);  // Same path as UI
});
```

---

# PART 4: PERFORMANCE BUDGETS

| Metric | Mobile | Desktop | Theater |
|--------|--------|---------|---------|
| **Frame Time** | 16.7ms (60 FPS) | 8.3ms (120 FPS) | 4.2ms (240 FPS) |
| **Memory** | <500 MB | <2 GB | <4 GB |
| **Event Capacity** | 50K | 250K | 1M (segmented) |
| **Query Time** | <5ms | <1ms | <0.5ms |
| **Audio Latency** | <20ms | <10ms | <5ms |
| **Network Sync** | <100ms | <50ms | <50ms |
| **MIDI Latency** | <10ms | <5ms | <5ms |

---

# PART 5: KHRONOS TIMING SYSTEM

## Architecture

```
┌─────────────────────────────────────────────────┐
│              KHRONOS ENGINE                     │
│  • Single Time Authority                        │
│  • tick ↔ sample ↔ seconds conversion          │
│  • 10Hz throttling (PUBLISH_INTERVAL_MS=100)   │
│  • Force-publish on play/pause/seek            │
└─────────────────────────────────────────────────┘
                    │
          KhronosBus.publish()
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
ClockSync      Subscribers     RAF Batching
(drift <100ms)  (cascade)    (single frame)
```

## ClockSync Registration Checklist

All these subsystems MUST register with ClockSync:
1. KronosClock (authoritative source)
2. AudioContext renderer loop
3. TRAX sequencer
4. OSMD cursor
5. Hermes timeline
6. TimelineContext (Theater8k)
7. NVX1 TimeCursor bridge
8. Widget timeline loops

## Correct Timing Access

```typescript
// ❌ WRONG - Never access time directly
const tick = performance.now();
const tick = Date.now();

// ✅ CORRECT - Always through ClockSync
const tick = ClockSyncService.instance.getAuthoritativeTick();
const tick = useKhronosTick();
```

---

# PART 6: APOLLO AUDIO SYSTEM

## The Apollo Rule (Non-Negotiable)

**ALL audio playback MUST use Apollo. No exceptions.**

```typescript
// ✅ CORRECT - Only approved methods
window.Apollo?.playNote(note, velocity);
window.Apollo?.stopNote(note);
Apollo.playChord(chord, options);

// ❌ FORBIDDEN - Will fail code review
Tone.Transport.start();              // NO
Tone.Synth.triggerAttackRelease();   // NO
VCO.playNote();                      // NO
Sonatina.playNote();                 // NO
WebAudio.createOscillator();         // NO
new AudioContext();                   // NO (use Apollo's context)
```

## Apollo Architecture

```
┌─────────────────────────────────────────┐
│            APOLLO ROUTER                │
│  (Swappable Engine Abstraction)         │
└─────────────────────────────────────────┘
          │
    ┌─────┼─────┬─────────┬─────────┐
    ▼     ▼     ▼         ▼         ▼
 Tone.js  VCO  Sonatina  MIDI   Future
 (synth) (osc) (sampler) (ext)  (engines)
```

## Console Tags to Monitor

| Tag | Meaning | Action |
|-----|---------|--------|
| `[VL.APOLLO.ROUTED]` | Voice leading routed through Apollo | Expected |
| `[APOLLO.PLAYCHORD]` | Chord playback initiated | Expected |
| `[CUTOFF]` | Note cutoff events | Expected |
| `[PLAY]` | Note tracking | Expected |
| `[APOLLO.ERROR]` | Audio routing failure | Investigate |

---

# PART 7: DO-NOT-DUPLICATE DIRECTIVE

## FORBIDDEN to Create

- Parallel widget systems (use Theater/Olympus/WidgetRegistry)
- Layout/drag/drop systems (use existing)
- Keyboard shortcut handlers (use existing)
- Audio routers (use Apollo)
- Progress trackers (use master-progress.json)
- State sync managers (use EventSpine)
- Intent bus systems (use EventSpine)
- Widget authority patterns (widgets are SLAVES)

## MUST USE EXISTING

| Need | Use This | NOT This |
|------|----------|----------|
| Widget management | Theater, Olympus, WidgetRegistry | Custom widget system |
| Audio routing | Apollo | Direct Tone.js/WebAudio |
| Progress tracking | master-progress.json | Custom tracker |
| State management | EventSpine + useEventSpine* hooks | Custom state stores |
| Timing | Khronos + ClockSync | performance.now() |
| Layout | Theater layout system | Custom drag/drop |

---

# PART 8: EPIC/SPRINT STRUCTURE

## Active Epics (32 Total)

| Priority | Epic | Status | Focus |
|----------|------|--------|-------|
| CRITICAL | EPIC-PHOENIX-PROTOCOL | P0-P9: 100%, P10: 20% | Timing/fidelity recapture |
| CRITICAL | EPIC-QR2-LOCKDOWN | In Progress | Quantum Rails 2.0 + 8K Theater |
| CRITICAL | EPIC-MOS2030-ENGINE | In Progress | Three.js WebGPU renderer |
| HIGH | EPIC-RELEASE-WEB | 85% Ready | Web app production deploy |
| HIGH | EPIC-HIVEMIND | Pending | Multi-agent safety/consensus |
| DONE | EPIC-OLYMPUS | Archived | Convergence page (complete) |
| DONE | EPIC-NVX1 | Superseded | Rescued by Phoenix Protocol |

## Phoenix Protocol Phases (P0-P14)

| Phase | Name | Status |
|-------|------|--------|
| P0 | Risk & Canon | DONE |
| P1 | Harness & Fixtures | DONE |
| P2 | Data & Adapter Corrections | DONE |
| P3 | Subdivision & Grid System | DONE |
| P4 | Rendering Fidelity | DONE |
| P5 | Transport/Audio/Metronome | DONE |
| P6 | Import/Export Fidelity | DONE |
| P7 | Editor & UX | DONE |
| P8 | Perf/Telemetry/Ops | DONE |
| P9 | Validation & Rollout | DONE |
| P10 | UI/UX Core & Preferences | IN PROGRESS (20%) |
| P11 | Chord/LH/Fretboard Engine | Pending |
| P12 | Metadata & Import UX | Pending |
| P13 | Search & Discovery | Pending |
| P14 | Micro-Widgets & Telemetry | Pending |

---

# PART 9: TESTING INFRASTRUCTURE

## SAVAGE³ Forensic Suite

The SAVAGE³ (Savage Cubed) test suite provides:
- **40+ metrics per frame** captured
- **Beat-1 Truth Table** generation
- **Three-brain clock profiling** (Khronos, Audio, Visual)
- **Drift detection** with forensic baselines

### Key Test Files
- `tests/e2e/nvx1-timeline-forensic-savage-cubed.spec.ts`
- `tests/audio/nvx1-timeline-forensic-savage-cubed-enhanced.spec.ts`
- `src/utils/diagnostics/timelineDataCapture.ts`

## Test Commands

```bash
# Unit tests
pnpm test

# E2E tests
pnpm e2e

# Khronos timing tests
pnpm test:khronos

# Audio validation
pnpm audio:validate

# SAVAGE³ forensic suite
pnpm playwright test nvx1-timeline-forensic-savage-cubed

# Quantum Rails regression (86 tests)
pnpm test:unit:nvx1-audio
```

## Test Configs

| Config | Port | Purpose |
|--------|------|---------|
| playwright.config.ts | 9135 | Main E2E |
| playwright.khronos.config.ts | 5174 | Khronos timing |
| playwright.cubes.config.ts | 9135 | ChordCubes |
| vitest.config.ts | - | Unit tests |

---

# PART 10: AGENT ECOSYSTEM

## Chain of Command

```
CHIEF (Strategic Orders)
  │ CHIEF-ORDER / CHIEF-INTEL / CHIEF-SEAL / CHIEF-OVERRIDE
  ▼
CODEX (Orchestrator/State Machine)
  │ Phases, patch waves, validation, progress sync
  ▼
BREAKROOM (Coordination Layer)
  │ Presence, locks, activities, discoveries
  ▼
AGENTS (Cursor/VSCode/CLI)
  │ Execute assigned tasks ONLY
  ▼
MCP/DOC BRAIN (Knowledge Oracle)
```

## Breakroom Protocol (THE LAW)

1. **Post activities BEFORE any work**
2. **Never edit releaseplan/*.json directly**
3. **Share discoveries publicly**
4. **Use FileLockManager for concurrent edits**
5. **Register presence on session start**

---

# PART 11: SEB QUARANTINE

## Global Invariants #11-12

**Novaxe SEB is a READ-ONLY archive.**

### FORBIDDEN
- Import SEB code
- Execute SEB code
- Revive SEB architecture
- Modify SEB files

### ALLOWED
- Forensic reading
- Idea mining
- Documentation extraction
- Architecture study

**All SEB-derived implementations must be rewritten in MSM/Phoenix/Olympus stacks.**

---

# PART 12: QUICK REFERENCE

## Ports
- Dev server: `localhost:9135`
- Khronos dev: `localhost:5174`

## Key Files

| Purpose | File |
|---------|------|
| Progress | `public/releaseplan/master-progress.json` |
| Codex State | `codex.state.json` |
| MDF2030 Spec | `docs/architecture/mos-2030-master-synthesis/MDF2030_MASTER_KNOWLEDGE_BASE.md` |
| Vision | `docs/MINDSONG_ENTERPRISE_VISION.md` |
| Agent Start | `docs/START_HERE_AGENTS.md` |
| Apollo Rule | `APOLLO_RULE.md` |

## Data Flow Summary

```
User Input (UI/MIDI)
       │
       ▼
    Widget (captures only)
       │
       ▼
    BRAIN (processes, updates EventSpine)
       │
       ▼
  EventSpine (single source of truth)
       │
       ▼
  ALL Widgets (subscribe, render)
       │
  Khronos (time authority)
```

---

## Skills Available

| Skill | Purpose |
|-------|---------|
| mdf2030-master | Complete MDF2030/MOS2030 spec knowledge |
| widget-architecture | Slave pattern, EventSpine projections |
| khronos-timing | Timing authority, ClockSync, drift detection |
| apollo-audio | Audio routing, engine switching |
| olympus-3d | Three.js WebGPU rendering |
| music-theory | Voice leading, harmony, EventSpine hooks |
| phoenix-protocol | P0-P14 phases, validation |
| playwright-testing | SAVAGE³, E2E patterns |
| epic-tracker | 32 epics, sprints, stories |
| agent-breakroom | Coordination protocol |
| midi-hardware | WebMIDI, <5ms latency |

See `.claude/skills/` for detailed skill documentation.
