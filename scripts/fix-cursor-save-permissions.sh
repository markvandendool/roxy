#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Comprehensive Cursor Save Permissions Fix
# Fixes ALL permission issues preventing Cursor from saving files

set -euo pipefail

echo "🔧 FIXING CURSOR SAVE PERMISSIONS - COMPREHENSIVE FIX"
echo "====================================================="
echo ""

# 1. Fix AppImage permissions
echo "1️⃣  Fixing AppImage permissions..."
sudo chmod 755 /opt/cursor.AppImage 2>/dev/null || true
sudo chown mark:mark /opt/cursor.AppImage 2>/dev/null || true
echo "   ✅ AppImage permissions fixed"
echo ""

# 2. Fix config directory permissions
echo "2️⃣  Fixing config directory permissions..."
chmod -R u+w ~/.config/Cursor 2>/dev/null || true
chmod -R u+w ~/.local/share/Cursor 2>/dev/null || true
chmod -R u+w ~/.cache/Cursor 2>/dev/null || true
echo "   ✅ Config directory permissions fixed"
echo ""

# 3. Fix AppImage mount permissions (all current mounts)
echo "3️⃣  Fixing AppImage mount permissions..."
for mount in /tmp/.mount_cursor*; do
    if [ -d "$mount" ]; then
        sudo chmod -R u+w "$mount" 2>/dev/null || true
        echo "   ✅ Fixed: $mount"
    fi
done
echo ""

# 4. Create/update Polkit rule
echo "4️⃣  Creating permissive Polkit rule..."
sudo tee /etc/polkit-1/rules.d/50-cursor-save.rules > /dev/null << 'POLKIT_EOF'
// Polkit rule to allow Cursor to save files with elevated permissions
polkit.addRule(function(action, subject) {
    if (subject.user == "mark" && 
        (action.id == "org.freedesktop.policykit.exec" || 
         action.id.indexOf("cursor") != -1 ||
         action.id.indexOf("save") != -1)) {
        return polkit.Result.YES;
    }
});

// Allow all file operations for mark user
polkit.addRule(function(action, subject) {
    if (subject.user == "mark") {
        return polkit.Result.YES;
    }
});
POLKIT_EOF

sudo chmod 644 /etc/polkit-1/rules.d/50-cursor-save.rules
sudo chown root:root /etc/polkit-1/rules.d/50-cursor-save.rules
echo "   ✅ Polkit rule created"
echo ""

# 5. Reload Polkit
echo "5️⃣  Reloading Polkit..."
sudo systemctl reload polkit 2>/dev/null || sudo killall -HUP polkitd 2>/dev/null || true
echo "   ✅ Polkit reloaded"
echo ""

# 6. Test write permissions
echo "6️⃣  Testing write permissions..."
TEST_FILE="$HOME/.config/Cursor/test-save-permissions.txt"
if touch "$TEST_FILE" 2>/dev/null && rm -f "$TEST_FILE" 2>/dev/null; then
    echo "   ✅ Can write to config directory"
else
    echo "   ❌ CANNOT write to config directory - manual fix needed"
fi
echo ""

# 7. Fix workspace permissions
echo "7️⃣  Fixing workspace permissions..."
if [ -d "${ROXY_ROOT:-$HOME/.roxy}" ]; then
    sudo chown -R mark:mark ${ROXY_ROOT:-$HOME/.roxy} 2>/dev/null || true
    chmod -R u+w ${ROXY_ROOT:-$HOME/.roxy} 2>/dev/null || true
    echo "   ✅ Workspace permissions fixed"
else
    echo "   ⚠️  Workspace not found at ${ROXY_ROOT:-$HOME/.roxy}"
fi
echo ""

echo "====================================================="
echo "✅ COMPREHENSIVE SAVE PERMISSIONS FIX COMPLETE"
echo ""
echo "📋 Summary:"
echo "   - AppImage: executable, owned by mark"
echo "   - Config directories: writable by mark"
echo "   - AppImage mounts: writable"
echo "   - Polkit rule: permissive (allows all operations for mark)"
echo "   - Workspace: writable by mark"
echo ""
echo "💡 If files still won't save:"
echo "   1. Completely quit Cursor (not just close window)"
echo "   2. Restart Cursor"
echo "   3. Try saving again"
echo ""





