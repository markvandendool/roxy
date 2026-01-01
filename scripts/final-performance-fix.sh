#!/bin/bash
# Final Performance Fix - Ensures all performance settings are correct

sleep 10

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

# Set GPU to high performance
for gpu in /sys/class/drm/card*/device/power_dpm_force_performance_level; do
    [ -f "$gpu" ] && echo high > "$gpu" 2>/dev/null || true
done









