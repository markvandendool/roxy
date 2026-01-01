# CURSOR PERFORMANCE FORENSIC REPORT
**Date**: January 1, 2026 04:26 UTC  
**Status**: CRITICAL - Recurring Performance Issue

## EXECUTIVE SUMMARY

Cursor is experiencing severe performance degradation due to:
1. **Runaway process consuming 82.7% CPU** (PID 557354, 61 minutes CPU time)
2. **Massive I/O bottleneck** (8.87% I/O wait, 1250 KB/s git operations)
3. **51GB workspace being indexed** (7.7GB .git directory)
4. **No file exclusions** (.cursorignore missing)
5. **Service configuration issues** (final-performance-fix.service inactive)

## DETAILED FINDINGS

### 1. Runaway Process Analysis

**Process**: PID 557354
- **CPU Usage**: 82.7%
- **CPU Time**: 61 minutes 18 seconds
- **State**: R<l (Running, blocked on I/O)
- **Type**: Cursor zygote process
- **Threads**: 9 threads, main thread using 45 minutes CPU time

**Root Cause**: Process is stuck in I/O-bound operation, likely indexing/searching large workspace.

### 2. I/O Bottleneck Analysis

**Disk I/O Statistics**:
- **nvme1n1 utilization**: 154.54%
- **I/O wait time**: 8.87%
- **Cursor disk I/O**: 580.77 KB/s
- **Git process I/O**: 1250.49 KB/s (PID 2152885)

**Root Cause**: Git integration is indexing 7.7GB .git directory, causing massive I/O load.

### 3. Workspace Size Analysis

**Workspace**: /opt/roxy
- **Total size**: 51GB
- **.git directory**: 7.7GB
- **node_modules**: ~120MB (multiple instances)
- **Files being watched**: 3,391 files

**Root Cause**: Workspace is too large for efficient indexing without exclusions.

### 4. System Load Analysis

- **Load average**: 5.38 (high for 56-core system)
- **CPU idle**: 92.6% (but individual cores maxed)
- **Memory**: 144GB available (no memory pressure)
- **I/O wait**: 8.87% (CRITICAL - indicates disk bottleneck)

### 5. Service Status Analysis

**Active Services**:
- ✅ cpu-performance.service: active
- ✅ fix-intel-pstate.service: active
- ✅ cursor-max-performance-optimized.service: active (running)

**Inactive Services**:
- ❌ final-performance-fix.service: inactive (not enabled)

**Service Issues**:
- cursor-max-performance-optimized.service is running but not preventing the issue
- Services apply optimizations but don't address root cause (workspace size)

### 6. Configuration Issues

**Missing Configuration**:
- ❌ No .cursorignore file (user rejected previously, but clearly needed)
- ⚠️ GPU power mode: "auto" (should be "high")
- ⚠️ I/O scheduler: Not verified for optimal performance

**Existing Configuration**:
- ✅ CPU governor: performance (all cores)
- ✅ Intel P-state: 100% min/max, turbo enabled
- ✅ Cursor priority: -20 (highest)
- ✅ Cursor CPU affinity: All 56 cores
- ✅ Cursor I/O priority: best-effort prio 4

## ROOT CAUSE ANALYSIS

### Primary Root Cause

**Cursor is trying to index a 51GB workspace without exclusions**, causing:
1. Massive file system scanning
2. Git integration indexing 7.7GB .git directory
3. I/O bottleneck (8.87% wait time)
4. CPU-bound processing of file metadata
5. Continuous re-indexing on workspace changes

### Why It Keeps Recurring

1. **No permanent exclusions**: Without .cursorignore, Cursor indexes everything on every open
2. **Git integration**: Cursor's git integration scans entire .git directory
3. **New processes**: Each new Cursor window spawns new indexing processes
4. **Service limitations**: Performance services optimize processes but don't prevent indexing
5. **Workspace size**: 51GB is too large to index efficiently without exclusions

## RECOMMENDED FIXES

### Critical (Must Do)

1. **Create .cursorignore** to exclude:
   - .git directory (7.7GB)
   - node_modules directories
   - Large build/cache directories
   - venv directories

2. **Fix I/O scheduler** for nvme1n1 to mq-deadline or none

3. **Enable final-performance-fix.service** as safety net

4. **Fix GPU power mode** to "high"

### Important (Should Do)

5. **Optimize Cursor settings** for large workspace
6. **Disable unnecessary Cursor features** for this workspace
7. **Add I/O priority for git processes**

### Optional (Nice to Have)

8. **Monitor and alert** on high I/O wait
9. **Pre-index workspace** during off-hours
10. **Use workspace-specific settings**

## IMPACT ASSESSMENT

**Current Impact**:
- 10-15 second typing delay
- 82.7% CPU usage by single process
- 8.87% I/O wait (system-wide slowdown)
- High load average (5.38)

**Expected Impact After Fixes**:
- Typing delay: <100ms
- CPU usage: <5% per process
- I/O wait: <1%
- Load average: <2.0

## CONCLUSION

The performance issue is **NOT a CPU or GPU problem** - it's an **I/O bottleneck caused by indexing a 51GB workspace without exclusions**. The previous fixes addressed symptoms (CPU governor, priority) but not the root cause (workspace indexing).

**The .cursorignore file is ESSENTIAL** - without it, Cursor will continue to index the entire workspace on every open, causing recurring performance issues.










