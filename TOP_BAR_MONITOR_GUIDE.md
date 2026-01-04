# Top Bar System Monitor - GNOME Extension Guide

## ✅ Currently Enabled: System Monitor Extension

The **System Monitor** extension is now enabled and will appear in your top bar after restarting GNOME Shell.

### How to See It:

1. **Restart GNOME Shell:**
   - Press `Alt + F2`
   - Type `r`
   - Press `Enter`
   - OR log out and back in

2. **Configure It:**
   - Open: `gnome-extensions-app`
   - Find "System Monitor" in the list
   - Click the gear icon to configure
   - Choose what to display (CPU, Memory, Network, etc.)

### Better Option: Install Vitals Extension

**Vitals** is more popular and shows more metrics (CPU, GPU, Memory, Disk, Network, Temperature):

```bash
# Option 1: Use install script
bash /opt/roxy/INSTALL_VITALS_EXTENSION.sh

# Option 2: Install via browser
# Visit: https://extensions.gnome.org/extension/1460/vitals/
# Click "Install" (requires browser extension)
```

### What Linux Users Use:

1. **Vitals** - Most popular, shows CPU/GPU/Memory/Disk/Network/Temp
2. **System Monitor** - Basic CPU/Memory (already enabled)
3. **Freon** - Temperature monitoring
4. **CPU Power Manager** - CPU frequency/usage

### Quick Commands:

```bash
# List all extensions
gnome-extensions list

# Enable System Monitor
gnome-extensions enable system-monitor@gnome-shell-extensions.gcampax.github.com

# Open extension manager
gnome-extensions-app

# Restart GNOME Shell (to see changes)
# Alt+F2, type 'r', Enter
```

The monitor will appear in your top bar (usually on the right side, near the system menu)!
