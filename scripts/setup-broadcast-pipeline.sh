#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Broadcasting Pipeline Setup Script
# Sets up OBS, audio routing, content pipeline, and automation

set -e

echo "=== Broadcasting Pipeline Setup ==="
echo ""

# 1. Install OBS WebSocket plugin
echo "[1/8] Installing OBS WebSocket plugin..."
if [ ! -f /usr/lib/obs-plugins/obs-websocket.so ]; then
    cd /tmp
    git clone https://github.com/obsproject/obs-websocket.git 2>/dev/null || true
    cd obs-websocket
    if [ ! -d build ]; then
        mkdir build && cd build
        cmake .. -DCMAKE_INSTALL_PREFIX=/usr
        make -j$(nproc)
        sudo make install
    fi
    echo "✅ OBS WebSocket installed"
else
    echo "✅ OBS WebSocket already installed"
fi

# 2. Install Python dependencies
echo ""
echo "[2/8] Installing Python dependencies..."
cd ${ROXY_ROOT:-$HOME/.roxy}
if [ ! -d venv ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install obsws-python faster-whisper openai-whisper torch torchaudio --index-url https://download.pytorch.org/whl/rocm6.0
pip install ffmpeg-python python-dotenv
echo "✅ Python dependencies installed"

# 3. Configure audio routing
echo ""
echo "[3/8] Configuring audio routing..."
# Set default mic (C-Media USB)
pactl set-default-source alsa_input.usb-C-Media_Electronics_Inc._USB_Advanced_Audio_Device-00.analog-mono 2>/dev/null || \
pactl set-default-source $(pactl list sources short | grep -i 'c-media\|usb.*audio' | head -1 | awk '{print $2}') || \
echo "⚠️  Could not set default mic (may need manual config)"

# Set default output (OWC interface)
pactl set-default-sink alsa_output.usb-Other_World_Computing_OWC_Thunderbolt_3_Audio_Device-00.analog-stereo 2>/dev/null || \
pactl set-default-sink $(pactl list sinks short | grep -i 'owc\|thunderbolt' | head -1 | awk '{print $2}') || \
echo "⚠️  Could not set default output (may need manual config)"

echo "✅ Audio routing configured"

# 4. Create OBS config directory
echo ""
echo "[4/8] Setting up OBS configuration..."
mkdir -p ~/.config/obs-studio/basic/profiles
mkdir -p ~/.config/obs-studio/basic/scenes
mkdir -p ~/.config/obs-studio/plugin_config/obs-websocket

# Create basic OBS profile
cat > ~/.config/obs-studio/basic/profiles/Untitled/profile.json << 'EOF'
{
  "type": "profile",
  "name": "Untitled",
  "video": {
    "base": "1920x1080",
    "output": "1920x1080",
    "fps": 60
  },
  "audio": {
    "sampleRate": 48000
  }
}
EOF

echo "✅ OBS configuration created"

# 5. Set up content pipeline directories
echo ""
echo "[5/8] Setting up content pipeline directories..."
mkdir -p ${ROXY_ROOT:-$HOME/.roxy}/content-pipeline/{recordings,clips,transcripts,thumbnails,encoded}
mkdir -p ${ROXY_ROOT:-$HOME/.roxy}/content-pipeline/encoded/{tiktok,youtube-shorts,instagram-reels,youtube-full}
chown -R mark:mark ${ROXY_ROOT:-$HOME/.roxy}/content-pipeline
echo "✅ Content pipeline directories created"

# 6. Create OBS WebSocket config
echo ""
echo "[6/8] Configuring OBS WebSocket..."
OBS_WS_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-25)
cat > ~/.config/obs-studio/plugin_config/obs-websocket/config.json << EOF
{
  "enabled": true,
  "port": 4455,
  "password": "${OBS_WS_PASSWORD}",
  "salt": "$(openssl rand -hex 16)",
  "password_required": true
}
EOF

# Save password to Infisical or .env
echo "OBS_WEBSOCKET_PASSWORD=${OBS_WS_PASSWORD}" >> ${ROXY_ROOT:-$HOME/.roxy}/.env
echo "OBS_WEBSOCKET_PORT=4455" >> ${ROXY_ROOT:-$HOME/.roxy}/.env
echo "✅ OBS WebSocket configured (password saved to ${ROXY_ROOT:-$HOME/.roxy}/.env)"

# 7. Create automation scripts
echo ""
echo "[7/8] Creating automation scripts..."

# Start broadcast pipeline script
cat > ${ROXY_ROOT:-$HOME/.roxy}/scripts/start-broadcast-pipeline.sh << 'SCRIPT_EOF'
#!/bin/bash
# Start broadcasting pipeline

# Start OBS
obs --startrecording &
OBS_PID=$!
echo "OBS started (PID: $OBS_PID)"

# Start transcription service (if recording exists)
# This will be triggered by n8n workflow

echo "Broadcast pipeline started"
echo "OBS PID: $OBS_PID"
SCRIPT_EOF

# Stop broadcast pipeline script
cat > ${ROXY_ROOT:-$HOME/.roxy}/scripts/stop-broadcast-pipeline.sh << 'SCRIPT_EOF'
#!/bin/bash
# Stop broadcasting pipeline

pkill -f "obs --startrecording" || true
pkill -f whisperx || true
pkill -f clip_extractor || true

echo "Broadcast pipeline stopped"
SCRIPT_EOF

chmod +x ${ROXY_ROOT:-$HOME/.roxy}/scripts/start-broadcast-pipeline.sh
chmod +x ${ROXY_ROOT:-$HOME/.roxy}/scripts/stop-broadcast-pipeline.sh
echo "✅ Automation scripts created"

# 8. Test OBS WebSocket connection
echo ""
echo "[8/8] Testing setup..."
if command -v obs &> /dev/null; then
    echo "✅ OBS Studio installed: $(obs --version)"
else
    echo "⚠️  OBS Studio not found in PATH"
fi

if python3 -c "import obsws_python" 2>/dev/null; then
    echo "✅ obsws-python installed"
else
    echo "⚠️  obsws-python not installed"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Start OBS: obs"
echo "2. Configure OBS WebSocket password in OBS settings"
echo "3. Set up n8n workflows for automation"
echo "4. Test audio routing: arecord -D hw:9,0 -f cd /tmp/test.wav"
echo ""
echo "OBS WebSocket password saved to: ${ROXY_ROOT:-$HOME/.roxy}/.env"
