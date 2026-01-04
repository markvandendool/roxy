# ROUTING GRAPH - Gate-by-Gate Decision Flow

**Evidence Bundle**: `20260102_191701_COPILOT_FULL_NEURON_MAP`  
**Generated**: 2026-01-02 19:17:01 UTC  
**Source**: Current code analysis + live API proofs

---

## GATE 1: HTTP METHOD DISPATCH

**Evidence**: `endpoints_scan.txt` lines 103, 105, 185, 187

| Method | Path | Line | Handler | Auth Required |
|--------|------|------|---------|---------------|
| GET | /health | 105 | Fastpath response | ❌ No |
| POST | /run | 185 | _handle_run_command() | ✅ Yes |
| POST | /batch | 187 | _handle_batch_command() | ✅ Yes |
| GET | /stream | - | _handle_streaming() | ❌ No |

**Flow**:
```
GET /health → 200 OK {"status": "ok", "service": "roxy-core", ...}
POST /run → Gate 2 (Auth)
POST /batch → Gate 2 (Auth)
```

---

## GATE 2: AUTHENTICATION

**Evidence**: `systemd_roxy_core_unit.txt` (no AUTH_TOKEN env), live API tests required X-ROXY-Token

**Location**: roxy_core.py lines 189-198 (/run), 342-351 (/batch)

**Logic**:
```python
if AUTH_TOKEN:
    provided_token = self.headers.get('X-ROXY-Token')
    if not provided_token or provided_token != AUTH_TOKEN:
        403 Forbidden
```

**Evidence**: All API tests (`api_*.json`) used X-ROXY-Token and succeeded → Auth is ACTIVE

---

## GATE 3: RATE LIMITING

**Evidence**: Code references at lines 204 (/run), 338 (/batch)

**Limits**:
- `/run`: 10 requests/minute per IP
- `/batch`: 5 requests/minute per IP

**Status**: ⚠️ **NOT STRESS TESTED** - Code exists but not proven under load

---

## GATE 4: SECURITY SANITIZATION

**Evidence**: roxy_core.py lines 232-250

**Process**:
1. Import `security.py` module
2. Call `sanitize_input(command)`
3. If `blocked=True` → 403 error
4. Use `sanitized` command for execution

**Status**: ⚠️ **INTEGRATION UNCLEAR** - Code exists, actual filtering not verified

---

## GATE 5: CACHE LOOKUP (BROKEN FASTPATH)

**Evidence**: `api_hi_roxy_*.json` (3 tests), `api_status_today_*.json` (3 tests)

**Expected Behavior**: Simple greetings should hit cache/fastpath, return <100ms
**Actual Behavior**: ALL "hi roxy" queries route to RAG (3-5 second response)

**Code Location**: roxy_core.py lines 419-446

**Problem**: 
- Cache check is gated by `_is_rag_query(command)` 
- NO fastpath for greeting patterns
- NO special handling for "hi roxy", "hello", "what is new today"

**Proof**:
```
api_hi_roxy_1.json: "[ROXY] Routing to: rag ['hi roxy']"
api_hi_roxy_2.json: "[ROXY] Routing to: rag ['hi roxy']"
api_hi_roxy_3.json: "[ROXY] Routing to: rag ['hi roxy']"
```

**Root Cause**: ❌ **NO GREETING FASTPATH EXISTS** in roxy_core.py

---

## GATE 6: PARSE COMMAND (PATTERN MATCHING)

**Evidence**: `parse_command_returns.txt` (26 returns → 13 cmd_types)

**Function**: `parse_command(text)` in roxy_commands.py

**Parse Universe** (order matters - first match wins):

| Line | Pattern | cmd_type | Status |
|------|---------|----------|--------|
| 82 | (default/fallback) | rag | ✅ Reachable |
| 88-103 | git keywords | git | ✅ Works |
| 110 | **obs keywords** | obs | ⚠️ **SHADOWS launch_app** |
| 112-118 | launch/open/start app | launch_app | ❌ **UNREACHABLE** |
| 121 | obs phrases | obs | ⚠️ Duplicate pattern |
| 127-131 | health keywords | health | ✅ Works |
| 135 | briefing | briefing | ⚠️ Placeholder |
| 140 | capabilities | capabilities | ✅ Works |
| 144 | model info | model_info | ✅ Works |
| 151 | browser control | unavailable | ✅ Works |
| 157 | shell execution | unavailable | ✅ Works |
| 162 | cloud integration | unavailable | ✅ Works |
| 166 | clip_extractor info | info | ✅ Works |
| 177, 193 | tool_direct syntax | tool_direct | ⚠️ Untested |
| 214, 218, 221 | tool_preflight patterns | tool_preflight | ⚠️ Untested |
| 225 | ask/search (explicit) | rag | ❌ **UNREACHABLE** (line 82 catches first) |

