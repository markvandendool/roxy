---
skill: roxy-agent-breakroom
version: 1.0.0
domain: coordination
primary_files: [~/.roxy/services/ghost_publisher.py, ~/.roxy/SKYBEAM_INDEX.yaml]
dependencies: [nats, postgresql, supabase]
keywords: [agent, breakroom, coordination, roxy, infrastructure, ghost-protocol]
last_audit: 2026-01-10
quality_score: 8.5/10
---

# ROXY Agent Breakroom - Infrastructure Coordination

## Quick Reference (50 words max)
Multi-agent coordination for ROXY infrastructure. Agents MUST: check SKYBEAM_INDEX.yaml first, use Ghost Protocol for state, follow runbooks for operations. Supports 11 Docker containers, 10 MCP servers (61+ tools), dual Ollama GPUs. All infrastructure work goes through NATS topics.

## Architecture Diagram (ASCII)
```
+---------------------------------------------------------------------+
|              ROXY AGENT COORDINATION SYSTEM                         |
+---------------------------------------------------------------------+
|                                                                     |
|  +-------------------+    +-------------------+                     |
|  | SKYBEAM INDEX     |    | GHOST PROTOCOL    |                     |
|  | ~/.roxy/          |    | NATS Publisher    |                     |
|  | SKYBEAM_INDEX.yaml|    | ghost.skybeam.*   |                     |
|  | (READ FIRST)      |    |                   |                     |
|  +-------------------+    +-------------------+                     |
|           |                        |                                |
|           v                        v                                |
|  +-------------------+    +-------------------+                     |
|  | BRAIN STRUCTURE   |    | RUNBOOKS          |                     |
|  | ~/.roxy/brain/    |    | ~/.roxy/ops/      |                     |
|  | 00_start          |    | runbooks/         |                     |
|  | 01_onboarding     |    | - startup.yaml    |                     |
|  | 02_architecture   |    | - shutdown.yaml   |                     |
|  | 03_howto          |    | - incident.yaml   |                     |
|  | 04_skills         |    | - maintenance.yaml|                     |
|  | 05_reference      |    +-------------------+                     |
|  | 06_legacy         |                                              |
|  +-------------------+                                              |
|                                                                     |
+---------------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------------+
|                     MCP SERVERS (10 servers, 61+ tools)             |
+---------------------------------------------------------------------+
| ai-orchestrator | browser | business | content | desktop | email   |
| obs | social | voice | ndi-bridge                                  |
+---------------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------------+
|                     INFRASTRUCTURE LAYER                            |
+---------------------------------------------------------------------+
| DOCKER (11)        | OLLAMA (2 GPUs)    | SYSTEMD (5)              |
| roxy-nats          | 6900XT (11434)     | roxy-proxy               |
| roxy-postgres      | W5700X (11435)     | ghost-publisher          |
| roxy-chromadb      | 18 models          | ollama-6900xt            |
| roxy-redis         |                    | ollama-w5700x            |
| roxy-neo4j         |                    | roxy-panel-daemon        |
| roxy-minio         |                    |                          |
| roxy-grafana       |                    |                          |
| roxy-prometheus    |                    |                          |
| roxy-alertmanager  |                    |                          |
| roxy-cadvisor      |                    |                          |
| roxy-n8n           |                    |                          |
+---------------------------------------------------------------------+
```

## Agent Onboarding Checklist

1. **READ FIRST** (in order):
   - `~/.roxy/SKYBEAM_INDEX.yaml` — Master navigation index
   - `~/.roxy/PROJECT_SKYBEAM.md` — Full infrastructure map
   - `~/.roxy/brain/00_START_HERE.md` — Quick start

2. **UNDERSTAND DOMAINS**:
   - MCP Servers: `~/.roxy/mcp-servers/`
   - Services: `~/.roxy/services/`
   - Voice: `~/.roxy/voice/`
   - Content Pipeline: `~/.roxy/content-pipeline/`
   - OBS: `~/.roxy/obs-portable/`
   - Home Automation: `~/.roxy/ha-integration/`

3. **KNOW THE OPERATIONS**:
   - Startup: `~/.roxy/ops/runbooks/startup.yaml`
   - Shutdown: `~/.roxy/ops/runbooks/shutdown.yaml`
   - Incidents: `~/.roxy/ops/runbooks/incident.yaml`
   - Maintenance: `~/.roxy/ops/runbooks/maintenance.yaml`

