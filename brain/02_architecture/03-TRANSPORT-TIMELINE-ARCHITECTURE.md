# 03 - Transport & Timeline System Architecture

**Audience:** Lead Architect, Senior Engineers  
**Purpose:** Resolve confusion about overlapping timeline/transport systems  
**Last Updated:** November 13, 2025

---

## The Problem: Too Many Timelines

You currently have **5 different timeline systems** that appear to overlap:

1. **Tone.Transport** (legacy, Tone.js)
2. **TransportKernel** (legacy custom system)
3. **UnifiedKernelEngine** (current production system)
4. **QuantumTimeline** (experimental, UI-specific)
5. **KronosClock** (WASM-based, high-precision)

**This document explains which one is actually in control and when.**

---

## System Selection Decision Tree

```
┌─────────────────────────────────────────────────────────────┐
│ User clicks PLAY on NVX1Score                               │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│ handlePlayPause() in NVX1Score.tsx (lines 2860-3050)      │
│ • Checks quantumStore.isPlaying                            │
│ • Calls ensureToneUnlocked()                               │
│ • Dispatches to useTransportStore.safePlay()               │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│ useTransportStore.safePlay() (TransportStore.ts)           │
│ • Validates state (hasScore, not already playing)          │
│ • Calls unifiedKernelFacade.dispatch({ type: 'play' })    │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│ UnifiedKernelFacade.dispatch() (lines 35-50)              │
│ • Logs "using unified kernel" (always true now)            │
│ • Routes to UnifiedKernelEngine.dispatch()                 │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│ UnifiedKernelEngine.dispatch('play') (line 2418)           │
│ • Checks FEATURE_FLAGS.KRONOS_ENABLED                      │
│ • If true → Creates KronosClock + AudioScheduler           │
│ • If false → Uses legacy AudioPlaybackService              │
│ • Starts requestAnimationFrame(tick) loop                  │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ├─────────────────┬──────────────────────────┐
                 ▼                 ▼                          ▼
        ┌────────────────┐ ┌──────────────┐ ┌────────────────────┐
        │ KronosClock    │ │ AudioScheduler│ │ RAF tick() loop    │
        │ (if enabled)   │ │ (if enabled)  │ │ (always)           │
        │                │ │               │ │                    │
        │ WASM timing    │ │ Event queue   │ │ 60 FPS position    │
        │ 960 PPQ        │ │ Apollo calls  │ │ sync to UI         │
        └────────────────┘ └──────────────┘ └────────────────────┘
```

---

## Active System: UnifiedKernelEngine (PRODUCTION)

**Location:** `src/services/transportKernel/UnifiedKernelEngine.ts`  
**Status:** ✅ **ACTIVE - This is the master timeline**  
**Lines of Code:** 2,915 lines

### Responsibilities

| Subsystem | Function | Active When |
|-----------|----------|-------------|
| **RAF Tick Loop** | UI position updates (60 FPS) | Always during playback |
| **KronosClock** | Sample-accurate WASM timing (960 PPQ) | `KRONOS_ENABLED=true` |
| **AudioScheduler** | Note scheduling, Apollo integration | `KRONOS_ENABLED=true` |
| **Software Advance** | Fallback when Kronos stalls | Kronos unavailable |
| **Snapshot Publisher** | State broadcast to UI (beat boundaries) | Always |
| **Loop Management** | Loop start/end enforcement | When `isLooping=true` |

### Key Entry Points

```typescript
// NVX1Score.tsx → calls this
useTransportStore.safePlay()

// Which calls this
unifiedKernelFacade.dispatch({ type: 'play' })

// Which executes
UnifiedKernelEngine.play() // Line 1065
  ├─ ensureToneContextUnlocked() // WebAudio autoplay policy
  ├─ initializeApollo() // Load guitar samples
  ├─ new KronosClock({ tempo, tickHz }) // WASM clock
  ├─ new AudioScheduler(callback) // Event queue
  └─ requestAnimationFrame(tick) // Start 60 FPS loop
```

### The Tick Loop (Heart of the System)

