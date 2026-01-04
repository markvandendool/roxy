# AUDIT GAPS - Exact Commands to Close

**Evidence Bundle**: `20260102_191701_COPILOT_FULL_NEURON_MAP`  
**Total Gaps**: 15  
**Categories**: P0 Critical (5), P1 Important (5), P2 Minor (5)

---

## P0 - CRITICAL (Must Fix Before Production)

### Gap 1: Greeting Fastpath Does Not Exist
**Impact**: 3-5 second delay for simple greetings (should be <100ms)  
**Evidence**: api_hi_roxy_*.json (all route to RAG)  
**Root Cause**: No fastpath check in roxy_core.py before subprocess

**Next Command**:
```bash
# Verify no fastpath exists:
grep -n "greeting\|fastpath\|simple.*response" ~/.roxy/roxy_core.py

# If missing, add before line 447 in roxy_core.py _execute_command():
# greeting_patterns = [r"^hi\s+roxy", r"^hello", r"^hey\s+roxy"]
# if any(re.match(p, command, re.I) for p in greeting_patterns):
#     return "Hi! I'm ROXY. How can I help?"

# Test:
curl -H "X-ROXY-Token: $(cat ~/.roxy/secret.token)" \
     -d '{"command":"hi roxy"}' \
     http://127.0.0.1:8766/run | jq -r '.result' | grep -v "Routing to: rag"
```

---

### Gap 2: OBS Launcher Routes to WebSocket (Not App Launcher)
**Impact**: "open obs" does NOT launch OBS  
**Evidence**: obs_launch_diff.txt (empty), api_open_obs.json (routes to obs handler)  
**Root Cause**: Line 110 (obs keywords) matches BEFORE line 112 (launch_app pattern)

**Next Command**:
```bash
# Verify shadowing:
sed -n '105,125p' ~/.roxy/roxy_commands.py

# Fix: Move lines 112-118 BEFORE line 110 in roxy_commands.py
# Then test:
pgrep obs  # Should be empty
curl -H "X-ROXY-Token: $(cat ~/.roxy/secret.token)" \
     -d '{"command":"open obs"}' \
     http://127.0.0.1:8766/run
sleep 3
pgrep obs  # Should show OBS PID
```

---

### Gap 3: launch_app Handler Missing
**Impact**: All app launch commands fail (even after fixing Gap 2)  
**Evidence**: handler_branches.txt (no "launch_app" branch)  
**Root Cause**: No implementation in execute_command()

**Next Command**:
```bash
# Verify missing:
grep -n 'cmd_type == "launch_app"' ~/.roxy/roxy_commands.py

# If missing, add after line 319 (after obs handler):
# elif cmd_type == "launch_app":
#     app_name = args[0] if args else ""
#     subprocess.Popen(["xdg-open", app_name], 
#                      stdout=subprocess.DEVNULL, 
#                      stderr=subprocess.DEVNULL)
#     return f"Launching {app_name}..."

# Test:
curl -H "X-ROXY-Token: $(cat ~/.roxy/secret.token)" \
     -d '{"command":"open firefox"}' \
     http://127.0.0.1:8766/run | jq -r '.result'
```

---

### Gap 4: Cursor Modules NOT Integrated
**Impact**: 4 modules exist (16 KB code) but not used → claimed "16/16 implemented" is false  
**Evidence**: sha256_all_py.txt (files exist), no import evidence  
**Root Cause**: Files created but never imported

**Next Command**:
```bash
# Verify no imports:
for mod in hybrid_search llm_router security feedback; do
  echo "=== $mod ==="
  grep -rn "from $mod\|import.*$mod" ~/.roxy --include="*.py" | grep -v venv | grep -v __pycache__
done

# Check if modules are functional:
cd ~/.roxy
python3 -c "import hybrid_search; print('OK')" 2>&1
python3 -c "import llm_router; print('OK')" 2>&1
python3 -c "import security; print('OK')" 2>&1
python3 -c "import feedback; print('OK')" 2>&1

# Decide: Integrate OR remove
```

