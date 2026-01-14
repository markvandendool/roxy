#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Best Vitals Dashboard for Linux
# Real-time comprehensive monitoring

clear
while true; do
    clear
    echo "╔══════════════════════════════════════════════════════════════════════════╗"
    echo "║                    SYSTEM VITALS DASHBOARD                                ║"
    echo "╚══════════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    # CPU Temperature (multiple sources)
    echo "🌡️  TEMPERATURE:"
    temp1=$(sensors 2>/dev/null | grep "Package id 0" | awk '{print $4}' | sed 's/+//;s/°C//')
    temp2=$(cat /sys/class/thermal/thermal_zone1/temp 2>/dev/null | awk '{printf "%.1f", $1/1000}')
    if [ -n "$temp1" ] && (( $(echo "$temp1 > 0 && $temp1 < 150" | bc -l) )); then
        echo "  CPU Package: ${temp1}°C"
    elif [ -n "$temp2" ] && (( $(echo "$temp2 > 0 && $temp2 < 150" | bc -l) )); then
        echo "  CPU Package: ${temp2}°C"
    else
        echo "  CPU Package: ERROR - Invalid reading!"
    fi
    
    # CPU Frequency
    echo ""
    echo "⚡ CPU FREQUENCY:"
    for cpu in 0 1 2 3; do
        freq=$(cat /sys/devices/system/cpu/cpu$cpu/cpufreq/scaling_cur_freq 2>/dev/null | awk '{printf "%.2f", $1/1000000}')
        echo "  CPU$cpu: ${freq} GHz"
    done
    
    # CPU Usage
    echo ""
    echo "📊 CPU USAGE:"
    top -bn1 | grep "Cpu(s)" | awk '{print "  " $2 " user, " $4 " system, " $8 " idle"}'
    
    # Memory
    echo ""
    echo "💾 MEMORY:"
    free -h | grep Mem | awk '{print "  Used: " $3 " / " $2 " (" int($3/$2*100) "%)"}'
    
    # Load Average
    echo ""
    echo "📈 LOAD AVERAGE:"
    uptime | awk -F'load average:' '{print "  " $2}'
    
    # Fan Speeds
    echo ""
    echo "🌀 FANS:"
    for pwm in /sys/class/hwmon/hwmon*/pwm1; do
        if [ -f "$pwm" ]; then
            speed=$(cat $pwm 2>/dev/null)
            percent=$(echo "scale=0; $speed*100/255" | bc)
            hwmon_name=$(cat $(dirname $pwm)/name 2>/dev/null || echo "unknown")
            echo "  $hwmon_name: ${speed}/255 (${percent}%)"
        fi
    done
    
    # Thermal Throttling
    echo ""
    echo "⚠️  THROTTLING:"
    pkg_throttle=$(cat /sys/devices/system/cpu/cpu0/thermal_throttle/package_throttle_count 2>/dev/null)
    core_throttle=$(cat /sys/devices/system/cpu/cpu0/thermal_throttle/core_throttle_count 2>/dev/null)
    echo "  Package: $pkg_throttle events"
    echo "  Core: $core_throttle events"
    
    echo ""
    echo "Press Ctrl+C to exit"
    sleep 2
done