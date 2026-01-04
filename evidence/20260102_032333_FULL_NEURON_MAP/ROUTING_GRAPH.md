# ROUTING GRAPH - Complete Decision Point Map

**Evidence Bundle**: `20260102_032333_FULL_NEURON_MAP/`  
**Source Files**: `roxy_core.py`, `roxy_commands.py`  
**Total Gates**: 7 (HTTP → Auth → Rate → Cache → Parse → Execute → RAG)

---

## GATE 1: HTTP METHOD DISPATCH
**File**: [roxy_core.py](roxy_core.py)  
**Evidence**: `endpoints_scan.txt`

```
Line 103-110: do_GET()
    ├─ Line 105: if self.path == "/health"
    │   └─ Lines 106-109: JSON fastpath response
    │      Exit: HTTP 200 {"status": "ok", "service": "roxy-core", ...}
    └─ Else: 404 Not Found

Line 183-188: do_POST()
    ├─ Line 185: if self.path == "/run"
    │   └─ Call _handle_run_command(request_body)
    ├─ Line 187: elif self.path == "/batch"
    │   └─ Call _handle_batch_command(request_body)
    └─ Else: 404 Not Found
```

**Decision Points**:
1. GET /health → Fastpath (no auth, no rate limit)
2. POST /run → Continue to Gate 2
3. POST /batch → Continue to Gate 2
4. Anything else → 404

---

## GATE 2: AUTHENTICATION
**File**: [roxy_core.py](roxy_core.py)  
**Lines**: 189-198 (_handle_run_command), 342-351 (_handle_batch_command)

```python
# Line 189: _handle_run_command
request_headers = {k: v for k, v in self.headers.items()}
if request_headers.get("X-ROXY-Token") != ROXY_TOKEN:
    response_data = {
        "response": "Forbidden: Invalid or missing X-ROXY-Token",
        "code": 403
    }
    _send_response(self, 401, response_data)  # Note: code=403 but HTTP 401
    return

# Line 342: _handle_batch_command (identical pattern)
```

**Decision Point**:
- Header `X-ROXY-Token` matches `~/.roxy/config.json` → Continue to Gate 3
- Else → HTTP 401 Unauthorized

---

## GATE 3: RATE LIMITING
**File**: [roxy_core.py](roxy_core.py)  
**Lines**: 204-212 (_handle_run_command), 338-340 (_handle_batch_command)

```python
# Line 204: _handle_run_command
client_ip = self.client_address[0]
if not rate_limiter.check_rate_limit(client_ip, "/run"):
    response_data = {
        "response": "Too many requests. Slow down.",
        "code": 429
    }
    _send_response(self, 429, response_data)
    return

# Line 338: _handle_batch_command
if not rate_limiter.check_rate_limit(client_ip, "/batch"):
    # Same 429 response
```

**Rate Limits** (from config or defaults):
- `/run`: 10 requests/minute per IP
- `/batch`: 5 requests/minute per IP

**Decision Point**:
- Rate limit OK → Continue to Gate 4
- Else → HTTP 429 Too Many Requests

---

## GATE 4: CACHE LOOKUP
**File**: [roxy_core.py](roxy_core.py)  
**Lines**: 223-232 (_handle_run_command)

```python
# Line 223: Check if greeting
if re.search(r"^(hi|hey|hello|yo|sup)\b.*roxy", command_text, re.IGNORECASE):
    greeting_response = "Hello! I am ROXY..." 
    response_data = {"response": greeting_response, "code": 200}
    _send_response(self, 200, response_data)
    return  # Exit: Fastpath greeting (no subprocess)

# Line 228: Check if status query
if is_status_query(command_text):
    # Skip cache for status queries
    # (Continue to subprocess without cache check)

# Lines 229-232: Check semantic cache
if cache.cache_enabled and cache.query_cache(command_text):
    cached_result = cache.query_cache(command_text)
    response_data = {"response": cached_result, "code": 200}
    _send_response(self, 200, response_data)
    return  # Exit: Cache hit
```

**Decision Tree**:
1. Is greeting pattern? → Return greeting, exit
2. Is status query? → Skip cache, continue to subprocess
3. Cache enabled AND hit? → Return cached response, exit
4. Else → Continue to subprocess (Gate 5)

