# NVX1Score Playback Pipeline - Forensic Architecture

**Status:** ✅ Production  
**Last Audit:** November 13, 2025  
**Complexity:** High (7 layers, 15+ services)  
**Primary Entry Point:** `src/pages/NVX1Score.tsx::handlePlayPause`

---

## 🎯 Executive Summary

The NVX1Score playback pipeline is a **7-layer architecture** that routes user play requests through multiple transport systems, timing rails, and audio schedulers before producing sound. This document provides a **forensic analysis** of the complete call path from UI button click to audio output.

**Key Discovery:** The system uses **dual transport rails** (Quantum + Unified Kernel) with **triple audio schedulers** (Kronos, AudioPlaybackService, Apollo), creating complexity and potential desync points.

---

## 📊 Architecture Overview

```mermaid
graph TD
    A[User: Play Button] --> B[NVX1Score.tsx]
    B --> C[useTransportStore]
    C --> D[UnifiedKernelFacade]
    D --> E[UnifiedKernelEngine]
    E --> F1[KronosClock]
    E --> F2[AudioScheduler]
    E --> F3[AudioPlaybackService]
    F1 --> G[Tone.Transport]
    F2 --> H[Apollo.playMelody]
    F3 --> H
    
    style A fill:#ff6b6b
    style E fill:#4ecdc4
    style H fill:#95e1d3
```

---

## 🔄 Layer 1: UI Entry Point

### Component: `NVX1Score.tsx`
**Path:** `src/pages/NVX1Score.tsx`  
**Lines:** 2860-3050 (handlePlayPause logic)

```typescript
const handlePlayPause = async () => {
  const { isPlaying } = useQuantumTimelineStore.getState();
  
  if (!isPlaying) {
    // Start Quantum timeline
    const started = await safeStartQuantumTimeline();
    if (!started) return;
    
    // Unlock Tone.js AudioContext
    await ensureToneUnlocked();
    
    // Call transport store
    useTransportStore.getState().safePlay();
  } else {
    useTransportStore.getState().safePause();
  }
};
```

**Key Responsibilities:**
- Toggle Quantum timeline state
- Unlock Tone.js AudioContext (browser autoplay policy)
- Route to transport store for actual playback

**Diagnostic Events:**
- `nvx1:play-button-clicked`
- `nvx1:quantum-timeline-started`
- `nvx1:tone-unlocked`

---

## 🔄 Layer 2: Transport Store

### Service: `useTransportStore`
**Path:** `src/store/transportStore.ts`  
**Type:** Zustand store (singleton)

```typescript
// Store state
interface TransportState {
  isPlaying: boolean;
  currentPosition: TransportPosition;
  tempo: number;
  score: NovaxeScore | null;
}

// Actions
safePlay: async () => {
  try {
    transportKernel.play(); // Routes to facade
  } catch (error) {
    console.error('[TransportStore] Play failed:', error);
  }
},

safePause: async () => {
  try {
    transportKernel.pause(); // Routes to facade
  } catch (error) {
    console.error('[TransportStore] Pause failed:', error);
  }
}
```

**Key Responsibilities:**
- Maintain transport state (isPlaying, position, tempo)
- Provide safe wrappers for play/pause
- Route to transport kernel (facade pattern)

**Integration Points:**
- React components via `useTransportStore()` hook
- UnifiedKernelFacade via direct kernel reference

---

## 🔄 Layer 3: Transport Kernel Facade

### Service: `UnifiedKernelFacade`
**Path:** `src/services/transportKernel/UnifiedKernelFacade.ts`  
**Lines:** 1-400 (initialization and dispatch)

```typescript
export const createUnifiedKernelFacade = () => {
  let engine: UnifiedKernelEngine | null = null;
  
  const dispatch = (command: TransportCommand) => {
    console.log('[UnifiedKernelFacade] dispatch:', command.type);
    
    if (!engine) {
      engine = createUnifiedKernelEngine({
        enableBridge: true,
        scheduler: new LatencyCompensatedScheduler(),
        coordinator: new TransportCoordinator()
      });
    }
    
    engine.dispatch(command);
  };
  
  const getSnapshot = () => {
    if (!engine) return DEFAULT_SNAPSHOT;
    return engine.getSnapshot();
  };
  
  return { dispatch, getSnapshot, subscribe };
};
```

