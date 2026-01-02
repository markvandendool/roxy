# 🖱️ Logitech Mouse Button Programming Setup Guide

**Date**: January 2025  
**Mouse**: Logitech G502 SE HERO Gaming Mouse  
**System**: Linux (Wayland)  
**Goal**: Full button programming like Logitech Options/G HUB

---

## Overview

You have a **Logitech G502 SE HERO** gaming mouse with multiple programmable buttons. On Linux, you can achieve Logitech-like control using two main approaches:

1. **Input Remapper** (Recommended) - Works on Wayland, GUI-based, supports all mice
2. **Piper + libratbag** - Best for Logitech gaming mice, uses hardware-level configuration

---

## Option 1: Input Remapper (Best for Wayland)

### Why Input Remapper?
- ✅ Works on **Wayland** (your current setup)
- ✅ Works on **X11** (backward compatible)
- ✅ **GUI-based** - Easy to use
- ✅ Supports **all mice** (not just Logitech)
- ✅ Can map buttons to **keyboard shortcuts, macros, commands**
- ✅ **Active development** - Well maintained

### Installation

```bash
# Install Input Remapper
sudo apt update
sudo apt install input-remapper

# Start the service (required for Wayland)
sudo systemctl enable input-remapper
sudo systemctl start input-remapper

# Add your user to the input group (may be needed)
sudo usermod -aG input $USER
```

**Note**: You may need to log out and back in after adding to the input group.

### Usage

1. **Launch Input Remapper**:
   ```bash
   input-remapper-control
   ```
   Or find "Input Remapper" in your applications menu.

2. **Configure Your Mouse**:
   - Select your Logitech G502 from the device list
   - Click on any button to remap it
   - Choose from:
     - Keyboard keys (e.g., `Ctrl+C`, `Alt+Tab`)
     - Mouse buttons (e.g., Left, Right, Middle)
     - Commands/scripts (e.g., `gnome-terminal`)
     - Macros (sequences of actions)

3. **Example Button Mappings**:
   - **Button 4** (Side button 1) → `Ctrl+C` (Copy)
   - **Button 5** (Side button 2) → `Ctrl+V` (Paste)
   - **Button 6** → `Super+Tab` (Window switcher)
   - **Button 7** → `gnome-terminal` (Open terminal)
   - **Button 8** → Custom macro

4. **Save and Apply**:
   - Click "Save" to save your configuration
   - The remapping will be active immediately
   - Settings persist across reboots

### Advanced Features

- **Macros**: Record sequences of key presses
- **Conditional Mapping**: Different mappings per application
- **Layers**: Switch between different button configurations
- **Autostart**: Automatically loads your configuration on boot

---

## Option 2: Piper + libratbag (Hardware-Level Configuration)

### Why Piper?
- ✅ **Hardware-level** configuration (settings stored in mouse)
- ✅ Works even when software isn't running
- ✅ Best for **Logitech gaming mice**
- ✅ Can configure **DPI, LED colors, polling rate**
- ✅ Official support for G502 series

### Installation

```bash
# Install libratbag (daemon) and Piper (GUI)
sudo apt update
sudo apt install piper libratbag2 ratbagd

# Start and enable the daemon
systemctl --user enable ratbagd
systemctl --user start ratbagd

# Verify your mouse is detected
ratbagctl list
```

### Usage

1. **Launch Piper**:
   ```bash
   piper
   ```
   Or find "Piper" in your applications menu.

2. **Configure Your Mouse**:
   - Your G502 should appear in the device list
   - Click on it to open the configuration window
   - Configure:
     - **Buttons**: Map each button to actions
     - **DPI**: Adjust sensitivity levels
     - **LED**: Change RGB lighting
     - **Profiles**: Create multiple profiles

3. **Button Mapping Options**:
   - Standard mouse buttons (Left, Right, Middle)
   - Keyboard keys
   - Special functions (DPI cycle, profile switch)
   - Disable button

4. **Save to Mouse**:
   - Click "Apply" to save settings to the mouse hardware
   - Settings persist even on other computers

### Check Device Support

```bash
# Check if your G502 is supported
ratbagctl list

# Get detailed info about your mouse
ratbagctl <device-name> info
```

