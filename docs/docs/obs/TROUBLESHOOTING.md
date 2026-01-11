# 🔧 SKOREQ Troubleshooting Guide

> Solutions for common issues with the SKOREQ OBS Dream Collection

---

## NDI Issues

### NDI Source Shows Black/Blank

**Symptoms:** NDI widget source is added but shows nothing

**Solutions:**

1. **Check widget server is running**
   ```bash
   curl http://localhost:5173
   # Should return HTML
   ```

2. **Verify NDI name matches exactly**
   - Source Properties → NDI Source Name
   - Must match: `MINDSONG-Piano`, `MINDSONG-Fretboard`, etc.
   - Case-sensitive!

3. **Restart NDI runtime**
   ```bash
   sudo systemctl restart avahi-daemon
   ```

4. **Check firewall**
   ```bash
   # NDI uses ports 5960-5969 and mDNS
   sudo ufw allow 5960:5969/tcp
   sudo ufw allow 5960:5969/udp
   sudo ufw allow 5353/udp
   ```

5. **Force NDI discovery**
   - In source properties, click "Refresh"
   - Or restart OBS

---

### NDI High Latency

**Symptoms:** Widget updates are delayed (>100ms)

**Solutions:**

1. **Set NDI to low latency mode**
   - Source Properties → Latency: "Lowest"

2. **Check network**
   ```bash
   # Should be < 1ms for localhost
   ping -c 10 localhost
   ```

3. **Reduce widget complexity**
   - Disable unused widgets
   - Lower widget resolution if possible

4. **Check CPU/GPU usage**
   - OBS → View → Stats
   - Should be < 50% CPU, < 80% GPU

---

### NDI Sources Not Appearing in List

**Solutions:**

1. **Install NDI runtime**
   ```bash
   # For DistroAV
   sudo apt install obs-ndi
   ```

2. **Check mDNS/Avahi**
   ```bash
   avahi-browse -t _ndi._tcp
   # Should list NDI sources
   ```

3. **Widget server NDI not enabled**
   - Check widget URL includes `?ndi=true`

---

## Scene Issues

### Scenes Not Switching

**Symptoms:** F-key hotkeys don't work

**Solutions:**

1. **Check hotkey assignment**
   - OBS → Settings → Hotkeys
   - Search for scene name
   - Reassign if empty

2. **OBS doesn't have focus**
   - Click on OBS window first
   - Or use global hotkeys (may need permissions)

3. **Key conflict**
   - Another app may be capturing F-keys
   - Try with OBS focused

---

### Scene Shows Wrong Layout

**Symptoms:** Sources are mispositioned

**Solutions:**

1. **Reset to saved transform**
   - Right-click source → Transform → Reset Transform

2. **Re-import scene collection**
   - Scene Collection → Import
   - Select backup JSON

3. **Check profile matches**
   - Wrong profile = wrong resolution
   - Profile → Select correct profile

---

## Camera Issues

### Camera Not Detected

**Solutions:**

1. **Check device connection**
   ```bash
   v4l2-ctl --list-devices
   ```

2. **Check permissions**
   ```bash
   sudo usermod -a -G video $USER
   # Logout/login required
   ```

3. **Device in use by another app**
   - Close other video apps
   - Check: `fuser /dev/video0`

---

### Decklink Capture Blank

**Solutions:**

1. **Check Decklink firmware**
   ```bash
   BlackmagicDesktopVideoSetup
   ```

2. **Verify input settings**
   - Resolution must match source exactly
   - Check SDI/HDMI input selection

3. **Check cable/connection**
   - Try different input
   - Check camera is outputting

---

## Audio Issues

### No Audio in Recording

**Solutions:**

1. **Check Audio Mixer**
   - Levels should be moving
   - Unmute sources

2. **Check source settings**
   - Source Properties → Audio
   - Ensure correct device selected

3. **Check output settings**
   - Settings → Output → Audio Track
   - Ensure track is enabled

---

### Audio Out of Sync

**Solutions:**

1. **Apply sync offset**
   - Advanced Audio Properties
   - Add positive offset for late audio
   - Add negative offset for early audio

