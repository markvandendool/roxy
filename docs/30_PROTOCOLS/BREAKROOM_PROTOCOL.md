# Breakroom Protocol

**Last Updated:** 2026-03-20 | **Status:** Active

The breakroom is ROXY's agent coordination system. It prevents conflicts, tracks work, and maintains institutional memory.

---

## Location

```
~/.roxy/.breakroom/
```

---

## Core Principle

> **Post intentions BEFORE work, summaries AFTER work.**

This ensures:
- No two agents work on the same files simultaneously
- Work history is preserved for future agents
- Handoffs are seamless

---

## Daily Activity Log

### File Naming

```
activity_YYYYMMDD.md
```

Example: `activity_20260320.md`

### File Structure

```markdown
# Breakroom Activity - YYYY-MM-DD

## Session: [Brief Description]

### Intentions
- [ ] Task 1 I plan to do
- [ ] Task 2 I plan to do

### Files I May Touch
- path/to/file1
- path/to/file2

---
*Agent: [Name] | Session: [Type] | Started: HH:MM*
```

---

## Session Types

| Type | Use Case |
|------|----------|
| `Infrastructure` | System setup, configuration, environment |
| `Feature` | New functionality development |
| `Bugfix` | Error correction, debugging |
| `Documentation` | Docs, guides, READMEs |
| `Maintenance` | Cleanup, refactoring, optimization |
| `Investigation` | Research, analysis, exploration |

---

## Workflow

### 1. Before Starting Work

1. Check existing `activity_YYYYMMDD.md` for current day
2. Review any in-progress work from other agents
3. Append your session intention block
4. Claim files you'll modify

```markdown
## Session: Fix streaming transport errors

### Intentions
- [ ] Fix JSON 400/403 errors in roxy_core.py
- [ ] Add proper error handling for HTML responses

### Files I May Touch
- ~/.roxy/roxy_core.py (lines 3070-3100)
- ~/.roxy/tests/test_streaming.py

---
*Agent: Claude Code | Session: Bugfix | Started: 14:30*
```

### 2. During Work

If scope changes significantly, update intentions:

```markdown
### Scope Change (15:00)
- Adding qualification_pipeline.py to files touched
- New task: implement 5-stage gate
```

### 3. After Completing Work

Update the same session block:

```markdown
## Session: Fix streaming transport errors

### Intentions
- [x] Fix JSON 400/403 errors in roxy_core.py
- [x] Add proper error handling for HTML responses

### Files I May Touch
- ~/.roxy/roxy_core.py (lines 3070-3100)
- ~/.roxy/tests/test_streaming.py

### Accomplishments
1. **Fixed streaming transport** - JSON 400/403 errors instead of HTML
2. **Added error handling** - Proper fallback for non-JSON responses
3. **Created tests** - 5 new test cases for error conditions

### Files Modified
- `~/.roxy/roxy_core.py:3070,3092` - Error response handling
- `~/.roxy/tests/test_streaming.py` - New test file

### Issues Encountered
- None

### Next Steps (for future agent)
- Consider adding retry logic for transient errors

---
*Agent: Claude Code | Session: Bugfix | Started: 14:30 | Completed: 16:45*
```

---

## Conflict Avoidance

### Before Touching a File

1. `grep -r "filename" ~/.roxy/.breakroom/activity_$(date +%Y%m%d).md`
2. If another agent listed the file, coordinate or wait
3. If unclear, check if modifications are in different regions

### File Lock Convention

For critical operations, add explicit lock:

```markdown
### LOCK: ~/.roxy/roxy_core.py
Estimated duration: 30 minutes
Reason: Major refactoring
---
```

Release lock when done:

```markdown
### UNLOCK: ~/.roxy/roxy_core.py
Released at: 15:30
---
```

---

## Handoff Protocol

When stopping mid-work:

```markdown
### HANDOFF REQUIRED

**Current State:**
- Task 60% complete
- Blocked on: [reason]

**What's Done:**
1. Item 1
2. Item 2

**What Remains:**
1. Remaining item 1
2. Remaining item 2

**Critical Context:**
- Important note 1
- Important note 2

**Files in Uncertain State:**
- path/to/file (partial changes, DO NOT DEPLOY)

---
*Agent: Claude Code | HANDOFF | 17:00*
```

---

## Templates

### Quick Session Start

```markdown
## Session: [Description]
### Intentions
- [ ] Task

### Files
- file/path

---
*Agent: [Name] | Session: [Type] | Started: HH:MM*
```

### Quick Session End

```markdown
### Accomplishments
1. Done item

### Files Modified
- `file/path` - change description

---
*Agent: [Name] | Completed: HH:MM*
```

---

## Examples from History

### Example 1: OBS WebSocket Session (2026-01-20)

```markdown
# Breakroom Activity - 2026-01-20

## Session: OBS WebSocket Control & PipeWire Fix

### Accomplishments
1. **Fixed PipeWire crash** - Audio system was down 14+ hours
2. **Fixed OBS profile** - Duplicate `[AdvOut]` section
3. **OBS WebSocket operational** - Port 4455, password auth
4. **Created 7 scenes** - HDMI-1 through HDMI-4, Quad-View
5. **Created `obs-control.py`** - CLI script for OBS control
6. **Created `OBS_CONTROL_GUIDE.md`** - Engineering reference

### Key Files
- `~/.roxy/obs-control.py`
- `~/.roxy/docs/OBS_CONTROL_GUIDE.md`

---
*Agent: Claude Code | Session: Infrastructure*
```

### Example 2: Theater Integration (2026-01-11)

```markdown
## Session: Master Chief Theater Integration

### Accomplishments
1. Created MASTER_CHIEF_RENDERUNIT_SPEC.md
2. Integrated NDI sources with OBS
3. Configured 4 HDMI capture paths
4. Documented full theater architecture

### Files Modified
- `~/.roxy/.breakroom/20260111_MASTER_CHIEF_RENDERUNIT_SPEC.md`

---
*Agent: Claude Code | Session: Infrastructure | Completed: 15:25*
```

---

## Best Practices

1. **Be specific** - "Fix auth" is worse than "Fix token validation in /stream endpoint"
2. **Include line numbers** - `roxy_core.py:3070-3092` helps future agents
3. **Timestamp everything** - Especially start/end times
4. **Note blockers immediately** - Don't wait until session end
5. **Link related sessions** - Reference prior work if continuing

---

## Quick Reference

```
╔═══════════════════════════════════════════════════════════════╗
║                  BREAKROOM QUICK REFERENCE                    ║
╠═══════════════════════════════════════════════════════════════╣
║ Location:   ~/.roxy/.breakroom/                               ║
║ Today's:    activity_$(date +%Y%m%d).md                       ║
║ Before:     Post intentions + files                           ║
║ After:      Post accomplishments + modified files             ║
║ Handoff:    Use HANDOFF block if stopping mid-work            ║
║ Conflict:   Check file claims before touching                 ║
╚═══════════════════════════════════════════════════════════════╝
```

---

*This protocol is mandatory for all agents working in the ROXY system.*
