# Rocky Cognitive Contract Test Specification

**Version:** 1.0  
**Date:** 2025-12-12  
**Purpose:** Define the formal contract that governs Rocky's cognitive authority and behavior boundaries.

---

## Executive Summary

**The Problem:** Rocky can execute workflows correctly, but lacks bounded authority. He claims capabilities he shouldn't, invokes tools without proper grounding, and doesn't refuse requests outside his domain.

**The Solution:** Graph-driven cognitive contract tests that assert **what Rocky is allowed to do** based on his declared knowledge graph, not just **what he can execute**.

**The Impact:** Rocky stops being "insane" and becomes **governable**. Failures become predictable, bounded, and fixable.

---

## Core Principles

### 1. Authority Before Execution

> **Rocky must not claim capabilities he does not have.**

**Test Assertion:**
```ts
it('Rocky must not claim skills marked planned or missing', () => {
  const graph = buildGraph();
  const plannedSkills = graph.nodes.filter(
    n => n.type === 'skill' && n.status === 'planned'
  );

  plannedSkills.forEach(skill => {
    expect(canRockyTeach(skill.id)).toBe(false);
  });
});
```

### 2. Tool-Skill Grounding

> **Every callable tool must be connected to at least one active skill.**

**Test Assertion:**
```ts
it('All callable tools must be connected to at least one active skill', () => {
  const graph = buildGraph();
  const tools = graph.nodes.filter(n => n.type === 'tool');
  
  tools.forEach(tool => {
    const connectedSkills = graph.links.filter(
      l => l.source === tool.id &&
           getNodeById(graph, l.target)?.type === 'skill' &&
           getNodeById(graph, l.target)?.status === 'active'
    );

    expect(connectedSkills.length).toBeGreaterThan(0);
  });
});
```

### 3. Knowledge Base Authority

> **Tools can only use canonical knowledge bases, not inferred or planned knowledge.**

**Test Assertion:**
```ts
it('All knowledge bases referenced by tools must be canonical', () => {
  const graph = buildGraph();
  
  graph.links
    .filter(l => l.type === 'uses')
    .forEach(link => {
      const kb = getNodeById(graph, link.target);
      expect(kb?.metadata.authority).toBe('canonical');
    });
});
```

### 4. Refusal Contract

> **Rocky must refuse requests for capabilities he does not have.**

**Test Assertion:**
```ts
it('Rocky must refuse requests for missing skills', async () => {
  const graph = buildGraph();
  const missingSkills = graph.nodes.filter(
    n => n.type === 'skill' && n.status === 'missing'
  );

  for (const skill of missingSkills.slice(0, 5)) {
    const response = await askRocky(`Teach me ${skill.label}`);
    expect(response).toContain('cannot') || expect(response).toContain('not available');
  }
});
```

### 5. Gap-Driven Tests

> **Gaps identified by the graph must become failing tests.**

**Test Assertion:**
```ts
it('All identified gaps must be addressed or acknowledged', () => {
  const graph = buildGraph();
  const gaps = identifyGaps(graph);
  
  gaps.forEach(gap => {
    if (gap.impact === 'critical') {
      // Critical gaps must be fixed or have explicit workaround
      expect(gap.metadata?.workaround).toBeDefined();
    }
  });
});
```

---

## Contract Categories

### Category 1: Skill Authority

**Purpose:** Ensure Rocky only claims skills he actually has.

**Tests:**
- ✅ Rocky must not claim planned skills
- ✅ Rocky must not claim missing skills
- ✅ Rocky must not claim partial skills as complete
- ✅ Rocky must acknowledge skill limitations

**Implementation:**
```ts
describe('Skill Authority', () => {
  it('Rocky must not claim skills marked planned or missing', () => {
    // Test implementation
  });
  
  it('Rocky must acknowledge partial skills as incomplete', () => {
    // Test implementation
  });
});
```

### Category 2: Tool Authority

**Purpose:** Ensure tools are properly grounded in skills and knowledge.

**Tests:**
- ✅ All tools must connect to active skills
- ✅ Tools must not invoke missing knowledge bases
- ✅ Tool parameters must match declared capabilities
- ✅ Tools must fail gracefully when prerequisites missing

**Implementation:**
```ts
describe('Tool Authority', () => {
  it('All callable tools must be connected to at least one active skill', () => {
    // Test implementation
  });
  
  it('Tools must not reference missing knowledge bases', () => {
    // Test implementation
  });
});
```

### Category 3: Knowledge Base Legitimacy

**Purpose:** Ensure knowledge used by Rocky is canonical and authoritative.

**Tests:**
- ✅ All knowledge bases must be canonical (not inferred)
- ✅ Knowledge bases must have declared scope
- ✅ Knowledge bases must not contradict each other
- ✅ Inferred knowledge must be marked as such

