#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Create OBS scenes for broadcasting

set -e

OBS_CONFIG="$HOME/.config/obs-studio/basic/scenes"

echo "=== Creating OBS Scenes ==="
echo ""

mkdir -p "$OBS_CONFIG"

# Scene 1: DAW Recording
cat > "$OBS_CONFIG/DAW_Recording.json" << 'EOF'
{
  "name": "DAW Recording",
  "sources": [
    {
      "name": "Display Capture - DAW",
      "type": "display_capture",
      "settings": {
        "display": 1,
        "show_cursor": false
      }
    },
    {
      "name": "Mic Audio",
      "type": "pulse_input_capture",
      "settings": {
        "device": "alsa_input.usb-C-Media_Electronics_Inc._USB_Advanced_Audio_Device-00.mono-fallback"
      }
    },
    {
      "name": "DAW Audio",
      "type": "pulse_output_capture",
      "settings": {
        "device": "alsa_output.usb-Other_World_Computing_OWC_Thunderbolt_3_Audio_Device-00.analog-stereo.monitor"
      }
    }
  ]
}
EOF

# Scene 2: Desktop Capture
cat > "$OBS_CONFIG/Desktop_Capture.json" << 'EOF'
{
  "name": "Desktop Capture",
  "sources": [
    {
      "name": "Display Capture - All",
      "type": "display_capture",
      "settings": {
        "display": 0,
        "show_cursor": true
      }
    },
    {
      "name": "System Audio",
      "type": "pulse_output_capture",
      "settings": {
        "device": "default"
      }
    }
  ]
}
EOF

# Scene 3: Camera Scene
cat > "$OBS_CONFIG/Camera_Scene.json" << 'EOF'
{
  "name": "Camera Scene",
  "sources": [
    {
      "name": "Cam Link 4K",
      "type": "v4l2_input",
      "settings": {
        "device": "/dev/video0"
      }
    },
    {
      "name": "Mic Audio",
      "type": "pulse_input_capture",
      "settings": {
        "device": "alsa_input.usb-C-Media_Electronics_Inc._USB_Advanced_Audio_Device-00.mono-fallback"
      }
    }
  ]
}
EOF

# Scene 4: Multi-Source Composite
cat > "$OBS_CONFIG/Multi_Source.json" << 'EOF'
{
  "name": "Multi-Source Composite",
  "sources": [
    {
      "name": "Display Capture",
      "type": "display_capture",
      "settings": {
        "display": 1
      }
    },
    {
      "name": "Cam Link 4K",
      "type": "v4l2_input",
      "settings": {
        "device": "/dev/video0"
      },
      "transform": {
        "position": {"x": 1600, "y": 0},
        "scale": {"x": 0.5, "y": 0.5}
      }
    },
    {
      "name": "Mic Audio",
      "type": "pulse_input_capture",
      "settings": {
        "device": "alsa_input.usb-C-Media_Electronics_Inc._USB_Advanced_Audio_Device-00.mono-fallback"
      }
    },
    {
      "name": "System Audio",
      "type": "pulse_output_capture",
      "settings": {
        "device": "default"
      }
    }
  ]
}
EOF

echo "✅ OBS scenes created:"
ls -1 "$OBS_CONFIG"/*.json | while read scene; do
    echo "  - $(basename $scene)"
done

echo ""
echo "To use:"
echo "1. Start OBS: obs"
echo "2. Scenes will be available in OBS"
echo "3. Configure sources as needed"
echo "4. Test recording"
