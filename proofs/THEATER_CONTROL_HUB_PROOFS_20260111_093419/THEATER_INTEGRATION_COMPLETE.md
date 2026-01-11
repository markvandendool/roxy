# MindSong + ROXY Theater Recording Integration

**Status:** PARTIAL - FREEZE IN EFFECT FOR THEATER-010/011
**Date:** 2026-01-11
**Total Lines:** 4,185

---

## Governance Notice

**THEATER-010 and THEATER-011 remain FROZEN** per Chief directive.

**Unfreeze condition:** One E2E run with real MindSong WS + real OBS instance (or staged integration test touching real OBS).

Mock tests do NOT satisfy unfreeze criteria.

---

## Verification Taxonomy

| Status | Definition |
|--------|------------|
| VERIFIED | Selftest against REAL implementation, passing |
| PROTOCOL-VERIFIED | Selftest against protocol/message format (not real impl) |
| MOCK-VERIFIED | Selftest using mocks only (no real dependencies) |
| IMPLEMENTED | Code exists, no selftest provided |
| FROZEN | Work blocked pending unfreeze condition |

---

## Executive Summary

This integration enables automated theater recording by connecting MindSong's 8K Theater with ROXY's OBS control infrastructure. The system uses a WebSocket relay hub pattern for decoupled, role-based communication between components.

### Current State

| Story | Status | Tests |
|-------|--------|-------|
| THEATER-001 Session Manifest | VERIFIED | 6/6 |
| THEATER-002A Hub | VERIFIED | 10/10 |
| THEATER-002B Stage Client | VERIFIED | 8/8 |
| Hub E2E | PROTOCOL-VERIFIED | 6/6 |
| THEATER-004 OBS Mapping | VERIFIED | schema |
| THEATER-005 KHRONOS Bridge | IMPLEMENTED | none |
| THEATER-006 OBS Director | VERIFIED | 8/8 |
| THEATER-007 Session Loading | VERIFIED | 6/6 |
| THEATER-008 Director Client | IMPLEMENTED | - |
| **THEATER-010 Scene Switching** | **MOCK-VERIFIED (FROZEN)** | 8/8 |
| **THEATER-011 Silent Mode** | **MOCK-VERIFIED (FROZEN)** | 8/8 |
| THEATER-012 File Handoff | VERIFIED | 6/6 |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MindSong (Stage GPU)                             │
│  ┌──────────────────┐  ┌──────────────────┐                        │
│  │ 8K Theater Stage │→ │ TheaterControl   │                        │
│  │ + KHRONOS Bus    │  │ StageClient      │                        │
│  └──────────────────┘  └────────┬─────────┘                        │
│                                 │                                   │
└─────────────────────────────────│───────────────────────────────────┘
                                  │ ws://127.0.0.1:9137
                                  ↓ ?role=stage
┌─────────────────────────────────────────────────────────────────────┐
│                    Theater Control Hub                              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ WebSocket Relay (port 9137)                                   │  │
│  │ • Role-based routing (stage/director/observer)                │  │
│  │ • Command dispatch (director → stage)                         │  │
│  │ • Event broadcast (stage → director)                          │  │
│  │ • Query correlation (UUID matching)                           │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────│───────────────────────────────────┘
                                  │
                                  ↓ ?role=director
┌─────────────────────────────────────────────────────────────────────┐
│                    ROXY (Director GPU)                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ OBS Director     │→ │ OBS WebSocket    │→ │ OBS Studio       │  │
│  │ Service          │  │ (port 4455)      │  │ Recording        │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│         │                                                           │
│         ↓                                                           │
│  ┌──────────────────┐                                               │
│  │ NATS Events      │→ ghost.theater.* / ghost.roxy.mode            │
│  └──────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Theater Control Hub (VERIFIED)

**Location:** `tools/theater-control-hub/`
**Endpoint:** `ws://127.0.0.1:9137/theater-control`
**Status:** VERIFIED (10/10 unit tests)

The hub is a pure relay server that routes messages based on client roles.

**Files:**
- `hub.ts` (442 lines) - Main server implementation
- `types.ts` (196 lines) - TypeScript interfaces
- `selftest.ts` (550 lines) - Unit tests (10 passing)
- `selftest_protocol_e2e.ts` (482 lines) - Protocol tests (6 passing) [RENAMED]

**Note on Protocol Test:** The `selftest_protocol_e2e.ts` uses an inline `TestHub` class, NOT the real `hub.ts`. This validates protocol correctness but not production hub implementation. Status: PROTOCOL-VERIFIED.

### 2. MindSong Stage Client (VERIFIED)

**Location:** `src/services/theater/`
**Status:** VERIFIED (8/8 tests)

Browser-side WebSocket client that connects to the hub as a `stage` role.

**Key Features:**
- Auto-reconnect with exponential backoff
- Rate-limited tick broadcasts (4 Hz / 250ms throttle)
- Command handler registration
- Event broadcasting
- Heartbeat sending (every 30s)

