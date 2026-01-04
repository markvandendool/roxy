# KhronosBus API Reference
**Version:** Phase F Freeze  
**Last Updated:** 2025-11-30

---

## Overview

KhronosBus is the canonical event bus for all time and transport functionality in MindSong JukeHub. It provides a single source of truth for transport state, eliminating timing conflicts and ensuring all components stay synchronized.

**Architecture:** `AudioWorklet → KhronosEngine → KhronosBus → Subscribers`

---

## Core API

### Import

```typescript
import { KhronosBus, KHRONOS_EVENTS } from '@/khronos';
```

### Event Names

```typescript
KHRONOS_EVENTS = {
  TICK: 'khronos:tick',           // Published every frame during playback
  PLAY: 'khronos:play',           // Play command executed
  PAUSE: 'khronos:pause',         // Pause command executed
  STOP: 'khronos:stop',           // Stop command executed
  SEEK: 'khronos:seek',            // Seek command executed
  TEMPO: 'khronos:tempo',          // Tempo changed
  LOOP: 'khronos:loop',            // Loop region changed
  COMMAND: 'khronos:command',     // Transport command published
  INITIALIZED: 'khronos:initialized', // Engine initialized
  DISPOSED: 'khronos:disposed',    // Engine disposed
}
```

---

## Subscribing to Events

### Subscribe to Tick Events (Most Common)

```typescript
import { KhronosBus } from '@/khronos';

// Subscribe to tick events (published every frame during playback)
const unsubscribe = KhronosBus.onTick((tick) => {
  console.log('Position:', tick.position);
  console.log('Is Playing:', tick.isPlaying);
  console.log('Tempo:', tick.tempo);
});

// Cleanup
unsubscribe();
```

### Subscribe to Any Event

```typescript
const unsubscribe = KhronosBus.subscribe('khronos:play', (payload) => {
  console.log('Play event:', payload);
});

unsubscribe();
```

### Subscribe to Commands

```typescript
const unsubscribe = KhronosBus.onCommand((command) => {
  console.log('Command:', command.command);
  console.log('Position:', command.position);
});

unsubscribe();
```

---

## Publishing Commands

### Direct Command Publishing

```typescript
import { KhronosBus, KHRONOS_EVENTS } from '@/khronos';
import type { KhronosCommand, KhronosPosition } from '@/khronos';

// Play
KhronosBus.publish(KHRONOS_EVENTS.COMMAND, {
  command: 'play',
  requestedAt: performance.now(),
});

// Pause
KhronosBus.publish(KHRONOS_EVENTS.COMMAND, {
  command: 'pause',
});

// Stop
KhronosBus.publish(KHRONOS_EVENTS.COMMAND, {
  command: 'stop',
});

// Seek
KhronosBus.publish(KHRONOS_EVENTS.COMMAND, {
  command: 'seek',
  position: { measureIndex: 4, beatInMeasure: 2, ticks: 0 },
});

// Set Tempo
KhronosBus.publish(KHRONOS_EVENTS.COMMAND, {
  command: 'set-tempo',
  tempo: 140,
});

// Set Loop
KhronosBus.publish(KHRONOS_EVENTS.COMMAND, {
  command: 'set-loop',
  loop: {
    start: { measureIndex: 0, beatInMeasure: 0, ticks: 0 },
    end: { measureIndex: 4, beatInMeasure: 0, ticks: 0 },
    enabled: true,
  },
});
```

### Using Helper Functions (Recommended)

```typescript
import {
  khronosPlay,
  khronosPause,
  khronosStop,
  khronosSeek,
  khronosSetTempo,
  khronosSetLoop,
  khronosClearLoop,
} from '@/khronos';

// Simpler API
khronosPlay();
khronosPause();
khronosStop();
khronosSeek({ measureIndex: 4, beatInMeasure: 2, ticks: 0 });
khronosSetTempo(140);
khronosSetLoop({
  start: { measureIndex: 0, beatInMeasure: 0, ticks: 0 },
  end: { measureIndex: 4, beatInMeasure: 0, ticks: 0 },
  enabled: true,
});
khronosClearLoop();
```

---

## React Hooks

### Position Hooks

```typescript
import {
  useKhronosPosition,
  useKhronosMeasureIndex,
  useKhronosBeatInMeasure,
  useKhronosTicks,
  useKhronosAbsoluteTick,
  useKhronosIsPlaying,
  useKhronosTempo,
} from '@/khronos';

function MyWidget() {
  // Full position object
  const { position, measureIndex, beatInMeasure, ticks, absoluteTick, isPlaying } =
    useKhronosPosition();

  // Or individual values (fewer re-renders)
  const measureIndex = useKhronosMeasureIndex();
  const beatInMeasure = useKhronosBeatInMeasure();
  const ticks = useKhronosTicks();
  const absoluteTick = useKhronosAbsoluteTick();
  const isPlaying = useKhronosIsPlaying();
  const tempo = useKhronosTempo();

  return <div>Measure: {measureIndex}, Beat: {beatInMeasure}</div>;
}
```

### Command Hooks

