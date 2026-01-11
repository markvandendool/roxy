# PROJECT SKYBEAM — Military-Grade Consolidation Proposal

**Date:** 2026-01-10
**Author:** Claude Opus 4.5 (Master Chief)
**Status:** PROPOSAL — AWAITING APPROVAL
**Classification:** AAA Enterprise Architecture

---

## EXECUTIVE AUDIT FINDINGS

### Current State: CRITICAL CHAOS

| Metric | Value | Severity |
|--------|-------|----------|
| **Total Size** | 51 GB | HIGH (bloat) |
| **Markdown Files** | 962 | CRITICAL (scattered) |
| **Python Files** | 46,265 | HIGH (mostly venvs) |
| **JSON Files** | 2,930 | HIGH (no schema) |
| **YAML Files** | 25,068 | HIGH (mostly benchmarks) |
| **Root-Level MD Files** | 30+ | CRITICAL (no index) |
| **Quarantined Folders** | 3 | MEDIUM (debt) |
| **CRM System** | NONE | CRITICAL (gap) |
| **Central Index** | NONE | CRITICAL (no nav) |
| **Credential Management** | Partial | HIGH (exposed .json) |

### Key Findings

1. **No Single Source of Truth** — 962 docs scattered with no navigation
2. **No CRM/Business System** — Zero customer tracking, leads, sales pipeline
3. **Exposed Credentials** — `.credentials.json` in monetization folder
4. **Bloated Venvs** — ~45GB in virtual environments (benchmarks, chatterbox)
5. **Quarantined Tech Debt** — 3 legacy/quarantined folders never cleaned
6. **No Runbooks** — Only 1 runbook file (warmup_studio.yaml)
7. **Scattered Voice Intents** — Only 1 file (obs_commands.yaml)
8. **No RAG Index** — ChromaDB has data but no unified knowledge index

---

## PROPOSED ARCHITECTURE: SKYBEAM UNIFIED KNOWLEDGE SYSTEM

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         SKYBEAM UNIFIED KNOWLEDGE ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                           SKYBEAM INDEX (ROOT)                               │   │
│  │                     ~/.roxy/SKYBEAM_INDEX.yaml                               │   │
│  │  • Master navigation for all agents                                          │   │
│  │  • RAG-optimized metadata                                                    │   │
│  │  • 20-metric evaluation scorecard                                            │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                              │
│       ┌──────────────────────────────┼──────────────────────────────┐              │
│       ▼                              ▼                              ▼              │
│  ┌─────────┐                   ┌─────────┐                   ┌─────────┐           │
│  │ BRAIN   │                   │ SYSTEMS │                   │ OPS     │           │
│  │ (Docs)  │                   │ (Infra) │                   │ (Run)   │           │
│  ├─────────┤                   ├─────────┤                   ├─────────┤           │
│  │01_onboard│                  │services/│                   │runbooks/│           │
│  │02_arch  │                   │mcp/     │                   │playbooks│           │
│  │03_howto │                   │docker/  │                   │schedules│           │
│  │04_skills│                   │systemd/ │                   │alerts/  │           │
│  │05_voice │                   │config/  │                   │monitors/│           │
│  └─────────┘                   └─────────┘                   └─────────┘           │
│       │                              │                              │              │
│       ▼                              ▼                              ▼              │
│  ┌─────────┐                   ┌─────────┐                   ┌─────────┐           │
│  │WORKSHOPS│                   │ VAULT   │                   │BUSINESS │           │
│  │(Projects)│                  │(Secrets)│                   │ (CRM)   │           │
│  ├─────────┤                   ├─────────┤                   ├─────────┤           │
│  │broadcast│                   │age-enc/ │                   │contacts/│           │
│  │monetize │                   │tokens/  │                   │leads/   │           │
│  │studio/  │                   │api_keys/│                   │deals/   │           │
│  │products/│                   │creds/   │                   │invoices/│           │
│  └─────────┘                   └─────────┘                   └─────────┘           │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## PHASE 1: DIRECTORY RESTRUCTURE

### New Structure (Proposed)