---

### Gap 5: Truth Gate Behavior Unclear
**Impact**: Unknown if validation is active → potential hallucination risk  
**Evidence**: truth_gate.py exists, also truth_gate.py.broken  
**Root Cause**: Two versions, no callsite evidence

**Next Command**:
```bash
# Find callsites:
grep -rn "truth_gate\|TruthGate\|get_truth_gate" ~/.roxy --include="*.py" | grep -v venv

# Compare versions:
diff ~/.roxy/truth_gate.py ~/.roxy/truth_gate.py.broken

# Check journal for validation logs:
journalctl --user -u roxy-core --since "1 hour ago" | grep -i "truth.*gate\|validation"

# Decision: Document current behavior (active/inactive/broken)
```

---

## P1 - IMPORTANT (Affects Reliability)

### Gap 6: Rate Limiting Not Stress Tested
**Impact**: DoS vulnerability if limits don't work  
**Evidence**: Code exists (lines 204, 338), not tested under load  
**Next Command**:
```bash
# Stress test /run (limit: 10 req/min):
TOKEN=$(cat ~/.roxy/secret.token)
for i in {1..15}; do
  curl -sS -H "X-ROXY-Token: $TOKEN" \
       -d '{"command":"ping"}' \
       http://127.0.0.1:8766/run &
done
wait | grep -c "429\|rate limit"

# Stress test /batch (limit: 5 req/min):
for i in {1..10}; do
  curl -sS -H "X-ROXY-Token: $TOKEN" \
       -d '{"commands":["ping"]}' \
       http://127.0.0.1:8766/batch &
done
wait | grep -c "429\|rate limit"
```

---

### Gap 7: Cache Hits Not Verified
**Impact**: Unknown if cache improves performance  
**Evidence**: cache_enabled=true, no hit logs  
**Next Command**:
```bash
# Test cache hit:
TOKEN=$(cat ~/.roxy/secret.token)
QUERY='{"command":"what is 2+2"}'

# First query (cache miss):
time curl -sS -H "X-ROXY-Token: $TOKEN" -d "$QUERY" http://127.0.0.1:8766/run > /tmp/resp1.json
T1=$(jq -r '.response_time' /tmp/resp1.json)

# Second query (should be cache hit):
time curl -sS -H "X-ROXY-Token: $TOKEN" -d "$QUERY" http://127.0.0.1:8766/run > /tmp/resp2.json
T2=$(jq -r '.response_time' /tmp/resp2.json)

# Check journal for cache hit log:
journalctl --user -u roxy-core --since "1 minute ago" | grep -i "cache.*hit"

# Verify T2 < T1:
python3 -c "import json; r1=json.load(open('/tmp/resp1.json')); r2=json.load(open('/tmp/resp2.json')); print(f'First: {r1.get(\"response_time\",0):.2f}s, Second: {r2.get(\"response_time\",0):.2f}s')"
```

---

### Gap 8: tool_direct Handler Untested
**Impact**: MCP tool integration unverified  
**Evidence**: Handler exists (line 353), MCP server alive, not tested  
**Next Command**:
```bash
# Verify MCP tools available:
curl -sS http://127.0.0.1:8765/health | jq '.tools | keys'

# Test tool_direct:
TOKEN=$(cat ~/.roxy/secret.token)
curl -sS -H "X-ROXY-Token: $TOKEN" \
     -d '{"command":"use git tool status"}' \
     http://127.0.0.1:8766/run | jq

# Should show git status output, not "unknown command"
```

---

### Gap 9: tool_preflight Handler Untested
**Impact**: Multi-step orchestration unverified  
**Evidence**: Handler exists (line 368), filesystem MCP alive, not tested  
**Next Command**:
```bash
# Verify filesystem MCP alive:
ps -fp 762751  # Should show bun filesystem MCP

# Test tool_preflight:
TOKEN=$(cat ~/.roxy/secret.token)
curl -sS -H "X-ROXY-Token: $TOKEN" \
     -d '{"command":"docs about README"}' \
     http://127.0.0.1:8766/run | jq

# Should show file listing + RAG synthesis
```

