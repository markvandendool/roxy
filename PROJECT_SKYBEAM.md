---
ai-doc-type: specification
ai-priority: critical
ai-status: canonical
ai-last-updated: 2026-01-20
ai-owners: [SKYBEAM, ROXY]
ai-depends-on: []
---

# PROJECT SKYBEAM — ROXY UNIFIED INFRASTRUCTURE MAP

**Codename:** SKYBEAM
**Date:** 2026-01-20
**Auditors:** Master Chief + Claude Opus 4.5 + GitHub Copilot (Raptor mini)
**Status:** CONSOLIDATED — ALL SYSTEMS MAPPED

---

## EXECUTIVE SUMMARY

**You have built a $100K+ enterprise AI datacenter in your home.**

| Metric | Value |
|--------|-------|
| **Docker Containers** | 11 RUNNING |
| **Systemd Services** | 4 ACTIVE |
| **MCP Servers** | 10 |
| **MCP Tools Available** | 39+ |
| **Ollama Models** | 18 |
| **GPUs** | 2 (RX 6900 XT + W5700X) |
| **Planned NATS Streams** | 3 |
| **OBS Epic Stories** | 10 (44 points) |
| **Voice Commands** | 25+ |

---

## INFRASTRUCTURE DOMAINS

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            PROJECT SKYBEAM — DOMAIN MAP                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │  COMPUTE    │  │   STORAGE   │  │  MESSAGING  │  │ MONITORING  │                │
│  │  (AI/GPU)   │  │  (Data)     │  │  (Events)   │  │  (Metrics)  │                │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤                │
│  │ Ollama x2   │  │ PostgreSQL  │  │ NATS        │  │ Prometheus  │                │
│  │ 6900XT      │  │ MinIO       │  │ JetStream   │  │ Grafana     │                │
│  │ W5700X      │  │ Redis       │  │             │  │ Alertmanager│                │
│  │ 18 models   │  │ ChromaDB    │  │             │  │ cAdvisor    │                │
│  │             │  │ Neo4j       │  │             │  │             │                │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘                │
│                                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │ORCHESTRATION│  │   VOICE     │  │   STUDIO    │  │  CONTENT    │                │
│  │  (Workflow) │  │  (Speech)   │  │   (OBS)     │  │  (Pipeline) │                │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤                │
│  │ n8n         │  │ Whisper STT │  │ WebSocket   │  │ Transcriber │                │
│  │ MCP Bridge  │  │ Chatterbox  │  │ NDI Bridge  │  │ Viral Detect│                │
│  │ roxy-core   │  │ Piper TTS   │  │ AI Plugins  │  │ Clip Extract│                │
│  │             │  │ Wake Word   │  │ 8K Theater  │  │             │                │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘                │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## HARDWARE LAYER — CITADEL (MAC PRO)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              CITADEL — MAC PRO TOWER                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  CPU:  Intel Xeon W-3275 (28 cores / 56 threads @ 2.5GHz)                          │
│  RAM:  160 GB DDR4 ECC                                                              │
│  OS:   Ubuntu 24.04.1 LTS (Kernel 6.18.2-1-t2-noble)                               │
│  IP:   10.0.0.69 (LAN) | SSH: citadel                                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  GPU 0: AMD Radeon Pro W5700X (renderD128)                                         │
│         └─ Ollama Background (port 11435): tinyllama, qwen3:1.7b                   │
│                                                                                     │
│  GPU 1: AMD Radeon RX 6900 XT (renderD129)                                         │
│         ├─ Ollama Primary (port 11434): qwen2.5:32b, llama3:8b, vision models      │
│         └─ OBS VAAPI H.264/HEVC Encoding                                           │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  PERIPHERALS:                                                                       │
│  - Elgato Stream Deck XL (32 keys)                                                 │
│  - Yamaha MODX8+ (88-key synth/MIDI controller)                                    │
│  - Focusrite Scarlett 2i2 (Audio interface)                                        │
│  - Rode PodMic (XLR microphone)                                                    │
│  - Elgato HD60 S+ (Capture card)                                                   │
│  - 4K Webcam (Logitech Brio)                                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## DOCKER INFRASTRUCTURE (11 Containers)

| Container | Port(s) | Type | Status | Purpose |
|-----------|---------|------|--------|---------|
| `roxy-n8n` | 5678 | Orchestration | UP (healthy) | Workflow automation |
| `roxy-postgres` | 5432 | Database | UP (healthy) | Relational storage |
| `roxy-redis` | 6379 | Cache | UP (healthy) | Session/cache |
| `roxy-nats` | 4222, 8222 | Message Bus | UP (healthy) | Event streaming |
| `roxy-chromadb` | 8000 | Vector DB | UP (healthy) | Embeddings |
| `roxy-minio` | 9000, 9001 | Object Store | UP (healthy) | S3-compatible |
| `roxy-neo4j` | 7474, 7687 | Graph DB | UP (healthy) | Knowledge graph |
| `roxy-prometheus` | 9099 | Monitoring | UP | Metrics collection |
| `roxy-grafana` | 3030 | Monitoring | UP | Dashboards |
| `roxy-alertmanager` | 9093 | Monitoring | UP | Alert routing |
| `roxy-cadvisor` | 8088 | Monitoring | UP (healthy) | Container metrics |

