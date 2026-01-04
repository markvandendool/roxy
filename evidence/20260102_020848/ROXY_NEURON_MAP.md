# ROXY NEURON MAP - Complete Brain Scan
**Evidence Bundle**: `~/.roxy/evidence/20260102_020848/`  
**Date**: 2026-01-02 02:40 UTC (POST-FIX)  
**Purpose**: Byte-level forensic inventory of all code paths, decision points, and state

---

## A) Processes (OS Level)

### ROXY Core Service
- **Systemd Unit**: `roxy-core.service`
- **Binary**: `/home/mark/.roxy/venv/bin/python /home/mark/.roxy/roxy_core.py`
- **PID**: 4155786 (as of 02:39 UTC)
- **Port**: **8766** (127.0.0.1:8766, TCP LISTEN)
- **Parent**: systemd user instance
- **Restart Policy**: `on-failure`
- **Status**: active (running)

### MCP Server (Separate Service)
- **Binary**: `python3` (unknown script)
- **PID**: 11275
- **Port**: **8765** (0.0.0.0:8765, TCP LISTEN)
- **Response**: MCP tool catalog (git, docker, obs, rag tools)
- **Relationship**: INDEPENDENT of ROXY (different process, different port)

### CLI Wrapper
- **Path**: `/usr/local/bin/roxy`
- **Type**: Bash script
- **Target**: `~/.roxy/venv/bin/python ~/.roxy/roxy_client.py`
- **Modes**: chat (interactive), status, start, stop, restart, logs, test, legacy

---

## B) Entrypoints (Request Path)

### Entry 1: CLI Interactive
```
/usr/local/bin/roxy chat
  → ~/.roxy/venv/bin/python ~/.roxy/roxy_client.py
  → while True: input() → POST http://127.0.0.1:8766/run {"command": "..."}
  → roxy_core.py:do_POST()
```

### Entry 2: CLI Single Command
```
/usr/local/bin/roxy --once "command"
  → roxy_client.py with --once flag
  → single POST http://127.0.0.1:8766/run {"command": "command"}
  → exit after response
```

### Entry 3: Direct API
```
curl -H "X-ROXY-Token: $(cat ~/.roxy/secret.token)" \
     -H "Content-Type: application/json" \
     -d '{"command": "..."}' \
     http://127.0.0.1:8766/run
  → roxy_core.py:do_POST() /run handler
```

### Entry 4: Batch API
```
curl -H "X-ROXY-Token: ..." \
     -d '{"commands": ["cmd1", "cmd2"]}' \
     http://127.0.0.1:8766/batch
  → roxy_core.py:do_POST() /batch handler
```

---

## C) Decision Points (Routing Graph)

### Gate 1: HTTP Method (roxy_core.py:103, 183)
```
GET /health → {"status": "ok", ...} (fastpath, no subprocess)
POST /run → _handle_run_command()
POST /batch → _handle_batch_command()
```

### Gate 2: Authentication (roxy_core.py:189, 342)
```
if "X-ROXY-Token" header != secret.token:
  → 401 Unauthorized
else:
  → continue
```

### Gate 3: Rate Limiting (roxy_core.py:204, 338)
```
if rate_limiter.check_rate_limit(client_ip, endpoint):
  → continue
else:
  → 429 Too Many Requests
```

### Gate 4: Cache Lookup (roxy_core.py:223-232)
**Decision Tree**:
```
command = request["command"]
if bypass_cache(command):  # status queries, greetings
  → skip to Gate 5
elif cache_enabled and cache.get(command):
  → return cached response (no subprocess)
else:
  → continue to Gate 5
```

**bypass_cache patterns**:
- Greeting regex: `r"^(hi|hey|hello|yo|sup)\b.*roxy"` (case-insensitive)
- Status queries: `is_status_query()` checks for "new today", "status", "update"

### Gate 5: Parse Command (roxy_commands.py:parse_command)
**Executed via**: `subprocess.run(["python3", "roxy_commands.py", command])`

**Decision Tree** (line numbers from parse_command):
```
1. Line 112-118: launch_app pattern ("open <app>", "launch <app>")
   → return ("launch_app", [app_name])

2. Line 127-131: health/ping/status
   → return ("health", [])

3. Line 88-103: git commands
   → return ("git", [subcommand, ...])

4. Line 110, 121: obs patterns
   → return ("obs", [text])

5. Line 135: briefing/summary
   → return ("briefing", [])

6. Line 140: capabilities
   → return ("capabilities", [])

7. Line 144: model info
   → return ("model_info", [])

8. Line 151, 157, 162: unavailable (browser, shell, cloud)
   → return ("unavailable", [reason])

9. Line 166: info (clip_extractor)
   → return ("info", [text])

10. Line 177, 193: MCP tool direct
    → return ("tool_direct", [tool_name, args])

11. Line 214, 218, 221: MCP tool preflight
    → return ("tool_preflight", [tool, params, original_text])

12. Line 82, 225: RAG fallback (catch-all)
    → return ("rag", [text])
```

