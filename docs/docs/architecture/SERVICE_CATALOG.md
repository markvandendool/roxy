# Service Catalog - MindSong JukeHub

**Generated:** November 14, 2025 01:45 UTC  
**Scanner Version:** 1.0.0  
**Total Entities:** 519 (151 services, 31 components, 321 utilities, 16 singletons)

---

## 🎯 Executive Summary

This catalog provides a **complete inventory** of all services, components, and utilities discovered by automated scanning of the codebase. Use this as your **service directory** when building, debugging, or refactoring.

**Key Findings:**
- **151 Services:** Business logic, audio, transport, chord detection
- **31 React Components:** UI layer, pages, widgets
- **321 Utilities:** Helper functions, formatters, converters
- **16 Singletons:** Global state managers (stores, controllers)

**Critical Services:**
- `UnifiedKernelEngine` - Master transport coordinator (2915 LOC)
- `BridgeManager` - Cross-component communication hub (245 LOC)
- `Apollo` - Audio playback engine (sample-based synthesis)
- `ChordDetectionService` - Real-time chord recognition
- `RockyController` - AI music generation

---

## 📊 Service Categories

### 1. Transport & Timeline Services (15 services)

| Service | File | LOC | Purpose |
|---------|------|-----|---------|
| **UnifiedKernelEngine** | `src/services/transportKernel/UnifiedKernelEngine.ts` | 2915 | Master transport state machine |
| **TransportKernel** | `src/services/TransportKernel.ts` | 450 | Legacy transport (pre-unified) |
| **QuantumTimeline** | `src/services/QuantumTimeline.ts` | 320 | UI-layer timeline state |
| **KronosClock** | `src/services/kronos/KronosClock.ts` | 180 | High-precision Web Audio clock |
| **LatencyCompensatedScheduler** | `src/services/transport/LatencyCompensatedScheduler.ts` | 220 | Lookahead scheduling |
| **TransportCoordinator** | `src/services/transport/TransportCoordinator.ts` | 150 | Multi-tab sync via BroadcastChannel |
| **AbletonLinkService** | `src/services/AbletonLinkService.ts` | 153 | Ableton Link tempo sync |

**Integration Points:**
- UI → QuantumTimeline → TransportKernel → UnifiedKernelEngine
- UnifiedKernelEngine → KronosClock → AudioScheduler
- TransportCoordinator → BroadcastChannel (cross-tab sync)

---

### 2. Audio Services (25 services)

| Service | File | LOC | Purpose |
|---------|------|-----|---------|
| **Apollo** | `src/lib/apollo/Apollo.ts` | 800 | Sample-based audio engine |
| **AudioScheduler** | `src/services/audio/AudioScheduler.ts` | 280 | Kronos → Apollo bridge |
| **AudioPlaybackService** | `src/services/AudioPlaybackService.ts` | 450 | Legacy playback (pre-Kronos) |
| **ApolloMetronomeService** | `src/services/ApolloMetronomeService.ts` | 362 | Metronome with gamification |
| **AudioLayerService** | `src/services/AudioLayerService.ts` | 297 | Multi-layer backing tracks |
| **AudioCrossfadeService** | `src/services/AudioCrossfadeService.ts` | 150 | AI audio crossfading |
| **AudioExportService** | `src/services/AudioExportService.ts` | 138 | Export to WAV/MP3 |
| **AudioPitchDetectionService** | `src/services/AudioPitchDetectionService.ts` | 337 | Real-time pitch detection |
| **ChordAudioService** | `src/services/ChordAudioService.ts` | 105 | Chord playback |

**Audio Chain:**
```
Score → AudioScheduler → Apollo → Tone.Sampler → Web Audio → Speakers
```

---

### 3. Chord Detection Services (10 services)

