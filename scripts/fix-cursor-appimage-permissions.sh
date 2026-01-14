#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Fix Cursor AppImage mount permissions permanently

# Fix all existing mount points
for mount in /tmp/.mount_cursor*; do
    if [ -d "$mount" ]; then
        echo "Fixing permissions for $mount"
        # Fix the main binary
        sudo chmod +x "$mount/usr/share/cursor/bin/cursor" 2>/dev/null || true
        # Fix all binaries in the bin directory
        sudo find "$mount/usr/share/cursor/bin" -type f -exec chmod +x {} \; 2>/dev/null || true
        # Fix the AppRun script
        sudo chmod +x "$mount/AppRun" 2>/dev/null || true
    fi
done

# Also ensure the AppImage itself is executable
chmod +x /opt/cursor.AppImage 2>/dev/null || true

echo "✅ Cursor AppImage permissions fixed"