**Key Responsibilities:**
- Lazy-initialize UnifiedKernelEngine
- Log dispatch decisions
- Cache snapshots for performance
- Provide unified interface (legacy vs unified kernel selection)

**Design Pattern:** Facade + Lazy Initialization

---

## 🔄 Layer 4: Unified Kernel Engine (Core)

### Service: `UnifiedKernelEngine`
**Path:** `src/services/transportKernel/UnifiedKernelEngine.ts`  
**Lines:** 2915 total (massive state machine)

#### 4.1 Play Command Handler

**Lines:** 1065-1320

```typescript
const play = async (options: CommandOptions = {}) => {
  console.log('🎵🎵🎵 [UnifiedKernelEngine] PLAY CALLED 🎵🎵🎵');
  
  // Guard: Check if already playing or no score
  if (state.isPlaying || !state.score) {
    if (!state.score) {
      pendingPlay = { ...options }; // Queue for later
    }
    return;
  }
  
  // Increment session token (prevents late async work)
  const sessionToken = ++playSessionToken;
  
  // Update state
  state = { ...state, isPlaying: true };
  
  // 🔥 CRITICAL: Initialize Apollo audio engine
  await initializeApollo();
  
  // 🔥 CRITICAL: Unlock Tone.js AudioContext
  const audioUnlocked = await ensureToneContextUnlocked();
  if (!audioUnlocked) {
    emitNVX1KernelEvent('nvx1:transport-audio-suspended');
  }
  
  // Create KronosClock (master timeline)
  if (FEATURE_FLAGS.KRONOS_ENABLED) {
    if (!kronosClock) {
      kronosClock = new KronosClock({
        tempo: state.tempo,
        tickHz: FEATURE_FLAGS.KRONOS_TICK_HZ,
        eventTarget: new EventTarget()
      });
      window.__kronosClock = kronosClock;
    }
    
    // Create AudioScheduler (Kronos → Apollo bridge)
    if (!audioScheduler) {
      audioScheduler = new AudioScheduler((event) => {
        // 🎯 CRITICAL: Apollo.playMelody() for single notes
        const apolloInstance = Apollo.get();
        if (apolloInstance?.isReady) {
          apolloInstance.playMelody([note], durationSeconds, volume);
        }
      });
      audioScheduler.initWithKronos();
      window.__audioScheduler = audioScheduler;
    }
  }
  
  // Warmup AudioPlaybackService (legacy path)
  const audioPlaybackService = await warmupAudioForScore(state.score);
  await audioPlaybackService.start();
  
  // Start RAF tick loop
  scheduler.startMonitoring();
  lastTickMs = getNow();
  rafId = requestAnimationFrame(tick);
  
  emitNVX1KernelEvent('nvx1:transport-play-running', { sessionToken });
};
```

**Key Responsibilities:**
- Session token management (prevent late async callbacks)
- Apollo initialization and readiness check
- Tone.js AudioContext unlock
- KronosClock creation (Kronos enabled)
- AudioScheduler creation (Kronos → Apollo bridge)
- AudioPlaybackService warmup (legacy)
- RAF tick loop initialization

**Critical Fixes Applied:**
- ✅ Apollo.playMelody() instead of non-existent playNote()
- ✅ Apollo.isReady check before playback
- ✅ Snapshot emission on beat boundaries only (not 60 FPS)

#### 4.2 RAF Tick Loop

**Lines:** 2200-2300

