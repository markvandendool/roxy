# Claude Skills - Complete Catalog
**Purpose:** Comprehensive reference for all Claude Skills in MindSong Juke Hub  
**Status:** ✅ Active  
**Last Updated:** 2025-12-10

---

## ⚠️ IMPORTANT: Source of Truth

**All skill documentation is in `.claude/skills/`** - RAG-optimized README.md files with YAML frontmatter, architecture diagrams, API references, and comprehensive coverage.

**Master Index:** [`.claude/skills/INDEX.md`](../../../.claude/skills/INDEX.md)

**Total Skills:** 33 (100% coverage, 870,696 LOC, 8.43/10 average quality)

**Omega System:** This skills system is the **Omega Knowledge Layer**. See `docs/omega/OMEGA_SYSTEM_MANUAL.md` for complete Omega documentation.

---

## Overview

Claude Skills are domain-specific knowledge modules that enhance Claude Code's understanding of MindSong Juke Hub. They activate automatically when relevant topics are mentioned, providing expert-level guidance.

Each skill in `.claude/skills/` includes:
- YAML frontmatter (searchable metadata)
- Architecture diagrams (visual understanding)
- Core files index (exact locations + line counts)
- API reference (copy-paste code)
- Integration points (how systems connect)
- Common patterns (reusable approaches)
- Troubleshooting (debug guides)

---

## All 33 Skills by Tier

### Tier 1: Core Architecture (P0 - CRITICAL)

#### Audio Domain (85,000 LOC)
- **[apollo-audio](../../../.claude/skills/apollo-audio/README.md)** - Apollo router system, Tone.js integration, audio scheduling
- **[apollo-consolidation](../../../.claude/skills/apollo-consolidation/README.md)** - SmartAudioRouter, 5-tier backend priority
- **[chordcubes-audio](../../../.claude/skills/chordcubes-audio/README.md)** - ChordCubes audio integration
- **[professional-mixer](../../../.claude/skills/professional-mixer/README.md)** - Mixing console, channels, effects
- **[vgm-soundfont](../../../.claude/skills/vgm-soundfont/README.md)** - VGM soundfont playback

#### Rendering Domain (120,000 LOC)
- **[olympus-3d](../../../.claude/skills/olympus-3d/README.md)** - Three.js rendering, InstancedMesh optimization
- **[threejs-runtime](../../../.claude/skills/threejs-runtime/README.md)** - Native WebGPU, RailCompositor pipeline
- **[webgpu-rendering](../../../.claude/skills/webgpu-rendering/README.md)** - 18 WGSL shaders, Rust/WASM, dual-canvas
- **[braid-visualization](../../../.claude/skills/braid-visualization/README.md)** - 15-circle Yin-Yang SVG, voice lines

#### State Domain (45,000 LOC)
- **[quantum-rails](../../../.claude/skills/quantum-rails/README.md)** - State synchronization, CSS variables
- **[khronos-timing](../../../.claude/skills/khronos-timing/README.md)** - Single time authority, tick↔seconds conversion

#### Music Theory Domain (65,000 LOC)
- **[music-theory](../../../.claude/skills/music-theory/README.md)** - Voice leading (VL1/VL2/VL3), chord analysis
- **[chord-engine](../../../.claude/skills/chord-engine/README.md)** - Chord detection, analysis, voicing
- **[voice-leading](../../../.claude/skills/voice-leading/README.md)** - Voice leading algorithms, SATB constraints

---

### Tier 2: Features (P1 - HIGH)

#### Notation Domain (95,000 LOC)
- **[nvx1-score](../../../.claude/skills/nvx1-score/README.md)** - NVX1 score engine, notation rendering (EXEMPLAR)
- **[notagen-pipeline](../../../.claude/skills/notagen-pipeline/README.md)** - Music generation pipeline

#### Visualization Domain (55,000 LOC)
- **[chord-cubes](../../../.claude/skills/chord-cubes/README.md)** - 3D chord visualization
- **[8k-theater](../../../.claude/skills/8k-theater/README.md)** - TheaterProvider, StageWidget, scene presets

#### AI/ML Domain (25,000 LOC)
- **[rag-brain](../../../.claude/skills/rag-brain/README.md)** - RAG system, embeddings, knowledge graph

#### Hardware Domain (15,000 LOC)
- **[midi-hardware](../../../.claude/skills/midi-hardware/README.md)** - WebMIDI integration, <5ms latency

---

### Tier 3: Infrastructure (P2 - MEDIUM)

#### Testing Domain (40,000 LOC)
- **[playwright-testing](../../../.claude/skills/playwright-testing/README.md)** - E2E testing, SAVAGE³ suite
- **[audio-testing](../../../.claude/skills/audio-testing/README.md)** - Audio validation, Quantum Rails tests

#### Build Domain (30,000 LOC)
- **[wasm-integration](../../../.claude/skills/wasm-integration/README.md)** - WASM boundary, Rust interop
- **[rust-bevy](../../../.claude/skills/rust-bevy/README.md)** - Rust Bevy integration

#### Integration Domain (20,000 LOC)
- **[figma-design-system](../../../.claude/skills/figma-design-system/README.md)** - Figma integration, design tokens
- **[obs-ndi-streaming](../../../.claude/skills/obs-ndi-streaming/README.md)** - OBS/NDI streaming

---

### Tier 4: Meta (P3 - LOW)

#### Process Domain (35,000 LOC)
- **[epic-tracker](../../../.claude/skills/epic-tracker/README.md)** - Epic/sprint/story tracking
- **[mdf2030-master](../../../.claude/skills/mdf2030-master/README.md)** - MDF2030/MOS2030 spec knowledge
- **[widget-architecture](../../../.claude/skills/widget-architecture/README.md)** - Widget slave pattern, EventSpine projections

#### Recovery Domain (15,000 LOC)
- **[phoenix-protocol](../../../.claude/skills/phoenix-protocol/README.md)** - Phoenix P0-P14 phases
- **[ghost-protocol](../../../.claude/skills/ghost-protocol/README.md)** - Agent handoff system

#### Coordination Domain (25,000 LOC)
- **[agent-breakroom](../../../.claude/skills/agent-breakroom/README.md)** - Multi-agent coordination
- **[novaxe-seb](../../../.claude/skills/novaxe-seb/README.md)** - SEB archive (read-only)

---

## External Skills

In addition to the 33 custom skills, Claude has access to:
- **36+ Anthropic skills** (official Claude capabilities)
- **Superpowers skills** (engineering best practices)

---

## Related Documentation

- **Master Index:** [`.claude/skills/INDEX.md`](../../../.claude/skills/INDEX.md) - Complete index with dependencies, keywords
- **Onboarding:** [`docs/CLAUDE_SKILLS_OVERVIEW.md`](../../CLAUDE_SKILLS_OVERVIEW.md) - Introduction for new agents
- **Commands:** [COMMANDS_REFERENCE.md](./COMMANDS_REFERENCE.md) - All slash commands
- **Excellence:** [EXCELLENCE_FRAMEWORK.md](./EXCELLENCE_FRAMEWORK.md) - 200 metrics framework
- **Telemetry:** [TELEMETRY_GUIDE.md](./TELEMETRY_GUIDE.md) - Skill activation tracking
- **Swarm:** [SWARM_MODE_GUIDE.md](./SWARM_MODE_GUIDE.md) - Multi-agent orchestration

---

**Maintained By:** Claude Skills System  
**Related:** `docs/CLAUDE_SKILLS_OVERVIEW.md`, `CLAUDE.md`, `.claude/skills/`

