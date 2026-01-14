#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# midi-latency-test.sh
# SKOREQ OBS Dream Collection - MIDI Latency Testing
# EPIC: SKOREQ-OBS-DREAM | STORY-009

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║      SKOREQ MIDI Latency Test Suite v1.0.0                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }

# ============================================
# 1. MIDI Device Detection
# ============================================
echo "1. MIDI Device Detection"
echo "------------------------"

if command -v aconnect &> /dev/null; then
    MIDI_CLIENTS=$(aconnect -l | grep -c "client [0-9]" || echo 0)
    if [ "$MIDI_CLIENTS" -gt 2 ]; then
        pass "Found $MIDI_CLIENTS MIDI clients"
        aconnect -l | grep -E "client [0-9]+:" | while read line; do
            echo "   $line"
        done
    else
        warn "Only system MIDI clients found. Connect a MIDI device."
    fi
else
    fail "aconnect not found. Install: sudo apt install alsa-utils"
fi
echo ""

# ============================================
# 2. USB Audio Latency Settings
# ============================================
echo "2. USB Audio Latency Configuration"
echo "-----------------------------------"

if [ -f /sys/module/snd_usb_audio/parameters/nrpacks ]; then
    NRPACKS=$(cat /sys/module/snd_usb_audio/parameters/nrpacks)
    if [ "$NRPACKS" -le 2 ]; then
        pass "USB audio nrpacks=$NRPACKS (low latency)"
    else
        warn "USB audio nrpacks=$NRPACKS (consider lowering)"
        echo "   To reduce: echo 'options snd-usb-audio nrpacks=1' | sudo tee /etc/modprobe.d/usb-audio.conf"
    fi
else
    warn "Cannot read USB audio parameters"
fi
echo ""

# ============================================
# 3. Virtual MIDI Port Check
# ============================================
echo "3. Virtual MIDI Port Status"
echo "---------------------------"

if lsmod | grep -q snd_virmidi; then
    pass "snd-virmidi module loaded"
    VIRMIDI_COUNT=$(aconnect -l | grep -c "Virtual Raw MIDI" || echo 0)
    echo "   $VIRMIDI_COUNT virtual MIDI ports available"
else
    warn "snd-virmidi not loaded"
    echo "   To load: sudo modprobe snd-virmidi"
    echo "   To persist: echo 'snd-virmidi' | sudo tee /etc/modules-load.d/virmidi.conf"
fi
echo ""

# ============================================
# 4. MIDI Routing Check
# ============================================
echo "4. Current MIDI Routing"
echo "-----------------------"

CONNECTIONS=$(aconnect -l | grep -c "Connecting To" || echo 0)
if [ "$CONNECTIONS" -gt 0 ]; then
    pass "Found $CONNECTIONS active MIDI connections"
    aconnect -l | grep "Connecting To" | while read line; do
        echo "   $line"
    done
else
    warn "No MIDI connections established"
    echo "   Use: aconnect <source>:0 <dest>:0"
fi
echo ""

# ============================================
# 5. System Performance Check
# ============================================
echo "5. System Performance"
echo "---------------------"

# CPU
CPU_USAGE=$(grep 'cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$4+$5)} END {printf "%.1f", usage}')
if (( $(echo "$CPU_USAGE < 50" | bc -l) )); then
    pass "CPU usage: ${CPU_USAGE}%"
else
    warn "CPU usage: ${CPU_USAGE}% (high - may affect latency)"
fi

# Memory
MEM_INFO=$(free -h | awk '/Mem:/ {print $3 "/" $2}')
pass "Memory: $MEM_INFO"

# Audio group membership
if groups | grep -q audio; then
    pass "User in 'audio' group"
else
    warn "User not in 'audio' group"
    echo "   Add: sudo usermod -a -G audio \$USER (then logout/login)"
fi
echo ""

