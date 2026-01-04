#!/bin/bash
#
# ROXY Voice Chat Launcher
# Start different voice chat modes
#

ROXY_DIR="$HOME/.roxy"
VENV="$ROXY_DIR/venv"

# Activate venv
source "$VENV/bin/activate"

show_menu() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║           🎤 ROXY Voice Chat Launcher                         ║"
    echo "╠═══════════════════════════════════════════════════════════════╣"
    echo "║                                                               ║"
    echo "║   1) Quick Voice Chat    - Simple CLI-based voice chat        ║"
    echo "║   2) Real-Time Voice     - Full-featured with interruption    ║"
    echo "║   3) WebRTC Browser      - Browser-based voice chat           ║"
    echo "║   4) Test Audio Setup    - Check microphone and speakers      ║"
    echo "║                                                               ║"
    echo "║   q) Quit                                                     ║"
    echo "║                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
}

test_audio() {
    echo "🔧 Testing audio setup..."
    echo ""
    
    python3 << 'EOF'
import sounddevice as sd
import numpy as np

print("📱 Input devices:")
inputs = sd.query_devices(kind='input')
if isinstance(inputs, dict):
    print(f"   Default: {inputs['name']}")
else:
    for d in inputs:
        print(f"   - {d['name']}")

print("\n🔊 Output devices:")
outputs = sd.query_devices(kind='output')
if isinstance(outputs, dict):
    print(f"   Default: {outputs['name']}")
else:
    for d in outputs:
        print(f"   - {d['name']}")

print("\n🎵 Playing test tone...")
duration = 0.5
frequency = 440
t = np.linspace(0, duration, int(44100 * duration))
tone = 0.3 * np.sin(2 * np.pi * frequency * t)
sd.play(tone, 44100)
sd.wait()
print("✅ Audio output working!")

print("\n🎤 Recording test (2 seconds)...")
recording = sd.rec(int(2 * 16000), samplerate=16000, channels=1)
sd.wait()
level = np.max(np.abs(recording))
print(f"✅ Audio input working! (peak level: {level:.4f})")
if level < 0.001:
    print("⚠️ Microphone level very low - check your input device")
EOF
}

case "${1:-menu}" in
    1|quick)
        echo "🎤 Starting Quick Voice Chat..."
        python3 "$ROXY_DIR/quick_voice.py"
        ;;
    2|realtime)
        echo "🎤 Starting Real-Time Voice Chat..."
        python3 "$ROXY_DIR/realtime_voice.py"
        ;;
    3|web|browser)
        echo "🌐 Starting WebRTC Voice Server..."
        echo "Open http://localhost:8767/voice in your browser"
        python3 "$ROXY_DIR/webrtc_voice_server.py"
        ;;
    4|test)
        test_audio
        ;;
    menu|*)
        while true; do
            show_menu
            read -p "Select option: " choice
            case $choice in
                1) python3 "$ROXY_DIR/quick_voice.py" ;;
                2) python3 "$ROXY_DIR/realtime_voice.py" ;;
                3) 
                    echo "Open http://localhost:8767/voice in your browser"
                    python3 "$ROXY_DIR/webrtc_voice_server.py"
                    ;;
                4) test_audio ;;
                q|Q) echo "👋 Goodbye!"; exit 0 ;;
                *) echo "Invalid option" ;;
            esac
        done
        ;;
esac

# Alias for realtime talk
    5|talk)
        echo "🎤 Starting Real-Time Talk (Simple Mode)..."
        python3 "$ROXY_DIR/realtime_talk.py"
        ;;
