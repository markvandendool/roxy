# Swarm Mode Guide
**Purpose:** How to use multi-agent swarm orchestration for complex tasks  
**Status:** ✅ Active  
**Last Updated:** 2025-01-11

---

## What is Swarm Mode?

Swarm Mode orchestrates **multiple specialized Claude agents** working in parallel on complex tasks. Each agent has a specific role and expertise, allowing for efficient division of labor.

---

## Available Agents

| Agent | Role | Capabilities | Cannot Do |
|-------|------|-------------|-----------|
| **Architect** | Design & ADRs | Architectural design, ADRs, invariants, pattern analysis | Write implementation code |
| **Code** | Implementation | TypeScript, React, service implementation, bug fixes | Make architectural decisions |
| **Test** | Testing | Vitest unit tests, Playwright E2E, visual regression | Write production code |
| **Perf** | Performance | GPU profiling, audio latency, frame budgets | Modify code (reports only) |
| **Breakroom** | Coordination | Activity posting, discovery sharing, swarm coordination | Execute tasks (coordinates only) |

---

## Using Swarm Mode

### Basic Usage
```
/swarm-exec "<task description>"
```

### Example
```
/swarm-exec "Implement UnifiedWidgetRegistry.ts with full bridges"
```

**What Happens:**
1. Task analyzed for required roles
2. Appropriate agents spawned in parallel
3. Breakroom Agent coordinates work
4. Agents execute concurrently
5. Results synthesized into final output

---

## Task Types & Agent Selection

### Feature Implementation
**Task:** "Add dark mode toggle to settings"

**Agents Spawned:**
- **Architect** → Designs toggle pattern
- **Code** → Implements TypeScript
- **Test** → Writes test coverage

**Command:**
```
/swarm-exec "Add dark mode toggle to settings"
```

---

### Bug Investigation
**Task:** "Debug Apollo initialization failure"

**Agents Spawned:**
- **Perf** → Profiles initialization timing
- **Code** → Analyzes code paths
- **Breakroom** → Coordinates and posts findings

**Command:**
```
/swarm-exec "Debug Apollo initialization failure"
```

---

### Performance Audit
**Task:** "Profile piano rendering and optimize"

**Agents Spawned:**
- **Perf** → GPU profiling, frame analysis
- **Architect** → Reviews optimization opportunities
- **Code** → Implements optimizations

**Command:**
```
/swarm-exec "Profile piano rendering and optimize"
```

---

### Architecture Review
**Task:** "Review Event Spine integration with Apollo"

**Agents Spawned:**
- **Architect** → Designs integration pattern
- **Code** → Reviews implementation
- **Test** → Validates integration

**Command:**
```
/swarm-exec "Review Event Spine integration with Apollo"
```

---

## Spawning Individual Agents

### Spawn Architect
```
/spawn-agent architect
```

**Use When:**
- Need architectural design
- Creating ADRs
- Defining invariants
- Pattern analysis

**Output:** Markdown design documents

---

### Spawn Code Agent
```
/spawn-agent code
```

**Use When:**
- Implementing features
- Fixing bugs
- Writing TypeScript
- Following existing patterns

**Output:** TypeScript implementation files

**Constraints:**
- Must respect architectural decisions
- Must follow Apollo Rule
- Must use existing patterns

---

### Spawn Test Agent
```
/spawn-agent test
```

**Use When:**
- Writing unit tests
- Creating E2E tests
- Visual regression
- Coverage requirements

**Output:** Test files (*.test.ts, *.spec.ts)

**Standards:**
- 70%+ coverage target
- Uses data-testid selectors
- Proper test helpers
- Console assertions for audio

---

### Spawn Perf Agent
```
/spawn-agent perf
```

**Use When:**
- Performance profiling
- GPU metrics
- Audio latency analysis
- Frame budget monitoring

**Output:** Performance reports (no code changes)

---

### Spawn Breakroom Agent
```
/spawn-agent breakroom
```

**Use When:**
- Coordinating swarm
- Posting activities
- Sharing discoveries
- Enforcing protocol

**Output:** Activity JSON, coordination logs

---

## Agent Invariants

All agents **must** follow these invariants:

1. **Event Spine** is the single musical authority
2. **3 Ears Principle** must be preserved
3. **Apollo Rule** - never call Tone.js directly
4. **Breakroom Protocol** - post activities before work
5. **Port Convention** - use 9135/5174
6. **SEB Quarantine** - no SEB code execution

