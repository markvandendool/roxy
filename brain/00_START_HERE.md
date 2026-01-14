# ROXY BRAIN — START HERE

**Welcome, Agent. This is your single entry point to the ROXY knowledge base.**

**Last Updated:** 2026-01-10
**Status:** CONSOLIDATED (Project SKYBEAM)

---

## Quick Navigation

| Priority | Document | Purpose |
|----------|----------|---------|
| 1 | `~/.roxy/SKYBEAM_INDEX.yaml` | **Master index — PARSE FIRST** |
| 2 | `~/.roxy/PROJECT_SKYBEAM.md` | Full infrastructure map |
| 3 | `01_onboarding/AGENT_RULES.md` | Operational constraints |
| 4 | `~/.roxy/ops/runbooks/` | Operational procedures |

---

## Brain Directory Structure

| Directory | Files | Purpose |
|-----------|-------|---------|
| `01_onboarding/` | 11 | Agent onboarding, how-to guides |
| `02_architecture/` | 36 | System architecture, Citadel deployment |
| `03_howto/` | 13 | Operational guides (GPU, Wayland, etc.) |
| `04_skills/` | 1+ | Agent skills (agent-breakroom) |
| `05_reference/` | 7 | Reference documentation |
| `06_legacy/` | 120+ | Historical/archived documents |
| `plans/` | 1+ | Strategic plans (CRM integration) |

## System Overview

```
ROXY = 51GB AI Command Center
├── 11 Docker containers (PostgreSQL, Redis, NATS, Neo4j, ChromaDB, MinIO, n8n, Grafana, Prometheus, Alertmanager, cAdvisor)
├── 18 Ollama models (dual GPU: RX 6900 XT + W5700X)
├── 10 MCP servers (39+ tools)
├── Voice pipeline (STT + TTS + Wake Word)
├── Content pipeline (video → viral clips)
├── OBS streaming automation
└── MindSong integration (77 CRM components, Ghost Protocol)
```

## Common Tasks

```bash
# Check system status
~/.roxy/start-universe.sh status

# Start everything
~/.roxy/start-universe.sh full

# View logs
journalctl --user -u 'roxy-*' -f

# Publish state to NATS
python3 ~/.roxy/services/ghost_publisher.py
```

## Directory Map

| Directory | Purpose |
|-----------|---------|
| `brain/` | All documentation (this folder) |
| `services/` | Core Python services |
| `mcp-servers/` | 10 MCP servers (61+ tools) |
| `ops/` | Operations (runbooks, voice intents) |
| `docker/` | Docker compose configuration |
| `workshops/` | Active projects (broadcast, monetization) |
| `vault/` | Secrets (age-encrypted) |
| `archive/` | Legacy/quarantined code |

## Runbooks

| Runbook | Purpose |
|---------|---------|
| `ops/runbooks/startup.yaml` | 4-phase system startup |
| `ops/runbooks/shutdown.yaml` | Graceful shutdown |
| `ops/runbooks/incident.yaml` | 5 incident response procedures |
| `ops/runbooks/maintenance.yaml` | Daily/weekly/monthly maintenance |

## Voice Intents

65 voice commands mapped to all MCP tools:
- Location: `ops/voice_intents.yaml`
- Coverage: OBS, Voice, Desktop, Browser, Content, Email, Business, Social, AI

## Credentials

**Location:** `~/.roxy/vault/`
**Encryption:** age
**WARNING:** NEVER echo, cat, or commit secrets

## MindSong Resources

MindSong Juke Hub (`/home/mark/mindsong-juke-hub/`) contains:
- **77 CRM components** — Full customer relationship management
- **Ghost Protocol** — Real-time architecture visualization
- **OBS/NDI services** — Streaming automation
- **Rocky AI** — LLM routing and governance

See `SKYBEAM_INDEX.yaml` → `mindsong:` for full inventory.

---

## Next Steps

1. Parse `~/.roxy/SKYBEAM_INDEX.yaml`
2. Read `~/.roxy/PROJECT_SKYBEAM.md`
3. Understand your task
4. Check relevant section in this brain/

---
*Project SKYBEAM — 2026-01-10*
