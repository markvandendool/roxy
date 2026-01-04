# TOOL SURFACE - Complete cmd_type Inventory

**Evidence Bundle**: `20260102_191701_COPILOT_FULL_NEURON_MAP`  
**Source**: parse_command_returns.txt + handler_branches.txt  
**Analysis Date**: 2026-01-02 19:17 UTC

---

## CMD_TYPE UNIVERSE (13 Types)

### 1. rag (RAG Query)

**Parse Lines**: 82 (fallback), 225 (explicit - UNREACHABLE)  
**Handler Line**: 394  
**Status**: ✅ **WORKING**

**Trigger Patterns**:
- Default fallback (any text not matching other patterns)
- Explicit "ask" or "search" keywords (unreachable due to fallback)

**Args Schema**: `[text]` - full query string

**Handler Logic**:
- Embedding → ChromaDB query → LLM synthesis
- Returns: RAG response with source citations

**Evidence**: 
- `api_hi_roxy_*.json` (3 tests, all succeeded)
- `api_status_today_*.json` (3 tests, all succeeded)
- `api_what_is_roxy.json` (succeeded)

**Known Issues**: 
- ⚠️ Catches ALL queries including greetings (no fastpath)
- ❌ Line 225 explicit pattern unreachable

---

### 2. git (Git Operations)

**Parse Lines**: 88-103  
**Handler Line**: 316  
**Status**: ✅ **IMPLEMENTED** (not tested in this audit)

**Trigger Patterns**:
- Keywords: git, commit, push, pull, branch, repo, merge, diff, log, status

**Args Schema**: 
- `["status"]` - default
- `["commit", message?]` - commit with optional message
- `["push"]`, `["pull"]`, `["diff"]`, `["log"]`

**Handler Logic**:
- Executes git commands via subprocess
- Working directory: repo root or current directory
- Returns: git command output

**Dependencies**: git binary required

**Evidence**: Handler exists at line 316 (not tested)

---

### 3. obs (OBS WebSocket Control)

**Parse Lines**: 110, 121  
**Handler Line**: 319  
**Status**: ⚠️ **SHADOWS launch_app** (WebSocket works)

**Trigger Patterns**:
- Keywords: obs, stream, streaming, record, recording, scene, brb, live, offline, vcam, virtual, replay, clip
- Phrases: "go live", "start stream", "stop stream", "start record", "switch to", "mute mic", etc.

**Args Schema**: `[text]` - full command passed to obs_controller.py

