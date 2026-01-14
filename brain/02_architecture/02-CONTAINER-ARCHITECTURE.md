# 02 - Container Architecture Diagram (C4 Level 2)

**Audience:** Senior engineers, solution architects  
**Purpose:** Understand major technical components and communication patterns

---

## Container Overview

MindSong JukeHub is a **browser-based single-page application** with the following high-level containers:

```mermaid
C4Container
    title Container Architecture - MindSong JukeHub (C4 Level 2)

    Person(user, "User", "Student/Teacher/Composer")

    Container_Boundary(browser, "Web Browser") {
        Container(spa, "React SPA", "TypeScript, React 18", "Main application UI, routing, state management")
        Container(stores, "Zustand Stores", "State management", "Global state (transport, scores, UI)")
        Container(kernel, "Transport Kernel", "UnifiedKernelEngine", "Timeline authority, playback coordination")
        
        ContainerDb(indexeddb, "IndexedDB", "Browser storage", "Cached scores, user settings, offline data")
    }

    Container_Boundary(workers, "Web Workers") {
        Container(kronos, "Kronos Engine", "Rust WASM", "High-precision timeline, 960 PPQ scheduling")
        Container(audioSched, "Audio Scheduler", "TypeScript", "Event queue, latency compensation")
        Container(videoEnc, "Video Encoder", "Canvas API", "Theater mode recording")
    }

    Container_Boundary(audio, "Web Audio Context") {
        Container(tone, "Tone.js Transport", "JavaScript", "Legacy timeline (being phased out)")
        Container(apollo, "Apollo.js Sampler", "Custom engine", "18K LOC guitar/piano sample playback")
        Container(webaudio, "Web Audio Nodes", "Browser API", "Effects, mixing, master output")
    }

    System_Ext(supabase, "Supabase", "Backend services")
    System_Ext(ai, "AI Services", "HuggingFace")

    Rel(user, spa, "Interacts with", "HTTPS")
    Rel(spa, stores, "Reads/writes state")
    Rel(stores, kernel, "Dispatches commands")
    Rel(kernel, kronos, "Syncs timeline", "postMessage")
    Rel(kernel, audioSched, "Schedules events", "postMessage")
    Rel(audioSched, apollo, "Triggers notes")
    Rel(apollo, webaudio, "Connects to")
    Rel(kernel, tone, "Fallback sync")
    Rel(spa, indexeddb, "Persists data")
    Rel(spa, supabase, "API calls", "HTTPS/WebSocket")
    Rel(spa, ai, "Generates audio/chords", "HTTPS")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

---

## Container Inventory

### 1️⃣ **React SPA** (Main Thread)

| Aspect | Details |
|--------|---------|
| **Technology** | React 18, TypeScript, Vite |
| **Size** | ~2MB bundle (minified + gzipped) |
| **Responsibilities** | - UI rendering (20+ pages)<br>- User input handling<br>- Routing (`/nvx1-score`, `/theater`, `/olympus`, etc.)<br>- Component lifecycle |
| **Key Pages** | `NVX1Score.tsx`, `Theater.tsx`, `Olympus.tsx`, `MSM.tsx`, `Quantum.tsx`, `MIDI-test.tsx` |
| **State Management** | Zustand stores (15+ stores) |
| **Deployment** | CDN (Vercel/Netlify), served as static files |

**Critical Insight:** Main thread is **UI-only**. All heavy computation moved to workers.

---

### 2️⃣ **Zustand Stores** (State Layer)

| Store | Purpose | Size | Critical? |
|-------|---------|------|-----------|
| `useTransportStore` | Playback state (play/pause/seek) | 500 LOC | 🔴 Critical |
| `useNVX1Store` | Score data (parts, measures, notes) | 800 LOC | 🔴 Critical |
| `useQuantumStore` | Quantum timeline state | 400 LOC | 🟡 Medium |
| `useOlympusStore` | Olympus page config | 300 LOC | 🟢 Optional |
| `useScoreStore` | V3 score format | 600 LOC | 🔴 Critical |
| `useToussaintMetronomeStore` | Metronome settings | 200 LOC | 🟢 Optional |
| ... | *10+ more stores* | ... | ... |

**Architecture Pattern:** Stores subscribe to **Transport Kernel** via `useSyncExternalStore` for reactivity.

```typescript
// Example: How stores sync with kernel
const snapshot = useSyncExternalStore(
  unifiedKernelFacade.subscribe('snapshot'),
  unifiedKernelFacade.getSnapshot
);
```

---

### 3️⃣ **Transport Kernel** (Timeline Authority)

```mermaid
graph TB
    subgraph "Transport Kernel Layers"
        A[UnifiedKernelFacade<br/>Public API]
        B[UnifiedKernelEngine<br/>Core logic]
        C[TransportCoordinator<br/>Multi-client sync]
        D[LatencyCompensatedScheduler<br/>Timing accuracy]
    end
    
    E[Zustand Stores] --> A
    A --> B
    B --> C
    B --> D
    B --> F[Kronos WASM]
    B --> G[AudioScheduler]
    B --> H[Tone.js]
    
    style B fill:#FFD700
    style F fill:#FF6B6B
    style G fill:#90EE90
