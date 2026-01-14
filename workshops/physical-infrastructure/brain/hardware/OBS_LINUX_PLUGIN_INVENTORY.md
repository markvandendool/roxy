# 🎬 OBS STUDIO LINUX - COMPLETE PLUGIN INVENTORY
## Mark's Mac Pro Roxy Workstation
### Generated: January 9, 2026

---

## 🚀 INSTALLED PLUGINS (47 Total)

### Core Plugins (Stock OBS 32.0.2)
- **obs-ffmpeg** - FFmpeg encoding/decoding
- **obs-x264** - Software H.264 encoding  
- **obs-nvenc** - NVIDIA hardware encoding
- **obs-qsv11** - Intel QuickSync encoding
- **obs-filters** - Core filters (color correction, crop, etc.)
- **obs-transitions** - Stock transitions
- **obs-outputs** - Streaming/recording outputs
- **obs-browser** - Browser sources (CEF-based)
- **obs-websocket** - WebSocket API (v5)

### Hardware Integration
- **decklink** - Blackmagic DeckLink capture ✅
- **decklink-output-ui** - DeckLink output configuration
- **decklink-captions** - CEA-708 caption support
- **aja** - AJA capture cards
- **linux-v4l2** - Video4Linux2 devices (webcams)
- **linux-pipewire** - PipeWire audio routing ⭐ LINUX EXCLUSIVE
- **linux-pulseaudio** - PulseAudio integration
- **linux-alsa** - ALSA audio devices
- **linux-jack** - JACK audio integration
- **linux-capture** - Screen/window capture

### NDI/Network
- **distroav** - NDI support (DistroAV fork) ✅
- **rtmp-services** - RTMP streaming services

### Scene/Source Management
- **advanced-scene-switcher** - Powerful automation ✅
- **move-transition** - Move sources between scenes ✅
- **vertical-canvas** - TikTok/Shorts vertical output ✅
- **source-copy** - Copy/paste sources
- **downstream-keyer** - Downstream keyer
- **image-source** - Image/slideshow sources
- **text-freetype2** - Text rendering
- **vlc-video** - VLC media source

### Effects & Filters (NEW!)
- **obs-advanced-masks** - Shaped masks, gradients ✅
- **obs-composite-blur** - Gaussian/box blur ✅
- **obs-stroke-glow-shadow** - Text/source outlines ✅
- **obs-retro-effects** - CRT, VHS, Matrix rain ✅ LINUX POWER!
- **obs-noise** - Procedural noise generation ✅
- **obs-shaderfilter** - Custom GLSL shaders ✅
- **obs-backgroundremoval** - AI background removal ✅

### Audio
- **audio-monitor** - Monitor audio sources ✅
- **obs-vst** - VST2 plugin support
- **obs-libfdk** - AAC encoding

### Streaming
- **aitum-multistream** - Multi-platform streaming

---

## 🛠️ STREAM DECK SETUP ✅

### Installed: streamdeck-ui
\`\`\`bash
# Launch Stream Deck UI
streamdeck

# Autostart on login
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/streamdeck-ui.desktop << 'SD'
[Desktop Entry]
Type=Application
Name=Stream Deck UI
Exec=streamdeck
StartupNotify=false
Terminal=false
SD
\`\`\`

### OBS Integration via WebSocket
- obs-websocket v5 already installed
- Stream Deck UI can control scenes, sources, streaming
- Set WebSocket password in OBS Settings → WebSocket Server

---

## 🎛️ LOUPEDECK SETUP

### Installed: ~/Downloads/loupedeckapp/
\`\`\`bash
cd ~/Downloads/loupedeckapp
python3 app.py
\`\`\`

### Features
- Touchbutton images & actions
- Encoder rotation mapping
- Hotkey shortcuts to OS
- Shell command execution
- Workspace/submenu system

---

## 🌟 LINUX-EXCLUSIVE ADVANTAGES

### Things macOS CANNOT DO:

| Feature | macOS | Linux |
|---------|-------|-------|
| Per-app audio capture | Needs virtual cables | linux-pipewire native! |
| Vulkan game capture | ❌ Metal only | obs-vkcapture ✅ |
| KVM VM frame relay | ❌ | obs-plugin-looking-glass |
| AMD hardware encoding | Limited | VAAPI native |
| True multi-GPU | ❌ | Full support |
| GStreamer pipelines | ❌ | obs-gstreamer |

### Performance Wins
- No Metal translation layer overhead
- Direct CUDA/OpenCL for AI effects
- Native Vulkan rendering path
- Better DeckLink latency

---

## 📦 PLUGINS TO BUILD/GET LATER

### From Source (No Linux Releases)
\`\`\`bash
# obs-freeze-filter
git clone https://github.com/exeldro/obs-freeze-filter
cd obs-freeze-filter && mkdir build && cd build
cmake .. && make && sudo make install

# obs-scale-to-sound  
git clone https://github.com/dimtpap/obs-scale-to-sound
\`\`\`

### From APT (Version mismatch - need OBS 30)
- obs-scene-tree-view
- obs-scene-collection-manager
- obs-transition-table

---

## 🔄 MIGRATION STATUS

### Assets Transfer
- Source: macstudio:/Volumes/Renders/ORION BACKUP LINUX/OBS Portable/
- Destination: ~/.roxy/obs-portable/
- Size: 18 GB
- Status: IN PROGRESS

### Path Remapping Required
\`\`\`bash
# After transfer completes:
cd ~/.roxy/workshops/physical-infrastructure/brain/hardware/
jq --arg old "/Volumes/Orion/OBS Portable" \
   --arg new "/home/mark/.roxy/obs-portable/assets" \
   'walk(if type == "string" then gsub($old; $new) else . end)' \
   Harry_Elgato_Fall_Freeze_fkup.json > Harry_Remapped.json
\`\`\`

### Import to OBS
1. Copy remapped JSON to ~/.config/obs-studio/basic/scenes/
2. OBS → Scene Collection → Import
3. Fix any remaining broken paths in OBS

---

## 🎮 HARDWARE TO CONFIGURE

- [ ] DeckLink inputs (4 cameras)
- [ ] CamLink/USB cameras  
- [ ] NDI sources (iMac GoPro, Dice)
- [ ] M-Audio AIR 192 4 (audio interface)
- [ ] Stream Deck XL
- [ ] Loupedeck Live