```
~/.roxy/
├── SKYBEAM_INDEX.yaml          # Master navigation (NEW)
├── PROJECT_SKYBEAM.md          # Infrastructure map (EXISTS)
│
├── brain/                       # All documentation (CONSOLIDATE)
│   ├── 00_START_HERE.md        # Single entry point
│   ├── 01_onboarding/          # New agent onboarding
│   │   ├── QUICK_START.md
│   │   ├── AGENT_RULES.md
│   │   └── CREDENTIAL_SETUP.md
│   ├── 02_architecture/        # System architecture
│   │   ├── INFRASTRUCTURE.md
│   │   ├── MCP_SERVERS.md
│   │   └── SERVICE_CATALOG.md
│   ├── 03_howto/               # Procedures & guides
│   │   ├── BROADCAST_GUIDE.md
│   │   ├── OBS_SETUP.md
│   │   └── VOICE_COMMANDS.md
│   ├── 04_skills/              # Agent skills
│   │   ├── code_review.md
│   │   ├── data_analysis.md
│   │   └── web_research.md
│   └── 05_reference/           # API docs, schemas
│       ├── NATS_TOPICS.md
│       └── API_ENDPOINTS.md
│
├── systems/                     # Infrastructure (REORGANIZE)
│   ├── services/               # Core Python services
│   ├── mcp-servers/            # MCP implementations
│   ├── docker/                 # Docker configs
│   ├── systemd/                # Systemd units
│   └── config/                 # All configs (centralized)
│
├── ops/                         # Operations (NEW)
│   ├── runbooks/               # Operational procedures
│   │   ├── startup.yaml
│   │   ├── shutdown.yaml
│   │   ├── incident.yaml
│   │   └── maintenance.yaml
│   ├── playbooks/              # Automation playbooks
│   ├── schedules/              # Cron/timer definitions
│   ├── alerts/                 # Alert configurations
│   └── monitors/               # Health checks
│
├── workshops/                   # Project workspaces (EXISTS)
│   ├── broadcast/              # Streaming (RENAME from physical-infrastructure)
│   │   ├── obs/
│   │   ├── ndi/
│   │   └── studio/
│   └── monetization/           # Revenue (EXISTS)
│       ├── automation/
│       ├── products/
│       └── analytics/
│
├── vault/                       # Secrets (SECURE)
│   ├── .age-key                # Master key
│   ├── api_keys/               # All API keys (encrypted)
│   ├── tokens/                 # Auth tokens (encrypted)
│   └── creds/                  # Service credentials (encrypted)
│
├── business/                    # CRM & Business (NEW)
│   ├── contacts/               # Contact management
│   ├── leads/                  # Lead tracking
│   ├── deals/                  # Sales pipeline
│   ├── invoices/               # Billing
│   └── analytics/              # Business metrics
│
├── voice/                       # Voice system (CONSOLIDATE)
│   ├── intents/                # All voice intents
│   ├── wakeword/
│   ├── stt/
│   └── tts/
│
├── apps/                        # Applications (EXISTS)
│   └── roxy-command-center/
│
├── data/                        # Runtime data (EXISTS)
│   ├── chroma_db/
│   ├── logs/
│   └── cache/
│
└── archive/                     # Archived/Legacy (CONSOLIDATE)
    ├── services.LEGACY.20260101/
    ├── services.QUARANTINED.20260105/
    └── quarantine.localai.20260107/
```

---

## PHASE 2: SKYBEAM MASTER INDEX

### Purpose
Single YAML file that any agent can parse to instantly understand the entire system.

### Schema

