# KhronosBus Developer Guide
**Version:** Phase F Freeze  
**Last Updated:** 2025-11-30

---

## Quick Start

### For React Components

```typescript
import { useKhronosPosition, useKhronosCommands } from '@/khronos';

function MyWidget() {
  // Get position
  const { position, isPlaying } = useKhronosPosition();
  
  // Get commands
  const { play, pause, stop } = useKhronosCommands();
  
  return (
    <div>
      <p>Measure: {position.measureIndex}, Beat: {position.beatInMeasure}</p>
      <button onClick={play}>Play</button>
      <button onClick={pause}>Pause</button>
    </div>
  );
}
```

### For Non-React Code

```typescript
import { KhronosBus, khronosPlay, getKhronosSnapshot } from '@/khronos';

// Subscribe to ticks
const unsubscribe = KhronosBus.onTick((tick) => {
  console.log('Position:', tick.position);
});

// Send commands
khronosPlay();

// Get state
const snapshot = getKhronosSnapshot();
console.log('Is Playing:', snapshot.isPlaying);
```

---

## Common Use Cases

### 1. Display Current Position

```typescript
import { useKhronosPosition } from '@/khronos';

function PositionDisplay() {
  const { measureIndex, beatInMeasure, ticks } = useKhronosPosition();
  
  return (
    <div>
      {measureIndex + 1}:{beatInMeasure + 1}:{ticks}
    </div>
  );
}
```

### 2. Play/Pause Button

```typescript
import { useKhronosCommands, useKhronosIsPlaying } from '@/khronos';

function PlayPauseButton() {
  const { play, pause, toggle } = useKhronosCommands();
  const isPlaying = useKhronosIsPlaying();
  
  return (
    <button onClick={toggle}>
      {isPlaying ? 'Pause' : 'Play'}
    </button>
  );
}
```

### 3. Seek to Position

```typescript
import { useKhronosCommands } from '@/khronos';

function SeekButton() {
  const { seek } = useKhronosCommands();
  
  const handleSeek = () => {
    seek({ measureIndex: 4, beatInMeasure: 2, ticks: 0 });
  };
  
  return <button onClick={handleSeek}>Seek to Measure 4</button>;
}
```

### 4. Tempo Control

```typescript
import { useKhronosCommands, useKhronosTempo } from '@/khronos';

function TempoControl() {
  const { setTempo } = useKhronosCommands();
  const tempo = useKhronosTempo();
  
  return (
    <div>
      <input
        type="range"
        min="60"
        max="200"
        value={tempo}
        onChange={(e) => setTempo(Number(e.target.value))}
      />
      <span>{tempo} BPM</span>
    </div>
  );
}
```

### 5. Beat-Synced Animation

```typescript
import { useKhronosBeatSync } from '@/khronos';

function AnimatedWidget() {
  const [animationFrame, setAnimationFrame] = useState(0);
  
  useKhronosBeatSync((beat, measure) => {
    // Trigger animation on beat
    setAnimationFrame(beat);
  });
  
  return <div className={`beat-${animationFrame}`}>Animated</div>;
}
```

### 6. Canvas/WebGL Rendering

```typescript
import { useKhronosTickCallback } from '@/khronos';
import { useRef, useEffect } from 'react';

function CanvasRenderer() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  useKhronosTickCallback((tick) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Update canvas based on tick.position
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    // ... render based on position
  });
  
  return <canvas ref={canvasRef} />;
}
```

### 7. Audio Scheduling

```typescript
import { KhronosBus } from '@/khronos';
import { AudioScheduler } from '@/services/audio/AudioScheduler';

// AudioScheduler already subscribes to KhronosBus
// Just use it normally
const scheduler = new AudioScheduler((event) => {
  // Play audio event
  playNote(event.payload);
});

scheduler.schedule({
  id: 'note-1',
  time: 1000, // milliseconds
  payload: { note: 'C4', velocity: 0.7 },
});
```

### 8. EventSpine Queries