```

**Responsibilities:**
- ✅ Single source of truth for playback state
- ✅ Coordinate Quantum (visual) vs Kronos (audio) timelines
- ✅ Handle play/pause/seek/loop commands
- ✅ Emit snapshots on beat boundaries (not 60 FPS)
- ✅ Load scores, calculate measure timing

**API:**
```typescript
// Dispatch commands
unifiedKernelFacade.dispatch({ type: 'play' });
unifiedKernelFacade.dispatch({ type: 'load-score', payload: nvx1Score });
unifiedKernelFacade.dispatch({ type: 'seek', position: { measureIndex: 4, beatInMeasure: 2 } });

// Subscribe to events
unifiedKernelFacade.subscribe('snapshot', (event) => {
  console.log('New snapshot:', event.snapshot);
});
```

---

### 4️⃣ **Kronos Engine** (Web Worker - WASM)

```mermaid
graph LR
    A[Rust Core] --> B[WASM Binary]
    B --> C[JavaScript Wrapper]
    C --> D[Web Worker Thread]
    D --> E[postMessage to Main]
    
    style A fill:#FFA500
    style B fill:#FF6B6B
```

| Aspect | Details |
|--------|---------|
| **Language** | Rust → compiled to WASM |
| **Size** | ~500KB WASM module |
| **Precision** | 960 PPQ (pulses per quarter note) |
| **Features** | - High-precision timeline<br>- Tempo map support<br>- Loop handling<br>- Event scheduling |
| **Thread** | Runs in dedicated Web Worker (no main thread blocking) |
| **Communication** | `postMessage` for commands, structured clone for data |

**Why Rust?** Sample-accurate timing requires deterministic performance (no GC pauses).

**API:**
```typescript
kronosEngine.loadScore(serializedScore); // Load score events
kronosEngine.play(); // Start playback
kronosEngine.seek(measure, beat); // Jump to position
kronosEngine.getState(timestamp); // Get current position
```

---

### 5️⃣ **Audio Scheduler** (Web Worker - TypeScript)

| Aspect | Details |
|--------|---------|
| **Purpose** | Queue audio events ahead of playback time |
| **Lookahead** | 100ms (configurable) |
| **Jitter Tolerance** | <5ms (measured via diagnostics) |
| **Event Types** | Note on/off, chord changes, metronome clicks |
| **Targets** | Apollo.js (primary), Tone.js (fallback) |

**Flow:**
```
Kronos (timeline position) 
  → AudioScheduler (queue events @ currentTime + 100ms)
  → Apollo.js (trigger samples)
  → Web Audio (speakers)
```

**Latency Compensation:**
```typescript
const scheduleTime = audioContext.currentTime + lookAheadMs / 1000;
apolloInstance.playMelody([note], duration, velocity, scheduleTime);
```

---

### 6️⃣ **Apollo.js Sampler** (Web Audio API)

```mermaid
graph TB
    A[Apollo.js<br/>18,000 LOC] --> B[Sample Loader]
    A --> C[Voice Leading Engine]
    A --> D[Crossfade Engine]
    A --> E[Effect Chain]
    
    B --> F[Preloaded Samples<br/>~100MB]
    C --> G[Smooth Chord Transitions]
    D --> H[No Clicks/Pops]
    E --> I[Reverb, Delay, EQ]
    
    I --> J[Master Bus]
    J --> K[Speakers]
    
    style A fill:#FF6B6B
    style F fill:#90EE90