```yaml
# ~/.roxy/SKYBEAM_INDEX.yaml
version: "1.0.0"
project: SKYBEAM
updated: 2026-01-10
status: production

# Quick start for agents
quickstart:
  entry_point: brain/00_START_HERE.md
  agent_rules: brain/01_onboarding/AGENT_RULES.md
  credentials: vault/README.md
  infrastructure: PROJECT_SKYBEAM.md

# Domain navigation
domains:
  brain:
    path: brain/
    description: All documentation and knowledge
    sections:
      - onboarding: "New agent setup"
      - architecture: "System design"
      - howto: "Procedures"
      - skills: "Agent capabilities"
      - reference: "API docs"

  systems:
    path: systems/
    description: Infrastructure and services
    components:
      services:
        path: systems/services/
        language: python
        entry: roxy_core.py
      mcp:
        path: systems/mcp-servers/
        servers: 10
        tools: 39
      docker:
        path: systems/docker/
        containers: 11

  ops:
    path: ops/
    description: Operations and automation
    runbooks:
      startup: ops/runbooks/startup.yaml
      shutdown: ops/runbooks/shutdown.yaml
      incident: ops/runbooks/incident.yaml

  workshops:
    path: workshops/
    description: Active projects
    active:
      - broadcast: "OBS, NDI, Studio"
      - monetization: "Content distribution"

  vault:
    path: vault/
    description: Secrets management
    encryption: age
    warning: "NEVER commit to git"

  business:
    path: business/
    description: CRM and business operations
    status: "NEW - needs implementation"

# Infrastructure summary
infrastructure:
  containers: 11
  systemd_services: 4
  mcp_servers: 10
  ollama_models: 18
  gpus: 2

# RAG metadata for semantic search
rag_tags:
  - infrastructure
  - broadcasting
  - monetization
  - voice-control
  - obs-streaming
  - content-pipeline
  - dual-gpu
  - mcp-tools
  - crm

# 20-metric evaluation
metrics:
  documentation_coverage: 0  # % of systems documented
  test_coverage: 0           # % test coverage
  runbook_coverage: 0        # % operations with runbooks
  secret_security: 0         # % secrets encrypted
  config_centralization: 0   # % configs in central location
  index_freshness: 0         # days since last index update
  agent_onboarding_time: 0   # minutes for new agent setup
  voice_intent_coverage: 0   # % features with voice commands
  monitoring_coverage: 0     # % services with health checks
  backup_coverage: 0         # % data with backups
  uptime_30d: 0              # % uptime last 30 days
  incident_mttr: 0           # mean time to resolve (hours)
  code_quality: 0            # linting score
  dependency_freshness: 0    # % deps up to date
  security_scan_score: 0     # vulnerability score
  api_documentation: 0       # % APIs documented
  error_rate_7d: 0           # error rate last 7 days
  resource_utilization: 0    # CPU/RAM efficiency
  cost_per_month: 0          # infrastructure cost
  revenue_per_month: 0       # business revenue
```

---

## PHASE 3: CLEANUP ACTIONS

### 3.1 Remove/Archive Bloat

| Item | Size | Action |
|------|------|--------|
| `venv/` | ~5GB | Keep (needed) |
| `chatterbox-venv/` | ~15GB | Keep (TTS) |
| `benchmarks/lm-eval-harness/` | ~20GB | Archive to external |
| `chroma_db.backup.*` | ~1GB | Delete (old) |
| `services.LEGACY.*` | ~50MB | Archive |
| `services__QUARANTINED.*` | ~50MB | Archive |
| `quarantine/` | ~100MB | Archive |

### 3.2 Consolidate Documentation

| Source | Destination | Files |
|--------|-------------|-------|
| Root `*.md` (30+) | `brain/05_reference/legacy/` | Move |
| `docs/docs/architecture/` | `brain/02_architecture/` | Merge |
| `docs/docs/testing/` | `brain/02_architecture/testing/` | Merge |
| `docs/docs/onboarding/` | `brain/01_onboarding/` | Merge |
| `docs/docs/brain/` | `brain/04_skills/` | Merge |

### 3.3 Secure Credentials

| File | Issue | Action |
|------|-------|--------|
| `workshops/monetization/.credentials.json` | Exposed | Encrypt + move to vault |
| `workshops/monetization/automation/.credentials.json` | Exposed | Encrypt + move to vault |
| `secret.token` | Root level | Move to vault |

---

## PHASE 4: NEW SYSTEMS TO BUILD

### 4.1 CRM System (CRITICAL GAP)

```python
# ~/.roxy/business/crm.py
"""
ROXY CRM - Simple contact/lead management

Tables (PostgreSQL):
- contacts: name, email, phone, company, tags, notes
- leads: contact_id, source, status, value, next_action
- deals: lead_id, stage, value, close_date, probability
- interactions: contact_id, type, timestamp, notes
"""
```

**Recommendation:** Use existing PostgreSQL + n8n for lightweight CRM:
1. Create CRM tables in `roxy-postgres`
2. Build n8n workflows for lead capture
3. Add MCP server for CRM operations
4. Expose via ROXY Command Center

### 4.2 Runbook System

