# Documentation Brain - Master Index

**Last Updated:** 2025-12-09  
**Status:** Active  
**Purpose:** Central navigation hub for all brain documentation categories

---

## 📚 Documentation Categories

### 00-quickstart/
Quick reference guides, onboarding checklists, and immediate action items.

**Key Files:**
- [INDEX.md](./00-quickstart/INDEX.md) - Complete quickstart navigation
- [QUICK_START.md](./00-quickstart/QUICK_START.md) - Agent onboarding
- [TECH_STACK.md](./00-quickstart/TECH_STACK.md) - Technology versions

### 10-architecture/
System architecture, design decisions, and structural documentation.

**Key Areas:**
- Audio routing (Apollo, Tone.js, VCO)
- 3D rendering (WebGPU, Rust/WASM)
- Event Spine & Intent Bus
- Widget architecture

### 20-decisions/
Architectural decisions, ADRs, and design rationale.

**Key Decisions:**
- WASM Boundary patterns
- Audio routing architecture
- Renderer ownership model
- Method naming conventions

### 30-playbooks/
Step-by-step guides for common tasks and workflows.

**Key Playbooks:**
- Fix WASM binding errors
- Add new widgets
- GPU profiling
- Layer implementation

### 40-patterns/
Correct implementation patterns and code examples.

**Key Patterns:**
- Instanced rendering
- Buffer creation
- Render pass setup
- WASM boundary correct usage

### 50-errors/
Error solutions, troubleshooting guides, and anti-patterns.

**Key Resources:**
- [ERROR_CATALOG.md](./50-errors/ERROR_CATALOG.md) - Complete error index
- Error-specific solutions (E0277, E0599, etc.)

### 60-projects/
Project-specific documentation, progress tracking, and feature specs.

**Key Projects:**
- Rocky AI
- NVX1 Score
- Olympus Widgets
- Theater 8K

### 70-external/
External documentation mirrors and third-party resources.

### 80-research/
Research notes, analysis, and experimental documentation.

### 85-ai-skills/ ⭐ **NEW**
**Claude Skills & AI Capabilities** - Domain-specific AI skills, commands, excellence framework, and swarm orchestration.

**Key Files:**
- [INDEX.md](./85-ai-skills/INDEX.md) - Skills documentation master index
- [SKILLS_OVERVIEW.md](./85-ai-skills/SKILLS_OVERVIEW.md) - Complete skills catalog
- [COMMANDS_REFERENCE.md](./85-ai-skills/COMMANDS_REFERENCE.md) - All slash commands
- [EXCELLENCE_FRAMEWORK.md](./85-ai-skills/EXCELLENCE_FRAMEWORK.md) - 200 metrics framework
- [TELEMETRY_GUIDE.md](./85-ai-skills/TELEMETRY_GUIDE.md) - Skill activation tracking
- [SWARM_MODE_GUIDE.md](./85-ai-skills/SWARM_MODE_GUIDE.md) - Multi-agent orchestration
- [IMPROVEMENT_WORKFLOW.md](./85-ai-skills/IMPROVEMENT_WORKFLOW.md) - Continuous improvement

**Skills:**
- `apollo-audio` - Audio engine debugging and Apollo router expertise
- `olympus-3d` - 3D rendering optimization and WebGPU knowledge
- `music-theory` - Voice leading (VL1/VL2/VL3) and music theory
- `playwright-testing` - E2E testing patterns and best practices
- `midi-hardware` - MIDI device integration and protocols
- `agent-breakroom` - Breakroom protocol and coordination

**Quick Access:**
- See [docs/CLAUDE_SKILLS_OVERVIEW.md](../../CLAUDE_SKILLS_OVERVIEW.md) for onboarding
- See [docs/brain/85-ai-skills/INDEX.md](./85-ai-skills/INDEX.md) for complete catalog

### 90-archive/
Archived documentation, deprecated patterns, and historical reference.

---

## 🔍 Search Strategies

### By Category
Navigate to the appropriate category directory above.

### By Error Code
```bash
grep -r "E####" docs/brain/50-errors/
```

### By Topic
```bash
grep -ri "topic" docs/brain/
```

### Using Doc Brain MCP
The Doc Brain MCP server (`scripts/doc-brain/mcp-server.mjs`) provides semantic search across all brain documentation, including the 85-ai-skills category.

---

## 🚀 Quick Links

- **Onboarding:** [docs/ONBOARDING_CANONICAL_TRUTH.md](../../ONBOARDING_CANONICAL_TRUTH.md)
- **Claude Skills:** [docs/CLAUDE_SKILLS_OVERVIEW.md](../../CLAUDE_SKILLS_OVERVIEW.md)
- **Architecture:** [docs/10-architecture/](../../10-architecture/)
- **Current Priorities:** [docs/CURRENT_PRIORITIES.md](../../CURRENT_PRIORITIES.md)

---

**Note:** This index provides high-level navigation. For detailed navigation within each category, see the category-specific INDEX.md files.



