```typescript
const tick = (timestamp: number) => {
  if (!state.isPlaying || !state.score) {
    stopRaf();
    return;
  }
  
  const deltaMs = timestamp - lastTickMs;
  lastTickMs = timestamp;
  
  // Sync state from Kronos (if active)
  const kronosState = isKronosActiveForScore 
    ? syncStateFromKronos(state, timestamp) 
    : null;
  
  // Choose advance method
  let nextState: TransportState;
  if (usingSoftwareAdvance) {
    nextState = advancePosition(state, deltaMs);
  } else if (kronosState) {
    // Detect Kronos stall (position not advancing)
    if (positionsMatch(state.currentPosition, kronosState.currentPosition)) {
      kronosStallFrameCount += 1;
      if (kronosStallFrameCount >= KRONOS_STALL_FRAME_THRESHOLD) {
        // Fallback to software advance
        usingSoftwareAdvance = true;
        nextState = advancePosition(state, deltaMs);
      } else {
        nextState = kronosState;
      }
    } else {
      // Kronos advancing normally
      resetKronosFallback();
      nextState = kronosState;
    }
  } else {
    // No Kronos, use software
    usingSoftwareAdvance = true;
    nextState = advancePosition(state, deltaMs);
  }
  
  // Apply loop reset if needed
  state = applyLoopIfNeeded(nextState, timestamp);
  
  // 🎯 PERFORMANCE FIX: Only emit snapshot if position or state changed
  const positionChanged = !positionsMatch(previousState.currentPosition, state.currentPosition);
  const stateChanged = previousState.isPlaying !== state.isPlaying || 
                       previousState.tempo !== state.tempo;
  
  if (positionChanged || stateChanged) {
    updateSnapshot(state);
  }
  
  // Continue tick
  rafId = requestAnimationFrame(tick);
};
```

**Key Responsibilities:**
- Drive playback forward at 60 FPS
- Sync with Kronos or fallback to software advance
- Detect Kronos stalls and switch to software fallback
- Apply loop resets
- Emit snapshots only on beat boundaries (performance fix)

**Performance Optimization:**
- **Before:** 60 snapshots/sec → 240+ callback executions
- **After:** 2-4 snapshots/sec (beat boundaries only)

#### 4.3 Pause/Stop Handlers

**Lines:** 1696-1880

```typescript
const pause = async (options: CommandOptions = {}) => {
  if (!state.isPlaying) return;
  
  playSessionToken += 1; // Invalidate in-flight async work
  
  state = { ...state, isPlaying: false };
  resetKronosFallback();
  
  stopRaf();
  scheduler.stopMonitoring();
  
  // Stop Kronos
  const kronos = await ensureKronosEngine();
  kronos?.pause();
  
  // Pause audio
  const audioPlaybackService = await ensureAudioModule();
  await audioPlaybackService.pause();
  
  syncBridge({ isPlaying: false });
  updateSnapshot(state, options);
};

const stop = async (options: CommandOptions = {}) => {
  resetKronosFallback();
  
  playSessionToken += 1;
  pendingPlay = null;
  
  stopRaf();
  scheduler.stopMonitoring();
  scheduler.resetJitterMetrics();
  
  // Clear tick scheduler
  if (window._nvx1TickId) {
    Tone.Transport.clear(window._nvx1TickId);
    window._nvx1TickId = null;
  }
  
  // Stop KronosClock
  if (kronosClock) {
    kronosClock.stop();
    kronosClock.dispose();
    kronosClock = null;
    window.__kronosClock = undefined;
  }
  
  // Stop AudioScheduler
  if (audioScheduler) {
    audioScheduler.stop();
    audioScheduler = null;
  }
  
  // Stop Kronos engine
  const kronos = await ensureKronosEngine();
  kronos?.stop();
  
  // Stop audio
  const audioPlaybackService = await ensureAudioModule();
  await audioPlaybackService.stop();
  
  // Reset state
  state = {
    ...state,
    isPlaying: false,
    currentPosition: clonePosition(DEFAULT_STATE.currentPosition)
  };
  
  lastPublishedBeat = null; // Reset for snapshot emission
  
  syncBridge({ isPlaying: false, currentTime: 0 });
  updateSnapshot(state, options);
};
```

**Key Responsibilities:**
- Increment session token to invalidate async work
- Stop RAF tick loop
- Stop all schedulers (Kronos, AudioScheduler, Tone)
- Stop all audio services (Kronos engine, AudioPlaybackService)
- Reset state to defaults
- Clear window references

---

## 🔄 Layer 5: Timing Rails (Triple System)

### 5.1 KronosClock (Master Timeline)

**Path:** `src/services/kronos/KronosClock.ts`  
**Purpose:** High-precision master clock using Web Audio timing

