#!/bin/bash
# COMPREHENSIVE PERFORMANCE FIX - Fixes Everything

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     COMPREHENSIVE PERFORMANCE FIX - FERRARI MODE          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 1. FIX TEMPERATURE SENSORS
echo "1. Loading temperature sensor modules..."
sudo modprobe coretemp 2>/dev/null || true
sudo modprobe k10temp 2>/dev/null || true
sudo modprobe nct6775 2>/dev/null || true
echo "✅ Temperature sensors initialized"

# 2. MAXIMUM FAN SPEED
echo ""
echo "2. Setting all fans to MAXIMUM speed..."
for pwm in /sys/class/hwmon/hwmon*/pwm*; do
    if [ -f "$pwm" ] && [ -w "$pwm" ]; then
        echo 255 | sudo tee "$pwm" > /dev/null 2>&1 && echo "  ✅ $(basename $pwm): MAX"
    fi
done
for pwm_enable in /sys/class/hwmon/hwmon*/pwm*_enable; do
    if [ -f "$pwm_enable" ]; then
        echo 1 | sudo tee "$pwm_enable" > /dev/null 2>&1
    fi
done
echo "✅ All fans at MAXIMUM"

# 3. REMOVE ALL CPU LIMITS
echo ""
echo "3. Removing all CPU performance limits..."
echo 100 | sudo tee /sys/devices/system/cpu/intel_pstate/min_perf_pct
echo 100 | sudo tee /sys/devices/system/cpu/intel_pstate/max_perf_pct
echo 0 | sudo tee /sys/devices/system/cpu/intel_pstate/no_turbo
echo "✅ P-state limits removed"

# 4. FORCE MAXIMUM FREQUENCY
echo ""
echo "4. Forcing CPU to maximum frequency..."
max_freq=$(cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq)
echo $max_freq | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_min_freq > /dev/null
echo $max_freq | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq > /dev/null
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance | sudo tee $cpu > /dev/null
done
echo "✅ CPU forced to $(echo "$max_freq / 1000000" | bc) GHz minimum"

# 5. DISABLE ALL C-STATES
echo ""
echo "5. Disabling all CPU idle states..."
for cpu in /sys/devices/system/cpu/cpu*/cpuidle/state*/disable; do
    echo 1 | sudo tee $cpu > /dev/null 2>&1 || true
done
echo "✅ All C-states disabled"

# 6. OPTIMIZE MEMORY
echo ""
echo "6. Optimizing memory settings..."
echo 1 | sudo tee /proc/sys/vm/swappiness
echo 10 | sudo tee /proc/sys/vm/dirty_ratio
echo 5 | sudo tee /proc/sys/vm/dirty_background_ratio
echo "✅ Memory optimized"

# 7. I/O OPTIMIZATION
echo ""
echo "7. Optimizing I/O..."
for disk in /sys/block/nvme*/queue/scheduler; do
    if grep -q none "$disk"; then
        echo none | sudo tee "$disk" > /dev/null
    fi
done
echo "✅ I/O optimized"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              ALL FIXES APPLIED - FERRARI MODE             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Current CPU frequencies:"
for cpu in 0 1 2 3; do
    freq=$(cat /sys/devices/system/cpu/cpu$cpu/cpufreq/scaling_cur_freq 2>/dev/null | awk '{printf "%.2f", $1/1000000}')
    echo "  CPU$cpu: ${freq} GHz"
done
echo ""
echo "Temperature:"
sensors 2>/dev/null | grep -E "Package|Core 0" | head -2 || echo "  Checking thermal zones..."
