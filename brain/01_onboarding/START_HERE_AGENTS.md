# START HERE — Agents (Dec 2025)

> ⚠️ **DEPRECATED — Use `docs/onboarding/START_HERE.md` instead.**
>
> This document is no longer the canonical entry point.
> All agents MUST start at [`docs/onboarding/START_HERE.md`](./onboarding/START_HERE.md).
>
> **Deprecated:** 2025-12-18 (Era 3 governance reconciliation)

---

**Purpose:** Quick primer pointing to the authoritative onboarding path.
**Read time:** 3–5 minutes.  

## 🚨 CRITICAL: NEVER BREAK GUARDRAILS
- ❌ **NEVER modify:** husky, `.husky/*`, git hooks, pre-commit, pre-push, CI config, lint-staged, governance scripts
- ❌ **NEVER bypass:** ExecutionGate, STRICT_SINGLE_STORY, path validation, schema validation
- ❌ **NEVER silence:** test failures, hook failures, validation failures (report as data, don't fix)
- ❌ **NEVER scope-launder:** "fix CI", "fix hooks", "just this once" — meta-system mutations are NOT story work
- ✅ **ONLY modify:** files explicitly in `filesInScope` for the current story
- ✅ **ONLY report:** system issues as data, never attempt to fix during story execution
- **Violation = immediate failure, proof invalidation, guardrail breach**

## If you read nothing else
1) **LUNO Epoch:** `docs/luno/README.md` ⭐ **START HERE - Read this first (5 min)**
2) **Omega System:** `docs/omega/OMEGA_SYSTEM_MANUAL.md` ⭐ **AI optimization system (10 min)**
3) Vision: `docs/MINDSONG_ENTERPRISE_VISION.md`
4) Breakroom: `docs/agent-breakroom/ONBOARDING.md`
5) Progress: `public/releaseplan/master-progress.json` (tickets=epics; single source, LUNO schema)

## Full Onboarding Path (follow in order)
0) Breakroom Orientation — `docs/agent-breakroom/ONBOARDING.md`  
1) **LUNO Epoch** — `docs/luno/README.md` ⭐ **Read this first for LUNO era**  
2) **Omega System** — `docs/omega/OMEGA_SYSTEM_MANUAL.md` ⭐ **AI optimization system**  
3) Start Here — (this file)  
4) Enterprise Vision — `docs/MINDSONG_ENTERPRISE_VISION.md`  
5) Agent Ecosystem — `docs/AGENT_ECOSYSTEM_OVERVIEW.md`  
6) Progress System — `docs/agent-breakroom/TICKETS_AND_PROGRESS_EXPLAINED.md` (LUNO schema)  
7) **🚨 MANDATORY: Orchestrator Skills** — `luno-orchestrator/skills/luno-orchestrator-bible/skill.md` ⭐ **100% REQUIRED**
   - **Definitive guide** for orchestrator system knowledge (15 parts)
   - **Path Format Truth:** Repo root files use `src/...`, orchestrator files use `luno-orchestrator/src/...`
   - **ExecutionResult:** Always derived from git, never passed
   - **ExecutionGate:** Only path to 'done' status
   - **STRICT_SINGLE_STORY:** Only modify files in filesInScope
   - **Quick Reference:** `.claude/skills/luno-orchestrator/README.md`
   - **Error Catalog:** `docs/release/ORCHESTRATOR_ERROR_CATALOG.md` (all known issues and solutions)
8) Tech Guides (WebGPU/Rust/WASM) — `docs/brain/WEBGPU_RUST_WASM_MASTERY_GUIDE.md` (when relevant)  
9) First Message Checklist — `docs/AGENT_FIRST_MESSAGE_CHECKLIST.md`  
10) Current Priorities — `docs/CURRENT_PRIORITIES.md`

**For complete onboarding sequence, see:** `docs/ONBOARDING_CANONICAL_TRUTH.md`

## Do-Not-Duplicate Directive
Do NOT build parallel: widget systems, layout/drag/drop systems, keyboard shortcut handlers, audio routers, progress trackers, or RAG stacks.  
Use ONLY: Theater, Olympus, WidgetRegistry, AudioGraphService, `public/releaseplan/master-progress.json`, `codex.state.json`, Doc Brain MCP.

## Claude Skills Quick Reference (Omega System)

**Available Skills:** 33 skills covering 870,696 LOC (see `.claude/skills/INDEX.md`)

**Omega System:** Complete AI optimization architecture
- **Knowledge Layer:** 33 curated skill modules
- **Retrieval Layer:** Hybrid search v2 (embeddings + keyword)
- **QA Layer:** Astral Gauntlet validation, drift detection
- **Multi-Agent Layer:** Breakroom bridge for agent interoperability
- **MCP Server:** Claude Desktop integration

**Quick Commands:**
- `/skill-diagnostics` - Test all skills
- `/excellence-audit` - 200-metric evaluation
- `/enable-skill-telemetry` - See skill activations
- `/swarm-exec "<task>"` - Multi-agent execution

**Full Guides:**
- **Omega Manual:** `docs/omega/OMEGA_SYSTEM_MANUAL.md` ⭐ **Complete Omega documentation**
- **Omega + LUNO Integration:** `docs/omega/OMEGA_LUNO_INTEGRATION.md` ⭐ **How they work together**
- **Skills Index:** `.claude/skills/INDEX.md` (Omega Knowledge Layer)
- **Claude Skills:** `docs/CLAUDE_SKILLS_OVERVIEW.md`
- **Deep Docs:** `docs/brain/85-ai-skills/` (framework docs only; skills in `.claude/skills/`)

**Omega + LUNO:**
- **Omega** = AI cognition substrate (skills, retrieval, RAG)
- **LUNO** = Architectural epoch + governance (epics, tickets, doctrine)
- **They are complementary** - Omega provides AI tools, LUNO provides governance

## Current Context
- **LUNO Epoch Active** (2025-12-10) - Unified doctrine-bound era, governance layer
- **Omega System Operational** - 33 skills, hybrid search v2, embeddings active (AI cognition substrate)
- **Phoenix Protocol:** P0–P9 certified (R14); Retired, succeeded by LUNO Initiative (see `docs/archive/phoenix/`)
- Breakroom is mandatory for all coordination (Supabase realtime).

## Quick Commands
```bash
./scripts/verify-project-identity.sh
node scripts/progress/status.mjs
node scripts/agent-breakroom/post-activity.mjs task_claimed "Claimed TASK-XXX" --task TASK-XXX --agent YourAgent
```
