#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Configure audio routing for broadcasting

set -e

echo "=== Audio Routing Setup ==="
echo ""

# Get audio device IDs
C_MEDIA_SOURCE=$(pactl list sources short | grep -i 'c-media\|usb.*advanced.*audio' | head -1 | awk '{print $2}' || echo "")
OWC_SINK=$(pactl list sinks short | grep -i 'owc\|thunderbolt.*audio' | head -1 | awk '{print $2}' || echo "")

if [ -z "$C_MEDIA_SOURCE" ]; then
    echo "⚠️  C-Media mic not found in PulseAudio"
    echo "   Available sources:"
    pactl list sources short | head -5
else
    echo "✅ Found C-Media mic: $C_MEDIA_SOURCE"
    pactl set-default-source "$C_MEDIA_SOURCE"
    echo "✅ Set as default input"
fi

if [ -z "$OWC_SINK" ]; then
    echo "⚠️  OWC interface not found in PulseAudio"
    echo "   Available sinks:"
    pactl list sinks short | head -5
else
    echo "✅ Found OWC interface: $OWC_SINK"
    pactl set-default-sink "$OWC_SINK"
    echo "✅ Set as default output"
fi

# Create PulseAudio config for OBS
mkdir -p ~/.config/pulse
cat > ~/.config/pulse/default.pa << 'EOF'
# Broadcasting audio routing
load-module module-alsa-source device=hw:9,0 source_name=usb_mic
load-module module-alsa-sink device=hw:5,0 sink_name=owc_output

# Set defaults
set-default-source usb_mic
set-default-sink owc_output
EOF

echo ""
echo "✅ Audio routing configured"
echo ""
echo "Test recording:"
echo "  arecord -D hw:9,0 -f cd -t wav /tmp/test.wav"
echo "  (speak, then Ctrl+C)"
echo "  aplay /tmp/test.wav"
