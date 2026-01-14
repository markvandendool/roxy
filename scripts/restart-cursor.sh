#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Restart Cursor completely to apply permission fixes

echo "🔄 Restarting Cursor..."
killall cursor 2>/dev/null || true
killall cursor.AppImage 2>/dev/null || true
sleep 3
${ROXY_ROOT:-$HOME/.roxy}/scripts/cursor-ultimate.sh &
echo "✅ Cursor restarted"