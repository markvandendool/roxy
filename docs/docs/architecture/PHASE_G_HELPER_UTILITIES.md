# Phase G Helper Utilities
**Status:** Pre-Unfreeze Preparation  
**Last Updated:** 2025-11-30

---

## Overview

This document contains helper utilities and code snippets for Phase G unfreeze. These utilities can be used for debugging, testing, and migration.

---

## Debug Utilities

### KhronosBus Debug Helper

```typescript
// src/utils/debug/khronosDebug.ts
import { KhronosBus } from '@/khronos';

export function enableKhronosDebug() {
  if (typeof window === 'undefined') return;
  
  (window as any).__KHRONOS_DEBUG = true;
  (window as any).__KHRONOS_DEBUG_DRIFT = true;
  
  console.info('[KhronosDebug] Debug mode enabled');
}

export function getKhronosDebugInfo() {
  if (typeof window === 'undefined') return null;
  
  const bus = (window as any).__khronosBus;
  if (!bus) return null;
  
  return {
    telemetry: bus.getTelemetry(),
    subscriberCount: bus.getSubscriberCount('khronos:tick'),
    hasSubscribers: bus.hasSubscribers('khronos:tick'),
  };
}

export function logKhronosState() {
  const info = getKhronosDebugInfo();
  if (!info) {
    console.warn('[KhronosDebug] KhronosBus not available');
    return;
  }
  
  console.table({
    'Ticks Published': info.telemetry.ticksPublished,
    'Commands Published': info.telemetry.commandsPublished,
    'Subscriber Count': info.subscriberCount,
    'Jitter Max (ms)': info.telemetry.jitterMaxMs,
    'Drift Heat': info.telemetry.driftHeat.toFixed(2),
    'Integrity Score': info.telemetry.positionalIntegrityScore,
  });
}
```

---

## Migration Utilities

### TransportService to KhronosBus Converter

```typescript
// src/utils/migration/transportServiceConverter.ts
import { KhronosBus, useKhronosPosition, useKhronosCommands } from '@/khronos';
import type { TransportState } from '@/services/TransportService';

/**
 * Convert TransportService state to KhronosBus snapshot
 * For migration purposes only
 */
export function convertTransportStateToKhronos(state: TransportState) {
  return {
    position: state.currentPosition,
    absoluteTick: state.currentPosition.measureIndex * 960 * 4 + 
                   state.currentPosition.beatInMeasure * 960 + 
                   state.currentPosition.ticks,
    tempo: state.tempo,
    isPlaying: state.isPlaying,
    loop: state.isLooping ? {
      start: state.loopStart,
      end: state.loopEnd,
      enabled: true,
    } : {
      start: null,
      end: null,
      enabled: false,
    },
  };
}

/**
 * Hook to replace TransportService.subscribe()
 * Returns position and isPlaying
 */
export function useTransportState() {
  const { position, isPlaying } = useKhronosPosition();
  const tempo = useKhronosTempo();
  
  return {
    currentPosition: position,
    isPlaying,
    tempo,
  };
}
```

---

## Testing Utilities

### Mock KhronosBus for Testing

```typescript
// src/test-utils/mockKhronosBus.ts
import { KhronosBus } from '@/khronos';
import type { KhronosTick } from '@/khronos';

export class MockKhronosBus {
  private subscribers = new Map<string, Set<Function>>();
  private telemetry = {
    ticksPublished: 0,
    commandsPublished: 0,
    subscriberCount: 0,
    lastTickTimestamp: 0,
    validationErrors: 0,
    jitterSamples: 0,
    jitterMaxMs: 0,
  };
  
  onTick(handler: (tick: KhronosTick) => void) {
    if (!this.subscribers.has('khronos:tick')) {
      this.subscribers.set('khronos:tick', new Set());
    }
    this.subscribers.get('khronos:tick')!.add(handler);
    this.telemetry.subscriberCount++;
    
    return () => {
      this.subscribers.get('khronos:tick')?.delete(handler);
      this.telemetry.subscriberCount--;
    };
  }
  
  publishTick(tick: KhronosTick) {
    const handlers = this.subscribers.get('khronos:tick');
    if (handlers) {
      handlers.forEach(handler => handler(tick));
    }
    this.telemetry.ticksPublished++;
    this.telemetry.lastTickTimestamp = tick.timestamp;
  }
  
  getTelemetry() {
    return { ...this.telemetry };
  }
}
```

---

## Performance Monitoring

### KhronosBus Performance Monitor

```typescript
// src/utils/performance/khronosPerformanceMonitor.ts
import { KhronosBus } from '@/khronos';

export class KhronosPerformanceMonitor {
  private startTime = performance.now();
  private tickCount = 0;
  private jitterSamples: number[] = [];
  private lastTickTime = 0;
  
  start() {
    const unsubscribe = KhronosBus.onTick((tick) => {
      this.tickCount++;
      
      const now = performance.now();
      if (this.lastTickTime > 0) {
        const delta = now - this.lastTickTime;
        this.jitterSamples.push(delta);
        if (this.jitterSamples.length > 100) {
          this.jitterSamples.shift();
        }
      }
      this.lastTickTime = now;
    });
    
    return unsubscribe;
  }
  
  getStats() {
    const elapsed = performance.now() - this.startTime;
    const tickRate = (this.tickCount / elapsed) * 1000;
    
    const jitterMean = this.jitterSamples.reduce((a, b) => a + b, 0) / this.jitterSamples.length;
    const jitterMax = Math.max(...this.jitterSamples);
    const jitterMin = Math.min(...this.jitterSamples);
    
    return {
      tickRate: tickRate.toFixed(2),
      tickCount: this.tickCount,
      elapsed: elapsed.toFixed(2),
      jitterMean: jitterMean.toFixed(2),
      jitterMax: jitterMax.toFixed(2),
      jitterMin: jitterMin.toFixed(2),
    };
  }
  
  logStats() {
    const stats = this.getStats();
    console.table(stats);
  }
}
```

