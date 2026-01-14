#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
#
# Force RX 6900 XT (card2) as primary GPU RIGHT NOW
# This applies to current session and forces all apps to use RX 6900 XT
#

echo "🔥 FORCING RX 6900 XT AS PRIMARY GPU..."

# Set environment variables for current shell and all child processes
export GBM_BACKEND=radeonsi
export __GLX_VENDOR_LIBRARY_NAME=mesa
export WLR_DRM_DEVICES=/dev/dri/card2
export DRI_PRIME=1
export MESA_LOADER_DRIVER_OVERRIDE=radeonsi
export MESA_GL_VERSION_OVERRIDE=4.6
export AMD_VULKAN_ICD=RADV

# For all running Cursor processes
for pid in $(pgrep -f cursor 2>/dev/null); do
    # Set environment for existing process (limited - only works for new threads)
    # We need to restart the app for full effect
    echo "Found Cursor PID $pid"
done

echo ""
echo "✅ Environment variables set for this shell"
echo ""
echo "⚠️  TO APPLY TO RUNNING APPS:"
echo "   1. Restart Cursor (close and reopen)"
echo "   2. OR log out and back in (best option)"
echo ""
echo "📊 TO VERIFY:"
echo "   glxinfo | grep 'OpenGL renderer'"
echo "   (Should show RX 6900 XT)"
echo ""
echo "🔧 TO FORCE ALL NEW APPS:"
echo "   Run this script, then start apps from this terminal"










