# Quantum Rails: DERIVE Layer Doctrine

> **Status:** CONSTITUTIONAL LAW
> **Scope:** SKOREQ Execution System
> **Enforcement:** Machine + Review
> **Version:** 1.0.0
> **Created:** 2025-12-20

---

## Executive Summary

SKOREQ implements **Quantum Rails** architecture: a three-layer system where truth flows in one direction, derivation is law, and UI is powerless.

```
NOW (facts) → DERIVE (law) → RENDER (opinion)
```

This document defines the invariants that make corruption impossible.

---

## The Three Layers

### 1. NOW Layer — Authoritative Facts

**Location:** `luno-orchestrator/src/telemetry/telemetry-bus.ts`

| Property | Description |
|----------|-------------|
| **Content** | Telemetry events, disk-persisted records |
| **Authority** | Sole source of execution truth |
| **Mutability** | Append-only, immutable after emission |
| **Access** | Worker writes, DERIVE reads |

**What NOW contains:**
- `ExecutionTelemetry` events (queued, started, completed, failed)
- `TelemetryRecord` aggregates (per-execution history)
- Timestamps, durations, commit hashes, errors

**What NOW does NOT contain:**
- Interpretations
- Progress calculations
- Status classifications
- UI state

### 2. DERIVE Layer — Pure Law

**Location:** `luno-orchestrator/src/telemetry/derive.ts`

| Property | Description |
|----------|-------------|
| **Content** | Pure functions over NOW data |
| **Authority** | Sole interpreter of meaning |
| **Mutability** | Stateless, no side effects |
| **Access** | RENDER consumes, tests verify |

**What DERIVE provides:**
- `deriveExecutionState()` — What state is this execution in?
- `deriveExecutionDurationMs()` — How long did it take?
- `deriveProgress()` — What percentage is complete?
- `deriveFailureRate()` — What's the failure rate?
- `deriveAnomalies()` — What's wrong?

**What DERIVE does NOT do:**
- Read from disk
- Access clocks
- Mutate state
- Depend on UI
- Make network calls

### 3. RENDER Layer — Disposable Opinion

**Location:** Future `luno-orchestrator/src/ui/` (RUNTIME-007)

| Property | Description |
|----------|-------------|
| **Content** | Visual representations of DERIVE output |
| **Authority** | None — read-only consumer |
| **Mutability** | Can change freely without affecting truth |
| **Access** | May ONLY import from DERIVE |

**What RENDER may do:**
- Display DERIVE outputs
- Format for human consumption
- Apply visual styling
- Animate state changes

**What RENDER may NOT do:**
- Import from `telemetry-bus.ts` directly
- Compute status or progress
- Infer meaning from raw events
- Trigger execution
- Mutate any state

---

## Non-Negotiable Invariants

### Invariant 1: Unidirectional Truth Flow

```
NOW → DERIVE → RENDER
 ↓       ↓        ↓
facts   law    opinion
```

Truth flows in ONE direction. No backchannel. No exceptions.

### Invariant 2: DERIVE Functions Are Pure

Every function in `derive.ts` must satisfy:

```typescript
// Given the same input, always produce the same output
derive(events) === derive(events)  // Always true

// Never mutate input
const before = JSON.stringify(events);
derive(events);
const after = JSON.stringify(events);
assert(before === after);

// Work on cloned data (replay-safe)
derive(events) === derive(JSON.parse(JSON.stringify(events)))
```

### Invariant 3: UI Cannot Derive Meaning

```typescript
// ❌ FORBIDDEN - UI computing status
const status = events.at(-1)?.status ?? 'unknown';

// ✅ REQUIRED - UI consuming DERIVE
const status = deriveExecutionState(events);
```

### Invariant 4: No Ad-Hoc Interpretation

If a component needs to know "what this means", the interpretation MUST:
1. Be implemented in `derive.ts`
2. Have unit tests
3. Be imported by name

No inline logic. No utility functions. No "just this once."

### Invariant 5: Telemetry Is Append-Only

Once emitted, telemetry events are immutable:

```typescript
// ❌ FORBIDDEN
record.events[0].status = 'completed';

// ❌ FORBIDDEN
telemetryBus.updateEvent(id, newData);

// ✅ CORRECT - Emit new event
telemetryBus.emitTelemetry('execution:completed', newEvent);
```

---

## UI Contract (RUNTIME-007 Constraints)

When RUNTIME-007 is implemented, it MUST obey:

### Import Rules

```typescript
// ✅ ALLOWED
import { deriveProgress, deriveExecutionState } from '../telemetry/derive';

// ❌ FORBIDDEN
import { telemetryBus } from '../telemetry/telemetry-bus';

// ❌ FORBIDDEN
import type { ExecutionTelemetry } from '../telemetry/execution-telemetry';
// (UI should not know about raw event shapes)
```

### Prop Traceability

Every UI prop must trace to a DERIVE function:

```typescript
// ✅ CORRECT - Props come from DERIVE
interface ExecutionCardProps {
  state: ReturnType<typeof deriveExecutionState>;
  duration: ReturnType<typeof deriveExecutionDurationMs>;
  outcome: ReturnType<typeof deriveExecutionOutcome>;
}

// ❌ FORBIDDEN - Props computed inline
interface ExecutionCardProps {
  events: ExecutionTelemetry[];  // Raw events leaked to UI
}
```

### No UI State for Truth

```typescript
// ❌ FORBIDDEN - UI owning truth
const [executionStatus, setExecutionStatus] = useState('running');

// ✅ CORRECT - UI reflecting DERIVE
const records = useRecords();  // From a hook that wraps DERIVE
const progress = deriveProgress(records);
```

---

## Why This Architecture

### What Jira Did Wrong

```
UI → State → Side effects → Logs (maybe)
```

Result:
- Status becomes political
- Progress is invented
- Failures are hidden
- Truth is negotiable

### What SKOREQ Does Right

```
Execution → Telemetry → Derivation → UI
```

Result:
- Status is computed from facts
- Progress is proven, not claimed
- Failures are visible
- Truth is mathematical

---

## Enforcement

### Machine Enforcement

1. **ESLint rule** (future): Forbid direct telemetry-bus imports in UI
2. **Type guards**: DERIVE outputs are branded types
3. **Test coverage**: 45+ tests verify DERIVE purity

### Review Enforcement

Any PR touching RENDER layer must verify:
- [ ] All props trace to DERIVE functions
- [ ] No raw telemetry imports
- [ ] No inline status computation
- [ ] No state management for truth

---

## Reference Implementation

### NOW (Complete)

```
luno-orchestrator/src/telemetry/
├── execution-telemetry.ts   # Type definitions
├── telemetry-bus.ts         # Event emission + persistence
├── derive.ts                # DERIVE layer
└── index.ts                 # Public exports
```

### DERIVE Functions (Complete)

| Function | Purpose |
|----------|---------|
| `deriveExecutionState` | Final state of execution |
| `deriveExecutionDurationMs` | Elapsed time |
| `deriveExecutionOutcome` | Success/failure + commit hash |
| `deriveExecutionFailure` | Error details |
| `deriveExecutionTimeline` | State transition history |
| `deriveIsTerminal` | Is execution finished? |
| `deriveStoryId` | Extract story ID |
| `deriveEpicId` | Extract epic ID |
| `groupRecordsByStatus` | Group by final status |
| `groupRecordsByEpic` | Group by epic |
| `deriveProgress` | Completion statistics |
| `deriveEpicProgress` | Per-epic progress |
| `deriveMeanDurationMs` | Average execution time |
| `deriveFailureRate` | Failure percentage |
| `deriveThroughput` | Executions per hour |
| `deriveAnomalies` | System health diagnostics |

### RENDER (Frozen)

RUNTIME-007 is frozen until:
1. This doctrine is reviewed
2. UI contract is signed off
3. Competitive research completes

---

## One-Sentence Summary

> **SKOREQ is a Quantum Rails system: execution is the rail, telemetry is time, derivation is law, and UI is optional.**

---

## Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2025-12-20 | Initial doctrine |
