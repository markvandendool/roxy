# 01 - System Context Diagram (C4 Level 1)

**Audience:** Executives, product managers, new engineers  
**Purpose:** Understand what MindSong JukeHub does and how it fits in the world

---

## System Context Overview

```mermaid
C4Context
    title System Context - MindSong JukeHub (C4 Level 1)

    Person(student, "Music Student", "Learning guitar, theory, composition")
    Person(teacher, "Music Teacher", "Creating lessons, tracking progress")
    Person(composer, "Composer", "Writing scores, arranging music")
    Person(performer, "Live Performer", "Theater mode, streaming")

    System(msj, "MindSong JukeHub", "Comprehensive music education & composition platform")

    System_Ext(youtube, "YouTube API", "Video playback, backing tracks")
    System_Ext(musicai, "Music AI Services", "MusicGen, NotaGen, BasicPitch")
    System_Ext(supabase, "Supabase", "Authentication, cloud storage, realtime sync")
    System_Ext(songsterr, "Songsterr API", "Tab library, chord charts")
    System_Ext(obs, "OBS Studio", "Live streaming, NDI output")
    System_Ext(daw, "External DAWs", "Ableton Link, MIDI Clock sync")
    System_Ext(midi, "MIDI Hardware", "Controllers, keyboards, guitars")
    
    Rel(student, msj, "Practices songs, learns theory")
    Rel(teacher, msj, "Creates lessons, monitors students")
    Rel(composer, msj, "Composes scores, arranges parts")
    Rel(performer, msj, "Performs live with visuals")

    Rel(msj, youtube, "Fetches videos, sync playback", "HTTPS")
    Rel(msj, musicai, "Generates backing tracks, transcribes audio", "HTTPS/WebSocket")
    Rel(msj, supabase, "Authenticates users, stores scores", "HTTPS/WebSocket")
    Rel(msj, songsterr, "Imports tabs, chord charts", "HTTPS")
    Rel(msj, obs, "Streams widgets via NDI", "NDI Protocol")
    Rel(msj, daw, "Syncs tempo & position", "MIDI/Ableton Link")
    Rel(midi, msj, "Sends note/CC data", "Web MIDI API")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="2")
```

---

## External Actors

### 👤 Primary Users

| Actor | Use Cases | Key Features |
|-------|-----------|--------------|
| **Music Student** | Learn songs, practice theory, track progress | Interactive fretboard, chord progressions, adaptive lessons |
| **Music Teacher** | Create curricula, assign exercises, monitor students | Lesson builder, progress tracking, performance analytics |
| **Composer** | Write original music, arrange orchestrations | Score editor (NVX1), notation export, MIDI input |
| **Live Performer** | Theater mode for concerts, streaming overlays | 8K Theater, Quantum timeline, OBS integration |

### 🔌 External Systems

| System | Purpose | Integration Type | Critical? |
|--------|---------|------------------|-----------|
| **YouTube API** | Backing track playback, sync with score | REST API + iframe embed | 🟡 Medium |
| **Music AI (HuggingFace)** | MusicGen (audio gen), NotaGen (chord gen), BasicPitch (transcription) | HTTPS/WebSocket | 🟢 Optional |
| **Supabase** | User auth, cloud storage, realtime collab | PostgreSQL + Realtime channels | 🔴 Critical |
| **Songsterr** | Import existing tabs/chords | REST API | 🟢 Optional |
| **OBS Studio** | Stream widgets as NDI sources | NDI Protocol (local network) | 🟢 Optional |
| **External DAWs** | Tempo/position sync for hybrid workflows | Ableton Link, MIDI Clock | 🟢 Optional |
| **MIDI Hardware** | Live input from controllers/guitars | Web MIDI API (browser) | 🟡 Medium |

---

## System Boundaries

### What MindSong JukeHub **IS**

✅ **Score-centric music learning platform**  
✅ **Interactive guitar/piano fretboard visualizer**  
✅ **Real-time chord progression analyzer**  
✅ **Multi-format score editor (NVX1, MusicXML, Guitar Pro)**  
✅ **Theater-mode visualization engine (8K, Quantum, Myst)**  
✅ **AI-assisted composition tools**  
✅ **Multi-tenant education system** (teachers + students)

### What MindSong JukeHub **IS NOT**

❌ **DAW replacement** (no multi-track audio recording/editing)  
❌ **Social network** (limited community features)  
❌ **Streaming service** (no music library/licensing)  
❌ **Notation software competitor** (not MuseScore/Sibelius-level engraving)

---

## Core Value Propositions

