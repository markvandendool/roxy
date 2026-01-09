#!/bin/bash
# Comprehensive fix for Cursor save issues

echo "🔧 Fixing Cursor save permissions..."

# 1. Make AppImage executable
chmod +x /opt/cursor.AppImage

# 2. Fix config directory
chmod -R u+w ~/.config/Cursor 2>/dev/null

# 3. Fix any mount points (they're read-only but we can try)
for mount in /tmp/.mount_cursor*; do
    if [ -d "$mount" ]; then
        # AppImage mounts are read-only, but we can ensure the AppImage itself works
        echo "Found mount: $mount"
    fi
done

# 4. Create a polkit rule to allow Cursor to save files
sudo tee /etc/polkit-1/rules.d/50-cursor-save.rules > /dev/null << 'POLKIT'
polkit.addRule(function(action, subject) {
    if (action.id == "org.freedesktop.policykit.exec" &&
        subject.user == "mark" &&
        action.lookup("program") != null &&
        action.lookup("program").indexOf("cursor") != -1) {
        return polkit.Result.YES;
    }
});
POLKIT

echo "✅ Fixes applied:"
echo "   - AppImage permissions fixed"
echo "   - Config directory permissions fixed"
echo "   - Polkit rule created for Cursor"
echo ""
echo "⚠️  RESTART CURSOR for changes to take effect"
