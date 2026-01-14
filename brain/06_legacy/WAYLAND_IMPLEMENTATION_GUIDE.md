# ROXY Full Control — Wayland Implementation Guide

**Your system:** Wayland session  
**Compositor:** (checking...)  
**Challenge:** Wayland restricts window control for security  
**Solution:** Use compositor-specific tools + XDG portals

---

## 🚨 Wayland Reality Check

Unlike X11, Wayland **intentionally restricts** cross-app control:
- ❌ No global window list (security by design)
- ❌ No arbitrary window focus/move (requires compositor cooperation)
- ✅ Can still launch apps, manage processes, control via APIs
- ✅ Can use compositor-specific commands (if supported)

**This is not a bug — it's Wayland's design philosophy.**

---

## ✅ What DOES Work on Wayland

### 1) App Launching (WORKS)
```bash
# Desktop entries
gtk-launch com.obsproject.Studio

# Direct commands
obs &

# XDG open (for files/URLs)
xdg-open ~/Videos/latest.mp4
```

### 2) Process Management (WORKS)
```bash
# Start/stop services
systemctl --user start roxy-voice

# Kill processes
pkill obs
```

### 3) API/WebSocket Control (WORKS — BEST APPROACH)
```bash
# OBS WebSocket
wscat -c ws://127.0.0.1:4455

# Home Assistant
curl http://homeassistant:8123/api/services/light/turn_on
```

### 4) File Operations (WORKS)
```bash
# Watch folders, read/write files
inotifywait -m ~/Videos/raw/
```

---

## ⚠️ What's HARDER on Wayland

### Window Management
**X11:** `wmctrl -r OBS -e 0,0,0,1920,1080` (easy)  
**Wayland:** Depends on compositor

**Your options:**

#### A) If using GNOME (check with `echo $XDG_CURRENT_DESKTOP`)
```bash
# Focus window
gdbus call --session --dest org.gnome.Shell \
  --object-path /org/gnome/Shell \
  --method org.gnome.Shell.Eval \
  "global.get_window_actors().find(w => w.meta_window.title.includes('OBS')).meta_window.activate()"

# List windows
gdbus call --session --dest org.gnome.Shell \
  --object-path /org/gnome/Shell \
  --method org.gnome.Shell.Eval \
  "global.get_window_actors().map(w => w.meta_window.title)"
```

#### B) If using KDE Plasma
```bash
# Use KWin scripting
qdbus org.kde.KWin /KWin org.kde.KWin.setCurrentDesktop 1
```

#### C) If using Sway (tiling WM)
```bash
# Sway has excellent control
swaymsg '[app_id="obs"] focus'
swaymsg '[app_id="obs"] move position 0 0'
swaymsg '[app_id="obs"] resize set 1920 1080'
```

---

## 🎯 Recommended Approach for ROXY

**Don't fight Wayland — embrace APIs instead of window hacks.**

### Studio Warmup (Wayland-friendly version)

```yaml
name: "Chord Cubes Studio Warmup"
steps:
  # ✅ WORKS: Launch apps
  - name: "Launch OBS"
    tool: exec
    args: {command: "gtk-launch", args: ["com.obsproject.Studio"]}
    
  # ✅ WORKS: API control (better than window positioning)
  - name: "Connect to OBS WebSocket"
    tool: net.ws_connect
    args: {url: "ws://127.0.0.1:4455", password: "$OBS_WS_PASSWORD"}
    
  # ✅ WORKS: Set scene via API (not GUI automation)
  - name: "Set scene to Chord Cubes"
    tool: net.ws_send
    args: {op: "SetCurrentProgramScene", sceneName: "Chord Cubes"}
    
  # ✅ WORKS: Launch teleprompter
  - name: "Launch teleprompter"
    tool: exec
    args: {command: "qprompt", args: ["~/scripts/chord_cubes/intro.txt"]}
    
  # ⚠️ WAYLAND-SPECIFIC: Window positioning
  # Option 1: Skip positioning (let user arrange windows once, then OBS remembers)
  # Option 2: Use compositor-specific commands (see below)
  # Option 3: Use GNOME extensions or Sway config for auto-layout
  
  # ✅ WORKS: Check sources via API
  - name: "Verify camera sources"
    tool: net.ws_send
    args: {op: "GetSourcesList"}
    expect: ["iPhone Camera", "Sony A7"]
```

