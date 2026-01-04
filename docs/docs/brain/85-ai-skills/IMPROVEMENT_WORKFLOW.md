# Skill Improvement Workflow
**Purpose:** Guide to how skills continuously improve and how to manually enhance them  
**Status:** ✅ Active  
**Last Updated:** 2025-01-11

---

## How Skills Auto-Refine

Skills automatically improve through four automation engines:

### 1. Repo Diff Scanner
**Location:** `.claude/automation/repo-diff-scanner.mts`

**What It Does:**
- Scans repository changes (git diff)
- Detects new domains, patterns, technologies
- Identifies files that indicate skill updates needed
- Suggests trigger phrase additions
- Detects cross-cutting patterns

**When It Runs:**
- On repository changes
- Before context refresh
- During skill refinement

**Output:** Domain detection report with suggested skill updates

---

### 2. Skill Refinement Engine
**Location:** `.claude/automation/skill-refinement-engine.mts`

**What It Does:**
- Analyzes diff scanner results
- Updates skill files automatically
- Adds new trigger phrases
- Updates skill content
- Creates new skills for new domains

**When It Runs:**
- After repo diff scan
- On skill update trigger
- During automated refinement cycle

**Output:** Updated skill files, new skills created

---

### 3. Context Refresh
**Location:** `.claude/automation/context-refresh.mts`

**What It Does:**
- Updates CLAUDE.md based on repo changes
- Refreshes skill context
- Updates domain sections
- Adds new critical files
- Updates quick commands

**When It Runs:**
- After significant changes
- On context refresh trigger
- During skill refinement

**Output:** Updated CLAUDE.md, refreshed context

---

### 4. Excellence Tracking
**Location:** `.claude/excellence/benchmark-tracker.mts`

**What It Does:**
- Tracks skill performance over time
- Monitors excellence metrics
- Detects skill drift
- Identifies improvement opportunities
- Maintains historical benchmarks

**When It Runs:**
- After excellence audits
- During performance tracking
- On benchmark updates

**Output:** Performance history, trend analysis, recommendations

---

## Repo Diff Scanner Integration

### How It Detects Changes

**Domain Detection:**
- Scans file paths for domain indicators
- Analyzes file content for patterns
- Detects new technologies
- Identifies skill-relevant changes

**Pattern Detection:**
- Event bus patterns
- Service patterns
- Hook patterns
- Registry patterns
- Bridge patterns

**Example Detection:**
```
New files detected:
- src/services/newAudioEngine.ts
- src/services/audio/NewScheduler.ts

Domain: audio-engine
Confidence: 95%
Suggested: Update apollo-audio skill
```

---

## Skill Refinement Process

### Automatic Updates

**Trigger Phrases:**
- New keywords detected → Add to triggers
- Missing triggers → Suggest additions
- Unused triggers → Flag for removal

**Content Updates:**
- New critical files → Add to skill file
- New patterns → Add to PATTERNS.md
- New issues → Add to TROUBLESHOOTING.md

**New Skills:**
- New domain detected → Generate skill template
- Missing coverage → Create new skill
- Domain split → Separate skills

---

## Context Refresh Process

### CLAUDE.md Updates

**Sections Updated:**
- Key Domains (new domains added)
- Critical Files (new files added)
- Testing (new test patterns)
- Quick Commands (new commands)

**Skill Context:**
- Skill descriptions refreshed
- Trigger phrases updated
- Related docs linked

---

## How to Manually Improve Skills

### Step 1: Identify Improvement Need
- Skill doesn't activate when it should
- Skill provides outdated information
- Skill missing new patterns
- Skill doesn't know about new features

### Step 2: Update Skill File
**Location:** `.claude/skills/[skill-name]/SKILL.md`

**What to Update:**
- Add new trigger phrases
- Update critical files list
- Add new patterns
- Update examples
- Fix outdated information

### Step 3: Update Brain Docs
**Location:** `.claude/skills/[skill-name]/README.md` (source of truth)