### For Students
- **Visual Learning:** See chord progressions, scales, fretboard positions in real-time
- **Adaptive Curriculum:** AI-powered lesson progression based on performance
- **Multi-Modal Practice:** Audio, MIDI, video, notation all synchronized

### For Teachers
- **Lesson Authoring:** Create custom exercises with embedded theory
- **Progress Tracking:** Dashboard showing student practice time, accuracy, mastery
- **Content Library:** Share/reuse lessons across classes

### For Composers
- **Rapid Prototyping:** AI-generated chord suggestions, voice leading analysis
- **Multi-Format Export:** MusicXML, MIDI, PDF, Data3/Data4
- **Live Playback:** Hear scores with Apollo.js sample engine

### For Performers
- **Theater Mode:** Full-screen synchronized visuals for concerts
- **OBS Integration:** Individual widgets as NDI sources for streaming
- **MIDI Sync:** Lock to external hardware/DAWs for hybrid performances

---

## High-Level Data Flow

```mermaid
graph LR
    A[External Sources] --> B[Import Pipeline]
    B --> C[Score Store<br/>NVX1/V3 format]
    C --> D[Transport Kernel<br/>Timeline + Playback]
    D --> E[Audio Engine<br/>Apollo + Kronos]
    E --> F[Browser Output<br/>Speakers + Visuals]
    
    C --> G[Export Pipeline]
    G --> H[External Formats<br/>MIDI/MusicXML/PDF]
    
    I[User Input<br/>MIDI/Keyboard/Mouse] --> D
    J[AI Services<br/>MusicGen/NotaGen] --> C
    
    style C fill:#90EE90
    style D fill:#FFD700
    style E fill:#FF6B6B
```

**Key Insight:** Everything flows through the **Score Store** (single source of truth) and the **Transport Kernel** (timeline authority).

---

## Technology Stack (Summary)

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 18 + TypeScript, Zustand (state), TanStack Query |
| **Audio** | Tone.js, Apollo.js (custom sampler), Web Audio API |
| **Timeline** | Kronos (Rust WASM), Quantum (RAF-based), UnifiedKernelEngine |
| **Backend** | Supabase (PostgreSQL + Edge Functions) |
| **AI/ML** | HuggingFace Inference API, TensorFlow.js (pitch detection) |
| **Build** | Vite, Biome (linting), Capacitor (mobile) |

---

## Deployment Model

```mermaid
graph TB
    subgraph "Browser (Main Thread)"
        A[React App]
        B[Zustand Stores]
        C[Transport Kernel]
    end
    
    subgraph "Web Workers"
        D[Kronos WASM]
        E[Audio Scheduler]
        F[Video Encoder]
    end
    
    subgraph "Audio Context"
        G[Tone.js Transport]
        H[Apollo Sampler]
        I[Web Audio Nodes]
    end
    
    A --> B
    B --> C
    C --> D
    C --> E
    C --> G
    G --> H
    H --> I
    
    style A fill:#87CEEB
    style D fill:#FFB6C1
    style G fill:#98FB98
```

**Critical Detail:** Audio worklets run in separate thread to avoid main-thread jank.

---

## Security & Privacy

| Aspect | Implementation |
|--------|----------------|
| **Authentication** | Supabase Auth (OAuth + email/password) |
| **Authorization** | Row-Level Security (RLS) in PostgreSQL |
| **Data Storage** | User scores encrypted at rest in Supabase |
| **API Keys** | Environment variables, never client-side |
| **MIDI/Audio** | Local-only (no server transmission) |

---

## Scalability Considerations

| Component | Current Limits | Scaling Strategy |
|-----------|---------------|------------------|
| **Concurrent Users** | ~1000 (Supabase free tier) | Migrate to Pro/Enterprise tier |
| **Score Complexity** | ~500 measures/score | Virtualized rendering, lazy loading |
| **Audio Samples** | ~100MB Apollo.js | CDN caching, progressive loading |
| **Real-time Sync** | ~10 users/session | Supabase Realtime channels |

---

## Next Steps

👉 **For deeper technical detail, continue to:**
- [02-CONTAINER-ARCHITECTURE.md](./02-CONTAINER-ARCHITECTURE.md) - See how components communicate
- [03-TRANSPORT-TIMELINE-ARCHITECTURE.md](./03-TRANSPORT-TIMELINE-ARCHITECTURE.md) - Understand the timeline mess
- [03c-SERVICE-INVENTORY.md](./03c-SERVICE-INVENTORY.md) - Browse all 300+ services

---

**Document Status:** ✅ Complete  
**Last Reviewed:** November 13, 2025  
**Maintained By:** Lead Architect
