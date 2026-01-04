# AUDIT GAPS - What Remains Unknown

**Evidence Bundle**: `20260102_164423_COPILOT_FULL_NEURON_MAP/`  
**Date**: 2026-01-02 16:44:23 UTC  
**Methodology**: Zero-trust forensic audit

---

## CRITICAL GAPS (Must Verify Before Production)

### GAP 1: OBS Launcher Routing FAILURE
**Status**: ❌ **CRITICAL BUG CONFIRMED**

**Evidence**: `api_open_obs.json`, `obs_launch_diff.txt`

**What We Know**:
- Command "open obs" routes to obs WebSocket handler (line 110/121 in parse_command)
- OBS does NOT launch (before: NOT_RUNNING, after: NOT_RUNNING)
- Response: "Could not connect to OBS. Is it running with WebSocket enabled?"

**What We DON'T Know**:
- Does a launch_app handler exist anywhere? (parse_command returns it line 116, but no handler in execute_command)
- Where should "open obs" be routed? (launch_app vs obs control)
- What's the correct fix priority in parse_command? (move launch_app before obs pattern?)

**Next Commands**:
```bash
# Verify launch_app handler exists
grep -n 'cmd_type == "launch_app"' ~/.roxy/roxy_commands.py

# Check parse priority
grep -n 'r"\\b(open|launch|start)' ~/.roxy/roxy_commands.py
grep -n 'cmd.startswith("obs")' ~/.roxy/roxy_commands.py

# Test if ANY launch command works
curl -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"command":"launch firefox"}' http://127.0.0.1:8766/run
```

**Expected Outcome**: If launch_app handler missing, must implement it. If priority wrong, must reorder parse patterns.

---

### GAP 2: Greeting Routing Anomaly
**Status**: ⚠️ **UNEXPECTED BEHAVIOR**

**Evidence**: `api_hi_roxy.json`

**What We Know**:
- Command "hi roxy" routes to RAG instead of greeting fastpath
- Response includes full RAG output (not simple greeting)
- roxy_core.py:223 has greeting bypass logic: `if re.search(r"^(hi|hey|hello|yo|sup)\b.*roxy", ...)`

**What We DON'T Know**:
- Why is greeting fastpath not triggered?
- Is regex pattern too strict? (requires "roxy" in query)
- Is there a code path that skips the fastpath check?

**Next Commands**:
```bash
# Verify fastpath logic
grep -A 10 'if re.search.*hi.*roxy' ~/.roxy/roxy_core.py

# Test exact pattern match
curl -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"command":"hi roxy exactly"}' http://127.0.0.1:8766/run

# Test without "roxy"
curl -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"command":"hi"}' http://127.0.0.1:8766/run
```

**Expected Outcome**: Identify why fastpath is bypassed, fix regex or routing logic.

---

### GAP 3: CLI --once Mode
**Status**: ❌ **NOT VERIFIED**

**What We Know**:
- CLI wrapper exists at /usr/local/bin/roxy
- roxy_client.py should handle --once flag
- Previous audit showed --once not working (interactive prompt appears)

**What We DON'T Know**:
- Does --once flag exist in current code?
- If exists, why doesn't it work?
- Alternative: deterministic single-command mode?

**Next Commands**:
```bash
# Check if --once exists
grep -n '\-\-once' ~/.roxy/roxy_client.py

# Test CLI mode
roxy --once "health check" 2>&1 | tee /tmp/roxy_once_test.txt

# Check for interactive prompts
grep -i "interactive\|type.*exit" /tmp/roxy_once_test.txt
```

**Expected Outcome**: Either fix --once implementation or document it as NOT_SUPPORTED.

---

### GAP 4: Cursor's 4 Modules Integration
**Status**: ❌ **NOT VERIFIED**

**Evidence**: File existence confirmed, imports NOT verified

**What We Know**:
- Files exist: hybrid_search.py, llm_router.py, security.py, feedback.py
- SHA256 hashes captured
- No grep matches in previous audit for imports

**What We DON'T Know**:
- Are these modules imported anywhere?
- Are they functional/tested?
- What's the integration plan?

**Next Commands**:
```bash
# Verify imports
grep -rn "import hybrid_search\|from hybrid_search" ~/.roxy --include="*.py" | grep -v venv
grep -rn "import llm_router\|from llm_router" ~/.roxy --include="*.py" | grep -v venv
grep -rn "import security\|from security" ~/.roxy --include="*.py" | grep -v venv
grep -rn "import feedback\|from feedback" ~/.roxy --include="*.py" | grep -v venv

# Check module functionality
python3 -c "import sys; sys.path.insert(0, '/home/mark/.roxy'); import hybrid_search; print('OK')"
python3 -c "import sys; sys.path.insert(0, '/home/mark/.roxy'); import llm_router; print('OK')"
```

