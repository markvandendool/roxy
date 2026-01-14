# Cursor Plan → Swarm Ticket Contract

**Status:** CANONICAL  
**Last Updated:** 2025-12-16  
**Purpose:** Define how to translate Cursor Plan Mode documents into swarm-executable ticket JSON

---

## 🔒 **CORE RULE**

> **Cursor "Plan Mode" documents are NOT executable.**
>
> All swarm work MUST be represented as a **swarm ticket JSON** that conforms to this contract.

**No exceptions.**

---

## 📋 **FIELD MAPPING (Plan → Ticket)**

| Cursor Plan Section | Swarm Ticket Field | Rules |
|---------------------|-------------------|-------|
| Epic / Story ID | `id` | Format: `EPIC-NAME-###-STORY-###` |
| Title / Summary | `title` | Clear, actionable, ≤80 chars |
| Problem / Intent | `description` | Why this work matters, what it achieves |
| Scope / Files | `filesInScope` | **Explicit paths only, no globs** |
| Dependencies | `dependencies` | Real story IDs or empty array |
| Definition of Done | `acceptanceCriteria` | Bullet list, testable conditions |
| Effort / Size | `storyPoints` | 1-5 for free-tier, 6-13 for paid-tier |
| Risk / Priority | `priority` | `low`, `medium`, `high`, `critical` |
| Execution tier | `queue` | `free-tier` (≤5 pts), `paid-tier` (>5 pts), `special` |
| Plan timestamp | `requestedAt` | ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ) |

---

## 📐 **CANONICAL JSON SHAPE**

**Copy this. Modify fields. Enqueue.**

```json
{
  "id": "TEST-EPIC-001-STORY-001",
  "title": "Perfect test epic – inconsequential but critical",
  "description": "Derived from Cursor Plan Mode document dated YYYY-MM-DD. No architectural impact.",
  "storyPoints": 3,
  "priority": "medium",
  "queue": "free-tier",
  "dependencies": [],
  "filesInScope": [
    "docs/example/TEST_EPIC_README.md"
  ],
  "acceptanceCriteria": [
    "Change is limited strictly to filesInScope",
    "No regressions introduced",
    "Diff matches plan exactly",
    "Execution completes without retries"
  ],
  "requestedAt": "2025-12-17T00:00:00Z"
}
```

---

## ✅ **"PROPERLY ADDED" CHECKLIST**

A ticket is **NOT properly added** until ALL boxes are checked:

- [ ] **Plan Mode doc exists** (source of truth)
- [ ] **JSON created from plan** (not copied verbatim)
- [ ] **`filesInScope` explicit and minimal** (no wildcards, no "all files in X")
- [ ] **`dependencies` empty or real** (no TODOs, no "TBD")
- [ ] **`storyPoints` ≤ queue budget** (free-tier: 1-5, paid-tier: 6-13)
- [ ] **`queue` set correctly** (matches storyPoints)
- [ ] **Ticket enqueued via approved mechanism** (see below)
- [ ] **No direct execution from Plan Mode** (plan is not code)

**If any box fails → ticket is NOT added.**

---

## 🎮 **HOW TO ENQUEUE (Phase 5 Control Surface)**

### **Option 1: CLI (Recommended)**

```bash
cd luno-orchestrator
bun run src/cli/luno.ts enqueue --story=YOUR-STORY-ID --queue=free-tier
```

### **Option 2: Add to master-progress.json (Advanced)**

**Not recommended unless you understand the schema.**

If you must:
1. Read `luno-orchestrator/master-progress.json`
2. Find the appropriate epic
3. Add story to `stories` array
4. Validate against schema (`luno-orchestrator/src/score/master-progress.schema.ts`)
5. Commit changes

**Prefer Option 1.**

---

## 📖 **EXAMPLE: REAL TRANSLATION**

### **Cursor Plan Mode Document (Input)**

```markdown
# Rocky Brain Map Integration

## Epic
ROCKY-BRAIN-MAP-001

## Summary
Integrate Rocky's knowledge graph visualization into Architecture Map

## Problem
Rocky has a separate brain map visualization that should be unified with the main architecture map component.

## Scope
- src/components/ArchitectureMap/panels/RockyBrainMap.tsx (existing)
- src/components/ArchitectureMap/ArchitectureMapApp.tsx (modify)
- docs/rocky/BRAIN_MAP_INTEGRATION.md (new)

## Dependencies
None (standalone feature)

## Effort
3 story points (low complexity, isolated scope)

## Definition of Done
- RockyBrainMap panel accessible from Architecture Map
- No regressions in existing Architecture Map
- Documentation complete
- Integration tested
```

### **Swarm Ticket JSON (Output)**

