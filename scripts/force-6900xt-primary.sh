#!/bin/bash
# Force RX 6900 XT (card2) as primary GPU for ALL applications

# Method 1: Set GBM backend (for GNOME/mutter)
export GBM_BACKEND=radeonsi
export __GLX_VENDOR_LIBRARY_NAME=mesa

# Method 2: Force DRM device (for wlroots compositors)
export WLR_DRM_DEVICES=/dev/dri/card2

# Method 3: DRI_PRIME for XWayland apps
export DRI_PRIME=1

# Method 4: Mesa environment (for all Mesa-based apps)
export MESA_LOADER_DRIVER_OVERRIDE=radeonsi
export MESA_GL_VERSION_OVERRIDE=4.6

# Method 5: Force specific GPU via AMDGPU
# This tells Mesa to prefer card2
export AMD_VULKAN_ICD=RADV

echo "✅ RX 6900 XT forced as primary GPU"
echo "   GBM_BACKEND=$GBM_BACKEND"
echo "   WLR_DRM_DEVICES=$WLR_DRM_DEVICES"
echo "   DRI_PRIME=$DRI_PRIME"
