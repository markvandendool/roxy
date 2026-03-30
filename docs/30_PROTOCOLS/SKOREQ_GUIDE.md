# SKOREQ System Guide

**Last Updated:** 2026-03-20 | **Status:** Active

SKOREQ (Story Queue) is ROXY's work prioritization system. It manages epics, stories, and execution order.

---

## Overview

SKOREQ provides:
- **Prioritized backlog** - Stories ranked by importance
- **Scope control** - Files explicitly listed per story
- **Acceptance criteria** - Clear definition of done
- **Progress tracking** - Status across epics

---

## Directory Structure

```
~/.roxy/skoreq/
└── {EPIC-ID}/
    ├── 00_MANIFEST.json      # Epic metadata
    ├── 01_STORIES.json       # Story definitions (optional)
    └── 04_FINAL_PROPOSAL.json # Approved proposal (primary)
```

### Location

```
~/.roxy/skoreq/
```

---

## Epic Format

### 04_FINAL_PROPOSAL.json (Primary File)

This is the authoritative source for an epic:

```json
{
  "epic": {
    "id": "ROXY-CHAT-EXTRACTION-V1",
    "title": "Extract Gold from Claude/Codex Chat Logs",
    "description": "Mine 715MB of chat history for plans, loose ends, scripts...",
    "createdAt": "2026-03-20T12:00:00Z",
    "createdBy": "claude-opus-4.5"
  },
  "stories": [
    {
      "id": "EXTRACT-001",
      "title": "Create unified chat log parser",
      "description": "Parse Claude and Codex history into unified format",
      "priority": "critical",
      "points": 5,
      "status": "done",
      "filesInScope": [
        "~/.roxy/scripts/knowledge/chat_log_parser.py",
        "~/.claude/history.jsonl"
      ],
      "acceptanceCriteria": [
        "All entries parsed without errors",
        "Unified ConversationTurn dataclass"
      ],
      "completedAt": "2026-03-20T06:48:00Z"
    }
  ],
  "meta": {
    "totalPoints": 31,
    "completedPoints": 28,
    "completionPercentage": 90.3,
    "lastUpdated": "2026-03-20T06:55:00Z"
  }
}
```

---

## Story Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier (e.g., `EXTRACT-001`) |
| `title` | string | Yes | Short description |
| `description` | string | Yes | Detailed explanation |
| `priority` | enum | Yes | `critical`, `high`, `medium`, `low` |
| `status` | enum | Yes | `todo`, `in_progress`, `done`, `blocked` |
| `points` | number | No | Story points (complexity estimate) |
| `filesInScope` | array | Yes | Files this story may modify |
| `acceptanceCriteria` | array | Yes | Conditions for completion |
| `completedAt` | string | No | ISO timestamp when done |
| `blockedBy` | string | No | What's blocking (if status=blocked) |

---

## Priority Levels

| Priority | Description | SLA |
|----------|-------------|-----|
| `critical` | System down or blocking all work | Immediate |
| `high` | Important feature or significant bug | Same day |
| `medium` | Normal priority work | This week |
| `low` | Nice to have, backlog | When available |

---

## Status Transitions

```
          ┌─────────────────┐
          │                 │
          ▼                 │
┌─────┐ ──► ┌───────────┐ ──► ┌──────┐
│ todo│     │in_progress│     │ done │
└─────┘ ◄── └───────────┘ ◄── └──────┘
   │              │
   │              ▼
   │        ┌─────────┐
   └──────► │ blocked │
            └─────────┘
```

### Rules

1. Only one story `in_progress` per agent
2. `blocked` requires `blockedBy` field
3. `done` requires all acceptance criteria met
4. `completedAt` set automatically when status→done

---

## API Endpoints

### GET /stories

List all stories across all epics:

```bash
curl http://127.0.0.1:8766/stories | jq
```

Response:
```json
{
  "stories": [...],
  "count": 6
}
```

### GET /stories/next

Get the next recommended story to work on:

```bash
curl http://127.0.0.1:8766/stories/next | jq
```

Response:
```json
{
  "story": {
    "id": "EXTRACT-006",
    "title": "Launch on Mac Studio and monitor",
    "priority": "high",
    "status": "todo",
    "filesInScope": [...]
  },
  "epic_id": "ROXY-CHAT-EXTRACTION-V1",
  "readiness_score": 0.85
}
```

### GET /stories/status

Get status summary across all epics:

```bash
curl http://127.0.0.1:8766/stories/status | jq
```

Response:
```json
{
  "total": 6,
  "by_status": {
    "todo": 1,
    "done": 5
  },
  "by_priority": {
    "critical": 3,
    "high": 3
  },
  "completion_percentage": 83.3
}
```

---

