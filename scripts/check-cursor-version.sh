#!/bin/bash
# Check Cursor version and available settings

echo "🔍 CURSOR VERSION & SETTINGS CHECK"
echo "===================================="
echo ""

# Check Cursor version
echo "1️⃣  Cursor Version:"
if [ -f "/opt/cursor.AppImage" ]; then
    /opt/cursor.AppImage --version 2>&1 | head -5 || echo "   ⚠️  Could not get version"
else
    echo "   ⚠️  Cursor AppImage not found at /opt/cursor.AppImage"
fi
echo ""

# Check settings file
SETTINGS_FILE="$HOME/.config/Cursor/User/settings.json"
echo "2️⃣  Settings File:"
if [ -f "$SETTINGS_FILE" ]; then
    echo "   ✅ Found: $SETTINGS_FILE"
    echo "   Size: $(stat -c%s "$SETTINGS_FILE") bytes"
    echo ""
    echo "   Chat-related settings:"
    grep -iE "chat|scroll|auto" "$SETTINGS_FILE" | head -20 || echo "   No chat settings found"
else
    echo "   ❌ Not found: $SETTINGS_FILE"
fi
echo ""

# Check for available settings in Cursor
echo "3️⃣  Checking for Cursor settings directory:"
if [ -d "$HOME/.config/Cursor" ]; then
    echo "   ✅ Cursor config directory exists"
    find "$HOME/.config/Cursor" -name "*.json" -type f | head -10
else
    echo "   ❌ Cursor config directory not found"
fi
echo ""

# Check Cursor processes
echo "4️⃣  Cursor Processes:"
CURSOR_PIDS=$(pgrep -f cursor 2>/dev/null || true)
if [ -n "$CURSOR_PIDS" ]; then
    echo "   ✅ Cursor is running (PIDs: $CURSOR_PIDS)"
    ps aux | grep -E "$CURSOR_PIDS" | grep -v grep | head -3
else
    echo "   ⚠️  Cursor is not running"
fi
echo ""

echo "✅ Check complete!"














