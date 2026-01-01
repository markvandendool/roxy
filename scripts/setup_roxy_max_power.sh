#!/bin/bash
# ROXY Maximum Power Setup - Automated Configuration
# Run this once to maximize ROXY's growth and power

set -e

ROXY_ROOT="/opt/roxy"
VENV_PYTHON="$ROXY_ROOT/venv/bin/python3"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🚀 ROXY MAXIMUM POWER SETUP                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Run Python maximizer
echo "Running automated optimization..."
cd "$ROXY_ROOT"
source venv/bin/activate
python3 scripts/maximize_roxy_power.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start ROXY with maximum power:"
echo "  sudo systemctl start roxy.service"
echo ""
echo "To enable auto-growth:"
echo "  sudo systemctl enable roxy.service"
echo ""









