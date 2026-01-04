# MindSong Skills Master Index

**Last Updated:** 2025-12-15
**Total Skills:** 34
**Coverage:** 870,696 LOC
**System Version:** 2.0.0 (Enterprise Grade)
**Epoch:** LUNO (Effective 2025-12-10)

---

## LUNO Epoch Notice

> **This skills system (Omega Knowledge Layer) operates within the LUNO epoch.**
>
> - **Omega System:** Active AI cognition substrate (see `docs/omega/OMEGA_SYSTEM_MANUAL.md`)
> - **LUNO Initiative:** Active governance layer (see `docs/luno/README.md`)
> - **Relationship:** Omega provides AI tools, LUNO provides governance
> - All new work uses LUNO naming conventions (`LUNO_*_###`)
> - System names (Khronos, Apollo, Hermes, EventSpine) remain unchanged in code
> - Phoenix Protocol references are deprecated — use LUNO for new initiatives
> - See `docs/luno/` for LUNO framework documentation
> - See `docs/luno/LUNO_AGENT_OPERATING_RULES.md` for mandatory agent rules
> - See `docs/omega/OMEGA_LUNO_INTEGRATION.md` for how they work together

---

## Quick Stats

| Metric | Value |
|--------|-------|
| Skills Populated | **34/34 (100%)** |
| Average Quality | 8.47/10 |
| Tier 1 (P0) | 13 skills |
| Tier 2 (P1) | 6 skills |
| Tier 3 (P2) | 6 skills |
| Tier 4 (P3) | 9 skills |

---

## System Documentation (v2.0 → 10.0/10)

| Document | Description |
|----------|-------------|
| [SUPREME.md](./SUPREME.md) | Master whitepaper - complete system architecture |
| [SKILL-GRAPH.md](./SKILL-GRAPH.md) | Full dependency graph with clusters |
| [AGENT-PROTOCOL.md](./AGENT-PROTOCOL.md) | Mandatory protocol for AI agents |
| [NOVADOCS-ARCHITECTURE.md](./NOVADOCS-ARCHITECTURE.md) | Productization architecture |
| [_TEMPLATE.md](./_TEMPLATE.md) | Template for creating new skills |

## Generated Data Files

| File | Description |
|------|-------------|
| `.embeddings.json` | 501 semantic chunks (384d) |
| `.graph-embeddings.json` | Node2Vec embeddings (64d) |
| `.skill-graph.json` | Graph structure (33 nodes, 80 edges) |
| `.fingerprints.json` | Content fingerprints for drift detection |
| `quality-report.json` | Quality scores for all 33 skills |
| `retrieval-metrics.json` | RAG performance metrics |

## Validation & Metrics

| Script | Purpose |
|--------|---------|
| `scripts/skills/mcp-skill-server.mjs` | MCP server (5 tools, 34 resources) |
| `scripts/skills/skill-embeddings.mjs` | Generate 501-chunk semantic embeddings |
| `scripts/skills/graph-embeddings.mjs` | Node2Vec graph embeddings (64d) |
| `scripts/skills/evaluate-retrieval.mjs` | 50-query retrieval metrics |
| `scripts/skills/security-scan.mjs` | Security & PII scanner |
| `scripts/skills/skill-fingerprint.mjs` | Content drift detection |
| `scripts/skills/skill-autogen.mjs` | Self-healing auto-generation |
| `scripts/skills/skill-redaction.mjs` | RBAC access control |
| `scripts/skills/generate-quality-report.mjs` | Quality scoring |
| `scripts/skills/validate-frontmatter.mjs` | YAML validation |
| `scripts/skills/validate-line-counts.mjs` | Line count validation |

## Client Libraries

| Client | Purpose |
|--------|---------|
| `scripts/skills/clients/skill-client.mjs` | Universal skill client |
| `scripts/skills/clients/claude-agent.mjs` | Claude-specific integration |
| `scripts/skills/clients/cursor-integration.mjs` | Cursor IDE integration |

## Latest Retrieval Metrics

| Metric | Value | Target |
|--------|-------|--------|
| Recall@20 | 0.97 | >0.80 |
| NDCG@10 | 0.74 | >0.75 |
| MRR | 0.71 | >0.90 |
| Avg Latency | 5.87ms | <100ms |

---

## Tier 1: Core Architecture (P0 - CRITICAL)

### Audio Domain (85,000 LOC)

| Skill | Status | Lines | Score | Last Audit |
|-------|--------|-------|-------|------------|
| [apollo-audio](./apollo-audio/README.md) | AUDITED | 320 | 9.2/10 | 2025-12-10 |
| [apollo-consolidation](./apollo-consolidation/README.md) | AUDITED | 350 | 9.4/10 | 2025-12-10 |
| [chordcubes-audio](./chordcubes-audio/README.md) | AUDITED | 398 | 9.0/10 | 2025-12-10 |
| [professional-mixer](./professional-mixer/README.md) | AUDITED | 409 | 9.1/10 | 2025-12-10 |
| [vgm-soundfont](./vgm-soundfont/README.md) | AUDITED | 310 | 9.1/10 | 2025-12-10 |

