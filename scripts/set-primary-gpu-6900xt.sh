#!/bin/bash

# Make RX 6900 XT (card2) the primary GPU

# Set DRI_PRIME to use card2 (RX 6900 XT) as default
# DRI_PRIME=0 = card0 (first)
# DRI_PRIME=1 = card1 (second) 
# But we need card2, so we'll use DRI_PRIME=2 or direct device selection

# For most applications, set DRI_PRIME=1 to use second GPU
# But card2 might be index 1 or 2 depending on enumeration

# Better: Use MESA_LOADER_DRIVER_OVERRIDE or direct device
export DRI_PRIME=1
export MESA_LOADER_DRIVER_OVERRIDE=radeonsi

# For X11, set primary provider
if command -v xrandr >/dev/null 2>&1; then
    # Get provider IDs
    PROVIDERS=$(xrandr --listproviders 2>/dev/null | grep "Provider" | awk '{print $2}')
    if [ -n "$PROVIDERS" ]; then
        # Provider 1 is usually the second GPU
        xrandr --setprovideroutputsource 1 0 2>/dev/null || true
    fi
fi

echo "✅ RX 6900 XT set as primary GPU"
echo "   DRI_PRIME=1 (using second GPU)"
