# 🚀 SKOREQ Dream Collection - Quick Start Guide

> **Get streaming in 5 minutes!**

---

## Prerequisites

- [ ] OBS Studio 30+ installed
- [ ] Theater 8K widget server running (`http://localhost:5173`)
- [ ] NDI runtime installed (DistroAV)
- [ ] move-transition plugin installed

---

## Step 1: Import Scene Collection

```bash
# Copy scene collection to OBS
cp ~/.roxy/obs-portable/scenes/skoreq-scenes.json \
   ~/.config/obs-studio/basic/scenes/

# Restart OBS
```

In OBS: **Scene Collection → Import → skoreq-scenes.json**

---

## Step 2: Select Profile

1. OBS → Profile → **SKOREQ** (horizontal) or **SKOREQ-Vertical**
2. Profile auto-configures:
   - Resolution: 2560×1440 (horizontal) or 1080×1920 (vertical)
   - FPS: 60
   - Encoder: NVENC H.264

---

## Step 3: Configure NDI Sources

For each NDI widget source:
1. Click source → Properties
2. Select NDI name from dropdown:
   - `MINDSONG-Piano`
   - `MINDSONG-Fretboard`
   - `MINDSONG-COF`
   - etc.
3. Set bandwidth to "Highest"

---

## Step 4: Configure Cameras

1. Click camera source → Properties
2. Select your device
3. Set resolution (1080p60 recommended)
4. Apply color correction filter if needed

---

## Step 5: Test Hotkeys

| Hotkey | Action |
|--------|--------|
| **F1** | Full Teaching Studio |
| **F2** | Close-Up Piano |
| **F3** | Guitar Focus |
| **F4** | Theory Breakdown |
| **Ctrl+R** | Toggle Recording |
| **Ctrl+S** | Toggle Streaming |

---

## Step 6: Voice Control (Optional)

Say: **"Hey ROXY, switch to piano scene"**

See [ROXY_OBS_VOICE_CONTROL.md](ROXY_OBS_VOICE_CONTROL.md) for all commands.

---

## You're Ready! 🎉

- Press **F1** for default teaching layout
- Press **Ctrl+R** to start recording
- Say **"show circle of fifths"** to ROXY

---

## Troubleshooting

**NDI source blank?**
→ Check widget server is running at `localhost:5173`

**Hotkeys not working?**
→ OBS → Settings → Hotkeys → Search for scene name

**Audio not recording?**
→ Check Audio Mixer levels in OBS

---

## Next Steps

1. 📖 Read [HORIZONTAL_LAYOUT_GUIDE.md](HORIZONTAL_LAYOUT_GUIDE.md)
2. 🎹 Set up [MIDI_INTEGRATION_GUIDE.md](MIDI_INTEGRATION_GUIDE.md)
3. 🎬 Learn [ANIMATION_SYSTEM_GUIDE.md](ANIMATION_SYSTEM_GUIDE.md)

---

*Part of the SKOREQ OBS Dream Collection*
