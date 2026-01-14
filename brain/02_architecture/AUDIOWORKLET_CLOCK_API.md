# AudioWorklet Clock API Reference
**Version:** Phase F Freeze  
**Last Updated:** 2025-11-30

---

## Overview

The AudioWorklet clock (`khronos-clock.js`) is the hardware-accurate timing source for the entire transport system. It runs in an AudioWorklet processor, providing precise beat calculations based on AudioContext time.

**Location:** `public/worklets/khronos-clock.js`

**Architecture:** `AudioWorklet → KhronosEngine → KhronosBus`

---

## Implementation

### AudioWorklet Processor

```javascript
class KhronosClock extends AudioWorkletProcessor {
  constructor() {
    super();
    this.tempo = 120;
    this.isPlaying = false;
    this.startTime = 0;
    this.pausedElapsed = 0;
    
    // Handle messages from main thread
    this.port.onmessage = (event) => {
      const data = event.data || {};
      if (data.type === 'set-tempo' && typeof data.tempo === 'number') {
        this.tempo = data.tempo;
      }
      if (data.type === 'start') {
        this.startTime = currentTime - this.pausedElapsed;
        this.pausedElapsed = 0;
        this.isPlaying = true;
      }
      if (data.type === 'pause') {
        if (this.isPlaying) {
          this.pausedElapsed = currentTime - this.startTime;
        }
        this.isPlaying = false;
      }
      if (data.type === 'stop' || data.type === 'reset') {
        this.startTime = currentTime;
        this.pausedElapsed = 0;
        this.isPlaying = data.playing || false;
      }
    };
  }

  process() {
    if (!this.isPlaying) {
      return true;
    }

    const elapsedSeconds = currentTime - this.startTime;
    const beats = elapsedSeconds * (this.tempo / 60);
    const beat = Math.floor(beats);
    const beatFraction = beats - beat;
    const measure = Math.floor(beat / 4); // TODO: feed real meter from engine

    // Post message to main thread
    this.port.postMessage({
      currentTime,
      beat,
      beatFraction,
      measure,
    });
    
    return true;
  }
}

registerProcessor('khronos-clock', KhronosClock);
```

---

## Message Protocol

### From Main Thread to AudioWorklet

#### Set Tempo

```javascript
workletNode.port.postMessage({
  type: 'set-tempo',
  tempo: 140, // BPM
});
```

#### Start Playback

```javascript
workletNode.port.postMessage({
  type: 'start',
});
```

#### Pause Playback

```javascript
workletNode.port.postMessage({
  type: 'pause',
});
```

#### Stop/Reset

```javascript
workletNode.port.postMessage({
  type: 'stop', // or 'reset'
  playing: false, // optional, for reset
});
```

---

### From AudioWorklet to Main Thread

#### Beat Update

```javascript
{
  currentTime: number,    // AudioContext.currentTime
  beat: number,          // Current beat (0-based)
  beatFraction: number,  // Fractional part of beat (0-1)
  measure: number,       // Current measure (0-based, 4/4 assumed)
}
```

**Frequency:** Published every audio frame (~128 samples at 44.1kHz = ~2.9ms)

---

## Integration with KhronosEngine

### Loading the AudioWorklet

```typescript
// In KhronosEngine.ts
private async ensureWorklet(): Promise<void> {
  await this.audioContext.audioWorklet.addModule('/worklets/khronos-clock.js');
  this.workletNode = new AudioWorkletNode(this.audioContext, 'khronos-clock');
  this.workletNode.port.onmessage = (event) => this.handleAudioTick(event.data);
}
```

### Handling Beat Updates

```typescript
private handleAudioTick(data: {
  currentTime: number;
  beat?: number;
  beatFraction?: number;
  measure?: number;
}): void {
  if (this.disposed || !this.state.isPlaying) return;
  
  const hasBeatData = typeof data.beat === 'number';
  
  if (hasBeatData) {
    // Convert beats to absolute ticks
    const beatFraction = typeof data.beatFraction === 'number' ? data.beatFraction : 0;
    const totalBeats = data.beat + beatFraction;
    const clockAbsolute = Math.max(0, Math.round(totalBeats * KHRONOS_PPQ));
    let nextAbsoluteTick = this.playStartAbsoluteTick + clockAbsolute;
    
    // Handle loop regions
    if (this.state.loop.enabled && this.loopStartTick !== null && this.loopEndTick !== null) {
      const loopLength = this.loopEndTick - this.loopStartTick;
      if (loopLength > 0 && nextAbsoluteTick >= this.loopEndTick) {
        const offsetWithinLoop = (nextAbsoluteTick - this.loopStartTick) % loopLength;
        nextAbsoluteTick = this.loopStartTick + offsetWithinLoop;
      }
    }
    
    this.state.absoluteTick = Math.max(0, nextAbsoluteTick);
    this.state.position = absoluteTickToPosition(this.state.absoluteTick);
    this.publishTick();
  }
}
```

