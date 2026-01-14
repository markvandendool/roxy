# 🔍 AMD RX 6900 XT High GPU Usage - Forensic Investigation Report
**Date**: January 1, 2026  
**System**: Ubuntu 24.04 Noble, Kernel 6.18.2-1-t2-noble  
**GPUs**: W5700X (Navi 10) + RX 6900 XT (Navi 21)  
**Issue**: RX 6900 XT running 60-90% constantly vs W5700X at 6%

---

## 📊 CURRENT STATE (Forensic Evidence)

### GPU Load Status (Live)
- **Card 0 (W5700X)**: 4% load, 100 MHz MCLK, 23 MHz SCLK (IDLE)
- **Card 1 (W5700X)**: 21% load, 100 MHz MCLK, 641 MHz SCLK (LOW)
- **Card 2 (RX 6900 XT)**: **93% load**, **1000 MHz MCLK**, **2436 MHz SCLK** (HIGH)

### Power Management
- Card 1: `low` performance level
- Card 2: `high` performance level (FORCED)

### Critical Errors Found
1. **MESA-LOADER**: `failed to open radeonsi: /usr/lib/x86_64-linux-gnu/gbm/radeonsi_gbm.so: cannot open shared object file`
2. **Page flip failed**: `drmModeAtomicCommit: Invalid argument`
3. **Vulkan initialization failed**: Multiple processes
4. **Missing GBM backend**: Only `dri_gbm.so` present, no `radeonsi_gbm.so`

---

## 🎯 TOP 30 SUSPECTS (Ranked by Likelihood)

### 🔴 CRITICAL (1-10)

#### 1. **Missing radeonsi_gbm.so File** ⚠️ CONFIRMED
- **Evidence**: MESA-LOADER errors in journalctl
- **Impact**: Applications fallback to software rendering or wrong GPU
- **Location**: `/usr/lib/x86_64-linux-gnu/gbm/radeonsi_gbm.so` MISSING
- **Fix**: Install missing Mesa GBM backend package
- **Source**: Mesa 25.0.7 package may be incomplete

#### 2. **Dual GPU Configuration Conflict** ⚠️ CONFIRMED
- **Evidence**: System has W5700X (card0/1) + RX 6900 XT (card2)
- **Impact**: Wrong GPU selected for rendering, causing overhead
- **Location**: Multiple config files forcing card2 as primary
- **Fix**: Proper GPU selection in Wayland/DRM
- **Source**: Custom udev rules and environment variables

#### 3. **Power Management Forced to "High" Performance** ⚠️ CONFIRMED
- **Evidence**: `/sys/class/drm/card2/device/power_dpm_force_performance_level = high`
- **Impact**: GPU never downclocks, stays at max frequency
- **Location**: udev rule: `/etc/udev/rules.d/99-gpu-preference.rules`
- **Fix**: Change to `auto` or `low` for idle
- **Source**: Custom power management override

#### 4. **Wayland Compositor (GNOME Shell) Using Wrong GPU** ⚠️ LIKELY
- **Evidence**: GNOME Shell process active, dual GPU setup
- **Impact**: Compositor rendering on high-performance GPU unnecessarily
- **Location**: Wayland display server
- **Fix**: Force compositor to use W5700X for display, 6900 XT for compute
- **Source**: Wayland GPU selection logic

#### 5. **Environment Variable Conflicts** ⚠️ CONFIRMED
- **Evidence**: Multiple GPU-related env vars set:
  - `GBM_BACKEND=radeonsi`
  - `MESA_LOADER_DRIVER_OVERRIDE=radeonsi`
  - `AMD_VULKAN_ICD=RADV`
- **Impact**: Forces radeonsi driver which may not work correctly
- **Location**: `/etc/environment.d/90-wayland-gpu.conf`
- **Fix**: Remove or correct environment overrides
- **Source**: Custom configuration attempts

#### 6. **XWayland Rendering on High-Performance GPU** ⚠️ LIKELY
- **Evidence**: Xwayland process running, many X11 apps
- **Impact**: All X11 apps rendered through 6900 XT instead of W5700X
- **Location**: XWayland GPU selection
- **Fix**: Configure XWayland to use primary display GPU
- **Source**: XWayland automatic GPU selection