## Story Selection Algorithm

The `/stories/next` endpoint uses a weighted scoring system:

```python
score = (
    priority_weight[story.priority] * 0.4 +
    readiness_score * 0.3 +
    dependency_score * 0.2 +
    age_factor * 0.1
)
```

### Priority Weights

| Priority | Weight |
|----------|--------|
| critical | 1.0 |
| high | 0.75 |
| medium | 0.5 |
| low | 0.25 |

### Readiness Score

Based on:
- Files in scope exist
- No blocking dependencies
- Required tools available
- Memory context available

---

## Creating a New Epic

### 1. Create Directory

```bash
mkdir -p ~/.roxy/skoreq/MY-EPIC-V1/
```

### 2. Create 04_FINAL_PROPOSAL.json

```json
{
  "epic": {
    "id": "MY-EPIC-V1",
    "title": "My Epic Title",
    "description": "What this epic accomplishes",
    "createdAt": "2026-03-20T12:00:00Z",
    "createdBy": "agent-name"
  },
  "stories": [
    {
      "id": "MY-001",
      "title": "First story",
      "description": "What this story does",
      "priority": "high",
      "status": "todo",
      "points": 3,
      "filesInScope": ["~/.roxy/somefile.py"],
      "acceptanceCriteria": [
        "Criterion 1",
        "Criterion 2"
      ]
    }
  ],
  "meta": {
    "totalPoints": 3,
    "completedPoints": 0,
    "completionPercentage": 0,
    "lastUpdated": "2026-03-20T12:00:00Z"
  }
}
```

### 3. Validate

```bash
cat ~/.roxy/skoreq/MY-EPIC-V1/04_FINAL_PROPOSAL.json | jq .
curl http://127.0.0.1:8766/stories | jq '.stories[] | select(.id | startswith("MY-"))'
```

---

## Working on a Story

### 1. Get Next Story

```bash
curl http://127.0.0.1:8766/stories/next | jq
```

### 2. Update Status to in_progress

Edit the `04_FINAL_PROPOSAL.json`:

```json
{
  "id": "EXTRACT-006",
  "status": "in_progress"
}
```

### 3. Post to Breakroom

Add to `~/.roxy/.breakroom/activity_YYYYMMDD.md`:

```markdown
## Session: EXTRACT-006 - Launch on Mac Studio

### Working On
Story: EXTRACT-006
Epic: ROXY-CHAT-EXTRACTION-V1
Files: ~/.roxy/mission_supervisor.py, ~/.ssh/config
```

### 4. Complete Work

Verify all acceptance criteria met.

### 5. Update Status to done

```json
{
  "id": "EXTRACT-006",
  "status": "done",
  "completedAt": "2026-03-20T14:30:00Z"
}
```

### 6. Update Meta

```json
"meta": {
  "totalPoints": 31,
  "completedPoints": 31,
  "completionPercentage": 100,
  "lastUpdated": "2026-03-20T14:30:00Z"
}
```

---

## Best Practices

### Story Writing

1. **Specific titles** - "Fix auth" → "Fix token validation in /stream endpoint"
2. **Measurable criteria** - "Works correctly" → "All 48 tests pass"
3. **Bounded scope** - List exact files, not entire directories
4. **Single responsibility** - One story = one coherent change

### Epic Management

1. **Prefix convention** - `ROXY-FEATURE-V1`, `SKYBEAM-NDI-V1`
2. **Version suffix** - Allows epic revisions
3. **Regular updates** - Keep `lastUpdated` current
4. **Archive completed** - Move done epics to archive folder

---

## Integration with Missions

Stories can be executed automatically via the mission system:

```bash
# Trigger mission for next story
curl -X POST http://127.0.0.1:8766/missions/run | jq
```

The mission supervisor will:
1. Select next story via `/stories/next`
2. Acquire lease
3. Execute story goal
4. Verify acceptance criteria
5. Update story status

---

## Quick Reference

```
╔═══════════════════════════════════════════════════════════════╗
║                  SKOREQ QUICK REFERENCE                       ║
╠═══════════════════════════════════════════════════════════════╣
║ Location:    ~/.roxy/skoreq/{EPIC-ID}/                        ║
║ Main file:   04_FINAL_PROPOSAL.json                           ║
║ Next story:  curl http://127.0.0.1:8766/stories/next          ║
║ All stories: curl http://127.0.0.1:8766/stories               ║
║ Status:      curl http://127.0.0.1:8766/stories/status        ║
║ Priorities:  critical > high > medium > low                   ║
║ Statuses:    todo → in_progress → done | blocked              ║
╚═══════════════════════════════════════════════════════════════╝
```

---

*SKOREQ is the source of truth for all prioritized work in ROXY.*
