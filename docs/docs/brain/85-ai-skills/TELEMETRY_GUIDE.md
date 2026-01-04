# Skill Telemetry Guide
**Purpose:** How to use telemetry to understand skill activations and AI behavior  
**Status:** ✅ Active  
**Last Updated:** 2025-01-11

---

## What is Skill Telemetry?

Skill Telemetry provides **transparent visibility** into which Claude skills activate, why they activate, and how they contribute to responses. This helps you understand Claude's reasoning process and verify skills are working correctly.

---

## Enabling Telemetry

### Enable
```
/enable-skill-telemetry
```

### Disable
```
/disable-skill-telemetry
```

**Default:** Disabled (clean responses)

---

## Telemetry Output Format

When enabled, responses include a `[Skill Telemetry]` block:

```
[Skill Telemetry]
- Activated Skills: apollo-audio, music-theory
- Context Sources: CLAUDE.md(✓), APOLLO_RULE.md(✓)
- Trigger Phrases: "audio playback", "chord progression"
- Response Time: 1.2s
- Token Usage: 1,234 tokens
- Tool Calls: 3 (read_file, grep, search_replace)
```

---

## Understanding Telemetry Data

### Activated Skills
Shows which domain skills fired for your query:
- `apollo-audio` - Audio-related question
- `olympus-3d` - 3D rendering question
- `music-theory` - Music theory question
- `playwright-testing` - Testing question
- `midi-hardware` - MIDI question
- `agent-breakroom` - Coordination question

**Multiple skills** can activate for complex queries.

### Context Sources
Shows which documentation files were loaded:
- `CLAUDE.md(✓)` - Core context loaded
- `APOLLO_RULE.md(✓)` - Rule document loaded
- `docs/brain/...` - Brain docs referenced

**Missing context** shows as `(✗)` - indicates potential knowledge gap.

### Trigger Phrases
Shows which keywords/phrases caused skill activation:
- Helps understand skill sensitivity
- Useful for refining triggers
- Identifies false positives

### Response Metrics
- **Response Time** - How long Claude took to respond
- **Token Usage** - Tokens consumed
- **Tool Calls** - Number and types of tools used

---

## Use Cases

### 1. Verify Skill Activation
**Question:** "How does Apollo routing work?"

**Expected Telemetry:**
```
- Activated Skills: apollo-audio
- Trigger Phrases: "apollo", "routing"
```

**If missing:** Skill may not be configured correctly.

### 2. Debug Missing Knowledge
**Question:** "How do I use InstancedMesh?"

**Telemetry:**
```
- Activated Skills: olympus-3d
- Context Sources: CLAUDE.md(✓), docs/brain/40-patterns/INSTANCED_RENDERING.md(✗)
```

**If context missing:** Documentation may not be indexed or skill needs update.

### 3. Understand Multi-Skill Queries
**Question:** "Fix audio playback in the piano widget"

**Telemetry:**
```
- Activated Skills: apollo-audio, olympus-3d
- Trigger Phrases: "audio playback", "piano widget"
```

**Shows:** Multiple domains involved, both skills activated.

### 4. Performance Monitoring
Track over time:
- Response times
- Token efficiency
- Tool call patterns
- Skill activation frequency

---

## Telemetry Configuration

**Location:** `.claude/telemetry/telemetry-config.json`

**Settings:**
- `enabled` - Global telemetry toggle
- `outputMode` - inline | separate | minimal
- `verbosity` - standard | detailed | minimal
- `tracking` - What to track (skills, context, triggers, metrics)

---

## Best Practices

### When to Enable
- **Debugging** - Understanding why skills don't activate
- **Learning** - Understanding skill behavior
- **Optimization** - Identifying performance issues
- **Verification** - Confirming skills work

### When to Disable
- **Production** - Clean responses for users
- **Simple Tasks** - No need for metadata
- **Performance** - Minimal overhead

### Regular Audits
- Enable telemetry periodically
- Review activation patterns
- Identify skill improvements needed
- Share insights with Breakroom

---

## Integration with Excellence Framework

Telemetry data feeds into:
- **H2. Monitoring & Telemetry** metrics
- **H3. Skill Evolution** tracking
- **Benchmark Tracker** historical data

Run `/excellence-audit improvement` to see telemetry metrics.

---

## Troubleshooting

### Skills Not Activating
1. Check trigger phrases in skill definition
2. Verify skill file exists in `.claude/skills/`
3. Run `/skill-diagnostics` to test
4. Check telemetry for context loading issues

### Too Much Telemetry
- Adjust `verbosity` in config
- Use `outputMode: minimal`
- Disable specific tracking options

### Missing Context
- Check if docs exist
- Verify Doc Brain MCP indexing
- Review context refresh logs

---

## Examples

### Example 1: Simple Query
**Query:** "What is Apollo?"

**Telemetry:**
```
[Skill Telemetry]
- Activated Skills: apollo-audio
- Context Sources: CLAUDE.md(✓)
- Trigger Phrases: "apollo"
- Response Time: 0.8s
```

### Example 2: Complex Query
**Query:** "Debug why piano rendering is slow and audio playback fails"

**Telemetry:**
```
[Skill Telemetry]
- Activated Skills: olympus-3d, apollo-audio
- Context Sources: CLAUDE.md(✓), docs/brain/40-patterns/INSTANCED_RENDERING.md(✓)
- Trigger Phrases: "piano rendering", "audio playback"
- Response Time: 2.1s
- Tool Calls: 5 (read_file, grep, codebase_search, read_lints, run_terminal_cmd)
```

### Example 3: No Skill Activation
**Query:** "What time is it?"

**Telemetry:**
```
[Skill Telemetry]
- Activated Skills: (none)
- Context Sources: CLAUDE.md(✓)
- Trigger Phrases: (none)
- Response Time: 0.3s
```

**Interpretation:** No domain-specific skills needed for general query.

---

## Advanced Usage

### Custom Telemetry
Modify `.claude/telemetry/telemetry-config.json` to:
- Track additional metrics
- Change output format
- Filter specific skills
- Add custom tags

### Telemetry Analysis
Use telemetry data to:
- Identify most-used skills
- Find skill gaps
- Optimize trigger phrases
- Improve context loading

---

## Reference

**Config:** `.claude/telemetry/telemetry-config.json`  
**Engine:** `.claude/telemetry/telemetry-engine.mts`  
**Commands:** `/enable-skill-telemetry`, `/disable-skill-telemetry`

---

**Status:** ✅ Active  
**Maintained By:** Claude Skills System  
**Related:** `COMMANDS_REFERENCE.md`, `SKILLS_OVERVIEW.md`




