```typescript
// Line 2207: tick() function
const tick = (timestamp: number) => {
  if (!state.isPlaying || !state.score) {
    stopRaf();
    return;
  }

  const deltaMs = timestamp - lastTickMs;
  lastTickMs = timestamp;

  // 🎯 Decision: Use Kronos or software advance?
  const kronosState = isKronosActiveForScore 
    ? syncStateFromKronos(state, timestamp) 
    : null;

  let nextState: TransportState;

  if (usingSoftwareAdvance) {
    // Fallback: manual delta-based position calculation
    nextState = advancePosition(state, deltaMs);
  } else if (kronosState) {
    // Primary: Use WASM-calculated position
    nextState = kronosState;
  }

  state = applyLoopIfNeeded(nextState, timestamp);

  // 🔥 PERFORMANCE FIX: Only emit on beat boundaries (not every frame)
  if (positionChanged || stateChanged) {
    updateSnapshot(state);
  }

  rafId = requestAnimationFrame(tick);
};
```

**Performance Fix Applied:** Snapshot publishing reduced from **60 FPS → 2-4 FPS** (beat boundaries only). This prevents 240+ callback executions/sec across all subscribers.

---

## Legacy Systems (DEPRECATED or PHASED OUT)

### 1. Tone.Transport (Legacy Audio Library)

**Location:** `node_modules/tone/build/esm/`  
**Status:** ⚠️ **DEPRECATED - Being phased out**  
**Still Used For:**
- Initial Tone.start() unlock (autoplay policy)
- Fallback when Kronos unavailable
- Legacy AudioPlaybackService compatibility

**Why Deprecated:**
- Numeric `loopEnd` overrides break NVX1 looping (see lines 28-52)
- Can't handle 960 PPQ precision (limited to 192 PPQ)
- No sample-accurate scheduling

**Migration Path:** Remove after Apollo/AudioScheduler proven stable.

---

### 2. TransportKernel (Legacy Custom System)

**Location:** `src/services/transportKernel/TransportKernel.ts`  
**Status:** ⚠️ **DEPRECATED - Replaced by UnifiedKernelEngine**  
**Last Active:** Early 2024

**Why Replaced:**
- Didn't support Kronos integration
- No loop management
- Missing quantum timeline sync
- Couldn't coordinate multiple playback sources

**Still Referenced In:**
- UnifiedKernelFacade (fallback path, never executed)
- Old test files

**Migration Path:** Safe to delete after verification.

---

### 3. QuantumTimeline (UI State Layer)

**Location:** `src/store/quantum.ts`  
**Status:** ✅ **ACTIVE - UI-specific state only**  
**Lines of Code:** ~400 lines

**Purpose:** Manages **UI-specific** timeline state for the `/quantum` page.

```typescript
// What QuantumTimeline does:
- isPlaying (UI toggle state)
- currentMeasure (UI display)
- loopMarkers (UI visual indicators)
- quantumMode (UI feature toggle)

// What it does NOT do:
❌ Audio playback
❌ Timeline authority
❌ Note scheduling
```

**Relationship to UnifiedKernelEngine:**

```
┌────────────────────────┐      ┌────────────────────────┐
│  QuantumTimeline       │      │  UnifiedKernelEngine   │
│  (UI State)            │      │  (Timeline Authority)  │
│                        │      │                        │
│  isPlaying: boolean ───┼─────>│  state.isPlaying       │
│  currentMeasure: number│<─────┼─  snapshot.position    │
│  loopStart: Position   │─────>│  commands: set-loop    │
└────────────────────────┘      └────────────────────────┘
       ▲                                  │
       │                                  │
       │         snapshot events          │
       └──────────────────────────────────┘
```

**Key Insight:** QuantumTimeline is a **subscriber** to UnifiedKernelEngine, not a competitor.

---

### 4. KronosClock (High-Precision WASM Timer)

**Location:** `src/services/kronos/KronosClock.ts`  
**Status:** ✅ **ACTIVE - Embedded in UnifiedKernelEngine**  
**Technology:** Rust WASM compiled to JS

**Purpose:** Provides sample-accurate timing when precision matters.

