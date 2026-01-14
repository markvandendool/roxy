# GOLDEN ERA ROOT CAUSE REPORT

**Date**: 2026-01-12
**Auditor**: Claude Opus 4.5
**Classification**: Definitive Engineering Analysis
**Directive**: AGENT DIRECTIVE — GOLDEN ERA RESTORATION INVESTIGATION

---

## EXECUTIVE VERDICT

**ROXY's regression is NOT a single bug but a STRUCTURAL ARCHITECTURAL MISMATCH.**

The `/run` endpoint (roxy_commands.py) was born as a **shallow command dispatcher** on Jan 4, 2026 (commit 584c83d) and NEVER received the cognitive integrations that were progressively added to `/stream` (streaming.py).

| Symptom | Root Cause |
|---------|------------|
| "Can't tell the time" | TruthPacket never integrated into `/run` |
| "Misroutes 'push headings' as git push" | Dumb keyword matching in route_command() |
| "Block of wood personality" | `/run` uses PromptTemplates (2-4 sentences), `/stream` uses get_system_prompt_header() (rich identity) |
| "model_used: null" | Model info never captured from llm_router response |
| "No web/browser" | Explicitly disabled at roxy_commands.py:222 |
| "No learning" | All 6 learning modules exist in LEGACY but never wired |
| "No autonomous agents" | All 7 agent modules exist in LEGACY but never wired |

---

## EVIDENCE INDEX

### E1: Runtime Path Verification (PASSED)
```
systemctl cat roxy-core.service:
  ExecStart=/home/mark/.roxy/venv/bin/python /home/mark/.roxy/roxy_core.py
  WorkingDirectory=/home/mark/.roxy

All module __file__ paths: /home/mark/.roxy/*
```
**Verdict**: Runtime path is CORRECT. Not a path misconfiguration.

### E2: Capability Gating
| Capability | Status | Evidence |
|------------|--------|----------|
| Network egress | WORKING | curl http://127.0.0.1:11435 -> OK |
| DNS | WORKING | getent hosts github.com -> resolved |
| Git | AVAILABLE | git status -> works |
| Web/Browser | **DISABLED** | roxy_commands.py:222: `if any(cmd in text_lower for cmd in ["browse", "search web", "open url"])` returns "Web browsing not available" |

### E3: Router Regression - DUMB KEYWORD MATCHING
**File**: `/home/mark/.roxy/roxy_commands.py` lines 153-164

```python
# THE PROBLEM: Keyword matching without intent
git_keywords = ["git", "commit", "push", "pull", "diff", "checkout", "branch", "merge"]
if any(w in words for w in git_keywords):
    # ...
    if "push" in text_lower:
        return ("git", ["push"])  # HIJACKS "list the 10 most recent push headings"
```

**Test Matrix**:
| Input | Expected Route | Actual Route | Status |
|-------|---------------|--------------|--------|
| "what time is it" | time_direct/TruthPacket | rag | FAIL |
| "list the 10 most recent push headings" | rag | git push | FAIL |
| "explain the streaming architecture" | rag | obs | FAIL |
| "system status" | system | system | PASS |

### E4: Prompt/Template Regression - TWO CODEPATHS
| Endpoint | Identity Loading | Personality |
|----------|------------------|-------------|
| `/stream` | `get_system_prompt_header()` + TruthPacket | Full ROXY persona |
| `/run` | `PromptTemplates.select_prompt()` | "Be concise (2-4 sentences)" |

**streaming.py line 272**:
```python
system_header = get_system_prompt_header()  # Rich identity
```

**roxy_commands.py line 797**:
```python
prompt = PromptTemplates.select_prompt(query, full_context, task_type="rag")  # Basic template
```

### E5: Memory Continuity
| Component | Status | Evidence |
|-----------|--------|----------|
| PostgreSQL memories | 645 stored | SELECT count(*) FROM conversation_memory |
| recall_conversations() | WIRED | roxy_commands.py:771 |
| Memory in prompts | INJECTED | lines 779-786 build memory_section |
| response_time | 0.001s | Suspiciously fast - possible cache hit |

