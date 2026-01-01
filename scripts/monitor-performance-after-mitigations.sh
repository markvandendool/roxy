#!/bin/bash

# 📊 PERFORMANCE MONITORING AFTER MITIGATION DISABLING
# Monitor CPU, GPU, temps, and performance

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   PERFORMANCE MONITORING - POST MITIGATION DISABLING      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

while true; do
    clear
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║   PERFORMANCE MONITOR - $(date '+%Y-%m-%d %H:%M:%S')        ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    # CPU Info
    echo "🔥 CPU PERFORMANCE:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    CPU_FREQ=$(lscpu | grep "CPU max MHz" | awk '{print $4}' || lscpu | grep "CPU MHz" | head -1 | awk '{print $3}')
    echo "   Max Frequency: ${CPU_FREQ} MHz"
    
    # Get current CPU frequency (average)
    if [ -f /proc/cpuinfo ]; then
        AVG_FREQ=$(grep "cpu MHz" /proc/cpuinfo | awk '{sum+=$4; count++} END {if(count>0) printf "%.0f", sum/count; else print "N/A"}')
        echo "   Average Frequency: ${AVG_FREQ} MHz"
    fi
    
    # CPU Temperature
    if [ -f /sys/class/hwmon/hwmon8/temp1_input ]; then
        CPU_TEMP=$(cat /sys/class/hwmon/hwmon8/temp1_input)
        CPU_TEMP_C=$((CPU_TEMP / 1000))
        echo "   Temperature: ${CPU_TEMP_C}°C"
        
        # Fan status based on temp
        if (( CPU_TEMP_C >= 80 )); then
            FAN_PCT=100
        elif (( CPU_TEMP_C >= 75 )); then
            FAN_PCT=90
        elif (( CPU_TEMP_C >= 70 )); then
            FAN_PCT=78
        elif (( CPU_TEMP_C >= 60 )); then
            FAN_PCT=63
        elif (( CPU_TEMP_C >= 50 )); then
            FAN_PCT=47
        elif (( CPU_TEMP_C >= 40 )); then
            FAN_PCT=31
        elif (( CPU_TEMP_C >= 30 )); then
            FAN_PCT=20
        else
            FAN_PCT=0
        fi
        echo "   Expected Fan Speed: ${FAN_PCT}%"
    fi
    
    # CPU Usage
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    echo "   CPU Usage: ${CPU_USAGE}%"
    echo ""
    
    # GPU Info
    echo "🎮 GPU PERFORMANCE:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    GPU_COUNT=0
    for gpu in /sys/class/drm/card*/device/power_dpm_force_performance_level; do
        if [ -f "$gpu" ]; then
            GPU_COUNT=$((GPU_COUNT + 1))
            GPU_NUM=$(basename $(dirname $(dirname $(dirname $gpu))))
            GPU_MODE=$(cat "$gpu")
            echo "   GPU $GPU_COUNT ($GPU_NUM): $GPU_MODE mode"
            
            # Try to get GPU temp
            GPU_TEMP_FILE=$(find $(dirname $gpu)/hwmon*/ -name "temp1_input" 2>/dev/null | head -1)
            if [ -f "$GPU_TEMP_FILE" ]; then
                GPU_TEMP=$(cat "$GPU_TEMP_FILE")
                GPU_TEMP_C=$((GPU_TEMP / 1000))
                echo "      Temperature: ${GPU_TEMP_C}°C"
            fi
        fi
    done
    echo ""
    
    # Memory
    echo "🧠 MEMORY:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    free -h | grep -E "^Mem|^Swap" | awk '{printf "   %s: %s used, %s free\n", $1, $3, $4}'
    
    # Check Zswap
    if [ -f /sys/module/zswap/parameters/enabled ]; then
        ZSWAP=$(cat /sys/module/zswap/parameters/enabled)
        if [ "$ZSWAP" = "Y" ]; then
            echo "   Zswap: ✅ ACTIVE"
        fi
    fi
    echo ""
    
    # Mitigations Status
    echo "🛡️  MITIGATIONS STATUS:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if [ -f /sys/devices/system/cpu/vulnerabilities/spectre_v2 ]; then
        SPECTRE_V2=$(cat /sys/devices/system/cpu/vulnerabilities/spectre_v2)
        if echo "$SPECTRE_V2" | grep -qi "vulnerable\|not mitigated"; then
            echo "   Spectre V2: ⚠️  DISABLED (performance mode)"
        else
            echo "   Spectre V2: ✅ Mitigated"
        fi
    fi
    
    if [ -f /sys/devices/system/cpu/vulnerabilities/retbleed ]; then
        RETBLEED=$(cat /sys/devices/system/cpu/vulnerabilities/retbleed)
        if echo "$RETBLEED" | grep -qi "vulnerable\|not mitigated"; then
            echo "   Retbleed: ⚠️  DISABLED (performance mode)"
        else
            echo "   Retbleed: ✅ Mitigated"
        fi
    fi
    echo ""
    
    # Load Average
    echo "📊 SYSTEM LOAD:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    uptime | awk -F'load average:' '{print "   "$2}'
    echo ""
    
    echo "Press Ctrl+C to exit"
    sleep 2
done