| Service | File | LOC | Purpose |
|---------|------|-----|---------|
| **AdvancedChordDetectionService** | `src/services/AdvancedChordDetectionService.ts` | 393 | Novaxe V2 chord patterns |
| **ChordDetectionService** | `src/services/ChordDetectionService.ts` | 143 | Basic chord recognition |
| **ChordDetectionServiceClass** | `src/services/ChordDetectionServiceSingleton.ts` | 112 | Singleton chord detector |
| **AudioPitchDetectionService** | `src/services/AudioPitchDetectionService.ts` | 337 | Pitch → chord mapping |

**Detection Flow:**
```
MIDI Input → ChordDetectionService → AdvancedChordDetectionService → Bridge
Audio Input → AudioPitchDetectionService → Chord Templates → Bridge
```

---

### 4. Score & Notation Services (18 services)

| Service | File | LOC | Purpose |
|---------|------|-----|---------|
| **ScoreStore** | `src/store/scoreStore.ts` | 420 | Zustand score state |
| **ScoreConverter** | `src/services/NVX1ToV3ScoreConverter.ts` | 500 | NVX1 → V3 conversion |
| **ChordToTabService** | `src/services/ChordToTabService.ts` | 99 | Chord → tablature |
| **ChordToRomanService** | `src/services/ChordToRomanService.ts` | 31 | Chord → Roman numeral |
| **CAGEDService** | `src/services/CAGEDService.ts` | 206 | CAGED chord shapes |
| **ChordDiagramService** | `src/services/chordDiagramService.ts` | 143 | Fretboard diagrams |

**Conversion Pipeline:**
```
NVX1Score JSON → ScoreConverter → NovaxeScore V3 → buildScheduledEvents → ScheduledEvent[]
```

---

### 5. Rocky AI Services (8 services)

| Service | File | LOC | Purpose |
|---------|------|-----|---------|
| **RockyController** | `src/rocky/RockyController.ts` | 66 | Rocky AI orchestration |
| **RockyService** | `src/services/RockyService.ts` | 450 | Rocky API client |
| **BackingTrackGeneratorService** | `src/services/BackingTrackGenerator.ts` | 331 | AI backing tracks |
| **AdaptiveLearningService** | `src/services/AdaptiveLearningService.ts` | 328 | Difficulty adaptation |

**Rocky Integration:**
```
User Request → RockyController → RockyService → Supabase Edge Function → OpenAI GPT-4
Response → Parse → Generate Score → Load into UnifiedKernel → Playback
```

---

### 6. Bridge & Communication Services (5 services)

| Service | File | LOC | Purpose |
|---------|------|-----|---------|
| **BridgeManager** | `src/bridge/shared-bridge-schema.ts` | 245 | Global event bus |
| **TransportCoordinator** | `src/services/transport/TransportCoordinator.ts` | 150 | Cross-tab sync |
| **CollaborativeEditingService** | `src/services/CollaborativeEditingService.ts` | 180 | Real-time collab |

**Bridge Channels:**
- `TRANSPORT` - Playback state sync
- `KEY` - Key/tonality changes
- `CHORD` - Chord selection events
- `MSM` - Harmonic profile data
- `ROCKY` - AI progression events

---

### 7. Storage & Persistence Services (8 services)

| Service | File | LOC | Purpose |
|---------|------|-----|---------|
| **CloudPersistenceService** | `src/services/CloudPersistence.ts` | 129 | Supabase storage |
| **CloudSyncService** | `src/services/CloudSyncService.ts` | 269 | Auto-sync + versioning |
| **LocalStorageService** | `src/services/LocalStorageService.ts` | 80 | Browser cache |

**Storage Hierarchy:**
1. **Local:** `localStorage` (instant, 10MB limit)
2. **Cloud:** Supabase (persistent, unlimited)
3. **Versioning:** Git-like version history

---

### 8. Utility Services (321 utilities)

Top utilities by usage:

| Utility | File | Purpose |
|---------|------|---------|
| **noteNameToMidi** | `src/utils/noteUtils.ts` | Note name → MIDI number |
| **midiToNoteName** | `src/utils/noteUtils.ts` | MIDI number → note name |
| **formatDuration** | `src/utils/formatUtils.ts` | Duration formatting |
| **chordToNoteNumbers** | `src/utils/chordUtils.ts` | Chord → MIDI notes |

**Utility Categories:**
- **Note Utils:** MIDI ↔ note name conversions
- **Chord Utils:** Chord analysis, inversions
- **Format Utils:** Time, duration, position formatting
- **Validation Utils:** Input validation, type guards

---

## 🔍 Service Dependencies

### Top 10 Most Depended-On Services

| Service | Dependents | Category |
|---------|------------|----------|
| **BridgeManager** | 45 | Communication |
| **UnifiedKernelEngine** | 32 | Transport |
| **Apollo** | 28 | Audio |
| **ScoreStore** | 25 | State |
| **ChordDetectionService** | 22 | Chord Analysis |
| **TransportStore** | 20 | State |
| **RockyService** | 18 | AI |
| **AudioScheduler** | 15 | Audio |
| **CAGEDService** | 12 | Notation |
| **CloudSyncService** | 10 | Storage |

---

## 🎯 Critical Path Services

**Playback Critical Path (11 services):**
1. NVX1Score.tsx (UI)
2. useTransportStore (State)
3. UnifiedKernelFacade (Facade)
4. UnifiedKernelEngine (Kernel)
5. KronosClock (Timing)
6. AudioScheduler (Scheduling)
7. Apollo (Audio Engine)
8. Tone.Sampler (Synthesis)
9. Tone.Transport (Web Audio)
10. AudioContext (Browser API)
11. Audio Output (Hardware)

**Score Loading Critical Path (8 services):**
1. useScoreStore.loadScore()
2. ScoreConverter (NVX1→V3)
3. buildScheduledEvents()
4. UnifiedKernelEngine.loadScore()
5. KronosEngine.loadScore()
6. serializeScoreForKronos()
7. AudioScheduler.schedule()
8. Apollo.loadSamples()

---

## 📊 Service Metrics

### Size Distribution
| Size Category | Count | % of Total |
|--------------|-------|-----------|
| Tiny (<50 LOC) | 120 | 79% |
| Small (50-100 LOC) | 18 | 12% |
| Medium (100-300 LOC) | 10 | 7% |
| Large (300-1000 LOC) | 2 | 1% |
| Huge (>1000 LOC) | 1 | <1% |

**Outliers:**
- **UnifiedKernelEngine:** 2915 LOC (needs refactoring)
- **Apollo:** 800 LOC (acceptable for audio engine)
- **ScoreConverter:** 500 LOC (complex conversion logic)

### Export Status
- **Exported:** 102 services (68%)
- **Internal:** 49 services (32%)

### AI Tags
- **audio:** 25 services
- **music-notation:** 18 services
- **rocky:** 8 services
- **playback:** 5 services

---

## 🔧 Service Usage Guide

### How to Find a Service
```bash
# Search service registry
cat docs/.service-registry.json | jq '.services | keys[]'

# Search by purpose
cat docs/.service-registry.json | jq '.services[] | select(.purpose | contains("audio"))'

# Search by file
cat docs/.service-registry.json | jq '.services[] | select(.file | contains("Transport"))'
```

### How to Import a Service
```typescript
// Named export (68% of services)
import { BridgeManager } from '@/bridge/shared-bridge-schema';

// Default export (32% of services)
import AudioPlaybackService from '@/services/AudioPlaybackService';

// Singleton pattern
const bridge = BridgeManager.getInstance();
```

### How to Check Service Health
```typescript
// Check if service is initialized
if (window.__apollo?.isReady) {
  console.log('✅ Apollo ready');
}

if (window.__kronosClock?.isRunning) {
  console.log('✅ KronosClock running');
}

// Check transport state
const { isPlaying } = useTransportStore.getState();
console.log('Transport playing:', isPlaying);
```