**Note**: /batch endpoint does NOT use cache (lines 338-371)

---

## GATE 5: PARSE COMMAND
**File**: [roxy_commands.py](roxy_commands.py) parse_command()  
**Evidence**: `parse_command_returns.txt` (24 return statements)

### Routing Priority (Top to Bottom)

```
Line 112-118: launch_app detection
    Pattern: r"\b(open|launch|start)\s+([\w\s\-]+)$" (case-insensitive)
    Return: {"cmd_type": "launch_app", "app": <matched_app>, "args": <parsed>}

Line 127-131: health check
    Conditions: "health" in cmd OR "ping" in cmd OR "check status" in cmd
    Return: {"cmd_type": "health"}

Line 88-103: git commands
    Pattern: Starts with "git " (strict)
    Sub-patterns:
        - "git commit" → check for -m flag, prompt if missing
        - "git push" → safety warning
        - Default → pass through to git CLI
    Return: {"cmd_type": "git", "git_cmd": <full_command>}

Line 110: obs commands
    Condition: cmd.startswith("obs ") (strict prefix)
    Return: {"cmd_type": "obs", "request": <obs_command>}

Line 121: obs commands (alternate)
    Pattern: r"obs\s+(.*)"
    Return: {"cmd_type": "obs", "request": <captured_request>}

Line 135: briefing
    Condition: "briefing" in cmd
    Return: {"cmd_type": "briefing"}

Line 140: capabilities
    Pattern: r"what (can you do|are your capabilities)" (case-insensitive)
    Return: {"cmd_type": "capabilities"}

Line 144: model info
    Pattern: r"(what|which) model" (case-insensitive)
    Return: {"cmd_type": "model_info"}

Line 151: unavailable (browser)
    Condition: cmd.startswith("browse ") OR "http" in cmd OR "www." in cmd
    Return: {"cmd_type": "unavailable", "reason": "Browser actions not available..."}

Line 157: unavailable (shell commands)
    Condition: cmd.startswith("run ") OR cmd.startswith("exec ")
    Return: {"cmd_type": "unavailable", "reason": "Direct shell execution not available..."}

Line 162: unavailable (cloud resources)
    Condition: r"(aws|gcp|azure)\s+" (case-insensitive)
    Return: {"cmd_type": "unavailable", "reason": "Cloud operations require tools..."}

Line 166: info (MCP server info)
    Condition: "mcp server" in cmd AND "info" in cmd
    Return: {"cmd_type": "info"}

Line 177: tool_direct (MCP tool with no context)
    Pattern: r"use\s+(\w+)\s+tool\s+(.+)" (e.g., "use git tool fetch origin")
    Return: {"cmd_type": "tool_direct", "tool": <tool_name>, "request": <tool_args>}

Line 193: tool_direct (MCP tool, alternate pattern)
    Pattern: r"(\w+)\s+tool\s+(.+)" (e.g., "git tool fetch origin")
    Return: {"cmd_type": "tool_direct", "tool": <tool_name>, "request": <tool_args>}

Line 214: tool_preflight (RAG + tool)
    Condition: "using <tool_name> tool" in cmd
    Return: {"cmd_type": "tool_preflight", "tool": <tool_name>, "request": <original_cmd>}

Line 218: tool_preflight (alternate)
    Pattern: r"with\s+(\w+)\s+tool\b"
    Return: {"cmd_type": "tool_preflight", "tool": <tool_name>, "request": <original_cmd>}

Line 221: tool_preflight (3rd variant)
    Pattern: r"(\w+)\s+tool\b" at start
    Return: {"cmd_type": "tool_preflight", "tool": <tool_name>, "request": <original_cmd>}

Line 82: rag (default fallback)
    Condition: None of the above matched
    Return: {"cmd_type": "rag", "query": <original_cmd>}

Line 225: rag (explicit - unreachable?)
    Condition: cmd.startswith("ask ") OR cmd.startswith("search ")
    Return: {"cmd_type": "rag", "query": <stripped_cmd>}
    Note: This may be unreachable because line 82 would catch these first
```

### Critical Routing Issues Found

