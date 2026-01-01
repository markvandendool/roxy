# Fix Click and Drag Highlighting Issue

## Quick Fixes Applied:

1. **Drag Threshold**: Set to 8 pixels (default)
2. **Primary Paste**: Enabled (middle-click paste)

## If Still Not Working:

### Method 1: Reset Mouse Settings
```bash
gsettings reset org.gnome.desktop.peripherals.mouse drag-threshold
gsettings reset org.gnome.desktop.peripherals.touchpad tap-to-click
```

### Method 2: Restart GNOME Shell
```bash
# Press Alt+F2, type 'r', press Enter
# OR
killall -SIGQUIT gnome-shell
```

### Method 3: Check for Conflicting Extensions
```bash
gnome-extensions list --enabled
# Disable extensions one by one to find the culprit
```

### Method 4: Reset Input Settings
```bash
gsettings reset-recursively org.gnome.desktop.peripherals.mouse
gsettings reset-recursively org.gnome.desktop.peripherals.touchpad
```

### Method 5: Check Accessibility Settings
```bash
gsettings get org.gnome.desktop.a11y.mouse click-type-window-areas
# Should be 'double'
```

## Common Causes:
- Extension conflicts
- GNOME Shell crash/recovery
- Input device settings
- Accessibility settings interfering

## Check System Errors:
```bash
journalctl -p err -b | tail -20
dmesg | grep -i error | tail -10
```
