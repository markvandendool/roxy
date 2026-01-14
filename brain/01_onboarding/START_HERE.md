# START HERE — Agent Onboarding

**Status:** ✅ Authoritative
**Last Updated:** 2025-12-18
**Purpose:** Single entry point for all agents
**Read Time:** 5 minutes

---

## Step 0: Governance (MANDATORY — 5 minutes)

**Before doing anything else, read:**

➡️ [`docs/governance/CANONICAL_GOVERNANCE.md`](../governance/CANONICAL_GOVERNANCE.md)

You must understand:
- **L0–L3 authority tiers** — What rules you can/cannot override
- **100-file commit limit** — Exceeding this requires L0 override
- **Evidence vs logic separation** — Never mix in same commit
- **Override protocol** — Exact format required (`FORCE PUSH — GOVERNANCE OVERRIDE`)

**Failure to follow governance rules will block or invalidate your work.**

See also:
- [`docs/governance/OVERRIDE_PROTOCOL.md`](../governance/OVERRIDE_PROTOCOL.md) — Exact override format
- [`docs/governance/AGENT_EXPERIENCE_CHECKLIST.md`](../governance/AGENT_EXPERIENCE_CHECKLIST.md) — Pre-commit checklist

---

## If You Read Nothing Else

1. **LUNO Epoch:** `docs/luno/README.md` ⭐ (5 min)
2. **Omega System:** `docs/omega/OMEGA_SYSTEM_MANUAL.md` ⭐ (10 min)
3. **Vision:** `docs/MINDSONG_ENTERPRISE_VISION.md` (15–20 min)
4. **Breakroom:** `docs/onboarding/tools/breakroom.md` (5 min)
5. **Service Catalog:** `docs/rag-canonical/20-services/master-catalog.md` (10 min) - **MANDATORY before coding**

---

## First 30 Minutes

### Step 1: Project Identity (2 min)
```bash
./scripts/verify-project-identity.sh
```
Expect: "MindSong Juke Hub — Musical Operating System — Rust/WASM + WebGPU + React + TypeScript"

