# Claude Skills - Commands Reference
**Purpose:** Complete reference for all Claude slash commands  
**Status:** ✅ Active  
**Last Updated:** 2025-01-11

---

## Diagnostic Commands

### `/skill-diagnostics`
**Purpose:** Run comprehensive self-test of all Claude Code skills, context loading, and repository knowledge

**What It Tests:**
- Core skills activation (6 custom skills)
- Context loading (CLAUDE.md, rules)
- Repository knowledge (ports, files, patterns)
- Rule enforcement (Apollo Rule, Breakroom Protocol)
- Architecture integrity (Event Spine, 3 Ears)

**Output:** Diagnostic report showing which skills activate and context validation

**Deep Dive:** [commands/skill-diagnostics.md](./commands/skill-diagnostics.md)

---

### `/excellence-audit [category]`
**Purpose:** Run comprehensive evaluation against the 200 Metrics of AI Excellence

**Usage:**
```
/excellence-audit              # Full audit (all 200 metrics)
/excellence-audit code         # A. Code Intelligence (25 metrics)
/excellence-audit domain       # B. Domain Expertise (25 metrics)
/excellence-audit execution    # C. Task Execution (25 metrics)
/excellence-audit reasoning    # D. Reasoning & Planning (25 metrics)
/excellence-audit safety       # E. Safety & Compliance (25 metrics)
/excellence-audit communication # F. Communication (25 metrics)
/excellence-audit collaboration # G. Collaboration (25 metrics)
/excellence-audit improvement  # H. Self-Improvement (25 metrics)
```

**Output:** ASCII report with scores, ratings, critical metrics status, top performers, improvement opportunities

**Rating Scale:**
- 🏆 LEGENDARY (95-100)
- ⭐ ELITE (90-94)
- ✅ EXCELLENT (85-89)
- 👍 PROFICIENT (80-84)
- 📊 COMPETENT (70-79)
- 📈 DEVELOPING (60-69)
- ⚠️ NEEDS IMPROVEMENT (<60)

**Deep Dive:** [commands/excellence-audit.md](./commands/excellence-audit.md)

---

### `/enable-skill-telemetry`
**Purpose:** Enable transparent telemetry layer to see which skills activate and why

**Effect:**
- Every Claude response includes `[Skill Telemetry]` block
- Shows activated skills, context sources, trigger phrases, response metrics
- Helps understand which skills fire for different tasks

**Example Output:**
```
[Skill Telemetry]
- Activated Skill: apollo-audio
- Context Source: CLAUDE.md(✓)
- Trigger Phrase: "audio playback"
- Response Time: 1.2s
```

**Deep Dive:** [commands/enable-skill-telemetry.md](./commands/enable-skill-telemetry.md)

---

### `/disable-skill-telemetry`
**Purpose:** Disable telemetry layer for clean responses without metadata

**Effect:**
- No `[Skill Telemetry]` blocks in responses
- Skills still work normally
- No tracking overhead

**Deep Dive:** [commands/disable-skill-telemetry.md](./commands/disable-skill-telemetry.md)

---

## Swarm Commands

### `/swarm-exec "<task description>"`
**Purpose:** Execute a task using multiple specialized agents working in parallel

**How It Works:**
1. Task Analysis - Parse task and identify required roles
2. Agent Spawning - Spawn appropriate agents in parallel
3. Coordination - Breakroom Agent coordinates work
4. Execution - Agents work concurrently on specialties
5. Synthesis - Results combined into final output

**Example:**
```
/swarm-exec "Implement UnifiedWidgetRegistry.ts with full bridges"
```

**Spawns:**
- **Architect** → Designs registry pattern
- **Code** → Implements TypeScript
- **Test** → Writes test coverage
- **Breakroom** → Coordinates and posts activities

**Deep Dive:** [commands/swarm-exec.md](./commands/swarm-exec.md)

---

### `/spawn-agent <role>`
**Purpose:** Spawn a specialized agent from the swarm to handle a specific type of task

**Available Roles:**
- `architect` - Design, ADRs, invariants
- `code` - TypeScript implementation
- `test` - Vitest + Playwright tests
- `perf` - Performance profiling
- `breakroom` - Swarm coordination

**Usage:**
```
/spawn-agent architect
/spawn-agent code
/spawn-agent test
```

**Deep Dive:** [commands/spawn-agent.md](./commands/spawn-agent.md)

---

## Intelligence Budget Commands

### `/cib jet|tank|quantum`
**Purpose:** Control Claude's reasoning depth and response characteristics

**Modes:**

**Jet Mode** (`/cib jet`)
- Speed: Maximum
- Depth: Minimal
- Use Case: Quick answers, simple tasks
- Characteristics: Concise, direct action, minimal exploration

**Tank Mode** (`/cib tank`)
- Speed: Slowest
- Depth: Maximum
- Use Case: Complex debugging, forensic analysis
- Characteristics: Exhaustive analysis, multiple perspectives, detailed reasoning

