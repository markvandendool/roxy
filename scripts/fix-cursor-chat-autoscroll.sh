#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Fix Cursor Chat Auto-Scroll Issue
# Adds all possible settings to enable auto-scroll in chat windows

set -euo pipefail

SETTINGS_FILE="$HOME/.config/Cursor/User/settings.json"
BACKUP_FILE="/tmp/cursor-settings-backup-$(date +%s).json"

echo "🔧 FIXING CURSOR CHAT AUTO-SCROLL"
echo "=================================="
echo ""

# Backup current settings
if [ -f "$SETTINGS_FILE" ]; then
    cp "$SETTINGS_FILE" "$BACKUP_FILE"
    echo "✅ Settings backed up to: $BACKUP_FILE"
else
    echo "⚠️  Settings file not found, creating new one..."
    mkdir -p "$(dirname "$SETTINGS_FILE")"
    echo "{}" > "$SETTINGS_FILE"
fi

# Read current settings
if [ -f "$SETTINGS_FILE" ]; then
    # Use Python to safely update JSON
    python3 << 'PYTHON_EOF'
import json
import sys
import os

settings_file = os.path.expanduser("~/.config/Cursor/User/settings.json")

try:
    with open(settings_file, 'r') as f:
        settings = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    settings = {}

# Add all possible chat auto-scroll settings
chat_scroll_settings = {
    "cursor.chat.autoScrollToBottom": True,
    "cursor.chat.scrollToLatest": True,
    "workbench.chat.autoScroll": True,
    "workbench.chat.autoScrollToBottom": True,
    "chat.autoScroll": True,
    "chat.autoScrollToBottom": True,
    "editor.scrollToBottomOnChat": True,
    "cursor.composer.autoScroll": True,
    "cursor.composer.autoScrollToBottom": True,
    "workbench.editor.autoScroll": True,
}

# Merge settings
settings.update(chat_scroll_settings)

# Write back
with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print("✅ Added chat auto-scroll settings:")
for key in sorted(chat_scroll_settings.keys()):
    print(f"   - {key}: {chat_scroll_settings[key]}")
PYTHON_EOF

    echo ""
    echo "✅ Settings updated successfully!"
    echo ""
    echo "📋 Added settings:"
    echo "   - cursor.chat.autoScrollToBottom: true"
    echo "   - cursor.chat.scrollToLatest: true"
    echo "   - workbench.chat.autoScroll: true"
    echo "   - workbench.chat.autoScrollToBottom: true"
    echo "   - chat.autoScroll: true"
    echo "   - chat.autoScrollToBottom: true"
    echo "   - editor.scrollToBottomOnChat: true"
    echo "   - cursor.composer.autoScroll: true"
    echo "   - cursor.composer.autoScrollToBottom: true"
    echo "   - workbench.editor.autoScroll: true"
    echo ""
    echo "🎯 NEXT STEPS:"
    echo "   1. Completely restart Cursor (killall cursor)"
    echo "   2. Launch Cursor Ultimate"
    echo "   3. Switch between chat windows"
    echo "   4. Verify auto-scroll works"
    echo ""
else
    echo "❌ Could not access settings file"
    exit 1
fi


















