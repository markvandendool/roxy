# AI Agent Protocol for MindSong Juke Hub

> **Version:** 2.0.0
> **Status:** MANDATORY COMPLIANCE
> **Applies To:** Claude, Cursor, Copilot, ChatGPT, Custom Agents
> **Last Updated:** 2025-12-10

---

## EXECUTIVE SUMMARY

This document defines the **mandatory protocol** for ALL AI agents working with the MindSong Juke Hub codebase. Compliance is enforced through CI/CD gates and Agent Breakroom monitoring.

---

## THE 10 COMMANDMENTS OF MINDSONG AGENTS

### 1. THOU SHALT READ BEFORE WRITING

**NEVER modify code without first reading:**
- The file you're editing
- Related files in the same directory
- The relevant skill documentation

```typescript
// ❌ FORBIDDEN - Blind editing
await edit('src/audio/Router.ts', changes);

// ✅ CORRECT - Read first
const content = await read('src/audio/Router.ts');
const skill = await mcp.call('get_skill', { skillName: 'apollo-audio' });
await edit('src/audio/Router.ts', informedChanges);
```

### 2. THOU SHALT USE THE SKILLS SYSTEM

**ALWAYS consult skills before any task:**

```typescript
// Before ANY task involving audio:
const skills = await mcp.call('search_skills', {
  query: 'audio routing playback',
  maxResults: 3
});

// Read the most relevant skill
const doc = await mcp.call('get_skill', {
  skillName: skills[0].name,
  section: 'ai-usage'
});
```

### 3. THOU SHALT NEVER VIOLATE MDF2030

The 15 MDF2030 Laws are **INVIOLABLE**:

| Law | Violation Example | Consequence |
|-----|-------------------|-------------|
| Single Time Authority | `performance.now()` | REJECT |
| Flat Event Spine | Nested event structures | REJECT |
| Rails Are Queries | Rail storing events | REJECT |
| Widgets Are Slaves | Widget authority pattern | REJECT |
| All Audio Through Apollo | Direct Tone.js access | REJECT |

### 4. THOU SHALT REGISTER WITH AGENT BREAKROOM

**BEFORE starting any session:**

```typescript
await breakroomClient.registerPresence({
  agentType: 'claude-opus',
  sessionId: uuid(),
  capabilities: ['code', 'research', 'documentation'],
  currentTask: 'Implementing feature X'
});
```

### 5. THOU SHALT POST ACTIVITIES BEFORE WORK

**NEVER start work without announcing:**

```typescript
// Post activity BEFORE starting
await breakroomClient.postActivity({
  type: 'WORKING_ON',
  files: ['src/audio/SmartAudioRouter.ts'],
  description: 'Fixing voice leading integration'
});

// Then do the work
await edit(...);

// Post completion
await breakroomClient.postActivity({
  type: 'COMPLETED',
  files: ['src/audio/SmartAudioRouter.ts'],
  description: 'Voice leading integration fixed'
});
```

### 6. THOU SHALT SHARE DISCOVERIES

**Found something important? Share it:**

```typescript
await breakroomClient.postDiscovery({
  type: 'ARCHITECTURE_INSIGHT',
  payload: {
    finding: 'SmartAudioRouter has hidden P-1 dedup guard',
    files: ['src/services/audio/SmartAudioRouter.ts:34-41'],
    impact: 'HIGH'
  }
});
```

### 7. THOU SHALT USE FILE LOCKS

**For concurrent editing safety:**

```typescript
// Acquire lock before editing shared files
const lock = await fileLockManager.acquire(
  'src/audio/SmartAudioRouter.ts',
  { ttl: 30000, agentId: myAgentId }
);

try {
  await edit(...);
} finally {
  await fileLockManager.release(lock);
}
```

### 8. THOU SHALT NEVER CREATE DUPLICATE SYSTEMS

**Check existing before creating:**