```typescript
import { useKhronosPosition } from '@/khronos';
import { getEventSpineStoreSync } from '@/models/EventSpine/EventSpineStoreSync';

function ScoreWidget() {
  const { position } = useKhronosPosition();
  
  // Query events at current position
  const events = getEventSpineStoreSync().getEventsInRange(
    BigInt(position.measureIndex * 960 * 4), // Convert to ticks
    BigInt((position.measureIndex + 1) * 960 * 4)
  );
  
  return <div>{events.length} events at current position</div>;
}
```

---

## Performance Tips

### 1. Use Specific Hooks

```typescript
// ✅ Good: Only subscribe to what you need
const measureIndex = useKhronosMeasureIndex();

// ⚠️ Avoid: Subscribing to full position when you only need measure
const { position } = useKhronosPosition();
const measureIndex = position.measureIndex;
```

### 2. Throttle Heavy Operations

```typescript
// Throttle updates to 100ms
const { position } = useKhronosPosition({ throttleMs: 100 });
```

### 3. Use Callback Hooks for Canvas

```typescript
// ✅ Good: Use callback hook for canvas
useKhronosTickCallback((tick) => {
  // Update canvas
});

// ⚠️ Avoid: Using position hook for canvas (causes re-renders)
const { position } = useKhronosPosition();
useEffect(() => {
  // Update canvas
}, [position]);
```

### 4. Only Update When Playing

```typescript
// Only update when playing
const { position } = useKhronosPosition({ onlyWhenPlaying: true });
```

---

## Debugging

### Enable Debug Mode

```typescript
// In browser console
window.__KHRONOS_DEBUG = true;
window.__KHRONOS_DEBUG_DRIFT = true;
```

### Check Telemetry

```typescript
const telemetry = window.__khronosBus.getTelemetry();
console.log('Jitter:', telemetry.jitterMaxMs);
console.log('Drift Heat:', telemetry.driftHeat);
console.log('Integrity Score:', telemetry.positionalIntegrityScore);
```

### Monitor Subscribers

```typescript
console.log('Tick Subscribers:', window.__khronosBus.getSubscriberCount('khronos:tick'));
```

---

## Best Practices

### 1. Always Unsubscribe

```typescript
useEffect(() => {
  const unsubscribe = KhronosBus.onTick((tick) => {
    // Handle tick
  });
  return unsubscribe; // Cleanup
}, []);
```

### 2. Use Hooks in React

```typescript
// ✅ Good: Use hooks
const { position } = useKhronosPosition();

// ⚠️ Avoid: Manual subscription in React
useEffect(() => {
  const unsub = KhronosBus.onTick((tick) => setPosition(tick.position));
  return unsub;
}, []);
```

### 3. Use Helper Functions

```typescript
// ✅ Good: Use helper functions
khronosPlay();

// ⚠️ Avoid: Direct publish (unless needed)
KhronosBus.publish(KHRONOS_EVENTS.COMMAND, { command: 'play' });
```

### 4. Don't Create Multiple Subscriptions

```typescript
// ❌ Bad: Multiple subscriptions
useEffect(() => {
  KhronosBus.onTick(handler1);
  KhronosBus.onTick(handler2);
}, []);

// ✅ Good: Single subscription with multiple handlers
useEffect(() => {
  const unsubscribe = KhronosBus.onTick((tick) => {
    handler1(tick);
    handler2(tick);
  });
  return unsubscribe;
}, []);
```

---

## Troubleshooting

### Issue: Position Not Updating

**Solution:**
- Check if KhronosEngine is initialized
- Verify subscription is active
- Check console for errors

### Issue: Commands Not Working

**Solution:**
- Verify KhronosEngine is initialized
- Check command format
- Verify KhronosBus is publishing commands

### Issue: High Jitter

**Solution:**
- Check system performance
- Reduce number of subscribers
- Throttle updates

### Issue: Memory Leaks

**Solution:**
- Always unsubscribe in cleanup
- Use hooks instead of manual subscriptions
- Check for multiple subscriptions

---

## Migration from Legacy APIs

See `TRANSPORT_SERVICE_MIGRATION_GUIDE.md` for detailed migration instructions.

---

## API Reference

See `KHRONOS_API_REFERENCE.md` for complete API documentation.

---

**Last Updated:** 2025-11-30  
**Status:** Phase F Freeze








