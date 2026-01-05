# ⚡ ROXY QUICK REFERENCE ⚡

```
 ██████╗ ███╗   ██╗███████╗     ██████╗ ██████╗ ███╗   ███╗███╗   ███╗ █████╗ ███╗   ██╗██████╗
██╔═══██╗████╗  ██║██╔════╝    ██╔════╝██╔═══██╗████╗ ████║████╗ ████║██╔══██╗████╗  ██║██╔══██╗
██║   ██║██╔██╗ ██║█████╗      ██║     ██║   ██║██╔████╔██║██╔████╔██║███████║██╔██╗ ██║██║  ██║
██║   ██║██║╚██╗██║██╔══╝      ██║     ██║   ██║██║╚██╔╝██║██║╚██╔╝██║██╔══██║██║╚██╗██║██║  ██║
╚██████╔╝██║ ╚████║███████╗    ╚██████╗╚██████╔╝██║ ╚═╝ ██║██║ ╚═╝ ██║██║  ██║██║ ╚████║██████╔╝
 ╚═════╝ ╚═╝  ╚═══╝╚══════╝     ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝
```

---

## 🔥 THE COMMAND

```bash
~/.roxy/start-universe.sh status
```

---

## 📊 PORTS TO KNOW

| PORT | WHAT | URL |
|------|------|-----|
| **3030** | GRAFANA | http://localhost:3030 |
| **9099** | PROMETHEUS | http://localhost:9099 |
| **8767** | P3_TORCHCREPE | ws://localhost:8767 |
| **8768** | P4_SWIFTF0 | ws://localhost:8768 |
| **8765** | MCP TOOLS | http://localhost:8765 |
| **8766** | ROXY BRAIN | http://localhost:8766 |
| **9135** | VITE DEV | http://localhost:9135 |
| **11434** | OLLAMA | http://localhost:11434 |

---

## 🐳 DOCKER

```bash
# All infrastructure
cd ~/mindsong-juke-hub/luno-orchestrator/citadel/compose
docker compose -f docker-compose.foundation.yml -f docker-compose.monitoring.yml up -d

# Status
docker ps --format "table {{.Names}}\t{{.Status}}"

# Logs
docker logs -f roxy-prometheus
```

---

## 🎸 PITCH DETECTION SWARM

| Engine | Latency | Status | Port |
|--------|---------|--------|------|
| P3_TORCHCREPE | **6ms** | 🟢 GPU | 8767 |
| P4_SWIFTF0 | **10ms** | 🟢 ONNX | 8768 |
| P1_BASIC_PITCH | 50ms | 🟢 Browser | - |
| P0_ESSENTIA | 100ms | 🟢 WASM | - |

**SwiftF0:** 95K params, 42× faster than CREPE, 91.8% accuracy

---

## 🚫 FORBIDDEN

- ❌ `docker run` → use compose
- ❌ Random terminal servers
- ❌ New systemd without docs
- ❌ `git commit --no-verify`
- ❌ Raw edit master-progress.json

---

## ✅ ALIASES (add to ~/.bashrc)

```bash
alias u='~/.roxy/start-universe.sh status'
alias uu='~/.roxy/start-universe.sh minimal'
alias uuu='~/.roxy/start-universe.sh full'
alias grafana='xdg-open http://localhost:3030'
```

---

## 📁 KEY FILES

| File | What |
|------|------|
| `~/.roxy/start-universe.sh` | **THE ONE SCRIPT** |
| `~/.roxy/UNIVERSE.md` | Full inventory |
| `~/mindsong-juke-hub/CLAUDE.md` | Agent context |

---

**40 SERVERS. 1 SCRIPT. 0 EXCUSES.**
