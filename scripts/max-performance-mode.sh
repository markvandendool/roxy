#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Maximum Performance Mode - Aggressive Tuning
# For Intel Xeon W-3275 with 56 cores

echo "=== ACTIVATING MAXIMUM PERFORMANCE MODE ==="

# CPU Performance
echo 100 | sudo tee /sys/devices/system/cpu/intel_pstate/min_perf_pct
echo 100 | sudo tee /sys/devices/system/cpu/intel_pstate/max_perf_pct
echo 0 | sudo tee /sys/devices/system/cpu/intel_pstate/no_turbo

for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance | sudo tee $cpu > /dev/null
done

# Disable C-states
for cpu in /sys/devices/system/cpu/cpu*/cpuidle/state[2-9]/disable; do
    echo 1 | sudo tee $cpu > /dev/null 2>&1 || true
done

# Memory
echo 1 | sudo tee /proc/sys/vm/swappiness
echo 10 | sudo tee /proc/sys/vm/dirty_ratio
echo 5 | sudo tee /proc/sys/vm/dirty_background_ratio

# I/O Scheduler
for disk in /sys/block/nvme*/queue/scheduler; do
    if grep -q none "$disk"; then
        echo none | sudo tee "$disk" > /dev/null
    fi
done

echo "✅ MAXIMUM PERFORMANCE MODE ACTIVATED"