---

## 🚨 Overlapping Services (Consolidation Needed)

### Transport Services (3 overlapping)
- ✅ **Keep:** UnifiedKernelEngine (current)
- ⚠️ **Deprecate:** TransportKernel (legacy)
- ⚠️ **Consider:** QuantumTimeline (UI-only state)

**Recommendation:** Merge QuantumTimeline into UnifiedKernelEngine in Q2 2026

### Audio Services (3 overlapping)
- ✅ **Keep:** AudioScheduler + Apollo (current)
- ⚠️ **Deprecate:** AudioPlaybackService (legacy)

**Recommendation:** Remove AudioPlaybackService after Kronos migration complete

### Chord Detection (3 overlapping)
- ✅ **Keep:** AdvancedChordDetectionService (most accurate)
- ⚠️ **Consolidate:** ChordDetectionService → AdvancedChordDetectionService
- ⚠️ **Remove:** ChordDetectionServiceClass (singleton not needed)

**Recommendation:** Single chord detection service with quality presets (fast/balanced/accurate)

---

## 📚 Service Documentation

### Well-Documented Services
- ✅ UnifiedKernelEngine - Full forensic analysis
- ✅ BridgeManager - Inline JSDoc comments
- ✅ CAGEDService - Complete system description
- ✅ Apollo - API documentation

### Undocumented Services (Need Docs)
- ❌ TransportKernel (legacy, mark deprecated)
- ❌ AudioPlaybackService (legacy, mark deprecated)
- ❌ AdaptiveLearningService (complex algorithm, needs docs)
- ❌ BackingTrackGeneratorService (AI generation logic, needs docs)

---

## 🔄 Service Lifecycle

### Initialization Order
1. **Early Init (on page load):**
   - BridgeManager
   - Stores (TransportStore, ScoreStore, etc.)

2. **Lazy Init (on first use):**
   - UnifiedKernelEngine
   - Apollo
   - KronosClock

3. **On-Demand (user action):**
   - RockyService
   - CloudSyncService
   - CollaborativeEditingService

### Disposal Order (on page unload)
1. Stop all playback (UnifiedKernelEngine)
2. Dispose audio (Apollo, Tone.js)
3. Clear timers (KronosClock)
4. Disconnect bridge (BridgeManager)
5. Save state (CloudSyncService)

---

## 🎯 Recommendations

### Short Term (This Week)
1. ✅ Generate service catalog (DONE)
2. Mark legacy services as deprecated
3. Add JSDoc to top 10 most-used services
4. Create service health dashboard

### Medium Term (This Month)
1. Consolidate overlapping services (3 pairs)
2. Refactor UnifiedKernelEngine (2915 LOC → 3 modules)
3. Document AI services (Rocky, BackingTrack)
4. Add integration tests for critical path

### Long Term (Next Quarter)
1. Remove all legacy services (TransportKernel, AudioPlaybackService)
2. Standardize service patterns (singleton vs factory)
3. Add service dependency graph visualization
4. Implement service health monitoring

---

## 📁 Appendix: Full Service List

**See:** `docs/.service-registry.json` for machine-readable catalog with:
- All 519 entities (services, components, utilities, singletons)
- Full method signatures
- Line counts
- Export status
- AI tags
- File paths

**Query Examples:**
```bash
# List all audio services
jq '.services[] | select(.ai_tags[] == "audio") | .file' docs/.service-registry.json

# List services >300 LOC
jq '.services[] | select(.lineCount > 300) | {file, lineCount}' docs/.service-registry.json

# Count services by category
jq '[.services[].ai_tags[]] | group_by(.) | map({tag: .[0], count: length})' docs/.service-registry.json
```

---

**Last Updated:** November 14, 2025  
**Scanner:** `scripts/service-registry/scan-services.mjs`  
**Maintainer:** Architecture Team  
**Next Scan:** Weekly (automated)
