#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Force GNOME/mutter to use RX 6900 XT

# Method 1: Set environment before starting GNOME
export GBM_BACKEND=radeonsi
export __GLX_VENDOR_LIBRARY_NAME=mesa

# Method 2: Force DRM device
export WLR_DRM_DEVICES=/dev/dri/card2

# Method 3: DRI_PRIME for compatibility
export DRI_PRIME=1

# Method 4: Mesa configuration
export MESA_LOADER_DRIVER_OVERRIDE=radeonsi

# For GNOME, we need to set this in the session
# Add to ~/.config/environment or /etc/environment.d/
echo "To apply to GNOME session, add these to:"
echo "  ~/.config/environment.d/90-gpu.conf"
echo "  Or: /etc/environment.d/90-wayland-gpu.conf (already done)"