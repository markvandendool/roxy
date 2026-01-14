#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
#
# Setup ROXY Systemd Service
#

echo "🔧 Setting up ROXY systemd service..."

# Copy service file
sudo cp ${ROXY_ROOT:-$HOME/.roxy}/scripts/roxy.service /etc/systemd/system/roxy.service 2>/dev/null || echo "Service file already exists"

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable roxy.service

echo "✅ ROXY service configured"
echo ""
echo "Commands:"
echo "  sudo systemctl start roxy    # Start ROXY"
echo "  sudo systemctl stop roxy     # Stop ROXY"
echo "  sudo systemctl status roxy   # Check status"
echo "  sudo journalctl -u roxy -f   # View logs"









