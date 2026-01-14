# Top Bar System Monitor Setup

## ✅ Installed: GNOME Vitals Extension

The **Vitals** extension shows CPU, GPU, Memory, Disk, Network, and Temperature in your GNOME top bar.

### Features:
- **CPU Usage**: Real-time CPU percentage
- **GPU Usage**: Both AMD GPUs (Navi 10 + Navi 21)
- **Memory**: RAM usage
- **Disk**: I/O activity
- **Network**: Up/down speeds
- **Temperature**: CPU and GPU temps
- **Battery**: If applicable

### How to Configure:

1. **Open Extension Preferences:**
   ```bash
   gnome-shell-extension-prefs vitals@CoreCoding.com
   ```
   Or use: `gnome-extensions-app` and search for "Vitals"

2. **Enable/Disable Metrics:**
   - Toggle which metrics appear in top bar
   - Choose display style (compact/full)
   - Set update interval
   - Configure colors

3. **Enable the Extension:**
   ```bash
   gnome-extensions enable vitals@CoreCoding.com
   ```

### Alternative Extensions:

If Vitals doesn't work, try:
- **System Monitor**: `system-monitor@gnome-shell-extensions.gcampax.github.com`
- **Freon**: Temperature monitoring
- **CPU Power Manager**: CPU frequency/usage

### Manual Installation (if needed):

```bash
# Download from extensions.gnome.org
# Or install via:
sudo apt install gnome-shell-extension-vitals
gnome-extensions enable vitals@CoreCoding.com
```

### Check Status:
```bash
gnome-extensions list --enabled | grep vitals
```

The vitals will appear in your top bar next to the system menu!
