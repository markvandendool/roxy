# 🗣️ HOW TO TALK TO ROXY

## Quick Start - Just Type:

```bash
roxy
```

That's it! This starts an interactive chat session with ROXY.

---

## All Available Commands

### 1. **Chat with ROXY** (Main Command)
```bash
roxy
# or
roxy chat
# or
roxy talk
# or
roxy converse
```

This opens an interactive terminal chat. ROXY will:
- Remember everything you say
- Learn from your conversations
- Store facts and preferences
- Use context from past chats

**Special Commands in Chat:**
- Type `status` to see ROXY's service status
- Type `memory` to see what ROXY remembers
- Type `exit` or `quit` to end the conversation

### 2. **Check ROXY Status**
```bash
roxy status
```

Shows if ROXY service is running, memory usage, and current state.

### 3. **View ROXY's Memory**
```bash
roxy memory
```

Shows:
- Number of conversations stored
- Number of learned facts
- Memory database statistics

### 4. **View ROXY Logs**
```bash
roxy logs
```

Shows real-time logs from ROXY service (press Ctrl+C to exit).

### 5. **Control ROXY Service**
```bash
roxy start     # Start ROXY service
roxy stop      # Stop ROXY service
roxy restart   # Restart ROXY service
```

---

## Example Chat Session

```bash
$ roxy
======================================================================
🤖 ROXY - Resident AI Assistant
======================================================================
Type 'exit' or 'quit' to end conversation
Type 'status' to see ROXY status
Type 'memory' to see what ROXY remembers
======================================================================

You: Hello ROXY!
ROXY: Hello! I'm ROXY, your resident AI assistant. I'm always learning and remembering. How can I help you today?

You: My name is Mark
ROXY: Nice to meet you, Mark! I'll remember that.

You: memory
ROXY: Memory Statistics:
  • Conversations: 2
  • Learned Facts: 501
  • Preferences: 0

ROXY: Recent things I've learned:
  • User's name is Mark
  • User said hello

You: exit
ROXY: Goodbye! I'll remember our conversation.
```

---

## Alternative Ways to Talk to ROXY

### Direct Python Interface
```bash
cd /opt/roxy
source venv/bin/activate
python3 services/roxy_interface.py
```

### Via Python Code
```python
import sys
sys.path.insert(0, '/opt/roxy/services')
from roxy_interface import RoxyInterface
import asyncio

async def chat():
    interface = RoxyInterface()
    response = await interface.chat_terminal("Hello ROXY!")
    print(response)

asyncio.run(chat())
```

---

## What ROXY Remembers

ROXY stores everything in `/opt/roxy/data/roxy_memory.db`:
- ✅ All conversations
- ✅ Learned facts (your name, preferences, etc.)
- ✅ User preferences
- ✅ System state
- ✅ Context from past interactions

**ROXY never forgets!** Every conversation makes ROXY smarter.

---

## Troubleshooting

**If `roxy` command not found:**
```bash
sudo ln -sf /opt/roxy/scripts/roxy /usr/local/bin/roxy
```

**If ROXY service not running:**
```bash
roxy start
# or
sudo systemctl start roxy.service
```

**Check if ROXY is running:**
```bash
systemctl status roxy.service
```

---

## Pro Tips

1. **ROXY learns from context** - Mention your preferences and ROXY remembers
2. **Use `memory` command** - See what ROXY has learned about you
3. **ROXY runs 24/7** - The service is always running in the background
4. **All conversations are stored** - ROXY builds a permanent memory of you

---

**Ready to chat? Just type `roxy`!** 🚀