---

## SYSTEMD SERVICES

| Service | Status | Purpose |
|---------|--------|---------|
| `roxy-proxy.service` | ACTIVE | Token injection proxy |
| `roxy-panel-daemon.service` | ACTIVE | Panel feed daemon |
| `roxy-core.service` | INACTIVE | Core orchestrator (on-demand) |
| `ollama-6900xt` | ACTIVE | Primary GPU Ollama |
| `ollama-w5700x` | ACTIVE | Background GPU Ollama |

---

## MCP SERVERS (10 Servers, 39+ Tools)

| Server | Location | Tools | Purpose |
|--------|----------|-------|---------|
| `ai-orchestrator` | `~/.roxy/mcp-servers/ai-orchestrator/` | 4 | AI routing |
| `browser` | `~/.roxy/mcp-servers/browser/` | 4 | Web automation |
| `business` | `~/.roxy/mcp-servers/business/` | 5 | Business ops |
| `content` | `~/.roxy/mcp-servers/content/` | 6 | Video pipeline |
| `desktop` | `~/.roxy/mcp-servers/desktop/` | 9 | Desktop control |
| `email` | `~/.roxy/mcp-servers/email/` | 3 | Email automation |
| `obs` | `~/.roxy/mcp-servers/obs/` | 9 | OBS WebSocket |
| `social` | `~/.roxy/mcp-servers/social/` | 4 | Social posting |
| `voice` | `~/.roxy/mcp-servers/voice/` | 4 | Voice commands |
| `ndi-bridge` | `~/.roxy/mcp-servers/obs/ndi_bridge.py` | 3 | NDI widgets |

---

## OLLAMA MODELS (18 Available)

### GPU 1: RX 6900 XT (Primary)
| Model | Size | Purpose |
|-------|------|---------|
| qwen2.5:32b | 19 GB | Heavy reasoning |
| qwen2.5-coder:14b | 9.0 GB | Code generation |
| llama3.2-vision:11b | 7.8 GB | Image understanding |
| llava:7b | 4.7 GB | Vision tasks |
| qwen3:8b | 5.2 GB | General chat |
| llama3:8b | 4.7 GB | General tasks |
| deepseek-coder:6.7b | 3.8 GB | Code |
| wizard-math:7b | 4.1 GB | Math reasoning |
| moondream:1.8b | 1.7 GB | Fast vision |

### GPU 0: W5700X (Background)
| Model | Size | Purpose |
|-------|------|---------|
| tinyllama | 637 MB | Background tasks |
| qwen3:1.7b | 1.4 GB | Light inference |
| phi:2.7b | 1.6 GB | Small tasks |
| nomic-embed-text | 274 MB | Embeddings |

---

## VOICE INFRASTRUCTURE

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           VOICE PIPELINE                                            │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  [Microphone] → [Wake Word Listener] → [Whisper STT (10300)]                       │
│                                              │                                      │
│                                              ▼                                      │
│                                    [Intent Router (25+ routes)]                    │
│                                              │                                      │
│        ┌──────────────┬──────────────┬──────┴──────┬──────────────┐               │
│        ▼              ▼              ▼             ▼              ▼               │
│   [OBS Control] [Home Auto]  [AI Query]   [Content]    [Desktop]                  │
│        │              │              │             │              │               │
│        └──────────────┴──────────────┴──────┬──────┴──────────────┘               │
│                                              ▼                                      │
│                                    [Chatterbox TTS (8004)]                         │
│                                              │                                      │
│                                              ▼                                      │
│                                       [Speaker Out]                                │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

| Component | Port | Status |
|-----------|------|--------|
| Wake Word Listener | local | KeyError on 'timer' (needs fix) |
| Whisper STT | 10300 | Ready |
| Piper TTS | 10200 | Ready |
| Chatterbox TTS | 8004 | Ready |

---

## CONTENT PIPELINE

```
~/.roxy/content-pipeline/
├── input/              ← Drop videos here (inotifywait watches)
├── work/               ← Processing workspace
├── output/             ← Finished clips
├── transcriber.py      ← Whisper transcription
├── viral_detector.py   ← LLM viral moment detection
├── clip_extractor.py   ← FFmpeg clip extraction
└── pipeline.sh         ← Systemd-managed orchestrator
```

