# ROXY NEURON MAP - Complete Byte-Level Inventory

**Evidence Bundle**: `20260102_164423_COPILOT_FULL_NEURON_MAP/`  
**Compressed**: `20260102_164423_COPILOT_FULL_NEURON_MAP.tar.gz` (37K, from 248K raw)  
**Date**: 2026-01-02 16:44:23 UTC  
**System**: Linux macpro-linux 6.18.2-1-t2-noble x86_64

---

## A) PROCESSES & PORTS (OS TRUTH)

### Port 8765: MCP Server
**Evidence**: `port_8765_lsof.txt`, `port_8765_owner_ps.txt`, `health_8765_verbose.txt`

| Property | Value |
|----------|-------|
| PID | 11275 |
| Command | `/home/mark/.roxy/venv/bin/python3 /home/mark/.roxy/mcp/mcp_server.py` |
| Parent | 1 (systemd) |
| STIME | Jan 01 (running 2 days) |
| Bind | 0.0.0.0:8765 (all interfaces) |
| Response | MCP tool catalog (21 tools: git, docker, obs, rag) |

### Port 8766: ROXY Core
**Evidence**: `port_8766_lsof.txt`, `port_8766_owner_ps.txt`, `health_8766_verbose.txt`

| Property | Value |
|----------|-------|
| PID | 809812 |
| Command | `/home/mark/.roxy/venv/bin/python /home/mark/.roxy/roxy_core.py` |
| Parent | 4143 (systemd --user) |
| STIME | 03:25 (running 13 hours) |
| Bind | 127.0.0.1:8766 (localhost only) |
| Response | `{"status": "ok", "service": "roxy-core", "timestamp": ...}` |

### Additional Processes
**Evidence**: `phase0_running_processes.txt`

| PID | Command | Purpose |
|-----|---------|---------|
| 762751 | `bun .../filesystem/dist/index.js` | Filesystem MCP server |
| 763676 | `node .../@modelcontextprotocol/server-github` | GitHub MCP server |
| 4059773 | `python3 scripts/index_mindsong_repo_resume.py --yes` | Background indexing |

---

## B) SYSTEMD UNITS

**Evidence**: `systemd_roxy_core_status.txt`, `systemd_roxy_core_unit.txt`, `systemd_related_units.txt`

| Unit | Status | PID | Uptime | Description |
|------|--------|-----|--------|-------------|
| roxy-core.service | active (running) | 809812 | 13h | ROXY Core (always-on background service) |
| roxy-voice.service | active (running) | - | - | ROXY Voice Pipeline - Complete Voice Interface |

**roxy-core.service Configuration**:
```ini
[Unit]
Description=ROXY Core (always-on background service)
After=default.target

[Service]
Type=simple
WorkingDirectory=%h/.roxy
ExecStart=%h/.roxy/venv/bin/python %h/.roxy/roxy_core.py
Restart=on-failure
RestartSec=2
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
```

---

## C) ENTRYPOINTS

### CLI Wrapper
**Path**: `/usr/local/bin/roxy`  
**Type**: Bash script  
**Target**: `~/.roxy/venv/bin/python ~/.roxy/roxy_client.py`

**Commands**:
- `roxy chat` - Interactive chat (default)
- `roxy status` - systemctl --user status roxy-core
- `roxy start` - systemctl --user start roxy-core
- `roxy stop` - systemctl --user stop roxy-core
- `roxy restart` - systemctl --user restart roxy-core
- `roxy logs` - journalctl --user -u roxy-core -f

### HTTP Endpoints
**Evidence**: `endpoints_scan.txt`, `health_8766_verbose.txt`

1. **GET /health** (Line 105) - Fastpath health check
2. **POST /run** (Line 185) - Single command execution
3. **POST /batch** (Line 187) - Batch command execution

---

## D) STATE & STORAGE

### ChromaDB
**Evidence**: `chroma_collections_proof.txt`

