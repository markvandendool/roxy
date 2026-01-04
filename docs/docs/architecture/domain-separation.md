# Domain Separation: Musical vs Orchestrator Systems

## CRITICAL: These domains MUST remain separate

### Musical System (MOS 2030)
**Purpose:** Music composition, notation, playback  
**Timing:** Musical time (beats, bars, tempo)  
**Key Components:**
- KHRONOS: Musical timing engine
- Event Spine: Musical event timeline
- NVX1Score: Musical composition/notation

### Orchestrator System  
**Purpose:** Software development, agent coordination  
**Timing:** Wall-clock time (UTC, milliseconds)  
**Key Components:**
- TaskScheduler: Development task timing
- Task Queue: Development events
- MasterProgress: Development progress tracking

## STRICT RULES

### Rule 1: KHRONOS is Musical-Only
```typescript
// ✅ CORRECT
import { KHRONOS } from '@/musical-system/khronos';

// ❌ WRONG - Use TaskScheduler
import { KHRONOS } from '@/orchestrator/...'; 
```

### Rule 2: Event Spine is Musical-Only
```typescript
// ✅ CORRECT
import { EventSpine } from '@/musical-system/event-spine';

// ❌ WRONG - Use Task Queue
import { EventSpine } from '@/orchestrator/...';
```

### Rule 3: "Score" is Musical-Only
```typescript
// ✅ CORRECT - Musical
import { NVX1Score } from '@/musical-system/score';

// ❌ WRONG - Use MasterProgress
import { Score } from '@/orchestrator/score';
```

## Enforcement
Any PR that violates these rules will be REJECTED.
Code reviews must verify domain separation.

**This is architectural law. Do not break it.**
