# ROXY Agent Quickstart

**Read Time:** 5 minutes | **Last Updated:** 2026-03-20 | **Status:** Canonical

This is THE ONE DOCUMENT. Read this and you understand the entire ROXY system.

---

## 0. Critical Rules (30 seconds)

```
RULE 1: Token Required    - ~/.roxy/secret.token for ALL API calls
RULE 2: Breakroom First   - Post intentions BEFORE starting work
RULE 3: Memory Always     - Use /memory/recall for context before acting
RULE 4: Never Modify      - roxy_core.py, systemd units, secret.token
RULE 5: SKOREQ Stories    - Check /stories/next for prioritized work
```

---

## 1. What is ROXY? (1 minute)

ROXY is a **dual-purpose autonomous system**:

| Mode | Purpose | Key Feature |
|------|---------|-------------|
| **SKYBEAM** | Automated content creation | NDI/OBS orchestration, video pipeline |
| **Mindsong-Juke-Hub** | Automated AAA coding | Mission-based story execution |

### Core Components

```
roxy_core.py (7.2K lines)     → HTTP API on port 8766
mission_supervisor.py          → Lease-backed autonomous execution
memory_postgres.py             → RAG brain (PostgreSQL + ChromaDB)
story_selector.py              → SKOREQ story prioritization
qualification_pipeline.py      → 5-stage production readiness gate
```

### Current State (Overmatch Phase 2 Complete)

```
QUALIFIED=YES | Score=1.0 | Tests=48/48 passing
```

---

## 2. Key Endpoints (1 minute)

### Primary Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Service liveness check |
| `/stream` | GET | SSE streaming for prompts |
| `/memory/recall` | POST | Semantic search in RAG brain |
| `/stories` | GET | List all SKOREQ stories |
| `/stories/next` | GET | Get next prioritized story |
| `/stories/status` | GET | Story status summary |
| `/missions` | GET | List all missions |
| `/missions/active` | GET | Current active mission |
| `/missions/run` | POST | Trigger mission execution |
| `/qualification/status` | GET | Production readiness status |
| `/qualification/run` | POST | Run qualification pipeline |

### Base URL

```
http://127.0.0.1:8766
```

All endpoints also available with `/v1/` prefix.

---

## 3. Authentication (30 seconds)

```bash
# Get the token
TOKEN=$(cat ~/.roxy/secret.token)

# Use in requests
curl -H "X-ROXY-Token: $TOKEN" http://127.0.0.1:8766/health

# Python
import requests
TOKEN = open(os.path.expanduser("~/.roxy/secret.token")).read().strip()
headers = {"X-ROXY-Token": TOKEN}
requests.get("http://127.0.0.1:8766/health", headers=headers)
```

---

## 4. Memory / RAG Brain (1 minute)

ROXY has a persistent memory with **45K+ knowledge items**:

```bash
# Query the memory
curl -X POST http://127.0.0.1:8766/memory/recall \
  -H "Content-Type: application/json" \
  -H "X-ROXY-Token: $TOKEN" \
  -d '{"query": "how to use OBS control", "k": 5}'
```

### Memory Sources

| Collection | Content |
|------------|---------|
| `extracted_knowledge` | Plans, TODOs, scripts, decisions from chat history |
| `roxy_onboarding` | Onboarding docs (this one!) |
| `roxy_api` | API documentation |
| `roxy_systems` | System architecture docs |

### Best Practices

1. **Always query memory first** before starting new work
2. Search for existing solutions before implementing
3. Use memory to understand past decisions

---

## 5. Breakroom Protocol (1 minute)

**Location:** `~/.roxy/.breakroom/`

### Before Starting Work

Create or append to `activity_YYYYMMDD.md`:

```markdown
# Breakroom Activity - 2026-03-20

## Session: [Brief Description]

### Intentions
- [ ] Task 1 I plan to do
- [ ] Task 2 I plan to do

### Files I May Touch
- path/to/file1
- path/to/file2

---
*Agent: [Your Name] | Session: [Type]*
```

### After Completing Work

Update the same file:

```markdown
### Accomplishments
1. Completed task 1
2. Completed task 2

### Files Modified
- path/to/file1 - what changed
- path/to/file2 - what changed

### Issues Encountered
- Any blockers or problems

---
*Agent: [Your Name] | Session: [Type] | Completed: HH:MM*
```

---

## 6. SKOREQ Story System (1 minute)

SKOREQ manages prioritized work items.

### Location

