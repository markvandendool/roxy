#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Real-time Performance Monitor

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         REAL-TIME PERFORMANCE MONITOR                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

while true; do
    clear
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         REAL-TIME PERFORMANCE MONITOR                      ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    echo "CPU FREQUENCIES:"
    for cpu in 0 1 2 3 4 5 6 7; do
        freq=$(cat /sys/devices/system/cpu/cpu$cpu/cpufreq/scaling_cur_freq 2>/dev/null | awk '{printf "%.2f", $1/1000000}')
        echo "  CPU$cpu: ${freq} GHz"
    done
    
    echo ""
    echo "CPU USAGE:"
    top -bn1 | grep "Cpu(s)" | awk '{print "  " $2 " user, " $4 " system, " $8 " idle"}'
    
    echo ""
    echo "MEMORY:"
    free -h | grep Mem | awk '{print "  Used: " $3 " / " $2 " (" $3/$2*100 "%)"}'
    
    echo ""
    echo "LOAD AVERAGE:"
    uptime | awk -F'load average:' '{print "  " $2}'
    
    echo ""
    echo "THERMAL THROTTLING:"
    throttle=$(cat /sys/devices/system/cpu/cpu0/thermal_throttle/package_throttle_count 2>/dev/null)
    echo "  Package throttles: $throttle"
    
    echo ""
    echo "TEMPERATURES:"
    sensors 2>/dev/null | grep -E "Package|Core 0" | head -2 | awk '{print "  " $0}'
    
    sleep 2
done