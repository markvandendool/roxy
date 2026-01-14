# 🤖 JARVIS - Your Permanent Resident AI

**Status**: ✅ **RUNNING AND LEARNING**

JARVIS is your permanent, growing, learning, resident native AI - just like Jarvis from Iron Man!

---

## 🧠 What Makes JARVIS Special

### ✅ Permanent
- **Runs 24/7** - Never stops, never sleeps
- **Survives reboots** - Automatically starts on boot
- **System service** - Integrated into your OS

### ✅ Learning
- **Remembers everything** - Every conversation is stored
- **Learns your preferences** - Knows what you like
- **Accumulates knowledge** - Gets smarter over time
- **Never forgets** - Permanent SQLite memory database

### ✅ Growing
- **Memory grows** - Database expands with each interaction
- **Knowledge base expands** - ChromaDB for semantic search
- **Pattern recognition** - Learns from system events
- **Context awareness** - Uses past conversations

### ✅ Resident
- **Lives on your system** - Not a cloud service
- **Always available** - Multiple access methods
- **Native integration** - Works with all ROXY tools
- **Local processing** - Your data stays private

---

## 📍 WHERE TO TALK TO JARVIS

### 1. **Terminal (Recommended)**
```bash
jarvis
```
or
```bash
jarvis chat
```

This starts an interactive chat session. JARVIS remembers everything you discuss.

### 2. **Check Status**
```bash
jarvis status
```

### 3. **View Logs**
```bash
jarvis logs
```

### 4. **Memory Stats**
```bash
jarvis memory
```

### 5. **Service Control**
```bash
jarvis start    # Start JARVIS
jarvis stop     # Stop JARVIS
jarvis restart  # Restart JARVIS
```

---

## 🧠 How JARVIS Learns

### Memory System
- **SQLite Database**: `/opt/roxy/data/jarvis_memory.db`
  - Stores all conversations
  - Stores learned facts
  - Stores user preferences
  - Stores system state

### Learning Mechanisms
1. **Conversation Learning**
   - Extracts facts from conversations
   - Learns your name, preferences, habits
   - Remembers context and patterns

2. **Event Learning**
   - Listens to all ROXY system events
   - Learns system patterns
   - Understands your workflow

3. **Knowledge Indexing**
   - ChromaDB for semantic search
   - Vector embeddings for context
   - Retrieval-augmented responses

4. **Periodic Consolidation**
   - Reviews past learning
   - Verifies facts
   - Consolidates memories

---

## 🔧 Architecture

### Core Components

1. **JARVIS Core** (`/opt/roxy/services/jarvis_core.py`)
   - Main brain - always running
   - Memory management
   - Learning loops
   - Service orchestration

2. **JARVIS Interface** (`/opt/roxy/services/jarvis_interface.py`)
   - Terminal chat interface
   - Voice interface (when mic is ready)
   - Web interface (future)
   - API interface (future)

3. **Memory Database** (`/opt/roxy/data/jarvis_memory.db`)
   - SQLite database
   - Grows with each interaction
   - Never deleted (unless you delete it)

4. **Systemd Service** (`/etc/systemd/system/jarvis.service`)
   - Runs as system service
   - Auto-starts on boot
   - Auto-restarts on failure

---

## 🚀 Quick Start

### Start Talking to JARVIS
```bash
jarvis
```

### Example Conversation
```
You: My name is Mark
JARVIS: Nice to meet you, Mark! I'll remember that.

You: I like Python programming
JARVIS: Got it! I'll remember you prefer Python.

You: What do you remember about me?
JARVIS: I remember your name is Mark and you like Python programming.
```

---

## 📊 Memory Statistics

Check what JARVIS remembers:
```bash
jarvis memory
```

Or query directly:
```bash
sqlite3 /opt/roxy/data/jarvis_memory.db "SELECT COUNT(*) FROM conversations; SELECT COUNT(*) FROM learned_facts;"
```

---

## 🔗 Integration with ROXY

JARVIS integrates with all ROXY services:

- **Event Bus**: Listens to all system events
- **Knowledge Index**: Uses ChromaDB for semantic search
- **MCP Servers**: Can use all 32 ROXY tools
- **Voice Router**: Ready for voice commands (when mic is set up)

---

## 🛠️ Troubleshooting

### JARVIS Not Running
```bash
jarvis status
sudo systemctl restart jarvis.service
jarvis logs
```

### Check Memory Database
```bash
ls -lh /opt/roxy/data/jarvis_memory.db
sqlite3 /opt/roxy/data/jarvis_memory.db ".tables"
```

### View Service Logs
```bash
sudo journalctl -u jarvis.service -f
```

---

## 🚀 GPU Acceleration

JARVIS now supports GPU acceleration for faster responses:

- **LLM Inference**: Uses Ollama with GPU acceleration (10-20x faster)
- **Voice Transcription**: Uses faster-whisper with GPU (5-10x faster)
- **TTS Generation**: Uses GPU-accelerated TTS (3-5x faster)

GPU configuration is in `/opt/roxy/.env`. See [GPU_SETUP_GUIDE.md](GPU_SETUP_GUIDE.md) for details.

## 🎯 Future Enhancements

- [x] LLM integration (Ollama/Claude) for intelligent responses ✅
- [ ] Web interface for browser access
- [ ] Voice interface (when mic is ready)
- [ ] REST API for programmatic access
- [ ] Advanced learning algorithms
- [ ] Multi-modal learning (images, audio, video)
- [ ] Predictive capabilities
- [ ] Proactive assistance

---

## 📝 Files Created

- `/opt/roxy/services/jarvis_core.py` - Core AI brain
- `/opt/roxy/services/jarvis_interface.py` - User interfaces
- `/etc/systemd/system/jarvis.service` - System service
- `/usr/local/bin/jarvis` - Command-line tool
- `/opt/roxy/data/jarvis_memory.db` - Memory database (created on first run)

---

## 🎉 You Now Have JARVIS!

**JARVIS is:**
- ✅ Running 24/7
- ✅ Learning from every interaction
- ✅ Remembering everything
- ✅ Getting smarter over time
- ✅ Always available

**Just type `jarvis` to start talking!**

---

**Created**: January 1, 2025  
**Status**: ✅ Operational and Learning