---

## Validation Utilities

### KhronosBus Validator

```typescript
// src/utils/validation/khronosValidator.ts
import { KhronosBus } from '@/khronos';
import type { KhronosTick } from '@/khronos';

export function validateKhronosBus() {
  const issues: string[] = [];
  
  // Check if bus is available
  if (typeof window === 'undefined') {
    issues.push('Window not available');
    return issues;
  }
  
  const bus = (window as any).__khronosBus;
  if (!bus) {
    issues.push('KhronosBus not available on window');
    return issues;
  }
  
  // Check subscriber count
  const subscriberCount = bus.getSubscriberCount('khronos:tick');
  if (subscriberCount === 0) {
    issues.push('No subscribers to khronos:tick');
  }
  
  // Check telemetry
  const telemetry = bus.getTelemetry();
  if (telemetry.jitterMaxMs > 50) {
    issues.push(`High jitter detected: ${telemetry.jitterMaxMs}ms`);
  }
  
  if (telemetry.positionalIntegrityScore < 80) {
    issues.push(`Low integrity score: ${telemetry.positionalIntegrityScore}`);
  }
  
  return issues;
}

export function validateTick(tick: KhronosTick) {
  const issues: string[] = [];
  
  if (tick.position.measureIndex < 0) {
    issues.push('Invalid measureIndex: must be >= 0');
  }
  
  if (tick.position.beatInMeasure < 0) {
    issues.push('Invalid beatInMeasure: must be >= 0');
  }
  
  if (tick.position.ticks < 0 || tick.position.ticks >= 960) {
    issues.push('Invalid ticks: must be 0-959');
  }
  
  if (tick.tempo < 20 || tick.tempo > 300) {
    issues.push('Invalid tempo: must be 20-300 BPM');
  }
  
  if (tick.absoluteTick < 0) {
    issues.push('Invalid absoluteTick: must be >= 0');
  }
  
  return issues;
}
```

---

## Migration Scripts

### Find TransportService Imports

```bash
#!/bin/bash
# scripts/find-transport-service-imports.sh

echo "Finding TransportService imports..."
grep -r "import.*TransportService" src/ | grep -v node_modules
grep -r "from.*TransportService" src/ | grep -v node_modules

echo ""
echo "Finding TransportService usage..."
grep -r "transportService\." src/ | grep -v node_modules
```

### Count Legacy References

```bash
#!/bin/bash
# scripts/count-legacy-references.sh

echo "TransportService imports:"
grep -r "import.*TransportService" src/ | wc -l

echo "UnifiedKernelEngine references:"
grep -r "UnifiedKernelEngine" src/ | wc -l

echo "Tone.Transport references:"
grep -r "Tone\.Transport" src/ | wc -l

echo "requestAnimationFrame usage:"
grep -r "requestAnimationFrame" src/ | wc -l
```

---

## Runtime Verification Helpers

### Quick Verification Script

```typescript
// src/utils/verification/quickVerify.ts
import { KhronosBus, getKhronosSnapshot, initializeKhronosEngine } from '@/khronos';

export async function quickVerify() {
  console.log('=== KhronosBus Quick Verification ===');
  
  // 1. Check initialization
  const engine = initializeKhronosEngine();
  if (!engine) {
    console.error('❌ KhronosEngine failed to initialize');
    return false;
  }
  console.log('✅ KhronosEngine initialized');
  
  // 2. Check AudioWorklet
  await engine.workletReady;
  console.log('✅ AudioWorklet loaded');
  
  // 3. Check subscribers
  const subscriberCount = KhronosBus.getSubscriberCount('khronos:tick');
  console.log(`✅ Subscribers: ${subscriberCount}`);
  
  // 4. Check telemetry
  const telemetry = KhronosBus.getTelemetry();
  console.log(`✅ Telemetry: ${telemetry.ticksPublished} ticks published`);
  
  // 5. Check snapshot
  const snapshot = getKhronosSnapshot();
  console.log(`✅ Snapshot: Position ${snapshot.position.measureIndex}:${snapshot.position.beatInMeasure}`);
  
  console.log('=== Verification Complete ===');
  return true;
}
```

---

## Usage Examples

### Enable Debug Mode

```typescript
import { enableKhronosDebug, logKhronosState } from '@/utils/debug/khronosDebug';

// Enable debug
enableKhronosDebug();

// Log state periodically
setInterval(() => {
  logKhronosState();
}, 5000);
```

### Monitor Performance

```typescript
import { KhronosPerformanceMonitor } from '@/utils/performance/khronosPerformanceMonitor';

const monitor = new KhronosPerformanceMonitor();
const unsubscribe = monitor.start();

// After 10 seconds
setTimeout(() => {
  monitor.logStats();
  unsubscribe();
}, 10000);
```

### Validate System

```typescript
import { validateKhronosBus } from '@/utils/validation/khronosValidator';

const issues = validateKhronosBus();
if (issues.length > 0) {
  console.warn('Validation issues:', issues);
} else {
  console.log('✅ All validations passed');
}
```

---

## Notes

- These utilities are for Phase G unfreeze and testing
- Some utilities may need to be created in actual files
- All utilities should be tested before use
- Remove debug utilities before production release

---

**Last Updated:** 2025-11-30  
**Status:** Pre-Unfreeze Preparation