**Verdict**: Memory IS wired but aggressive caching may bypass LLM entirely.

### E6: Autonomous Agents - ZERO INTEGRATION
**Current roxy_commands.py**: 0 references to autonomous/agent/proactive/planning/decision

**Legacy /opt/roxy/services.LEGACY.20260101_200448/autonomous/**:
```
collaboration.py      decision_making.py   planning.py
problem_detection.py  resource_optimizer.py  response_system.py
error_learning.py (7 modules total)
```

**Verdict**: Complete loss. Modules exist but are NOT imported or called.

### E7: Regression Commits
| Commit | Date | Significance |
|--------|------|--------------|
| 584c83d | Jan 4 | "ROXY Full Stack" - birth of roxy_commands.py (shallow) |
| 9e86ee0 | Jan 10 | TruthPacket added to streaming.py ONLY |
| e7056af | Recent | "fix(routing): prevent false command classification" - didn't fix keyword problem |
| 02d6375 | Recent | "fix(time): DETERMINISTIC time queries" - attempted but incomplete |

**Last Known Good**: There was no "good" state - `/run` was born broken.

---

## ROOT CAUSE BREAKDOWN

### RC1: TruthPacket Never Reached /run (CRITICAL)
- **File**: `/home/mark/.roxy/roxy_commands.py`
- **Function**: `query_rag()`, `_query_rag_impl()`, `route_command()`
- **Missing**: `from truth_packet import generate_truth_packet, format_truth_for_prompt`
- **Impact**: Time queries return RAG garbage instead of system time

### RC2: Keyword Routing Hijacks Intent (CRITICAL)
- **File**: `/home/mark/.roxy/roxy_commands.py`
- **Function**: `route_command()` lines 133-297
- **Problem**: Simple word matching without NLP intent classification
- **Impact**: "push headings" → git push, "streaming architecture" → OBS

### RC3: Dual Personality Architecture (HIGH)
- **streaming.py**: Uses `get_system_prompt_header()` for rich ROXY identity
- **roxy_commands.py**: Uses `PromptTemplates` forcing "2-4 sentences"
- **Impact**: Different behavior based on which endpoint called

### RC4: Model Info Not Captured (MEDIUM)
- **File**: `/home/mark/.roxy/roxy_commands.py`
- **Function**: `_query_rag_impl()` calls `router.route_and_generate()` but doesn't capture model
- **CommandResponse metadata**: Only includes `command` and `routing_meta`, not `model`
- **Impact**: `model_used: null` in /run responses

### RC5: Web/Browser Explicitly Disabled (MEDIUM)
- **File**: `/home/mark/.roxy/roxy_commands.py` line 222
- **Code**: `return "Web browsing is not available. ..."`
- **Impact**: No web search capability even though infrastructure exists

---

## MINIMAL RESTORATION PLAN (5 PATCHES)

### Patch 1: Inject TruthPacket into /run (CRITICAL)
**File**: `/home/mark/.roxy/roxy_commands.py`
**Changes**:
1. Add import: `from truth_packet import generate_truth_packet, format_truth_for_prompt`
2. Add time query detection in `route_command()`: `if is_time_date_query(text): return ("time_direct", [text])`
3. Add handler in `execute_command()`: `elif cmd_type == "time_direct": return answer_time_query(query)`
4. Add `answer_time_query()` function using TruthPacket only (no RAG)

**Validation**:
```bash
curl -X POST http://127.0.0.1:8766/run -H "X-ROXY-Token: $TOKEN" \
  -H "Content-Type: application/json" -d '{"command":"what time is it"}'
# Expected: Contains "January" and "2026"
```

### Patch 2: Intent-Based Routing (CRITICAL)
**File**: `/home/mark/.roxy/roxy_commands.py`
**Changes**:
1. Add intent classifier: `from query_detection import classify_intent`
2. Replace keyword matching in `route_command()` with intent-based routing
3. Only route to git/obs/etc if HIGH confidence match

**Validation**:
```bash
curl -X POST http://127.0.0.1:8766/run -H "X-ROXY-Token: $TOKEN" \
  -H "Content-Type: application/json" -d '{"command":"list the 10 most recent push headings"}'
# Expected: Routing to RAG, not git push
```

### Patch 3: Unified Identity Loading (HIGH)
**File**: `/home/mark/.roxy/roxy_commands.py`
**Changes**:
1. Add import: `from truth_packet import get_system_prompt_header`
2. Replace `PromptTemplates.select_prompt()` with `get_system_prompt_header()` + custom prompt
3. Remove forced brevity ("2-4 sentences")

**Validation**:
```bash
curl -X POST http://127.0.0.1:8766/run -H "X-ROXY-Token: $TOKEN" \
  -H "Content-Type: application/json" -d '{"command":"tell me about yourself"}'
# Expected: Full ROXY personality, not robotic response
```

### Patch 4: Capture Model Info (MEDIUM)
**File**: `/home/mark/.roxy/roxy_commands.py`
**Changes**:
1. Modify `_query_rag_impl()` to capture model from router response
2. Add model to CommandResponse metadata
3. Return `{"metadata": {"model": "qwen2.5-coder:14b", ...}}`

**Validation**:
```bash
curl -X POST http://127.0.0.1:8766/run -H "X-ROXY-Token: $TOKEN" \
  -H "Content-Type: application/json" -d '{"command":"hello"}'
# Expected: "model_used": "qwen2.5-coder:14b" (not null)
```

### Patch 5: Enable Web Search (MEDIUM)
**File**: `/home/mark/.roxy/roxy_commands.py`
**Changes**:
1. Remove line 222 disabled message
2. Route web queries to brave_search MCP tool
3. Add web search handler

**Validation**:
```bash
curl -X POST http://127.0.0.1:8766/run -H "X-ROXY-Token: $TOKEN" \
  -H "Content-Type: application/json" -d '{"command":"search web for python tutorials"}'
# Expected: Actual search results
```

---

## REGRESSION TIMELINE

```
Jan 1-3, 2026: Golden Era (at /roxy, not ~/.roxy)
  - 93+ modules including learning/, memory/, autonomous/
  - Full cognitive architecture

Jan 4, 2026: 584c83d "ROXY Full Stack"
  - Created roxy_commands.py as shallow dispatcher
  - Keyword routing established
  - PromptTemplates introduced

Jan 5-9, 2026: Migration to ~/.roxy
  - Legacy services archived
  - PostgreSQL memory added (infrastructure)
  - But cognitive modules not reconnected

Jan 10, 2026: 9e86ee0
  - TruthPacket added to streaming.py ONLY
  - /run endpoint forgotten

Jan 11-12, 2026: Multiple "fix" commits
  - e7056af, 02d6375 - Attempted routing fixes
  - Didn't address fundamental keyword matching
  - Didn't add TruthPacket to /run
```

---

## CONCLUSION

ROXY's current state is an **architectural bifurcation**: `/stream` received progressive enhancements (TruthPacket, rich identity) while `/run` remained at its Jan 4 birth state.

The 5 patches above address the most critical gaps. Full restoration of the Golden Era cognitive architecture (learning, autonomous agents) would require significantly more work - essentially re-integrating the 20+ modules in `/opt/roxy/services.LEGACY.20260101_200448/`.

**Priority Order**:
1. Patch 1 (TruthPacket) - Fixes "can't tell time"
2. Patch 2 (Intent routing) - Fixes "push headings" misroute
3. Patch 3 (Unified identity) - Fixes "block of wood"
4. Patch 4 (Model capture) - Fixes observability
5. Patch 5 (Web search) - Restores capability

---

*Report generated: 2026-01-12*
*Auditor: Claude Opus 4.5*
*Classification: Definitive Root Cause Analysis*
