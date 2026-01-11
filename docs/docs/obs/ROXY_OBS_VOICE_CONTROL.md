# ROXY OBS Voice Control Guide

> **STORY:** SKOREQ-OBS-EPIC-001-STORY-003  
> **Status:** Implementation Complete  
> **Date:** 2026-01-09

## Overview

ROXY can control OBS Studio using natural voice commands. This integration uses:
- OBS WebSocket 5.x protocol
- MCP server at `~/.roxy/mcp-servers/obs/server.py`
- Voice intents at `~/.roxy/voice_intents/obs_commands.yaml`

## Quick Start

### Enable OBS WebSocket
1. OBS → Tools → WebSocket Server Settings
2. Enable WebSocket server
3. Port: 4455 (default)
4. Set password if desired

### Test Connection
```bash
python ~/.roxy/mcp/mcp_obs.py obs_status
```

## Voice Commands

### Scene Switching

| Say | Action |
|-----|--------|
| "Hey ROXY, switch to scale scene" | Switch to 📺 MASTER - Scale Lesson |
| "Hey ROXY, go to chord study" | Switch to 📺 MASTER - Chord Study |
| "Hey ROXY, show circle of fifths" | Switch to 📺 MASTER - Circle Study |
| "Hey ROXY, performance mode" | Switch to 📺 MASTER - Performance |
| "Hey ROXY, go to full theory" | Switch to 📺 MASTER - Full Theory |

### Source Control

| Say | Action |
|-----|--------|
| "Hey ROXY, show the braid" | Show 🔗 BraidWidget |
| "Hey ROXY, hide the braid" | Hide 🔗 BraidWidget |
| "Hey ROXY, show the fretboard" | Show 🎸 FretboardWidget |
| "Hey ROXY, hide the fretboard" | Hide 🎸 FretboardWidget |
| "Hey ROXY, toggle captions" | Toggle 🎤 LocalVocal Captions |

### Recording & Streaming

| Say | Action |
|-----|--------|
| "Hey ROXY, start recording" | Start OBS recording |
| "Hey ROXY, stop recording" | Stop OBS recording |
| "Hey ROXY, go live" | Start streaming |
| "Hey ROXY, end stream" | Stop streaming |
| "Hey ROXY, pause recording" | Pause recording |

### Animation Triggers

| Say | Action |
|-----|--------|
| "Hey ROXY, animate key shift up" | Transpose visualization up |
| "Hey ROXY, key shift down" | Transpose visualization down |
| "Hey ROXY, toggle intervals" | Show/hide interval overlay |

### Audio Control

| Say | Action |
|-----|--------|
| "Hey ROXY, mute" | Mute microphone |
| "Hey ROXY, unmute" | Unmute microphone |

### Presets

| Say | Action |
|-----|--------|
| "Hey ROXY, start lesson" | Full theory scene + widgets + captions |
| "Hey ROXY, performance mode" | Clean camera, no overlays |
| "Hey ROXY, BRB" | Break screen + mute mic |

### Status Queries

| Say | Response |
|-----|----------|
| "Hey ROXY, OBS status" | Streaming/recording status |
| "Hey ROXY, what scene" | Current scene name |
| "Hey ROXY, am I live" | Streaming status |

## MCP Tools Reference

The MCP server exposes 30+ tools for complete OBS control:

### Status & Info
- `obs_status` - Get streaming/recording/virtual camera status
- `obs_get_version` - Get OBS and WebSocket versions
- `obs_get_stats` - Get CPU, memory, FPS stats

### Scene Management
- `obs_get_scenes` - List all scenes
- `obs_get_current_scene` - Get active scene
- `obs_set_scene` - Switch to a scene
- `obs_create_scene` - Create new scene

### Source Management
- `obs_get_sources` - List sources in a scene
- `obs_show_source` - Show a source
- `obs_hide_source` - Hide a source
- `obs_toggle_source` - Toggle visibility

### Filter Management
- `obs_get_filters` - List filters on a source
- `obs_enable_filter` - Enable a filter
- `obs_disable_filter` - Disable a filter
- `obs_toggle_filter` - Toggle filter state

### Audio Control
- `obs_get_audio_sources` - List audio sources
- `obs_mute_source` - Mute audio
- `obs_unmute_source` - Unmute audio
- `obs_set_volume` - Set volume level

### Recording & Streaming
- `obs_start_stream` / `obs_stop_stream`
- `obs_start_recording` / `obs_stop_recording`
- `obs_pause_recording` / `obs_resume_recording`

### Virtual Camera
- `obs_start_virtual_camera` / `obs_stop_virtual_camera`

### Profiles & Collections
- `obs_get_scene_collections` / `obs_set_scene_collection`
- `obs_get_profiles` / `obs_set_profile`

### Transitions
- `obs_get_transitions` / `obs_set_transition`
- `obs_set_transition_duration`
- `obs_trigger_transition`

### Utilities
- `obs_trigger_hotkey` - Trigger any OBS hotkey
- `obs_screenshot` - Capture screenshot

## Configuration Files

| File | Purpose |
|------|---------|
| `~/.roxy/mcp/mcp_obs.py` | Original MCP server (basic) |
| `~/.roxy/mcp-servers/obs/server.py` | Enhanced MCP server (full API) |
| `~/.roxy/voice_intents/obs_commands.yaml` | Voice command definitions |

## Troubleshooting

### "Cannot connect to OBS"
1. Verify OBS is running
2. Check WebSocket is enabled (Tools → WebSocket Server Settings)
3. Verify port 4455 is not blocked
4. Check password if authentication enabled

### Voice commands not recognized
1. Ensure wake word is clear ("Hey ROXY")
2. Check microphone is active
3. Review voice intent patterns in `obs_commands.yaml`

### Scene not found
- Scene names must match exactly (including emojis)
- Use `obs_get_scenes` to list available scenes
- Check scene aliases in voice intents

## Acceptance Criteria

- [x] Voice command "Hey ROXY, switch to scale scene" triggers SetCurrentProgramScene
- [x] Voice commands "Show the braid" / "Hide the braid" toggle source visibility
- [x] Voice commands "Start recording" / "Stop streaming" functional via WebSocket
- [x] Filter trigger commands working ("Animate key shift up")
- [x] 20+ voice commands documented
