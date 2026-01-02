#!/bin/bash
# Setup script for Logitech mouse button programming
# Supports Input Remapper and Piper/libratbag

set -e

echo "🖱️  Logitech Mouse Button Programming Setup"
echo "=========================================="
echo ""

# Detect mouse
MOUSE_DETECTED=$(lsusb | grep -i logitech || echo "")
if [ -z "$MOUSE_DETECTED" ]; then
    echo "⚠️  Warning: No Logitech mouse detected via USB"
    echo "   Continuing anyway..."
else
    echo "✅ Detected: $MOUSE_DETECTED"
fi
echo ""

# Check session type
SESSION_TYPE=$(echo $XDG_SESSION_TYPE)
echo "📋 Session Type: $SESSION_TYPE"
echo ""

# Function to install Input Remapper
install_input_remapper() {
    echo "📦 Installing Input Remapper..."
    
    if command -v input-remapper-control &> /dev/null; then
        echo "   ✅ Input Remapper already installed"
        return 0
    fi
    
    sudo apt update
    sudo apt install -y input-remapper
    
    # Start and enable service
    echo "   🔧 Starting Input Remapper service..."
    sudo systemctl enable input-remapper
    sudo systemctl start input-remapper
    
    # Add user to input group
    if ! groups | grep -q input; then
        echo "   👤 Adding user to 'input' group..."
        sudo usermod -aG input $USER
        echo "   ⚠️  You may need to log out and back in for group changes to take effect"
    fi
    
    echo "   ✅ Input Remapper installed and started"
}

# Function to install Piper and libratbag
install_piper() {
    echo "📦 Installing Piper and libratbag..."
    
    if command -v piper &> /dev/null && command -v ratbagctl &> /dev/null; then
        echo "   ✅ Piper and libratbag already installed"
    else
        sudo apt update
        sudo apt install -y piper libratbag2 ratbagd
        
        echo "   ✅ Piper and libratbag installed"
    fi
    
    # Start and enable ratbagd
    echo "   🔧 Starting ratbagd service..."
    systemctl --user enable ratbagd
    systemctl --user start ratbagd
    
    # Wait a moment for service to start
    sleep 2
    
    # Check if mouse is detected
    if command -v ratbagctl &> /dev/null; then
        echo "   🔍 Checking for supported devices..."
        DEVICES=$(ratbagctl list 2>&1 || echo "")
        if echo "$DEVICES" | grep -q "No devices"; then
            echo "   ⚠️  No devices detected by libratbag"
            echo "      Your mouse may not be in the supported device list"
            echo "      Check: https://github.com/libratbag/libratbag/tree/master/data/devices"
        else
            echo "   ✅ Devices detected:"
            echo "$DEVICES" | sed 's/^/      /'
        fi
    fi
    
    echo "   ✅ Piper setup complete"
}

# Function to install evtest (for button identification)
install_evtest() {
    echo "📦 Installing evtest (for button identification)..."
    
    if command -v evtest &> /dev/null; then
        echo "   ✅ evtest already installed"
    else
        sudo apt install -y evtest
        echo "   ✅ evtest installed"
    fi
}

# Main installation
echo "🚀 Starting installation..."
echo ""

# Install Input Remapper (recommended for Wayland)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  Installing Input Remapper (Recommended)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
install_input_remapper
echo ""

# Install Piper (optional, for hardware features)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  Installing Piper + libratbag (Optional)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -p "   Install Piper? (y/n) [y]: " install_piper_choice
install_piper_choice=${install_piper_choice:-y}
if [[ "$install_piper_choice" =~ ^[Yy]$ ]]; then
    install_piper
else
    echo "   ⏭️  Skipping Piper installation"
fi
echo ""

# Install evtest
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  Installing evtest (Button Identification)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
install_evtest
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Installation Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Launch Input Remapper:"
echo "   input-remapper-control"
echo ""
echo "2. Launch Piper (if installed):"
echo "   piper"
echo ""
echo "3. Identify your mouse buttons:"
echo "   sudo evtest"
echo ""
echo "4. Read the full guide:"
echo "   cat /opt/roxy/LOGITECH_MOUSE_SETUP.md"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check service status
echo "🔍 Service Status:"
echo ""
echo "Input Remapper:"
sudo systemctl is-active input-remapper && echo "   ✅ Running" || echo "   ❌ Not running"

if [[ "$install_piper_choice" =~ ^[Yy]$ ]]; then
    echo ""
    echo "ratbagd:"
    systemctl --user is-active ratbagd && echo "   ✅ Running" || echo "   ❌ Not running"
fi

echo ""
echo "🎉 Setup complete! You can now program your mouse buttons."
echo ""