---

## Timing Accuracy

### Advantages of AudioWorklet

1. **Hardware Accuracy:** Runs in audio thread, synchronized to audio hardware
2. **Low Latency:** Direct access to AudioContext time
3. **Precise Timing:** No JavaScript event loop delays
4. **Consistent:** Frame-accurate timing

### Beat Calculation

```javascript
const elapsedSeconds = currentTime - this.startTime;
const beats = elapsedSeconds * (this.tempo / 60);
```

**Formula:**
- `beats = (elapsedSeconds * tempo) / 60`
- `beat = Math.floor(beats)` (whole beats)
- `beatFraction = beats - beat` (fractional part)

---

## Limitations

### Current Limitations

1. **Fixed Meter:** Assumes 4/4 time signature (hardcoded `Math.floor(beat / 4)`)
2. **No Time Signature Changes:** Doesn't handle meter changes
3. **Simple Beat Calculation:** Doesn't account for tempo changes during playback

### Future Enhancements

1. **Dynamic Meter:** Accept time signature from engine
2. **Tempo Changes:** Handle tempo changes during playback
3. **Complex Time Signatures:** Support for 3/4, 6/8, etc.

---

## Debugging

### Enable Debug Logging

```typescript
// In KhronosEngine, add debug logging
if (typeof window !== 'undefined' && (window as any).__KHRONOS_DEBUG) {
  console.log('[KhronosEngine] AudioWorklet tick:', data);
}
```

### Check AudioWorklet Status

```typescript
// In browser console
const engine = window.__khronosEngine;
console.log('Worklet Node:', engine?.workletNode);
console.log('Worklet Ready:', engine?.workletReady);
```

---

## Testing

### Manual Test

1. Load page
2. Check console for AudioWorklet load errors
3. Start playback
4. Monitor beat updates in console
5. Verify beats increment correctly

### Automated Test

```typescript
// Test AudioWorklet loading
test('AudioWorklet loads successfully', async () => {
  const engine = initializeKhronosEngine();
  await engine?.workletReady;
  expect(engine?.workletNode).toBeDefined();
});

// Test beat calculation
test('Beat calculation is accurate', async () => {
  const engine = initializeKhronosEngine();
  await engine?.workletReady;
  
  // Start playback
  engine?.play();
  
  // Wait for beat updates
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  // Verify beats incremented
  const snapshot = getKhronosSnapshot();
  expect(snapshot.absoluteTick).toBeGreaterThan(0);
});
```

---

## Performance Considerations

### AudioWorklet Thread

- Runs in dedicated audio thread
- No JavaScript event loop delays
- Frame-accurate timing (~2.9ms at 44.1kHz)

### Message Passing

- Messages are asynchronous
- Low overhead
- No blocking operations

### Beat Update Frequency

- Updates every audio frame (~128 samples)
- At 44.1kHz: ~344 updates/second
- KhronosEngine throttles to ~60Hz for UI updates

---

## Error Handling

### AudioWorklet Load Failure

```typescript
try {
  await this.audioContext.audioWorklet.addModule('/worklets/khronos-clock.js');
} catch (err) {
  console.error('[KhronosEngine] Failed to load AudioWorklet clock', err);
  // Fallback to delta-based timing
}
```

### Fallback Behavior

If AudioWorklet fails to load, KhronosEngine falls back to delta-based timing using `performance.now()`.

---

## Migration Notes

### From Tone.Transport

**Before:**
- Tone.Transport used JavaScript timers
- Timing was approximate
- Subject to event loop delays

**After:**
- AudioWorklet provides hardware-accurate timing
- No event loop delays
- Frame-accurate timing

---

## Best Practices

### 1. Always Check Worklet Ready

```typescript
await engine.workletReady;
// Now safe to use worklet
```

### 2. Handle Load Failures

```typescript
try {
  await ensureWorklet();
} catch (err) {
  // Handle error gracefully
}
```

### 3. Clean Up on Dispose

```typescript
dispose() {
  if (this.workletNode) {
    this.workletNode.port.onmessage = null;
    this.workletNode.disconnect();
    this.workletNode = null;
  }
}
```

---

## Related Documentation

- `KHRONOS_API_REFERENCE.md` - KhronosBus API
- `DEVELOPER_GUIDE_KHRONOS.md` - Developer guide
- `PHASE_F_FREEZE_ARCHITECTURAL_DIAGNOSTIC.md` - Architecture diagnostic

---

**Last Updated:** 2025-11-30  
**Status:** Phase F Freeze