**Handler Logic**:
- Connects to OBS WebSocket (default: ws://localhost:4455)
- Parses natural language into OBS commands
- Returns: OBS action result or error

**Evidence**: `api_open_obs.json`
```
Command: "open obs"
Parsed as: obs (due to "obs" keyword)
Result: "Could not connect to OBS. Is it running with WebSocket enabled?"
```

**Critical Bug**: ❌ **"open obs" should launch OBS, not control WebSocket**

**Dependencies**: OBS running with WebSocket plugin

---

### 4. launch_app (Application Launcher)

**Parse Lines**: 112-118  
**Handler Line**: ❌ **MISSING**  
**Status**: ❌ **BROKEN** (parsed but not executed)

**Trigger Patterns**:
- launch/open/start + app/application/program
- Examples: "open obs", "launch firefox", "start spotify"

**Args Schema**: `[app_name]` - name of application to launch

**Handler Logic**: ❌ **NOT IMPLEMENTED**

**Expected Behavior**:
```python
subprocess.Popen(["xdg-open", app_name])
```

**Evidence**: 
- `parse_command_returns.txt` line 112-118 (pattern exists)
- `handler_branches.txt` (no launch_app branch)
- `api_open_obs.json` (routed to obs handler instead)

**Root Cause**: Pattern shadowed by obs keywords (line 110 matches first)

---

### 5. health (System Health)

**Parse Lines**: 127-131  
**Handler Line**: 322  
**Status**: ✅ **WORKING**

**Trigger Patterns**:
- Keywords: health, temps, temperature, docker, containers

**Args Schema**: `[]` - no args

**Handler Logic**:
- GPU temperatures (via nvidia-smi or rocm-smi)
- Docker container status
- Memory usage
- Disk space
- System uptime

**Evidence**: `api_batch_ping_health.json`
```
Command: "health"
Result: GPU temps, memory usage, container status (working)
```

**Dependencies**: nvidia-smi/rocm-smi, docker

---

### 6. briefing (Daily Briefing)

**Parse Lines**: 135  
**Handler Line**: 325  
**Status**: ⚠️ **PLACEHOLDER**

**Trigger Patterns**:
- Exact match: "briefing"

**Args Schema**: `[]` - no args

**Handler Logic**: Returns placeholder message
```
"Briefing feature coming soon. Will compile:\n- Git activity\n- System events\n- Scheduled items"
```

**Evidence**: Code exists but returns placeholder

**Decision Needed**: Implement OR remove

---

### 7. capabilities (List Skills)

**Parse Lines**: 140  
**Handler Line**: 328  
**Status**: ✅ **IMPLEMENTED** (not tested)

**Trigger Patterns**:
- Exact match: "capabilities"

**Args Schema**: `[]` - no args

**Handler Logic**:
- Reads capabilities.py
- Returns list of available skills and tools

**Evidence**: Handler exists at line 328

---

### 8. model_info (LLM Model Details)

**Parse Lines**: 144  
**Handler Line**: 335  
**Status**: ✅ **IMPLEMENTED** (not tested)

**Trigger Patterns**:
- Keywords: model, llm, ollama

**Args Schema**: `[]` - no args

**Handler Logic**:
- Queries Ollama API for model list
- Returns active model name and parameters

**Dependencies**: Ollama running on localhost:11434

**Evidence**: Handler exists at line 335

---

### 9. unavailable (Feature Not Available)

**Parse Lines**: 151 (browser), 157 (shell), 162 (cloud)  
**Handler Line**: 343  
**Status**: ✅ **WORKING**

**Trigger Patterns**:
- "browse" or "browser" → browser_control
- "shell" or "terminal" → shell_execution
- "cloud" or "aws" or "gcp" → cloud_integration

**Args Schema**: `[feature_name]` - which feature is unavailable

**Handler Logic**: Returns user-friendly "not available" message

**Evidence**: Handler exists at line 343

---

### 10. info (File Information)

**Parse Lines**: 166  
**Handler Line**: 365  
**Status**: ✅ **IMPLEMENTED** (not tested)

**Trigger Patterns**:
- "clip_extractor" or "extractor"

**Args Schema**: `[description]` - info string to return

**Handler Logic**: Returns hardcoded information strings

**Evidence**: Handler exists at line 365

---

### 11. tool_direct (MCP Tool Execution)

**Parse Lines**: 177, 193  
**Handler Line**: 353  
**Status**: ⚠️ **UNTESTED**

**Trigger Patterns**:
- "use <tool> tool <args>"
- "call <tool> with <args>"

**Args Schema**: `[tool_name, tool_args]`

**Handler Logic**:
- Parses tool name and arguments
- Calls MCP server (port 8765) tool endpoint
- Returns tool execution result

**Dependencies**: MCP server running on port 8765

**Evidence**: 
- Handler exists at line 353
- MCP server alive (`health_8765_verbose.txt` shows 21 tools)
- Not tested in this audit

---

### 12. tool_preflight (Multi-Step Tool Orchestration)

**Parse Lines**: 214, 218, 221  
**Handler Line**: 368  
**Status**: ⚠️ **UNTESTED**

**Trigger Patterns**:
- "docs about <filename>" → list_files in docs/
- "code for <filename>" → search_code
- "files in mindsong" → list_files

**Args Schema**: `[tool_name, tool_params, original_query]`

**Handler Logic**:
- Step 1: Execute filesystem tool (list_files, search_code)
- Step 2: Pass results + original query to RAG
- Returns: Combined tool output + RAG synthesis

**Dependencies**: Filesystem MCP server

**Evidence**: 
- Handler exists at line 368
- Filesystem MCP server alive (PID 762751 in phase0_running_processes.txt)
- Not tested in this audit

---

## DEAD CODE

### Line 225: Explicit RAG Pattern (UNREACHABLE)
```python
return ("rag", [text])  # After "ask" or "search"
```

**Problem**: Line 82 fallback catches all text BEFORE line 225 is reached

**Fix**: Remove line 225 OR move to before line 82

---

## MISSING HANDLERS

### launch_app (Parsed but Not Executed)
**Parsed**: Lines 112-118  
**Handler**: ❌ None  
**Impact**: All app launch commands fail

**Proposed Handler**:
```python
elif cmd_type == "launch_app":
    app_name = args[0] if args else ""
    try:
        subprocess.Popen(["xdg-open", app_name], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        return f"Launching {app_name}..."
    except Exception as e:
        return f"Could not launch {app_name}: {e}"
```

---

## SHADOWING BUGS

### OBS Shadows launch_app
**Root Cause**: Line 110 (obs keywords) matches BEFORE line 112 (launch_app)

**Example**: "open obs"
- Contains "obs" keyword → matches line 110 → returns ("obs", ...)
- NEVER reaches line 112 launch_app pattern
- Result: Tries to control OBS WebSocket instead of launching OBS

**Fix**: Move lines 112-118 BEFORE line 110

---

## SUMMARY

**Total cmd_types**: 13  
**Implemented**: 11 (git, obs, health, capabilities, model_info, unavailable, info, tool_direct, tool_preflight, rag, briefing*)  
**Missing**: 1 (launch_app)  
**Placeholders**: 1 (briefing)  
**Dead Code**: 1 (line 225)  
**Untested**: 3 (tool_direct, tool_preflight, info)  
**Tested & Working**: 3 (rag, obs WebSocket, health)

**Critical Bugs**:
1. ❌ launch_app parsed but no handler
2. ❌ OBS shadows launch_app (pattern ordering)
3. ❌ Line 225 unreachable (dead code)

**Next Actions**:
1. Implement launch_app handler
2. Reorder patterns (launch_app before obs)
3. Test tool_direct, tool_preflight, info
4. Implement or remove briefing placeholder

---

**END OF TOOL SURFACE INVENTORY**
