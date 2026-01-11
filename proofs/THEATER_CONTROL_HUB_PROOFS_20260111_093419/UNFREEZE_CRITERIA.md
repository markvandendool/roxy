# THEATER-010/011 Unfreeze Acceptance Criteria

**Status:** FROZEN
**Date:** 2026-01-11
**Authority:** Chief directive

---

## Overview

THEATER-010 (Scene Switching) and THEATER-011 (Silent Mode) are currently FROZEN.
Mock tests pass but do NOT satisfy unfreeze criteria.

**Unfreeze requires:** Real OBS touched + Real hub.ts in path

---

## Gate A: Real hub.ts in Path (NON-NEGOTIABLE)

### Pass Conditions

1. Test launches **`tools/theater-control-hub/src/hub.ts`** (or imports and starts the same `createHub()` / server entry used by `hub.ts`)
2. **NO TestHub reimplementation** - must use production code
3. Stage and Director connect over WebSocket to hub endpoint
4. Both complete role registration successfully

### Required Artifacts

**File:** `hub_real_e2e_results.json`

```json
{
  "test_name": "hub_real_e2e",
  "timestamp": "2026-01-XX...",
  "hub": {
    "start_timestamp": "...",
    "port": 9137,
    "endpoint": "ws://127.0.0.1:9137/theater-control",
    "implementation": "hub.ts"  // MUST say hub.ts, NOT TestHub
  },
  "clients": {
    "stage": {
      "connected": true,
      "role": "stage",
      "client_id": "stage_..."
    },
    "director": {
      "connected": true,
      "role": "director",
      "client_id": "director_..."
    }
  },
  "message_flow": {
    "commands_sent": 1,
    "events_received": 1,
    "correlation_ids": ["cmd_001", "evt_001"]
  },
  "result": "PASS"
}
```

**Manifest entry required:**
```
<sha256>  hub_real_e2e_results.json
  Gate A: Real hub.ts - PASS
```

---

## Gate B: Real OBS Touched (UNFREEZE CONDITION)

### Pass Conditions

1. Test establishes **real OBS WebSocket connection** to configured host/port (default 4455)
2. Test calls **`GetVersion`** and records structured response
3. Test performs **one real scene switch**:
   - Calls `SetCurrentProgramScene` with real scene name from mapping config
   - Confirms success via return code OR by calling `GetCurrentProgramScene`

### Required Artifacts

**File:** `obs_ws_transcript.json`

```json
{
  "test_name": "obs_real_connection",
  "timestamp": "2026-01-XX...",
  "connection": {
    "host": "127.0.0.1",
    "port": 4455,
    "connected": true,
    "protocol_version": "5.x"
  },
  "get_version": {
    "request_id": "...",
    "obs_version": "30.x.x",
    "obs_web_socket_version": "5.x.x",
    "platform": "linux"
  },
  "scene_switch": {
    "request": {
      "request_type": "SetCurrentProgramScene",
      "scene_name": "MindSong Performance 8K"
    },
    "response": {
      "request_status": {
        "result": true,
        "code": 100
      }
    }
  },
  "verify_scene": {
    "request_type": "GetCurrentProgramScene",
    "current_scene_name": "MindSong Performance 8K"
  },
  "result": "PASS"
}
```

**File:** `obs_ws_log_excerpt.txt` (10-50 lines max)

```
[2026-01-XX HH:MM:SS] Connecting to OBS WebSocket at ws://127.0.0.1:4455
[2026-01-XX HH:MM:SS] Connected successfully
[2026-01-XX HH:MM:SS] Sending GetVersion request
[2026-01-XX HH:MM:SS] GetVersion response: OBS 30.x.x, WebSocket 5.x.x
[2026-01-XX HH:MM:SS] Sending SetCurrentProgramScene: MindSong Performance 8K
[2026-01-XX HH:MM:SS] Scene switch successful
[2026-01-XX HH:MM:SS] Verifying with GetCurrentProgramScene
[2026-01-XX HH:MM:SS] Current scene confirmed: MindSong Performance 8K
```

**Manifest entries required:**
```
<sha256>  obs_ws_transcript.json
  Gate B: Real OBS - GetVersion + SetCurrentProgramScene - PASS

<sha256>  obs_ws_log_excerpt.txt
  Gate B: OBS connection log excerpt
```

---

## Gate C: Preset→Scene Bridge Through Real Hub (THEATER-010)

### Pass Conditions

1. Director sends `set_preset` command **through real hub.ts** to stage
2. Stage emits `preset_changed` event **back through the hub**
3. Director receives event and triggers OBS scene switch using mapping config
4. Scene switch completes successfully (Gate B must also pass)

### Required Artifacts

**File:** `hub_flow_trace.json`

```json
{
  "test_name": "preset_scene_bridge",
  "timestamp": "2026-01-XX...",
  "flow": [
    {
      "step": 1,
      "direction": "director -> hub",
      "message_type": "command",
      "message_id": "cmd_preset_001",
      "payload": {
        "action": "set_preset",
        "preset": "performance"
      },
      "timestamp": "..."
    },
    {
      "step": 2,
      "direction": "hub -> stage",
      "message_type": "command",
      "message_id": "cmd_preset_001",
      "timestamp": "..."
    },
    {
      "step": 3,
      "direction": "stage -> hub",
      "message_type": "event",
      "message_id": "evt_preset_001",
      "payload": {
        "event": "preset_changed",
        "preset": "performance"
      },
      "timestamp": "..."
    },
    {
      "step": 4,
      "direction": "hub -> director",
      "message_type": "event",
      "message_id": "evt_preset_001",
      "timestamp": "..."
    },
    {
      "step": 5,
      "action": "obs_scene_switch",
      "scene": "MindSong Performance 8K",
      "result": "success",
      "timestamp": "..."
    }
  ],
  "timestamps_monotonic": true,
  "result": "PASS"
}
```