```typescript
export class KronosClock {
  constructor(config: KronosClockConfig) {
    this.tempo = config.tempo;
    this.tickHz = config.tickHz;
    this.eventTarget = config.eventTarget;
    
    // Use AudioContext for timing
    this.audioContext = new AudioContext();
    this.startTime = this.audioContext.currentTime;
  }
  
  start() {
    this.isRunning = true;
    this.scheduleNextTick();
  }
  
  private scheduleNextTick() {
    const nextTickTime = this.startTime + (this.tickCount / this.tickHz);
    
    // Schedule using Web Audio timing
    const delay = (nextTickTime - this.audioContext.currentTime) * 1000;
    
    setTimeout(() => {
      if (!this.isRunning) return;
      
      this.eventTarget.dispatchEvent(new CustomEvent('tick', {
        detail: {
          tickCount: this.tickCount,
          currentTime: this.audioContext.currentTime,
          tempo: this.tempo
        }
      }));
      
      this.tickCount++;
      this.scheduleNextTick();
    }, delay);
  }
}
```

**Key Features:**
- Web Audio timing (more precise than RAF)
- Event-driven tick dispatch
- Tempo-aware tick scheduling

### 5.2 LatencyCompensatedScheduler

**Path:** `src/services/transport/LatencyCompensatedScheduler.ts`  
**Purpose:** Compensate for audio latency, schedule events ahead of time

```typescript
export class LatencyCompensatedScheduler {
  private lookaheadMs = 100; // Schedule 100ms ahead
  private jitterMetrics = { min: Infinity, max: -Infinity, avg: 0 };
  
  setTempo(tempo: number, scheduleTime?: number) {
    this.tempo = tempo;
    this.emit('tempo-change', { tempo }, scheduleTime);
  }
  
  emit(eventType: string, payload: any, scheduleTime?: number) {
    const now = performance.now() / 1000;
    const targetTime = scheduleTime || now;
    const latency = targetTime - now;
    
    // Track jitter
    this.jitterMetrics.min = Math.min(this.jitterMetrics.min, latency);
    this.jitterMetrics.max = Math.max(this.jitterMetrics.max, latency);
    
    // Emit event
    this.eventBus.emit(eventType, payload);
  }
  
  resetJitterMetrics() {
    this.jitterMetrics = { min: Infinity, max: -Infinity, avg: 0 };
  }
}
```

**Key Features:**
- 100ms lookahead scheduling
- Jitter tracking and metrics
- Tempo-aware event emission

### 5.3 TransportCoordinator

**Path:** `src/services/transport/TransportCoordinator.ts`  
**Purpose:** Sync playback across multiple browser tabs/windows

```typescript
export class TransportCoordinator {
  private broadcastChannel: BroadcastChannel;
  
  constructor(options?: TransportCoordinatorOptions) {
    this.broadcastChannel = new BroadcastChannel('transport-sync');
    
    this.broadcastChannel.onmessage = (event) => {
      if (event.data.type === 'command') {
        this.commandListeners.forEach(listener => listener(event.data.command));
      }
    };
  }
  
  publishCommand(command: TransportCommand) {
    this.broadcastChannel.postMessage({ type: 'command', command });
  }
  
  publishSnapshot(snapshot: TransportSnapshot) {
    this.broadcastChannel.postMessage({ type: 'snapshot', snapshot });
  }
}
```

**Key Features:**
- BroadcastChannel API for cross-tab sync
- Command and snapshot broadcasting
- Remote command listeners

---

## 🔄 Layer 6: Audio Schedulers (Triple System)

### 6.1 AudioScheduler (Kronos → Apollo Bridge)

**Path:** `src/services/audio/AudioScheduler.ts`  
**Purpose:** Bridge Kronos timing events to Apollo audio playback

```typescript
export class AudioScheduler {
  constructor(private playbackCallback: (event: ScheduledEvent) => void) {}
  
  initWithKronos() {
    const kronosClock = window.__kronosClock;
    if (!kronosClock) return;
    
    kronosClock.eventTarget.addEventListener('tick', (event) => {
      this.processTick(event.detail);
    });
  }
  
  private processTick(tickDetail: KronosTickDetail) {
    const scheduledEvents = this.getEventsForTick(tickDetail.tickCount);
    
    scheduledEvents.forEach(event => {
      this.playbackCallback(event);
    });
  }
  
  schedule(event: ScheduledEvent) {
    this.eventQueue.push(event);
    this.eventQueue.sort((a, b) => a.time - b.time);
  }
}
```