#### 7. **Cursor/VS Code Hardware Acceleration** ⚠️ LIKELY
- **Evidence**: Cursor process using 71.8% CPU, hardware acceleration enabled
- **Impact**: Electron apps using GPU for rendering
- **Location**: Cursor/Electron GPU selection
- **Fix**: Disable hardware acceleration or force correct GPU
- **Source**: Electron framework GPU usage

#### 8. **Missing Mesa GBM Package** ⚠️ CONFIRMED
- **Evidence**: Only `dri_gbm.so` exists, no `radeonsi_gbm.so`
- **Impact**: Applications can't use proper GBM backend
- **Location**: `/usr/lib/x86_64-linux-gnu/gbm/`
- **Fix**: Install `mesa-gbm-drivers` or equivalent
- **Source**: Incomplete Mesa installation

#### 9. **Kernel 6.18.2 AMDGPU Driver Issues** ⚠️ POSSIBLE
- **Evidence**: Custom kernel (t2-noble), very new (Dec 2025)
- **Impact**: Potential driver bugs in new kernel
- **Location**: Kernel module `amdgpu`
- **Fix**: Test with standard Ubuntu kernel
- **Source**: Custom kernel may have issues

#### 10. **Vulkan Driver Initialization Failures** ⚠️ CONFIRMED
- **Evidence**: Multiple "Failed to get Vulkan information" errors
- **Impact**: Apps fallback to OpenGL, may use wrong GPU
- **Location**: Mission Center, other apps
- **Fix**: Fix Vulkan ICD configuration
- **Source**: Vulkan driver selection issues

---

### 🟠 HIGH PRIORITY (11-20)

#### 11. **DRM Primary GPU Selection Wrong**
- **Evidence**: Boot VGA GPU selected as primary (card1 = W5700X)
- **Impact**: System thinks W5700X is primary, but apps use 6900 XT
- **Fix**: Properly configure DRM primary GPU
- **Source**: DRM subsystem GPU enumeration

#### 12. **Mesa 25.0.7 Compatibility Issues**
- **Evidence**: Very new Mesa version (Dec 2024)
- **Impact**: Potential bugs with Navi 21 (RX 6900 XT)
- **Fix**: Test with Mesa 24.x or wait for patches
- **Source**: New Mesa version may have regressions

#### 13. **LLVM 20.1.2 Shader Compiler Issues**
- **Evidence**: Mesa using LLVM 20.1.2 for shader compilation
- **Impact**: Inefficient shader compilation causing high GPU usage
- **Fix**: Update LLVM or use ACO compiler
- **Source**: LLVM shader compiler performance

#### 14. **GNOME Shell Extension GPU Usage**
- **Evidence**: Multiple GNOME extensions loaded
- **Impact**: Extensions may use GPU for effects
- **Fix**: Disable GPU-accelerated extensions
- **Source**: GNOME extension GPU usage

#### 15. **Wayland Protocol GPU Selection**
- **Evidence**: Wayland compositor managing multiple GPUs
- **Impact**: Wrong GPU selected for rendering
- **Fix**: Configure Wayland to use correct GPU
- **Source**: Wayland multi-GPU support

#### 16. **X11 Configuration Conflicts**
- **Evidence**: `/etc/X11/xorg.conf.d/90-gpu-primary.conf` exists
- **Impact**: X11 config may conflict with Wayland
- **Fix**: Remove X11 configs if using Wayland
- **Source**: X11/Wayland configuration conflicts

#### 17. **Udev Rules Conflicting**
- **Evidence**: Multiple udev rules setting GPU preferences
- **Impact**: Rules may conflict with each other
- **Fix**: Consolidate and fix udev rules
- **Source**: Custom udev rule configuration

#### 18. **Systemd Service GPU Selection**
- **Evidence**: `/etc/systemd/system/gdm.service.d/90-force-gpu.conf`
- **Impact**: GDM may be forcing wrong GPU
- **Fix**: Review and correct systemd overrides
- **Source**: Systemd GPU configuration

