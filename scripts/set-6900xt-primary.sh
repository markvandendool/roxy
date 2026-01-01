#!/bin/bash

# Make RX 6900 XT (card2) the primary GPU for all applications

echo "🔧 Setting RX 6900 XT as primary GPU..."

# Method 1: Set DRI_PRIME default to 1 (second GPU = RX 6900 XT)
# Add to ~/.bashrc and ~/.profile
if ! grep -q "DRI_PRIME=1" ~/.bashrc 2>/dev/null; then
    echo "" >> ~/.bashrc
    echo "# Force RX 6900 XT as primary GPU" >> ~/.bashrc
    echo "export DRI_PRIME=1" >> ~/.bashrc
    echo "✅ Added DRI_PRIME=1 to ~/.bashrc"
fi

if ! grep -q "DRI_PRIME=1" ~/.profile 2>/dev/null; then
    echo "" >> ~/.profile
    echo "# Force RX 6900 XT as primary GPU" >> ~/.profile
    echo "export DRI_PRIME=1" >> ~/.profile
    echo "✅ Added DRI_PRIME=1 to ~/.profile"
fi

# Method 2: Create system-wide environment file
sudo tee /etc/environment.d/90-gpu-primary.conf > /dev/null << 'ENVEOF'
# Force RX 6900 XT (card2) as primary GPU
DRI_PRIME=1
ENVEOF

echo "✅ Created system-wide GPU config"
echo ""
echo "⚠️  You need to:"
echo "   1. Log out and back in (or restart)"
echo "   2. Or run: source ~/.bashrc"
echo ""
echo "To verify: echo \$DRI_PRIME (should show 1)"
