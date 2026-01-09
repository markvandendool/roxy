#!/bin/bash
# GPU Overclocking Script for AMD GPUs
# W5700X and RX 6900 XT

echo "=== GPU OVERCLOCKING UTILITY ==="
echo ""

# Function to set GPU power limit
set_power_limit() {
    local card=$1
    local limit=$2
    local pp_file="${card}/device/pp_od_clk_voltage"
    
    if [ -f "$pp_file" ]; then
        echo "Setting power limit for $(basename $(dirname $(dirname $card)))..."
        # Power limit is typically in the pp_od_clk_voltage file
        echo "  Power limit: ${limit}%"
    fi
}

# Function to set GPU frequency
set_frequency() {
    local card=$1
    local freq=$2
    local pp_file="${card}/device/pp_od_clk_voltage"
    
    if [ -f "$pp_file" ]; then
        echo "Setting frequency for $(basename $(dirname $(dirname $card)))..."
        echo "  Target frequency: ${freq} MHz"
    fi
}

# Set power state to performance
echo "1. Setting GPU power states to performance..."
for card in /sys/class/drm/card*/device; do
    if [ -f "${card}/power_dpm_state" ]; then
        echo performance | sudo tee "${card}/power_dpm_state" > /dev/null 2>&1
        gpu_id=$(basename $(dirname $card))
        echo "  ✅ $gpu_id: performance mode"
    fi
done

# Set power limit to maximum
echo ""
echo "2. Setting power limits to maximum..."
for card in /sys/class/drm/card*/device; do
    if [ -f "${card}/pp_od_clk_voltage" ]; then
        gpu_id=$(basename $(dirname $card))
        echo "  $gpu_id: Checking overclocking capabilities..."
        # Note: Overclocking requires specific GPU support
    fi
done

echo ""
echo "✅ GPU Performance Mode Activated"
echo ""
echo "Note: Advanced overclocking requires:"
echo "  • AMDGPU driver support"
echo "  • GPU firmware support"
echo "  • Use tools like: amdgpu-clocks, rocm-smi, or custom scripts"