**Issue 1: OBS Launch Routes to WebSocket**
- Command: "open obs"
- Expected: Line 112 launch_app → cmd_type=launch_app, app="obs"
- Actual: Line 110 or 121 obs → cmd_type=obs (WebSocket handler)
- **Root Cause**: obs pattern (line 110/121) matches before launch_app pattern (line 112)
- **Evidence**: `open_obs_result.json` (WebSocket error, no launch)

**Issue 2: Unreachable RAG Pattern**
- Line 225 checks for cmd.startswith("ask ") or cmd.startswith("search ")
- But line 82 (default fallback) would catch these first
- **Status**: Dead code?

---

## GATE 6: EXECUTE COMMAND
**File**: [roxy_commands.py](roxy_commands.py) execute_command()  
**Evidence**: `handler_branches.txt` (11 branches)

```
Line 316: if cmd_type == "git"
    Handler: subprocess.run(git_cmd, shell=True, ...)
    Return: Git CLI output

Line 319: elif cmd_type == "obs"
    Handler: obs_controller.execute(request)
    File: obs_controller.py (WebSocket interaction)
    Return: OBS WebSocket response OR error

Line 322: elif cmd_type == "health"
    Handler: Multi-step subprocess chain
        1. systemctl --user status roxy-core (lines 324-328)
        2. sensors (CPU temps) (lines 330-333)
        3. docker info (lines 335-338)
    Return: Formatted health report

Line 325: elif cmd_type == "briefing"
    Handler: TBD (placeholder return)
    Return: "Daily briefing coming soon."

Line 328: elif cmd_type == "capabilities"
    Handler: Static JSON
    Return: {
        "RAG": "Query indexed documentation...",
        "Git": "Execute git commands...",
        "OBS": "Control OBS Studio...",
        ...
    }

Line 335: elif cmd_type == "model_info"
    Handler: Static string
    Return: "I am using: ollama/llama3.2:3b (local)..."

Line 343: elif cmd_type == "unavailable"
    Handler: Error message
    Return: parse_result.get("reason", "This command is not available.")

Line 353: elif cmd_type == "tool_direct"
    Handler: MCP tool execution via HTTP
    Steps:
        1. POST to http://localhost:8765/execute (lines 355-361)
        2. Parse JSON response
        3. Format output
    Return: Tool execution result OR error

Line 365: elif cmd_type == "info"
    Handler: Static text
    Return: "MCP Server Info:\nRunning at: http://localhost:8765..."

Line 368: elif cmd_type == "tool_preflight"
    Handler: RAG query → MCP tool
    Steps:
        1. Query RAG for context (lines 370-375)
        2. POST to http://localhost:8765/execute (lines 377-383)
        3. Format output
    Return: RAG context + tool result

Line 394: elif cmd_type == "rag"
    Handler: _query_rag_impl() → Gate 7
    Return: RAG response
```

---

## GATE 7: RAG QUERY PATH
**File**: [roxy_commands.py](roxy_commands.py) _query_rag_impl()

### Path 1: Advanced RAG (if available)

```
Line 400-410: Try /opt/roxy/services/adapters
    1. Import advanced_rag from /opt/roxy/services/adapters
    2. Check if advanced_rag.is_available()
    3. Call advanced_rag.query(query, n_results)
    4. Return result
    5. On error: Fall through to Path 2
```

### Path 2: Basic RAG (always available)

**Entry Point**: Line 417 (via _query_with_fallback helper)

