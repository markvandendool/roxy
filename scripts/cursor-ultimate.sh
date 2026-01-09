#!/bin/bash
# ============================================================================
# CURSOR ULTIMATE LAUNCHER v2.0 - MAXIMUM PERFORMANCE
# ============================================================================
# Optimized for: Intel Xeon W-3275 (56 threads) + AMD RX 6900 XT + 157GB RAM
# ============================================================================

# ============================================
# AMD RX 6900 XT GPU OPTIMIZATION
# ============================================
export DRI_PRIME=1  # Use discrete GPU
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json
export AMD_VULKAN_ICD=RADV
export RADV_PERFTEST=nggc,aco,sam,rt,gpl  # Enable AMD performance features
export mesa_glthread=true  # Multi-threaded OpenGL
export LIBGL_ALWAYS_SOFTWARE=0
export LIBGL_DRI3_DISABLE=0
export GALLIUM_DRIVER=radeonsi
export MESA_GL_VERSION_OVERRIDE=4.6
export __GL_THREADED_OPTIMIZATIONS=1
export __GL_SYNC_TO_VBLANK=0

# ============================================
# INTEL XEON W-3275 CPU OPTIMIZATION (56 threads)
# ============================================
export OMP_NUM_THREADS=56
export MKL_NUM_THREADS=56
export NUMEXPR_NUM_THREADS=56
export OMP_SCHEDULE=dynamic
export OMP_PROC_BIND=spread
export UV_THREADPOOL_SIZE=56

# ============================================
# ELECTRON/CHROMIUM OPTIMIZATION FLAGS
# ============================================
GPU_FLAGS=(
    "--enable-gpu-rasterization"
    "--enable-oop-rasterization"
    "--enable-zero-copy"
    "--enable-native-gpu-memory-buffers"
    "--use-angle=default"  # Use ANGLE default backend
    "--enable-features=Vulkan,UseSkiaRenderer,VaapiVideoDecoder,VaapiVideoEncoder"
    "--use-vulkan"
    "--disable-gpu-vsync"
    "--ignore-gpu-blocklist"
    "--num-raster-threads=16"  # Increased for 56 cores
    "--enable-accelerated-2d-canvas"
    "--enable-accelerated-video-decode"
)

CPU_FLAGS=(
    "--renderer-process-limit=8"
    "--js-flags=--max-old-space-size=32768 --expose-gc"  # 32GB heap (no comma!)
    "--disk-cache-size=8589934592"  # 8GB disk cache
    "--enable-parallel-downloading"
)

# ============================================
# PERFORMANCE & QUALITY FLAGS
# ============================================
PERF_FLAGS=(
    "--disable-background-networking"
    "--disable-background-timer-throttling"
    "--disable-renderer-backgrounding"
    "--disable-backgrounding-occluded-windows"
    "--disable-ipc-flooding-protection"
    "--disable-frame-rate-limit"
    "--disable-breakpad"
    "--disable-component-update"
    "--force-high-performance-gpu"
    "--enable-smooth-scrolling"
    "--max-decoded-image-size-mb=2048"
)

# ============================================
# PERMISSIONS & PRE-LAUNCH
# ============================================
chmod +x /opt/cursor.AppImage 2>/dev/null || true
chmod -R u+w ~/.config/Cursor ~/.cache/Cursor 2>/dev/null || true

# Fix AppImage mounts
for m in /tmp/.mount_cursor*; do
    [ -d "$m" ] && mountpoint -q "$m" 2>/dev/null && chmod -R u+w "$m" 2>/dev/null || true
done

# ============================================
# COMBINE ALL FLAGS
# ============================================
ALL_FLAGS=("${GPU_FLAGS[@]}" "${CPU_FLAGS[@]}" "${PERF_FLAGS[@]}")

# ============================================
# LAUNCH CURSOR ULTIMATE v2.0
# ============================================
echo "🚀 Cursor Ultimate v2.0 - Maximum Performance"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💻 Intel Xeon W-3275 (56 threads @ 2.5-4.6GHz)"
echo "🎮 AMD Radeon RX 6900 XT (OpenGL 4.6 + Vulkan)"
echo "🧠 157GB RAM | 8GB Cache | 32GB V8 Heap"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚡ Optimizations: GPU Accel | 56-Core | Zero-Copy | OOP"
echo ""

exec /opt/cursor.AppImage "${ALL_FLAGS[@]}" "$@" 2>&1