```
~/.roxy/skoreq/{EPIC-ID}/
├── 00_MANIFEST.json      # Epic metadata
├── 01_STORIES.json       # Story definitions
└── 04_FINAL_PROPOSAL.json # Approved proposal
```

### Story Format

```json
{
  "id": "EXTRACT-001",
  "title": "Create unified chat log parser",
  "description": "Parse Claude and Codex history into unified format",
  "priority": "critical",    // critical, high, medium, low
  "status": "todo",          // todo, in_progress, done, blocked
  "points": 5,
  "filesInScope": ["~/.roxy/scripts/knowledge/chat_log_parser.py"],
  "acceptanceCriteria": [
    "All entries parsed without errors",
    "Unified output format"
  ]
}
```

### Get Next Story

```bash
curl -H "X-ROXY-Token: $TOKEN" http://127.0.0.1:8766/stories/next
```

---

## 7. Mission System (30 seconds)

Missions are **lease-backed autonomous executions** of stories.

### Lifecycle

```
PENDING → ACQUIRED → RUNNING → VERIFYING → COMPLETE|FAILED
                                        ↘ EXPIRED (if lease timeout)
```

### Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| Lease TTL | 300s | Time before lease expires |
| Cooldown | 1800s | Wait between story retries |
| Max Attempts | 3 | Retry limit per story |
| Concurrent | 1 | Max simultaneous missions |

### Traces

All mission activity logged to:
```
~/.roxy/data/mission_traces/{mission_id}.jsonl
```

---

## 8. Directory Structure

```
~/.roxy/
├── roxy_core.py            # Main HTTP/IPC service
├── mission_supervisor.py   # Mission execution
├── memory_postgres.py      # RAG brain
├── story_selector.py       # SKOREQ integration
├── qualification_pipeline.py # Production gates
├── secret_scanner.py       # Security scanning
├── preflight_bridge.py     # Luno integration
│
├── data/
│   ├── mission_ledger.json # Mission history
│   └── mission_traces/     # Execution logs
│
├── .breakroom/             # Agent coordination
│   └── activity_*.md       # Daily activity logs
│
├── skoreq/                 # Story queue
│   └── {EPIC-ID}/          # Epic folders
│
├── knowledge/              # Extracted knowledge
│   ├── extracted_*.jsonl   # Raw extractions
│   └── reports/            # Generated reports
│
├── docs/                   # Documentation (you are here)
│   ├── 00_ONBOARDING/
│   ├── 10_API_REFERENCE/
│   ├── 20_SYSTEMS/
│   ├── 30_PROTOCOLS/
│   └── 90_ARCHIVE/
│
└── chroma_db/              # Vector database (586MB)
```

---

## 9. Quick Commands

### Check System Health

```bash
curl http://127.0.0.1:8766/health | jq
```

### Query Memory

```bash
curl -X POST http://127.0.0.1:8766/memory/recall \
  -d '{"query": "your search term", "k": 5}'
```

### Get Next Story

```bash
curl http://127.0.0.1:8766/stories/next | jq
```

### Check Qualification

```bash
curl http://127.0.0.1:8766/qualification/status | jq
```

### View Active Mission

```bash
curl http://127.0.0.1:8766/missions/active | jq
```

---

## 10. Current Priorities

Check SKOREQ for latest priorities:

```bash
ls ~/.roxy/skoreq/
cat ~/.roxy/skoreq/*/04_FINAL_PROPOSAL.json | jq '.stories[] | select(.status=="todo")'
```

Or use the API:

```bash
curl http://127.0.0.1:8766/stories/next | jq
```

---

## Quick Reference Card

```
╔═══════════════════════════════════════════════════════════════╗
║                    ROXY QUICK REFERENCE                       ║
╠═══════════════════════════════════════════════════════════════╣
║ Token:     ~/.roxy/secret.token                               ║
║ Port:      8766                                               ║
║ Breakroom: ~/.roxy/.breakroom/activity_YYYYMMDD.md            ║
║ SKOREQ:    ~/.roxy/skoreq/{EPIC-ID}/04_FINAL_PROPOSAL.json    ║
║ Memory:    POST /memory/recall {"query": "...", "k": 5}       ║
║ Stories:   GET /stories/next                                  ║
║ Missions:  GET /missions/active                               ║
║ Health:    GET /health                                        ║
╚═══════════════════════════════════════════════════════════════╝
```

---

*This document is the canonical agent onboarding reference. All agents should read this before starting work.*
