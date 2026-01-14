#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
#
# Wayland GPU Configuration
# Forces RX 6900 XT (card2) as primary GPU for Wayland
#

# For wlroots-based compositors (Sway, Hyprland, etc.)
# WLR_DRM_DEVICES=/dev/dri/card2

# For GNOME (mutter)
# GBM_BACKEND=nvidia-drm  # For NVIDIA, but we have AMD
# For AMD, GNOME automatically detects both GPUs

# For KDE (kwin)
# KWIN_DRM_DEVICE=/dev/dri/card2

# System-wide environment (applies to all Wayland sessions)
# Add to /etc/environment.d/90-wayland-gpu.conf:
# WLR_DRM_DEVICES=/dev/dri/card2

echo "Wayland GPU configuration guide created"
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
echo "See ${ROXY_ROOT}/scripts/wayland-gpu-config.sh for details"