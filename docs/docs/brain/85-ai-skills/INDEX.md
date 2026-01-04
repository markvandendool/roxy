# Claude Skills - Brain Docs Index
**Purpose:** Master index for Claude Skills documentation in brain docs  
**Status:** ✅ Active  
**Last Updated:** 2025-12-10

---

## ⚠️ IMPORTANT: Source of Truth

**All skill documentation is now in `.claude/skills/`** - This directory contains RAG-optimized, comprehensive skill README.md files (33 skills, 100% coverage, 9.25/10 average quality).

**Master Index:** [`.claude/skills/INDEX.md`](../../../.claude/skills/INDEX.md)

---

## Framework & Automation Documentation

These documents are unique to `docs/brain/85-ai-skills/` and complement the skill files:

| Document | Purpose | Read Time |
|----------|---------|-----------|
| [SKILLS_OVERVIEW.md](./SKILLS_OVERVIEW.md) | Complete skills catalog (references all 33 skills) | 10 min |
| [COMMANDS_REFERENCE.md](./COMMANDS_REFERENCE.md) | All slash commands | 15 min |
| [EXCELLENCE_FRAMEWORK.md](./EXCELLENCE_FRAMEWORK.md) | 200 metrics deep dive | 20 min |
| [TELEMETRY_GUIDE.md](./TELEMETRY_GUIDE.md) | Telemetry usage | 5 min |
| [SWARM_MODE_GUIDE.md](./SWARM_MODE_GUIDE.md) | Multi-agent orchestration | 10 min |
| [IMPROVEMENT_WORKFLOW.md](./IMPROVEMENT_WORKFLOW.md) | Continuous improvement | 10 min |
| [EXCELLENCE_DASHBOARD.md](./EXCELLENCE_DASHBOARD.md) | Metrics tracking | 5 min |
| [TELEMETRY_ENFORCEMENT.md](./TELEMETRY_ENFORCEMENT.md) | CI/CD integration | 5 min |

### Automation Documentation

| Document | Purpose |
|----------|---------|
| [automation/AUTO_REFINEMENT.md](./automation/AUTO_REFINEMENT.md) | Auto-refinement system |
| [automation/CONTEXT_REFRESH.md](./automation/CONTEXT_REFRESH.md) | Context refresh engine |
| [automation/REPO_DIFF_SCANNER.md](./automation/REPO_DIFF_SCANNER.md) | Repository diff scanner |

---

## All 33 Skills (Source: `.claude/skills/`)

### Tier 1: Core Architecture (P0 - CRITICAL)

**Audio Domain:**
- [apollo-audio](../../../.claude/skills/apollo-audio/README.md)
- [apollo-consolidation](../../../.claude/skills/apollo-consolidation/README.md)
- [chordcubes-audio](../../../.claude/skills/chordcubes-audio/README.md)
- [professional-mixer](../../../.claude/skills/professional-mixer/README.md)
- [vgm-soundfont](../../../.claude/skills/vgm-soundfont/README.md)

**Rendering Domain:**
- [olympus-3d](../../../.claude/skills/olympus-3d/README.md)
- [threejs-runtime](../../../.claude/skills/threejs-runtime/README.md)
- [webgpu-rendering](../../../.claude/skills/webgpu-rendering/README.md)
- [braid-visualization](../../../.claude/skills/braid-visualization/README.md)

**State Domain:**
- [quantum-rails](../../../.claude/skills/quantum-rails/README.md)
- [khronos-timing](../../../.claude/skills/khronos-timing/README.md)

**Music Theory Domain:**
- [music-theory](../../../.claude/skills/music-theory/README.md)
- [chord-engine](../../../.claude/skills/chord-engine/README.md)
- [voice-leading](../../../.claude/skills/voice-leading/README.md)

### Tier 2: Features (P1 - HIGH)

**Notation Domain:**
- [nvx1-score](../../../.claude/skills/nvx1-score/README.md)
- [notagen-pipeline](../../../.claude/skills/notagen-pipeline/README.md)

**Visualization Domain:**
- [chord-cubes](../../../.claude/skills/chord-cubes/README.md)
- [8k-theater](../../../.claude/skills/8k-theater/README.md)

**AI/ML Domain:**
- [rag-brain](../../../.claude/skills/rag-brain/README.md)

**Hardware Domain:**
- [midi-hardware](../../../.claude/skills/midi-hardware/README.md)

### Tier 3: Infrastructure (P2 - MEDIUM)

**Testing Domain:**
- [playwright-testing](../../../.claude/skills/playwright-testing/README.md)
- [audio-testing](../../../.claude/skills/audio-testing/README.md)

**Build Domain:**
- [wasm-integration](../../../.claude/skills/wasm-integration/README.md)
- [rust-bevy](../../../.claude/skills/rust-bevy/README.md)

**Integration Domain:**
- [figma-design-system](../../../.claude/skills/figma-design-system/README.md)
- [obs-ndi-streaming](../../../.claude/skills/obs-ndi-streaming/README.md)

### Tier 4: Meta (P3 - LOW)

**Process Domain:**
- [epic-tracker](../../../.claude/skills/epic-tracker/README.md)
- [mdf2030-master](../../../.claude/skills/mdf2030-master/README.md)
- [widget-architecture](../../../.claude/skills/widget-architecture/README.md)

**Recovery Domain:**
- [phoenix-protocol](../../../.claude/skills/phoenix-protocol/README.md)
- [ghost-protocol](../../../.claude/skills/ghost-protocol/README.md)

**Coordination Domain:**
- [agent-breakroom](../../../.claude/skills/agent-breakroom/README.md)
- [novaxe-seb](../../../.claude/skills/novaxe-seb/README.md)

---

## Quick Access

- **Master Index:** [`.claude/skills/INDEX.md`](../../../.claude/skills/INDEX.md) - Complete index with stats, dependencies, keywords
- **Onboarding:** [`docs/CLAUDE_SKILLS_OVERVIEW.md`](../../CLAUDE_SKILLS_OVERVIEW.md) - Introduction for new agents
- **Commands:** [COMMANDS_REFERENCE.md](./COMMANDS_REFERENCE.md) - All slash commands

---

**Note:** All skill documentation is now consolidated into comprehensive README.md files in `.claude/skills/` as the single source of truth. Legacy SKILL_GUIDE.md, PATTERNS.md, TROUBLESHOOTING.md files have been **disabled** (moved to `skills.DISABLED/` for safety).

## Omega System Integration

**This directory is part of the Omega System (AI cognition substrate).**

- **Omega Knowledge Layer:** `.claude/skills/` (33 skills - source of truth)
- **Omega Documentation:** `docs/omega/OMEGA_SYSTEM_MANUAL.md`
- **LUNO Governance:** `docs/luno/` (epoch, tickets, doctrine)
- **Integration Guide:** `docs/omega/OMEGA_LUNO_INTEGRATION.md`

**Relationship:**
- **Omega** = AI tools (skills, retrieval, RAG, embeddings) - **ACTIVE**
- **LUNO** = Governance (epoch, rules, doctrine) - **ACTIVE**
- They are complementary, not conflicting.

