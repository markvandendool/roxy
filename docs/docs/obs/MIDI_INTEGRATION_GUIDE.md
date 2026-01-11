# 🎹 MIDI Integration Guide

> **Version:** 1.0.0  
> **EPIC:** SKOREQ-OBS-DREAM  
> **Story:** STORY-009  
> **Platform:** Linux (ALSA)

---

## Overview

The SKOREQ system integrates MIDI for:

1. **OBS Control** - Scene switching, source toggles, transport
2. **Widget Visualization** - Real-time piano/fretboard display
3. **Key Transposition** - Animated key changes via MIDI

---

## Prerequisites

### Required Software

```bash
# Install MIDI utilities
sudo apt install alsa-utils alsa-tools qjackctl kmidimon

# Virtual MIDI ports
sudo modprobe snd-virmidi
```

### OBS Plugin

Install [obs-midi-mg](https://github.com/nhielost/obs-midi-mg):

```bash
# Download latest release for Linux
# Copy to ~/.config/obs-studio/plugins/
```

---

## MIDI Device Setup

### List Connected Devices

```bash
aconnect -l
```

Example output:
```
client 0: 'System' [type=kernel]
    0 'Timer           '
client 14: 'Midi Through' [type=kernel]
    0 'Midi Through Port-0'
client 20: 'USB MIDI Keyboard' [type=kernel,card=1]
    0 'USB MIDI Keyboard MIDI 1'
client 24: 'Launchpad Mini' [type=kernel,card=2]
    0 'Launchpad Mini MIDI 1'
```

### Create Virtual MIDI Port

For software routing:

```bash
# Load virtual MIDI kernel module
sudo modprobe snd-virmidi

# Verify
aconnect -l | grep -i virmidi
```

Make persistent:
```bash
echo "snd-virmidi" | sudo tee /etc/modules-load.d/virmidi.conf
```

---

## OBS MIDI Bindings

### Scene Switching

| MIDI Note | Channel | Scene |
|-----------|---------|-------|
| C2 (36) | 1 | 📺 M1: Full Teaching Studio |
| C#2 (37) | 1 | 📺 M2: Close-Up Piano |
| D2 (38) | 1 | 📺 M3: Guitar Focus |
| D#2 (39) | 1 | 📺 M4: Theory Breakdown |
| E2 (40) | 1 | 📺 M5: Multi-Instrument |
| F2 (41) | 1 | 📺 M6: Full Widget Array |
| F#2 (42) | 1 | 📺 M7: DAW Production |
| G2 (43) | 1 | 📺 M8: Interview Mode |

### Source Toggles

| MIDI Note | Channel | Source |
|-----------|---------|--------|
| C3 (48) | 1 | 🎹 PianoWidget |
| C#3 (49) | 1 | 🎸 FretboardWidget |
| D3 (50) | 1 | 🔵 CircleOfFifths |
| D#3 (51) | 1 | 📊 HarmonicProfile |
| E3 (52) | 1 | 🎵 ScoreTab |
| F3 (53) | 1 | ⏱️ Metronome |
| F#3 (54) | 1 | 🌀 BraidWidget |
| G3 (55) | 1 | 📐 TempoGeometry |

### Transport Controls

| MIDI Note | Channel | Action |
|-----------|---------|--------|
| C4 (60) | 1 | Toggle Recording |
| C#4 (61) | 1 | Toggle Streaming |
| D4 (62) | 1 | Pause Recording |
| D#4 (63) | 1 | Screenshot |

### Fader Controls (CC)

| CC | Channel | Action |
|----|---------|--------|
| CC 1 | 1 | Desktop Audio Level |
| CC 2 | 1 | Mic/Aux Level |
| CC 3 | 1 | Piano Widget Opacity |
| CC 4 | 1 | Fretboard Opacity |
| CC 7 | 1 | Camera Brightness |

---

## Widget MIDI Visualization

### Routing Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ MIDI        │────▶│ DAW         │────▶│ Widget      │
│ Keyboard    │     │ (Ableton)   │     │ Server      │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
                                        ┌─────────────┐
                                        │ NDI to OBS  │
                                        └─────────────┘
```

### Connect MIDI to Widget Server

```bash
# Find device IDs
aconnect -l

# Route MIDI keyboard to widget server
aconnect 'USB MIDI Keyboard':0 'Widget Server':0
```

### Widget Server MIDI Port

The widget server (Theater 8K) listens on a virtual MIDI port:

```javascript
// Widget server MIDI configuration
{
  "midi": {
    "enabled": true,
    "portName": "Widget Server",
    "channels": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "noteRange": [21, 108]  // Piano range A0-C8
  }
}
```

---

## Key Transposition via MIDI

### Method 1: CC Messages

| CC | Channel | Action |
|----|---------|--------|
| CC 16 | 1 | Transpose Up |
| CC 17 | 1 | Transpose Down |
| CC 18 | 1 | Reset to C |

### Method 2: Keyboard Input

Play C4-B4 on Channel 2 to set key:

| Note | Key |
|------|-----|
| C4 (60) | C Major |
| C#4 (61) | Db Major |
| D4 (62) | D Major |
| ... | ... |
| B4 (71) | B Major |

### Implementation

```python
# MCP tool for MIDI-triggered transposition
@mcp_tool("midi_transpose")
async def handle_transpose(note: int, channel: int):
    if channel == 2 and 60 <= note <= 71:
        key = NOTE_TO_KEY[note - 60]
        await animate_key_shift(key)
        await update_widgets(key)
```

---

## Latency Testing

### Target Latencies

| Path | Target | Acceptable |
|------|--------|------------|
| MIDI → Widget | < 5ms | < 10ms |
| Widget Render | < 10ms | < 16ms |
| NDI → OBS | < 5ms | < 10ms |
| **Total** | **< 20ms** | **< 50ms** |

### Test Procedure

1. **Setup**: High-speed camera recording both keyboard and screen
2. **Action**: Play note on keyboard
3. **Measure**: Count frames between keypress and visual update
4. **Calculate**: `latency = frames / fps`

### Latency Test Script

```bash
#!/bin/bash
# midi-latency-test.sh

echo "MIDI Latency Test for SKOREQ"
echo "============================"
echo ""

# Check MIDI devices
echo "1. Connected MIDI Devices:"
aconnect -l | grep -E "client [0-9]+:"
echo ""

# Check latency mode
echo "2. Checking USB latency..."
cat /sys/module/snd_usb_audio/parameters/nrpacks 2>/dev/null || echo "Default nrpacks"
echo ""

# Test MIDI throughput
echo "3. MIDI throughput test (5 seconds)..."
echo "   Press keys on your MIDI device..."
timeout 5 aseqdump -p "USB MIDI Keyboard" 2>/dev/null | head -20
echo ""

# Check system load
echo "4. System performance:"
echo "   CPU: $(grep 'cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$4+$5)} END {print usage "%"}')"
echo "   Memory: $(free -h | awk '/Mem:/ {print $3 "/" $2}')"
echo ""

# Check NDI
echo "5. NDI sources:"
avahi-browse -t _ndi._tcp 2>/dev/null | head -10 || echo "NDI discovery not available"
echo ""

echo "Test complete. For detailed latency measurement,"
echo "record screen + audio at 240fps and count frames."
```

Make executable:
```bash
chmod +x ~/.roxy/scripts/midi-latency-test.sh
```

---

## Troubleshooting

### MIDI Not Received

```bash
# Check device is connected
lsusb | grep -i midi

# Check ALSA sees it
aconnect -l

# Monitor MIDI input
aseqdump -p "USB MIDI Keyboard"

# Check permissions
sudo usermod -a -G audio $USER
# (logout/login required)
```

### High Latency

```bash
# Reduce USB audio buffer
echo "options snd-usb-audio nrpacks=1" | sudo tee /etc/modprobe.d/usb-audio.conf

# Use realtime scheduling
sudo usermod -a -G realtime $USER

# Check for CPU throttling
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
# Set to performance if needed
```

### MIDI Channel Conflicts

Use different channels:
- **Channel 1**: OBS control (scenes, sources)
- **Channel 2**: Key transposition
- **Channel 3-10**: DAW instruments

---

## Complete ALSA Routing Script

```bash
#!/bin/bash
# setup-midi-routing.sh

echo "Setting up MIDI routing for SKOREQ..."

# Wait for devices
sleep 2

# Get device IDs
KEYBOARD=$(aconnect -l | grep -i "midi keyboard" | grep -oP "client \K[0-9]+")
CONTROLLER=$(aconnect -l | grep -i "launchpad\|apc\|push" | grep -oP "client \K[0-9]+")
VIRMIDI=$(aconnect -l | grep -i "virmidi" | grep -oP "client \K[0-9]+")

# Route keyboard to virtual port (for widget server)
if [ -n "$KEYBOARD" ] && [ -n "$VIRMIDI" ]; then
    aconnect "$KEYBOARD":0 "$VIRMIDI":0
    echo "✓ Keyboard routed to virtual port"
fi

# Controller goes direct to OBS (via obs-midi plugin)
if [ -n "$CONTROLLER" ]; then
    echo "✓ Controller available for OBS-MIDI: client $CONTROLLER"
fi

echo "MIDI routing complete!"
aconnect -l
```

---

## Related Documentation

- [ANIMATION_SYSTEM_GUIDE.md](ANIMATION_SYSTEM_GUIDE.md) - Key transposition animations
- [NDI_WIDGET_ARCHITECTURE.md](NDI_WIDGET_ARCHITECTURE.md) - Widget communication
- [ROXY_OBS_VOICE_CONTROL.md](ROXY_OBS_VOICE_CONTROL.md) - Voice alternatives

---

*Part of the SKOREQ OBS Dream Collection*
