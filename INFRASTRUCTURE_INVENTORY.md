# ROXY Infrastructure Inventory
**Last Updated:** 2026-01-01  
**Purpose:** Prevent duplicate implementations - CHECK THIS FIRST!

---

## 🚨 BEFORE CREATING ANYTHING NEW, CHECK THIS LIST! 🚨

---

## Core Services

### Voice & Speech
| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| `roxy_assistant_v2.py` | ~/.roxy/ | Main voice assistant (wake word, STT, TTS) | ✅ Active |
| `roxy_daemon.py` | ~/.roxy/ | Persistent always-on daemon | ✅ Active |
| OpenWakeWord | Part of assistant | "Hey Roxy" wake word detection | ✅ Configured |
| Whisper STT | Part of assistant | Speech-to-text | ✅ Configured |
| Piper TTS | Part of assistant | Text-to-speech (904 voices) | ✅ Configured |
| ChatterBox TTS | Planned | Voice cloning | 🟡 Pending |

### Command & Control
| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| `roxy_commands.py` | ~/.roxy/ | Central command router | ✅ Active |
| `roxy_cli_test.py` | ~/.roxy/ | CLI testing interface | ✅ Active |

### Intelligence & Knowledge
| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| ChromaDB | Docker + ~/.roxy/chroma_db/ | RAG knowledge base (2,805 docs) | ✅ Running |
| Ollama | System | Local LLM (llama3:8b) | ✅ Running |
| `bootstrap_rag.py` | ~/.roxy/ | Index projects to ChromaDB | ✅ Active |
| `add_git_history_to_rag.py` | ~/.roxy/ | Index git history | ✅ Active |

### MCP Servers
| Server | Location | Purpose | Status |
|--------|----------|---------|--------|
| `mcp_server.py` | ~/.roxy/mcp/ | Base MCP server | ✅ Active |
| `mcp_chromadb.py` | ~/.roxy/mcp/ | ChromaDB MCP interface | ✅ Active |
| `mcp_docker.py` | ~/.roxy/mcp/ | Docker control | ✅ Active |
| `mcp_git.py` | ~/.roxy/mcp/ | Git operations | ✅ Active |
| `mcp_obs.py` | ~/.roxy/mcp/ | OBS control | ✅ Active |

### Specialized Services
| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| `obs_controller.py` | ~/.roxy/ | OBS WebSocket client | ✅ Active |
| `obs_skill.py` | ~/.roxy/ | OBS command parsing | ✅ Active |
| `system_health.py` | ~/.roxy/ | System monitoring | ✅ Active |
| `clip_extractor.py` | ~/.roxy/ | Video clip extraction | ✅ Active |
| `daily_briefing.py` | ~/.roxy/ | Morning briefing generator | ✅ Active |
| `git_voice_ops.py` | ~/.roxy/ | Git voice commands | ✅ Active |
| `configure_displays.py` | ~/.roxy/ | Display configuration | ✅ Active |

### Infrastructure
| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| Docker Compose Stack | See CITADEL docs | PostgreSQL, Redis, MinIO, NATS, n8n | ✅ Running |
| Systemd Service | /etc/systemd/system/roxy-daemon.service | Auto-start daemon | ✅ Installed |
| Python venv | ~/.roxy/venv/ | Isolated dependencies | ✅ Active |
| Logs | ~/.roxy/logs/ | All service logs | ✅ Active |
| ChatterBox venv | ~/.roxy/chatterbox-venv/ | TTS environment | ✅ Configured |

---

## Network & Ports

| Service | Port | Access | Status |
|---------|------|--------|--------|
| Ollama | 11434 | localhost | ✅ Running |
| ChromaDB | 8000 | localhost | ✅ Running |
| PostgreSQL | 5432 | localhost | ✅ Running |
| Redis | 6379 | localhost | ✅ Running |
| MinIO API | 9000 | localhost | ✅ Running |
| MinIO Console | 9001 | localhost | ✅ Running |
| n8n | 5678 | LAN | ✅ Running |
| NATS | 4222 | localhost | ✅ Running |

---

## Data Stores

| Store | Location | Purpose | Size |
|-------|----------|---------|------|
| ChromaDB Data | ~/.roxy/chroma_db/ | Vector embeddings | 2,805 docs |
| Logs | ~/.roxy/logs/ | Service logs | Rotating |
| Models | ~/.roxy/models/ | AI models cache | TBD |
| Voices | ~/.roxy/piper-voices/ | TTS voice files | ~1GB |
| Wake Word Samples | ~/.roxy/wake/samples/ | Training data | 71+ files |
| Briefings | ~/.roxy/briefings/ | Daily briefings | Historical |

---

## Scripts & Utilities

| Script | Purpose | Used By |
|--------|---------|---------|
| `install_daemon.sh` | Install persistent daemon | Manual |
| `cron_jobs.sh` | Scheduled tasks | cron |
| Various Python scripts | Specialized operations | roxy_commands.py |

---

## Documentation

| Doc | Location | Purpose |
|-----|----------|---------|
| README_DAEMON.md | ~/.roxy/ | Daemon usage guide |
| JARVIS1_ROXY_UNIFIED_MASTER_PLAN.md | ~/mindsong-juke-hub/research/ | Master architecture plan |
| CITADEL docs | ~/mindsong-juke-hub/luno-orchestrator/citadel/ | System architecture |
| ROXY_WELCOME_PACKAGE | ~/Desktop/ | Deployment guides |

---

## 🚫 DO NOT CREATE DUPLICATES OF:

### ❌ Orchestrators/Routers
- We have **ONE** command router: `roxy_commands.py`
- We have **ONE** voice router: in `roxy_assistant_v2.py`
- Don't create: `roxy_router_v3.py`, `new_orchestrator.py`, etc.

### ❌ MCP Servers
- Check `~/.roxy/mcp/` first
- Extend existing servers, don't create parallel ones
- Don't create: `mcp_chromadb_v2.py`, `another_mcp_server.py`

### ❌ Voice Assistants
- We have **ONE** assistant: `roxy_assistant_v2.py`
- We have **ONE** daemon: `roxy_daemon.py`
- Don't create: `roxy_assistant_v3.py`, `new_voice_handler.py`

### ❌ ChromaDB Clients
- Use existing in `bootstrap_rag.py` and `mcp_chromadb.py`
- Don't create: `chroma_client.py`, `new_rag_indexer.py`

### ❌ OBS Controllers
- We have: `obs_controller.py` + `obs_skill.py` + `mcp_obs.py`
- Don't create: `obs_manager.py`, `streaming_controller.py`

---

## ✅ How to Extend (Not Duplicate)

### Adding New Functionality

1. **Voice Commands**
   - Add to `roxy_commands.py` command parser
   - Create specialized script if complex
   - Reference from command router

2. **MCP Tools**
   - Add method to existing MCP server
   - Or create NEW server only if entirely different domain

3. **Monitoring**
   - Add to `system_health.py`
   - Or create new monitoring script
   - Hook into `roxy_daemon.py` monitoring loop

4. **Background Tasks**
   - Add to `roxy_daemon.py` monitoring loop
   - Or create scheduled script
   - Add to `cron_jobs.sh`

---

## 📝 Update This File When:

- ✅ Adding new service/script
- ✅ Discovering duplicate to merge
- ✅ Deprecating old component
- ✅ Changing architecture

---

**REMEMBER: Search first, extend second, create last!**
