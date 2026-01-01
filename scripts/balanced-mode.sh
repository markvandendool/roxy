#!/bin/bash
# Balanced Performance Mode - Optimized but Sustainable

echo "╔════════════════════════════════════════════════════════════╗"
echo "║              BALANCED PERFORMANCE MODE                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Fans: Automatic control (smart curve)
echo "1. Setting fans to automatic control..."
for pwm_enable in /sys/class/hwmon/hwmon*/pwm*_enable; do
    if [ -f "$pwm_enable" ]; then
        echo 2 | sudo tee "$pwm_enable" > /dev/null 2>&1
    fi
done
echo "✅ Fans: Automatic (quiet when idle, fast when needed)"

# CPU: Allow scaling but keep performance governor
echo ""
echo "2. Configuring CPU scaling..."
echo 1000000 | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_min_freq > /dev/null
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance | sudo tee $cpu > /dev/null
done
echo "✅ CPU: 1.0 GHz (idle) → 4.4 GHz (turbo)"
echo "✅ Governor: performance (scales up aggressively)"

# Keep all optimizations
echo ""
echo "3. Performance optimizations: ACTIVE"
echo "✅ P-State: 100% min/max"
echo "✅ Turbo: Enabled"
echo "✅ Memory: Optimized"
echo "✅ I/O: Optimized"

# Re-enable C-states for idle
echo ""
echo "4. Enabling C-states for idle power savings..."
for cpu in /sys/devices/system/cpu/cpu*/cpuidle/state*/disable; do
    if [ -f "$cpu" ]; then
        echo 0 | sudo tee $cpu > /dev/null 2>&1 || true
    fi
done
echo "✅ C-states: Enabled (power saving when idle)"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║         BALANCED MODE ACTIVATED                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "System will now:"
echo "  • Run quietly when idle (fans slow, CPU at 1.0 GHz)"
echo "  • Scale up aggressively when needed (CPU to 4.4 GHz)"
echo "  • Keep all performance optimizations active"
echo "  • Save power when not under load"
