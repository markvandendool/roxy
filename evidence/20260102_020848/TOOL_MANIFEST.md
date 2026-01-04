# TOOL MANIFEST - Complete Routing & Handler Map
**Evidence Bundle**: `~/.roxy/evidence/20260102_020848/`  
**Source**: `~/.roxy/roxy_commands.py`  
**Date**: 2026-01-02 02:18 UTC

---

## Command Type Registry

| # | cmd_type | Parser Line | Handler Line | Status |
|---|----------|-------------|--------------|--------|
| 1 | `rag` | 82, 225 | 394 | ✅ EXISTS |
| 2 | `git` | 88-103 | 316 | ✅ EXISTS |
| 3 | `obs` | 110, 121 | 319 | ✅ EXISTS |
| 4 | `health` | 127, 129, 131 | 322 | ✅ EXISTS |
| 5 | `briefing` | 135 | 325 | ✅ EXISTS |
| 6 | `capabilities` | 140 | 328 | ✅ EXISTS |
| 7 | `model_info` | 144 | 335 | ✅ EXISTS |
| 8 | `unavailable` | 151, 157, 162 | 343 | ✅ EXISTS |
| 9 | `tool_direct` | 177, 193 | 353 | ✅ EXISTS |
| 10 | `info` | 166 | 365 | ✅ EXISTS |
| 11 | `tool_preflight` | 214, 218, 221 | 368 | ✅ EXISTS |

**Total Routes**: 11 command types  
**Parser Coverage**: 100% (all return paths accounted for)  
**Handler Coverage**: 100% (all cmd_type branches exist)

---

## Parser Route Breakdown (parse_command)

### Git Commands (Lines 88-103)
```python
88:  "git status" → ("git", ["status"])
93:  "git commit <msg>" → ("git", ["commit", msg])
94:  "git commit" → ("git", ["commit"])
96:  "git push" → ("git", ["push"])
98:  "git pull" → ("git", ["pull"])
100: "git diff" → ("git", ["diff"])
102: "git log" → ("git", ["log"])
103: default git → ("git", ["status"])
```

### OBS Commands (Lines 110, 121)
```python
110: "obs|stream|record" → ("obs", [text])
121: fallback OBS → ("obs", [text])
```

### Health/Status (Lines 127-131)
```python
127: "health|alive|running" → ("health", [])
129: "status" → ("health", [])
131: "ping" → ("health", [])
```

### Informational (Lines 135-144)
```python
135: "briefing|summary" → ("briefing", [])
140: "capabilities|what can" → ("capabilities", [])
144: "model|which model" → ("model_info", [])
```

### Unavailable (Lines 151-162)
```python
151: "browse|open url" → ("unavailable", ["browser_control"])
157: "run|execute" → ("unavailable", ["shell_execution"])
162: "deploy|cloud|aws" → ("unavailable", ["cloud_integration"])
```

### Info (Line 166)
```python
166: "clip_extractor.py" → ("info", ["clip_extractor.py - ..."])
```

### Tool Direct (Lines 177, 193)
```python
177: MCP tool with args → ("tool_direct", [tool_name, tool_args])
193: MCP tool simple → ("tool_direct", [tool_name, tool_args])
```

### Tool Preflight (Lines 214-221)
```python
214: "onboarding docs" → ("tool_preflight", ["list_files", {...}, text])
218: "find <filename>" → ("tool_preflight", ["search_code", {...}, text])
221: "list files" → ("tool_preflight", ["list_files", {...}, text])
```

### RAG Fallback (Lines 82, 225)
```python
82:  Early RAG (specific patterns)
225: Default RAG (catch-all)
```

---

## Handler Execution Map (execute_command)

| Handler | Line | Subprocess/Tool | Validators | Notes |
|---------|------|----------------|------------|-------|
| `git` | 316 | git CLI | None | Direct git commands |
| `obs` | 319 | OBS WebSocket | None | Port 4455, ws://localhost |
| `health` | 322 | systemd status | None | Service + temps |
| `briefing` | 325 | subprocess | None | Daily summary |
| `capabilities` | 328 | static list | None | Returns tool catalog |
| `model_info` | 335 | static | None | Returns "ollama/llama3.2:3b" |
| `unavailable` | 343 | None | None | Returns error message |
| `tool_direct` | 353 | MCP tool exec | ❌ Truth Gate (unused) | Direct tool call |
| `info` | 365 | None | None | Returns info text |
| `tool_preflight` | 368 | MCP tool exec | None | Tool with context injection |
| `rag` | 394 | ChromaDB + Ollama | None | **BROKEN: 768-dim mismatch** |