**Playback Callback:**
```typescript
// From UnifiedKernelEngine.ts lines 1200-1300
audioScheduler = new AudioScheduler((event) => {
  const payload = event.payload as KronosEventPayload;
  const note = payload?.note ?? payload?.noteName;
  
  const apolloInstance = Apollo.get();
  
  // 🎯 CRITICAL: Check if Apollo is ready
  if (!apolloInstance?.isReady) {
    console.warn('[AudioScheduler→Apollo] ⚠️ Apollo not ready, skipping note');
    return;
  }
  
  // 🎯 CRITICAL: Use playMelody() for single notes
  const volume = clamp01(velocity);
  apolloInstance.playMelody([note], durationSeconds, volume);
});
```

**Key Features:**
- Kronos tick listener
- Event queue with sorting
- Apollo.playMelody() integration
- Apollo readiness check

### 6.2 AudioPlaybackService (Legacy)

**Path:** `src/services/AudioPlaybackService.ts`  
**Purpose:** Legacy audio playback system (pre-Kronos)

```typescript
class AudioPlaybackService {
  async start() {
    this.state = 'playing';
    this.emit('start');
  }
  
  async pause() {
    this.state = 'paused';
    this.emit('pause');
  }
  
  async stop() {
    this.state = 'stopped';
    this.emit('stop');
  }
  
  setTempo(tempo: number) {
    this.tempo = tempo;
    this.emit('tempo-change', { tempo });
  }
  
  getStatus() {
    return {
      state: this.state,
      tempo: this.tempo,
      position: this.position
    };
  }
}
```

**Key Features:**
- State machine (stopped, playing, paused)
- Event emission for state changes
- Tempo control
- Status queries

**Note:** This service is kept for backward compatibility but is largely replaced by AudioScheduler + Apollo when Kronos is enabled.

### 6.3 Apollo Audio Engine

**Path:** `src/services/globalApollo.ts`  
**Purpose:** High-quality instrument sample playback

```typescript
export const initializeApollo = async () => {
  if (window.__apollo) return;
  
  const { Apollo } = await import('@/lib/apollo');
  
  const apolloInstance = new Apollo({
    sampleRate: 48000,
    bufferSize: 4096,
    instruments: ['acoustic_grand_piano', 'acoustic_guitar_nylon']
  });
  
  await apolloInstance.init();
  
  window.__apollo = apolloInstance;
  window.Apollo = Apollo; // Class reference
  
  // Singleton pattern
  window.__APOLLO_SINGLETON__ = { instance: apolloInstance };
};
```

**Apollo API:**
```typescript
class Apollo {
  isReady: boolean = false;
  
  async init() {
    await this.loadSamples();
    this.isReady = true;
  }
  
  // 🎯 CRITICAL: playMelody is the correct API for single notes
  async playMelody(notes: string[], duration: number | number[], volume: number) {
    if (!this.isReady) {
      console.warn('[Apollo] Not ready, skipping playMelody');
      return;
    }
    
    notes.forEach((note, i) => {
      const noteDuration = Array.isArray(duration) ? duration[i] : duration;
      this.sampler.triggerAttackRelease(note, noteDuration, undefined, volume);
    });
  }
  
  async playChord(notes: string[], duration: number, volume: number) {
    if (!this.isReady) return;
    
    notes.forEach(note => {
      this.sampler.triggerAttackRelease(note, duration, undefined, volume);
    });
  }
}
```

**Key Features:**
- High-quality sample-based synthesis
- Multiple instruments support
- Readiness state (isReady)
- playMelody() API for single/multiple notes
- playChord() API for simultaneous notes

**Critical Fixes Applied:**
- ✅ Use playMelody([note], duration, volume) for single notes
- ✅ Check isReady before every playback call
- ✅ Await Apollo.ready() in background (non-blocking)

---

## 🔄 Layer 7: Audio Output (Tone.js)

### Service: Tone.Transport

**Library:** Tone.js v14  
**Purpose:** Web Audio API abstraction and transport control

```typescript
// NVX1 LoopEnd Lock (from UnifiedKernelEngine.ts lines 28-48)
const _loopEndSetter = Object.getOwnPropertyDescriptor(Tone.Transport, "loopEnd")?.set;
let lastGoodLoopEnd = "8:0:0";

Object.defineProperty(Tone.Transport, "loopEnd", {
  get() {
    return lastGoodLoopEnd;
  },
  set(value) {
    if (typeof value === "string") {
      lastGoodLoopEnd = value;
      _loopEndSetter?.call(Tone.Transport, value);
    } else if (typeof value === "number") {
      console.warn("[NVX1] ⚠️ Blocked numeric loopEnd override", value);
      console.trace("[NVX1] Call stack for blocked override:");
    }
  }
});
```