| Need | Check First | Use Existing |
|------|-------------|--------------|
| Audio routing | apollo-audio skill | SmartAudioRouter |
| State management | quantum-rails skill | EventSpine |
| Widget system | widget-architecture skill | Theater/Olympus |
| Progress tracking | epic-tracker skill | master-progress.json |
| Time authority | khronos-timing skill | KhronosClock |

### 9. THOU SHALT RUN VALIDATION

**Before any PR:**

```bash
# Run all validations
node scripts/skills/validate-frontmatter.mjs
node scripts/skills/validate-line-counts.mjs
node scripts/skills/generate-quality-report.mjs

# Check for regressions
npm run test:unit
npm run test:e2e

# Verify no MDF2030 violations
grep -r "performance.now()" src/ # Should be 0
grep -r "tempoAuthority.*true" src/ # Should be 0
```

### 10. THOU SHALT DOCUMENT LEARNINGS

**Update skills when you learn something:**

```typescript
// If you discover something not in the skill docs:
await breakroomClient.postDiscovery({
  type: 'DOCUMENTATION_GAP',
  payload: {
    skillName: 'apollo-audio',
    missingInfo: 'Backend priority order not documented',
    suggestedAddition: 'Add backend priority table'
  }
});
```

---

## AGENT TYPE SPECIFIC PROTOCOLS

### Claude Protocol

```typescript
// Claude-specific initialization
const claude = {
  // Always use MCP for skill access
  async getContext(task) {
    const skills = await mcp.call('search_skills', { query: task });
    return skills.map(s => mcp.call('get_skill', { skillName: s.name }));
  },

  // Use reasoning patterns from AI Usage Guidance
  async planTask(task) {
    const skill = await mcp.call('get_skill', {
      skillName: relevantSkill,
      section: 'ai-usage'
    });
    return parseReasoningPatterns(skill.content);
  },

  // Never bypass Apollo
  audioConstraint: 'ALL_AUDIO_THROUGH_APOLLO',

  // Never create widget authorities
  widgetConstraint: 'WIDGETS_ARE_SLAVES'
};
```

### Cursor Protocol

```typescript
// Cursor-specific initialization
const cursor = {
  // Inline skill suggestions
  async suggestFromSkills(context) {
    const query = extractKeywords(context);
    return mcp.call('search_skills', { query, maxResults: 3 });
  },

  // Auto-check MDF2030 compliance
  async validateEdit(changes) {
    const violations = checkMDF2030Compliance(changes);
    if (violations.length > 0) {
      return { blocked: true, reason: violations };
    }
    return { blocked: false };
  },

  // File modification patterns from skills
  async getModificationGuide(file) {
    const skill = findSkillForFile(file);
    return mcp.call('get_skill', {
      skillName: skill,
      section: 'patterns'
    });
  }
};
```

### Copilot Protocol

```typescript
// Copilot-specific initialization
const copilot = {
  // Context-aware completions using skills
  async getCompletionContext(cursor) {
    const file = cursor.currentFile;
    const skill = findSkillForFile(file);
    const patterns = await mcp.call('get_skill', {
      skillName: skill,
      section: 'patterns'
    });
    return { patterns, constraints: getMDF2030Constraints() };
  },

  // Block forbidden patterns
  blockedPatterns: [
    'new AudioContext',
    'Tone.Transport',
    'tempoAuthority: true',
    'harmonicAuthority: true',
    'performance.now()'
  ]
};
```

### ChatGPT Protocol

```typescript
// ChatGPT-specific initialization
const chatgpt = {
  // Always ground responses in skills
  async groundResponse(query) {
    const skills = await mcp.call('search_skills', { query });
    const docs = await Promise.all(
      skills.map(s => mcp.call('get_skill', { skillName: s.name }))
    );
    return { groundingSources: docs };
  },

  // No code modifications without skill consultation
  requiresSkillCheck: true,

  // Read-only by default
  canModifyCode: false,
  canSuggestModifications: true
};
```

---