### Gate 6: Execute Command (roxy_commands.py:execute_command)
**Handler Dispatch** (line 316-421):
```
if cmd_type == "git":          → git CLI subprocess
elif cmd_type == "obs":        → obs_controller.py WebSocket client
elif cmd_type == "health":     → systemctl status + temps + docker ps
elif cmd_type == "briefing":   → daily summary
elif cmd_type == "capabilities": → static tool catalog JSON
elif cmd_type == "model_info": → "ollama/llama3.2:3b"
elif cmd_type == "unavailable": → error message
elif cmd_type == "tool_direct": → MCP tool execution (UNUSED: Truth Gate not called)
elif cmd_type == "info":       → return info text
elif cmd_type == "tool_preflight": → MCP tool with context injection
elif cmd_type == "rag":        → _query_rag_impl()
elif cmd_type == "launch_app": → gtk-launch via subprocess
elif cmd_type == "status_today": → git log + evidence scan + service status
```

### Gate 7: RAG Query Path (roxy_commands.py:_query_rag_impl)
**Decision Tree**:
```
1. Try advanced RAG from /opt/roxy/services (lines 441-464)
   if use_advanced_rag and /opt/roxy/services/adapters exists:
     → get_rag_service().answer_question()
   on error:
     → fallback to basic RAG

2. Basic RAG (lines 467-539):
   a. Query expansion: _expand_query(query)
   b. Embedding: DefaultEmbeddingFunction (384-dim) [FIXED 02:40 UTC]
   c. ChromaDB query: collection.query(query_embeddings=[embedding])
   d. Hybrid reranking (if hybrid_search available)
   e. LLM synthesis: Ollama llama3.2:3b
   f. Return formatted response
```

---

## D) Tool Surface Area

### HTTP Endpoints
| Endpoint | Method | Auth | Handler | Rate Limited |
|----------|--------|------|---------|--------------|
| `/health` | GET | No | do_GET (fastpath) | No |
| `/run` | POST | Yes | _handle_run_command | Yes (10 req/min) |
| `/batch` | POST | Yes | _handle_batch_command | Yes (5 req/min) |

### Command Types (parse_command returns)
| cmd_type | Parser Lines | Handler Line | Subprocess/Tool | Status |
|----------|--------------|--------------|-----------------|--------|
| `launch_app` | 112-118 | 411 | gtk-launch | ✅ Routed early |
| `health` | 127-131 | 322 | systemctl | ✅ Works |
| `git` | 88-103 | 316 | git CLI | ✅ Works |
| `obs` | 110, 121 | 319 | obs_controller.py | ❌ WebSocket fails |
| `briefing` | 135 | 325 | subprocess | ⚠️ Untested |
| `capabilities` | 140 | 328 | static JSON | ✅ Works |
| `model_info` | 144 | 335 | static string | ✅ Works |
| `unavailable` | 151, 157, 162 | 343 | error message | ✅ Works |
| `tool_direct` | 177, 193 | 353 | MCP tool exec | ⚠️ Untested |
| `info` | 166 | 365 | static text | ✅ Works |
| `tool_preflight` | 214, 218, 221 | 368 | MCP tool | ⚠️ Untested |
| `rag` | 82, 225 | 394 | ChromaDB+Ollama | ✅ FIXED |
| `status_today` | 149-157 | 390 | git log + scan | ✅ Works |

### MCP Tools (via tool_direct/tool_preflight)
**Source**: Port 8765 MCP server `/health` response

**Git Tools**: git_status, git_commit, git_push, git_pull, git_diff, git_log  
**Docker Tools**: docker_ps, docker_logs, docker_restart, docker_stats  
**OBS Tools**: obs_status, obs_start_stream, obs_stop_stream, obs_start_recording, obs_stop_recording, obs_set_scene, obs_get_scenes  
**RAG Tools**: rag_query, rag_add, rag_count, rag_collections

---

## E) State & Storage

### 1. ChromaDB (`~/.roxy/chroma_db/`)
**Path**: `/home/mark/.roxy/chroma_db`  
**Database**: `chroma.sqlite3` (380 MB)

