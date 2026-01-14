#!/bin/bash
# Boot Persistence Verification Script
# Run this after reboot to verify all optimizations are applied

echo "🔍 VERIFYING PERMANENT OPTIMIZATIONS AFTER BOOT"
echo "================================================"
echo ""

PASSED=0
FAILED=0

# 1. Check GPU Power Mode
echo "1️⃣  GPU Power Mode..."
GPU_MODE=$(cat /sys/class/drm/card*/device/power_dpm_force_performance_level 2>/dev/null | head -1)
if [ "$GPU_MODE" = "high" ]; then
    echo "   ✅ GPU power mode: HIGH"
    PASSED=$((PASSED + 1))
else
    echo "   ❌ GPU power mode: $GPU_MODE (expected: high)"
    FAILED=$((FAILED + 1))
fi

# 2. Check CPU Governor
echo "2️⃣  CPU Governor..."
CPU_GOV=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null)
if [ "$CPU_GOV" = "performance" ]; then
    echo "   ✅ CPU governor: PERFORMANCE"
    PASSED=$((PASSED + 1))
else
    echo "   ❌ CPU governor: $CPU_GOV (expected: performance)"
    FAILED=$((FAILED + 1))
fi

# 3. Check I/O Scheduler
echo "3️⃣  I/O Scheduler..."
IO_SCHED=$(cat /sys/block/nvme*/queue/scheduler 2>/dev/null | grep -o '\[mq-deadline\]' | head -1)
if [ -n "$IO_SCHED" ]; then
    echo "   ✅ I/O scheduler: mq-deadline (or none, both optimal)"
    PASSED=$((PASSED + 1))
else
    echo "   ⚠️  I/O scheduler: Check manually"
    FAILED=$((FAILED + 1))
fi

# 4. Check File Watcher Limit
echo "4️⃣  File Watcher Limit..."
WATCHER_LIMIT=$(cat /proc/sys/fs/inotify/max_user_watches 2>/dev/null)
if [ "$WATCHER_LIMIT" -ge 1048576 ]; then
    echo "   ✅ File watcher limit: $WATCHER_LIMIT"
    PASSED=$((PASSED + 1))
else
    echo "   ❌ File watcher limit: $WATCHER_LIMIT (expected: >= 1048576)"
    FAILED=$((FAILED + 1))
fi

# 5. Check Systemd Services
echo "5️⃣  Systemd Services..."
SERVICES=(
    "roxy-maximum-performance.service"
    "roxy-cpu-performance-permanent.service"
    "roxy-io-scheduler-permanent.service"
    "cursor-max-performance-optimized.service"
)

for service in "${SERVICES[@]}"; do
    if systemctl is-enabled "$service" >/dev/null 2>&1; then
        if systemctl is-active "$service" >/dev/null 2>&1; then
            echo "   ✅ $service: enabled and active"
            PASSED=$((PASSED + 1))
        else
            echo "   ⚠️  $service: enabled but not active"
            FAILED=$((FAILED + 1))
        fi
    else
        echo "   ❌ $service: not enabled"
        FAILED=$((FAILED + 1))
    fi
done

# 6. Check TCP Buffer Sizes
echo "6️⃣  TCP Buffer Sizes..."
TCP_RMEM=$(sysctl -n net.core.rmem_max 2>/dev/null)
TCP_WMEM=$(sysctl -n net.core.wmem_max 2>/dev/null)
if [ "$TCP_RMEM" -ge 134217728 ] && [ "$TCP_WMEM" -ge 134217728 ]; then
    echo "   ✅ TCP buffers: rmem_max=${TCP_RMEM}, wmem_max=${TCP_WMEM}"
    PASSED=$((PASSED + 1))
else
    echo "   ⚠️  TCP buffers: rmem_max=${TCP_RMEM}, wmem_max=${TCP_WMEM}"
    FAILED=$((FAILED + 1))
fi

# Summary
echo ""
echo "================================================"
echo "📊 VERIFICATION RESULTS"
echo "================================================"
echo "   ✅ Passed: $PASSED"
if [ $FAILED -gt 0 ]; then
    echo "   ❌ Failed: $FAILED"
    echo ""
    echo "⚠️  Some optimizations may need manual application"
    ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
    echo "   Run: sudo ${ROXY_ROOT}/scripts/maximize-system-performance.sh"
    exit 1
else
    echo "   ✅ All optimizations verified!"
    echo ""
    echo "🎉 PERMANENT OPTIMIZATIONS ARE WORKING CORRECTLY"
    exit 0
fi








