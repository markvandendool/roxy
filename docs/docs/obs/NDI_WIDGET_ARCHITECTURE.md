# NDI Widget Architecture

> **STORY:** SKOREQ-OBS-EPIC-001-STORY-001  
> **Status:** Implementation Complete  
> **Date:** 2026-01-09

## Overview

The NDI Widget Bridge enables 8K Theater widgets to appear as independent NDI sources in OBS, allowing professional-grade compositing with alpha channel transparency.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         8K THEATER                                │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    React/WebGPU Widgets                   │    │
│  │  PianoWidget │ FretboardWidget │ BraidWidget │ COFWidget │    │
│  └──────────────────────────────────────────────────────────┘    │
│                              │                                    │
│                              ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              Browser Source (per widget)                  │    │
│  │         http://localhost:5173/widgets/{name}?ndi=true    │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                        OBS STUDIO                                 │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              NDI Widget Bridge (ndi_bridge.py)            │    │
│  │     Captures browser sources → Creates NDI outputs        │    │
│  └──────────────────────────────────────────────────────────┘    │
│                              │                                    │
│                              ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    NDI Output Sources                     │    │
│  │  MINDSONG-Piano │ MINDSONG-Fretboard │ MINDSONG-Braid    │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                    EXTERNAL CONSUMERS                             │
│  - OBS on other machines (NDI source)                            │
│  - vMix, Wirecast, other video software                          │
│  - NDI Studio Monitor                                            │
│  - Hardware NDI decoders                                         │
└──────────────────────────────────────────────────────────────────┘
```

## Widget Configuration

Each widget is configured in `~/.roxy/obs-portable/config/ndi-widget-bridge.json`:

| Widget | NDI Source Name | Resolution | Transparent | MIDI |
|--------|----------------|------------|-------------|------|
| PianoWidget | MINDSONG-Piano | 1920×400 | ✅ | ✅ |
| FretboardWidget | MINDSONG-Fretboard | 1920×600 | ✅ | ✅ |
| BraidWidget | MINDSONG-Braid | 800×800 | ✅ | ❌ |
| COFWidget | MINDSONG-COF | 800×800 | ✅ | ❌ |
| HarmonicProfileWidget | MINDSONG-HarmonicProfile | 1200×400 | ✅ | ❌ |
| ScoreTabWidget | MINDSONG-ScoreTab | 1920×600 | ✅ | ❌ |
| MetronomeWidget | MINDSONG-Metronome | 400×400 | ✅ | ❌ |
| TempoGeometryWidget | MINDSONG-TempoGeometry | 800×800 | ✅ | ❌ |

## Latency Targets

| Metric | Target | Description |
|--------|--------|-------------|
| MIDI → Visual | < 50ms | Time from MIDI input to fretboard highlight |
| KRONOS Sync | < 16ms | Beat sync accuracy (1 frame at 60fps) |
| NDI Transmit | < 33ms | NDI encoding and network transmission |

## Installation

### Prerequisites

1. **DistroAV** (NDI for OBS on Linux):
   ```bash
   # Already installed via Flatpak
   flatpak install flathub com.obsproject.Studio.Plugin.DistroAV
   ```

2. **NDI Tools** (optional, for monitoring):
   ```bash
   # Download from https://ndi.video/tools/
   ```

### Configuration

1. Start the 8K Theater dev server:
   ```bash
   cd ~/mindsong-juke-hub && bun run dev
   ```

2. Start the NDI bridge:
   ```bash
   python ~/.roxy/mcp-servers/obs/ndi_bridge.py
   ```

3. In OBS, add NDI sources:
   - Tools → NDI Source
   - Select `MINDSONG-*` sources

## OBS Browser Source Settings

For each widget browser source:

```json
{
  "url": "http://localhost:5173/widgets/{name}?ndi=true",
  "width": 1920,
  "height": 600,
  "css": "body { background: transparent !important; overflow: hidden; }",
  "fps": 60,
  "fpsCustom": true,
  "shutdown": false,
  "restartWhenActive": false
}
```

## MCP Integration

The NDI bridge exposes MCP tools for ROXY voice control:

| Tool | Description |
|------|-------------|
| `ndi_bridge_status` | Get current bridge status |
| `ndi_bridge_start_widget` | Start NDI for specific widget |
| `ndi_bridge_start_all` | Start all widget NDI outputs |
| `ndi_bridge_health` | Perform health check with latency report |

### Example ROXY Commands

```
"Hey ROXY, start the fretboard NDI"
"Show me the NDI bridge health"
"Start all widget NDI sources"
```

## Troubleshooting

### NDI Sources Not Appearing

1. Check DistroAV plugin is enabled in OBS
2. Verify NDI bridge is running: `ps aux | grep ndi_bridge`
3. Check firewall allows NDI (mDNS port 5353, NDI ports 5960-5969)

### High Latency

1. Reduce widget resolution in config
2. Check CPU usage (WebGPU should be < 30%)
3. Disable unnecessary widgets

### Alpha Channel Issues

1. Ensure `?ndi=true` parameter in widget URL
2. Verify CSS has `background: transparent`
3. Check OBS source color format (BGRA)

## Files

| File | Purpose |
|------|---------|
| `~/.roxy/obs-portable/config/ndi-widget-bridge.json` | Widget configuration |
| `~/.roxy/mcp-servers/obs/ndi_bridge.py` | NDI bridge server |
| `~/.roxy/docs/docs/obs/NDI_WIDGET_ARCHITECTURE.md` | This document |

## Acceptance Criteria

- [x] Each widget visible as independent NDI source in OBS
- [x] Alpha channel preserved for transparency
- [x] Latency target defined (< 50ms)
- [x] NDI sources auto-discoverable on local network
- [x] Documentation complete