**Quantum Mode** (`/cib quantum`) - Default
- Speed: Balanced
- Depth: Adaptive
- Use Case: General development work
- Characteristics: Adapts to task complexity, optimal for most tasks

**Deep Dive:** [commands/cib.md](./commands/cib.md)

---

## Validation Commands

### `/apollo-validate`
**Purpose:** Check for Apollo Rule compliance in the codebase

**What It Checks:**
- Direct Tone.js calls (forbidden)
- Apollo.playNote() usage (approved)
- Violations in source files
- Exceptions (Apollo implementation, tests)

**Output:** Compliance report with violations and approved usage counts

**Deep Dive:** [commands/apollo-validate.md](./commands/apollo-validate.md)

---

### `/audio-check`
**Purpose:** Validate the Apollo audio system and playback functionality

**Steps:**
1. Run `pnpm audio:validate`
2. Check console for success/error indicators
3. Verify Apollo readiness in browser console
4. Report common issues

**Success Indicators:**
- `[Apollo] Ready`
- `[VL.APOLLO.ROUTED]`
- `[APOLLO.PLAYCHORD]`

**Error Indicators:**
- `[GlobalApollo] Failed to initialize`
- `[ApolloMetronome] Operating in emergency mode`

**Deep Dive:** [commands/audio-check.md](./commands/audio-check.md)

---

### `/perf-audit`
**Purpose:** Performance analysis for GPU, audio, and frame budget

**What It Analyzes:**
- Frame rate (target: 60fps)
- Frame time (target: <8ms)
- GPU metrics
- Audio latency (target: <5ms MIDI, <16ms audio)
- Memory usage
- Draw call counts

**Output:** Performance report with metrics and recommendations

**Deep Dive:** [commands/perf-audit.md](./commands/perf-audit.md)

---

### `/visual-regression`
**Purpose:** Visual test comparison using screenshot diffing

**What It Does:**
- Captures screenshots
- Compares with baseline
- Detects visual changes
- Reports differences

**Use Cases:**
- Widget rendering verification
- UI component changes
- Layout regression detection

**Deep Dive:** [commands/visual-regression.md](./commands/visual-regression.md)

---

### `/run-tests`
**Purpose:** Execute test suites (Vitest + Playwright)

**What It Runs:**
- Unit tests (Vitest)
- E2E tests (Playwright)
- Coverage reports
- Test results summary

**Usage:**
```
/run-tests              # All tests
/run-tests unit         # Vitest only
/run-tests e2e          # Playwright only
/run-tests khronos      # Khronos timing tests
```

**Deep Dive:** [commands/run-tests.md](./commands/run-tests.md)

---

### `/breakroom-status`
**Purpose:** Check Breakroom system status and coordination health

**What It Reports:**
- Active agents
- Recent activities
- System health
- Connection status
- Lock status

**Deep Dive:** [commands/breakroom-status.md](./commands/breakroom-status.md)

---

### `/deploy-prep`
**Purpose:** Pre-deployment checks for production readiness

**What It Checks:**
- Build success
- Test pass rate
- Apollo Rule compliance
- Performance targets
- Error handling
- Documentation completeness

**Output:** Deployment readiness report with checklist

**Deep Dive:** [commands/deploy-prep.md](./commands/deploy-prep.md)

---

### `/discover-skills`
**Purpose:** Interactive skill discovery for current task

**What It Does:**
- Analyzes current task/context
- Identifies relevant skills
- Shows skill descriptions
- Links to skill guides
- Suggests usage patterns

**Output:** Personalized skill recommendations with links

**Deep Dive:** [commands/discover-skills.md](./commands/discover-skills.md)

---

## Command Categories

| Category | Commands | Purpose |
|----------|----------|---------|
| **Diagnostic** | skill-diagnostics, excellence-audit, enable/disable-telemetry | Testing and monitoring |
| **Swarm** | swarm-exec, spawn-agent | Multi-agent orchestration |
| **Intelligence** | cib | Reasoning depth control |
| **Validation** | apollo-validate, audio-check, perf-audit, visual-regression, run-tests | System verification |
| **Coordination** | breakroom-status | Agent coordination |
| **Deployment** | deploy-prep | Production readiness |
| **Discovery** | discover-skills | Skill finding |

---

## Quick Reference

| Command | When to Use | Time |
|---------|-------------|------|
| `/skill-diagnostics` | First time setup, troubleshooting | 30s |
| `/excellence-audit` | Performance evaluation | 2min |
| `/enable-skill-telemetry` | Understanding skill activation | Instant |
| `/swarm-exec` | Complex multi-domain tasks | 5-10min |
| `/spawn-agent architect` | Design work needed | 2-5min |
| `/cib tank` | Deep debugging required | Ongoing |
| `/apollo-validate` | Before audio changes | 1min |
| `/audio-check` | Audio issues | 2min |
| `/perf-audit` | Performance problems | 3min |
| `/discover-skills` | Finding relevant skills | 30s |

---

**Status:** ✅ Active  
**Maintained By:** Claude Skills System  
**Related:** `docs/CLAUDE_SKILLS_OVERVIEW.md`, `INDEX.md`




