**Expected Outcome**: Determine if modules are dead code or need activation.

---

### GAP 5: Truth Gate Behavior
**Status**: ⚠️ **UNCLEAR**

**What We Know**:
- File exists: truth_gate.py (SHA256: 6710c9493dc87c2f...)
- File also exists: truth_gate.py.broken
- No evidence of Truth Gate being called in current routing

**What We DON'T Know**:
- Is Truth Gate active in production?
- Should greetings bypass Truth Gate?
- What triggers Truth Gate validation?

**Next Commands**:
```bash
# Find Truth Gate callsites
grep -rn "truth_gate\|TruthGate" ~/.roxy --include="*.py" | grep -v venv | grep -v ".broken"

# Check if Truth Gate is imported
grep -n "import truth_gate\|from truth_gate" ~/.roxy/roxy_core.py
grep -n "import truth_gate\|from truth_gate" ~/.roxy/roxy_commands.py

# Compare working vs broken versions
diff ~/.roxy/truth_gate.py ~/.roxy/truth_gate.py.broken | head -50
```

**Expected Outcome**: Determine Truth Gate's current role and correct behavior.

---

## IMPORTANT GAPS (Affects Reliability)

### GAP 6: Rate Limiting Stress Test
**Status**: ⚠️ **NOT STRESS TESTED**

**What We Know**:
- Code exists: roxy_core.py lines 204, 338
- Limits: 10 req/min for /run, 5 req/min for /batch
- Logic appears sound

**What We DON'T Know**:
- Does rate limiting actually work under load?
- What happens at exactly the limit?
- Are there race conditions?

**Next Commands**:
```bash
# Stress test /run endpoint
for i in {1..15}; do
  curl -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
    -d '{"command":"ping"}' http://127.0.0.1:8766/run &
done
wait

# Check for 429 responses
journalctl --user -u roxy-core --since "1 minute ago" | grep "429\|rate limit"
```

**Expected Outcome**: Verify rate limiting triggers at correct thresholds, no crashes.

---

### GAP 7: Subprocess Timeout Coverage
**Status**: ⚠️ **INCOMPLETE**

**What We Know**:
- git: 30s timeout ✅
- systemctl: 5s timeout ✅
- sensors: 5s timeout ✅
- docker: 10s timeout ✅
- MCP tool_direct: 60s timeout ✅
- MCP tool_preflight: 120s timeout ✅

**What We DON'T Know**:
- obs_controller.execute(): timeout? (WebSocket - not visible in roxy_commands.py)
- Any other subprocess calls without timeout?

**Next Commands**:
```bash
# Find all subprocess.run calls
grep -n "subprocess.run\|subprocess.Popen" ~/.roxy/roxy_commands.py

# Check obs_controller timeout
grep -n "timeout\|WebSocket" ~/.roxy/obs_controller.py | head -20

# Verify launch_app timeout (if handler exists)
grep -A 5 'cmd_type == "launch_app"' ~/.roxy/roxy_commands.py
```

**Expected Outcome**: All subprocess calls should have reasonable timeouts.

---

### GAP 8: Advanced RAG Path
**Status**: ⚠️ **NOT VERIFIED**

**What We Know**:
- Code exists: roxy_commands.py lines 400-410
- Tries to import from /opt/roxy/services/adapters
- Falls back to basic RAG on error

**What We DON'T Know**:
- Does /opt/roxy/services/adapters exist?
- Is advanced_rag functional?
- Has it ever been triggered?

**Next Commands**:
```bash
# Check if advanced RAG exists
ls -la /opt/roxy/services/adapters/ 2>&1

# Test import
python3 -c "
import sys
sys.path.insert(0, '/opt/roxy/services/adapters')
try:
    import advanced_rag
    print('IMPORTED')
    print('is_available:', advanced_rag.is_available())
except Exception as e:
    print('FAILED:', e)
"

# Force advanced RAG path
curl -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"command":"what is roxy", "use_advanced_rag": true}' \
  http://127.0.0.1:8766/run
```

**Expected Outcome**: Determine if advanced RAG is dead code or needs activation.

---

### GAP 9: tool_direct and tool_preflight Handlers
**Status**: ⚠️ **UNTESTED**

**What We Know**:
- Code exists: roxy_commands.py lines 353-363 (tool_direct), 368-391 (tool_preflight)
- Both call MCP server at http://localhost:8765/execute
- Parse patterns exist

**What We DON'T Know**:
- Do these handlers work?
- Have they ever been triggered?
- Are MCP tools accepting these requests?

