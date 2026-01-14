#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# GPU Overclocking Guide for AMD GPUs

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         GPU OVERCLOCKING GUIDE - W5700X & RX 6900 XT     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

echo "CURRENT GPU STATUS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
for card in /sys/class/drm/card*/device; do
    gpu_id=$(basename $(dirname $card))
    if [ -f "${card}/pp_od_clk_voltage" ]; then
        echo "GPU $gpu_id:"
        echo "  Power State: $(cat ${card}/power_dpm_state 2>/dev/null)"
        echo "  Overclocking: Available via pp_od_clk_voltage"
        echo ""
    fi
done

echo "OVERCLOCKING METHODS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Method 1: AMDGPU PP_OD_CLK_VOLTAGE (Recommended)"
echo "  Location: /sys/class/drm/card*/device/pp_od_clk_voltage"
echo "  Usage: echo 's 0 2100' | sudo tee /sys/class/drm/card*/device/pp_od_clk_voltage"
echo "  (Sets GPU clock to 2100 MHz)"
echo ""
echo "Method 2: Power Limit Increase"
echo "  Location: /sys/class/drm/card*/device/pp_od_clk_voltage"
echo "  Usage: echo 'c' | sudo tee /sys/class/drm/card*/device/pp_od_clk_voltage"
echo "  (Shows current limits)"
echo ""
echo "Method 3: ROCm/ROCm-SMI (If installed)"
echo "  Usage: rocm-smi --setperflevel high"
echo "  Usage: rocm-smi --setpoweroverdrive 20"
echo ""
echo "SAFE OVERCLOCKING VALUES:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "RX 6900 XT:"
echo "  • Stock GPU Clock: ~2100 MHz"
echo "  • Safe OC: +50-100 MHz (2150-2200 MHz)"
echo "  • Memory: +50-100 MHz"
echo "  • Power Limit: +10-15%"
echo ""
echo "W5700X:"
echo "  • Stock GPU Clock: ~1900 MHz"
echo "  • Safe OC: +50-75 MHz (1950-1975 MHz)"
echo "  • Memory: +50-75 MHz"
echo "  • Power Limit: +5-10%"
echo ""
echo "⚠️  WARNING: Overclocking can cause instability and void warranties!"
echo "   Always monitor temperatures and test stability!"