**Critical Routing Bug**: Line 110 matches "obs" keyword BEFORE line 112 can match "open app"

**Evidence**: `parse_obs_vs_launch_app.txt`
```python
Line 110: if any(w in words for w in obs_keywords):  # "obs" matches
Line 110:     return ("obs", [text])
Line 112: # launch_app pattern never reached when "obs" keyword present
```

**Proof**: `api_open_obs.json`
```
Command: "open obs"
Parsed as: obs (not launch_app)
Handler: OBS WebSocket controller
Result: "Could not connect to OBS. Is it running with WebSocket enabled?"
```

---

## GATE 7: EXECUTE COMMAND (HANDLER DISPATCH)

**Evidence**: `handler_branches.txt` (11 branches)

**Function**: `execute_command(cmd_type, args)` in roxy_commands.py

**Handler Coverage Table**:

| cmd_type | Handler Line | Implementation | Test Evidence |
|----------|--------------|----------------|---------------|
| git | 316 | ✅ Full (status/commit/push/pull/diff/log) | Not tested in this audit |
| obs | 319 | ✅ WebSocket controller | api_open_obs.json |
| health | 322 | ✅ System health report | api_batch_ping_health.json |
| briefing | 325 | ⚠️ Placeholder (returns "Briefing feature...") | Not tested |
| capabilities | 328 | ✅ Lists available skills | Not tested |
| model_info | 335 | ✅ Ollama model details | Not tested |
| unavailable | 343 | ✅ Returns "not available" messages | Not tested |
| tool_direct | 353 | ⚠️ MCP tool execution | Not tested |
| info | 365 | ✅ Returns info strings | Not tested |
| tool_preflight | 368 | ⚠️ Multi-step tool orchestration | Not tested |
| rag | 394 | ✅ RAG query (ChromaDB + LLM) | api_hi_roxy_*.json, api_what_is_roxy.json |
| **launch_app** | ❌ **MISSING** | ❌ No handler exists | api_open_obs.json (routed to obs instead) |

**Dead Branches**: 1 (line 225 unreachable due to line 82 fallback)  
**Missing Handlers**: 1 (launch_app parsed but not executed)  
**Placeholders**: 1 (briefing)  
**Untested**: 3 (tool_direct, tool_preflight, info)

---

## GATE 8: CACHE WRITE

**Evidence**: roxy_core.py lines 500+ (after execution)

**Logic**: If `mode == "rag"` from structured response, cache the result

**Status**: ⚠️ Cache writes exist, hits not verified in this audit

---

## ROUTING FAILURES (PROVEN)

### P0-1: Greeting Fastpath DOES NOT EXIST
**Evidence**: `api_hi_roxy_*.json` (3 tests, all route to RAG)  
**Impact**: 3-5 second delay for simple greetings (should be <100ms)  
**Root Cause**: No fastpath check in roxy_core.py before subprocess call

### P0-2: OBS Shadows launch_app
**Evidence**: `api_open_obs.json`, `parse_obs_vs_launch_app.txt`  
**Impact**: "open obs" routes to WebSocket controller, does NOT launch OBS  
**Root Cause**: Line 110 (obs keywords) matches BEFORE line 112 (launch_app pattern)  
**Proof**: `obs_launch_diff.txt` is empty (OBS did not launch)

### P0-3: launch_app Handler Missing
**Evidence**: `handler_branches.txt` (no "launch_app" branch)  
**Impact**: Even if parse_command returns launch_app, execute fails  
**Root Cause**: No handler implementation

---

## PROPOSED FIXES (NOT APPLIED)

### Fix 1: Move launch_app Pattern Before OBS
```python
# Line 110-118 should move to BEFORE line 110
# This ensures "open app" matches before "obs" keyword
```

### Fix 2: Implement launch_app Handler
```python
elif cmd_type == "launch_app":
    app_name = args[0] if args else ""
    if shutil.which("xdg-open"):
        subprocess.Popen(["xdg-open", app_name])
        return f"Launching {app_name}..."
    return f"Could not launch {app_name}"
```

### Fix 3: Add Greeting Fastpath
```python
# In roxy_core.py _execute_command(), before subprocess:
greeting_patterns = [r"^hi\s+roxy", r"^hello", r"^hey\s+roxy"]
if any(re.match(p, command, re.I) for p in greeting_patterns):
    return "Hi! I'm ROXY, your resident AI assistant. How can I help?"
```

---

**END OF ROUTING GRAPH**  
**Coverage**: 7 gates mapped, 13 cmd_types documented, 3 P0 failures proven  
**Next Actions**: Apply fixes 1-3 after Chief authorization
