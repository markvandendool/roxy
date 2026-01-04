# TransportService → KhronosBus Migration Guide
**Version:** Phase F Freeze  
**Last Updated:** 2025-11-30

---

## Overview

This guide helps migrate code from the legacy `TransportService` API to the new `KhronosBus` API. The `TransportService` is now a thin proxy that routes to KhronosBus, but direct KhronosBus usage is recommended for new code.

---

## Migration Checklist

- [ ] Identify all `TransportService` imports
- [ ] Replace with KhronosBus hooks or direct API
- [ ] Update event subscriptions
- [ ] Update command dispatch
- [ ] Test migration
- [ ] Remove `TransportService` import

---

## Common Patterns

### Pattern 1: Getting Position

#### Before (TransportService)

```typescript
import transportService from '@/services/TransportService';

// In component
const [position, setPosition] = useState(null);

useEffect(() => {
  const unsubscribe = transportService.subscribe((state) => {
    setPosition(state.currentPosition);
  });
  return unsubscribe;
}, []);
```

#### After (KhronosBus Hook)

```typescript
import { useKhronosPosition } from '@/khronos';

// In component
const { position } = useKhronosPosition();
```

#### After (Direct Subscription)

```typescript
import { KhronosBus } from '@/khronos';

useEffect(() => {
  const unsubscribe = KhronosBus.onTick((tick) => {
    const position = tick.position;
    // Use position
  });
  return unsubscribe;
}, []);
```

---

### Pattern 2: Play/Pause/Stop

#### Before (TransportService)

```typescript
import transportService from '@/services/TransportService';

transportService.play();
transportService.pause();
transportService.stop();
```

#### After (KhronosBus Helper)

```typescript
import { khronosPlay, khronosPause, khronosStop } from '@/khronos';

khronosPlay();
khronosPause();
khronosStop();
```

#### After (React Hook)

```typescript
import { useKhronosCommands } from '@/khronos';

function MyComponent() {
  const { play, pause, stop } = useKhronosCommands();
  
  return (
    <div>
      <button onClick={play}>Play</button>
      <button onClick={pause}>Pause</button>
      <button onClick={stop}>Stop</button>
    </div>
  );
}
```

---

### Pattern 3: Seek

#### Before (TransportService)

```typescript
import transportService from '@/services/TransportService';

transportService.seek(4, 2, 0); // measure, beat, ticks
// or
transportService.seek({ measureIndex: 4, beatInMeasure: 2, ticks: 0 });
```

#### After (KhronosBus Helper)

```typescript
import { khronosSeek } from '@/khronos';

khronosSeek({ measureIndex: 4, beatInMeasure: 2, ticks: 0 });
```

#### After (React Hook)

```typescript
import { useKhronosCommands } from '@/khronos';

function MyComponent() {
  const { seek } = useKhronosCommands();
  
  const handleSeek = () => {
    seek({ measureIndex: 4, beatInMeasure: 2, ticks: 0 });
  };
  
  return <button onClick={handleSeek}>Seek to Measure 4</button>;
}
```

---

### Pattern 4: Set Tempo

#### Before (TransportService)

```typescript
import transportService from '@/services/TransportService';

transportService.setTempo(140);
```

#### After (KhronosBus Helper)

```typescript
import { khronosSetTempo } from '@/khronos';

khronosSetTempo(140);
```

#### After (React Hook)

```typescript
import { useKhronosCommands } from '@/khronos';

function MyComponent() {
  const { setTempo } = useKhronosCommands();
  
  return <button onClick={() => setTempo(140)}>Set Tempo 140</button>;
}
```

---

### Pattern 5: Get State

#### Before (TransportService)

```typescript
import transportService from '@/services/TransportService';

const state = transportService.getState();
const isPlaying = state.isPlaying;
const position = state.currentPosition;
const tempo = state.tempo;
```

#### After (KhronosBus Store)

```typescript
import { useKhronosStore } from '@/khronos';

function MyComponent() {
  const isPlaying = useKhronosStore((s) => s.isPlaying);
  const position = useKhronosStore((s) => s.position);
  const tempo = useKhronosStore((s) => s.tempo);
  
  // Or use hooks
  const { position, isPlaying } = useKhronosPosition();
  const tempo = useKhronosTempo();
}
```

#### After (Outside React)

```typescript
import { getKhronosSnapshot } from '@/khronos';

const snapshot = getKhronosSnapshot();
const isPlaying = snapshot.isPlaying;
const position = snapshot.position;
const tempo = snapshot.tempo;
```

---

### Pattern 6: Load Score

#### Before (TransportService)

```typescript
import transportService from '@/services/TransportService';

await transportService.loadScore(score, measureTimingInfo);
```

#### After (KhronosBus)

**Note:** Score loading is no longer handled by transport. Use dedicated score loading services:

```typescript
// Score loading is now separate from transport
// Use your score loading service instead
import { loadScore } from '@/services/ScoreLoadingService';

await loadScore(score, measureTimingInfo);
```

---

### Pattern 7: Loop Regions

#### Before (TransportService)