## SESSION LIFECYCLE

### 1. Initialization

```typescript
async function initializeAgentSession(agentType) {
  // 1. Register with Breakroom
  await breakroomClient.registerPresence({
    agentType,
    sessionId: uuid(),
    startTime: Date.now()
  });

  // 2. Load skill index
  const index = await mcp.call('get_skill_index');

  // 3. Cache commonly needed skills
  const coreSkills = ['mdf2030-master', 'widget-architecture', 'apollo-audio'];
  await Promise.all(coreSkills.map(s =>
    mcp.call('get_skill', { skillName: s })
  ));

  // 4. Check for any active locks on files
  const locks = await fileLockManager.listActive();

  return { index, locks };
}
```

### 2. Task Execution

```typescript
async function executeTask(task) {
  // 1. Find relevant skills
  const skills = await mcp.call('search_skills', {
    query: task.description,
    maxResults: 5
  });

  // 2. Post activity
  await breakroomClient.postActivity({
    type: 'STARTING_TASK',
    taskId: task.id,
    skills: skills.map(s => s.name)
  });

  // 3. Get AI usage guidance
  const guidance = await Promise.all(skills.map(s =>
    mcp.call('get_skill', { skillName: s.name, section: 'ai-usage' })
  ));

  // 4. Execute with constraints
  const result = await executeWithConstraints(task, guidance);

  // 5. Validate output
  const validation = await validateOutput(result);

  // 6. Post completion
  await breakroomClient.postActivity({
    type: 'COMPLETED_TASK',
    taskId: task.id,
    validation
  });

  return result;
}
```

### 3. Termination

```typescript
async function terminateAgentSession() {
  // 1. Release all locks
  await fileLockManager.releaseAll(myAgentId);

  // 2. Post session summary
  await breakroomClient.postActivity({
    type: 'SESSION_END',
    summary: {
      tasksCompleted: completedTasks.length,
      filesModified: modifiedFiles,
      discoveriesShared: discoveries.length
    }
  });

  // 3. Deregister presence
  await breakroomClient.deregisterPresence(sessionId);
}
```

---

## ERROR HANDLING

### MDF2030 Violation Detected

```typescript
if (mdf2030ViolationDetected) {
  // 1. DO NOT proceed with the change
  // 2. Log the violation
  await breakroomClient.postDiscovery({
    type: 'MDF2030_VIOLATION_ATTEMPTED',
    payload: {
      law: violatedLaw,
      code: attemptedCode,
      file: targetFile
    }
  });

  // 3. Consult skill for correct pattern
  const correctPattern = await mcp.call('get_skill', {
    skillName: 'mdf2030-master',
    section: 'patterns'
  });

  // 4. Return guidance
  return {
    blocked: true,
    reason: `MDF2030 Law ${violatedLaw} violated`,
    correctApproach: correctPattern
  };
}
```

### Skill Not Found

```typescript
if (!skillFound) {
  // 1. Search with broader terms
  const broader = await mcp.call('search_skills', {
    query: expandQuery(originalQuery),
    maxResults: 10
  });

  // 2. If still not found, check dependency graph
  const graph = await mcp.call('get_skill_graph', {
    skillName: nearestSkill,
    depth: 3
  });

  // 3. Post discovery about missing coverage
  await breakroomClient.postDiscovery({
    type: 'SKILL_COVERAGE_GAP',
    payload: {
      query: originalQuery,
      suggestedSkill: analyzedSuggestion
    }
  });
}
```

### File Lock Conflict

```typescript
if (fileLockConflict) {
  // 1. Check who has the lock
  const lockHolder = await fileLockManager.getLockHolder(file);

  // 2. If lock is stale (>TTL), request release
  if (lockHolder.age > lockHolder.ttl) {
    await fileLockManager.forceRelease(file, 'STALE_LOCK');
  } else {
    // 3. Wait or work on different file
    await waitForLockRelease(file, { maxWait: 30000 });
  }
}
```