```

**Technology:** Custom JavaScript audio engine (predates Tone.js integration)

**Features:**
- ✅ Multi-sampled guitar/piano/bass
- ✅ Velocity layers (3-5 per note)
- ✅ Round-robin sample selection
- ✅ Voice leading for smooth chord progressions
- ✅ Built-in effects (reverb, delay, chorus)

**Loading Strategy:**
1. **On page load:** Preload C major scale (instant feedback)
2. **Lazy load:** Fetch other notes on-demand
3. **Cache:** Store in memory for session

**Critical Path:**
```typescript
// AudioScheduler calls this:
window.Apollo.get().playMelody([note], duration, velocity);

// Apollo internally:
// 1. Select appropriate sample (velocity + round-robin)
// 2. Schedule via Web Audio API
// 3. Apply crossfade if chord change
// 4. Route through effect chain
```

---

### 7️⃣ **Tone.js Transport** (Legacy - Being Phased Out)

| Aspect | Details |
|--------|---------|
| **Status** | 🟡 **Deprecated** (replaced by Kronos for new features) |
| **Current Use** | Fallback for MIDI-test page, legacy widgets |
| **Migration Plan** | Remove by Q2 2026 |
| **Why Deprecated?** | - Not sample-accurate<br>- BPM drift over long sessions<br>- Conflicts with Kronos timeline |

**Do NOT use for new features.** Use `unifiedKernelFacade` instead.

---

### 8️⃣ **IndexedDB** (Browser Storage)

```mermaid
graph LR
    A[User Scores] --> B[IndexedDB]
    C[User Settings] --> B
    D[Cached AI Results] --> B
    E[Offline Queue] --> B
    
    B --> F[Sync to Supabase<br/>when online]
    
    style B fill:#87CEEB
```

**Stores:**
- `scores` - Full score JSON (NVX1, V2, V3 formats)
- `settings` - User preferences, UI state
- `cache` - AI-generated content (chord suggestions, backing tracks)
- `offline-queue` - Actions to sync when online

**Quota:** ~50MB typical, up to 1GB available (browser-dependent)

---

## Communication Patterns

### Pattern 1: Command → Kernel → Workers

```mermaid
sequenceDiagram
    participant UI as React Component
    participant Store as Zustand Store
    participant Kernel as Transport Kernel
    participant Kronos as Kronos Worker
    participant Audio as Audio Scheduler

    UI->>Store: dispatch({ type: 'play' })
    Store->>Kernel: unifiedKernelFacade.dispatch({ type: 'play' })
    Kernel->>Kronos: postMessage({ cmd: 'play' })
    Kernel->>Audio: postMessage({ cmd: 'start-scheduling' })
    Audio-->>Kernel: ACK
    Kronos-->>Kernel: ACK
    Kernel->>Store: emit('snapshot', newState)
    Store->>UI: Re-render with isPlaying=true
```

**Key Insight:** Kernel orchestrates, workers execute in parallel.

---

### Pattern 2: Snapshot Propagation (Beat Boundaries Only)

```mermaid
graph TB
    A[RAF Tick 60 FPS] --> B{Position Changed?}
    B -->|No| C[Skip - No Snapshot]
    B -->|Yes| D{On Beat Boundary?}
    D -->|No| C
    D -->|Yes| E[Build Snapshot]
    E --> F[Emit to Listeners]
    F --> G[Zustand Stores Update]
    G --> H[React Re-renders]
    
    style E fill:#90EE90
    style H fill:#FFD700
