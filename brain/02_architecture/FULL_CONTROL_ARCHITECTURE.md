# ROXY Full Computer Control — Architecture Blueprint

**Goal:** "Hey Roxy, warm up the studio" → lights on, OBS opens, windows positioned, teleprompter ready, cameras armed, record → post-process → upload → monitor feedback.

**Date:** 2026-01-02  
**Status:** Architecture design (not implemented yet)

---

## 🎯 Core Principle: Universal Primitives, Not Per-App Hacks

Don't build "OBS tool", "camera tool", "light tool" separately.  
Build **5 universal control surfaces** that reach everything:

---

## 1️⃣ The Five Universal Primitives

### A) `exec` — Shell/Process Control
**What it does:** Run commands, launch apps, manage processes
```python
exec(command, args=[], timeout=30, capture_output=True)
```

**Examples:**
- `exec("obs")` → launch OBS
- `exec("systemctl", ["--user", "start", "roxy-voice"])` → start service
- `exec("wmctrl", ["-r", "OBS", "-e", "0,0,0,1920,1080"])` → resize window

**Safety:**
- Allowlist mode (approved commands only) OR
- Confirmation gate for unknown commands
- Audit log of every exec

---

### B) `window` — Desktop Window Management
**What it does:** Focus, move, resize, list windows

**X11 tools:** `wmctrl`, `xdotool`  
**Wayland:** `swaymsg` (Sway), compositor-specific, or XDG portals

```python
window.list() → ["OBS Studio", "Firefox", "VS Code"]
window.focus("OBS Studio")
window.move("OBS Studio", x=0, y=0, width=1920, height=1080)
window.get_active() → "OBS Studio"
```

**Use cases:**
- Snap OBS to left half, teleprompter to right half
- Detect if OBS is running/visible
- Multi-monitor layout presets

---

### C) `files` — File System Operations
**What it does:** Read, write, watch, search files

```python
files.read(path)
files.write(path, content)
files.list(directory, pattern="*.md")
files.watch(directory, callback=on_file_change)
files.search(root, query="chord cube script")
```

**Safety:**
- Restricted to allowed roots (e.g., `~/Documents`, `~/Videos`)
- No write to system paths without confirmation

**Use cases:**
- Load teleprompter script from `~/scripts/chord_cubes/`
- Save rendered video to `~/Videos/exports/`
- Watch for new recordings in OBS output folder

---

### D) `net` — Network/API Control
**What it does:** HTTP/WebSocket to control services

```python
net.ws_connect("ws://127.0.0.1:4455", auth=obs_password)
net.ws_send({"op": "SetCurrentScene", "sceneName": "Chord Cubes"})
net.http_post("http://homeassistant:8123/api/services/light/turn_on", {...})
```

**Use cases:**
- OBS WebSocket (scene switch, record start/stop)
- Home Assistant (lights, smart plugs)
- NDI camera control (if camera supports HTTP API)
- Upload to YouTube/TikTok APIs

---

### E) `input` — Keyboard/Mouse Automation (optional, advanced)
**What it does:** Type text, click, press keys

**X11:** `xdotool`  
**Wayland:** `ydotool` (requires elevated permissions), or portals

```python
input.type("Hello from ROXY")
input.click(x=100, y=200)
input.key("ctrl+s")
```

**Use cases:**
- Start teleprompter scroll (if no API exists)
- Click "Go Live" button if no API exists
- **Usually avoidable** — prefer APIs/commands over GUI automation

---

## 2️⃣ Studio Warmup Runbook (Example)

**User says:** "Hey Roxy, warm up the studio for a Chord Cubes video"

**ROXY executes:** `runbooks/warmup_chord_cubes.yaml`

