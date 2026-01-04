# Domain Boundary Protection: Score System Terminology Separation

**Date:** 2025-12-15  
**Status:** 📋 **DEFERRED** - Documented for v3.1+ implementation  
**Priority:** Medium (architectural clarity, not blocking)  
**Source:** Master Chief architectural insight

---

## 🚨 THE CORE ISSUE: TWO SEPARATE DOMAINS

### Domain 1: Musical System (MOS 2030)
```
KHRONOS (timing engine - musical beats/tempo)
  ↓
Event Spine (musical events timeline)
  ↓
NVX1Score (musical notation/composition)
  ↓
Musical playback/rendering
```

**Purpose:** Make music, render notation, synchronize audio/video  
**Data:** Notes, chords, tempo, time signatures, tracks  
**Timing:** Musical time (beats, bars, tempo)

---

### Domain 2: Orchestrator System (Agent Development)
```
Task Scheduler (orchestrator timing - wall-clock UTC)
  ↓
Progress Tracking (master-progress.json)
  ↓
Story/Sprint Execution
  ↓
Agent work coordination
```

**Purpose:** Build software, track development progress, coordinate agents  
**Data:** Epics, sprints, stories, completion status  
**Timing:** Wall-clock time (UTC timestamps, duration)

---

## ⚠️ THE DANGER: NAMESPACE COLLISION

**Current Collision Points:**

1. **"Score" terminology:**
   - Musical domain: "score" = sheet music (NVX1Score)
   - Orchestrator domain: "score" = progress tracking (master-progress.json, ScoreLoader)

2. **Timing systems:**
   - Musical domain: KHRONOS (beat-based, tempo-relative)
   - Orchestrator domain: Task scheduler (wall-clock, UTC-based)

3. **Event systems:**
   - Musical domain: Event Spine (musical events)
   - Orchestrator domain: Task queue (development events)

**If we conflate these, we risk:**
- ❌ Musical timing logic bleeding into orchestrator scheduling
- ❌ Orchestrator progress data mixing with musical composition data
- ❌ Agent confusion about which "score" or "event" system to use
- ❌ Architecture corruption at fundamental level

---

## ✅ PROPOSED SOLUTION: CLEAR NAMING CONVENTIONS

### Option A: Rename Orchestrator "Score" (RECOMMENDED)

**Musical Domain (unchanged):**
- ✅ `NVX1Score` - Musical composition
- ✅ `Event Spine` - Musical event timeline
- ✅ `KHRONOS` - Musical timing engine

**Orchestrator Domain (renamed):**
- ✅ `MasterProgress` (instead of "score")
- ✅ `ProgressLoader` (instead of ScoreLoader)
- ✅ `ProgressTracker` (instead of ScoreTracker)
- ✅ `master-progress.json` (already correct)

**Result:** Zero terminology overlap

---

### Option B: Use Prefix/Suffix Consistently

**Musical Domain:**
- ✅ `MusicalScore` or `NVX1Score`
- ✅ `MusicalEventSpine`
- ✅ `MusicalKHRONOS` or just `KHRONOS`

**Orchestrator Domain:**
- ✅ `DevScore` or `ProjectScore`
- ✅ `DevEventSpine` or `TaskEventSpine`
- ✅ `DevScheduler` (NOT "KHRONOS")

**Result:** Clear domain prefix on everything

---

### Option C: "Skore" Variant

**Musical Domain:**
- ✅ `Score` - Musical score (traditional spelling)
- ✅ `Event Spine` - Musical events
- ✅ `KHRONOS` - Musical timing

**Orchestrator Domain:**
- ✅ `Skore` - Development progress (variant spelling)
- ✅ `SkoreLoader`, `SkoreTracker`
- ✅ Task Scheduler (NOT "KHRONOS")

**Result:** Phonetically similar but visually distinct

---

## 🎯 RECOMMENDATION: Option A + Strict Separation

### Musical Domain (Untouched)
```typescript
// musical-score.ts
export class NVX1Score {
  // Musical composition data
}

// khronos.ts
export class KHRONOS {
  // Musical timing engine
  // Operates in beats/bars/tempo
}

// event-spine.ts
export class EventSpine {
  // Musical event timeline
}
```

### Orchestrator Domain (Renamed)
```typescript
// master-progress.ts (renamed from score-loader.ts)
export class MasterProgress {
  // Development progress tracking
  // NOT related to musical scores
}

// progress-loader.ts (renamed from score-loader.ts)
export class ProgressLoader {
  // Loads master-progress.json
  // NOT ScoreLoader (musical)
}

// task-scheduler.ts
export class TaskScheduler {
  // Orchestrator timing (wall-clock)
  // NOT KHRONOS (musical timing)
}
```