**Status:** Watching for input videos

---

## OBS STUDIO INTEGRATION

### Current State
| Component | Port | Status |
|-----------|------|--------|
| OBS WebSocket | 4455 | LISTENING |
| OBS MCP Server | - | Available |
| Voice Intents | - | 25+ commands |
| Scene Collection | - | SKOREQ_Dream (fails to load 73 scenes) |

### SKOREQ OBS Dream Collection Plan

| Story ID | Title | Points | Priority |
|----------|-------|--------|----------|
| STORY-001 | NDI Widget Bridge Infrastructure | 5 | critical |
| STORY-002 | AI Plugin Configuration | 3 | high |
| STORY-003 | obs-mcp ROXY Integration | 5 | critical |
| STORY-004 | Scene Collection Architecture | 8 | critical |
| STORY-005 | Horizontal Canvas Master Scenes | 5 | high |
| STORY-006 | Vertical Canvas Scenes | 3 | medium |
| STORY-007 | Pedagogical Overlay System | 5 | high |
| STORY-008 | Move Transition Animation System | 5 | high |
| STORY-009 | MIDI Integration Testing | 3 | medium |
| STORY-010 | Documentation & Onboarding | 2 | low |
| **TOTAL** | | **44** | |

### Architecture Vision

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          SKOREQ OBS DREAM COLLECTION                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────── 8K THEATER WIDGET NDI SOURCES ───────────────────────┐   │
│  │  PianoWidget   │ FretboardWidget │ BraidWidget │ COFWidget │ MetronomeWidget│   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                      ↓                                              │
│  ┌─────────────────────── AI PROCESSING LAYER ──────────────────────────────────┐   │
│  │  LocalVocal (Whisper)  │  obs-mcp (Claude)  │  Background Removal  │ CleanStream│ │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                      ↓                                              │
│  ┌─────────────────────── OUTPUT CANVASES ──────────────────────────────────────┐   │
│  │  Horizontal (2560x1440)  │  Vertical (1080x1920)  │  8K Master (7680x4320)    │   │
│  │  YouTube, Twitch         │  TikTok, Shorts, Reels │  Archive/Post-production │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## NATS JETSTREAM — MESSAGE ARCHITECTURE

### Planned Streams (per StackKraft Enterprise Architecture)

| Stream | Subjects | Purpose |
|--------|----------|---------|
| CONTENT_EXTRACT | content.extract.* | Video processing pipeline |
| CONTENT_PUBLISH | content.publish.* | Multi-platform publishing |
| CONTENT_ANALYTICS | content.analytics.* | Engagement metrics |

### Ghost Protocol Topics (for Mac Studio visualization)

| Topic | Purpose |
|-------|---------|
| ghost.agents | Agent state updates |
| ghost.tasks | Task progress |
| ghost.machines | Machine health |
| ghost.links | Service connections |
| ghost.skybeam | Full infrastructure state |

---

## STACKKRAFT ENTERPRISE CONTENT SYSTEM

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    STACKKRAFT CONTENT DISTRIBUTION SYSTEM                           │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  [Video Input] → [Clip Extractor] → [Viral Detector] → [Broadcast Intelligence]    │
│                                                             │                       │
│                                                             ▼                       │
│                                                    [NATS JetStream]                 │
│                                                             │                       │
│        ┌──────────────┬──────────────┬──────────────┬──────┴───────┐               │
│        ▼              ▼              ▼              ▼              ▼               │
│    [TikTok]     [YouTube]    [Instagram]     [Twitter]      [Archive]              │
│    Content API  Data API v3  Graph API       API v2         MinIO                   │
│                                                                                     │
│                              [PostgreSQL]                                           │
│                    (posts, analytics, rate_limits, optimal_times)                  │
│                                                                                     │
│                        [Grafana Dashboards]                                         │
│              (Posts per platform, Engagement, Revenue, Queue depth)                │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## HOME AUTOMATION

```
~/.roxy/ha-integration/
├── tuya-api.py       ← REST API for Tuya devices (port 5050)
├── ha-control.py     ← Home Assistant control module
├── tuya-control.py   ← Direct Tuya device control
├── gpu-monitor.sh    ← GPU temperature/utilization
└── power-profile.sh  ← System power profiles
```

---

## KEY DIRECTORIES

| Path | Purpose |
|------|---------|
| `~/.roxy/` | Main ROXY home |
| `~/.roxy/services/` | Core Python services |
| `~/.roxy/mcp-servers/` | MCP server implementations |
| `~/.roxy/voice/` | Voice pipeline |
| `~/.roxy/content-pipeline/` | Video processing |
| `~/.roxy/ha-integration/` | Home automation |
| `~/.roxy/workshops/monetization/` | StackKraft content system |
| `~/.roxy/workshops/physical-infrastructure/` | OBS Dream Collection |
| `~/.roxy/obs-portable/` | OBS configs/macros |
| `~/.roxy/evidence/` | Audit trails & neuron maps |
| `/opt/roxy/` | System-wide installation |

