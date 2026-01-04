# ROXY Persistent Daemon

**Status:** ✅ INSTALLED - Extends existing ROXY infrastructure  
**Purpose:** Make ROXY always-on and omnipresent like JARVIS

---

## 🎯 What This Does

This daemon **extends** (not replaces) the existing ROXY infrastructure to provide:

### ✅ Always-On Presence
- Background service that runs 24/7
- Auto-starts on boot (via systemd)
- Survives system reboots

### ⌨️ Global Hotkey Access
- **Ctrl+Space** anywhere → instant ROXY chat
- Works across all applications
- No need to switch to terminal

### 🎤 Voice Integration
- Leverages existing `roxy_assistant_v2.py`
- "Hey Roxy" wake word (when voice enabled)
- Hands-free interaction

### 🧠 Intelligent Monitoring
- Auto-indexes all projects to ChromaDB
- Periodic system health checks
- Proactive suggestions (future)

---

## 📋 Prerequisites

Already installed (from existing ROXY setup):
- ✅ `roxy_assistant_v2.py` - Voice assistant
- ✅ `roxy_commands.py` - Command router
- ✅ `system_health.py` - Health monitoring
- ✅ ChromaDB - Knowledge base
- ✅ Ollama - Local LLM

New dependencies:
- `pynput` - For global hotkeys

---

## 🚀 Quick Start

### Install
```bash
cd ~/.roxy
chmod +x install_daemon.sh
./install_daemon.sh
```

### Run Manually (Test Mode)
```bash
~/.roxy/venv/bin/python ~/.roxy/roxy_daemon.py
```

### Run as Service (Production)
```bash
sudo systemctl enable roxy-daemon
sudo systemctl start roxy-daemon
```

### Check Status
```bash
# Service status
sudo systemctl status roxy-daemon

# Live logs
journalctl -u roxy-daemon -f

# File logs
tail -f ~/.roxy/logs/roxy_daemon_*.log
```

---

## 🎮 Usage

### Global Hotkey
1. Press **Ctrl+Space** anywhere on your system
2. Terminal chat interface opens
3. Type your query, get instant response
4. Type `exit` to close

### Voice Activation (if enabled)
1. Say **"Hey Roxy"**
2. Speak your command
3. ROXY responds via TTS

### Terminal
```bash
# Direct command
~/.roxy/venv/bin/python ~/.roxy/roxy_commands.py "git status"

# Or use existing scripts
~/.roxy/system_health.py
~/.roxy/obs_controller.py status
```

---

## 🔧 Architecture

```
┌─────────────────────────────────────────────┐
│         ROXY Persistent Daemon              │
├─────────────────────────────────────────────┤
│                                             │
│  INPUTS:                                    │
│  ├── Global Hotkey (Ctrl+Space)            │
│  ├── Voice ("Hey Roxy")                    │
│  └── File Watchers (future)                │
│                                             │
├─────────────────────────────────────────────┤
│                                             │
│  CORE (Extends Existing):                  │
│  ├── roxy_assistant_v2.py (voice)          │
│  ├── roxy_commands.py (routing)            │
│  ├── ChromaDB (RAG)                        │
│  └── Ollama (LLM)                          │
│                                             │
├─────────────────────────────────────────────┤
│                                             │
│  BACKGROUND TASKS:                          │
│  ├── Project indexing to ChromaDB          │
│  ├── System health monitoring              │
│  ├── Proactive suggestions (future)        │
│  └── Event watchers (future)               │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 📁 Files Created

```
~/.roxy/
├── roxy_daemon.py          # Main daemon (NEW)
├── roxy-daemon.service     # Systemd service (NEW)
├── install_daemon.sh       # Installer (NEW)
├── README_DAEMON.md        # This file (NEW)
│
├── roxy_assistant_v2.py    # EXTENDED (existing)
├── roxy_commands.py        # EXTENDED (existing)
├── system_health.py        # USED (existing)
├── bootstrap_rag.py        # USED (existing)
└── logs/                   # Daemon logs
```

---

## 🎯 Future Enhancements

### Phase 2: IDE Integration
- LSP server for VS Code/Cursor
- Inline code suggestions
- Multi-file edits
- Autonomous refactoring

### Phase 3: Advanced Monitoring
- Git hook integration
- File change notifications
- Error auto-detection
- Proactive fixes

### Phase 4: UI Improvements
- Qt/GTK floating window
- System tray icon
- Rich chat interface
- Visual notifications

### Phase 5: Multi-Modal
- Screen analysis
- Webcam integration
- Gesture control
- AR overlay (future)

---

## 🐛 Troubleshooting

### Daemon won't start
```bash
# Check permissions
ls -l ~/.roxy/roxy_daemon.py  # Should be executable

# Check venv
~/.roxy/venv/bin/python --version

# Check dependencies
~/.roxy/venv/bin/pip list | grep pynput
```

### Hotkey not working
```bash
# Install pynput
~/.roxy/venv/bin/pip install pynput

# Check for conflicts with other global hotkeys
# Try different hotkey in roxy_daemon.py
```

### Voice not working
```bash
# Voice requires roxy_assistant_v2.py
ls -l ~/.roxy/roxy_assistant_v2.py

# Check dependencies
~/.roxy/venv/bin/pip list | grep -E "openwakeword|sounddevice"
```

### High CPU usage
```bash
# Check monitoring interval in roxy_daemon.py
# Adjust sleep times if needed

# Stop service
sudo systemctl stop roxy-daemon
```

---

## 📚 Related Documentation

- [JARVIS-1 Master Plan](~/mindsong-juke-hub/research/JARVIS1_ROXY_UNIFIED_MASTER_PLAN.md)
- [CITADEL Architecture](~/mindsong-juke-hub/luno-orchestrator/citadel/)
- [MCP Servers](~/.roxy/mcp/)
- [ROXY Welcome Package](~/Desktop/ROXY_WELCOME_PACKAGE/)

---

## ⚡ Quick Reference

```bash
# Start daemon
sudo systemctl start roxy-daemon

# Stop daemon
sudo systemctl stop roxy-daemon

# Restart daemon
sudo systemctl restart roxy-daemon

# View logs
journalctl -u roxy-daemon -f

# Manual test run
~/.roxy/venv/bin/python ~/.roxy/roxy_daemon.py

# Uninstall service
sudo systemctl stop roxy-daemon
sudo systemctl disable roxy-daemon
sudo rm /etc/systemd/system/roxy-daemon.service
sudo systemctl daemon-reload
```

---

**Built with ❤️ as part of LUNA-000 CITADEL**  
**Extends existing ROXY infrastructure - No duplication!**