# ============================================
# 6. NDI Status Check
# ============================================
echo "6. NDI Source Detection"
echo "-----------------------"

if command -v avahi-browse &> /dev/null; then
    NDI_SOURCES=$(timeout 3 avahi-browse -t _ndi._tcp 2>/dev/null | grep -c "IPv4" || echo 0)
    if [ "$NDI_SOURCES" -gt 0 ]; then
        pass "Found $NDI_SOURCES NDI sources"
        timeout 3 avahi-browse -t _ndi._tcp 2>/dev/null | grep "IPv4" | while read line; do
            echo "   $line"
        done
    else
        warn "No NDI sources found (widget server may not be running)"
    fi
else
    warn "avahi-browse not found. Install: sudo apt install avahi-utils"
fi
echo ""

# ============================================
# 7. OBS WebSocket Check
# ============================================
echo "7. OBS WebSocket Status"
echo "-----------------------"

if command -v nc &> /dev/null; then
    if nc -z localhost 4455 2>/dev/null; then
        pass "OBS WebSocket responding on port 4455"
    else
        warn "OBS WebSocket not responding (OBS may not be running)"
    fi
else
    warn "netcat not available for port check"
fi
echo ""

# ============================================
# 8. Interactive MIDI Test
# ============================================
echo "8. Interactive MIDI Test"
echo "------------------------"
echo "   This will listen for MIDI input for 5 seconds."
echo "   Press any key on your MIDI device..."
echo ""

MIDI_DEVICE=""
# Try to find a MIDI input device
if aconnect -l 2>/dev/null | grep -qi "midi keyboard\|usb midi\|launchpad"; then
    MIDI_DEVICE=$(aconnect -l | grep -i "midi keyboard\|usb midi\|launchpad" | head -1 | grep -oP "client \K[0-9]+")
fi

if [ -n "$MIDI_DEVICE" ] && command -v aseqdump &> /dev/null; then
    echo "   Listening on client $MIDI_DEVICE..."
    timeout 5 aseqdump -p "$MIDI_DEVICE" 2>/dev/null | head -10 || echo "   (No MIDI events received)"
else
    warn "Cannot run interactive test (no device or aseqdump not found)"
fi
echo ""

# ============================================
# 9. Latency Estimation
# ============================================
echo "9. Estimated Latency Budget"
echo "---------------------------"
echo "   Target: < 50ms end-to-end"
echo ""
echo "   Component          Target    Status"
echo "   ─────────────────────────────────────"
echo "   USB MIDI input     < 5ms     $([ "$NRPACKS" -le 2 ] && echo 'OK' || echo 'Check')"
echo "   Widget processing  < 15ms    (depends on widget server)"
echo "   NDI transmission   < 10ms    $([ "$NDI_SOURCES" -gt 0 ] && echo 'OK' || echo 'Check')"
echo "   OBS rendering      < 16ms    (1 frame at 60fps)"
echo "   ─────────────────────────────────────"
echo "   Total estimate     < 46ms"
echo ""

# ============================================
# 10. Manual Latency Test Instructions
# ============================================
echo "10. Manual Latency Measurement"
echo "------------------------------"
echo "   For precise latency measurement:"
echo ""
echo "   1. Record screen + audio at 240fps (phone slow-mo works)"
echo "   2. Set up DAW with visible click/flash synced to audio click"
echo "   3. Play keyboard while recording"
echo "   4. In video editor, count frames between:"
echo "      - Audio click (waveform spike)"
echo "      - Visual update in widget"
echo "   5. Calculate: frames ÷ 240 × 1000 = latency in ms"
echo ""

# ============================================
# Summary
# ============================================
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                      Test Complete                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "For issues, check:"
echo "  - ~/.roxy/docs/docs/obs/MIDI_INTEGRATION_GUIDE.md"
echo "  - Run: aconnect -l (list devices)"
echo "  - Run: aseqdump -p <client> (monitor MIDI)"
echo ""