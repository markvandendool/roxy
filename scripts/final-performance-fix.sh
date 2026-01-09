#!/bin/bash
# Final Performance Fix - Ensures all performance settings are correct
# CRITICAL: Only touch RX 6900 XT (card2). NEVER touch W5700X (card1)!

sleep 5

# Set CPU governor to performance
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    [ -f "$cpu" ] && echo performance > "$cpu" 2>/dev/null || true
done

# Set Intel P-state
if [ -f /sys/devices/system/cpu/intel_pstate/min_perf_pct ]; then
    echo 100 > /sys/devices/system/cpu/intel_pstate/min_perf_pct 2>/dev/null || true
    echo 100 > /sys/devices/system/cpu/intel_pstate/max_perf_pct 2>/dev/null || true
    echo 0 > /sys/devices/system/cpu/intel_pstate/no_turbo 2>/dev/null || true
fi

# Set ONLY RX 6900 XT (card2) to high performance
# W5700X (card1) at 09:00.0 causes PCIe AER BadTLP crashes - DO NOT TOUCH!
GPU_CARD2="/sys/class/drm/card2/device/power_dpm_force_performance_level"
if [ -f "$GPU_CARD2" ]; then
    echo high > "$GPU_CARD2" 2>/dev/null && echo "RX 6900 XT (card2) set to high performance"
fi

echo "Final performance fix applied (W5700X excluded)"
