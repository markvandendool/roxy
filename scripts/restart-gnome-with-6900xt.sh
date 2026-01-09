#!/bin/bash
# Restart GNOME to apply RX 6900 XT configuration

echo "🔄 Restarting GNOME to apply GPU configuration..."
echo "⚠️  This will restart your session (you'll stay logged in)"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    killall -SIGQUIT gnome-shell
    echo "✅ GNOME restarting..."
    echo "   Wait a few seconds for it to come back"
    echo "   Then verify: glxinfo | grep 'OpenGL renderer'"
else
    echo "Cancelled"
fi