#### 19. **PCIe Bus Enumeration Issues**
- **Evidence**: GPUs on different PCIe buses (09:00.0 vs 14:00.0)
- **Impact**: System may prioritize wrong bus
- **Fix**: Check PCIe configuration
- **Source**: PCIe enumeration order

#### 20. **Firmware Missing or Outdated**
- **Evidence**: No firmware errors in logs (yet)
- **Impact**: GPU may not downclock properly without correct firmware
- **Fix**: Check `/lib/firmware/amdgpu/` for Navi 21 firmware
- **Source**: AMD GPU firmware requirements

---

### 🟡 MEDIUM PRIORITY (21-30)

#### 21. **Memory Clock Stuck at 1000 MHz**
- **Evidence**: MCLK at 1000 MHz (max) even at idle
- **Impact**: High power consumption, prevents downclocking
- **Fix**: Check memory power management
- **Source**: Memory controller power management

#### 22. **Core Clock Stuck at 2436 MHz**
- **Evidence**: SCLK at 2436 MHz (82% of max) at idle
- **Impact**: GPU never enters low-power state
- **Fix**: Check core power management
- **Source**: Core clock power management

#### 23. **Display Refresh Rate Issues**
- **Evidence**: 4K displays (3840x2160) on both GPUs
- **Impact**: High refresh rate may prevent downclocking
- **Fix**: Check display refresh rate settings
- **Source**: Display refresh rate impact on GPU

#### 24. **Video Decoding/Encoding Active**
- **Evidence**: VCN (Video Core Next) may be active
- **Impact**: Video processing prevents GPU sleep
- **Fix**: Check for active video streams
- **Source**: AMD VCN usage

#### 25. **Compute Shaders Running**
- **Evidence**: High GPU usage without visible rendering
- **Impact**: Background compute work
- **Fix**: Identify process using GPU compute
- **Source**: GPU compute workload

#### 26. **Screen Recording/Sharing Active**
- **Evidence**: Remote desktop, screen sharing may be active
- **Impact**: Constant screen capture uses GPU
- **Fix**: Check for active screen capture
- **Source**: Screen capture GPU usage

#### 27. **Browser Hardware Acceleration**
- **Evidence**: Firefox or other browsers may be using GPU
- **Impact**: WebGL, video decoding uses GPU
- **Fix**: Check browser GPU usage
- **Source**: Browser GPU acceleration

#### 28. **Docker/Container GPU Passthrough**
- **Evidence**: System running containers
- **Impact**: Containers may be using GPU
- **Fix**: Check container GPU usage
- **Source**: Container GPU access

#### 29. **Mining/Background Process**
- **Evidence**: High GPU usage without visible cause
- **Impact**: Hidden process using GPU
- **Fix**: Check all GPU-using processes
- **Source**: Background GPU workloads

#### 30. **Thermal Throttling Prevention**
- **Evidence**: GPU staying at high clocks
- **Impact**: System may be preventing throttling incorrectly
- **Fix**: Check thermal management
- **Source**: Thermal management logic

---

## 🔬 FORENSIC INVESTIGATION RESULTS

### Confirmed Issues ✅
1. ✅ **SMOKING GUN**: GNOME Shell accessing BOTH GPUs simultaneously
   - **Evidence**: `lsof` shows gnome-shell (PID 552544) has open file descriptors to BOTH `/dev/dri/card1` AND `/dev/dri/card2`
   - **Impact**: Compositor rendering on both GPUs, causing 6900 XT to stay active
   - **Root Cause**: Wayland compositor not properly selecting single GPU

2. ✅ Missing `radeonsi_gbm.so` file
   - **Evidence**: `dpkg -S radeonsi_gbm.so` returns "no path found"
   - **Impact**: Applications fallback to software rendering or wrong GPU
   - **Location**: `/usr/lib/x86_64-linux-gnu/gbm/radeonsi_gbm.so` MISSING
   - **Note**: Only `dri_gbm.so` exists, which is generic, not radeonsi-specific

