# Roxy OBS Automation Scripts

Production-ready Python & Bash utilities for OBS Studio automation. Control OBS via command line, voice commands, or MCP (Model Context Protocol).

## What's Included

```
obs-scripts/
├── scripts/
│   ├── obs_controller.py      # CLI controller (start/stop stream, scenes)
│   ├── obs_skill.py           # Voice command integration
│   ├── obs_automation.py      # Automation helpers
│   └── obs-canvas-performance-test.py  # Performance testing
├── mcp/
│   ├── obs_mcp_server.py      # MCP server for AI integration
│   └── ndi_bridge.py          # NDI widget bridge
├── lua/
│   └── obs-zoom-to-mouse.lua  # Zoom-to-mouse Lua script
├── voice-intents/
│   └── obs_commands.yaml      # Voice command definitions
└── examples/
    └── (sample configs)
```

## Requirements

- OBS Studio 28+ (with WebSocket enabled)
- Python 3.10+
- websockets library: `pip install websockets`

## Quick Start

### 1. Enable OBS WebSocket

1. Open OBS Studio
2. Tools → WebSocket Server Settings
3. Enable WebSocket Server (default port: 4455)
4. Optional: Set a password

### 2. Test Connection

```bash
# Check status
python3 scripts/obs_controller.py status

# List scenes
python3 scripts/obs_controller.py scenes

# Switch scene
python3 scripts/obs_controller.py scene "My Scene"
```

### 3. Control Recording/Streaming

```bash
# Start/stop recording
python3 scripts/obs_controller.py start-recording
python3 scripts/obs_controller.py stop-recording

# Start/stop streaming
python3 scripts/obs_controller.py start-stream
python3 scripts/obs_controller.py stop-stream
```

## MCP Server (AI Integration)

The MCP server allows AI assistants like Claude to control OBS:

```bash
# Start MCP server
python3 mcp/obs_mcp_server.py
```

Available tools:
- `obs_get_status` - Get recording/streaming status
- `obs_start_recording` / `obs_stop_recording`
- `obs_get_scenes` / `obs_switch_scene`
- `obs_take_screenshot`

## Voice Integration

The `obs_skill.py` provides voice command handling. Pair with your preferred speech recognition system.

Supported intents (see `voice-intents/obs_commands.yaml`):
- "Start recording" / "Stop recording"
- "Go live" / "End stream"
- "Switch to [scene name]"
- "Show [source]" / "Hide [source]"

## Lua Scripts

### obs-zoom-to-mouse.lua

Smooth zoom-to-mouse cursor effect for tutorials and demos.

Installation:
1. Copy to OBS scripts folder
2. Tools → Scripts → Add Script
3. Configure zoom factor and transition speed

## Configuration

Edit the connection settings at the top of each script:

```python
OBS_HOST = "localhost"
OBS_PORT = 4455
OBS_PASSWORD = ""  # Set if authentication enabled
```

## Troubleshooting

### "Could not connect to OBS"
- Ensure OBS is running
- Check WebSocket is enabled (Tools → WebSocket Server Settings)
- Verify port 4455 is not blocked

### "Authentication failed"
- Set `OBS_PASSWORD` in the script to match OBS settings

### Scripts not found
- Run from the obs-scripts directory
- Use absolute paths if running from elsewhere

## License

MIT License - See LICENSE file

## Support

- Issues: https://github.com/stackkraft/obs-scripts/issues
- Email: stackkraft@gmail.com

---

Built with ROXY AI Infrastructure
