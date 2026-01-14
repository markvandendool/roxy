#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Remove ALL Power Limits - Maximum Performance

echo "=== REMOVING ALL POWER LIMITS ==="

# 1. Intel RAPL Power Limits
echo "1. Removing Intel RAPL power limits..."
for domain in /sys/devices/virtual/powercap/intel-rapl/intel-rapl:*/; do
    for limit in ${domain}constraint_*_power_limit_uw; do
        if [ -f "$limit" ]; then
            max=$(cat ${limit%_uw}_max_power_uw 2>/dev/null)
            if [ -n "$max" ] && [ "$max" != "0" ]; then
                echo $max | sudo tee $limit > /dev/null 2>&1
                echo "  ✅ $(basename $domain): $(basename $limit) = ${max}μW"
            fi
        fi
    done
done

# 2. Intel P-State
echo ""
echo "2. Setting Intel P-State to maximum..."
echo 100 | sudo tee /sys/devices/system/cpu/intel_pstate/min_perf_pct
echo 100 | sudo tee /sys/devices/system/cpu/intel_pstate/max_perf_pct
echo 0 | sudo tee /sys/devices/system/cpu/intel_pstate/no_turbo

# 3. Force minimum frequency to maximum
echo ""
echo "3. Forcing minimum frequency to maximum..."
max_freq=$(cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq)
echo $max_freq | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_min_freq > /dev/null
echo $max_freq | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq > /dev/null

# 4. Performance governor
echo ""
echo "4. Setting all CPUs to performance governor..."
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance | sudo tee $cpu > /dev/null
done

echo ""
echo "✅ ALL POWER LIMITS REMOVED"
echo "   CPU should now be able to reach maximum frequency"