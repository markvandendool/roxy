#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Fix Cursor AppImage permissions and save issues

echo "Fixing Cursor permissions..."

# Make AppImage executable
chmod +x /opt/cursor.AppImage

# Fix Cursor config directory permissions
chmod -R u+w ~/.config/Cursor 2>/dev/null

# Fix any existing mount points
for mount in /tmp/.mount_cursor*; do
    if [ -d "$mount" ]; then
        echo "Fixing permissions for $mount"
        sudo chmod -R u+x "$mount/usr/share/cursor/bin/cursor" 2>/dev/null || true
    fi
done

# Ensure user can write to home
chmod u+w ~ 2>/dev/null

echo "✅ Permissions fixed"
echo ""
echo "⚠️  If issues persist, try:"
echo "   1. Close Cursor completely"
echo "   2. Restart Cursor"
echo "   3. If still failing, run Cursor with: sudo /opt/cursor.AppImage"