```

**Before Fix:** 60 snapshots/sec → 240+ re-renders/sec  
**After Fix:** 2-4 snapshots/sec (only on beat changes) → 8-16 re-renders/sec

---

### Pattern 3: Score Loading Pipeline

```mermaid
graph LR
    A[Upload/Import] --> B{Format?}
    B -->|NVX1| C[convertNVX1ToV3]
    B -->|V2| D[Keep as-is]
    B -->|V3| E[Validate schema]
    B -->|MusicXML| F[MusicXMLImportService]
    B -->|GuitarPro| G[GuitarProImportService]
    
    C --> H[Normalized V3 Score]
    D --> H
    E --> H
    F --> H
    G --> H
    
    H --> I[useScoreStore.setState]
    I --> J[Kernel.dispatch load-score]
    J --> K[serializeScoreForKronos]
    K --> L[Kronos.loadScore]
    J --> M[warmupAudioForScore]
    M --> N[Apollo.preloadSamples]
    
    style H fill:#90EE90
    style L fill:#FF6B6B
    style N fill:#FFD700
```

**Critical:** All formats converge to **V3 schema** before playback.

---

## Threading Model

```mermaid
graph TB
    subgraph "Main Thread (UI)"
        A[React Rendering]
        B[Event Handlers]
        C[Zustand State]
    end
    
    subgraph "Worker 1: Kronos"
        D[Timeline Calculation]
        E[Position Updates]
    end
    
    subgraph "Worker 2: Audio Scheduler"
        F[Event Queue]
        G[Latency Compensation]
    end
    
    subgraph "Worker 3: Video Encoder"
        H[Canvas Capture]
        I[H264 Encoding]
    end
    
    subgraph "Audio Thread"
        J[AudioWorklet]
        K[Web Audio Graph]
    end
    
    A -->|postMessage| D
    D -->|postMessage| F
    F -->|Schedule| K
    A -->|postMessage| H
    
    style A fill:#87CEEB
    style D fill:#FF6B6B
    style F fill:#90EE90
    style J fill:#FFD700
```

**Performance Impact:**
- **Main Thread:** ~10% CPU (UI only)
- **Kronos Worker:** ~5% CPU (timeline math)
- **Audio Scheduler:** ~15% CPU (event queue)
- **Audio Thread:** ~20% CPU (sample playback)

---

## Data Flow Summary

```mermaid
graph TB
    A[User Action] --> B[React Component]
    B --> C[Zustand Store]
    C --> D[Transport Kernel]
    D --> E[Kronos Worker]
    D --> F[Audio Scheduler]
    F --> G[Apollo.js]
    G --> H[Web Audio]
    H --> I[Speakers]
    
    D --> J[Snapshot Event]
    J --> C
    C --> B
    
    K[Score Data] --> L[IndexedDB]
    L --> C
    C --> M[Supabase Sync]
    
    style D fill:#FFD700
    style E fill:#FF6B6B
    style G fill:#90EE90
```

---

## Technology Decisions & Rationale

| Decision | Rationale |
|----------|-----------|
| **Rust WASM for Kronos** | Sample-accurate timing requires no GC pauses; Rust provides deterministic performance |
| **Web Workers for scheduling** | Offload heavy computation from main thread to avoid UI jank |
| **Apollo.js custom sampler** | Tone.js couldn't handle voice leading smoothly; needed full control |
| **Zustand over Redux** | Simpler API, better TypeScript support, no boilerplate |
| **Vite over Webpack** | 10x faster dev server, native ESM, better tree-shaking |
| **Supabase over Firebase** | PostgreSQL (relational), built-in auth, easier migrations |

---

## Known Limitations & Bottlenecks

| Issue | Impact | Workaround |
|-------|--------|------------|
| **300+ services** | Hard to navigate codebase | This documentation + consolidation plan |
| **5 timeline systems** | Timing conflicts, race conditions | Migrate all to UnifiedKernel |
| **Apollo.js size (100MB samples)** | Slow initial load | CDN + progressive loading |
| **No server-side audio** | Can't generate MP3 exports | Use WebCodecs API client-side |

---

## Next Steps

👉 **Dive deeper into specific subsystems:**
- [03-TRANSPORT-TIMELINE-ARCHITECTURE.md](./03-TRANSPORT-TIMELINE-ARCHITECTURE.md) - Timeline chaos explained
- [03a-AUDIO-PLAYBACK-ARCHITECTURE.md](./03a-AUDIO-PLAYBACK-ARCHITECTURE.md) - Apollo + Kronos detailed
- [03c-SERVICE-INVENTORY.md](./03c-SERVICE-INVENTORY.md) - Browse all services

---

**Document Status:** ✅ Complete  
**Last Reviewed:** November 13, 2025