---

## 🔒 STRICT BOUNDARY ENFORCEMENT

### Rule 1: KHRONOS is ONLY for Musical System
```typescript
// ✅ CORRECT - Musical domain
import { KHRONOS } from '@/musical-system/khronos';
const musicTimer = new KHRONOS();
musicTimer.setTempo(120); // Musical tempo

// ❌ WRONG - Orchestrator domain
import { KHRONOS } from '@/musical-system/khronos';
const taskTimer = new KHRONOS(); // NO! Use TaskScheduler
```

### Rule 2: Event Spine is ONLY for Musical Events
```typescript
// ✅ CORRECT - Musical domain
import { EventSpine } from '@/musical-system/event-spine';
const musicalEvents = new EventSpine();
musicalEvents.addNote({ pitch: 'C4', duration: 0.5 });

// ❌ WRONG - Orchestrator domain
import { EventSpine } from '@/musical-system/event-spine';
const taskEvents = new EventSpine(); // NO! Use TaskQueue
```

### Rule 3: "Score" is ONLY for Musical Notation
```typescript
// ✅ CORRECT - Musical domain
import { NVX1Score } from '@/musical-system/score';
const composition = new NVX1Score();

// ❌ WRONG - Orchestrator domain
import { Score } from '@/orchestrator/score'; // NO! Use MasterProgress
```

---

## 📋 MIGRATION PLAN (If We Rename)

### Phase 1: Add Aliases (Non-Breaking)
```typescript
// master-progress.ts
export class MasterProgress { /* ... */ }
export const ScoreLoader = MasterProgress; // Alias for compatibility
```

### Phase 2: Update Documentation
- Mark `ScoreLoader` as deprecated
- Document that "Score" is musical-only
- Add architecture diagram showing separation

### Phase 3: Gradual Migration
- New code uses `MasterProgress`
- Old code keeps working with alias
- Migrate gradually over v3.1-v3.5

### Phase 4: Remove Aliases (v4.0)
- Delete `ScoreLoader` alias
- Enforce strict naming

---

## 🎯 ANSWER TO KEY QUESTION

> "we can use khronos for both i just want to be sure we are not conflating and breaking a barrier that we should not break"

**Strong Recommendation: NO - Keep KHRONOS Musical-Only**

**Why:**

1. **KHRONOS operates in musical time** (beats, bars, tempo)
   - Not wall-clock time (UTC timestamps)
   - Different timing semantics entirely

2. **Orchestrator needs wall-clock timing**
   - Tasks execute in real time
   - Deadlines are calendar-based
   - Different requirements than musical timing

3. **Architectural purity matters**
   - Musical system should not depend on orchestrator
   - Orchestrator should not depend on musical system
   - Clean separation enables independent evolution

**Better Approach:**
- ✅ KHRONOS = Musical timing engine (beats/tempo)
- ✅ TaskScheduler = Orchestrator timing (wall-clock)
- ✅ Clear separation, zero confusion

---

## 🚀 IMPLEMENTATION TIMELINE

### For v3.0 Ship (Today)
**Do nothing** - Don't rename anything yet. Ship v3.0 as-is.

### For v3.1 (Post-Ship)
**Document the separation:**
- Add architecture diagram
- Update onboarding docs
- Add code comments explaining distinction
- Create this document (done)

### For v4.0 (Future)
**Consider renaming:**
- `ScoreLoader` → `MasterProgressLoader`
- `ScoreTracker` → `ProgressTracker`
- Enforce strict domain separation in code reviews

---

## ✅ CONCLUSION

**This boundary protection is critical architectural hygiene.**

**The collision is real:**
- "Score" means two different things
- Timing systems serve different purposes
- Event systems track different domains

**Recommendation:**
1. **Short term:** Document the separation clearly (this document)
2. **Medium term:** Rename orchestrator "score" to "progress" (v3.1+)
3. **Long term:** Enforce strict domain boundaries in code (v4.0)

**DO NOT:**
- Use KHRONOS for orchestrator timing
- Mix Event Spine (musical) with Task Queue (orchestrator)
- Let "score" terminology blur the domains

**This is good architectural hygiene. Thank you for raising it.**

---

**Status:** 📋 **DEFERRED TO v3.1+**  
**Priority:** Medium (architectural clarity, not blocking)  
**Reference:** Master Chief architectural insight, 2025-12-15
