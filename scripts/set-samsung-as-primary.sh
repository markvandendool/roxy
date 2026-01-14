#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
#
# Set Samsung (DP-9, center monitor) as primary display
# Works on both X11 and Wayland
#

echo "🖥️  Setting Samsung (DP-9, center) as Primary Display..."
echo ""

# Check if we're on Wayland or X11
if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
    echo "✅ Detected Wayland session"
    echo ""
    echo "On Wayland, use GNOME Settings to set primary:"
    echo "   1. Open: gnome-control-center display"
    echo "   2. Click the ⭐ star icon on the Samsung (center) monitor"
    echo "   3. Drag displays to arrange if needed"
    echo ""
    echo "OR use this command to open Display Settings:"
    echo "   gnome-control-center display"
    echo ""
    
    # Try to open Display Settings automatically
    read -p "Open Display Settings now? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        gnome-control-center display &
        echo "✅ Opened Display Settings"
        echo "   Click the ⭐ star on Samsung (center) monitor"
    fi
else
    echo "✅ Detected X11 session"
    echo ""
    echo "Setting DP-9 (Samsung, center) as primary via xrandr..."
    
    # Set DP-9 as primary
    xrandr --output DP-9 --primary
    
    if [ $? -eq 0 ]; then
        echo "✅ Successfully set DP-9 as primary display"
        echo ""
        echo "Current configuration:"
        xrandr --listmonitors 2>/dev/null
    else
        echo "❌ Failed to set primary display"
        exit 1
    fi
fi

echo ""
echo "📐 Display Arrangement:"
echo "   Left:   DP-8"
echo "   Center: DP-9 (Samsung) ← Should be primary/home"
echo "   Right:  HDMI-1"
echo ""
echo "✅ Done! The 'home stuff' should now be on Samsung (center)"