2. **Check sample rate**
   - Settings → Audio → Sample Rate
   - Should match interface (typically 48kHz)

---

## Animation Issues

### Move Transition Not Working

**Symptoms:** Sources don't animate

**Solutions:**

1. **Check filter is applied**
   - Source → Filters
   - Should see "Move Source" filter

2. **Check trigger settings**
   - Filter Properties → Start Trigger
   - Typically "Show" for entrance

3. **Verify plugin installed**
   ```bash
   ls ~/.config/obs-studio/plugins/ | grep move
   ```

---

### Key Transposition Not Animating

**Solutions:**

1. **Check move_source_filter applied to all widgets**
   - Each widget needs its own filter

2. **Verify animation parameters**
   ```json
   {
     "pos_x": "-=160",  // Relative position
     "duration": 1300,
     "easing": 7
   }
   ```

3. **Check hotkey triggers filter**
   - Advanced Scene Switcher macro
   - Or obs-websocket command

---

## MIDI Issues

### MIDI Not Received

**Solutions:**

1. **Check device connected**
   ```bash
   aconnect -l
   ```

2. **Check obs-midi plugin**
   - Tools → obs-midi
   - Device should be listed

3. **Verify MIDI channel**
   - Default is Channel 1
   - Check device isn't on different channel

4. **Test MIDI input**
   ```bash
   aseqdump -p "Device Name"
   # Play notes, should show output
   ```

---

### MIDI High Latency

**Solutions:**

1. **Reduce USB buffer**
   ```bash
   echo "options snd-usb-audio nrpacks=1" | sudo tee /etc/modprobe.d/usb-audio.conf
   # Reboot required
   ```

2. **Use direct USB (no hub)**

3. **Close other MIDI apps**

---

## Performance Issues

### High CPU Usage

**Solutions:**

1. **Reduce preview resolution**
   - Settings → Video → Base Resolution (lower)

2. **Disable unused sources**
   - Hide sources you're not using

3. **Use hardware encoding**
   - Settings → Output → Encoder → NVENC/VAAPI

4. **Lower FPS**
   - 30fps instead of 60fps for recording

---

### Frame Drops

**Symptoms:** Stuttering, "Encoding overloaded"

**Solutions:**

1. **Lower output resolution**
   - 1080p instead of 1440p

2. **Increase encoder preset speed**
   - NVENC: Performance instead of Quality

3. **Close background apps**

4. **Check thermal throttling**
   ```bash
   sensors
   # CPU should be < 90°C
   ```

---

### GPU Memory Issues

**Solutions:**

1. **Reduce source count**
   - Combine sources into nested scenes
   - Disable unused NDI sources

2. **Lower texture quality**
   - Some sources have quality settings

3. **Restart OBS periodically**
   - Memory leaks accumulate

---

## LocalVocal Issues

### Captions Not Appearing

**Solutions:**

1. **Check filter is enabled**
   - Source → Filters → LocalVocal should be active

2. **Check model loaded**
   - First run downloads model
   - Check ~/.cache/obs-localvocal/

3. **Check audio input**
   - LocalVocal needs audio source
   - Verify microphone is working

---

### Poor Transcription Accuracy

**Solutions:**

1. **Use larger model**
   - medium.en instead of small.en
   - Better accuracy, higher CPU

2. **Improve audio quality**
   - Reduce background noise
   - Use proper microphone

3. **Adjust sensitivity**
   - Filter Properties → Sensitivity

---

## Getting Help

### Collect Diagnostic Info

```bash
# System info
uname -a
obs --version

# GPU info
nvidia-smi || lspci | grep VGA

# OBS logs
cat ~/.config/obs-studio/logs/$(ls -t ~/.config/obs-studio/logs/ | head -1)
```

### Log Locations

- OBS logs: `~/.config/obs-studio/logs/`
- Plugin configs: `~/.config/obs-studio/plugin_config/`
- Crash reports: `~/.config/obs-studio/crashes/`

### Community Resources

- OBS Forums: https://obsproject.com/forum/
- OBS Discord: https://discord.gg/obsproject
- NDI Discord: https://discord.gg/ndi

---

*Part of the SKOREQ OBS Dream Collection*