**Violations:** Agent will refuse or warn

---

## Coordination Flow

### 1. Task Analysis
Breakroom Agent analyzes task and identifies:
- Required roles
- Dependencies
- Coordination needs

### 2. Agent Spawning
Agents spawned in parallel:
- Each gets task subset
- Clear boundaries defined
- Communication channels established

### 3. Execution
Agents work concurrently:
- Architect designs
- Code implements
- Test validates
- Perf profiles
- Breakroom coordinates

### 4. Synthesis
Results combined:
- Architect design → Code implementation
- Code changes → Test coverage
- Perf findings → Optimization recommendations
- All activities → Breakroom posts

---

## Best Practices

### Task Description Quality
**Good:**
```
/swarm-exec "Implement UnifiedWidgetRegistry with full Event Spine integration, TypeScript types, and Playwright tests"
```

**Poor:**
```
/swarm-exec "fix widget thing"
```

**Guidelines:**
- Be specific about requirements
- Mention technologies involved
- Include acceptance criteria
- Reference related systems

### Agent Selection
- **Simple tasks** → Single agent (don't use swarm)
- **Multi-domain** → Swarm with relevant agents
- **Complex** → Full swarm (all agents)

### Coordination
- Breakroom Agent handles coordination
- Agents post activities automatically
- Discoveries shared via Breakroom
- No duplicate work

---

## Output Formats

Each agent produces output in its format:

| Agent | Output Format | Location |
|-------|--------------|----------|
| Architect | Markdown design docs | `docs/architecture/` or inline |
| Code | TypeScript files | `src/` |
| Test | Test files | `tests/` or `src/**/*.test.ts` |
| Perf | Performance reports | Console or markdown |
| Breakroom | Activity JSON | Breakroom database |

---

## Breakroom Integration

All swarm agents automatically:
1. **Register** with Breakroom on spawn
2. **Post** `task_claimed` when starting
3. **Share** discoveries during work
4. **Post** `task_completed` when finishing
5. **Coordinate** via Breakroom chat

**No manual Breakroom posting needed** - agents handle it.

---

## Limitations

### What Swarm Can't Do
- **Real-time collaboration** - Agents work sequentially in response
- **Shared state** - Each agent has independent context
- **Cross-agent debugging** - No shared debugging session
- **Live code editing** - Changes are sequential

### When Not to Use Swarm
- **Simple tasks** - Single agent sufficient
- **Quick fixes** - Overhead not worth it
- **Exploratory work** - Need flexibility
- **Learning** - Single agent better for understanding

---

## Examples

### Example 1: Full Feature
```
/swarm-exec "Add metronome visualization widget with Three.js rendering, Apollo audio sync, and Playwright tests"
```

**Agents:**
- Architect → Widget architecture design
- Code → Three.js + Apollo integration
- Test → Playwright E2E tests
- Perf → Frame budget validation
- Breakroom → Coordinates and posts

---

### Example 2: Performance Optimization
```
/swarm-exec "Optimize piano rendering to achieve 60fps with InstancedMesh and GPU profiling"
```

**Agents:**
- Perf → Profiles current performance
- Architect → Designs optimization strategy
- Code → Implements InstancedMesh
- Test → Validates frame rate
- Breakroom → Coordinates

---

### Example 3: Bug Fix
```
/swarm-exec "Fix Apollo emergency mode initialization failure with root cause analysis"
```

**Agents:**
- Perf → Profiles initialization timing
- Code → Analyzes failure points
- Test → Creates regression test
- Breakroom → Posts findings

---

## Troubleshooting

### Agents Not Spawning
- Check task description clarity
- Verify agent roles are available
- Review Breakroom connection

### Coordination Issues
- Check Breakroom status: `/breakroom-status`
- Verify activities are posting
- Review agent boundaries

### Conflicting Outputs
- Architect and Code disagree → Review design first
- Test failures → Code agent adjusts
- Perf issues → Code agent optimizes

---

## Reference

**Swarm Engine:** `.claude/swarm/swarm-engine.mts`  
**Agent Roles:** `.claude/swarm/roles/`  
**Command:** `/swarm-exec`, `/spawn-agent`

---

**Status:** ✅ Active  
**Maintained By:** Claude Skills System  
**Related:** `COMMANDS_REFERENCE.md`, `SKILLS_OVERVIEW.md`




























