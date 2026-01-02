#!/bin/bash
#===============================================================================
# iPhone VNC Setup - Remote Desktop Access from iPhone
# Sets up wayvnc for Wayland remote desktop access
#===============================================================================

set -euo pipefail

USER_HOME="$HOME"
SERVICE_DIR="$USER_HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/wayvnc.service"

echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║  iPhone VNC Setup - Remote Desktop Access                                ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if wayvnc is installed
if ! command -v wayvnc &> /dev/null; then
    echo "❌ wayvnc is not installed"
    echo "   Installing wayvnc..."
    sudo apt update && sudo apt install -y wayvnc
fi

echo "✅ wayvnc is installed"
echo ""

# Get system IP address
SYSTEM_IP=$(ip addr show | grep -E "inet " | grep -v "127.0.0.1" | awk '{print $2}' | cut -d/ -f1 | head -1)
echo "📍 System IP address: $SYSTEM_IP"
echo ""

# Prompt for VNC password
echo "🔐 Setting up VNC password..."
echo "   (This will be used to connect from your iPhone)"
read -sp "Enter VNC password (min 8 chars): " VNC_PASSWORD
echo ""
read -sp "Confirm VNC password: " VNC_PASSWORD_CONFIRM
echo ""

if [ "$VNC_PASSWORD" != "$VNC_PASSWORD_CONFIRM" ]; then
    echo "❌ Passwords don't match!"
    exit 1
fi

if [ ${#VNC_PASSWORD} -lt 8 ]; then
    echo "❌ Password must be at least 8 characters!"
    exit 1
fi

# Create wayvnc config directory
mkdir -p "$USER_HOME/.config/wayvnc"

# Create wayvnc config file with password
CONFIG_FILE="$USER_HOME/.config/wayvnc/config"
cat > "$CONFIG_FILE" << EOF
address=0.0.0.0
port=5900
password=$VNC_PASSWORD
EOF

chmod 600 "$CONFIG_FILE"

echo "✅ Password configured"
echo ""

# Create systemd user service directory
mkdir -p "$SERVICE_DIR"

# Create systemd service file
# Note: Using CONFIG_FILE variable which is set above
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=WayVNC - VNC server for Wayland
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/wayvnc -C $CONFIG_FILE
Restart=on-failure
RestartSec=5
Environment=WAYLAND_DISPLAY=wayland-0

[Install]
WantedBy=default.target
EOF

echo "✅ Created systemd service file: $SERVICE_FILE"
echo ""

# Reload systemd
systemctl --user daemon-reload

# Enable service
systemctl --user enable wayvnc.service

echo "✅ Service enabled (will start on login)"
echo ""

# Start service
systemctl --user start wayvnc.service

# Wait a moment for service to start
sleep 2

# Check service status
if systemctl --user is-active --quiet wayvnc.service; then
    echo "✅ wayvnc service is running"
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════════════════╗"
    echo "║  ✅ VNC Server is Ready!                                                  ║"
    echo "╚═══════════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📱 iPhone Connection Details:"
    echo "   Server: $SYSTEM_IP"
    echo "   Port: 5900"
    echo "   Password: [the password you just set]"
    echo ""
    echo "📲 iPhone Apps to Use:"
    echo "   • VNC Viewer (by RealVNC) - Free, recommended"
    echo "   • Jump Desktop - Paid, excellent"
    echo "   • Screens - Paid, great features"
    echo ""
    echo "🔧 Service Management:"
    echo "   Start:   systemctl --user start wayvnc"
    echo "   Stop:    systemctl --user stop wayvnc"
    echo "   Status:  systemctl --user status wayvnc"
    echo "   Logs:    journalctl --user -u wayvnc -f"
    echo ""
    echo "⚠️  Security Note:"
    echo "   Make sure your firewall allows port 5900 if needed:"
    echo "   sudo ufw allow 5900/tcp"
    echo ""
else
    echo "❌ Service failed to start"
    echo "   Check logs: journalctl --user -u wayvnc -n 50"
    exit 1
fi