**Path**: `~/.roxy/chroma_db`

**Collections**:
| Collection | Documents | Metadata |
|------------|-----------|----------|
| roxy_cache | 24 | ROXY semantic cache |
| mindsong_docs | 40 | ROXY RAG (minimal onboarding) |

**Embedding**: DefaultEmbeddingFunction (384-dim) for all collections

### Configuration
**Files**:
- `~/.roxy/config.json` - System configuration
- `~/.roxy/secret.token` - API authentication token

### Logs
**Paths**:
- `journalctl --user -u roxy-core` - Systemd logs
- `~/.roxy/logs/` - Application logs (if exists)
- `/tmp/indexing.log` - Background indexing logs

### Evidence
**Path**: `~/.roxy/evidence/`  
**Current Bundle**: `20260102_164423_COPILOT_FULL_NEURON_MAP/` (38 files, 248K)

---

## E) ROUTING GRAPH SUMMARY (7 Gates)

**Full Details**: See `ROUTING_GRAPH.md`

### Gate 1: HTTP Method Dispatch
- GET /health → Fastpath response
- POST /run → _handle_run_command()
- POST /batch → _handle_batch_command()

### Gate 2: Authentication
- X-ROXY-Token header validation
- 401 Unauthorized on failure

### Gate 3: Rate Limiting
- /run: 10 requests/minute per IP
- /batch: 5 requests/minute per IP

### Gate 4: Cache Lookup
- Greeting pattern → Fastpath (⚠️ BYPASSED - routes to RAG)
- Status query → Bypass cache
- Cache hit → Return cached response
- Cache miss → Continue to subprocess

### Gate 5: Parse Command
**26 return statements → 13 cmd_types**:
- launch_app, git, obs, health, briefing, capabilities
- model_info, unavailable, info, tool_direct, tool_preflight, rag

### Gate 6: Execute Command
**11 handler branches**:
- git, obs, health, briefing (placeholder), capabilities
- model_info, unavailable, tool_direct, info, tool_preflight, rag
- ❌ **MISSING**: launch_app handler

### Gate 7: RAG Query Path
- Advanced RAG (if available) → /opt/roxy/services/adapters
- Basic RAG → DefaultEmbedding → ChromaDB → Ollama LLM

---

## F) TOOL SURFACE (13 cmd_types)

**Full Details**: See `TOOL_SURFACE.md`

| cmd_type | Parser Lines | Handler Line | Status |
|----------|--------------|--------------|--------|
| launch_app | 112-118 | ❌ MISSING | NOT WORKING |
| git | 88-103 | 316 | ✅ Works |
| obs | 110, 121 | 319 | ⚠️ Works (routing bug) |
| health | 127-131 | 322 | ✅ Works |
| briefing | 135 | 325 | ⚠️ Placeholder |
| capabilities | 140 | 328 | ✅ Works |
| model_info | 144 | 335 | ✅ Works |
| unavailable | 151, 157, 162 | 343 | ✅ Works |
| info | 166 | 365 | ✅ Works |
| tool_direct | 177, 193 | 353 | ⚠️ Untested |
| tool_preflight | 214, 218, 221 | 368 | ⚠️ Untested |
| rag | 82 (fallback) | 394 | ✅ Works |
| rag | 225 (explicit) | 394 | ❌ Unreachable |

**Dead Branches**: 1 (line 225 unreachable)  
**Missing Handlers**: 1 (launch_app)  
**Placeholders**: 1 (briefing)

---

## G) EMBEDDING CONTRACT

**Full Details**: See `EMBEDDING_CONTRACT.md`

**Runtime Dimension**: **384** (PROVEN via `embedding_dim_proof.txt`)

