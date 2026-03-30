# NDI Recording Runbook — MindSong Theater8K

**Last Updated**: 2026-01-24
**Status**: OPERATIONAL

---

## Quick Start (TL;DR)

```bash
# 1. Mac Studio: Start Theater-8K dev server
ssh macstudio "cd ~/mindsong-juke-hub && bun dev"

# 2. Mac Studio: Start NDI bridge (in separate terminal)
ssh macstudio "cd ~/mindsong-juke-hub/tools/skybeam-ndi-bridge && cargo run --release"

# 3. Linux: Open OBS with FPS_Tester scene collection
obs --collection FPS_Tester --profile Theater8K_Optimized

# 4. Linux: Verify NDI sources visible, then start recording
```

---

## NDI Source Names (Canonical)

| Source | NDI Name | Resolution | Origin |
|--------|----------|------------|--------|
| **Landscape** | `MindSong-Landscape` | 3840x2160 (4K) | skybeam-ndi-bridge |
| **Vertical** | `MindSong-Vertical` | 1080x1920 | skybeam-ndi-bridge |

**Network Names**: When broadcast, these appear as:
- `MACPRO-LINUX (MindSong-Landscape)` (if bridge runs on Linux)
- `MARKS-MAC-MINI.LOCAL (MindSong-Landscape)` (if bridge runs on Mac Studio)

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                         MAC STUDIO (10.0.0.92)                         │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌─────────────────────┐         ┌─────────────────────┐              │
│  │   Theater-8K        │ WebGL   │  skybeam-ndi-bridge │  NDI         │
│  │   (bun dev :9135)   ├────────►│  (Rust, :9200/9201) ├─────────┐    │
│  │   Browser Render    │ Canvas  │  H.264 → NDI Send   │         │    │
│  └─────────────────────┘         └─────────────────────┘         │    │
│                                                                   │    │
└───────────────────────────────────────────────────────────────────┼────┘
                                                                    │
                                    NDI over 10GbE Network          │
                                                                    │
┌───────────────────────────────────────────────────────────────────┼────┐
│                         LINUX/ROXY (10.0.0.69)                    │    │
├───────────────────────────────────────────────────────────────────┼────┤
│                                                                   │    │
│  ┌─────────────────────┐         ┌─────────────────────┐         │    │
│  │   OBS Studio        │◄────────┤  NDI Sources        │◄────────┘    │
│  │   (4455 WebSocket)  │  NDI    │  MindSong-Landscape │              │
│  │   FPS_Tester Scene  │  Recv   │  MindSong-Vertical  │              │
│  └─────────┬───────────┘         └─────────────────────┘              │
│            │                                                           │
│            │ VAAPI H.264                                               │
│            ▼                                                           │
│  ┌─────────────────────┐                                               │
│  │   Recording Output  │                                               │
│  │   ~/.roxy/content-  │                                               │
│  │   pipeline/input/   │                                               │
│  └─────────────────────┘                                               │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## OBS Configuration

### Scene Collection: `FPS_Tester`

| Source Name | NDI Source | Resolution |
|-------------|------------|------------|
| MindSong-Landscape | MACPRO-LINUX (MindSong-Landscape) | 3840x2160 |
| MindSong-Vertical | MACPRO-LINUX (MindSong-Vertical) | 1080x1920 |

### Profile: `Theater8K_Optimized`

| Setting | Value |
|---------|-------|
| Base Resolution | 3840x2160 |
| Output Resolution | 3840x2160 |
| FPS | 60 |
| Encoder | ffmpeg_vaapi_tex (AMD VAAPI) |
| Bitrate | 80,000 kbps |
| Format | MP4 |
| Recording Path | /home/mark/Videos |

### Vertical Canvas Plugin

| Setting | Value |
|---------|-------|
| Width | 1080 |
| Height | 1920 |
| Current Scene | Vertical NDI test |
| Recording Path | /home/mark (update to pipeline) |

---

## Startup Procedure (Detailed)

### Step 1: Start Mac Studio Services

```bash
# SSH to Mac Studio
ssh macstudio

# Terminal 1: Start Theater-8K dev server
cd ~/mindsong-juke-hub
bun dev
# Wait for "Local: http://localhost:9135" message

# Terminal 2: Start skybeam-ndi-bridge
cd ~/mindsong-juke-hub/tools/skybeam-ndi-bridge
cargo run --release
# Should see:
#   === SKYBEAM NDI Bridge ===
#   Dual canvas mode: Landscape + Vertical
#   Landscape: MindSong-Landscape (3840x2160 @ 60fps)
#   Vertical: MindSong-Vertical (1080x1920 @ 60fps)
```

### Step 2: Verify NDI on Linux

```bash
# On Linux, check NDI sources are visible
ndi-find

# Expected output:
#   MARKS-MAC-MINI.LOCAL (MindSong-Landscape)
#   MARKS-MAC-MINI.LOCAL (MindSong-Vertical)
```

### Step 3: Open OBS and Configure

```bash
# Start OBS with correct scene and profile
obs --collection FPS_Tester --profile Theater8K_Optimized

# Or via GUI:
# 1. Open OBS
# 2. Scene Collection → FPS_Tester
# 3. Profile → Theater8K_Optimized
```

### Step 4: Verify and Record

1. **Check NDI sources** in Sources panel:
   - MindSong-Landscape should show Theater-8K content
   - MindSong-Vertical should show vertical version

2. **Start recording**:
   - Click "Start Recording" for main canvas (4K)
   - In Vertical Canvas dock, click "Start Recording" for vertical

3. **Stop recording**:
   - Click "Stop Recording" when done
   - Files saved to `/home/mark/Videos/`

---

## Troubleshooting

### NDI Sources Not Visible

```bash
# Check if NDI bridge is running
ssh macstudio "pgrep -l skybeam"

# Check network connectivity
ping -c 3 10.0.0.92

# Restart NDI bridge if needed
ssh macstudio "pkill skybeam; cd ~/mindsong-juke-hub/tools/skybeam-ndi-bridge && cargo run --release &"
```

### Recording Fails / Low FPS

1. **Check GPU load**:
   ```bash
   rocm-smi
   ```

2. **Switch encoder** if VAAPI overloaded:
   - Profile → Output → Recording → Encoder → x264

3. **Lower bitrate** if disk I/O limited:
   - Settings → Output → Recording → Bitrate → 50000

### WebSocket Control (OBS MCP)

```bash
# Check OBS WebSocket
curl -s http://localhost:4455/health || echo "WebSocket not responding"

# Control via ROXY MCP
ssh localhost "~/.roxy/obs-control.py status"
ssh localhost "~/.roxy/obs-control.py record start"
```

---

## Ports Reference

| Port | Service | Machine |
|------|---------|---------|
| 9135 | Theater-8K Dev Server | Mac Studio |
| 9200 | NDI Bridge (Landscape WS) | Mac Studio |
| 9201 | NDI Bridge (Vertical WS) | Mac Studio |
| 4455 | OBS WebSocket | Linux |
| 4222 | NATS | Linux |

---

## Related Documents

- `~/.roxy/PROJECT_SKYBEAM.md` - Full infrastructure map
- `~/.roxy/config/theater_obs_mapping.json` - OBS mapping config
- `~/mindsong-juke-hub/docs/skoreq/NDI-LLG-BROADCAST-20260122/` - SKOREQ plan
- `~/.roxy/workshops/physical-infrastructure/brain/hardware/SKOREQ_OBS_DREAM_COLLECTION_PLAN.md`

---

**Author**: Claude Opus 4.5
**Epic**: NDI-LLG-BROADCAST-20260122