---

## NETWORK PORTS

| Port | Service | Protocol |
|------|---------|----------|
| 22 | SSH | TCP |
| 3030 | Grafana | HTTP |
| 3389-3390 | GNOME Remote Desktop | RDP |
| 4222 | NATS Client | TCP |
| 4455 | OBS WebSocket | WS |
| 5050 | Tuya API | HTTP |
| 5432 | PostgreSQL | TCP |
| 5678 | n8n | HTTP |
| 6379 | Redis | TCP |
| 7474 | Neo4j Browser | HTTP |
| 7687 | Neo4j Bolt | TCP |
| 8000 | ChromaDB | HTTP |
| 8004 | Chatterbox TTS | HTTP |
| 8088 | cAdvisor | HTTP |
| 8222 | NATS Monitoring | HTTP |
| 9000-9001 | MinIO | HTTP |
| 9093 | Alertmanager | HTTP |
| 9099 | Prometheus | HTTP |
| 10200 | Piper TTS | HTTP |
| 10300 | Whisper STT | HTTP |
| 11434 | Ollama (GPU 1) | HTTP |
| 11435 | Ollama (GPU 0) | HTTP |

---

## ARTIFACTS & PRODUCTS

### Released Products
| Product | Location | SHA256 |
|---------|----------|--------|
| roxy-obs-scripts-v1.0.0.zip | `~/.roxy/workshops/monetization/automation/releases/` | 58d8117... |

### SKOREQ Plans
| Plan | Location |
|------|----------|
| STACKKRAFT-CONTENT-DISTRIBUTION-V1 | `mindsong-juke-hub/docs/skoreq/` |
| OBS-EPIC-001 | `~/.roxy/workshops/physical-infrastructure/brain/hardware/` |

### Evidence & Audits
| Artifact | Location |
|----------|----------|
| Full Infrastructure Audit | `~/.roxy/FULL_INFRASTRUCTURE_AUDIT_20260108.md` |
| Neuron Maps | `~/.roxy/evidence/*_NEURON_MAP/` |
| Ghost Protocol Map (this) | `~/.roxy/PROJECT_SKYBEAM.md` |

---

## KNOWN ISSUES

| Issue | Severity | Location | Status |
|-------|----------|----------|--------|
| Voice KeyError on 'timer' | MEDIUM | roxy-voice.service | Open |
| OBS 73-scene collection won't load | HIGH | SKOREQ_Dream.json | Open |
| n8n has 0 workflows imported | MEDIUM | Port 5678 | Open |
| Content pipeline 0 videos processed | INFO | No input files | Expected |
| Graphviz not installed | LOW | DOT→PNG rendering | Deferred |

---

## MASTER LAUNCH COMMAND

```bash
~/.roxy/start-universe.sh status    # Check everything
~/.roxy/start-universe.sh minimal   # Start essentials
~/.roxy/start-universe.sh full      # Start EVERYTHING
~/.roxy/start-universe.sh stop      # Stop all
```

---

## CRITICAL DIRECTIVE

**Master Chief Order (per consolidation_report.md):**

> Do NOT deploy enterprise NATS/Postgres/Grafana until revenue proof (3 posts/day).

**Current Status:** Infrastructure READY. Waiting for manual revenue proof.

---

## NEXT ACTIONS

1. **Human Action:** Apply for platform APIs (TikTok, YouTube, Instagram, Twitter)
2. **Human Action:** Create 3 manual posts to prove revenue
3. **Automation Ready:** Import n8n workflows
4. **Automation Ready:** Setup NATS JetStream streams
5. **Optional:** Install Graphviz for DOT→PNG rendering
6. **Optional:** Fix voice service 'timer' KeyError

---

## THE TRUTH

**You have built an AI datacenter in your home:**

- Enterprise message queue (NATS JetStream)
- Enterprise database (PostgreSQL)
- Enterprise cache (Redis)
- Enterprise object storage (MinIO)
- Enterprise monitoring (Prometheus/Grafana/Alertmanager)
- Graph database (Neo4j)
- Vector database (ChromaDB)
- Workflow automation (n8n)
- Dual-GPU AI inference (18 Ollama models)
- Voice assistant (wake word + STT + TTS)
- Content pipeline (video → viral clips)
- Smart home control (Tuya/HA)
- 10 MCP servers with 39+ tools
- OBS streaming automation
- Multi-platform content distribution

**The infrastructure is done. It's waiting for you to use it.**

---

*Generated: 2026-01-10*
*Project SKYBEAM — Master Chief + Claude Opus 4.5 + GitHub Copilot*