**Production Paths**:
| Location | Function | Dimension | Status |
|----------|----------|-----------|--------|
| roxy_commands.py:468 | DefaultEmbeddingFunction | 384 | ✅ ACTIVE |
| cache.py:81 | DefaultEmbeddingFunction | 384 | ✅ FIXED |
| cache.py:134 | DefaultEmbeddingFunction | 384 | ✅ FIXED |
| rebuild_rag_index.py | DefaultEmbeddingFunction | 384 | ✅ ACTIVE |

**Non-Production**:
| Location | Function | Dimension | Status |
|----------|----------|-----------|--------|
| bootstrap_rag.py | nomic-embed-text | 768 | ⚠️ Script only |
| roxy_cli_test.py | nomic-embed-text | 768 | ⚠️ Test only |

**Verdict**: ✅ **ZERO MISMATCHES** - All production paths use 384-dim

---

## H) SECURITY / TRUTH GATE STATUS

### Authentication
**Status**: ✅ **ACTIVE**  
**Method**: X-ROXY-Token header validation  
**Location**: roxy_core.py lines 189-198 (_handle_run_command), 342-351 (_handle_batch_command)

### Rate Limiting
**Status**: ✅ **ACTIVE** (code exists, not stress tested)  
**Method**: IP-based rate limiting  
**Limits**: 10 req/min (/run), 5 req/min (/batch)  
**Location**: roxy_core.py lines 204, 338

### Truth Gate
**Status**: ⚠️ **UNCLEAR**  
**Evidence**: File exists (`truth_gate.py`), also `truth_gate.py.broken`  
**Problem**: No evidence of Truth Gate being called in current routing  
**Impact**: Unknown if validation is active or disabled

---

## I) KNOWN FAILURES & RISKS

### P0 - CRITICAL (Must Fix Before Production)

1. **OBS Launcher Routing FAILURE**
   - **Evidence**: `api_open_obs.json`, `obs_launch_diff.txt`
   - **Problem**: "open obs" routes to WebSocket handler, NOT app launcher
   - **Impact**: OBS does not launch (before: NOT_RUNNING, after: NOT_RUNNING)
   - **Fix**: Move launch_app pattern before obs pattern in parse_command

2. **Greeting Fastpath Bypassed**
   - **Evidence**: `api_hi_roxy.json`
   - **Problem**: "hi roxy" routes to RAG instead of greeting fastpath
   - **Impact**: 3-5 second delay for greetings (should be <100ms)
   - **Fix**: Investigate why fastpath regex check is bypassed

3. **Missing launch_app Handler**
   - **Evidence**: `handler_branches.txt` (no launch_app branch)
   - **Problem**: Parse returns launch_app, execute has no handler
   - **Impact**: All launch commands fail with "Unknown command type"
   - **Fix**: Implement launch_app handler with xdg-open/open subprocess

### P1 - IMPORTANT (Affects Reliability)

4. **Cursor Modules NOT Integrated**
   - **Evidence**: SHA256 hashes exist, imports NOT verified
   - **Problem**: hybrid_search, llm_router, security, feedback not used
   - **Impact**: Claimed functionality not available, potential dead code
   - **Fix**: Audit each module, integrate OR remove

5. **Truth Gate Behavior Unclear**
   - **Evidence**: `truth_gate.py` and `truth_gate.py.broken` both exist
   - **Problem**: No callsites found, unclear if active
   - **Impact**: Unknown security/validation behavior
   - **Fix**: Clarify Truth Gate role, document activation conditions

6. **Rate Limiting Not Stress Tested**
   - **Evidence**: Code exists (lines 204, 338), not verified under load
   - **Problem**: Unknown if limits actually work, race conditions possible
   - **Impact**: DoS vulnerability if rate limiting fails
   - **Fix**: Stress test with 15+ concurrent requests

### P2 - MINOR (Cleanup/Documentation)

7. **Unreachable Code (Line 225)**
   - **Evidence**: `parse_command_returns.txt`
   - **Problem**: Line 225 "ask"/"search" check is unreachable (line 82 catches first)
   - **Impact**: Dead code, confusing for maintenance
   - **Fix**: Remove or document reason for keeping