```yaml
name: "Chord Cubes Studio Warmup"
steps:
  - name: "Turn on studio lights"
    tool: net.http_post
    args:
      url: "http://homeassistant:8123/api/services/light/turn_on"
      json: {entity_id: "light.studio_overhead"}
    
  - name: "Launch OBS"
    tool: exec
    args: {command: "obs"}
    wait: 3  # seconds for OBS to start
    
  - name: "Position OBS window"
    tool: window.move
    args: {title: "OBS", x: 0, y: 0, width: 1920, height: 1080}
    
  - name: "Connect to OBS WebSocket"
    tool: net.ws_connect
    args: {url: "ws://127.0.0.1:4455", password: "$OBS_WS_PASSWORD"}
    
  - name: "Set scene to Chord Cubes"
    tool: net.ws_send
    args: {op: "SetCurrentScene", sceneName: "Chord Cubes"}
    
  - name: "Launch teleprompter"
    tool: exec
    args: {command: "qprompt", args: ["~/scripts/chord_cubes/intro.txt"]}
    
  - name: "Position teleprompter window"
    tool: window.move
    args: {title: "QPrompt", x: 1920, y: 0, width: 1920, height: 1080}
    
  - name: "Check camera sources"
    tool: net.ws_send
    args: {op: "GetSourcesList"}
    expect: ["iPhone Camera", "Sony A7"]
    
  - name: "Ready state"
    output: "✅ Studio ready. Say 'start recording' when you're ready."
```

**Key features:**
- **Declarative** (YAML, not imperative code)
- **Idempotent** (can re-run safely)
- **Failure handling** (if step fails, ROXY reports which step + why)
- **Preconditions** (check disk space, verify cameras present)

---

## 3️⃣ Post-Production Pipeline (Watch Folder)

**Trigger:** OBS saves video to `~/Videos/raw/`  
**ROXY watches** that folder and auto-processes

```yaml
name: "Chord Cubes Post Pipeline"
trigger: {type: "file_created", path: "~/Videos/raw/*.mp4"}
steps:
  - name: "Denoise audio"
    tool: exec
    args: {command: "ffmpeg", args: ["-i", "$INPUT", "-af", "arnndn", "$TEMP/denoised.mp4"]}
    
  - name: "Upscale to 4K"
    tool: exec
    args: {command: "realesrgan", args: ["-i", "$TEMP/denoised.mp4", "-o", "$TEMP/upscaled.mp4"]}
    
  - name: "Generate subtitles"
    tool: exec
    args: {command: "whisper", args: ["$TEMP/upscaled.mp4", "--model", "large-v3", "--output_format", "srt"]}
    
  - name: "Burn in styled subtitles"
    tool: exec
    args: {command: "ffmpeg", args: ["-i", "$TEMP/upscaled.mp4", "-vf", "subtitles=$TEMP/subs.srt:force_style='...'", "$OUTPUT/final.mp4"]}
    
  - name: "Create vertical cut (9:16)"
    tool: exec
    args: {command: "ffmpeg", args: ["-i", "$OUTPUT/final.mp4", "-vf", "crop=1080:1920", "$OUTPUT/final_vertical.mp4"]}
    
  - name: "Generate title/description"
    tool: rag_query
    args: {query: "Generate viral YouTube title for chord cube video covering I-V-vi-IV progression"}
    
  - name: "Upload to YouTube"
    tool: net.http_post
    args: {url: "https://www.googleapis.com/upload/youtube/v3/videos", ...}
```

**Watch folder runs in background** — you don't manually trigger it.

---

## 4️⃣ Safety Layers (Chief-Grade Requirements)

### A) Allowlist Mode (Default)
```python
ALLOWED_COMMANDS = [
    "obs", "code", "firefox", "google-chrome",
    "qprompt", "ffmpeg", "whisper",
    "wmctrl", "xdotool",
    "systemctl --user start *",
    "systemctl --user stop *",
]
```

Any command not in allowlist → requires confirmation.

### B) Confirmation Gates
```python
REQUIRE_CONFIRMATION = [
    "rm", "sudo", "chmod", "chown",
    "systemctl --system *",  # system-wide (not user) services
    "shutdown", "reboot",
]
```

### C) Audit Log
Every action logged:
```json
{"timestamp": "2026-01-02T01:30:00Z", "action": "exec", "command": "obs", "user_intent": "warm up studio", "result": "success", "pid": 12345}
```

### D) Dry-Run Mode
Before executing destructive operations:
```python
roxy.dry_run = True  # Shows what WOULD happen
```

---

## 5️⃣ Implementation Priority (Phased Rollout)

### Phase 1: Universal Launcher + Window Layout (1-2 days)
- `exec` tool (allowlist mode)
- `window.list`, `window.move`, `window.focus`
- Test: "open obs and snap to left half"

### Phase 2: OBS WebSocket Control (1 day)
- `net.ws_connect` for OBS
- Scene switching, record start/stop
- Test: "switch to chord cubes scene and start recording"