---

## QUALITY GATES

### Pre-Commit Checks

| Check | Threshold | Action |
|-------|-----------|--------|
| MDF2030 Violations | 0 | Block commit |
| TypeScript Errors | 0 | Block commit |
| Unit Test Failures | 0 | Block commit |
| Skill Quality Score | ≥8.0 | Block commit |

### Pre-PR Checks

| Check | Threshold | Action |
|-------|-----------|--------|
| E2E Test Failures | 0 | Block PR |
| Coverage Regression | >1% drop | Block PR |
| Performance Regression | >10% | Block PR |
| Skill Validation | Pass | Block PR |

### Continuous Monitoring

| Metric | Alert Threshold | Action |
|--------|-----------------|--------|
| Retrieval Precision@5 | <0.85 | Investigate |
| Embedding Drift | >5% | Regenerate |
| Skill Score Drop | >0.5 | Review |
| Agent Conflict Rate | >10% | Lock review |

---

## COMPLIANCE VERIFICATION

```bash
# Run full compliance check
node scripts/agent-compliance-check.mjs

# Expected output:
# ✅ MDF2030 Laws: 15/15 compliant
# ✅ Skill Coverage: 33/33 skills (100%)
# ✅ Agent Protocol: All 10 commandments verified
# ✅ Quality Gates: All passing
# ✅ Breakroom Integration: Active
#
# COMPLIANCE SCORE: 100%
```

---

## APPENDIX: FORBIDDEN PATTERNS

### Code Patterns (Will Be Rejected)

```typescript
// ❌ FORBIDDEN - Direct time access
const tick = performance.now();
const tick = Date.now();

// ❌ FORBIDDEN - Direct audio context
new AudioContext();
Tone.Transport.start();
Tone.Synth.triggerAttackRelease();

// ❌ FORBIDDEN - Widget authority
tempoAuthority: true
harmonicAuthority: true
keyAuthority: true
analysisAuthority: true
voicingAuthority: true

// ❌ FORBIDDEN - Widget-to-widget communication
widget1.emit('chord', data);
widget2.on('chord', handler);

// ❌ FORBIDDEN - Widget owning state
const [currentChord, setCurrentChord] = useState();

// ❌ FORBIDDEN - Parallel systems
class MyNewWidgetSystem { }
class MyNewAudioRouter { }
class MyNewStateManager { }
```

### File Patterns (Require Special Approval)

```
❌ src/services/[new-service]/*.ts - No new services without approval
❌ src/audio/[new-router]/*.ts - No new audio systems
❌ src/store/[new-store].ts - No new state stores
❌ releaseplan/*.json - Never edit directly
```

---

## APPENDIX: CORRECT PATTERNS

### Audio Routing

```typescript
// ✅ CORRECT - Use Apollo
window.Apollo?.playNote(note, velocity);
window.Apollo?.playChord(chord, options);

// ✅ CORRECT - Use SmartAudioRouter
import { useAudioRouter } from '@/hooks/audio/useAudioRouter';
const { playNote, playChord } = useAudioRouter();
```

### Time Access

```typescript
// ✅ CORRECT - Use ClockSync
import { ClockSyncService } from '@/services/ClockSyncService';
const tick = ClockSyncService.instance.getAuthoritativeTick();

// ✅ CORRECT - Use Khronos hook
import { useKhronosTick } from '@/hooks/useKhronosTick';
const tick = useKhronosTick();
```

### Widget State

```typescript
// ✅ CORRECT - Subscribe to EventSpine
import { useEventSpineActiveChord } from '@/hooks/useEventSpine';
const activeChord = useEventSpineActiveChord();

// ✅ CORRECT - User input flows to Brain
const handleUserClick = (note) => {
  Brain.processUserInput(note); // Brain updates EventSpine
};
```

---

**This protocol is MANDATORY for all AI agents. Violations will be detected and blocked automatically.**

**Generated by Claude Skills System v2.0**