**Note**: If your G502 isn't detected, it may need a device file. Check:
- [libratbag device files](https://github.com/libratbag/libratbag/tree/master/data/devices)
- You may need to create a device file for your specific model

---

## Option 3: Hybrid Approach (Best of Both Worlds)

Use **both** tools:
- **Piper** for hardware-level settings (DPI, LED, profiles)
- **Input Remapper** for software-level button remapping (macros, commands, app-specific)

This gives you maximum flexibility!

---

## Identifying Your Mouse Buttons

### Using `evtest` (Recommended)

```bash
# Install evtest
sudo apt install evtest

# Run evtest and select your mouse
sudo evtest

# Press each button and note the button numbers
# Example output:
# Event: time 1234567890.123456, type 1 (EV_KEY), code 272 (BTN_LEFT), value 1
# Button 272 = Left click
```

### Using `xev` (X11 only, won't work on Wayland)

```bash
# Install xev
sudo apt install x11-utils

# Run xev (only works on X11, not Wayland)
xev -event button
```

### Button Number Reference (Typical G502)

- **Button 1**: Left click
- **Button 2**: Middle click (scroll wheel)
- **Button 3**: Right click
- **Button 4**: Side button (back/thumb)
- **Button 5**: Side button (forward/thumb)
- **Button 6**: DPI shift (usually)
- **Button 7+**: Additional buttons (varies by model)

---

## Troubleshooting

### Input Remapper Not Working on Wayland

1. **Check service status**:
   ```bash
   sudo systemctl status input-remapper
   ```

2. **Check permissions**:
   ```bash
   groups  # Should include 'input'
   ```

3. **Restart service**:
   ```bash
   sudo systemctl restart input-remapper
   ```

### Piper Not Detecting Mouse

1. **Check ratbagd status**:
   ```bash
   systemctl --user status ratbagd
   ```

2. **Check device support**:
   ```bash
   ratbagctl list
   ```

3. **Check logs**:
   ```bash
   journalctl --user -u ratbagd -f
   ```

4. **Restart daemon**:
   ```bash
   systemctl --user restart ratbagd
   ```

### Buttons Not Responding

1. **Check if remapping is active**:
   - Input Remapper: Check if the service is running
   - Piper: Settings should be saved to mouse

2. **Test with evtest**:
   ```bash
   sudo evtest
   ```
   Verify buttons are being detected at hardware level

3. **Check for conflicts**:
   - Disable other input remapping tools
   - Check GNOME settings for mouse button assignments

---

## Advanced: Custom Scripts and Macros

### Example: Button to Run Script

In Input Remapper, you can map a button to run a custom script:

1. Create a script:
   ```bash
   #!/bin/bash
   # ~/scripts/mouse-button-action.sh
   notify-send "Mouse Button Pressed!"
   ```

2. Make it executable:
   ```bash
   chmod +x ~/scripts/mouse-button-action.sh
   ```

3. In Input Remapper, map button to:
   ```
   /home/mark/scripts/mouse-button-action.sh
   ```

### Example: Complex Macro

Create a macro that:
1. Opens terminal
2. Types a command
3. Presses Enter

In Input Remapper:
- Record macro
- Press: `Super+T` (open terminal)
- Type: `cd /opt/roxy && ls`
- Press: `Enter`
- Save macro
- Assign to mouse button

---

## Comparison: Input Remapper vs Piper

| Feature | Input Remapper | Piper |
|---------|---------------|-------|
| **Wayland Support** | ✅ Yes | ✅ Yes |
| **GUI** | ✅ Yes | ✅ Yes |
| **Hardware Storage** | ❌ No | ✅ Yes |
| **Macros** | ✅ Yes | ❌ No |
| **App-Specific Mapping** | ✅ Yes | ❌ No |
| **DPI Control** | ❌ No | ✅ Yes |
| **LED Control** | ❌ No | ✅ Yes |
| **Works Without Software** | ❌ No | ✅ Yes |
| **All Mice** | ✅ Yes | ❌ Gaming mice only |

---

## Recommended Setup

For your **Logitech G502 SE HERO** on **Wayland**:

1. **Install Input Remapper** (primary tool)
   - Best for general button remapping
   - Works reliably on Wayland
   - Easy to use GUI

2. **Install Piper** (optional, for hardware features)
   - Use for DPI profiles
   - Use for LED customization
   - Use for hardware-level button mapping (if needed)

3. **Use Input Remapper for**:
   - Mapping buttons to keyboard shortcuts
   - Creating macros
   - App-specific mappings
   - Running commands/scripts

4. **Use Piper for**:
   - DPI sensitivity levels
   - RGB LED colors
   - Hardware profiles

---

## Quick Start Commands

```bash
# Install everything
sudo apt update
sudo apt install input-remapper piper libratbag2 ratbagd evtest

# Start services
sudo systemctl enable --now input-remapper
systemctl --user enable --now ratbagd

# Launch configuration tools
input-remapper-control  # Input Remapper GUI
piper                    # Piper GUI

# Test your mouse buttons
sudo evtest
```

---

## Resources

- **Input Remapper**: https://github.com/sezanzeb/input-remapper
- **Piper**: https://github.com/libratbag/piper
- **libratbag**: https://github.com/libratbag/libratbag
- **Device Support**: https://github.com/libratbag/libratbag/tree/master/data/devices

---

## Next Steps

1. ✅ Install Input Remapper
2. ✅ Install Piper (optional)
3. ✅ Launch Input Remapper and configure your buttons
4. ✅ Test each button mapping
5. ✅ Create custom macros for your workflow
6. ✅ Set up app-specific mappings (if needed)

Enjoy your fully programmable mouse! 🎮