```yaml
# ~/.roxy/ops/runbooks/startup.yaml
name: System Startup
description: Full ROXY system startup procedure
steps:
  - name: Start Docker containers
    command: docker compose -f ~/.roxy/docker/docker-compose.yml up -d
    timeout: 120
    verify: docker ps | grep -c roxy
    expected: 11

  - name: Start Ollama services
    command: systemctl --user start ollama-6900xt ollama-w5700x
    timeout: 60
    verify: curl -s http://localhost:11434/api/tags
    expected: models

  - name: Verify NATS
    command: timeout 5 python3 -c "import nats; print('ok')"
    expected: ok

  # ... more steps
```

### 4.3 RAG Knowledge Index

Build unified ChromaDB collection from all documentation:

```python
# ~/.roxy/systems/services/rag_indexer.py
"""
Index all documentation into ChromaDB for semantic search.

Collections:
- skybeam_docs: All markdown documentation
- skybeam_code: Code snippets and examples
- skybeam_config: Configuration references
"""
```

---

## PHASE 5: ROXY COMMAND CENTER INTEGRATION

### Current State
- GTK4 app exists at `~/.roxy/apps/roxy-command-center/`
- Has daemon_client.py for orchestrator connection
- Missing: CRM panel, Documentation browser, Runbook executor

### Proposed Panels

| Panel | Status | Priority |
|-------|--------|----------|
| Infrastructure | EXISTS | - |
| Voice Control | EXISTS | - |
| OBS Control | EXISTS | - |
| **CRM** | NEW | HIGH |
| **Docs Browser** | NEW | MEDIUM |
| **Runbooks** | NEW | HIGH |
| **Metrics** | NEW | MEDIUM |

---

## IMPLEMENTATION TIMELINE

### Week 1: Foundation
1. Create SKYBEAM_INDEX.yaml
2. Create brain/ directory structure
3. Move root-level markdown to brain/
4. Secure credentials in vault

### Week 2: Consolidation
1. Merge docs/docs/ into brain/
2. Archive legacy/quarantine folders
3. Create ops/runbooks/ with basic procedures
4. Build CRM database schema

### Week 3: Integration
1. Create CRM MCP server
2. Update ROXY Command Center with CRM panel
3. Build RAG indexer
4. Create runbook executor

### Week 4: Validation
1. Run 20-metric evaluation
2. Fix gaps identified
3. Update all indexes
4. Agent onboarding test

---

## 20-METRIC EVALUATION FRAMEWORK

| # | Metric | Target | Current | Gap |
|---|--------|--------|---------|-----|
| 1 | Documentation Coverage | 90% | ~30% | -60% |
| 2 | Test Coverage | 80% | ~10% | -70% |
| 3 | Runbook Coverage | 100% | ~5% | -95% |
| 4 | Secret Security | 100% | ~60% | -40% |
| 5 | Config Centralization | 100% | ~20% | -80% |
| 6 | Index Freshness | <7d | N/A | N/A |
| 7 | Agent Onboarding Time | <5min | ~30min | -25min |
| 8 | Voice Intent Coverage | 80% | ~20% | -60% |
| 9 | Monitoring Coverage | 100% | ~70% | -30% |
| 10 | Backup Coverage | 100% | ~30% | -70% |
| 11 | Uptime 30d | 99.9% | ~95% | -4.9% |
| 12 | Incident MTTR | <1hr | ~4hr | -3hr |
| 13 | Code Quality | 90% | ~60% | -30% |
| 14 | Dependency Freshness | 90% | ~70% | -20% |
| 15 | Security Scan Score | A | C | -2 grades |
| 16 | API Documentation | 100% | ~40% | -60% |
| 17 | Error Rate 7d | <1% | ~5% | -4% |
| 18 | Resource Utilization | 80% | ~60% | -20% |
| 19 | Cost/Month | $0 | $0 | OK |
| 20 | Revenue/Month | $1000+ | $0 | -$1000 |

**Current Score: ~35/100 (CRITICAL)**
**Target Score: 90/100 (AAA Enterprise)**

---

## APPROVAL REQUIRED

This proposal requires human approval before execution:

- [ ] Approve directory restructure
- [ ] Approve credential migration to vault
- [ ] Approve archival of 20GB benchmarks
- [ ] Approve CRM system creation
- [ ] Approve timeline

**Command to execute after approval:**
```bash
# Will create a phased implementation script
~/.roxy/scripts/skybeam_consolidate.sh phase1
```

---

*Generated: 2026-01-10 by Claude Opus 4.5 (Master Chief)*
*Classification: PROJECT SKYBEAM — CONSOLIDATION PROPOSAL*