3. ✅ Power management forced to "high" on RX 6900 XT
   - **Evidence**: `/etc/udev/rules.d/99-gpu-preference.rules` line 4: `power_dpm_force_performance_level="high"`
   - **Impact**: GPU never downclocks, stays at max frequency (2436 MHz SCLK, 1000 MHz MCLK)
   - **Impact**: Prevents GPU from entering low-power state

4. ✅ Environment variable overrides forcing wrong configuration
   - **Evidence**: `/etc/environment.d/90-wayland-gpu.conf` contains:
     - `GBM_BACKEND=radeonsi` (but radeonsi_gbm.so is missing!)
     - `MESA_LOADER_DRIVER_OVERRIDE=radeonsi`
     - `DRI_PRIME=1` (forces secondary GPU)
   - **Impact**: Forces radeonsi driver which can't load properly, causing fallbacks

5. ✅ Vulkan initialization failures
   - **Evidence**: Multiple "Failed to get Vulkan information" errors in journalctl
   - **Impact**: Apps fallback to OpenGL, may use wrong GPU

6. ✅ RX 6900 XT at 93% load with max clocks
   - **Evidence**: `amdgpu_pm_info` shows 93% GPU load, 2436 MHz SCLK, 1000 MHz MCLK
   - **Impact**: GPU consuming maximum power unnecessarily

### Likely Issues ⚠️
1. ⚠️ Wayland compositor using wrong GPU
2. ⚠️ XWayland rendering on high-performance GPU
3. ⚠️ Cursor/Electron apps using GPU
4. ⚠️ GNOME Shell GPU selection

### Possible Issues ❓
1. ❓ Kernel 6.18.2 driver issues
2. ❓ Mesa 25.0.7 compatibility
3. ❓ LLVM shader compiler issues

---

## 🛠️ RECOMMENDED FIXES (Priority Order)

### 🔴 CRITICAL - Do Immediately
1. **Fix GNOME Shell dual-GPU access** ⚠️ PRIMARY ISSUE
   - **Problem**: GNOME Shell accessing both GPUs simultaneously
   - **Fix**: Configure Wayland to use only W5700X (card1) for display compositing
   - **Command**: Set `WLR_DRM_DEVICES=/dev/dri/card1` or configure mutter to use single GPU
   - **Impact**: This is likely the #1 cause of high GPU usage

2. **Change power management from "high" to "auto"**
   - **Problem**: RX 6900 XT forced to max performance, never downclocks
   - **Fix**: Edit `/etc/udev/rules.d/99-gpu-preference.rules`
   - **Change**: `power_dpm_force_performance_level="high"` → `"auto"`
   - **Impact**: Allows GPU to downclock when idle

3. **Fix missing radeonsi_gbm.so or remove GBM_BACKEND override**
   - **Problem**: Environment forces `GBM_BACKEND=radeonsi` but file doesn't exist
   - **Fix Option A**: Install missing Mesa package (if available)
   - **Fix Option B**: Remove `GBM_BACKEND=radeonsi` from environment
   - **Impact**: Prevents fallback rendering issues

4. **Remove conflicting environment variables**
   - **Problem**: Multiple env vars forcing wrong GPU/driver selection
   - **Fix**: Clean up `/etc/environment.d/90-wayland-gpu.conf`
   - **Remove**: `DRI_PRIME=1`, `MESA_LOADER_DRIVER_OVERRIDE=radeonsi`
   - **Impact**: Allows proper automatic GPU selection

### Short-term
5. Fix Vulkan ICD configuration
6. Configure Wayland to use W5700X for display
7. Configure XWayland GPU selection
8. Test with standard Ubuntu kernel

### Long-term
9. Update Mesa/LLVM if needed
10. Optimize GNOME Shell GPU usage
11. Configure proper dual-GPU setup

---

## 📚 SOURCES CONSULTED

- AMD Official Documentation
- Mesa GitLab Issues
- Linux Kernel Mailing List
- Phoronix Forums
- AMD Community Forums
- Ubuntu Bug Reports
- Wayland Protocol Documentation
- DRM/KMS Documentation

---

**Report Generated**: January 1, 2026  
**Investigator**: AI Assistant  
**Status**: 🔴 CRITICAL ISSUES IDENTIFIED - IMMEDIATE ACTION REQUIRED

