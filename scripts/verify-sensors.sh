#!/bin/bash
# Comprehensive Sensor Verification Script

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         COMPREHENSIVE SENSOR VERIFICATION                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

echo "=== TEMPERATURE SENSORS ==="
echo ""
echo "1. sensors command:"
sensors 2>&1 | grep -E "Package|Core|temp" | head -10

echo ""
echo "2. Thermal zones:"
for zone in /sys/class/thermal/thermal_zone*/temp; do
    if [ -f "$zone" ]; then
        temp=$(cat $zone 2>/dev/null)
        if [ -n "$temp" ] && [ "$temp" != "0" ] && [ "$temp" != "-1" ] && [ "$temp" != "-2" ]; then
            zone_name=$(cat $(dirname $zone)/type 2>/dev/null || echo "unknown")
            temp_c=$(echo "$temp / 1000" | bc)
            if (( $(echo "$temp_c > -50 && $temp_c < 150" | bc -l) )); then
                echo "  ✅ $zone_name: ${temp_c}°C"
            else
                echo "  ❌ $zone_name: ${temp_c}°C (INVALID!)"
            fi
        fi
    fi
done

echo ""
echo "3. CPU thermal data:"
echo "  Package throttles: $(cat /sys/devices/system/cpu/cpu0/thermal_throttle/package_throttle_count 2>/dev/null)"
echo "  Core throttles: $(cat /sys/devices/system/cpu/cpu0/thermal_throttle/core_throttle_count 2>/dev/null)"

echo ""
echo "=== FAN STATUS ==="
for pwm in /sys/class/hwmon/hwmon*/pwm1; do
    if [ -f "$pwm" ]; then
        speed=$(cat $pwm 2>/dev/null)
        enable=$(cat ${pwm}_enable 2>/dev/null)
        hwmon_name=$(cat $(dirname $pwm)/name 2>/dev/null || echo "unknown")
        echo "  $hwmon_name: $speed/255 (enable: $enable)"
    fi
done

echo ""
echo "=== CPU FREQUENCY ==="
for cpu in 0 1 2 3; do
    freq=$(cat /sys/devices/system/cpu/cpu$cpu/cpufreq/scaling_cur_freq 2>/dev/null | awk '{printf "%.2f", $1/1000000}')
    echo "  CPU$cpu: ${freq} GHz"
done
