#!/bin/bash
#
# Setup JARVIS Systemd Service
#

echo "🔧 Setting up JARVIS systemd service..."

# Copy service file
sudo cp /opt/roxy/scripts/jarvis.service /etc/systemd/system/jarvis.service 2>/dev/null || echo "Service file already exists"

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable jarvis.service

echo "✅ JARVIS service configured"
echo ""
echo "Commands:"
echo "  sudo systemctl start jarvis    # Start JARVIS"
echo "  sudo systemctl stop jarvis     # Stop JARVIS"
echo "  sudo systemctl status jarvis   # Check status"
echo "  sudo journalctl -u jarvis -f   # View logs"









