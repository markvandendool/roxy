# 🌐 CITADEL Phase 2 - Browser Automation Deployment

**Date**: December 31, 2025  
**Status**: ✅ DEPLOYED

---

## Components Deployed

### 1. ✅ Playwright
- **Location**: Installed in `/opt/roxy/venv`
- **Version**: Latest
- **Browser**: Chromium installed
- **Status**: Operational

### 2. ✅ browser-use AI Agent
- **Location**: Installed in `/opt/roxy/venv`
- **Version**: Latest
- **Features**: 
  - AI-powered browser automation
  - 89% WebVoyager benchmark
  - Native Ollama integration
- **Status**: Operational

### 3. ✅ gVisor Sandbox
- **Runtime**: `runsc` (installed at `/usr/bin/runsc`)
- **Version**: release-20251215.0
- **Docker Config**: `/etc/docker/daemon.json`
- **Status**: Configured

### 4. ✅ Browser MCP Server
- **Location**: `/opt/roxy/mcp-servers/browser/server.py`
- **Tools**:
  - `browse_and_extract` - Navigate and extract info
  - `search_web` - Web search with AI
  - `fill_form` - Form automation
  - `screenshot_page` - Screenshot capture
- **Status**: Ready

### 5. ✅ Browser Agent
- **Location**: `/opt/roxy/agents/browser-agent/agent.py`
- **Features**: AI-powered browser tasks
- **Status**: Ready

### 6. ✅ Browser Sandbox Container
- **Compose File**: `/opt/roxy/compose/docker-compose.browser-sandbox.yml`
- **Runtime**: gVisor (runsc)
- **Security**: Minimal capabilities, read-only filesystem
- **Status**: Configured

---

## Installation Details

### Python Packages (in venv)
```bash
cd /opt/roxy
source venv/bin/activate
pip list | grep -E "playwright|browser-use|langchain"
```

### Playwright Browsers
```bash
source venv/bin/activate
python -m playwright install chromium
```

### gVisor Configuration
- **Runtime Path**: `/usr/bin/runsc`
- **Docker Config**: `/etc/docker/daemon.json`
- **Test**: `docker run --runtime=runsc hello-world`

---

## Usage

### Browser Agent (Direct)
```bash
cd /opt/roxy
source venv/bin/activate
python agents/browser-agent/agent.py
```

### Browser MCP Server
```bash
cd /opt/roxy
source venv/bin/activate
python mcp-servers/browser/server.py
```

### Browser Sandbox (Docker)
```bash
cd /opt/roxy/compose
docker compose -f docker-compose.browser-sandbox.yml up -d
```

---

## Integration

### With Ollama
- **Model**: `llama3:8b` (default)
- **Host**: `http://localhost:11434`
- **Configuration**: Set via `OLLAMA_HOST` and `OLLAMA_MODEL` env vars

### With NATS Event Bus
- **Connection**: `nats://127.0.0.1:4222`
- **Streams**: `AGENTS`, `BROWSER_EVENTS`
- **Status**: Ready for integration

### With MCP (Model Context Protocol)
- **Server**: `/opt/roxy/mcp-servers/browser/server.py`
- **Tools**: 4 browser automation tools
- **Status**: Ready

---

## Security

### gVisor Sandbox
- **Isolation**: Kernel-level sandboxing
- **Capabilities**: Minimal (NET_BIND_SERVICE only)
- **Filesystem**: Read-only root, tmpfs for /tmp and /run
- **Security**: no-new-privileges enabled

### Browser Sessions
- **Storage**: `/opt/roxy/secrets/browser-sessions`
- **Screenshots**: `/opt/roxy/data/browser-screenshots`
- **Permissions**: Restricted access

---

## Testing

### Test Playwright
```bash
cd /opt/roxy
source venv/bin/activate
python -c "from playwright.sync_api import sync_playwright; print('✅ Playwright works')"
```

### Test browser-use
```bash
cd /opt/roxy
source venv/bin/activate
python -c "from browser_use import Agent; print('✅ browser-use works')"
```

### Test Browser Automation
```python
from browser_use import Agent
from langchain_ollama import ChatOllama

llm = ChatOllama(model="llama3:8b", base_url="http://localhost:11434")
agent = Agent(task="Go to example.com and get the title", llm=llm)
result = await agent.run()
```

### Test gVisor
```bash
docker run --runtime=runsc hello-world
```

---

## Next Steps

### Phase 2 Complete ✅
- Browser automation deployed
- gVisor sandbox configured
- MCP server ready
- Integration points established

### Phase 3: Desktop Automation
- Install dotool
- Configure Wayland automation
- Set up window-calls

### Phase 4: Voice Control
- Deploy openWakeWord
- Set up faster-whisper
- Configure XTTS v2

---

## Troubleshooting

### Playwright Not Found
```bash
cd /opt/roxy
source venv/bin/activate
pip install playwright
python -m playwright install chromium
```

### browser-use Import Error
```bash
source venv/bin/activate
pip install browser-use langchain-ollama
```

### gVisor Not Working
```bash
# Check installation
which runsc
runsc --version

# Check Docker config
cat /etc/docker/daemon.json

# Restart Docker
sudo systemctl restart docker
```

### Ollama Not Available
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if needed
ollama serve
```

---

**Deployment Complete**: December 31, 2025  
**Epic**: LUNA-000 CITADEL  
**Phase**: PHASE-2 Browser Automation  
**Status**: ✅ OPERATIONAL
