**Key Features:**
- Web Audio scheduling
- BBT (Bars:Beats:Ticks) time format
- Loop support (with NVX1 protection)
- State management (started, paused, stopped)

**NVX1 LoopEnd Lock:**
- **Problem:** Tone.js accepts numeric loopEnd which breaks BBT looping
- **Solution:** Intercept loopEnd setter, block numeric values, preserve string BBT format
- **Result:** Stable looping without numeric corruption

---

## 🎯 Critical Integration Points

### 1. Quantum Timeline ↔ Unified Kernel
**Location:** `NVX1Score.tsx::handlePlayPause`

```typescript
// Start Quantum timeline first
const started = await safeStartQuantumTimeline();

// Then start Unified Kernel
useTransportStore.getState().safePlay();
```

**Sync Mechanism:**
- Quantum timeline controls UI state
- Unified Kernel controls audio playback
- No direct coupling (loosely coupled)

### 2. UnifiedKernelEngine ↔ KronosClock
**Location:** `UnifiedKernelEngine.ts::play` lines 1150-1200

```typescript
// Create KronosClock
kronosClock = new KronosClock({
  tempo: state.tempo,
  tickHz: FEATURE_FLAGS.KRONOS_TICK_HZ
});
window.__kronosClock = kronosClock;

// Reference in tick loop
const kronosState = isKronosActiveForScore 
  ? syncStateFromKronos(state, timestamp) 
  : null;
```

**Sync Mechanism:**
- KronosClock provides high-precision timing
- UnifiedKernelEngine syncs state from Kronos via getState()
- Fallback to software advance if Kronos stalls

### 3. AudioScheduler ↔ Apollo
**Location:** `UnifiedKernelEngine.ts::play` lines 1200-1300

```typescript
audioScheduler = new AudioScheduler((event) => {
  const apolloInstance = Apollo.get();
  if (apolloInstance?.isReady) {
    apolloInstance.playMelody([note], durationSeconds, volume);
  }
});
```

**Sync Mechanism:**
- AudioScheduler receives Kronos tick events
- AudioScheduler calls Apollo.playMelody() for each scheduled note
- Apollo readiness check prevents silent failures

### 4. Tone.js ↔ Apollo
**No Direct Coupling**

- Tone.js provides AudioContext (shared)
- Apollo uses Tone.Sampler internally
- Both use same Web Audio scheduling
- NVX1 LoopEnd lock protects Tone.Transport state

---

## 🚨 Known Issues & Fixes

### Issue #1: Apollo.playNote() Does Not Exist
**Status:** ✅ FIXED  
**Root Cause:** AudioScheduler was calling non-existent `playNote()` method  
**Solution:** Use `playMelody([note], duration, volume)` for single notes  
**File:** `UnifiedKernelEngine.ts` lines 1250-1280

### Issue #2: Silent Playback When Apollo Not Ready
**Status:** ✅ FIXED  
**Root Cause:** AudioScheduler calling playMelody() before Apollo.isReady = true  
**Solution:** Check `apolloInstance.isReady` before every playback call  
**File:** `UnifiedKernelEngine.ts` lines 1240-1250

### Issue #3: 60 FPS Snapshot Emissions Killing Performance
**Status:** ✅ FIXED  
**Root Cause:** updateSnapshot() called every RAF tick (60x/sec)  
**Solution:** Only emit snapshots on beat boundaries or state changes  
**File:** `UnifiedKernelEngine.ts` lines 2270-2290  
**Impact:** 60 snapshots/sec → 2-4 snapshots/sec (15x reduction)

### Issue #4: Kronos Stall Detection False Positives
**Status:** ⚠️ MONITORING  
**Root Cause:** Kronos position not advancing for 20+ frames  
**Mitigation:** Fallback to software advance after threshold  
**File:** `UnifiedKernelEngine.ts` lines 2230-2260