**Manifest entry required:**
```
<sha256>  hub_flow_trace.json
  Gate C: Preset->Scene bridge through real hub - PASS
```

---

## Gate D: Recording Mode Toggles Published (THEATER-011)

### Pass Conditions

1. Director enters recording mode:
   - Publishes to `ghost.roxy.mode` topic
   - Payload includes `mode=recording` and `actions` list
2. Director exits recording mode:
   - Publishes `mode=normal`
3. Both publishes captured by test harness

**Note:** If using real NATS, this gate is fully verified. If using a publish stub, this is "staged" verification only.

### Required Artifacts

**File:** `roxy_mode_events.json`

```json
{
  "test_name": "recording_mode_transitions",
  "timestamp": "2026-01-XX...",
  "nats_connected": true,
  "topic": "ghost.roxy.mode",
  "events": [
    {
      "transition": "enter_recording",
      "payload": {
        "event_type": "mode_changed",
        "session_id": "SESSION_TEST_...",
        "data": {
          "mode": "recording",
          "previous_mode": "normal",
          "actions": [
            "pause_skybeam_timers",
            "mute_notifications",
            "suppress_non_critical_events"
          ]
        }
      },
      "timestamp": "..."
    },
    {
      "transition": "exit_recording",
      "payload": {
        "event_type": "mode_changed",
        "session_id": "SESSION_TEST_...",
        "data": {
          "mode": "normal",
          "previous_mode": "recording",
          "actions": [
            "resume_skybeam_timers",
            "unmute_notifications",
            "enable_all_events"
          ]
        }
      },
      "timestamp": "..."
    }
  ],
  "result": "PASS"
}
```

**Manifest entry required:**
```
<sha256>  roxy_mode_events.json
  Gate D: Recording mode transitions - PASS
```

---

## Decision Rule: What Unfreezes What?

| Story | Required Gates | Status |
|-------|----------------|--------|
| THEATER-010 | A + B + C | Gates A, B, C must all PASS |
| THEATER-011 | A + B + D | Gates A, B, D must all PASS |

### Intermediate States

If Gate B passes but C/D fail:
- Mark as **"Real-OBS Verified / Hub Verified"**
- Still FROZEN until remaining gates pass

---

## Minimal Staged E2E Test Spec

### Recommended Runner Script Shape

Create `selftest_hub_real_e2e.ts`:

```typescript
// 1. Start REAL hub.ts in-process
import { createHub } from './hub';
const hub = createHub({ port: 9137 });
await hub.start();

// 2. Create two WS clients
const stageWs = new WebSocket('ws://127.0.0.1:9137/theater-control?role=stage');
const directorWs = new WebSocket('ws://127.0.0.1:9137/theater-control?role=director');

// 3. Director sends set_preset
directorWs.send(JSON.stringify({
  type: 'command',
  id: 'cmd_preset_001',
  payload: { action: 'set_preset', preset: 'performance' }
}));

// 4. Stage echoes preset_changed
stageWs.on('message', (data) => {
  const msg = JSON.parse(data);
  if (msg.payload?.action === 'set_preset') {
    stageWs.send(JSON.stringify({
      type: 'event',
      id: 'evt_preset_001',
      payload: { event: 'preset_changed', preset: msg.payload.preset }
    }));
  }
});

// 5. Director receives event and calls real OBS
directorWs.on('message', async (data) => {
  const msg = JSON.parse(data);
  if (msg.payload?.event === 'preset_changed') {
    // Connect to real OBS
    const obs = await connectToOBS('127.0.0.1', 4455);
    await obs.call('GetVersion');
    await obs.call('SetCurrentProgramScene', { sceneName: 'MindSong Performance 8K' });
    const current = await obs.call('GetCurrentProgramScene');
    // Verify and write artifacts
  }
});

// 6. Write artifacts and exit
```

This approach:
- Uses real hub.ts (Gate A)
- Touches real OBS (Gate B)
- Exercises preset→scene flow (Gate C)
- Avoids needing full MindSong browser for unfreeze

---

## File Naming Conventions

| Artifact | Filename |
|----------|----------|
| Real hub E2E results | `hub_real_e2e_results.json` |
| OBS WebSocket transcript | `obs_ws_transcript.json` |
| OBS log excerpt | `obs_ws_log_excerpt.txt` |
| Hub flow trace | `hub_flow_trace.json` |
| ROXY mode events | `roxy_mode_events.json` |

All artifacts must have SHA256 entries in `sha256_manifest.txt`.

---

## Governance Enforcement

Per Chief directive:
> Any test labeled E2E must import or execute the REAL implementation under test (hub.ts, obs_client.py, etc). Inline reimplementations are PROTOCOL tests only.

Violation = immediate status reclassification from VERIFIED to PROTOCOL-VERIFIED.