### Rendering Domain (120,000 LOC)

| Skill | Status | Lines | Score | Last Audit |
|-------|--------|-------|-------|------------|
| [olympus-3d](./olympus-3d/README.md) | AUDITED | 340 | 9.2/10 | 2025-12-10 |
| [threejs-runtime](./threejs-runtime/README.md) | AUDITED | 380 | 9.3/10 | 2025-12-10 |
| [webgpu-rendering](./webgpu-rendering/README.md) | AUDITED | 390 | 9.4/10 | 2025-12-10 |
| [braid-visualization](./braid-visualization/README.md) | AUDITED | 340 | 9.2/10 | 2025-12-10 |

### State Domain (45,000 LOC)

| Skill | Status | Lines | Score | Last Audit |
|-------|--------|-------|-------|------------|
| [quantum-rails](./quantum-rails/README.md) | AUDITED | 380 | 9.2/10 | 2025-12-10 |
| [khronos-timing](./khronos-timing/README.md) | AUDITED | 350 | 9.3/10 | 2025-12-10 |

### Music Theory Domain (65,000 LOC)

| Skill | Status | Lines | Score | Last Audit |
|-------|--------|-------|-------|------------|
| [music-theory](./music-theory/README.md) | AUDITED | 390 | 9.3/10 | 2025-12-10 |
| [chord-engine](./chord-engine/README.md) | AUDITED | 350 | 9.2/10 | 2025-12-10 |
| [voice-leading](./voice-leading/README.md) | AUDITED | 376 | 9.0/10 | 2025-12-10 |

---

## Tier 2: Features (P1 - HIGH)

### Notation Domain (95,000 LOC)

| Skill | Status | Lines | Score | Last Audit |
|-------|--------|-------|-------|------------|
| [nvx1-score](./nvx1-score/README.md) | EXEMPLAR | 838 | 9.5/10 | 2025-12-10 |
| [notagen-pipeline](./notagen-pipeline/README.md) | AUDITED | 360 | 9.3/10 | 2025-12-10 |

### Visualization Domain (55,000 LOC)

| Skill | Status | Lines | Score | Last Audit |
|-------|--------|-------|-------|------------|
| [chord-cubes](./chord-cubes/README.md) | AUDITED | 310 | 9.3/10 | 2025-12-10 |
| [8k-theater](./8k-theater/README.md) | AUDITED | 360 | 9.3/10 | 2025-12-10 |

### AI/ML Domain (25,000 LOC)

| Skill | Status | Lines | Score | Last Audit |
|-------|--------|-------|-------|------------|
| [rag-brain](./rag-brain/README.md) | AUDITED | 290 | 9.2/10 | 2025-12-10 |

### Hardware Domain (15,000 LOC)

| Skill | Status | Lines | Score | Last Audit |
|-------|--------|-------|-------|------------|
| [midi-hardware](./midi-hardware/README.md) | AUDITED | 280 | 9.2/10 | 2025-12-10 |

---

## Tier 3: Infrastructure (P2 - MEDIUM)

### Testing Domain (40,000 LOC)

| Skill | Status | Lines | Score | Last Audit |
|-------|--------|-------|-------|------------|
| [playwright-testing](./playwright-testing/README.md) | AUDITED | 320 | 9.3/10 | 2025-12-10 |
| [audio-testing](./audio-testing/README.md) | AUDITED | 290 | 9.2/10 | 2025-12-10 |

### Build Domain (30,000 LOC)

| Skill | Status | Lines | Score | Last Audit |
|-------|--------|-------|-------|------------|
| [wasm-integration](./wasm-integration/README.md) | AUDITED | 310 | 9.3/10 | 2025-12-10 |
| [rust-bevy](./rust-bevy/README.md) | AUDITED | 300 | 9.2/10 | 2025-12-10 |

### Integration Domain (20,000 LOC)

| Skill | Status | Lines | Score | Last Audit |
|-------|--------|-------|-------|------------|
| [figma-design-system](./figma-design-system/README.md) | AUDITED | 340 | 9.4/10 | 2025-12-10 |
| [obs-ndi-streaming](./obs-ndi-streaming/README.md) | AUDITED | 310 | 9.1/10 | 2025-12-10 |

---

## Tier 4: Meta (P3 - LOW)

### Process Domain (35,000 LOC)

