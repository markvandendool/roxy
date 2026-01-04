# ROXY FULL STACK MAP
**Forensic Architecture Inventory - 2026-01-02**

## Executive Summary

**Status**: ROXY canonical stack (`~/.roxy`) is operational on single port 8766.
**Evidence**: `~/.roxy/evidence/20260102_020848/`
**Collections**: 2 (mindsong_docs: 1028 docs, roxy_cache: 8 entries)

---

## A) Process & Service Topology

### Systemd Service
- **Unit**: `roxy-core.service`
- **Binary**: `/home/mark/.roxy/venv/bin/python /home/mark/.roxy/roxy_core.py`
- **PID**: 3975632 (as of 02:05 UTC)
- **Port**: **8766** (127.0.0.1, TCP)
- **Status**: active (running)
- **Restart**: `systemctl --user restart roxy-core`

### CLI Wrapper
- **Path**: `/usr/local/bin/roxy`
- **Type**: Bash wrapper routing to `~/.roxy/venv/bin/python ~/.roxy/roxy_client.py`
- **Commands**: chat, status, start, stop, restart, logs, test, legacy
- **Port reference**: 8766 (test command uses this)

### Client
- **Script**: `~/.roxy/roxy_client.py`
- **Mode**: Interactive (default) or `--once "command"` (non-interactive)
- **Port**: Reads from `~/.roxy/config.json` or env `ROXY_PORT` (default 8766)
- **Auth**: X-ROXY-Token header from `~/.roxy/secret.token`

### Subprocess (Command Handler)
- **Script**: `~/.roxy/roxy_commands.py`
- **Invoked by**: roxy_core via subprocess.run()
- **Embedding**: DefaultEmbeddingFunction (384-dim, all-MiniLM-L6-v2)

---

## B) Code Entrypoints + Routing Graph

### Request Flow (HTTP → Response)

```
HTTP POST → roxy_core.py:handle_request()
    ↓
├─ Greeting regex? → Return greeting (no subprocess)
├─ Health endpoint? → Return {"status": "ok"}
├─ Status query? → Bypass cache (is_status_query check)
└─ _is_rag_query? → Check cache (if not bypassed)
    ↓
Cache HIT? → Return cached response
Cache MISS or bypass? → subprocess.run(roxy_commands.py)
    ↓
parse_command(text) → (cmd_type, args)
    ↓
execute_command(cmd_type, args, text) → response_text
    ↓
Return response + optionally cache
```

### parse_command() Decision Table (roxy_commands.py L74-247)

| Priority | Pattern | Route | Args |
|----------|---------|-------|------|
| 1 | Empty text | rag | [] |
| 2 | Greeting regex | greeting | [] |
| 3 | `open obs` / `launch obs` | launch_app | ["obs"] |
| 4 | `open <app>` / `launch <app>` | launch_app | [app_name] |
| 5 | "what is new", "new today", etc. | status_today | [] |
| 6 | JSON tool call | tool_direct | [tool_name, tool_args] |
| 7 | `RUN_TOOL ...` | tool_direct | [tool_name, tool_args] |
| 8 | "onboarding" in text | tool_preflight | list_files onboarding dir |
| 9 | "show me <file>" | tool_preflight | search_code for file |
| 10 | "list files" / "show files" | tool_preflight | list_files workspace |
| 11 | Unavailable tools (docker, obs) | unavailable | [tool_name] |
| 12 | **Default fallback** | rag | [original_text] |

### Cache Bypass Logic (roxy_core.py L340-348)

```python
is_status_query = any(kw in command.lower() for kw in [
    "what is new", "new today", "status today", "changes today"
])

bypass_cache = (
    is_greeting_query or      # Greetings never cache
    is_status_query or        # Status queries skip cache (CHIEF FIX)
    command.strip().startswith('{') or  # JSON tool calls
    command.startswith('RUN_TOOL ') or  # Explicit tool syntax
    self._is_file_claim_query(command)  # File-existence queries
)
```

