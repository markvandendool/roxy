#!/bin/bash
# Quick script to set Samsung (central) as primary
# Usage: ./set-samsung-primary.sh OUTPUT_NAME
# Example: ./set-samsung-primary.sh DP-8

if [ -z "$1" ]; then
    echo "❌ Please specify output name"
    echo ""
    echo "Available outputs:"
    xrandr 2>/dev/null | grep " connected" | awk '{print "   "$1}'
    echo ""
    echo "Usage: $0 OUTPUT_NAME"
    echo "Example: $0 DP-8"
    exit 1
fi

OUTPUT="$1"

# Verify output exists and is connected
if ! xrandr 2>/dev/null | grep -q "^$OUTPUT connected"; then
    echo "❌ Output '$OUTPUT' not found or not connected"
    echo ""
    echo "Available outputs:"
    xrandr 2>/dev/null | grep " connected" | awk '{print "   "$1}'
    exit 1
fi

# Set as primary
xrandr --output "$OUTPUT" --primary

if [ $? -eq 0 ]; then
    echo "✅ Set $OUTPUT as primary display"
    echo ""
    echo "Current arrangement:"
    xrandr --listmonitors 2>/dev/null
else
    echo "❌ Failed to set primary (might be on Wayland - use GNOME Settings instead)"
    echo ""
    echo "On Wayland, use:"
    echo "   gnome-control-center display"
    echo "   Then drag displays to arrange, and click the star on Samsung"
fi