```typescript
// Created inside UnifiedKernelEngine.play()
kronosClock = new KronosClock({
  tempo: state.tempo,
  tickHz: FEATURE_FLAGS.KRONOS_TICK_HZ, // Default: 960 Hz
  eventTarget: kronosEventTarget
});
```

**When Active:**
- `FEATURE_FLAGS.KRONOS_ENABLED === true`
- Score has playable note events
- Not in fallback mode

**When Inactive:**
- Feature flag off
- No notes in score (visual-only)
- Kronos stalled (falls back to software advance)

---

## Audio Scheduling: The Critical Path

```
User plays note → How does sound actually happen?

┌──────────────────────────────────────────────────────────┐
│ 1. UnifiedKernelEngine.play() starts KronosClock         │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│ 2. AudioScheduler.initWithKronos() subscribes to clock   │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│ 3. KronosClock emits scheduled events at exact times     │
│    Event: { time: 1234.567, note: "E2", velocity: 0.8 }  │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│ 4. AudioScheduler callback executes (line 1211)          │
│    const apolloInstance = window.Apollo.get()            │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│ 5. Apollo.playMelody([note], duration, volume)           │
│    (if isReady, else skip with warning)                  │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│ 6. Apollo → Tone.Sampler → WebAudioContext → speakers 🔊 │
└──────────────────────────────────────────────────────────┘
```

**Critical Insight:** There are **no intermediate layers**. This is a direct pipeline:
- KronosClock (timing) → AudioScheduler (routing) → Apollo (synthesis) → WebAudio (output)

---

## Feature Flags: What Controls What

**Location:** `src/utils/featureFlags.ts`

```typescript
export const FEATURE_FLAGS = {
  KRONOS_ENABLED: true,          // Master switch for KronosClock
  KRONOS_TICK_HZ: 960,           // Timing precision (960 PPQ)
  // ... other flags
}
```

| Flag | Effect | Default |
|------|--------|---------|
| `KRONOS_ENABLED=true` | Use KronosClock + AudioScheduler | `true` |
| `KRONOS_ENABLED=false` | Use legacy AudioPlaybackService + Tone.Transport | `false` |

**Migration Status (Nov 2025):**
- ✅ Kronos is default
- ⚠️ Legacy path still exists (safety fallback)
- 🎯 Goal: Remove legacy path by Q1 2026

---

## The Confusion: Where It Came From

### Timeline of Architectural Evolution

| Date | System Added | Reason |
|------|--------------|--------|
| **2023-Q1** | Tone.Transport | Initial playback (V1 project) |
| **2023-Q3** | TransportKernel | Custom timeline for NVX1 |
| **2024-Q1** | QuantumTimeline | UI state for `/quantum` page |
| **2024-Q3** | KronosClock | Sample-accurate WASM timing |
| **2024-Q4** | UnifiedKernelEngine | Merge all systems into one |
| **2025-Q1** | AudioScheduler | Replace AudioPlaybackService |