| Skill | Status | Lines | Score | Last Audit |
|-------|--------|-------|-------|------------|
| [epic-tracker](./epic-tracker/README.md) | AUDITED | 280 | 9.2/10 | 2025-12-10 |
| [mdf2030-master](./mdf2030-master/README.md) | AUDITED | 320 | 9.4/10 | 2025-12-10 |
| [widget-architecture](./widget-architecture/README.md) | AUDITED | 290 | 9.3/10 | 2025-12-10 |

### Recovery Domain (15,000 LOC)

| Skill | Status | Lines | Score | Last Audit |
|-------|--------|-------|-------|------------|
| [phoenix-protocol](./phoenix-protocol/README.md) | AUDITED | 310 | 9.3/10 | 2025-12-10 |
| [ghost-protocol](./ghost-protocol/README.md) | AUDITED | 300 | 9.2/10 | 2025-12-10 |

### Coordination Domain (25,000 LOC)

| Skill | Status | Lines | Score | Last Audit |
|-------|--------|-------|-------|------------|
| [agent-breakroom](./agent-breakroom/README.md) | AUDITED | 310 | 9.4/10 | 2025-12-10 |
| [novaxe-seb](./novaxe-seb/README.md) | AUDITED | 290 | 9.3/10 | 2025-12-10 |

### Orchestration Domain (45,000 LOC) ⭐ NEW

| Skill | Status | Lines | Score | Last Audit |
|-------|--------|-------|-------|------------|
| [luno-orchestrator](./luno-orchestrator/README.md) | AUDITED | 280 | 9.8/10 | 2025-12-15 |

> **CRITICAL:** The luno-orchestrator skill documents the autonomous story execution system.
> Agents MUST understand story status values, path format rules, and ExecutionGate before any work.

---

## Skill Dependencies Graph

```
                    ┌──────────────────┐
                    │   khronos-timing │
                    │   (Master Clock) │
                    └────────┬─────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  apollo-audio   │ │  quantum-rails  │ │   nvx1-score    │
│  (Audio Engine) │ │   (Sync State)  │ │   (Notation)    │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ chordcubes-audio│ │  voice-leading  │ │   olympus-3d    │
│ (ChordCubes)    │ │   (VL Engine)   │ │   (3D Render)   │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┴───────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   chord-cubes   │
                    │  (3D ChordViz)  │
                    └─────────────────┘
```

---

## Search Keywords by Domain

### Audio
`apollo`, `tone.js`, `worklet`, `audio`, `sampler`, `synthesizer`, `midi`, `playback`, `latency`, `buffer`, `backend`, `router`, `mixer`, `channel`, `gain`, `pan`, `mute`, `solo`, `master`, `dB`, `envelope`, `ADSR`, `cutoff`, `release`, `attack`

### Rendering
`olympus`, `three.js`, `webgpu`, `scene`, `mesh`, `geometry`, `material`, `shader`, `animation`, `camera`, `light`, `renderer`, `frame`, `budget`, `fps`, `particle`, `post-processing`, `bloom`, `glow`

### State
`khronos`, `quantum-rails`, `clock`, `tempo`, `bpm`, `ppq`, `tick`, `drift`, `sync`, `transport`, `play`, `pause`, `seek`, `loop`, `timeline`, `event`, `spine`, `state`

### Music Theory
`chord`, `scale`, `mode`, `interval`, `voicing`, `voice-leading`, `inversion`, `quality`, `root`, `bass`, `melody`, `harmony`, `progression`, `key`, `signature`, `notagen`, `transition`

### Notation
`nvx1`, `score`, `measure`, `bar`, `note`, `rest`, `beam`, `stem`, `clef`, `staff`, `render`, `layout`, `engraving`, `musicxml`, `midi`

---

## Quick Command Reference

### Run Skill Tests
```bash
# All audio skills
npm test -- tests/audio/

# Specific skill area
npm test -- tests/savage3/
```

### Validate Skill Document
```bash
node scripts/evaluate-skill.ts .claude/skills/SKILL_NAME/README.md
```

### Audit All Skills
```bash
for skill in .claude/skills/*/README.md; do
  echo "=== $skill ==="
  node scripts/evaluate-skill.ts "$skill"
done
```

---

## Contributing

1. Use `_TEMPLATE.md` for new skills
2. Target 350-500 lines
3. Include YAML frontmatter
4. Run evaluation script
5. Update this index

---

## Legend

| Status | Meaning |
|--------|---------|
| EMPTY | Directory exists, no README.md |
| EXISTS | README.md present, needs audit |
| EXEMPLAR | Reference implementation |
| AUDITED | Passed 50-metric evaluation |

| Score | Rating |
|-------|--------|
| 9.5+ | LEGENDARY |
| 9.0-9.4 | EXCELLENT |
| 8.0-8.9 | GOOD (needs work) |
| <8.0 | FAILING |