8. **Cache Hit Evidence Missing**
   - **Evidence**: Cache enabled, no evidence of actual hits
   - **Problem**: Unknown if cache returns hits correctly
   - **Impact**: Performance unclear
   - **Fix**: Test identical query twice, verify cache hit log

---

## J) ACTION PLAN

### Immediate (Next 30 Minutes)

1. **Fix OBS Routing**
   ```python
   # Move lines 112-118 BEFORE line 110 in roxy_commands.py
   # Test: curl -d '{"command":"open obs"}' http://127.0.0.1:8766/run
   # Verify: pgrep -a obs  # Should show OBS process
   ```

2. **Implement launch_app Handler**
   ```python
   # Add to execute_command() around line 315:
   if cmd_type == "launch_app":
       app_name = parsed_args[0] if parsed_args else ""
       if shutil.which("xdg-open"):
           subprocess.Popen(["xdg-open", app_name])
       return f"Launching {app_name}..."
   ```

3. **Investigate Greeting Fastpath**
   ```bash
   # Add debug logging before fastpath check in roxy_core.py:223
   # Test: curl -d '{"command":"hi roxy"}' http://127.0.0.1:8766/run
   # Check: journalctl --user -u roxy-core -f
   ```

### Short-Term (Next 2 Hours)

4. **Audit Cursor Modules**
   ```bash
   # For each: hybrid_search, llm_router, security, feedback
   grep -rn "import MODULE" ~/.roxy --include="*.py" | grep -v venv
   python3 -c "import sys; sys.path.insert(0, '/home/mark/.roxy'); import MODULE; print('OK')"
   ```

5. **Clarify Truth Gate**
   ```bash
   # Find callsites
   grep -rn "truth_gate\|TruthGate" ~/.roxy --include="*.py" | grep -v venv
   # Compare versions
   diff ~/.roxy/truth_gate.py ~/.roxy/truth_gate.py.broken
   ```

6. **Stress Test Rate Limiting**
   ```bash
   # 15 concurrent requests
   for i in {1..15}; do
     curl -H "X-ROXY-Token: $TOKEN" -d '{"command":"ping"}' http://127.0.0.1:8766/run &
   done
   wait
   # Check for 429 responses
   ```

### Long-Term (Next Session)

7. **Remove Unreachable Code**
   - Delete line 225 in parse_command
   - Add unit test ensuring "ask"/"search" route to RAG

8. **Verify Cache Hit Behavior**
   - Run identical query twice
   - Check logs for cache hit message
   - Measure response time difference

9. **Test Untested Handlers**
   - tool_direct: `curl -d '{"command":"use git tool status"}' ...`
   - tool_preflight: `curl -d '{"command":"summarize repo using git tool"}' ...`
   - Advanced RAG: Check if /opt/roxy/services/adapters exists

10. **Implement or Remove Briefing**
    - If implementing: create handler logic
    - If removing: delete parse pattern (line 135)

---

## SUMMARY

**Evidence Quality**: ✅ **HIGH** (38 files, zero-trust, all claims backed)  
**System State**: ⚠️ **PARTIALLY FUNCTIONAL** (core works, 3 critical bugs)  
**Critical Failures**: 3 (OBS routing, greeting fastpath, launch_app handler)  
**Integration Gaps**: 5 (Cursor modules, Truth Gate, rate limit stress, cache hits, unreachable code)  
**Next Steps**: Fix 3 P0 bugs, verify 4 P1 integrations, test 3 P2 items  
**Compression**: ✅ `20260102_164423_COPILOT_FULL_NEURON_MAP.tar.gz` (37K from 248K raw)

---

**END OF NEURON MAP**  
**Bundle**: `~/.roxy/evidence/20260102_164423_COPILOT_FULL_NEURON_MAP/`  
**Completion**: 2026-01-02 16:54 UTC