```typescript
import { useKhronosCommands } from '@/khronos';

function TransportControls() {
  const { play, pause, stop, seek, setTempo, setLoop, clearLoop } = useKhronosCommands();

  return (
    <div>
      <button onClick={play}>Play</button>
      <button onClick={pause}>Pause</button>
      <button onClick={stop}>Stop</button>
      <button onClick={() => seek({ measureIndex: 0, beatInMeasure: 0, ticks: 0 })}>
        Seek to Start
      </button>
      <button onClick={() => setTempo(140)}>Set Tempo 140</button>
    </div>
  );
}
```

### Callback Hooks (for Canvas/WebGL)

```typescript
import { useKhronosTickCallback, useKhronosBeatSync, useKhronosMeasureSync } from '@/khronos';

function CanvasRenderer() {
  // Every tick
  useKhronosTickCallback((tick) => {
    // Update canvas based on tick.position
  });

  // On beat boundaries
  useKhronosBeatSync((beat, measure) => {
    // Trigger beat-synced animation
  });

  // On measure boundaries
  useKhronosMeasureSync((measure) => {
    // Change section
  });

  return <canvas />;
}
```

---

## Type Definitions

### KhronosTick

```typescript
interface KhronosTick {
  position: KhronosPosition;
  absoluteTick: number;
  tempo: number;
  isPlaying: boolean;
  loop?: KhronosLoopRegion;
  timestamp: number; // performance.now()
}
```

### KhronosPosition

```typescript
interface KhronosPosition {
  measureIndex: number;  // 0-based
  beatInMeasure: number;  // 0-based
  ticks: number;         // 0-959 (KHRONOS_PPQ = 960)
}
```

### KhronosCommand

```typescript
type KhronosCommand = {
  command: 'play' | 'pause' | 'stop' | 'seek' | 'set-tempo' | 'toggle' | 'restart' | 'set-loop' | 'clear-loop';
  position?: KhronosPosition;
  tempo?: number;
  loop?: KhronosLoopRegion;
  source?: string;
  requestedAt?: number;
}
```

### KhronosLoopRegion

```typescript
interface KhronosLoopRegion {
  start: KhronosPosition | null;
  end: KhronosPosition | null;
  enabled: boolean;
  startTick?: number | null;
  endTick?: number | null;
}
```

---

## Constants

```typescript
KHRONOS_PPQ = 960; // Pulses Per Quarter Note

DEFAULT_KHRONOS_POSITION = {
  measureIndex: 0,
  beatInMeasure: 0,
  ticks: 0,
};
```

---

## Telemetry

### Get Telemetry

```typescript
const telemetry = KhronosBus.getTelemetry();

console.log('Ticks Published:', telemetry.ticksPublished);
console.log('Commands Published:', telemetry.commandsPublished);
console.log('Subscriber Count:', telemetry.subscriberCount);
console.log('Jitter Max (ms):', telemetry.jitterMaxMs);
console.log('Drift Heat:', telemetry.driftHeat);
console.log('Positional Integrity Score:', telemetry.positionalIntegrityScore);
```

### Reset Telemetry

```typescript
KhronosBus.resetTelemetry();
```

---

## Store API (Zustand)

### Using the Store

```typescript
import { useKhronosStore, getKhronosSnapshot, getKhronosPosition } from '@/khronos';

// In React component
function MyComponent() {
  const position = useKhronosStore((s) => s.position);
  const isPlaying = useKhronosStore((s) => s.isPlaying);
  const tempo = useKhronosStore((s) => s.tempo);
  
  return <div>{position.measureIndex}</div>;
}

// Outside React
const snapshot = getKhronosSnapshot();
const position = getKhronosPosition();
```

---

## Best Practices

### 1. Always Unsubscribe

```typescript
useEffect(() => {
  const unsubscribe = KhronosBus.onTick((tick) => {
    // Handle tick
  });
  
  return unsubscribe; // Cleanup on unmount
}, []);
```

### 2. Use Hooks When Possible

```typescript
// ✅ Good: Use hooks
const { position } = useKhronosPosition();

// ⚠️ Avoid: Manual subscription in React
useEffect(() => {
  const unsub = KhronosBus.onTick(...);
  return unsub;
}, []);
```

### 3. Use Helper Functions for Commands

```typescript
// ✅ Good: Use helper functions
khronosPlay();

// ⚠️ Avoid: Direct publish (unless needed)
KhronosBus.publish(KHRONOS_EVENTS.COMMAND, { command: 'play' });
```

### 4. Throttle Heavy Operations

```typescript
// For expensive operations, throttle updates
const { position } = useKhronosPosition({ throttleMs: 100 });
```

### 5. Use Specific Hooks for Performance

```typescript
// ✅ Good: Only subscribe to what you need
const measureIndex = useKhronosMeasureIndex();

// ⚠️ Avoid: Subscribing to full position when you only need measure
const { position } = useKhronosPosition();
const measureIndex = position.measureIndex;
```

---

## Debugging

### Enable Debug Mode

```typescript
// In browser console
window.__KHRONOS_DEBUG = true;
window.__KHRONOS_DEBUG_DRIFT = true;

// Access bus directly
window.__khronosBus.getTelemetry();
```

### Check Subscribers

```typescript
KhronosBus.hasSubscribers('khronos:tick'); // true/false
KhronosBus.getSubscriberCount('khronos:tick'); // number
```

---

## Migration from TransportService

See `TRANSPORT_SERVICE_MIGRATION_GUIDE.md` for detailed migration instructions.

---

**Last Updated:** 2025-11-30  
**Status:** Phase F Freeze