**Files to Update:**
- `SKILL_GUIDE.md` - Add new knowledge
- `PATTERNS.md` - Add new patterns
- `TROUBLESHOOTING.md` - Add new issues

### Step 4: Test Improvement
```bash
/skill-diagnostics
```

**Verify:**
- Skill activates correctly
- New knowledge appears
- Patterns recognized

### Step 5: Post to Breakroom
```bash
node scripts/agent-breakroom/post-activity.mjs discovery_posted "Improved apollo-audio skill with new patterns" --category architecture
```

---

## Excellence Metrics Tracking

### Performance History

**Tracked Metrics:**
- Skill activation rate
- Context loading success
- Response accuracy
- Pattern recognition
- Excellence audit scores

**Trend Analysis:**
- Improving (scores increasing)
- Stable (scores consistent)
- Declining (scores decreasing)

**Streak Detection:**
- Consecutive improvements
- Consistent performance
- Decline patterns

---

## Benchmark History

### Historical Data

**Stored:**
- Excellence audit results
- Skill performance metrics
- Improvement suggestions
- Critical metric status

**Used For:**
- Trend analysis
- Improvement recommendations
- Performance baselines
- Regression detection

---

## Improvement Recommendations

### From Excellence Framework

**Category-Specific:**
- Code Intelligence → Improve TypeScript patterns
- Domain Expertise → Enhance domain knowledge
- Task Execution → Optimize efficiency
- Self-Improvement → Better auto-refinement

**Critical Metrics:**
- Must maintain 100% on critical metrics
- Focus improvements on failing metrics
- Track progress over time

---

## Manual Improvement Workflow

### 1. Run Excellence Audit
```
/excellence-audit
```

**Identify:**
- Low-scoring categories
- Missing knowledge
- Pattern gaps

### 2. Analyze Results
- Review improvement opportunities
- Identify skill gaps
- Plan updates

### 3. Update Skills
- Modify skill files
- Update brain docs
- Add new patterns

### 4. Test Changes
```
/skill-diagnostics
/enable-skill-telemetry
```

### 5. Re-Audit
```
/excellence-audit
```

**Compare:**
- Before vs after scores
- Improvement trends
- Critical metrics status

### 6. Share Improvements
- Post to Breakroom
- Update documentation
- Track in benchmark history

---

## Automation Triggers

### When Auto-Refinement Runs

**Triggers:**
- Git commit with significant changes
- New files in skill-relevant directories
- Pattern changes detected
- Manual trigger via script

**Frequency:**
- Daily automated scan
- On-demand via script
- Before context refresh

---

## Integration with Breakroom

### Discovery Sharing

**Post Improvements:**
```typescript
postDiscovery({
  title: 'Improved apollo-audio skill',
  content: 'Added new patterns for audio scheduling',
  category: 'architecture'
});
```

**Share Metrics:**
- Excellence audit results
- Skill performance trends
- Improvement suggestions

---

## Best Practices

### Do
- ✅ Update skills when adding features
- ✅ Post improvements to Breakroom
- ✅ Test skill changes
- ✅ Track in excellence framework
- ✅ Update brain docs with skills

### Don't
- ❌ Modify skills without testing
- ❌ Remove trigger phrases without checking
- ❌ Skip Breakroom posting
- ❌ Ignore excellence metrics

---

## Reference

**Engines:**
- Repo Diff Scanner: `.claude/automation/repo-diff-scanner.mts`
- Skill Refinement: `.claude/automation/skill-refinement-engine.mts`
- Context Refresh: `.claude/automation/context-refresh.mts`
- Benchmark Tracker: `.claude/excellence/benchmark-tracker.mts`

**Commands:**
- `/excellence-audit` - Track improvements
- `/skill-diagnostics` - Test skills
- `/enable-skill-telemetry` - Monitor activations

---

**Status:** ✅ Active  
**Maintained By:** Claude Skills System  
**Related:** `EXCELLENCE_DASHBOARD.md`, `EXCELLENCE_FRAMEWORK.md`


