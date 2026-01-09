# ROXY Core - Hub Architecture

**Status: ✅ DEPLOYED ON MAC STUDIO (Hub Migration 2026-01-07)**

## ⚠️ CRITICAL: Hub Location

**ROXY Hub runs on Mac Studio (10.0.0.92), NOT on this machine (ROXY Linux).**

| Component | Host | Endpoint |
|-----------|------|----------|
| ROXY Core | Mac Studio | 127.0.0.1:8766 (local only) |
| ROXY Proxy | Mac Studio | 0.0.0.0:9136 (LAN accessible) |
| Token | Mac Studio | ~/.roxy/secret.token |

**From ROXY Linux or any LAN machine:**
```bash
# Status
curl http://10.0.0.92:9136/api/status

# Tool execution
TOKEN=$(cat ~/.roxy/secret.token)
curl -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"command":"RUN_TOOL read_file {\"path\":\"/etc/hosts\"}"}' \
  http://10.0.0.92:9136/api/roxy/run
```

---

## Architecture

ROXY uses a **hub-satellite architecture**:

1. **ROXY Core** (`roxy_core.py`) - Hub service on Mac Studio
   - Runs on Mac Studio (10.0.0.92)
   - Exposes HTTP IPC on `localhost:8766` (local only)
   - Routes commands via `roxy_commands.py`
   - Handles tool execution (read_file, list_files, git_status, etc.)

2. **ROXY Proxy** (`roxy_proxy.py`) - LAN gateway on Mac Studio
   - Listens on `0.0.0.0:9136` (LAN accessible)
   - Injects X-ROXY-Token header automatically
   - Maps API paths (/api/status → /health, /api/roxy/run → /run)

3. **ROXY Client** (`roxy_client.py`) - Interactive terminal chat (optional)
   - Can run on any machine
   - Connects to hub via HTTP (10.0.0.92:9136)

## Why Hub on Mac Studio?

**Previous approach (PROBLEMATIC):**
- ❌ sshfs mount to mindsong-juke-hub caused D-state processes
- ❌ Terminal stalls due to FUSE blocking
- ❌ Hub services on ROXY Linux with network latency

**Current approach (WORKING):**
- ✅ Hub co-located with mindsong-juke-hub repository
- ✅ No sshfs mounts (eliminated root cause of stalls)
- ✅ Proxy handles LAN access with token injection
- ✅ git_status tool reads local repo directly

## Current Status

```bash
# Hub health (from any LAN machine)
$ curl http://10.0.0.92:9136/api/status
{"status": "ok", "service": "roxy-core", ...}

# Tool execution
$ TOKEN=$(cat ~/.roxy/secret.token)
$ curl -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
    -d '{"command":"RUN_TOOL git_status {}"}' \
    http://10.0.0.92:9136/api/roxy/run
{"status": "success", "result": "M file1.ts\nM file2.md\n..."}

# Available tools
- read_file: Read file contents
- list_files: List directory
- search_code: Search code
- git_status: Git status of mindsong-juke-hub (read-only)
```

## Usage

**Press Ctrl+Space anywhere** → Opens gnome-terminal with ROXY chat

In the terminal:
```
🎤 You: what's the weather?
🤖 ROXY: [response from roxy_commands.py]

🎤 You: exit
👋 Closing ROXY chat
```

## Verification Commands

```bash
# Check hub health
curl http://10.0.0.92:9136/api/status

# Check processes on Mac Studio
ssh macstudio 'lsof -iTCP:8766 -sTCP:LISTEN -nP'  # Should show Python
ssh macstudio 'lsof -iTCP:9136 -sTCP:LISTEN -nP'  # Should show Python

# Test tool execution
TOKEN=$(cat ~/.roxy/secret.token)
curl -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"command":"RUN_TOOL read_file {\"path\":\"/etc/hosts\"}"}' \
  http://10.0.0.92:9136/api/roxy/run

# Restart hub services (on Mac Studio)
ssh macstudio 'pkill -f roxy_core.py; pkill -f roxy_proxy.py'
ssh macstudio 'cd ~/.roxy && nohup python3 roxy_core.py > ~/opslogs/roxy-core.log 2>&1 &'
ssh macstudio 'cd ~/.roxy && nohup python3 roxy_proxy.py > ~/opslogs/roxy-proxy.log 2>&1 &'
```

## Files on Mac Studio

- `~/.roxy/roxy_core.py` - Hub service
- `~/.roxy/roxy_proxy.py` - LAN proxy
- `~/.roxy/roxy_commands.py` - Command router with git_status
- `~/.roxy/secret.token` - Auth token (600 permissions)
- `~/Library/LaunchAgents/com.mindsong.roxy-*.plist` - LaunchAgents
- `~/.roxy/install_daemon.sh` - Updated installer (user service, no pynput)
- **Canonical path guardrail**: `roxy_core.py` now exits if launched from `/services/` or `/opt/roxy`; keep the running copy at `~/.roxy/roxy_core.py` (see `roxy-path-doctor.sh`).
- **Canonical runtime contract**: Only supported ExecStart is `%h/.roxy/venv/bin/python %h/.roxy/roxy_core.py` with `EnvironmentFile=%h/.roxy/.env`.

## Files Deprecated

- `~/.roxy/roxy_daemon.py` - Old approach with pynput (Wayland incompatible)
- `~/.roxy/roxy-daemon.service` - Old system service (wrong target)

## Port Configuration

- **8765**: MCP server (existing infrastructure)
- **8766**: ROXY core IPC (new)

## Next Steps (Optional)

1. **Option B (GTK GUI prompt)**: Replace terminal with GTK popup window
   - Requires: `pip install PyGObject`
   - Benefit: Inline prompt instead of full terminal

2. **Option C (Voice activation)**: "Hey ROXY" wake word
   - Requires: Full voice stack (Whisper, TTS, audio pipeline)
   - Benefit: Hands-free interaction

3. **Background indexing**: Add ChromaDB auto-indexing to `roxy_core.py`
   - Benefit: Better RAG context

4. **Multi-client**: Allow multiple terminal windows to connect simultaneously
   - Benefit: Chat history preserved across sessions

## LUNA-000 CITADEL Compliance

✅ **RULE #0**: Checked for duplicates (found existing MCP server on port 8765, changed to 8766)
✅ **Evidence-based**: All claims verified with `systemctl status`, `curl`, `gsettings get`
✅ **Wayland-correct**: No global hotkey capture, uses GNOME DE integration
✅ **User service**: Runs under user session, not system-wide
✅ **Extends existing**: Routes through `roxy_commands.py`, no duplication

---

**ROXY is now a persistent, always-on AI workstation accessible via Ctrl+Space. 🚀**
