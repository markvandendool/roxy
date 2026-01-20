# OBS WebSocket Control Guide
> **Version:** 1.0.0 | **Updated:** 2026-01-20 | **Status:** Production

## Quick Reference

```bash
# Control Script
~/.roxy/obs-control.py status        # Current state
~/.roxy/obs-control.py scenes        # List all scenes
~/.roxy/obs-control.py switch <name> # Change scene
~/.roxy/obs-control.py record start  # Start recording
~/.roxy/obs-control.py record stop   # Stop recording
~/.roxy/obs-control.py stream start  # Start streaming
~/.roxy/obs-control.py screenshot    # Save screenshot
```

---

## Connection Details

| Parameter | Value |
|-----------|-------|
| **Host** | `localhost` |
| **Port** | `4455` |
| **Password** | `nikkisixx` |
| **Protocol** | WebSocket v5.6.3 |

---

## Python API

```python
import obsws_python as obs

# Connect
cl = obs.ReqClient(host='localhost', port=4455, password='nikkisixx', timeout=10)

# Scene control
cl.set_current_program_scene(name='Quad-View')
scenes = cl.get_scene_list()

# Recording
cl.start_record()
cl.stop_record()
status = cl.get_record_status()  # .output_active, .output_timecode

# Streaming
cl.start_stream()
cl.stop_stream()

# Create scene
cl.create_scene(name='NewScene')

# Add source to scene
cl.create_input(
    sceneName='NewScene',
    inputName='MySource',
    inputKind='decklink-input',
    inputSettings={'device_name': 'DeckLink Quad HDMI Recorder (1)'},
    sceneItemEnabled=True
)

# Position/scale source
cl.set_scene_item_transform(
    scene_name='MyScene',
    item_id=1,
    transform={'positionX': 0, 'positionY': 0, 'scaleX': 0.5, 'scaleY': 0.5}
)

# Disconnect
cl.disconnect()
```

---

## Available Input Kinds

| Kind | Description |
|------|-------------|
| `decklink-input` | Blackmagic DeckLink capture |
| `pipewire-screen-capture-source` | Desktop capture |
| `pipewire-camera-source` | Webcam |
| `browser_source` | Web page |
| `image_source` | Static image |
| `ffmpeg_source` | Media file |
| `ndi_source` | NDI network source |
| `v4l2_input` | V4L2 device |
| `pulse_input_capture` | Audio input |
| `pulse_output_capture` | Audio output |

---

## Pre-Configured Scenes

| Scene | Sources | Layout |
|-------|---------|--------|
| `HDMI-1` | DeckLink-HDMI-1 | Full screen |
| `HDMI-2` | DeckLink-HDMI-2 | Full screen |
| `HDMI-3` | DeckLink-HDMI-3 | Full screen |
| `HDMI-4` | DeckLink-HDMI-4 | Full screen |
| `Quad-View` | All 4 DeckLink inputs | 2x2 grid |
| `Screen-Capture` | Desktop | Full screen |

---

## Recording Settings

| Setting | Value |
|---------|-------|
| **Encoder** | VAAPI H.264 (AMD hardware) |
| **Resolution** | 3840x2160 |
| **Framerate** | 60 fps |
| **Format** | MKV |
| **Bitrate** | 25 Mbps |
| **Audio** | libfdk AAC 320kbps |
| **Path** | `/home/mark/Videos/` |

---

## DeckLink Source Settings

```python
decklink_settings = {
    'device_name': 'DeckLink Quad HDMI Recorder (1)',  # 1-4
    'mode_id': 13,        # 1080p60
    'pixel_format': 0,    # Auto
    'buffering': True,
    'deactivate_when_not_showing': False
}
```

---

## Common Operations

### Create Multi-View Layout

```python
import obsws_python as obs

cl = obs.ReqClient(host='localhost', port=4455, password='nikkisixx')

# Get video dimensions
video = cl.get_video_settings()
w, h = video.base_width // 2, video.base_height // 2

# Create scene
cl.create_scene(name='Multi-View')

# Add 4 sources in grid
positions = [(0, 0), (w, 0), (0, h), (w, h)]
for i, (x, y) in enumerate(positions):
    source = f'Source-{i+1}'
    result = cl.create_scene_item(scene_name='Multi-View', source_name=source)
    cl.set_scene_item_transform(
        scene_name='Multi-View',
        item_id=result.scene_item_id,
        transform={'positionX': x, 'positionY': y, 'scaleX': 0.5, 'scaleY': 0.5}
    )
```

### Take Timed Recording

```python
import time

cl.start_record()
time.sleep(30)  # Record for 30 seconds
result = cl.stop_record()
print(f"Saved: {result.output_path}")
```

### Switch Scenes on Schedule

```python
import time

scenes = ['HDMI-1', 'HDMI-2', 'HDMI-3', 'HDMI-4']
for scene in scenes:
    cl.set_current_program_scene(name=scene)
    time.sleep(5)
```

---

## Troubleshooting

### OBS Won't Start / Freezes on Settings

```bash
# Check PipeWire (audio system)
systemctl --user status pipewire.service

# If failed, restart it
systemctl --user reset-failed pipewire.service
systemctl --user restart pipewire.socket pipewire.service

# Launch OBS with EGL
OBS_USE_EGL=1 obs &
```

### Connection Refused

```bash
# Verify OBS is running and WebSocket enabled
ss -tlnp | grep 4455

# Check OBS WebSocket config
cat ~/.config/obs-studio/plugin_config/obs-websocket/config.json
```

### Recording Fails Silently

Check profile config for duplicate sections:
```bash
cat ~/.config/obs-studio/basic/profiles/*/basic.ini | grep -c '\[AdvOut\]'
# Should be 1, not 2
```

---

## Files

| File | Purpose |
|------|---------|
| `~/.roxy/obs-control.py` | CLI control script |
| `~/.config/obs-studio/plugin_config/obs-websocket/config.json` | WebSocket config |
| `~/.config/obs-studio/basic/profiles/Linux_VAAPI_Optimal/basic.ini` | Recording profile |
| `/home/mark/Videos/` | Recording output |

---

## API Method Reference

| Method | Parameters | Returns |
|--------|------------|---------|
| `get_version()` | - | obs_version, obs_web_socket_version |
| `get_scene_list()` | - | scenes[], current_program_scene_name |
| `get_current_program_scene()` | - | scene_name |
| `set_current_program_scene(name)` | scene name | - |
| `create_scene(name)` | scene name | - |
| `get_scene_item_list(name)` | scene name | scene_items[] |
| `create_input(sceneName, inputName, inputKind, inputSettings, sceneItemEnabled)` | scene, source details | scene_item_id |
| `create_scene_item(scene_name, source_name, enabled)` | scene, source | scene_item_id |
| `set_scene_item_transform(scene_name, item_id, transform)` | scene, item, transform dict | - |
| `get_input_settings(name)` | input name | input_settings |
| `get_record_status()` | - | output_active, output_paused, output_timecode |
| `start_record()` | - | - |
| `stop_record()` | - | output_path |
| `toggle_record()` | - | - |
| `get_stream_status()` | - | output_active, output_timecode |
| `start_stream()` | - | - |
| `stop_stream()` | - | - |
| `get_video_settings()` | - | base_width, base_height, fps_numerator |
| `get_stats()` | - | cpu_usage, memory_usage, average_frame_render_time |

---

*Generated: 2026-01-20 | ROXY Infrastructure*