---

## External Tool Surface

### MCP Tools (via tool_direct/tool_preflight)
Available tools extracted from capabilities endpoint:
- **git_status**, git_commit, git_push, git_pull, git_diff, git_log
- **docker_ps**, docker_logs, docker_restart, docker_stats
- **obs_status**, obs_start_stream, obs_stop_stream, obs_start_recording, obs_stop_recording, obs_set_scene, obs_get_scenes
- **rag_query**, rag_add, rag_count, rag_collections

### Subprocess Invocations
- `git` (Lines 316-318): Direct git command passthrough
- `obs_controller.py` (Line 319): OBS WebSocket client
- `systemctl --user status roxy-core` (Line 322): Health check
- `roxy_commands.py` itself via subprocess.run() from roxy_core.py

---

## Critical Validators (Truth Gate, FactChecker, Rate Limiting)

| Validator | Location | Status | Evidence |
|-----------|----------|--------|----------|
| Truth Gate | Line 47-53 (track_tool_execution) | ❌ NOT CALLED | Function exists but never invoked |
| FactChecker | N/A | ❌ NOT IMPLEMENTED | Referenced in comments only |
| Rate Limiting | N/A | ❌ NOT IMPLEMENTED | No code found |
| Request Timeouts | N/A | ❌ NOT IMPLEMENTED | subprocess.run() has no timeout |
| Input Validation | N/A | ⚠️ MINIMAL | Some regex checks only |

---

## 🔴 CRITICAL ISSUE: Embedding Dimension Mismatch

**Location**: `roxy_commands.py:471`  
**Code**:
```python
embed_resp = requests.post(
    "http://localhost:11434/api/embeddings",
    json={"model": "nomic-embed-text", "prompt": expanded_query},
```

**Problem**:
- Query-time embedder: **nomic-embed-text (768-dim)**
- Collection embedder: **DefaultEmbeddingFunction (384-dim, all-MiniLM-L6-v2)**
- **Result**: Every RAG query fails with dimension mismatch

**Evidence**:
- `api_status_today_raw.json`: "Collection expecting embedding with dimension of 384, got 768"
- `api_what_is_roxy_raw.json`: Same error
- `embedding_dimension_proof.txt`: DefaultEmbeddingFunction confirmed 384-dim
- `chroma_query_proof.txt`: Direct query with DefaultEmbeddingFunction succeeds

**Fix Required**: Change line 471 to use DefaultEmbeddingFunction instead of Ollama nomic-embed-text

---

## Request Flow (Detailed)

```
1. HTTP POST /run → roxy_core.py:handle_request()
2. Auth check (X-ROXY-Token)
3. Cache lookup (unless bypass_cache=True for status queries)
4. If cache MISS → subprocess.run(["python3", "roxy_commands.py", command])
5. parse_command(text) → (cmd_type, args)
6. execute_command(cmd_type, args, text) → response
7. If cmd_type == "rag":
   a. Query expansion
   b. Ollama embedding (WRONG: 768-dim nomic-embed-text)
   c. ChromaDB query (FAILS: expects 384-dim)
   d. Ollama LLM synthesis
8. Return response (cache if appropriate)
```

---

## Completeness Assessment

### ✅ COMPLETE
- Parser route coverage (11 cmd_types, all paths lead somewhere)
- Handler branch coverage (11 handlers, all cmd_types handled)
- Git tool surface (6 commands)
- OBS tool surface (7 commands)
- Docker tool surface (4 commands)

### ❌ INCOMPLETE
- **Validators**: Truth Gate exists but not called, FactChecker missing
- **Safety**: No rate limiting, no request timeouts, minimal input validation
- **RAG**: Embedding dimension mismatch breaks all RAG queries
- **Error Handling**: Most handlers have no try/except
- **Observability**: No metrics, no structured logging

---

## Next Actions (to close proof gaps)

### P0 (CRITICAL - blocks all RAG)
1. Fix embedding dimension mismatch in roxy_commands.py:471
2. Test RAG query after fix (prove it works)

### P1 (SAFETY)
1. Add request timeouts to subprocess.run() calls
2. Activate Truth Gate validation (call track_tool_execution)
3. Implement rate limiting

### P2 (COMPLETENESS)
1. Add try/except to all handlers
2. Add structured logging (request IDs, timing)
3. Implement FactChecker

---

**Methodology**: Extracted all parser return statements and handler branches, reconciled into single source of truth. No interpretation - only line numbers and exact code.
