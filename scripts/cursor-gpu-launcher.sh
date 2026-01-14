#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Cursor GPU-Accelerated Launcher
# Forces RX 6900 XT (card2) and enables all GPU acceleration features

# Set GPU to RX 6900 XT (card2)
export DRI_PRIME=2
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json
export AMD_VULKAN_ICD=RADV

# Force GPU acceleration
export LIBGL_ALWAYS_SOFTWARE=0
export GALLIUM_DRIVER=radeonsi

# Electron/Chromium GPU acceleration flags
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

# CPU/Threading optimization
CPU_FLAGS=(
    "--enable-features=ParallelDownloading"
    "--js-flags=--max-old-space-size=16384"
)

# Performance flags
PERF_FLAGS=(
    "--disable-background-networking"
    "--disable-background-timer-throttling"
    "--disable-renderer-backgrounding"
    "--disable-backgrounding-occluded-windows"
    "--disable-ipc-flooding-protection"
)

# Combine all flags
ALL_FLAGS=("${GPU_FLAGS[@]}" "${CPU_FLAGS[@]}" "${PERF_FLAGS[@]}")

# Launch Cursor with all optimizations
exec /opt/cursor.AppImage "${ALL_FLAGS[@]}" "$@"
