# Planning & Execution Model

**Status:** ✅ **CANONICAL**  
**Last Updated:** 2025-12-13  
**Purpose:** Define the mapping between human-facing lexicon and internal execution model

---

## Overview

The MindSong planning and execution system uses **two lexicons** for the same underlying structure:

1. **Human-facing lexicon** (what users see in `/progress` UI)
2. **Internal execution model** (what orchestrator executes, what JSON stores)

This document defines the canonical mapping between these lexicons.

---

## Canonical Mapping Table

| Human Term | Internal Term | Executed? | Purpose |
|------------|---------------|-----------|---------|
| **Ticket** | **Epic** | ❌ | Strategic goal, planning unit |
| **Sprint** | **Sprint** | ❌ | Timebox, groups work |
| **Task** | **Story** | ✅ | Atomic execution unit, agent contract |
| **Milestone** | **Milestone** | ❌ | Timeline marker, reporting artifact |

---

## Why Aliasing Exists

### Hard Constraint: Orchestrator Contracts

The orchestrator and all execution systems assume **Story is the atomic execution unit**:

- Orchestrator dispatches `storyId` to agents
- Agents report `currentStory` in telemetry
- Podium visualizes story lifecycle
- ARES validates at story granularity
- Governance locks stories

**Renaming Story → Task internally would break:**
- Orchestrator contracts
- Telemetry systems
- Historical data
- Agent execution pipeline

### Human Mental Model

Humans naturally think in:
- **Tickets** (why are we doing this?)
- **Sprints** (when?)
- **Tasks** (what am I doing?)

The UI uses human-friendly terms while the execution layer uses execution-focused terms.

---

## Entity Definitions

### Epic (Internal) / Ticket (Human)

**Purpose:** Strategic goal, planning container  
**ID Format:** `LUNO-{NUM}`  
**Status Values:** `pending`, `in_progress`, `done`, `blocked`  
**Executed By:** N/A (planning only)

Epics are strategic containers that group related work. They are not executed directly by agents.

**Example:**
```json
{
  "id": "LUNO-026",
  "name": "LUNO Orchestrator Bootstrap",
  "status": "in_progress"
}
```

### Sprint

**Purpose:** Timebox, groups stories  
**ID Format:** `LUNO-{EPIC}-S{NUM}`  
**Status Values:** `pending`, `in_progress`, `done`, `blocked`  
**Executed By:** N/A (planning only)

Sprints are timeboxes that group stories for execution. They provide temporal organization but are not executed directly.

**Example:**
```json
{
  "id": "LUNO-026-S7",
  "name": "CLI & Observability",
  "status": "in_progress",
  "epicId": "LUNO-026"
}
```

### Story (Internal) / Task (Human)

**Purpose:** Atomic execution unit, agent contract  
**ID Format:** `LUNO-{EPIC}-STORY-{NUM}`  
**Status Values:** `todo`, `in_progress`, `done`, `blocked`  
**Executed By:** ✅ **Orchestrator**

Stories are the atomic unit of execution. Agents receive stories, execute them, and report completion. The UI displays these as "Tasks" for human clarity.

**Example:**
```json
{
  "id": "LUNO-026-STORY-033",
  "title": "Wire Podium telemetry",
  "status": "todo",
  "sprintId": "LUNO-026-S7",
  "epicId": "LUNO-026"
}
```

**Critical:** Stories are the **only** execution unit. Tasks (UI) = Stories (JSON/Orchestrator).

### Milestone

**Purpose:** Timeline marker, reporting artifact  
**ID Format:** `{EPIC}-MS-{NAME}`  
**Status Values:** N/A (non-executable)  
**Executed By:** ❌ **Never executed**

Milestones are reporting artifacts that mark significant points in an epic's timeline. They are:
- Visible in `/progress` timeline
- Never executed by agents
- Never appear in Podium
- Used for progress reporting only

**Example:**
```json
{
  "id": "LUNO-026-MS-S7-COMPLETE",
  "name": "Sprint 7 Complete",
  "epicId": "LUNO-026",
  "targetDate": "2025-12-20"
}
```

---

## Data Flow

### UI → JSON Transformation

The `ProgressService` transforms internal JSON structure to UI-friendly format:

```typescript
// Internal JSON structure
epic.stories[] → tasks[] (for UI consumption)
```

**Key Point:** The UI "Tasks" are actually JSON "Stories". This transformation is explicit and documented.

### Execution Flow

```
1. Human creates "Task" in UI
   ↓
2. System stores as "Story" in master-progress.json
   ↓
3. Orchestrator finds Story with status="todo"
   ↓
4. Orchestrator dispatches Story to agent
   ↓
5. Agent executes Story
   ↓
6. Agent reports Story completion
   ↓
7. UI displays Story as "Task" (completed)
```

---

## Progress Ref Mapping

When using `buildProgressRef()` utility:

- `kind: 'epic'` = Ticket (human term)
- `kind: 'task'` = Story (execution unit)
- `kind: 'sprint'` = Sprint (same in both)
- `kind: 'milestone'` = Milestone (reporting only)

---

## Schema Rules

### Stories (Execution Unit)

**Required Fields:**
- `id` (string, format: `LUNO-{EPIC}-STORY-{NUM}`)
- `title` (string)
- `status` (enum: `todo`, `in_progress`, `done`, `blocked`)
- `sprintId` (string, references Sprint)
- `epicId` (string, references Epic)

**Deprecated Fields (DO NOT USE):**
- `type: "task"` - Redundant (stories are always stories)
- `tasks[]` - Vestigial (nested tasks not used)

**Validation:**
- Stories must NOT have `type: "task"` field
- Stories must NOT have `tasks[]` array
- Stories are the only execution unit

### Milestones

**Rules:**
- Milestones are optional
- Milestones are non-executable
- Milestones should never block agent execution
- Milestones are reporting artifacts only

---

## Common Questions

### Q: Why not rename Story → Task internally?

**A:** This would break orchestrator contracts, telemetry, and historical data. The alias layer is safer and maintains backward compatibility.

### Q: Can I create a Task without a Story?

**A:** No. Tasks (UI) are always Stories (JSON). Creating a "Task" in the UI creates a Story in JSON.

### Q: What about nested tasks in stories?

**A:** The `story.tasks[]` field is vestigial and unused. Stories are atomic - they don't contain nested tasks.

### Q: Are Milestones executed?

**A:** No. Milestones are reporting artifacts only. They mark timeline points but are never executed by agents.

---

## Related Documentation

- **LUNO Ticket Schema:** `docs/luno/LUNO_TICKET_SCHEMA.md`
- **LUNO Agent Rules:** `docs/luno/LUNO_AGENT_OPERATING_RULES.md`
- **Progress Service:** `src/services/ProgressService.ts`
- **Orchestrator:** `luno-orchestrator/src/orchestrator/`

---

## Summary

**Canonical Internal Model (Agents + JSON):**
```
Epic → Sprint → Story (execution unit)
```

**Canonical Human-Facing Model (UI):**
```
Ticket → Sprint → Task
```

**Mapping:**
- Ticket = Epic (alias)
- Task = Story (alias)
- Milestone = Timeline marker (non-executable)

No structural fork. No duplication. No runtime breakage.

---

**Status:** ✅ **CANONICAL**  
**Enforcement:** All agents must understand this mapping  
**Last Updated:** 2025-12-13






