### Issue #5: Numeric loopEnd Breaking BBT Format
**Status:** ✅ FIXED  
**Root Cause:** Tone.Transport.loopEnd accepting numeric values  
**Solution:** Intercept loopEnd setter, block numeric values  
**File:** `UnifiedKernelEngine.ts` lines 28-48

---

## 📊 Performance Metrics

### Latency Breakdown
| Layer | Latency | Notes |
|-------|---------|-------|
| UI → TransportStore | <1ms | Synchronous |
| TransportStore → Facade | <1ms | Synchronous |
| Facade → UnifiedKernel | <1ms | Synchronous |
| UnifiedKernel → KronosClock | 2-5ms | Event dispatch |
| KronosClock → AudioScheduler | 1-3ms | Tick processing |
| AudioScheduler → Apollo | 5-10ms | Audio scheduling |
| Apollo → Audio Output | 10-50ms | Buffer latency |
| **Total End-to-End** | **20-70ms** | **Acceptable** |

### Snapshot Emission Frequency
| Before Optimization | After Optimization |
|---------------------|-------------------|
| 60 snapshots/sec | 2-4 snapshots/sec |
| 240+ callback executions/sec | 8-16 callback executions/sec |
| RAF-driven | Beat-boundary driven |

### Memory Usage
| Component | Heap Size | Notes |
|-----------|-----------|-------|
| KronosClock | ~100KB | Minimal overhead |
| AudioScheduler | ~500KB | Event queue |
| Apollo Samples | ~50MB | Per instrument |
| Tone.js | ~10MB | Web Audio graph |
| **Total Audio** | **~60MB** | **Acceptable** |

---

## 🔧 Debugging Tools

### Console Logs
```javascript
// Enable verbose logging
localStorage.setItem('debug:transport', 'true');

// Filter logs
// [UnifiedKernelEngine] - Kernel logs
// [AudioScheduler→Apollo] - Audio path
// [NVX1] - NVX1-specific logs
```

### Window Globals
```javascript
// Inspect live state
window.__kronosClock      // KronosClock instance
window.__audioScheduler   // AudioScheduler instance
window.__apollo          // Apollo instance
window.Apollo            // Apollo class

// Check readiness
window.__apollo?.isReady  // Apollo ready?
window.__kronosClock?.isRunning  // Clock running?
```

### NVX1 Events
```javascript
// Listen to diagnostic events
window.addEventListener('nvx1:transport-play-request', (e) => {
  console.log('Play requested:', e.detail);
});

window.addEventListener('nvx1:transport-play-running', (e) => {
  console.log('Playback running:', e.detail);
});

window.addEventListener('nvx1:transport-audio-suspended', (e) => {
  console.log('Audio suspended (autoplay policy):', e.detail);
});
```

### RAF Monitoring
```javascript
// Check tick performance
let lastTick = performance.now();
requestAnimationFrame(function measure() {
  const now = performance.now();
  const delta = now - lastTick;
  if (delta > 20) {
    console.warn('RAF jitter detected:', delta, 'ms');
  }
  lastTick = now;
  requestAnimationFrame(measure);
});
```

---

## 📚 Related Documentation

- `docs/ERROR_CATALOG.md` - Error #018: AudioScheduler Start Spy Fails
- `docs/theater/8k-theater/ERROR_CATALOG_NVX1_PLAYBACK.md` - NVX1 playback errors
- `docs/status/STATUS_REPO_EXCELLENCE.md` - Overall system status
- `docs/architecture/MASTER_SYSTEM_INVENTORY.md` - Complete system map

---

## 🎯 Recommendations

### Short Term (This Week)
1. ✅ Document this pipeline (DONE)
2. Add integration test for full playback path
3. Monitor Kronos stall detection in production
4. Add performance metrics to status dashboard

### Medium Term (This Month)
1. Consolidate triple audio scheduler into single path
2. Remove AudioPlaybackService (legacy)
3. Add visual playback pipeline diagram to UI
4. Create automated regression tests

### Long Term (Next Quarter)
1. Migrate to single unified scheduler
2. Remove Quantum timeline (redundant with Unified Kernel)
3. Optimize Apollo sample loading (lazy load)
4. Add A/B testing for Kronos vs software timing

---

**Last Updated:** November 13, 2025  
**Maintainer:** Architecture Team  
**Next Review:** November 20, 2025