```json
{
  "id": "ROCKY-BRAIN-MAP-001-STORY-001",
  "title": "Integrate Rocky Brain Map into Architecture Map",
  "description": "Rocky's knowledge graph visualization (RockyBrainMap.tsx) currently exists as a standalone component. This story integrates it as a panel in the main Architecture Map for unified navigation. Derived from Cursor Plan Mode document dated 2025-12-16. No architectural impact, isolated scope, zero risk.",
  "storyPoints": 3,
  "priority": "medium",
  "queue": "free-tier",
  "dependencies": [],
  "filesInScope": [
    "src/components/ArchitectureMap/panels/RockyBrainMap.tsx",
    "src/components/ArchitectureMap/ArchitectureMapApp.tsx",
    "docs/rocky/BRAIN_MAP_INTEGRATION.md"
  ],
  "acceptanceCriteria": [
    "RockyBrainMap panel accessible from Architecture Map navigation",
    "No regressions in existing Architecture Map panels",
    "Documentation added to docs/rocky/BRAIN_MAP_INTEGRATION.md",
    "Change is limited strictly to filesInScope",
    "Execution completes without retries"
  ],
  "requestedAt": "2025-12-16T12:00:00Z"
}
```

### **Enqueue Command**

```bash
cd luno-orchestrator
bun run src/cli/luno.ts enqueue --story=ROCKY-BRAIN-MAP-001-STORY-001 --queue=free-tier
```

---

## 🧠 **ONE SENTENCE (USE EVERYWHERE)**

> **"Add the ticket properly" means:**
>
> *Translate the Cursor Plan Mode document into a swarm ticket JSON using the Cursor Plan → Swarm Ticket Contract, then enqueue it via the orchestrator control surface.*

**Memorize this. Enforce this. Repeat this.**

---

## 🚫 **ANTI-PATTERNS (FORBIDDEN)**

### ❌ **DO NOT:**

1. **Execute directly from Plan Mode**
   - Plan Mode is for humans, not swarms
   - Plans are ideas, tickets are contracts

2. **Copy-paste plan verbatim into JSON**
   - Translation requires judgment (e.g., expanding "Scope" into explicit file paths)

3. **Use wildcards in `filesInScope`**
   - ❌ `"src/components/**/*.tsx"`
   - ✅ `"src/components/ArchitectureMap/ArchitectureMapApp.tsx"`

4. **Add tickets without enqueuing**
   - Adding to `master-progress.json` without enqueuing = invisible to workers

5. **Bypass the control surface**
   - Direct queue writes are forbidden (use `luno enqueue`)

6. **Guess story points**
   - If unsure, estimate low and let ExecutionGate catch overruns

---

## 📊 **VALIDATION CHECKLIST (BEFORE ENQUEUE)**

Run through this **every time**:

| Check | Question | Pass? |
|-------|----------|-------|
| 1 | Does `filesInScope` contain ONLY explicit paths? | [ ] |
| 2 | Is `dependencies` empty or real story IDs? | [ ] |
| 3 | Does `storyPoints` match `queue` budget? | [ ] |
| 4 | Are `acceptanceCriteria` testable and specific? | [ ] |
| 5 | Is `requestedAt` in ISO 8601 format? | [ ] |
| 6 | Does `title` clearly state the work? | [ ] |
| 7 | Does `description` explain WHY this matters? | [ ] |

**All boxes must be checked before enqueue.**

---

## 🎯 **WORKFLOW SUMMARY**

```
1. Create Cursor Plan Mode document
   ↓
2. Extract fields using mapping table
   ↓
3. Construct JSON using canonical shape
   ↓
4. Validate using checklist
   ↓
5. Enqueue via control surface (luno enqueue)
   ↓
6. Worker picks up and executes
```

**Every ticket follows this path. No shortcuts.**

---

## 📐 **SCHEMA REFERENCE**

For advanced users, the authoritative schema is:

```
luno-orchestrator/src/score/master-progress.schema.ts
```

**But you should not need to read it.** This contract is the human-facing interface.

---

## 🔗 **RELATED DOCUMENTATION**

- **Control Surface:** `luno-orchestrator/docs/CONTROL_SURFACE_GUIDE.md`
- **Orchestrator Skills:** `luno-orchestrator/skills/luno-orchestrator-bible/skill.md`
- **Main Onboarding:** `docs/onboarding/ONBOARDING_START_HERE.md`
- **Agent Checklist:** `docs/AGENT_FIRST_MESSAGE_CHECKLIST.md`

---

## 🫡 **FINAL TRUTH**

**Plans are ideas.**  
**Tickets are contracts.**  
**Execution requires contracts, not ideas.**

This document is the bridge between the two.

---

**Last Updated:** 2025-12-16  
**Status:** CANONICAL  
**Enforcement:** Mandatory for all swarm work