**Next Commands**:
```bash
# Test tool_direct
curl -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"command":"use git tool status"}' http://127.0.0.1:8766/run

# Test tool_preflight
curl -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"command":"summarize repo using git tool"}' \
  http://127.0.0.1:8766/run

# Verify MCP server accepts these
curl -X POST http://localhost:8765/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "git_status", "arguments": {}}'
```

**Expected Outcome**: Verify handlers work or mark as dead code.

---

### GAP 10: Briefing Handler
**Status**: ⚠️ **PLACEHOLDER**

**What We Know**:
- Code exists: roxy_commands.py line 325
- Returns: "Daily briefing coming soon."
- Parse pattern exists: line 135

**What We DON'T Know**:
- Is this intentionally unimplemented?
- What's the implementation plan?
- Should parse pattern be removed?

**Next Commands**:
```bash
# Test briefing command
curl -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"command":"briefing"}' http://127.0.0.1:8766/run

# Check if daily_briefing.py exists
ls -la ~/.roxy/daily_briefing.py

# Verify if it's called anywhere
grep -rn "daily_briefing" ~/.roxy --include="*.py" | grep -v venv
```

**Expected Outcome**: Either implement or mark as TODO.

---

## MINOR GAPS (Documentation/Cleanup)

### GAP 11: Cache Hit Evidence
**Status**: ⚠️ **NO EVIDENCE**

**What We Know**:
- Cache enabled (health response: cache_enabled=true)
- Cache write/lookup code exists
- No evidence of actual cache hit in tests

**What We DON'T Know**:
- Does cache actually return hits?
- What's the hit rate?
- Are embeddings matching correctly?

**Next Commands**:
```bash
# Test cache hit
curl -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"command":"what is roxy"}' http://127.0.0.1:8766/run

# Immediately repeat (should hit cache)
curl -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"command":"what is roxy"}' http://127.0.0.1:8766/run

# Check logs for cache hit
journalctl --user -u roxy-core --since "1 minute ago" | grep -i cache
```

**Expected Outcome**: Verify cache hit/miss logging and functionality.

---

### GAP 12: Context Manager Integration
**Status**: ❌ **UNKNOWN**

**What We Know**:
- File may exist: context_manager.py
- Not in SHA256 list (not verified)

**What We DON'T Know**:
- Does file exist?
- Is it used anywhere?
- What's its purpose?

**Next Commands**:
```bash
# Check existence
ls -la ~/.roxy/context_manager.py

# Check imports
grep -rn "context_manager" ~/.roxy --include="*.py" | grep -v venv

# If exists, check SHA256
sha256sum ~/.roxy/context_manager.py
```

**Expected Outcome**: Document existence and integration status.

---

### GAP 13: Unreachable Code (Line 225)
**Status**: ⚠️ **DEAD CODE CONFIRMED**

**What We Know**:
- Line 225 in parse_command: `if cmd.startswith("ask ") or cmd.startswith("search ")`
- Line 82 (default fallback) catches these first
- Functionally equivalent but unreachable

**What We DON'T Know**:
- Should this be removed?
- Was it left for documentation?
- Are there unit tests relying on it?

**Next Commands**:
```bash
# Check if tests exist
grep -rn 'startswith.*ask\|startswith.*search' ~/.roxy --include="*test*.py"

# Safe to remove? Check git blame
cd ~/.roxy && git log -p --follow -S 'startswith("ask")' -- roxy_commands.py | head -50
```

**Expected Outcome**: Remove dead code or document reason for keeping.

---

## SUMMARY

**CRITICAL (Must Fix)**: 5 gaps
1. OBS launcher routing FAILURE
2. Greeting routing anomaly
3. CLI --once mode not verified
4. Cursor modules not integrated
5. Truth Gate behavior unclear

**IMPORTANT (Affects Reliability)**: 5 gaps
6. Rate limiting not stress tested
7. Subprocess timeout incomplete
8. Advanced RAG path not verified
9. tool_direct/tool_preflight untested
10. Briefing handler placeholder

**MINOR (Cleanup/Docs)**: 3 gaps
11. Cache hit evidence missing
12. Context manager unknown
13. Unreachable code (line 225)

**Next Actions**:
1. Fix OBS routing (P0)
2. Investigate greeting fastpath (P0)
3. Verify/fix CLI --once (P0)
4. Audit Cursor module integration (P1)
5. Clarify Truth Gate role (P1)
6. Stress test rate limiting (P1)
7. Verify all subprocess timeouts (P1)
8. Test advanced RAG path (P2)
9. Test MCP tool handlers (P2)
10. Implement or remove briefing (P2)