### execute_command() Handler Map (roxy_commands.py L360-750)

| cmd_type | Handler | Tools Used | Output |
|----------|---------|------------|--------|
| greeting | Inline string | None | "Hello! I'm ROXY..." |
| launch_app | Desktop launch | pgrep, gtk-launch, Popen | "Launching..." or "Already running" |
| status_today | Git + file system | subprocess.run(git log), os.listdir | Git activity, evidence bundles, service status |
| tool_direct | execute_tool_direct() | MCP tools (git, docker, obs) | Tool JSON response |
| tool_preflight | Verify → execute_tool_direct() | list_files, search_code, then RAG | Tool result + RAG context |
| unavailable | Error message | None | "Tool X is not available yet" |
| rag | RAG pipeline | ChromaDB query, Ollama | LLM response with sources |

---

## C) Data Stores & Contracts

### ChromaDB (Vector Store)
- **Path**: `~/.roxy/chroma_db/`
- **Client**: PersistentClient
- **Collections**:
  - `mindsong_docs`: 1028 documents (RAG knowledge base)
  - `roxy_cache`: 8 semantic cache entries
- **Embedding**: DefaultEmbeddingFunction (384-dim)
- **Distance**: Cosine similarity
- **Size**: 380 MB (chroma.sqlite3)

### Config Files
- **Main**: `~/.roxy/config.json`
  - `port`: 8766
  - `host`: 127.0.0.1
- **Auth**: `~/.roxy/secret.token`
- **Logs**: `~/.roxy/logs/roxy-core.log`, `rag.log`

### Cache Layers
1. **Semantic cache**: ChromaDB `roxy_cache` collection (persistent)
2. **Greeting regex**: Pre-routing check (no cache)
3. **Health endpoint**: Pre-routing check (no cache)

---

## D) Tool Surface Area ("Neurons")

### MCP Tools (via tool_direct)

| Tool | Args | Function | Status |
|------|------|----------|--------|
| git_status | {} | Git repo status | ✅ Available |
| git_commit | {message} | Stage all + commit | ✅ Available |
| git_push | {} | Push to remote | ✅ Available |
| git_pull | {} | Pull from remote | ✅ Available |
| git_diff | {staged: bool} | Show diff | ✅ Available |
| git_log | {count: int} | Recent commits | ✅ Available |
| docker_ps | {all: bool} | List containers | ⚠️ Marked unavailable |
| docker_logs | {container, lines} | Container logs | ⚠️ Marked unavailable |
| docker_restart | {container} | Restart container | ⚠️ Marked unavailable |
| docker_stats | {} | Resource stats | ⚠️ Marked unavailable |
| obs_status | {} | OBS stream/record status | ⚠️ Marked unavailable |
| obs_start_stream | {} | Start streaming | ⚠️ Marked unavailable |
| obs_stop_stream | {} | Stop streaming | ⚠️ Marked unavailable |
| obs_start_recording | {} | Start recording | ⚠️ Marked unavailable |
| obs_stop_recording | {} | Stop recording | ⚠️ Marked unavailable |
| obs_set_scene | {scene} | Switch scene | ⚠️ Marked unavailable |
| obs_get_scenes | {} | List scenes | ⚠️ Marked unavailable |
| rag_query | {query, n_results} | Query knowledge base | ✅ Available |
| rag_add | {content, metadata} | Add document | ✅ Available |
| rag_count | {} | Document count | ✅ Available |
| rag_collections | {} | List collections | ✅ Available |

### Built-in Commands (no MCP)

| Command Type | Detection Pattern | Handler |
|--------------|-------------------|---------|
| greeting | Regex: `hi roxy\|hello roxy\|hey roxy` | Hardcoded response |
| launch_app | `open <app>\|launch <app>` | gtk-launch + pgrep |
| status_today | `what is new\|new today\|status today` | Git log + evidence scan |