```
Step 1 (Line 428-434): Query Expansion
    Function: _expand_query(original_query)
    Logic:
        - If query < 5 words → try to add context (placeholder)
        - Return: [original_query]  (currently no expansion)

Step 2 (Line 437-440): Embedding Generation
    Function: DefaultEmbeddingFunction()
    Input: expanded_queries (list of strings)
    Output: 384-dim vectors (list of lists)
    Evidence: embedding_dim_proof.txt

Step 3 (Line 442-449): ChromaDB Query
    Collection: mindsong_docs
    Query: collection.query(
        query_embeddings=embeddings,
        n_results=n_results,  # Default 5
        include=["documents", "metadatas", "distances"]
    )
    Return: {"ids": [...], "documents": [...], "metadatas": [...], "distances": [...]}

Step 4 (Line 452-468): Hybrid Reranking (Optional)
    If hybrid_search available:
        1. Import from hybrid_search
        2. Call rerank_results(query, chroma_results)
        3. Use reranked results
    Else:
        4. Use raw ChromaDB results

Step 5 (Line 471-486): LLM Synthesis
    Model: ollama/llama3.2:3b
    Endpoint: http://localhost:11434/api/chat
    Prompt:
        System: "You are ROXY, a helpful AI assistant..."
        User: "Question: {query}\n\nContext:\n{formatted_docs}\n\nAnswer:"
    Parameters:
        - temperature: 0.1 (low randomness)
        - num_predict: 500 (max tokens)
    Output: LLM response text

Step 6 (Line 489-496): Format Response
    Structure:
        {answer}

        Sources:
        - {source_1}
        - {source_2}
        ...
```

### Critical Path: Error Recovery (FIXED)

**Before (Line 420-424, BROKEN)**:
```python
return error_recovery.execute_with_fallback(
    _query_rag_impl,
    _query_with_fallback,
    query, n_results, use_advanced_rag  # Wrong signature!
)
```

**After (FIXED)**:
```python
# Call directly - error recovery signature mismatch
return _query_with_fallback()
```

**Impact**: Error recovery was non-functional. Now uses direct call with try/except.

---

## ROUTING SUMMARY

### Total Decision Points: 7 Gates

1. **HTTP Method** (3 routes)
2. **Auth** (2 outcomes: pass/fail)
3. **Rate Limit** (2 outcomes: pass/fail)
4. **Cache** (4 paths: greeting/status/hit/miss)
5. **Parse** (24 return statements → 13 cmd_types)
6. **Execute** (11 handler branches)
7. **RAG** (2 paths: advanced/basic, 6 substeps each)

### Command Types (13)

| cmd_type | Handler | Status |
|----------|---------|--------|
| launch_app | subprocess (xdg-open, etc.) | ⚠️ ROUTING BUG (OBS) |
| git | Git CLI subprocess | ✅ Works |
| obs | obs_controller.py (WebSocket) | ✅ Works (but preempts launch) |
| health | systemctl + sensors + docker | ✅ Works |
| briefing | Placeholder | ⚠️ Not implemented |
| capabilities | Static JSON | ✅ Works |
| model_info | Static string | ✅ Works |
| unavailable | Error message | ✅ Works |
| tool_direct | MCP tool exec | ⚠️ Untested |
| info | Static text | ✅ Works |
| tool_preflight | RAG + MCP tool | ⚠️ Untested |
| rag | ChromaDB + Ollama | ✅ FIXED (error recovery) |

### Unreachable Code (1)

- Line 225: `cmd.startswith("ask ")` or `cmd.startswith("search ")`
  - **Reason**: Line 82 (default fallback to rag) catches everything first
  - **Impact**: None (functionality still works via fallback)

### Critical Bugs (2)

1. **OBS Launch Routing**
   - Pattern `obs ` (line 110/121) matches before `open obs` (line 112)
   - **Fix**: Reorder patterns OR add explicit "launch obs" check

2. **Error Recovery Signature Mismatch** (FIXED)
   - execute_with_fallback() called with wrong signature
   - **Fix Applied**: Direct call to _query_with_fallback()

---

## VERIFICATION MATRIX

| Gate | Evidence File | Status |
|------|---------------|--------|
| HTTP | endpoints_scan.txt | ✅ 3 endpoints mapped |
| Auth | (code inspection) | ✅ Lines verified |
| Rate Limit | (code inspection) | ✅ Lines verified |
| Cache | api_test_greeting.json | ✅ Greeting fastpath works |
| Parse | parse_command_returns.txt | ✅ 24 returns mapped |
| Execute | handler_branches.txt | ✅ 11 branches mapped |
| RAG | api_test_rag.json | ✅ Working after fix |

---

**End of Routing Graph**  
**Lines Mapped**: 103-496 (roxy_core.py + roxy_commands.py)  
**Decision Points**: 7 gates, 13 cmd_types, 24 parser returns, 11 handler branches
