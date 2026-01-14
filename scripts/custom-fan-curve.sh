#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Custom Fan Curve - Aggressive but Reasonable
# Mac Pro Cooling - Racing Curve

# Fan curve configuration
# Temp thresholds and fan speeds (0-255)
# Format: TEMP_THRESHOLD:FAN_SPEED

FAN_CURVE=(
    "30:50"    # 30°C = 20% fan (quiet idle)
    "40:80"    # 40°C = 31% fan (light load)
    "50:120"   # 50°C = 47% fan (moderate)
    "60:160"   # 60°C = 63% fan (warm)
    "70:200"   # 70°C = 78% fan (hot - aggressive)
    "75:230"   # 75°C = 90% fan (very hot)
    "80:255"   # 80°C = 100% fan (maximum - emergency)
)

get_cpu_temp() {
    # Try multiple sources for accurate temperature
    temp1=$(sensors 2>/dev/null | grep "Package id 0" | awk '{print $4}' | sed 's/+//;s/°C//')
    temp2=$(cat /sys/class/thermal/thermal_zone1/temp 2>/dev/null | awk '{printf "%.1f", $1/1000}')
    
    # Use the higher, more accurate reading
    if [ -n "$temp1" ] && [ -n "$temp2" ]; then
        if (( $(echo "$temp1 > $temp2" | bc -l) )); then
            echo "$temp1"
        else
            echo "$temp2"
        fi
    elif [ -n "$temp1" ]; then
        echo "$temp1"
    elif [ -n "$temp2" ]; then
        echo "$temp2"
    else
        echo "50"  # Default safe temperature
    fi
}

get_fan_speed() {
    local temp=$1
    local speed=50  # Default minimum
    
    for curve in "${FAN_CURVE[@]}"; do
        threshold=$(echo $curve | cut -d: -f1)
        fan_speed=$(echo $curve | cut -d: -f2)
        
        if (( $(echo "$temp >= $threshold" | bc -l) )); then
            speed=$fan_speed
        fi
    done
    
    echo $speed
}

# Main loop
echo "=== Custom Fan Curve Active ==="
echo "Monitoring temperature and adjusting fans..."

while true; do
    temp=$(get_cpu_temp)
    fan_speed=$(get_fan_speed $temp)
    
    # Set fan speeds
    for pwm in /sys/class/hwmon/hwmon*/pwm1; do
        if [ -f "$pwm" ] && [ -w "$pwm" ]; then
            echo 1 | sudo tee "${pwm}_enable" > /dev/null 2>&1  # Manual mode
            echo $fan_speed | sudo tee "$pwm" > /dev/null 2>&1
        fi
    done
    
    # Log every 30 seconds
    if [ $((SECONDS % 30)) -eq 0 ]; then
        echo "[$(date +%H:%M:%S)] Temp: ${temp}°C → Fan: ${fan_speed}/255 ($(echo "scale=0; $fan_speed*100/255" | bc)%)"
    fi
    
    sleep 2
done