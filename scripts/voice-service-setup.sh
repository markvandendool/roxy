#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
#
# Setup ROXY Voice Pipeline Systemd Service
#

echo "🔧 Setting up ROXY Voice Pipeline systemd service..."

# Copy service file
sudo cp ${ROXY_ROOT:-$HOME/.roxy}/scripts/roxy-voice.service /etc/systemd/system/roxy-voice.service 2>/dev/null || echo "Service file already exists"

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable roxy-voice.service

echo "✅ ROXY Voice Pipeline service configured"
echo ""
echo "Commands:"
echo "  sudo systemctl start roxy-voice    # Start voice pipeline"
echo "  sudo systemctl stop roxy-voice     # Stop voice pipeline"
echo "  sudo systemctl status roxy-voice   # Check status"
echo "  sudo journalctl -u roxy-voice -f   # View logs"









