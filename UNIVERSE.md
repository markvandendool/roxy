# 🚀 THE ROXY UNIVERSE - ONE COMMAND TO RULE THEM ALL

```
██╗   ██╗███╗   ██╗██╗██╗   ██╗███████╗██████╗ ███████╗███████╗
██║   ██║████╗  ██║██║██║   ██║██╔════╝██╔══██╗██╔════╝██╔════╝
██║   ██║██╔██╗ ██║██║██║   ██║█████╗  ██████╔╝███████╗█████╗
██║   ██║██║╚██╗██║██║╚██╗ ██╔╝██╔══╝  ██╔══██╗╚════██║██╔══╝
╚██████╔╝██║ ╚████║██║ ╚████╔╝ ███████╗██║  ██║███████║███████╗
 ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝
```

---

## ⚡ TL;DR - JUST RUN THIS

```bash
~/.roxy/start-universe.sh status   # What's running?
~/.roxy/start-universe.sh minimal  # Start essentials
~/.roxy/start-universe.sh full     # Start EVERYTHING
~/.roxy/start-universe.sh stop     # Stop all
```

---

## 🔥 THE NUMBERS

| Metric | Count |
|--------|-------|
| **Total Possible Servers** | 40 |
| **Currently Running** | 21 |
| **Actually Critical** | 17 |
| **You Need to Think About** | **1 SCRIPT** |

---

## 📊 WHAT'S RUNNING RIGHT NOW

### TIER 1: CORE BRAIN (Auto-start via systemd)
| Port | Service | Status |
|------|---------|--------|
| **8766** | ROXY Core API | 🟢 |
| **8765** | MCP Server | 🟢 systemd |
| **8767** | Pitch Detector | 🟢 |
| **9767** | Pitch Metrics | 🟢 |

### TIER 2: VOICE STACK (Home Assistant managed)
| Port | Service | Status |
|------|---------|--------|
| **10300** | Whisper STT | 🟢 |
| **10200** | Piper TTS | 🟢 |
| **10400** | Wake Word | 🟢 |
| **8004** | Chatterbox TTS | 🟢 |

### TIER 3: DOCKER INFRASTRUCTURE (docker-compose)
| Port | Service | Status |
|------|---------|--------|
| **5432** | PostgreSQL | 🟢 |
| **6379** | Redis | 🟢 |
| **5678** | n8n Workflows | 🟢 |
| **9000** | MinIO S3 | 🟢 |
| **8000** | ChromaDB | 🟢 |
| **4222** | NATS | 🟢 |

### TIER 4: MONITORING (docker-compose)
| Port | Service | URL |
|------|---------|-----|
| **9099** | Prometheus | http://localhost:9099 |
| **3030** | Grafana | http://localhost:3030 |

### TIER 5: DEV (On-Demand)
| Port | Service | Command |
|------|---------|---------|
| **9135** | Vite Dev | `pnpm dev` |
| **3847** | Podium | `bun run orchestrator` |

---

## 🎯 QUICK COMMANDS

```bash
# Add to ~/.bashrc:
alias universe='~/.roxy/start-universe.sh'
alias u='~/.roxy/start-universe.sh status'
alias uu='~/.roxy/start-universe.sh minimal'
```

---

## 🐳 DOCKER COMMANDS

```bash
# Start all infrastructure
cd ~/mindsong-juke-hub/luno-orchestrator/citadel/compose
docker compose -f docker-compose.foundation.yml -f docker-compose.monitoring.yml up -d

# Check containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Logs
docker logs -f roxy-prometheus
docker logs -f roxy-grafana
```

---

## 🔧 SYSTEMD SERVICES

```bash
# Already configured:
sudo systemctl status mcp-server      # MCP Tool API

# Enable pitch detector on boot:
sudo cp ~/.roxy/systemd/roxy-pitch.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now roxy-pitch
```

---

## 🎸 PITCH DETECTION SWARM

**Current Score: 62/100** (was 35)

| Engine | Port | Latency | Status |
|--------|------|---------|--------|
| P3_LOCAL_GPU | 8767 | **5.6ms** | 🟢 TorchCrepe |
| P1_BASIC_PITCH | browser | ~50ms | 🟢 Spotify |
| P0_ESSENTIA | browser | ~100ms | 🟢 WASM |
| P4_SWIFTF0 | TBD | ~3ms | 🔴 Placeholder |

**Consensus:** SwarmConsensusService.ts → Bayesian fusion

---

## 📁 KEY FILES

| File | Purpose |
|------|---------|
| `~/.roxy/start-universe.sh` | **THE ONE SCRIPT** |
| `~/.roxy/systemd/roxy-pitch.service` | Boot persistence |
| `~/mindsong-juke-hub/luno-orchestrator/citadel/compose/` | Docker configs |
| `~/mindsong-juke-hub/src/services/consensus/SwarmConsensusService.ts` | Bayesian fusion |

---

## ⚠️ FORBIDDEN

- ❌ Starting servers manually in random terminals
- ❌ Creating new systemd services without updating this doc
- ❌ Running `docker run` instead of `docker compose`
- ❌ Forgetting what's running

---

## ✅ THE LAW

1. **ONE SCRIPT** to start everything
2. **DOCKER COMPOSE** for infrastructure
3. **SYSTEMD** for boot persistence
4. **GRAFANA** for monitoring (localhost:3030)

---

**Last Updated:** 2026-01-04
**Servers Tamed:** 40 → 1 script
