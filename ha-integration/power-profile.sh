#!/bin/bash
# Roxy Power Profiles

PROFILE="$1"

case "$PROFILE" in
    morning)
        echo "☀️ Morning profile"
        sudo rocm-smi --setperflevel auto 2>/dev/null
        # Lights off (when Tuya works)
        # python3 ~/.roxy/ha-integration/tuya-control.py off "Studio Lights"
        ;;
    
    work)
        echo "💼 Work profile"
        sudo rocm-smi --setperflevel high 2>/dev/null
        ;;
    
    night)
        echo "🌙 Night profile"
        sudo rocm-smi --setperflevel low 2>/dev/null
        # All lights off
        ;;
    
    gaming)
        echo "🎮 Gaming profile"
        sudo rocm-smi --setperflevel high 2>/dev/null
        # Max GPU fans
        sudo rocm-smi --setfan 100 2>/dev/null
        ;;
    
    streaming)
        echo "🔴 Streaming profile"
        python3 ~/.roxy/ha-integration/roxy-hardware.py go-live
        ;;
    
    idle)
        echo "😴 Idle profile"
        sudo rocm-smi --setperflevel auto 2>/dev/null
        sudo rocm-smi --resetfans 2>/dev/null
        ;;
    
    *)
        echo "Usage: power-profile.sh [morning|work|night|gaming|streaming|idle]"
        exit 1
        ;;
esac

echo "Profile '$PROFILE' activated"