```typescript
import transportService from '@/services/TransportService';

transportService.setLoop(
  { measureIndex: 0, beatInMeasure: 0, ticks: 0 },
  { measureIndex: 4, beatInMeasure: 0, ticks: 0 }
);
transportService.toggleLoop();
```

#### After (KhronosBus Helper)

```typescript
import { khronosSetLoop, khronosClearLoop } from '@/khronos';

khronosSetLoop({
  start: { measureIndex: 0, beatInMeasure: 0, ticks: 0 },
  end: { measureIndex: 4, beatInMeasure: 0, ticks: 0 },
  enabled: true,
});

khronosClearLoop();
```

#### After (React Hook)

```typescript
import { useKhronosCommands } from '@/khronos';

function MyComponent() {
  const { setLoop, clearLoop } = useKhronosCommands();
  
  const handleSetLoop = () => {
    setLoop({
      start: { measureIndex: 0, beatInMeasure: 0, ticks: 0 },
      end: { measureIndex: 4, beatInMeasure: 0, ticks: 0 },
      enabled: true,
    });
  };
  
  return (
    <div>
      <button onClick={handleSetLoop}>Set Loop</button>
      <button onClick={clearLoop}>Clear Loop</button>
    </div>
  );
}
```

---

## File-by-File Migration

### Files That Need Migration (9 files)

1. `src/services/AudioLayerService.ts`
2. `src/services/TransportAdapter.ts`
3. `src/services/transportKernel/types.ts`
4. `src/store/advancedTransport.ts`
5. `src/services/transportKernel/TransportBridge.ts`
6. `src/services/transportKernel/UnifiedKernelPrototype.ts`
7. `src/services/transportKernel/TransportKernel.ts`
8. `src/services/TransportYouTubeSyncService.ts`
9. `src/components/theater8k/transport/transportControllerStore.ts`

---

## Step-by-Step Migration Process

### Step 1: Identify Usage

```bash
# Find all TransportService imports
grep -r "import.*TransportService" src/
grep -r "from.*TransportService" src/
```

### Step 2: Replace Imports

```typescript
// Before
import transportService from '@/services/TransportService';

// After
import { KhronosBus, useKhronosPosition, useKhronosCommands } from '@/khronos';
```

### Step 3: Replace API Calls

Follow the patterns above to replace:
- `transportService.subscribe()` → `KhronosBus.onTick()` or hooks
- `transportService.play()` → `khronosPlay()` or `useKhronosCommands().play`
- `transportService.getState()` → `useKhronosStore()` or `getKhronosSnapshot()`

### Step 4: Update Types

```typescript
// Before
import type { TransportState, TransportPosition } from '@/services/TransportService';

// After
import type { KhronosPosition, KhronosTick } from '@/khronos';
```

### Step 5: Test

- Verify position updates work
- Verify play/pause/stop work
- Verify seek works
- Verify tempo changes work
- Verify loop regions work

---

## Common Pitfalls

### Pitfall 1: Forgetting to Unsubscribe

```typescript
// ❌ Bad: Memory leak
useEffect(() => {
  KhronosBus.onTick((tick) => {
    // Handle tick
  });
}, []);

// ✅ Good: Proper cleanup
useEffect(() => {
  const unsubscribe = KhronosBus.onTick((tick) => {
    // Handle tick
  });
  return unsubscribe;
}, []);
```

### Pitfall 2: Using TransportService in New Code

```typescript
// ❌ Bad: Using legacy API in new code
import transportService from '@/services/TransportService';

// ✅ Good: Use KhronosBus directly
import { useKhronosCommands } from '@/khronos';
```

### Pitfall 3: Not Using Hooks in React

```typescript
// ❌ Bad: Manual subscription in React
const [position, setPosition] = useState(null);
useEffect(() => {
  const unsub = KhronosBus.onTick((tick) => setPosition(tick.position));
  return unsub;
}, []);

// ✅ Good: Use hooks
const { position } = useKhronosPosition();
```

---

## Migration Priority

### High Priority (Core Services)
1. `AudioLayerService.ts` - Core audio service
2. `TransportAdapter.ts` - Legacy bridge (can be removed after migration)
3. `transportControllerStore.ts` - Theater transport controls

### Medium Priority (Supporting Services)
4. `TransportBridge.ts` - Bridge service
5. `TransportKernel.ts` - Kernel service
6. `TransportYouTubeSyncService.ts` - YouTube sync

### Low Priority (Types/Prototypes)
7. `types.ts` - Type definitions
8. `UnifiedKernelPrototype.ts` - Prototype code
9. `advancedTransport.ts` - Advanced transport store

---

## Testing Checklist

After migration, verify:

- [ ] Position updates correctly during playback
- [ ] Play/pause/stop buttons work
- [ ] Seek works correctly
- [ ] Tempo changes work
- [ ] Loop regions work
- [ ] No memory leaks (check unsubscribe)
- [ ] No console errors
- [ ] Performance is acceptable

---

## Rollback Plan

If migration causes issues:

1. Revert to `TransportService` import
2. `TransportService` still works (it's a KhronosBus proxy)
3. Fix issues and re-migrate

---

**Last Updated:** 2025-11-30  
**Status:** Phase F Freeze → Phase G Migration








