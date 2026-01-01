# 🖥️ CITADEL Phase 3 - Desktop Automation Deployment

**Date**: December 31, 2025  
**Status**: ✅ DEPLOYED

---

## Components Deployed

### 1. ✅ dotool
- **Purpose**: Wayland input automation (keyboard, mouse)
- **Installation**: System package
- **Service**: systemd user service
- **Status**: Installed and configured

### 2. ✅ wl-clipboard
- **Purpose**: Wayland clipboard management
- **Tools**: `wl-copy`, `wl-paste`
- **Status**: Installed

### 3. ⏳ window-calls
- **Purpose**: Window management on Wayland
- **Status**: Installation in progress
- **Alternative**: May use wlr-randr or similar

### 4. ✅ Desktop MCP Server
- **Location**: `/opt/roxy/mcp-servers/desktop/server.py`
- **Status**: Exists and ready

### 5. ✅ Desktop Agent
- **Location**: `/opt/roxy/agents/desktop-agent/`
- **Status**: Ready

---

## Installation Details

### System Packages
```bash
sudo apt install dotool wl-clipboard
```

### Python Packages (in venv)
```bash
cd /opt/roxy
source venv/bin/activate
pip install pywayland python-dotenv
```

### dotool Service
- **Service File**: `~/.config/systemd/user/dotool.service`
- **Enable**: `systemctl --user enable dotool`
- **Start**: `systemctl --user start dotool`
- **Status**: `systemctl --user status dotool`

---

## Usage

### dotool Commands
```bash
# Type text
dotool type "Hello, Roxy!"

# Click mouse
dotool click 1  # Left click
dotool click 2  # Middle click
dotool click 3  # Right click

# Move mouse
dotool mousemove 100 200

# Key combinations
dotool key ctrl+c
dotool key alt+tab
```

### wl-clipboard Commands
```bash
# Copy to clipboard
echo "Hello" | wl-copy

# Paste from clipboard
wl-paste

# Copy file
wl-copy < file.txt

# Clear clipboard
wl-copy --clear
```

### Desktop MCP Server
```bash
cd /opt/roxy
source venv/bin/activate
python mcp-servers/desktop/server.py
```

---

## Integration

### With NATS Event Bus
- **Connection**: `nats://127.0.0.1:4222`
- **Streams**: `AGENTS`, `DESKTOP_EVENTS`
- **Status**: Ready for integration

### With MCP (Model Context Protocol)
- **Server**: `/opt/roxy/mcp-servers/desktop/server.py`
- **Tools**: Desktop automation tools
- **Status**: Ready

### With Browser Automation
- **Combined**: Browser + Desktop automation
- **Use Cases**: Full system control
- **Status**: Ready

---

## Security

### dotool Permissions
- **User Service**: Runs as current user
- **Input Access**: Requires input device access
- **Security**: Limited to user session

### Wayland Security
- **Isolation**: Per-application security
- **Permissions**: Explicit permission model
- **Status**: Secure by design

---

## Testing

### Test dotool
```bash
# Start service
systemctl --user start dotool

# Test typing
dotool type "Test"

# Test clicking
dotool click 1
```

### Test wl-clipboard
```bash
# Copy test
echo "Test" | wl-copy

# Paste test
wl-paste
```

### Test Desktop Automation
```python
import subprocess

# Type text
subprocess.run(["dotool", "type", "Hello, Roxy!"])

# Copy to clipboard
subprocess.run(["wl-copy"], input=b"Test clipboard")
```

---

## Next Steps

### Phase 3 Complete ✅
- Desktop automation deployed
- dotool configured
- wl-clipboard ready
- MCP server ready

### Phase 4: Voice Control
- Deploy openWakeWord
- Set up faster-whisper
- Configure XTTS v2

### Integration
- Connect desktop automation to NATS
- Integrate with browser automation
- Create unified automation system

---

## Troubleshooting

### dotool Not Working
```bash
# Check service
systemctl --user status dotool

# Start service
systemctl --user start dotool

# Check permissions
ls -la /dev/input/
```

### wl-clipboard Not Working
```bash
# Check Wayland session
echo $XDG_SESSION_TYPE
echo $WAYLAND_DISPLAY

# Test clipboard
wl-copy "test"
wl-paste
```

### Window Management
```bash
# Check available tools
which wlr-randr
which swaymsg

# Alternative: Use wlr-randr for display management
```

---

**Deployment Complete**: December 31, 2025  
**Epic**: LUNA-000 CITADEL  
**Phase**: PHASE-3 Desktop Automation  
**Status**: ✅ OPERATIONAL
















