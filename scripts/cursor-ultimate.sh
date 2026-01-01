#!/bin/bash
# Cursor Ultimate Launcher - MAXIMUM PERFORMANCE
# GPU Acceleration + CPU Optimization + Hyperthreading + Permissions Fix

# ============================================
# GPU ACCELERATION (RX 6900 XT)
# ============================================
export DRI_PRIME=2  # Force RX 6900 XT (card2)
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json
export AMD_VULKAN_ICD=RADV
export LIBGL_ALWAYS_SOFTWARE=0
export GALLIUM_DRIVER=radeonsi

# ============================================
# CPU & HYPERTHREADING OPTIMIZATION
# ============================================
# Ensure all 56 cores (28 physical + 28 HT) are available
export OMP_NUM_THREADS=56
export MKL_NUM_THREADS=56
export NUMEXPR_NUM_THREADS=56

# ============================================
# ELECTRON/CHROMIUM GPU FLAGS
# ============================================
GPU_FLAGS=(
    "--enable-gpu"
    "--enable-gpu-rasterization"
    "--enable-zero-copy"
    "--use-gl=desktop"
    "--enable-features=VaapiVideoDecoder,VaapiVideoEncoder,UseSkiaRenderer"
    "--disable-gpu-vsync"
    "--enable-hardware-acceleration"
    "--ignore-gpu-blacklist"
    "--num-raster-threads=8"
    "--enable-oop-rasterization"
)

# ============================================
# CPU/THREADING OPTIMIZATION FLAGS
# ============================================
CPU_FLAGS=(
    "--enable-features=ParallelDownloading"
    "--js-flags=--max-old-space-size=16384"
)

# ============================================
# PERFORMANCE FLAGS
# ============================================
PERF_FLAGS=(
    "--disable-background-networking"
    "--disable-background-timer-throttling"
    "--disable-renderer-backgrounding"
    "--disable-backgrounding-occluded-windows"
    "--disable-ipc-flooding-protection"
)

# ============================================
# PERMISSIONS FIX
# ============================================
# Ensure AppImage is executable
chmod +x /opt/cursor.AppImage 2>/dev/null || true

# Fix config directory permissions
chmod -R u+w ~/.config/Cursor 2>/dev/null || true

# ============================================
# COMBINE ALL FLAGS
# ============================================
ALL_FLAGS=("${GPU_FLAGS[@]}" "${CPU_FLAGS[@]}" "${PERF_FLAGS[@]}")

# ============================================
# LAUNCH CURSOR WITH ALL OPTIMIZATIONS
# ============================================
exec /opt/cursor.AppImage "${ALL_FLAGS[@]}" "$@"







