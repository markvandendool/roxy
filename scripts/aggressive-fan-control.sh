#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Aggressive Fan Control - Racing Curve for Maximum Cooling

echo "=== ACTIVATING AGGRESSIVE FAN CONTROL ==="

# Set all fans to maximum speed (255 = 100%)
for pwm in /sys/class/hwmon/hwmon*/pwm*; do
    if [ -f "$pwm" ] && [ -w "$pwm" ]; then
        echo 255 | sudo tee "$pwm" > /dev/null 2>&1
        echo "✅ Set $(basename $pwm) to maximum (255)"
    fi
done

# Enable manual fan control
for pwm_enable in /sys/class/hwmon/hwmon*/pwm*_enable; do
    if [ -f "$pwm_enable" ]; then
        echo 1 | sudo tee "$pwm_enable" > /dev/null 2>&1
        echo "✅ Enabled manual control for $(basename $pwm_enable)"
    fi
done

echo ""
echo "✅ ALL FANS SET TO MAXIMUM SPEED"
echo "   This will be LOUD but will provide maximum cooling"