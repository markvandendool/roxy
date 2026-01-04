## Khronos → Audio Path (Release Snapshot)
- User click → NVX1Score/Olympus UI → PlaybackController.play() → KhronosAudioBridge → AudioPlaybackService.start()
- AudioScheduler runs in `mode='khronos'`, consuming `KhronosBus` ticks.
- Events normalized via OpenDAWTimeline → scheduler queue → UniversalAudioRouter/Apollo → speakers.
- Debug hooks: `__KHRONOS_TICK_COUNT__`, `__AUDIO_SCHEDULER_DEBUG__`, `__NVX1_PLAYBACK_DEBUG__`.
- Single timing authority: AudioWorklet clock (`khronos-clock.js`). No Tone.Transport timing.

## Instrument Registry & Mapping
- GlobalInstrumentRegistry: GM + VGM-lite + orchestral-lite + pop presets (ToneJS-safe roots).
- InstrumentLoader: presets carry ADSR, velocityCurve, optional pan; fallbacks always resolve.
- ScoreInstrumentAdapter heuristics (priority order): chip/8-bit/square lead → synth.lead.square; EP/Rhodes → keys.ep; pads → synth.pad.warm; strings/violin/cello/contrabass → orch.strings.ensemble; brass/horn/trumpet/trombone → orch.brass.horn; flute/clarinet/oboe/bassoon → orch.winds.flute; choir/vox → choir.ensemble; marimba/bells → mallet.marimba; harp → harp.standard; drums → drums.standard; bass → guitar.clean; generic piano → piano.grand. Instrument pan defaults used when part pan is absent.

## ChordCubes Timing
- Arpeggios scheduled on Khronos ticks (absoluteTick + tempo/KHRONOS_PPQ), no setTimeout.
- Uses current tempo snapshot; only routes through UniversalAudioRouter/Apollo. UI/scene untouched.

## Rocky Optimized Function (Edge)
- Cache keys: `params_hash` / `_queryHash`, columns `nvx1_score`, `audio_render_url`, `cached` flag (false on first response, true on hits).
- Validation: chords array required, key string required, `_queryHash` required; invalid JSON → 400 (`validation_error`).
- 500 reserved for internal errors. Cached responses still update usage stats in background.

## Manual Verification (browser)

### NVX1Score/Olympus Playback
1. Load a score (NVX1Score.tsx or Olympus.tsx)
2. Press Play → verify:
   - Audio plays (not silent)
   - Ticks advance (`window.__KHRONOS_TICK_COUNT__` increments)
   - Scheduler queue > 0 (`window.__AUDIO_SCHEDULER_DEBUG__.diagnostics.queueSize > 0`)
   - Mode is 'khronos' (`window.__AUDIO_SCHEDULER_DEBUG__.mode === 'khronos'`)
   - Playhead stays in sync with audio (±50ms tolerance)

### ChordCubes Arpeggios
1. Trigger an arpeggio → verify:
   - Steady timing (no drift)
   - No setTimeout usage (all scheduling via KhronosBus ticks)
   - Arpeggio notes play in correct order

### Rocky Optimized Function
1. Invalid request (empty chords) → 400 with `error: 'validation_error'`, `fields: ['chords']`
2. Valid new query → 200 with `cached: false`
3. Same query repeated → 200 with `cached: true`

## Debug Variables (Browser Console)

### Khronos Timing
- `window.__KHRONOS_TICK_COUNT__` - Total ticks published by KhronosEngine
- `window.__KHRONOS_DEBUG__` - Enable verbose Khronos logging
- `window.__KHRONOS_DEBUG_DRIFT__` - Enable drift diagnostics

### Audio Scheduler
- `window.__AUDIO_SCHEDULER_DEBUG__` - Scheduler state (mode, queueSize, diagnostics)
- `window.__SCHEDULER_DEBUG_TICKS__` - Enable tick-by-tick logging (dev only)

### NVX1 Playback
- `window.__NVX1_PLAYBACK_DEBUG__` - Playback state (position, isPlaying, tempo)
- `window.nvxDebug()` - Run comprehensive diagnostics snapshot

### Audio Routing
- `window.DEBUG_AUDIO_ROUTING` - Enable audio routing debug logs

## How to Debug Audio Playback in Chrome

1. **Open DevTools → Console**
2. **Check Khronos ticks**: `window.__KHRONOS_TICK_COUNT__` should increment when playing
3. **Check scheduler queue**: `window.__AUDIO_SCHEDULER_DEBUG__.diagnostics.queueSize` should be > 0
4. **Check audio context**: `window.__AUDIO_SCHEDULER_DEBUG__.audioContext.state` should be 'running'
5. **Enable verbose logging**: Set `window.__KHRONOS_DEBUG__ = true` and `window.__SCHEDULER_DEBUG_TICKS__ = true`
6. **Run diagnostics**: `window.nvxDebug()` for full system snapshot

## Understanding Instrument Fallback Chain

1. **Part-level instrument** (`part.instrument.id` or `part.instrument.name`) - highest priority
2. **Name hints** (specific → general): chip/8-bit → synth.lead.square; EP/Rhodes → keys.ep; etc.
3. **Family mapping**: guitar → guitar.acoustic; piano → piano.grand; etc.
4. **Partial matches**: If exact match fails, try substring matching
5. **Ultimate fallback**: `guitar.acoustic` (safe default)

**Priority order ensures deterministic mapping** - same score always maps to same instruments.

## Khronos Timing Safety Checklist

- [ ] KhronosEngine initialized (`window.__KHRONOS_TICK_COUNT__` exists)
- [ ] Ticks advancing (`window.__KHRONOS_TICK_COUNT__` increments)
- [ ] AudioScheduler mode is 'khronos' (`window.__AUDIO_SCHEDULER_DEBUG__.mode === 'khronos'`)
- [ ] Scheduler queue > 0 when playing
- [ ] No Tone.Transport timing (Phase F - KhronosEngine is master clock)
- [ ] AudioContext state is 'running'
- [ ] No duplicate ticks (check `window.__KHRONOS_DEBUG_DRIFT__` if enabled)
- [ ] Playhead/audio alignment within ±50ms tolerance