### Step 2: LUNO Epoch (5 min)
Read: `docs/luno/README.md`
- LUNO initiative context
- Ticket naming (EPIC-LUNO-*, LUNO_*_###)
- Doctrine reference required

### Step 3: Omega System (10 min)
Read: `docs/omega/OMEGA_SYSTEM_MANUAL.md`
- AI optimization system
- 33 skills available
- How Omega + LUNO work together

### Step 4: Breakroom Setup (5 min)
Read: `docs/onboarding/tools/breakroom.md`
- Register agent
- Post activities
- File locking

### Step 5: Progress System (5 min)
Read: `docs/onboarding/00-first-30-minutes/progress.md`
- `public/releaseplan/master-progress.json` structure
- Tickets = epics
- How to check status

### Step 5.5: LUNO Orchestrator (5 min) ⭐ NEW
Read: `.claude/skills/luno-orchestrator/README.md`
- Autonomous story execution system
- **CRITICAL**: Story status values (`todo`, `in_progress`, `execution_pending`, `done`, `blocked`)
- **CRITICAL**: Path format rules (see below)
- ExecutionGate = ONLY path to 'done'
- Git commit = ONLY proof of execution

### Step 5.6: Cursor Plan → Swarm Ticket (5 min) ⭐ NEW
Read: `docs/onboarding/CURSOR_PLAN_TO_SWARM_TICKET.md`
- **How to add work to the swarm**
- Cursor Plan Mode → swarm ticket JSON translation contract
- Field mapping table (plan → ticket)
- "Add the ticket properly" = follow this contract
- **CRITICAL**: Plans are ideas, tickets are contracts

### Step 6: Common Mistakes (3 min)
Read: `docs/onboarding/common-mistakes/`
- What NOT to do
- Anti-patterns

---

## First Day

### Complete 30-Minute Path
Finish all steps above.

## Remote Access (iMac / "Friday")
If you need to access the iMac known as **Friday** (citadel-worker-1):

- Host: `10.0.0.65`
- User: `mark`
- Key: `~/imackeys`
- Recommended alias (add to `~/.ssh/config`):

```text
Host friday
  HostName 10.0.0.65
  User mark
  IdentityFile ~/imackeys
```

- Jump example (via `imac`):
```
ssh -J imac mark@10.0.0.69
```

**Voice profile note:** To change ROXY voice profile without enabling another user's profile, set `ROXY_TTS_PROFILE` in `~/.roxy/.env` and restart the `roxy-voice` service.

Example (set to your profile `mine`):
```bash
if rg -q '^ROXY_TTS_PROFILE' ~/.roxy/.env; then
  sed -i 's/^ROXY_TTS_PROFILE=.*/ROXY_TTS_PROFILE=mine/' ~/.roxy/.env
else
  echo 'ROXY_TTS_PROFILE=mine' >> ~/.roxy/.env
fi
sudo systemctl restart roxy-voice
```

### Read Enterprise Vision (15 min)
Read: `docs/MINDSONG_ENTERPRISE_VISION.md`
- Mission & North Star
- Core Architecture Pillars
- Current Strategic Initiatives
- Agent Ecosystem

### Read Service Catalog (10 min) ⚠️ MANDATORY
Read: `docs/rag-canonical/20-services/master-catalog.md`
- **CRITICAL:** Check this before building ANY system
- Prevents duplicate rebuilds
- Single source of truth for all systems

### Read Execution Contract (10 min)
Read: `docs/reference/contracts/execution-queue.md`
- How to submit execution requests
- Schema requirements
- Validation rules

### Explore First Day Guides
Read: `docs/onboarding/01-first-day/`
- Tool setup
- Common workflows
- Where to ask questions

---

## First Week

### Complete First Day Path
Finish all steps above.

### Read Domain-Specific Guides
Explore: `docs/rag-canonical/`
- Architecture: `docs/rag-canonical/10-architecture/`
- Services: `docs/rag-canonical/20-services/`
- Schemas: `docs/rag-canonical/30-schemas/`
- Invariants: `docs/rag-canonical/40-invariants/`
- Execution: `docs/rag-canonical/50-execution/`

### Review Governance Rules
Read: `docs/reference/governance/`
- LUNO: `docs/reference/governance/luno/`
- Breakroom: `docs/reference/governance/breakroom/`
- Agent: `docs/reference/governance/agent/`

### Explore Historical Context (As Needed)
Explore: `docs/brain/`
- Decisions: `docs/brain/20-decisions/`
- Research: `docs/brain/80-research/`
- Projects: `docs/brain/60-projects/`

### Practice Exercises
Complete: `docs/onboarding/02-first-week/exercises/`

---

## What You MUST Read

**Mandatory (Before Any Work):**
- `docs/luno/README.md` - LUNO epoch context
- `docs/onboarding/tools/breakroom.md` - Breakroom protocol
- `docs/MINDSONG_ENTERPRISE_VISION.md` - Enterprise vision
- `docs/rag-canonical/20-services/master-catalog.md` - **Service catalog (prevent rebuilds)**

**Mandatory (Before Coding):**
- `docs/rag-canonical/20-services/master-catalog.md` - Check existing systems
- `docs/reference/contracts/execution-queue.md` - Execution contract
- `docs/onboarding/common-mistakes/` - Anti-patterns

---

## What You MUST NOT Read

**Do NOT Read (Unless Needed for Historical Context):**
- `docs/brain/` - Exploratory, may contain contradictions
- `docs/archive/` - Historical only
- `docs/scratch/` - Experimental
- Multiple onboarding variants - Only use this consolidated path

**Do NOT Trust:**
- Chat memory over RAG for canonical facts
- Outdated documentation
- Duplicate service catalogs (only use master-catalog.md)

---

## Critical Rules

### Path Format Rules (CRITICAL — Updated 2025-12-15)

**Repository Structure:**
```
MINDSONG JUKE HUB (repo root)
├── src/                    ← Repo root source files
├── tests/                  ← Repo root tests
├── luno-orchestrator/      ← Orchestrator subdirectory
│   ├── src/                ← Orchestrator source files
│   └── tests/              ← Orchestrator tests
└── ...
```

**Path Rules for LLM/Agent Output:**
```typescript
// ❌ WRONG - Never use these formats
"/src/foo.ts"                      // Absolute path (leading /)
"./src/foo.ts"                     // Relative prefix

// ✅ CORRECT - For repo root files
"src/foo.ts"                       // Repo root file
"tests/unit/foo.test.ts"           // Repo root test

// ✅ CORRECT - For orchestrator files
"luno-orchestrator/src/foo.ts"     // Orchestrator file
"luno-orchestrator/tests/unit/x.test.ts" // Orchestrator test
```

**Path Normalization:** The orchestrator strips `luno-orchestrator/` prefix for filesInScope matching.
Both `src/foo.ts` and `luno-orchestrator/src/foo.ts` match a filesInScope entry of `src/foo.ts`.

### Story Status Values (P0-A LOCKED)

**VALID:**
- `todo` — Not started
- `in_progress` — Human planning ONLY (NO code changes)
- `execution_pending` — Dispatched, awaiting git commit
- `done` — Git commit exists + verified
- `blocked` — Cannot proceed

**FORBIDDEN (Runtime Error):**
- ❌ `completed` — Use `done`
- ❌ `executed` — Use `done`
- ❌ `finished` — Use `done`
- ❌ `in-progress` (hyphenated) — Use `in_progress`

### Do-Not-Duplicate Directive
**Do NOT build parallel:**
- Widget systems
- Layout/drag/drop systems
- Keyboard shortcut handlers
- Audio routers
- Progress trackers
- RAG stacks

**Use ONLY:**
- Theater, Olympus, WidgetRegistry, AudioGraphService
- `public/releaseplan/master-progress.json`
- `codex.state.json`
- Doc Brain MCP

### Breakroom Protocol
- Post activities before/during/after work
- Do NOT edit `public/releaseplan/*.json` directly
- Register/claim tasks via Breakroom
- Use file locks for coordination

### Breakroom vs Orchestrator Authority

| System | Authority | Purpose |
|--------|-----------|---------|
| **Orchestrator** | Authoritative for story state | `done` status ONLY via ExecutionGate |
| **Breakroom** | Advisory/coordination | Claims, intent, discussion |

**Rule:** Orchestrator determines when work is `done`. Breakroom coordinates who is working on what.

### RAG Trust Hierarchy
1. **RAG** (highest) - Single source of truth for canonical facts
2. **Reference Docs** - Contracts, invariants, governance
3. **Chat Memory** (lowest) - Session-specific context only

---

## Quick Commands

```bash
# Verify project identity
./scripts/verify-project-identity.sh

# Check progress status
node scripts/progress/status.mjs

# Post Breakroom activity
node scripts/agent-breakroom/post-activity.mjs task_claimed "Claimed TASK-XXX" --task TASK-XXX --agent YourAgent
```

---

## Questions Onboarding Answers

- ✅ What is this project? → Vision doc
- ✅ How do I not break things? → Common mistakes, protocols
- ✅ Where do I find canonical facts? → RAG canonical
- ✅ How do I coordinate with other agents? → Breakroom
- ✅ What systems exist? → Service catalog
- ✅ What are the rules? → Governance docs

---

## Questions Onboarding Defers

- ❓ Deep architectural decisions → `docs/brain/20-decisions/`
- ❓ Historical alternatives → `docs/brain/`
- ❓ Research findings → `docs/brain/80-research/`
- ❓ Experimental work → `docs/scratch/`

---

## Current Context (Jan 2026)

- **LUNO Epoch Active** (2025-12-10) - Unified doctrine-bound era
- **Omega System Operational** - 33 skills, hybrid search v2
- **Phoenix Protocol:** P0–P9 certified (R14); Retired, succeeded by LUNO
- **Breakroom:** Mandatory for all coordination (Supabase realtime)
- **Progress:** `public/releaseplan/master-progress.json` (single source, LUNO schema)
- **Claude-Mem:** Shared persistent memory across all agents (see below)

---

## Shared Agent Memory (Claude-Mem)

**All Claude agents on this machine and Mac Studio share persistent memory.**

### How It Works
- **Plugin:** Claude-Mem v9.0.4 installed on both machines
- **Storage:** `~/.claude-mem/claude-mem.db` (SQLite)
- **Sync:** Bi-directional rsync every 5 minutes
- **Worker:** Port 37777 (Linux) / 37778 (Mac Studio)

### Key Benefits
- Context persists across sessions
- All agents share learned knowledge
- Semantic search of past work
- Automatic context injection

### Commands
```bash
# Check worker status
cd ~/.claude/plugins/marketplaces/claude-mem && bun run worker:status

# View memory logs
tail -f ~/.claude-mem/logs/claude-mem-$(date +%Y-%m-%d).log

# Manual sync
~/.shared-claude-memory/sync-memory.sh

# Search past work (via MCP)
# Use mem-search skill or HTTP API on port 37777
```

### Sync Architecture
```
┌─────────────────────┐      rsync (5min)      ┌─────────────────────┐
│   Linux (roxy)      │ ◄──────────────────────► │   Mac Studio       │
│   10.0.0.69         │                          │   10.0.0.92        │
│   ~/.claude-mem/    │                          │   ~/.claude-mem/   │
│   Worker: :37777    │                          │   Worker: :37778   │
└─────────────────────┘                          └─────────────────────┘
```

### Related Infrastructure
- **Roxy Memory:** PostgreSQL + ChromaDB + Redis (see `~/.roxy/memory_postgres.py`)
- **MCP Memory Server:** `@anthropic/mcp-memory@latest` (project-level)
- **Breakroom:** Supabase tables for agent coordination

**Full documentation:** `~/.shared-claude-memory/MEMORY_INFRASTRUCTURE.md`

---

## Next Steps

1. Complete "First 30 Minutes" path
2. Read service catalog (prevent rebuilds)
3. Register in Breakroom
4. Check current priorities: `docs/CURRENT_PRIORITIES.md`
5. Start work with proper coordination

---

## Related Documents

- [Canonical Documentation Architecture](../reference/governance/CANONICAL_DOCUMENTATION_ARCHITECTURE.md) - Domain definitions
- [RAG Ingestion Policy](../reference/governance/RAG_INGESTION_POLICY.md) - RAG rules
- [Duplication Risk Report](../reference/governance/DUPLICATION_RISK_REPORT.md) - Prevention strategies

---

**This is the SINGLE entry point. All other onboarding variants are deprecated.**




