## Activity Types (ROXY-Specific)

| Activity | Description | NATS Topic |
|----------|-------------|------------|
| `infrastructure_check` | System health check | ghost.skybeam.machines |
| `mcp_tool_call` | MCP tool invocation | ghost.skybeam.agents |
| `service_restart` | Container/service restart | ghost.skybeam.links |
| `config_change` | Configuration update | ghost.skybeam.full |
| `voice_command` | Voice intent processed | ghost.voice.* |
| `discovery_posted` | New finding shared | ghost.discoveries |

## NATS Topics for Agent Coordination

```yaml
# Infrastructure State
ghost.skybeam.machines:    # Docker + systemd status
ghost.skybeam.agents:      # Ollama models + GPUs
ghost.skybeam.links:       # Port health checks
ghost.skybeam.full:        # Complete snapshot

# Planned (not yet implemented)
ghost.crm.contacts:        # CRM contact changes
ghost.crm.deals:           # Deal pipeline updates
ghost.content.extract:     # Video processing
ghost.content.publish:     # Multi-platform publishing
```

## Agent Rules (MANDATORY)

### NEVER DO:
- Edit master configs without backup
- Restart services during active recordings
- Change Ollama GPU assignments without checking rocm-smi
- Push to production without testing voice commands
- Create new containers without updating docker-compose.yml
- Modify runbooks without testing

### ALWAYS DO:
- Check SKYBEAM_INDEX.yaml before any work
- Publish state via ghost_publisher.py after changes
- Follow runbooks for operational procedures
- Test MCP tools before assuming they work
- Use voice intents from `~/.roxy/ops/voice_intents.yaml`
- Document discoveries in brain/ structure

## Common Agent Tasks

### Check System Health
```bash
~/.roxy/start-universe.sh status
```

### Publish Infrastructure State
```bash
python3 ~/.roxy/services/ghost_publisher.py
```

### Restart a Container
```bash
docker restart roxy-<container>
```

### Check Ollama Models
```bash
ollama list  # Port 11434 (6900XT)
```

### View Logs
```bash
journalctl --user -u 'roxy-*' -f
```

## File Authority Matrix

| File/Path | Authority | Agent Access |
|-----------|-----------|--------------|
| `SKYBEAM_INDEX.yaml` | SKYBEAM | READ-FIRST |
| `PROJECT_SKYBEAM.md` | SKYBEAM | READ-ONLY |
| `ops/runbooks/*.yaml` | OPS | EXECUTE |
| `services/*.py` | DEV | MODIFY w/ backup |
| `mcp-servers/*/` | DEV | MODIFY w/ testing |
| `docker/docker-compose.yml` | INFRA | MODIFY w/ approval |
| `vault/` | SECRETS | NEVER EXPOSE |

## Integration with MindSong

ROXY integrates with MindSong Juke Hub for:
- **CRM**: 77 React components in `~/mindsong-juke-hub/src/components/crm/`
- **Ghost Protocol**: Widget at `~/mindsong-juke-hub/src/components/theater8k/widgets/ghost-protocol/`
- **ROXY Page**: `~/mindsong-juke-hub/src/pages/RoxyPage.tsx`

## Quick Reference Card

| Need | Command/Location |
|------|-----------------|
| Start all | `~/.roxy/start-universe.sh full` |
| Stop all | `~/.roxy/start-universe.sh stop` |
| Check status | `~/.roxy/start-universe.sh status` |
| View index | `~/.roxy/SKYBEAM_INDEX.yaml` |
| Runbooks | `~/.roxy/ops/runbooks/` |
| Voice intents | `~/.roxy/ops/voice_intents.yaml` |
| MCP servers | `~/.roxy/mcp-servers/` |
| Vault | `~/.roxy/vault/` |
| Brain | `~/.roxy/brain/` |

## Compliance Checklist

- [ ] Read SKYBEAM_INDEX.yaml before any work
- [ ] Understand the infrastructure map
- [ ] Know which runbook applies to your task
- [ ] Test changes before deploying
- [ ] Publish state after changes
- [ ] Document discoveries
- [ ] Never expose vault secrets