---

## 🔧 Practical Workarounds

### 1) Window Positioning: Use OBS's "Remember Position"
Instead of ROXY positioning windows every time:
- Arrange windows manually ONCE
- OBS remembers position on next launch
- ROXY just launches apps, they auto-position

### 2) Multi-Monitor: Use Display Settings Presets
GNOME/KDE allow saving display configurations:
```bash
# Switch to "Studio" display profile
gnome-monitor-config set studio
```

### 3) Tiling WM: Use Sway Workspaces
If you switch to Sway (popular tiling WM on Wayland):
```bash
# Workspace 1: Studio layout
swaymsg 'workspace 1; exec obs; exec qprompt'
```

---

## 🚀 Quick Wins (Implement These First)

### Phase 1: API-First Control (2-3 days)
✅ Focus on what works universally:
- App launching (gtk-launch, exec)
- OBS WebSocket (scene control, record start/stop)
- Home Assistant API (lights)
- Process management (systemctl)

**Skip** window positioning for now — users can arrange manually.

### Phase 2: Watch Folder Post-Production (2 days)
✅ This works identically on Wayland:
- Watch ~/Videos/raw/ for new files
- Auto-process: denoise, upscale, subtitles
- No GUI automation needed

### Phase 3: Voice Integration (1-2 days)
✅ Wake word → transcription → runbook execution
- Works same on Wayland
- No window control needed for voice pipeline

---

## 📊 Wayland Capability Matrix

| Capability | X11 | Wayland | ROXY Approach |
|------------|-----|---------|---------------|
| Launch app | ✅ Easy | ✅ Easy | `gtk-launch` or `exec` |
| Window focus | ✅ Easy | ⚠️ Hard | **Skip** (use APIs instead) |
| Window resize | ✅ Easy | ⚠️ Hard | **Skip** (OBS remembers position) |
| OBS control | ✅ API | ✅ API | **WebSocket** (works everywhere) |
| Lights control | ✅ API | ✅ API | **Home Assistant API** |
| File operations | ✅ Easy | ✅ Easy | Standard filesystem tools |
| Process mgmt | ✅ Easy | ✅ Easy | systemctl, pkill, pgrep |
| Input automation | ✅ Easy | ❌ Restricted | **Avoid** (use APIs instead) |

---

## 🎬 Your "Warm Up Studio" Flow (Wayland-Optimized)

**What you say:** "Hey Roxy, warm up the studio"

**What happens:**
1. ✅ Turn on lights (Home Assistant API)
2. ✅ Launch OBS (gtk-launch)
3. ⏭️ Skip window positioning (OBS remembers from last time)
4. ✅ Connect to OBS WebSocket
5. ✅ Set scene to "Chord Cubes" (via API)
6. ✅ Launch teleprompter (exec)
7. ✅ Verify camera sources (via API)
8. ✅ Arm recording (via API)
9. ✅ Voice feedback: "Studio ready. Say 'start recording' when ready."

**Total skipped:** Only window positioning (which you can do manually once).

---

## 🔑 Key Takeaway

**On Wayland, embrace APIs over window hacking.**

Your workflow is actually **easier** on Wayland because:
- OBS has WebSocket API (better than window control)
- Lights have API (Home Assistant)
- Cameras (if NDI/HTTP) have API
- Post-processing doesn't need GUI

The ONLY thing harder is "snap windows to exact positions" — and that's optional if apps remember their layout.

---

## Next Steps

1. **Fix OBS WebSocket config** (user saw connection error)
   ```bash
   # Check if OBS WebSocket is listening
   ss -lptn | grep 4455
   
   # Update ROXY's OBS config to match
   rg -n "obs|websocket|4455" ~/.roxy -S
   ```

2. **Implement launch_app tool** (already done in server, test it)
   ```bash
   curl -H "X-ROXY-Token: $(cat ~/.roxy/secret.token)" \
     -H "Content-Type: application/json" \
     -d '{"command":"open obs"}' \
     http://127.0.0.1:8766/run
   ```

3. **Create first runbook** (warmup_studio.yaml)

4. **Test end-to-end** without window positioning

**Timeline:** 1 week for "Studio Autopilot MVP" (launch + API control + post-processing).

**Question:** What compositor are you using?
```bash
echo $XDG_CURRENT_DESKTOP
```
(GNOME, KDE, Sway, or other?)