---

### Gap 10: CLI --once and --stream Flags Untested
**Impact**: CLI modes unverified  
**Evidence**: Flags exist in roxy_client.py, not tested  
**Next Command**:
```bash
# Test --once:
~/.roxy/venv/bin/python ~/.roxy/roxy_client.py --once "health"
# Should print health output and exit

# Test --stream:
~/.roxy/venv/bin/python ~/.roxy/roxy_client.py --stream "what is 2+2"
# Should show streaming SSE output
```

---

## P2 - MINOR (Cleanup/Documentation)

### Gap 11: Unreachable Code (Line 225)
**Impact**: Confusing for maintenance  
**Evidence**: parse_command_returns.txt (line 225 after line 82 fallback)  
**Next Command**:
```bash
# Verify unreachable:
sed -n '80,230p' ~/.roxy/roxy_commands.py | grep -n "return.*rag"
# Should show line 82 (fallback) before line 225 (explicit)

# Fix: Delete line 225 or move before line 82
```

---

### Gap 12: Subprocess Timeouts Not Stress Tested
**Impact**: Long-running commands might hang  
**Evidence**: timeout=30 in code, not tested  
**Next Command**:
```bash
# Test timeout:
TOKEN=$(cat ~/.roxy/secret.token)
curl -sS -H "X-ROXY-Token: $TOKEN" \
     -d '{"command":"sleep 45"}' \
     http://127.0.0.1:8766/run | jq

# Should timeout after ~30 seconds with error
```

---

### Gap 13: context_manager Integration Unclear
**Impact**: Multi-turn conversations unverified  
**Evidence**: Import exists (line 408), not tested  
**Next Command**:
```bash
# Test multi-turn context:
TOKEN=$(cat ~/.roxy/secret.token)
curl -sS -H "X-ROXY-Token: $TOKEN" \
     -d '{"command":"my name is Alice"}' \
     http://127.0.0.1:8766/run > /dev/null
sleep 1
curl -sS -H "X-ROXY-Token: $TOKEN" \
     -d '{"command":"what is my name"}' \
     http://127.0.0.1:8766/run | jq -r '.result'

# Should reference "Alice" from previous context
```

---

### Gap 14: Advanced RAG Path Not Tested
**Impact**: Fallback/advanced features unverified  
**Evidence**: /opt/roxy/services/adapters exists, not tested  
**Next Command**:
```bash
# Check advanced RAG availability:
ls -la /opt/roxy/services/adapters/

# Grep for advanced RAG callsite:
grep -rn "advanced.*rag\|services/adapters" ~/.roxy/roxy_commands.py

# If found, test with complex query requiring advanced features
```

---

### Gap 15: Ingestion Process Embedding Dimension
**Impact**: Unknown if ingestion uses 384-dim or 768-dim  
**Evidence**: PID 4059773 running, dimension not verified  
**Next Command**:
```bash
# Check ingestion script dimension:
grep -n "DefaultEmbeddingFunction\|nomic-embed-text\|embedding_function" \
     /opt/roxy/scripts/index_mindsong_repo_resume.py

# Should use DefaultEmbeddingFunction (384-dim)
# If uses nomic-embed-text (768-dim) → P0 BUG (dimension mismatch)
```

---

## SUMMARY

**Total Gaps**: 15  
**P0 Critical**: 5 (greeting fastpath, OBS routing, launch_app handler, Cursor modules, Truth Gate)  
**P1 Important**: 5 (rate limiting, cache hits, tool handlers, CLI flags)  
**P2 Minor**: 5 (unreachable code, timeouts, context, advanced RAG, ingestion)

**Estimated Time to Close All Gaps**:
- P0: 2-4 hours (fixes + testing)
- P1: 2-3 hours (stress tests + integration tests)
- P2: 1-2 hours (cleanup + documentation)
- **Total**: 5-9 hours

---

**END OF AUDIT GAPS**  
**Next Action**: Execute P0 commands to close critical gaps