### Phase 3: Watch Folder Post Pipeline (2-3 days)
- File watcher on `~/Videos/raw/`
- `ffmpeg` denoise + upscale
- `whisper` subtitles
- Test: save recording → auto-processed

### Phase 4: Studio Warmup Runbook (1 day)
- YAML runbook parser
- Multi-step execution with failure handling
- Test: full "warm up studio" command

### Phase 5: Upload + Social Integration (2-3 days)
- YouTube API upload
- Title/description generation from RAG
- Optional: TikTok/IG via scheduling tools

---

## 6️⃣ What About "Open Any App"?

**Short answer:** Use `xdg-open` or desktop entry resolution.

```python
def launch_app(target):
    # Try desktop entry first (respects .desktop files)
    try:
        subprocess.run(["gtk-launch", target], check=True)
        return f"✅ Launched {target}"
    except:
        pass
    
    # Fallback: try as command
    try:
        subprocess.Popen([target], start_new_session=True)
        return f"✅ Launched {target}"
    except FileNotFoundError:
        return f"❌ Not found: {target}"
```

**No per-app routes needed** — this is generic.

---

## 7️⃣ Linux Desktop Type (X11 vs Wayland)

**Check your session:**
```bash
echo $XDG_SESSION_TYPE
```

- **X11:** Full window control via `wmctrl`, `xdotool`
- **Wayland:** More restricted, use compositor-specific tools:
  - Sway: `swaymsg`
  - GNOME: `gdbus` + XDG portals
  - KDE: `kwin` scripting

**Recommendation:** If on Wayland, prefer `exec` + APIs over GUI automation.

---

## 8️⃣ Voice Pipeline Integration

**Current status (per Cursor):**
- `/opt/roxy/voice/` has Whisper STT + openWakeWord
- **Issue:** `/opt/roxy` is legacy stack
- **Fix:** Migrate voice to `~/.roxy/voice/` and integrate with runbooks

**Voice → Runbook flow:**
1. Wake word: "Hey Roxy"
2. Transcribe: "warm up the studio"
3. Route to runbook: `warmup_chord_cubes.yaml`
4. Execute steps
5. TTS feedback: "Studio ready. Cameras armed. Say 'start recording' when ready."

---

## 9️⃣ GPU Optimization (Per Cursor's Work)

**Problem:** All models compete for GPU (Whisper + Ollama + TTS = 15-17GB VRAM overflow)

**Solution:** Hybrid CPU/GPU distribution
- **Whisper → CPU** (56 threads handle it well)
- **Ollama LLM → GPU** (keep for speed)
- **TTS → GPU** (keep for real-time)

**Expected results:**
- Before: 100% GPU, 15-17GB VRAM (overflow)
- After: 60-70% GPU, 10-13GB VRAM (stable)

**Implementation:** Already done by Cursor (`.env` config + service updates)

---

## 🔟 What You DON'T Need

### ❌ Per-app integrations
Don't write separate code for each app — use primitives.

### ❌ A bigger GPU
RX 6900 XT (16GB) is sufficient with proper resource management.

### ❌ "Learning every Linux command"
There are thousands, but 95% of control comes from ~20 primitives.

---

## Summary: The "Studio Autopilot" Stack

| Layer | Tools | Status |
|-------|-------|--------|
| **Universal primitives** | exec, window, files, net, input | **To build** |
| **Runbook engine** | YAML parser + step executor | **To build** |
| **OBS control** | WebSocket client | **Partially done** (needs config fix) |
| **Post pipeline** | Watch folder + ffmpeg/whisper | **To build** |
| **Voice integration** | Wake word + STT → runbooks | **Partially done** (needs migration) |
| **Safety gates** | Allowlist + confirmation + audit | **To build** |

**Time estimate:** 2-3 weeks for full "Studio Autopilot" capability.

**First milestone (this week):** Universal launcher + window layout + OBS WebSocket working.

---

## Next Immediate Steps

1. **Fix OBS WebSocket connection** (config mismatch)
2. **Implement `launch_app` tool** (already done, needs client-side execution)
3. **Add `window` primitives** (wmctrl/xdotool on X11)
4. **Create first runbook:** `warmup_studio.yaml`
5. **Test end-to-end:** "warm up studio" → lights + OBS + windows positioned

**Question for you:** What's your desktop session type?
```bash
echo $XDG_SESSION_TYPE
```
If X11 → easy window control.  
If Wayland → needs compositor-specific approach.