**Collections**:
| Collection | Count | Embedding | Dimension | Purpose |
|------------|-------|-----------|-----------|---------|
| `mindsong_docs` | 1028 | DefaultEmbeddingFunction | 384 | RAG knowledge base |
| `roxy_cache` | 8 | DefaultEmbeddingFunction | 384 | Semantic cache |

**Evidence**: `chroma_collections.txt`, `embedding_dimension_proof.txt` (384-dim confirmed)

### 2. Config Files
**`~/.roxy/config.json`**:
- `IPC_PORT`: 8766
- Cache settings, rate limits, etc.

**`~/.roxy/secret.token`**:
- Bearer token for X-ROXY-Token auth

### 3. Cache Layers
**In-Memory Cache** (roxy_core.py):
- Simple dict cache (no size limit, no TTL in code)
- Bypass for greetings and status queries

**Semantic Cache** (ChromaDB `roxy_cache` collection):
- Vector similarity matching
- **FIXED**: Now uses DefaultEmbeddingFunction (384-dim) instead of nomic-embed-text (768-dim)

### 4. Evidence Bundles
**Location**: `~/.roxy/evidence/<timestamp>/`  
**Current**: `20260102_020848/` (26 files, ~150KB)

### 5. Logs
**Systemd Journal**: `journalctl --user -u roxy-core`  
**Custom Logs**: (if any exist in `~/.roxy/logs/`)

---

## F) Invariants (PROVEN vs NOT PROVEN)

### ✅ PROVEN Invariants

1. **Single Port Listener**
   - **Invariant**: ROXY listens ONLY on 127.0.0.1:8766
   - **Evidence**: `ports_ss_RECHECK.txt`, `port_8766_lsof_RECHECK.txt`
   - **PID**: 4155786 (python, roxy_core.py)
   - **Note**: Port 8765 is MCP server (PID 11275), separate process

2. **Embedding Dimension Contract**
   - **Invariant**: All ROXY code uses 384-dim DefaultEmbeddingFunction
   - **Evidence**: `embedding_surface_scan.txt` (46 matches)
   - **FIXED**: cache.py lines 84, 137 (768-dim nomic-embed-text → 384-dim DefaultEmbeddingFunction)
   - **Status**: ✅ FIXED at 02:40 UTC

3. **Deterministic Greeting Routing**
   - **Invariant**: "hi roxy" always routes to greeting (no subprocess)
   - **Evidence**: `cli_test_1_greeting.txt`
   - **Code**: roxy_core.py:226-231 (regex fastpath)

4. **Status Query Cache Bypass**
   - **Invariant**: "what is new today" bypasses cache, routes to status_today
   - **Evidence**: `cli_test_2_status.txt`, `api_status_today_AFTER_FIX.json`
   - **Code**: roxy_commands.py:149-157 (status_today), roxy_core.py:340-348 (is_status_query)

5. **ChromaDB Collections Exist**
   - **Invariant**: mindsong_docs (1028 docs), roxy_cache (8 entries)
   - **Evidence**: `chroma_collections.txt`, `chroma_query_proof.txt`

6. **Authentication Required**
   - **Invariant**: All POST /run and /batch require X-ROXY-Token header
   - **Code**: roxy_core.py:189, 342

7. **Rate Limiting Active**
   - **Invariant**: /run: 10 req/min, /batch: 5 req/min
   - **Code**: roxy_core.py:204, 338

### ❌ NOT PROVEN Invariants

1. **Truth Gate Validation**
   - **Claim**: Tool execution is validated by track_tool_execution()
   - **Reality**: Function exists (line 47-53) but NEVER CALLED
   - **Status**: ❌ NOT IMPLEMENTED

2. **FactChecker**
   - **Claim**: Outputs are validated by FactChecker
   - **Reality**: Referenced in comments only, no implementation found
   - **Status**: ❌ NOT IMPLEMENTED

3. **Request Timeouts**
   - **Claim**: Subprocess calls have timeouts
   - **Reality**: Most subprocess.run() have NO timeout parameter
   - **Status**: ❌ NOT IMPLEMENTED (risk: hung processes)

4. **OBS Launch**
   - **Claim**: "open obs" launches OBS application
   - **Evidence**: `open_obs_api.json` → "Could not connect to OBS. Is it running with WebSocket enabled?"
   - **Status**: ❌ ROUTES TO WEBSOCKET, NOT LAUNCHER

5. **Concurrent Request Handling**
   - **Claim**: ROXY handles multiple simultaneous requests
   - **Reality**: Single-threaded BaseHTTPRequestHandler (blocking)
   - **Status**: ❌ NOT IMPLEMENTED (serial processing only)

6. **Hybrid Search Integration**
   - **Claim**: Cursor added hybrid_search.py (186 lines)
   - **File Exists**: ✅ YES (`new_files_check.txt`)
   - **Wired Into RAG**: ⚠️ UNKNOWN (code exists but usage not proven)

