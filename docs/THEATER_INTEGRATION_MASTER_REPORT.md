# Theater Control Integration Master Report

**Version:** 1.0.0
**Date:** 2026-01-11T14:30:00-07:00
**Author:** Claude Opus 4.5 (ROXY + MindSong coordination)
**Status:** READY FOR IMPLEMENTATION

---

## Executive Summary

This report documents the complete integration plan for connecting ROXY's OBS Director to MindSong's 8K Theater via the Theater Control Hub. ROXY side is **READY**. MindSong side needs **handler wiring**.

**Goal:** Director (ROXY) sends commands through Hub to Stage (MindSong) for automated theater recording with EventSpine-driven drum animations.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Hub Protocol](#2-hub-protocol)
3. [ROXY Components (READY)](#3-roxy-components-ready)
4. [MindSong Components (NEED WIRING)](#4-mindsong-components-need-wiring)
5. [Q&A Evidence Bank](#5-qa-evidence-bank)
6. [Handler Wiring Specification](#6-handler-wiring-specification)
7. [DrumKit Visibility Control](#7-drumkit-visibility-control)
8. [Exit Criteria](#8-exit-criteria)
9. [File Reference Matrix](#9-file-reference-matrix)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            ROXY (10.0.0.69)                             │
│  ┌──────────────────────┐    ┌──────────────────────┐                   │
│  │ OBS Director Service │───▶│ Theater Control      │                   │
│  │ obs_director.py      │    │ Client (Director)    │                   │
│  │ (1030 lines, READY)  │    │ Lines 248-427        │                   │
│  └──────────────────────┘    └──────────────────────┘                   │
│           │                           │                                 │
│           │                           │ ws://10.0.0.92:9137             │
│           ▼                           │ ?role=director                  │
│  ┌──────────────────────┐             │                                 │
│  │ OBS WebSocket        │             │                                 │
│  │ Port 4455 (READY)    │             │                                 │
│  └──────────────────────┘             │                                 │
└───────────────────────────────────────│─────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Mac Studio (10.0.0.92)                              │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │              Theater Control Hub (port 9137)                      │  │
│  │              tools/theater-control-hub/src/hub.ts                 │  │
│  │              Start: bun start                                     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│           │                                    │                        │
│           │ Commands                           │ Events                 │
│           ▼                                    │                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │              Theater Control Stage Client                         │  │
│  │              src/services/theater/TheaterControlStageClient.ts    │  │
│  │              Connects as: ?role=stage                             │  │
│  │              Handler registration: onCommand() line 430           │  │
│  │              STATUS: NO HANDLERS WIRED                            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│           │                                                             │
│           ▼                                                             │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐   │
│  │ Widget Manager │  │ NVX1 Store     │  │ Transport Controller   │   │
│  │ (visibility)   │  │ (score load)   │  │ (play/pause/stop)      │   │
│  └────────────────┘  └────────────────┘  └────────────────────────┘   │
│           │                   │                    │                    │
│           ▼                   ▼                    ▼                    │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    8K Theater Stage                               │  │
│  │                    EightKTheaterStage.tsx                         │  │
│  │                    DrumKit: lines 810-950 (visible, no gate)      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Hub Protocol

### 2.1 Connection Endpoints

| Role | URL | Purpose |
|------|-----|---------|
| Stage | `ws://localhost:9137/theater-control?role=stage` | MindSong browser connects |
| Director | `ws://10.0.0.92:9137/theater-control?role=director` | ROXY connects |
| Observer | `ws://localhost:9137/theater-control?role=observer` | Read-only monitoring |

### 2.2 Message Types

```typescript
// Command (Director → Hub → Stage)
{
  "type": "command",
  "id": "msg_1",
  "timestamp": "2026-01-11T14:30:00Z",
  "payload": {
    "action": "play" | "pause" | "stop" | "seek" | "set_preset" |
              "set_widget_visibility" | "load_song" | "start_ndi" | "stop_ndi",
    ...actionSpecificFields
  }
}

// Event (Stage → Hub → Director)
{
  "type": "event",
  "id": "evt_1",
  "timestamp": "2026-01-11T14:30:00Z",
  "payload": {
    "event": "tick" | "playback_changed" | "song_ended" | "song_loaded" |
             "ndi_started" | "preset_changed",
    ...eventSpecificFields
  }
}

// Query (Director → Hub → Stage → Hub → Director)
{
  "type": "query",
  "id": "qry_1",
  "timestamp": "2026-01-11T14:30:00Z",
  "payload": {
    "query": "playback_state" | "current_tick" | "widget_states"
  }
}
```

### 2.3 Command Payloads

| Command | Payload | Handler Target |
|---------|---------|----------------|
| `play` | `{}` | `transportControllerStore.getState().play()` |
| `pause` | `{}` | `transportControllerStore.getState().pause()` |
| `stop` | `{}` | `transportControllerStore.getState().stop()` |
| `seek` | `{ tick: number }` | Transport seek method |
| `seek_seconds` | `{ seconds: number }` | Transport seek by time |
| `set_tempo` | `{ bpm: number }` | Transport tempo |
| `set_preset` | `{ preset: string }` | Theater preset switching |
| `set_widget_visibility` | `{ widgetId: string, visible: boolean }` | `theaterWidgetManager.setWidgetVisibility()` |
| `load_song` | `{ source: "songvault", songId: string }` | SongVaultLoader → NVX1Store |
| `start_ndi` | `{ quality: "high" \| "medium" \| "low" }` | NDI streaming start |
| `stop_ndi` | `{}` | NDI streaming stop |

### 2.4 Event Payloads

| Event | Payload | When Emitted |
|-------|---------|--------------|
| `tick` | `{ tick: number, seconds: number }` | 4Hz during playback (KHRONOS) |
| `playback_changed` | `{ state: "playing" \| "paused" \| "stopped" }` | Transport state change |
| `song_ended` | `{}` | Playback reaches end |
| `song_loaded` | `{ songId: string, success: boolean, error?: string }` | After load_song completes |
| `ndi_started` | `{ streams: string[] }` | NDI streams active |
| `preset_changed` | `{ preset: string }` | Theater preset changed |

---

## 3. ROXY Components (READY)

### 3.1 OBS Director Service

**File:** `~/.roxy/services/obs_director.py` (1030 lines)

**Features:**
- Session manifest loading and validation
- Theater Control WebSocket client (director role)
- OBS recording start/stop with pre/post-roll
- Scene switching based on presets
- SKYBEAM handoff
- NATS event publishing
- Silent mode (pauses ROXY automation during recording)

**Key Classes:**
```python
class TheaterControlClient:  # Lines 248-427
    async def connect() -> bool
    async def send_command(action: str, **kwargs) -> dict
    async def query(query_type: str) -> dict
    async def play() -> dict
    async def pause() -> dict
    async def stop() -> dict
    async def seek(tick: int) -> dict
    async def set_preset(preset: str) -> dict
    async def start_ndi(quality: str) -> dict
    async def get_state() -> dict

class OBSDirectorService:  # Lines 434-982
    async def start_session(manifest_path: str) -> str
    async def begin_recording(session_id: str) -> bool
    async def stop_recording(session_id: str) -> dict
    async def handoff_to_skybeam(session_id: str) -> str
    async def on_theater_event(event: TheaterEvent) -> None
```

### 3.2 OBS WebSocket (Gate B/C/D Verified)

**Port:** 4455 (no auth)
**Selftest:** `selftest_obs_ws_real.py` - PASS
**Recording:** `selftest_gate_d_recording.py` - 5/5 PASS

### 3.3 Scene-Preset Mapping

**File:** `~/.roxy/config/theater_obs_mapping.json`

```json
{
  "mappings": {
    "presets": {
      "analysis": { "obs_scene_landscape": "MindSong Analysis 8K" },
      "performance": { "obs_scene_landscape": "MindSong Performance 8K" },
      "teaching": { "obs_scene_landscape": "MindSong Teaching 8K" },
      "minimal": { "obs_scene_landscape": "MindSong Minimal 8K" },
      "composer": { "obs_scene_landscape": "MindSong Composer 8K" }
    }
  }
}
```

### 3.4 NATS Topics

| Topic | Purpose |
|-------|---------|
| `ghost.theater.status` | Session status updates |
| `ghost.theater.recording.start` | Recording started |
| `ghost.theater.recording.stop` | Recording stopped |
| `ghost.theater.session.complete` | Session complete with job_id |
| `ghost.theater.error` | Error events |
| `ghost.roxy.mode` | Recording mode (normal/recording) |

---

## 4. MindSong Components (NEED WIRING)

### 4.1 Theater Control Stage Client

**File:** `src/services/theater/TheaterControlStageClient.ts`
**Status:** Hub connection works, but NO HANDLERS REGISTERED

**Singleton access:**
```typescript
const client = TheaterControlStageClient.getInstance();
```

**Handler registration (line 430):**
```typescript
public onCommand(action: CommandAction, handler: CommandHandler): () => void {
  const handlers = this.commandHandlers.get(action) ?? [];
  handlers.push(handler);
  this.commandHandlers.set(action, handlers);
  log('debug', `Registered command handler: ${action}`);
  return () => { /* unsubscribe */ };
}
```

**"No handler" log (line 375):**
```typescript
log('warn', `No handler for command: ${action}`);
```

### 4.2 Theater Widget Manager

**File:** `src/components/theater8k/TheaterWidgetManager.ts`
**Singleton (line 307):**
```typescript
export const theaterWidgetManager = new TheaterWidgetManager();
```

**Registry (lines 35-36):**
```typescript
export interface WidgetManagerState {
  widgets: Map<string, WidgetRegistration>;
}
```

**Visibility method (line 189):**
```typescript
setWidgetVisibility(widgetId: string, visible: boolean) {
  const registration = this.state.widgets.get(widgetId);
  if (!registration) return;
  registration.visible = visible;
  console.info(`[WidgetManager] Widget ${widgetId} visibility: ${visible}`);
}
```

### 4.3 Widget IDs

| Widget | ID | Definition File |
|--------|-----|-----------------|
| TRAX | `"trax"` | `widgets/trax/TraxWidget.tsx:41` |
| Metronome | `"toussaint-metronome"` | `widgets/metronome/ToussaintMetronomeWidget.tsx:1031` |
| Piano | `"canvas-piano"` | `widgets/piano/CanvasPianoWidgetDefinition.ts` |
| Fretboard | (in definition) | `widgets/fretboard/FretboardWidgetDefinition.ts` |
| Score Tab | (in definition) | `widgets/score/ScoreTabWidget.tsx` |
| Room Cube | (in definition) | `widgets/room/RoomCubeRoomWidget.tsx` |
| **DrumKit** | **NOT A WIDGET** | `EightKTheaterStage.tsx:810-950` |

### 4.4 Score Loading Path

**Step 1 - Load from SongVault:**
```typescript
// src/services/songvault/SongVaultLoader.ts:556
async loadSongById(id: string): Promise<UnifiedSong | null>
```

**Step 2 - Inject into NVX1Store:**
```typescript
// src/store/nvx1.ts:806
loadScore: async (score: NVX1Score | null) => Promise<void>
```

**Complete path:**
```typescript
import { songVaultLoader } from '@/services/songvault/SongVaultLoader';
import { useNVX1Store } from '@/store/nvx1';

const song = await songVaultLoader.loadSongById(songId);
if (song?.nvx1_score) {
  await useNVX1Store.getState().loadScore(song.nvx1_score);
}
```

### 4.5 Transport Controller

**File:** `src/components/theater8k/transport/transportControllerStore.ts`

**Methods:**
- `play()` - line 316
- `pause()` - line 323
- `stop()` - line 330

**Note:** These dispatch to UnifiedKernel and TransportServiceMSOS.

### 4.6 DrumKit (Three.js Overlay)

**File:** `src/components/theater8k/EightKTheaterStage.tsx:810-950`

**Current state:** Always visible, no control gate.

**Key elements:**
- Canvas: `drumkit-overlay-canvas` (line 845)
- GLB Path: `/assets/drumkit/drumkit-source.glb` (line 824)
- RAF Registration: `schedulerHandle.addListener()` (line 907)
- Renderer: `DrumKitRenderer` from `@/services/olympus/rendering/DrumKitRenderer`

---

## 5. Q&A Evidence Bank

### Q1: Widget Visibility Source of Truth

**Answer:** `theaterWidgetManager.setWidgetVisibility(widgetId, visible)`

**Evidence:**
```
File: src/components/theater8k/TheaterWidgetManager.ts
Line 189: setWidgetVisibility(widgetId: string, visible: boolean)
Line 307: export const theaterWidgetManager = new TheaterWidgetManager();
```

### Q2: Canonical Song Load Path

**Answer:** `songVaultLoader.loadSongById()` → `useNVX1Store.getState().loadScore()`

**Evidence:**
```
File: src/services/songvault/SongVaultLoader.ts:556
  async loadSongById(id: string): Promise<UnifiedSong | null>

File: src/store/nvx1.ts:806
  loadScore: async (score) => { ... }
```

### Q3: DrumKit Widget ID and Mount

**Answer:** DrumKit is NOT a widget. It's a Three.js overlay mounted directly in EightKTheaterStage.tsx.

**Evidence:**
```
File: src/components/theater8k/EightKTheaterStage.tsx
Lines 810-950: DrumKit loading and rendering
Line 824: const drumKitPath = '/assets/drumkit/drumkit-source.glb';
Line 845: drumKitCanvas.id = 'drumkit-overlay-canvas';
```

### Q4: Metronome Integration

**Answer:** ToussaintMetronomeWidget subscribes to TimelineContext.

**Evidence:**
```
File: src/components/theater8k/widgets/metronome/ToussaintMetronomeWidget.tsx
Line 4: import { useTimeline, useTimelineControls, useTimelineRuntime } from "@/components/theater8k/TimelineContext";
Line 1031: id: "toussaint-metronome",
```

### Q5: TRAX Status

**Answer:** Placeholder widget awaiting full WebGPU implementation.

**Evidence:**
```
File: src/components/theater8k/widgets/trax/TraxWidget.tsx
Line 17-37: Returns placeholder div "TRAX WIDGET PLACEHOLDER"
Line 41: id: "trax",
```

### Q6: EventSpine via Theater Commands

**Answer:** NO - transport methods exist but handlers not wired.

**Evidence:**
```
File: src/components/theater8k/transport/transportControllerStore.ts
Line 316: play()
Line 323: pause()
Line 330: stop()

File: src/services/theater/TheaterControlStageClient.ts
Line 375: log('warn', `No handler for command: ${action}`);
```

### Q7: Hub Startup

**Answer:** Manual only. No systemd service or startup script.

**Evidence:**
```
File: tools/theater-control-hub/package.json
  "scripts": { "start": "bun run src/hub.ts" }

Port 9137: NOT BOUND (verified via ss -tlnp)
```

---

## 6. Handler Wiring Specification

### 6.1 New File: `src/services/theater/initTheaterHandlers.ts`

```typescript
/**
 * Theater Control Handler Initialization
 *
 * Wires stage client command handlers to MindSong subsystems.
 * Called once during app initialization.
 */

import { TheaterControlStageClient } from './TheaterControlStageClient';
import { theaterWidgetManager } from '@/components/theater8k/TheaterWidgetManager';
import { useNVX1Store } from '@/store/nvx1';
import { songVaultLoader } from '@/services/songvault/SongVaultLoader';
// Import transport controller when path confirmed

// DrumKit visibility control (set by EightKTheaterStage)
declare global {
  interface Window {
    __setDrumKitVisible?: (visible: boolean) => void;
  }
}

export function initTheaterHandlers(): void {
  const client = TheaterControlStageClient.getInstance();

  console.info('[TheaterHandlers] Registering command handlers...');

  // ========================================
  // Transport Commands
  // ========================================

  client.onCommand('play', async () => {
    console.info('[TheaterHandlers] play command received');
    // TODO: Wire to transportControllerStore.getState().play()
    // Need to confirm exact import path
  });

  client.onCommand('pause', async () => {
    console.info('[TheaterHandlers] pause command received');
    // TODO: Wire to transportControllerStore.getState().pause()
  });

  client.onCommand('stop', async () => {
    console.info('[TheaterHandlers] stop command received');
    // TODO: Wire to transportControllerStore.getState().stop()
  });

  client.onCommand('seek', async (payload) => {
    const { tick } = payload as { tick: number };
    console.info('[TheaterHandlers] seek command received:', tick);
    // TODO: Wire to transport seek
  });

  client.onCommand('set_tempo', async (payload) => {
    const { bpm } = payload as { bpm: number };
    console.info('[TheaterHandlers] set_tempo command received:', bpm);
    // TODO: Wire to transport tempo
  });

  // ========================================
  // Widget Visibility Commands
  // ========================================

  client.onCommand('set_widget_visibility', async (payload) => {
    const { widgetId, visible } = payload as { widgetId: string; visible: boolean };
    console.info('[TheaterHandlers] set_widget_visibility:', widgetId, visible);

    // Special case: DrumKit pseudo-widget
    if (widgetId === 'drumkit') {
      if (window.__setDrumKitVisible) {
        window.__setDrumKitVisible(visible);
      } else {
        console.warn('[TheaterHandlers] DrumKit visibility controller not available');
      }
      return;
    }

    // Regular widgets via TheaterWidgetManager
    theaterWidgetManager.setWidgetVisibility(widgetId, visible);
  });

  // ========================================
  // Song Loading Commands
  // ========================================

  client.onCommand('load_song', async (payload) => {
    const { songId, source } = payload as { songId: string; source?: string };
    console.info('[TheaterHandlers] load_song command received:', songId);

    try {
      // Load from SongVault
      const song = await songVaultLoader.loadSongById(songId);

      if (!song) {
        client.broadcastEvent('song_loaded', { songId, success: false, error: 'not_found' });
        return;
      }

      if (!song.nvx1_score) {
        client.broadcastEvent('song_loaded', { songId, success: false, error: 'no_nvx1_score' });
        return;
      }

      // Inject into NVX1Store
      await useNVX1Store.getState().loadScore(song.nvx1_score);

      // Broadcast success
      client.broadcastEvent('song_loaded', {
        songId,
        success: true,
        title: song.title,
        duration: song.duration_seconds
      });

      console.info('[TheaterHandlers] Song loaded successfully:', song.title);

    } catch (error) {
      console.error('[TheaterHandlers] Song load error:', error);
      client.broadcastEvent('song_loaded', {
        songId,
        success: false,
        error: error instanceof Error ? error.message : 'unknown'
      });
    }
  });

  // ========================================
  // NDI Commands (placeholder)
  // ========================================

  client.onCommand('start_ndi', async (payload) => {
    const { quality } = payload as { quality: string };
    console.info('[TheaterHandlers] start_ndi command received:', quality);
    // TODO: Wire to NDI streaming start
  });

  client.onCommand('stop_ndi', async () => {
    console.info('[TheaterHandlers] stop_ndi command received');
    // TODO: Wire to NDI streaming stop
  });

  // ========================================
  // Preset Commands
  // ========================================

  client.onCommand('set_preset', async (payload) => {
    const { preset } = payload as { preset: string };
    console.info('[TheaterHandlers] set_preset command received:', preset);
    // TODO: Wire to theater preset switching
    client.broadcastEvent('preset_changed', { preset });
  });

  console.info('[TheaterHandlers] All handlers registered');
}
```

### 6.2 Integration Point

Add to app initialization (e.g., `App.tsx` or `8KTheaterProvider.tsx`):

```typescript
import { initTheaterHandlers } from '@/services/theater/initTheaterHandlers';

// In useEffect or initialization block:
useEffect(() => {
  initTheaterHandlers();
}, []);
```

---

## 7. DrumKit Visibility Control

### 7.1 Modification to EightKTheaterStage.tsx

Add after line 845 (canvas creation):

```typescript
// DrumKit visibility state
let drumKitVisible = true;

// Expose visibility controller globally
if (typeof window !== 'undefined') {
  (window as any).__setDrumKitVisible = (visible: boolean) => {
    drumKitVisible = visible;
    drumKitCanvas.style.display = visible ? 'block' : 'none';
    console.info('[8KTheater] DrumKit visibility:', visible);
  };
}
```

Update render function (line 896):

```typescript
const renderDrumKit = (timestamp: number) => {
  if (!drumKitVisible) return;  // Skip if hidden
  drumKitRenderer.updateAnimations(timestamp);
  drumKitWebGLRenderer.render(drumKitScene, drumKitCamera);
};
```

### 7.2 Cleanup

Add to cleanup section:

```typescript
// Remove global visibility controller
if (typeof window !== 'undefined') {
  delete (window as any).__setDrumKitVisible;
}
```

---

## 8. Exit Criteria

### Today's E2E Validation

| # | Criterion | Validation Method |
|---|-----------|-------------------|
| 1 | Hub listening on 9137 | `lsof -iTCP:9137 -sTCP:LISTEN` (Mac) |
| 2 | Stage connected | Hub logs show "stage connected" |
| 3 | Director can send commands | ROXY sends `set_preset("drums")`, stage logs it |
| 4 | `load_song` triggers score load | Stage logs `[TheaterHandlers] Song loaded` |
| 5 | `song_loaded` event reaches Director | ROXY logs receive event |
| 6 | `set_widget_visibility` works | Widget toggles in UI |
| 7 | DrumKit visibility toggles | DrumKit shows/hides via command |
| 8 | Transport commands work | `play`/`stop` trigger transport |

### Proof Artifacts Required

1. **Hub startup log** showing port binding
2. **Stage connection log** showing role=stage
3. **Command transcript** showing each command type
4. **Event transcript** showing events from stage
5. **Screenshot** of DrumKit visibility toggle

---

## 9. File Reference Matrix

### ROXY Files (READY)

| File | Purpose | Status |
|------|---------|--------|
| `~/.roxy/services/obs_director.py` | OBS orchestration | READY |
| `~/.roxy/services/obs_client.py` | OBS WebSocket client | READY |
| `~/.roxy/config/theater_obs_mapping.json` | Preset→Scene map | READY |
| `~/.roxy/services/sha256_manifest.txt` | Gate proof | READY |
| `~/.roxy/.breakroom/activity_20260111.md` | Activity log | READY |

### MindSong Files (NEED WORK)

| File | Purpose | Status |
|------|---------|--------|
| `tools/theater-control-hub/src/hub.ts` | WebSocket hub | READY (not running) |
| `src/services/theater/TheaterControlStageClient.ts` | Stage client | NEEDS HANDLERS |
| `src/services/theater/initTheaterHandlers.ts` | Handler init | **CREATE NEW** |
| `src/components/theater8k/TheaterWidgetManager.ts` | Widget visibility | READY |
| `src/components/theater8k/EightKTheaterStage.tsx` | DrumKit | NEEDS GATE |
| `src/store/nvx1.ts` | Score store | READY |
| `src/services/songvault/SongVaultLoader.ts` | Song loader | READY |

### Hub Start Command

```bash
cd ~/mindsong-juke-hub/tools/theater-control-hub
bun start
```

---

## Appendix A: Message Flow Diagrams

### A.1 Song Load Flow

```
ROXY Director                Hub                    Stage Client
     │                        │                          │
     │ command: load_song     │                          │
     │ {songId: "abc-123"}    │                          │
     │───────────────────────▶│                          │
     │                        │ relay to stage           │
     │                        │─────────────────────────▶│
     │                        │                          │
     │                        │                          │ songVaultLoader.loadSongById()
     │                        │                          │ useNVX1Store.loadScore()
     │                        │                          │
     │                        │     event: song_loaded   │
     │                        │◀─────────────────────────│
     │ event: song_loaded     │                          │
     │ {songId, success:true} │                          │
     │◀───────────────────────│                          │
     │                        │                          │
```

### A.2 Recording Session Flow

```
ROXY Director                Hub                    Stage              OBS
     │                        │                       │                  │
     │ connect as director    │                       │                  │
     │───────────────────────▶│                       │                  │
     │                        │                       │                  │
     │ command: set_preset    │                       │                  │
     │───────────────────────▶│──────────────────────▶│                  │
     │                        │                       │                  │
     │ command: start_ndi     │                       │                  │
     │───────────────────────▶│──────────────────────▶│                  │
     │                        │  event: ndi_started   │                  │
     │◀───────────────────────│◀──────────────────────│                  │
     │                        │                       │                  │
     │ StartRecording         │                       │                  │
     │────────────────────────│───────────────────────│─────────────────▶│
     │                        │                       │                  │
     │ command: play          │                       │                  │
     │───────────────────────▶│──────────────────────▶│                  │
     │                        │   event: tick (4Hz)   │                  │
     │◀───────────────────────│◀──────────────────────│                  │
     │                        │                       │                  │
     │                        │  event: song_ended    │                  │
     │◀───────────────────────│◀──────────────────────│                  │
     │                        │                       │                  │
     │ StopRecording          │                       │                  │
     │────────────────────────│───────────────────────│─────────────────▶│
     │                        │                       │                  │
     │ Handoff to SKYBEAM     │                       │                  │
     │                        │                       │                  │
```

---

## Appendix B: NATS Event Examples

```json
// ghost.theater.status
{
  "event_type": "session_started",
  "session_id": "SESSION_20260111_143000_abc12345",
  "timestamp": "2026-01-11T14:30:00Z",
  "data": {
    "preset": "performance",
    "manifest_path": "/home/mark/.roxy/theater-sessions/session_xyz.json"
  }
}

// ghost.theater.recording.start
{
  "event_type": "recording_started",
  "session_id": "SESSION_20260111_143000_abc12345",
  "timestamp": "2026-01-11T14:30:02Z",
  "data": {
    "pre_roll_seconds": 2
  }
}

// ghost.theater.session.complete
{
  "event_type": "session_complete",
  "session_id": "SESSION_20260111_143000_abc12345",
  "timestamp": "2026-01-11T14:35:00Z",
  "data": {
    "job_id": "JOB_20260111_143500_def67890",
    "status": "ingested"
  }
}
```

---

**END OF REPORT**

*Generated: 2026-01-11T14:30:00-07:00*
*Report ID: THEATER-MASTER-REPORT-20260111*