### Validators (Truth Gate - ASPIRATIONAL)
- `track_tool_execution()` exists but unused
- `FactChecker` referenced but not implemented
- No rate limiting enforced

---

## E) Performance Breakdown (Measured)

### Request Timing (from logs)
- **"what is new today"** (status_today):
  - Subprocess: 361ms
  - Total: 392ms
  
- **"what is roxy"** (RAG):
  - Subprocess: 14,876ms (~15 seconds!)
  - Total: 14,885ms

### Bottlenecks
1. **First RAG query slow**: ChromaDB init + embedding model load
2. **Subprocess overhead**: ~15-30ms per invocation
3. **Ollama query**: ~14 seconds for LLM response (network call to localhost:11434)

---

## F) Known Issues & Gaps

### ✅ FIXED (2026-01-02)
1. Port confusion (8766 vs 8765 typo in logs) - **FIXED**
2. Status queries hitting cache - **FIXED** (bypass logic added)
3. launch_app blocked by unavailable check - **FIXED** (moved early)
4. pgrep false positives - **FIXED** (exact match patterns)

### ❌ NOT PROVEN / MISSING
1. **Docker tools**: Marked unavailable but not tested
2. **OBS tools**: Marked unavailable but not tested
3. **Truth Gate**: Code exists but not enforced
4. **FactChecker**: Referenced but not implemented
5. **Rate limiting**: No implementation
6. **Voice pipeline**: Separate stack in `/opt/roxy` (not integrated)

### ⚠️ OPERATIONAL RISKS
1. **RAG latency**: 15-second first query (unacceptable for voice)
2. **No request timeouts**: Subprocess can hang indefinitely
3. **No concurrent request handling**: Single-threaded server
4. **No health monitoring**: No metrics/alerting

---

## G) File Manifest (Code Entrypoints)

```
~/.roxy/
├── roxy_core.py          # HTTP server, routing, cache
├── roxy_client.py        # CLI client (interactive + --once)
├── roxy_commands.py      # parse_command + execute_command
├── config.json           # Port 8766, host 127.0.0.1
├── secret.token          # Auth token (X-ROXY-Token header)
├── chroma_db/            # ChromaDB persistent storage
│   ├── chroma.sqlite3    # Main database (380 MB)
│   ├── mindsong_docs/    # Collection: 1028 documents
│   └── roxy_cache/       # Collection: 8 cache entries
├── logs/                 # Log files
│   ├── roxy-core.log     # Main service log
│   └── rag.log           # RAG-specific log
├── evidence/             # Timestamped proof bundles
│   └── 20260102_020848/  # Latest evidence bundle
├── mcp/                  # MCP server (separate service)
│   └── mcp_server.py
└── venv/                 # Python 3.12.3 virtualenv
    └── lib/python3.12/site-packages/
        └── chromadb/     # 1.3.7 (DefaultEmbeddingFunction)
```

---

## H) Diagnostic Commands (Quick Reference)

### Service Control
```bash
systemctl --user status roxy-core
systemctl --user restart roxy-core
journalctl --user -u roxy-core -f
```

### Port Verification
```bash
ss -lptn | grep 8766
lsof -nP -iTCP:8766 -sTCP:LISTEN
```

### Health Check
```bash
curl http://127.0.0.1:8766/health
```

### CLI Test (Non-Interactive)
```bash
~/.roxy/venv/bin/python ~/.roxy/roxy_client.py --once "what is new today"
```

### ChromaDB Inspection
```bash
cd ~/.roxy && python3 - <<'PY'
import chromadb
client = chromadb.PersistentClient(path="chroma_db")
for c in client.list_collections():
    print(f"{c.name}: {c.count()} documents")
PY
```

---

**Last Updated**: 2026-01-02 02:08 UTC  
**Evidence Bundle**: `~/.roxy/evidence/20260102_020848/`  
**Status**: Operational (single port 8766, cache bypass working, CLI --once mode added)
