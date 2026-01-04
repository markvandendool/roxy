# Global Widget Architecture - EXISTING PATTERNS ONLY

**⚠️ CRITICAL: This document ONLY describes patterns that EXIST in the codebase. No invented patterns.**

**Last Verified:** 2025-01-27  
**Purpose:** Reference guide for agents working on Chord Cubes, Harmonic Profile, and LiveHub connections

---

## ✅ What Actually Exists

### 1. GlobalMidiEventBus (EXISTS - Documented)

**Location**: `src/services/GlobalMidiEventBus.ts`  
**Documentation**: `docs/midi-audio-global/architecture/ARCHITECTURE.md`  
**Status**: ✅ Implemented and documented

**Event Types** (from existing code):
- `chord:detected` - Chord recognition results
- `midi:snapshot` - Unified note snapshots
- `midi:noteon` / `midi:noteoff` - Individual MIDI events
- `braid:highlight` - Roman numeral highlighting

**Usage** (from existing code):
```typescript
// Emit
globalMidiEventBus.emit({ type: 'chord:detected', ... }, true);

// Subscribe
const unsubscribe = globalMidiEventBus.on('chord:detected', (event) => { ... });
```

---

### 2. GlobalMidiIngestService (EXISTS - Documented)

**Location**: `src/services/GlobalMidiIngestService.ts`  
**Documentation**: `docs/midi-audio-global/implementation/IMPLEMENTATION_STATUS.md`  
**Status**: ✅ Implemented and documented

**Key Method** (from existing code):
```typescript
globalMidiIngestService.emitExternalChordDetection(chord, {
  origin: 'audio',
  source: 'real-time',
  fusion: { decision: 'oracle', votes: [...] }
});
```

---

### 3. Bridge Services (EXIST - In Code)

#### GuitarTubeSwarmBridge
**Location**: `src/services/guitartube/GuitarTubeSwarmBridge.ts`  
**Status**: ✅ EXISTS in codebase  
**Pattern**: Converts MIR playback time → `chord:detected` events via `globalMidiIngestService.emitExternalChordDetection()`

#### chordCubesBridge
**Location**: `src/services/chordCubesBridge.ts`  
**Status**: ✅ EXISTS in codebase  
**Pattern**: PostMessage bridge for Chord Cubes iframe communication

#### hpLiveEntryBridge
**Location**: `src/components/harmonic/hpLiveEntryBridge.ts`  
**Status**: ✅ EXISTS in codebase  
**Pattern**: Global `window.onHPChordClick` handler → `live:chord` CustomEvent

---

### 4. ChordCubesEmbed (EXISTS - In Code)

**Location**: `src/components/olympus/ChordCubesEmbed.tsx`  
**Status**: ✅ EXISTS in codebase  
**Pattern**: 
- Listens for `cubes:chord-click` messages from iframe
- Converts to `chord:detected` event
- Emits via `globalMidiEventBus.emit()`

**Key Code** (lines 522-650):
```typescript
case 'cubes:chord-click': {
  const chordEvent: ChordDetectedEventWithRoman = {
    type: 'chord:detected',
    chord: { symbol, notes, midiNotes, root, type },
    romanNumeral,
    origin: 'cube-click',
  };
  globalMidiEventBus.emit(chordEvent, true);
}
```

---

### 5. LiveHub Integration (EXISTS - In Code)

**Location**: `src/pages/LiveHub.tsx`  
**Status**: ✅ EXISTS in codebase  
**Pattern**: 
- Listens to `live:chord` CustomEvents (from HP bridge)
- Listens to `chord:detected` from globalMidiEventBus
- Forwards to MSM iframe via `postToMSM()`

**Key Code** (lines 387-416):
```typescript
useEffect(() => {
  const onLiveChord = (e: CustomEvent) => {
    postToMSM({ channel: 'MSM_LIVE', type: 'appendChord', payload });
  };
  window.addEventListener('live:chord', onLiveChord);
  return () => window.removeEventListener('live:chord', onLiveChord);
}, []);
```

---

## 📚 Existing Documentation References

### Service Registry (MANDATORY READING)
- **Location**: `docs/brain/60-projects/rocky/SERVICE_REGISTRY_COMPLETE.md`
- **Key Rule**: **NEVER CREATE SERVICE #277** - Use existing services only
- **Global Event Bus**: Listed as Core Service #2 (GlobalMidiEventBus)

### Architecture Documentation
- **Global MIDI Architecture**: `docs/midi-audio-global/architecture/ARCHITECTURE.md`
- **Implementation Status**: `docs/midi-audio-global/implementation/IMPLEMENTATION_STATUS.md`
- **Service Catalog**: `docs/architecture/SERVICE_CATALOG.md`

### Widget Documentation
- **Widget Integration Checklist**: `docs/brain/10-architecture/WIDGET_INTEGRATION_CHECKLIST.md`
- **Widget Reference Implementations**: `docs/brain/10-architecture/WIDGET_REFERENCE_IMPLEMENTATIONS.md`

---

## 🚨 What NOT to Do

### ❌ DO NOT Create New Services
- **Rule**: Check `SERVICE_REGISTRY_COMPLETE.md` first
- **If service exists**: Use it (don't create alternative)
- **If unsure**: Ask before creating

### ❌ DO NOT Invent Patterns
- **Presentational/Container split**: NOT documented, NOT required
- **Portable/Standalone architecture**: NOT documented, NOT required
- **Connector interfaces**: NOT documented, NOT required

### ✅ DO Use Existing Patterns
- Use `GlobalMidiEventBus` for all event communication
- Use `GlobalMidiIngestService.emitExternalChordDetection()` for external chord sources
- Use existing bridge services (GuitarTubeSwarmBridge, chordCubesBridge, hpLiveEntryBridge)

---

## 🎯 For Chord Cubes / Harmonic Profile Agent

### Current State (Verified in Code)

1. **Chord Cubes**:
   - ✅ `ChordCubesEmbed.tsx` exists and emits to `globalMidiEventBus`
   - ✅ `chordCubesBridge.ts` exists for iframe communication
   - ✅ Subscribes to `chord:detected` events (line 367)

2. **Harmonic Profile**:
   - ✅ `hpLiveEntryBridge.ts` exists
   - ✅ Emits `live:chord` CustomEvents
   - ✅ LiveHub listens and forwards to MSM

3. **LiveHub**:
   - ✅ Listens to both `live:chord` and `chord:detected`
   - ✅ Forwards to MSM iframe

### What to Verify

1. **Check existing connections**: Verify both widgets are using existing services
2. **No new services**: Don't create new bridges - use existing ones
3. **Follow existing patterns**: Match how `GuitarTubeSwarmBridge` works

---

## 📖 Quick Reference: Key Files

- **Global Event Bus**: `src/services/GlobalMidiEventBus.ts` (EXISTS)
- **MIDI Ingest Service**: `src/services/GlobalMidiIngestService.ts` (EXISTS)
- **GuitarTube Bridge**: `src/services/guitartube/GuitarTubeSwarmBridge.ts` (EXISTS)
- **Chord Cubes Bridge**: `src/services/chordCubesBridge.ts` (EXISTS)
- **Chord Cubes Embed**: `src/components/olympus/ChordCubesEmbed.tsx` (EXISTS)
- **HP Bridge**: `src/components/harmonic/hpLiveEntryBridge.ts` (EXISTS)
- **LiveHub**: `src/pages/LiveHub.tsx` (EXISTS)

---

**⚠️ REMINDER: This document ONLY describes what EXISTS. Do NOT invent new patterns. Use existing services from SERVICE_REGISTRY_COMPLETE.md.**