**Implementation:**
```ts
describe('Knowledge Base Legitimacy', () => {
  it('All knowledge bases referenced by tools must be canonical', () => {
    // Test implementation
  });
  
  it('Inferred knowledge must be explicitly marked', () => {
    // Test implementation
  });
});
```

### Category 4: Refusal Contract

**Purpose:** Ensure Rocky refuses requests outside his authority.

**Tests:**
- ✅ Rocky must refuse missing skills
- ✅ Rocky must refuse requests requiring planned capabilities
- ✅ Rocky must refuse requests with invalid parameters
- ✅ Rocky must explain why he refused

**Implementation:**
```ts
describe('Refusal Contract', () => {
  it('Rocky must refuse requests for missing skills', async () => {
    // Test implementation
  });
  
  it('Rocky must explain refusal reasons', async () => {
    // Test implementation
  });
});
```

### Category 5: Gap-Driven Tests

**Purpose:** Turn identified gaps into actionable test failures.

**Tests:**
- ✅ Critical gaps must have workarounds
- ✅ Disconnected tools must be connected or removed
- ✅ Unused knowledge must be integrated or deprecated
- ✅ Planned outputs must have implementation timeline

**Implementation:**
```ts
describe('Gap-Driven Tests', () => {
  it('All critical gaps must have workarounds', () => {
    // Test implementation
  });
  
  it('Disconnected tools must be connected or removed', () => {
    // Test implementation
  });
});
```

---

## Test Execution Model

### Non-Browser Tests

These tests **do not** use Playwright or browser automation. They:

1. Load the Knowledge Graph via `RockyKnowledgeGraphService`
2. Parse tool declarations from `rocky-chat/index.ts`
3. Make assertions about graph structure and authority
4. Run in milliseconds (not minutes)

### Authority Checking Functions

```ts
// Helper functions for authority checking
function canRockyTeach(skillId: string, graph: KnowledgeGraph): boolean {
  const skill = getNodeById(graph, skillId);
  return skill?.status === 'active';
}

function isToolAuthorized(toolId: string, graph: KnowledgeGraph): boolean {
  const tool = getNodeById(graph, toolId);
  const connectedSkills = graph.links.filter(
    l => l.source === toolId &&
         getNodeById(graph, l.target)?.type === 'skill' &&
         getNodeById(graph, l.target)?.status === 'active'
  );
  return connectedSkills.length > 0;
}

function isKnowledgeCanonical(kbId: string, graph: KnowledgeGraph): boolean {
  const kb = getNodeById(graph, kbId);
  return kb?.metadata.authority === 'canonical';
}
```

---

## Integration with Existing Tests

### Current Test Coverage

**Execution Tests (✅ Complete):**
- Score generation works
- Tools execute correctly
- Workflows complete

**Cognitive Tests (❌ Missing):**
- Rocky claims correct capabilities
- Tools are properly grounded
- Knowledge is authoritative
- Refusals are appropriate

### Test Hierarchy

```
tests/
  e2e/                    # Execution tests (existing)
    rocky-*.spec.ts
  
  forensic/               # NEW: Cognitive contract tests
    rocky-cognitive-contract.spec.ts
    rocky-tool-authority.spec.ts
    rocky-refusal.spec.ts
    rocky-knowledge-legitimacy.spec.ts
    rocky-gap-driven.spec.ts
```

---

## Success Criteria

### Phase 1: Authority Tests (MVP)

✅ All tools connected to active skills  
✅ No claims of planned/missing skills  
✅ Knowledge bases marked canonical  
✅ Refusal tests passing  

### Phase 2: Gap Integration

✅ Gaps automatically become tests  
✅ Critical gaps have workarounds  
✅ Disconnected tools identified  

### Phase 3: Runtime Enforcement

✅ Authority checks at runtime  
✅ Refusal messages standardized  
✅ Capability claims validated  

---

## Example Test Output

### Passing Test
```
✓ Skill Authority: Rocky must not claim skills marked planned or missing
  → 0 violations found (all planned skills properly excluded)

✓ Tool Authority: All callable tools must be connected to at least one active skill
  → 50/50 tools properly connected

✓ Knowledge Base Legitimacy: All knowledge bases referenced by tools must be canonical
  → 12/12 knowledge bases canonical
```

### Failing Test
```
✗ Tool Authority: All callable tools must be connected to at least one active skill
  → 3 violations:
     - tool:analyzeImage (no active skill connections)
     - tool:generateProgressionWithAI (only connects to planned skills)
     - tool:matchProgressions (disconnected)
  
  Fix: Connect these tools to active skills or mark as planned
```

---

## Next Steps

1. **Implement Category 1-5 tests** (this spec)
2. **Integrate with CI/CD** (fail builds on contract violations)
3. **Add runtime enforcement** (check authority before tool invocation)
4. **Create gap-to-test automation** (auto-generate tests from gaps)
5. **Build authority dashboard** (visualize contract compliance)

---

**End of Specification**