**Root Cause:** Each iteration added a new layer **without removing the old one**. This created:
- 5 systems that appear to do the same thing
- Unclear ownership (who's in charge?)
- Difficult debugging (which system caused the bug?)

---

## The Solution: Single Source of Truth

### Master Timeline Authority (TODAY)

```
┌─────────────────────────────────────────────────────────┐
│           UnifiedKernelEngine (MASTER)                  │
│                                                         │
│  • Owns all playback state                             │
│  • Single dispatch() entry point                       │
│  • Coordinates KronosClock when enabled                │
│  • Falls back to software advance when needed          │
│  • Publishes snapshots to all subscribers              │
└─────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
   │ NVX1Score UI │   │ Theater UI   │   │ Olympus UI   │
   │ (subscriber) │   │ (subscriber) │   │ (subscriber) │
   └──────────────┘   └──────────────┘   └──────────────┘
```

**Key Principle:** All UI components are **subscribers** to UnifiedKernelEngine. They **never** control playback directly.

---

## Debugging: Which System Is Running?

### Production Debug Commands (Browser Console)

```javascript
// Check if Kronos is active
window.__kronosClock
// ✅ Object → Kronos is running
// ❌ undefined → Using software advance

// Check AudioScheduler
window.__audioScheduler
// ✅ Object → Kronos path active
// ❌ undefined → Legacy AudioPlaybackService active

// Check NVX1 readiness
window.__nvxReady
// ✅ true → AudioScheduler registered
// ❌ undefined/false → Not ready

// Get current transport snapshot
unifiedKernelFacade.getSnapshot()
// Returns: { playState, tempo, position, loop, currentChord }

// Check which kernel is active
// Open UnifiedKernelFacade.ts and look for console log on line 37
// Should always say "using unified kernel"
```

### Log Markers to Watch

```
✅ Good Logs (Expected):
[UnifiedKernelEngine] play initiated { sessionToken: 1 }
[Kronos] loadScore → ok { events: 1234, measures: 32 }
[AudioScheduler→Apollo] Apollo.playMelody: { note: "E2", volume: 0.85 }

🚨 Bad Logs (Problems):
[UnifiedKernelEngine] ⚠️ NO SCORE - cannot play!
[AudioScheduler→Apollo] ⚠️ Apollo not ready (isReady=false)
[UnifiedKernelEngine] kronos state stalled, switching to software advance
```

---

## Migration Roadmap

### Phase 1: Current State (Nov 2025)
- [x] UnifiedKernelEngine is master
- [x] KronosClock + AudioScheduler active
- [x] Tone.Transport in fallback mode only
- [ ] TransportKernel still referenced (unused)
- [ ] QuantumTimeline as UI-only layer

### Phase 2: Cleanup (Dec 2025)
- [ ] Remove TransportKernel.ts
- [ ] Remove Tone.Transport dependency
- [ ] Remove legacy AudioPlaybackService
- [ ] Document QuantumTimeline as UI-state-only

### Phase 3: Consolidation (Q1 2026)
- [ ] Single timeline system (UnifiedKernelEngine)
- [ ] No fallback paths
- [ ] Clear separation: Engine (logic) vs Stores (UI state)

---

## Decision Log

### Why UnifiedKernelEngine Won

| Requirement | UnifiedKernelEngine | TransportKernel | Tone.Transport |
|-------------|---------------------|-----------------|----------------|
| 960 PPQ precision | ✅ Via Kronos | ❌ 192 PPQ max | ❌ 192 PPQ |
| Loop management | ✅ Built-in | ❌ Manual | ⚠️ Buggy |
| Multi-source sync | ✅ Coordinator | ❌ None | ❌ None |
| WASM integration | ✅ KronosClock | ❌ No | ❌ No |
| Sample-accurate | ✅ AudioScheduler | ❌ No | ⚠️ Timing drift |
| Snapshot pub/sub | ✅ Beat boundaries | ❌ Polling | ❌ Events only |

---

## Summary: What You Need to Know

### For Daily Development

1. **Ignore Tone.Transport** - it's legacy, only used for unlock
2. **Ignore TransportKernel** - it's dead code
3. **QuantumTimeline is UI state only** - not timeline authority
4. **UnifiedKernelEngine is the master** - all playback flows through it
5. **KronosClock is an implementation detail** - embedded in UnifiedKernelEngine

### The Call Chain (Memorize This)

```
User clicks PLAY
  ↓
NVX1Score.handlePlayPause()
  ↓
useTransportStore.safePlay()
  ↓
unifiedKernelFacade.dispatch({ type: 'play' })
  ↓
UnifiedKernelEngine.play()
  ↓
KronosClock.start() + AudioScheduler.init()
  ↓
requestAnimationFrame(tick) loop
  ↓
Apollo.playMelody() → 🔊 Sound
```

### What to Delete (When Ready)

- `src/services/transportKernel/TransportKernel.ts` (unused)
- `src/services/AudioPlaybackService.ts` (replaced by AudioScheduler)
- Tone.Transport references (after Apollo stable)

---

## Related Documents

- **Audio Pipeline:** See `04-AUDIO-PIPELINE.md`
- **Data Flow:** See `05-DATA-FLOW.md`
- **Container Architecture:** See `02-CONTAINER-ARCHITECTURE.md`

---

**Document Owner:** Lead Architect (Mark van den Dool)  
**Last Reviewed:** November 13, 2025  
**Next Review:** December 2025 (after Phase 2 cleanup)