7. **LLM Router**
   - **Claim**: Cursor added llm_router.py (154 lines)
   - **File Exists**: ✅ YES
   - **Used Anywhere**: ⚠️ UNKNOWN (grep needed for imports)

8. **Security Module**
   - **Claim**: Cursor added security.py (181 lines)
   - **File Exists**: ✅ YES
   - **Integrated**: ⚠️ UNKNOWN

9. **Feedback Module**
   - **Claim**: Cursor added feedback.py (136 lines)
   - **File Exists**: ✅ YES
   - **Integrated**: ⚠️ UNKNOWN

### ⚠️ PARTIAL / NEEDS VALIDATION

1. **/batch Endpoint**
   - **Code**: ✅ EXISTS (roxy_core.py:187, 338-371)
   - **Tested**: ✅ WORKS (`batch_endpoint_test.txt` shows successful response)
   - **Verdict**: ✅ PROVEN

2. **Cache Semantic Matching**
   - **Collections**: roxy_cache has 8 entries
   - **Dimension Fixed**: ✅ 384-dim (matches query path now)
   - **Hit Behavior**: ⚠️ NOT TESTED (need query variations)

---

## G) File Manifest (Core Code)

### Process Entrypoints
| File | Lines | SHA256 (first 16 chars) | Role |
|------|-------|-------------------------|------|
| roxy_core.py | 725 | 2e3ac22820117331 | HTTP server, routing, cache |
| roxy_commands.py | 673 | 6dbd576940230a62 | Command parser, handler dispatcher |
| roxy_client.py | (unknown) | 125a5d635925d9b1 | CLI client |

### New Modules (Cursor "16/16 Complete")
| File | Lines | Size | Integrated? |
|------|-------|------|-------------|
| rag/hybrid_search.py | 186 | 6.3K | ⚠️ UNKNOWN |
| llm_router.py | 154 | 5.4K | ⚠️ UNKNOWN |
| feedback.py | 136 | 4.7K | ⚠️ UNKNOWN |
| security.py | 181 | 6.2K | ⚠️ UNKNOWN |

**Total New Code**: 657 lines, ~22KB

### Support Files
- `cache.py`: Semantic cache implementation (FIXED: 384-dim embeddings)
- `obs_controller.py`: OBS WebSocket client
- `rebuild_rag_index.py`: RAG collection builder
- `bootstrap_rag.py`: Initial RAG setup
- `fix_embedding_dimension.py`: Embedding migration tool

---

## H) Diagnostic Commands (Quick Reference)

### Port Verification
```bash
ss -H -lptn | grep -E ':(8765|8766)\b'
lsof -nP -iTCP:8766 -sTCP:LISTEN
```

### Service Status
```bash
systemctl --user status roxy-core
journalctl --user -u roxy-core --since "5 minutes ago" --no-pager
```

### ChromaDB Check
```bash
python3 << 'PY'
import chromadb
from pathlib import Path
client = chromadb.PersistentClient(path=str(Path.home()/".roxy"/"chroma_db"))
for c in client.list_collections():
    print(f"{c.name}: {c.count()} docs")
PY
```

### Embedding Dimension Proof
```bash
python3 << 'PY'
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
ef = DefaultEmbeddingFunction()
print("Dimension:", len(ef(["test"])[0]))
PY
```

### API Test
```bash
TOKEN=$(cat ~/.roxy/secret.token)
curl -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"command":"ping"}' http://127.0.0.1:8766/run
```

---

## I) Critical Findings Summary

### Fixes Applied (02:40 UTC)
1. **Embedding Dimension Mismatch**: cache.py lines 84, 137 (768→384)
2. **Port Documentation**: roxy_core.py line 665 (8765→8766)

### Contradictions Resolved
1. **Port 8765 vs 8766**: BOTH exist. 8765=MCP server, 8766=ROXY. No conflict.
2. **Embedding Sources**: NOW UNIFIED at 384-dim (cache.py fixed)

### Remaining Gaps
1. **Cursor Modules**: 4 files exist but integration NOT PROVEN
2. **OBS Launch**: Routes to WebSocket, not gtk-launch
3. **Truth Gate**: Code exists but never called
4. **Timeouts**: Most subprocesses lack timeout parameters

---

**Methodology**: Line-by-line code read, process inspection (ss/lsof), API testing, embedding runtime probing. All claims backed by evidence files with exact line numbers or command outputs.

**Next Actions**: Test Cursor module integration, fix OBS launcher routing, add subprocess timeouts, activate Truth Gate validation.
