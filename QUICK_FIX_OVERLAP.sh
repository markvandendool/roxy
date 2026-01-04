#!/bin/bash
# Quick fix for taskbar stats overlapping date

echo "🔧 Fixing taskbar stats size..."

# If Vitals is installed
if gnome-extensions list | grep -q vitals; then
    echo "Configuring Vitals extension..."
    dconf write /org/gnome/shell/extensions/vitals/font-size "uint32 9" 2>/dev/null
    dconf write /org/gnome/shell/extensions/vitals/compact-mode true 2>/dev/null
    echo "✅ Vitals: font-size 9, compact mode enabled"
fi

# If System Monitor is enabled
if gnome-extensions list --enabled | grep -q system-monitor; then
    echo "System Monitor is enabled - configure via Extension Manager"
    echo "Open: gnome-extensions-app"
    echo "Find System Monitor, click gear, reduce font size"
fi

echo ""
echo "✅ Done! Restart GNOME Shell if needed: Alt+F2, 'r', Enter"