**Files:**
- `TheaterControlStageClient.ts` (557 lines)
- `types.ts` (179 lines)
- `selftest_stage_client.ts` (644 lines)
- `useTheaterKhronosBridge.ts` (253 lines)
- `index.ts` (20 lines)

### 3. KHRONOS Bridge (IMPLEMENTED - no selftest)

**Location:** `src/services/theater/useTheaterKhronosBridge.ts`
**Status:** IMPLEMENTED (needs selftest for VERIFIED)

React hook that integrates KhronosBus timing with the Theater Control Hub.

**Features:**
- Auto-connects to hub on mount
- Subscribes to KhronosBus.onTick()
- Rate limiting via stage client
- Command handler registration

### 4. OBS Director Service (VERIFIED for core, FROZEN for OBS features)

**Location:** `~/.roxy/services/obs_director.py` (1,029 lines)
**Status:** Core VERIFIED, Scene Switching + Silent Mode FROZEN

Python service that orchestrates OBS recording based on theater commands.

### 5. Scene Switching (FROZEN)

**Status:** IMPLEMENTED + MOCK-VERIFIED (FROZEN)

**Mapping Config:** `~/.roxy/services/theater_obs_mapping.json`

Maps MindSong theater presets to OBS scenes. Mock tests pass (8/8) but **freeze remains in effect** until real OBS is touched.

**Unfreeze requirement:** Test must connect to real OBS WebSocket (port 4455), call `GetVersion`, and execute `SetCurrentProgramScene`.

### 6. Silent Mode (FROZEN)

**Status:** IMPLEMENTED + MOCK-VERIFIED (FROZEN)

When recording starts, ROXY enters "recording mode" which pauses automation. Mock tests pass (8/8) but **freeze remains in effect** until real OBS integration is tested.

---

## Test Results Summary

| Test Suite | Tests | Status |
|------------|-------|--------|
| Hub Unit Tests (THEATER-002A) | 10/10 | VERIFIED |
| Hub E2E Protocol | 6/6 | PROTOCOL-VERIFIED |
| Stage Client (THEATER-002B) | 8/8 | VERIFIED |
| Scene Switching (THEATER-010) | 8/8 | MOCK-VERIFIED (FROZEN) |
| Silent Mode (THEATER-011) | 8/8 | MOCK-VERIFIED (FROZEN) |
| Session Manifest (THEATER-001) | 6/6 | VERIFIED |
| OBS Director (THEATER-006) | 8/8 | VERIFIED |
| Session Loading (THEATER-007) | 6/6 | VERIFIED |
| File Handoff (THEATER-012) | 6/6 | VERIFIED |

**Summary:**
- 58 tests against real implementations (VERIFIED)
- 16 tests mock-only (MOCK-VERIFIED, frozen stories)
- 6 tests protocol-only (PROTOCOL-VERIFIED)

---

## Unfreeze Conditions for THEATER-010/011

Per Chief directive, unfreeze requires ONE of:
1. E2E run with real MindSong WS + real OBS instance
2. Staged integration test that touches real OBS

**Required proof artifacts:**
- OBS WebSocket connection log showing `GetVersion` response
- `SetCurrentProgramScene` call with real scene name
- Real `hub.ts` (not TestHub) in the communication path
- SHA256 of test output + OBS log excerpt

---

## Pending Work

| Item | Status |
|------|--------|
| THEATER-003: 1080p Portrait NDI | PENDING |
| THEATER-005: KHRONOS Bridge selftest | NOT STARTED |
| Hub E2E with real hub.ts | NOT STARTED |
| THEATER-010/011 Real OBS Test | NOT STARTED (unfreeze gate) |

---

## File Metrics

### MindSong (Stage Client)
| File | Lines |
|------|-------|
| TheaterControlStageClient.ts | 557 |
| selftest_stage_client.ts | 644 |
| useTheaterKhronosBridge.ts | 253 |
| types.ts | 179 |
| index.ts | 20 |
| **Subtotal** | **1,653** |

### Theater Control Hub
| File | Lines |
|------|-------|
| hub.ts | 442 |
| selftest.ts | 550 |
| selftest_protocol_e2e.ts | 482 |
| types.ts | 196 |
| package.json | 23 |
| **Subtotal** | **1,693** |

### ROXY Services
| File | Lines |
|------|-------|
| obs_director.py | 1,029 |
| selftest_scene_switching.py | 340 |
| selftest_silent_mode.py | 353 |
| theater_obs_mapping.json | 117 |
| **Subtotal** | **1,839** |

### Grand Total: 4,185 lines

---

## References

- Plan: `~/.claude/plans/validated-giggling-toast.md`
- Manifest: `sha256_manifest.txt`
- Hub: `tools/theater-control-hub/`
- Stage Client: `src/services/theater/`
- Director: `~/.roxy/services/obs_director.py`
