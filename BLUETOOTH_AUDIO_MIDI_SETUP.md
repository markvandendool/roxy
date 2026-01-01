# Bluetooth, Audio & MIDI Setup Guide

## Current Status

### ✅ Working
- **MIDI Devices**: Multiple MIDI devices detected and working
  - Loupedeck CT
  - Launchpad Pro MK3 (3 ports: MIDI, DIN, DAW)
  - APC Key 25 mk2 (Keys + Control)
  - SSCOM MIDI devices (2 ports)
  - Midi Through (virtual)
- **Audio System**: PipeWire running and managing audio
  - Apple T2 Audio (built-in)
  - USB Advanced Audio Device
  - HDMI Audio (HDA ATI HDMI)
- **Bluetooth Service**: Running but no controller detected

### ⚠️ Needs Setup
- **Bluetooth**: No default controller available
  - Bluetooth kernel module is loaded
  - Service is running
  - May need USB Bluetooth adapter or driver configuration

## MIDI Setup

### Current MIDI Devices
```bash
# List MIDI devices
aconnect -l

# Connect MIDI devices (example)
aconnect 40:0 144:0  # Connect Launchpad to PipeWire
```

### WebMIDI in Browser
The mindsong-juke-hub project uses WebMIDI API which works directly in browsers:
- Navigate to the app at `http://127.0.0.1:9135`
- MIDI devices should appear automatically via WebMIDI
- Use the MIDI Device Selector component in the UI

## Audio Setup

### PipeWire Commands
```bash
# Check audio status
wpctl status

# List audio devices
wpctl list-devices

# Set default sink (output)
wpctl set-default <device-id>

# Set volume
wpctl set-volume @DEFAULT_AUDIO_SINK@ 50%

# List sinks (outputs)
wpctl list-sinks

# List sources (inputs)
wpctl list-sources
```

### Audio Routing
- Default output: Check with `wpctl status`
- Switch outputs: Use `wpctl set-default <device-id>`
- Volume control: `wpctl set-volume @DEFAULT_AUDIO_SINK@ <0-100>%`

## Bluetooth Setup

### Check Hardware
```bash
# Check if Bluetooth hardware exists
lsusb | grep -i bluetooth
lspci | grep -i bluetooth
rfkill list bluetooth
```

### Enable Bluetooth (if hardware available)
```bash
# Power on Bluetooth
bluetoothctl power on

# Make discoverable
bluetoothctl discoverable on

# Scan for devices
bluetoothctl scan on

# Pair device
bluetoothctl pair <MAC_ADDRESS>

# Connect device
bluetoothctl connect <MAC_ADDRESS>

# Trust device (auto-connect)
bluetoothctl trust <MAC_ADDRESS>
```

### If No Bluetooth Controller
1. **Check for USB Bluetooth adapter**: `lsusb`
2. **Install drivers** (if needed):
   ```bash
   sudo apt update
   sudo apt install bluez bluez-tools
   ```
3. **Check kernel modules**: `lsmod | grep bluetooth`
4. **Restart Bluetooth service**:
   ```bash
   sudo systemctl restart bluetooth
   ```

## macOS Features Comparison

### What's Available on Linux
- ✅ **MIDI**: Full MIDI support via ALSA + PipeWire
- ✅ **Audio**: PipeWire (better than macOS CoreAudio in many ways)
- ✅ **WebMIDI**: Browser-based MIDI (same as macOS)
- ⚠️ **Bluetooth**: Needs hardware/driver setup
- ✅ **Audio Routing**: PipeWire provides advanced routing

### What Might Be Different
- **CoreAudio**: Linux uses PipeWire/ALSA (more flexible)
- **Bluetooth Audio**: May need additional setup for A2DP
- **MIDI Routing**: Uses `aconnect` instead of macOS MIDI Studio

## Quick Commands Reference

```bash
# MIDI
aconnect -l                    # List MIDI devices
aconnect <src> <dest>         # Connect MIDI devices

# Audio
wpctl status                   # Audio status
wpctl set-volume @DEFAULT_AUDIO_SINK@ 50%  # Set volume
wpctl list-devices            # List audio devices

# Bluetooth
bluetoothctl power on          # Power on
bluetoothctl devices          # List paired devices
bluetoothctl scan on          # Scan for new devices
```

## Next Steps

1. **For Bluetooth**: Check if you have a USB Bluetooth adapter or if built-in Bluetooth needs drivers
2. **For Audio**: Test audio routing with `wpctl` commands
3. **For MIDI**: MIDI is already working! Use the browser's WebMIDI or `aconnect` for routing

## Browser WebMIDI Access

The mindsong-juke-hub app at `http://127.0.0.1:9135` should automatically detect MIDI devices via the WebMIDI API. No additional setup needed - just allow MIDI access when the browser prompts.




















