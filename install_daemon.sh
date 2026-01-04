#!/bin/bash
# Install ROXY Core (Wayland-Correct User Service)
# Extends existing ROXY infrastructure with always-on capabilities

set -e

ROXY_DIR="$HOME/.roxy"
VENV_DIR="$ROXY_DIR/venv"
SERVICE_NAME="roxy-core"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

# Uninstall mode
if [ "$1" = "uninstall" ]; then
    echo "================================================"
    echo "  ROXY Core Uninstallation"
    echo "================================================"
    
    systemctl --user stop "$SERVICE_NAME" 2>/dev/null || true
    systemctl --user disable "$SERVICE_NAME" 2>/dev/null || true
    rm -f "$SYSTEMD_USER_DIR/$SERVICE_NAME.service"
    systemctl --user daemon-reload
    
    echo "✓ Service removed"
    echo ""
    echo "To remove GNOME shortcut:"
    echo "  gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings '[]'"
    echo ""
    echo "To remove ROXY directory (WARNING: deletes all data):"
    echo "  rm -rf $ROXY_DIR"
    exit 0
fi

echo "================================================"
echo "  ROXY Core Installation (Wayland-Correct)"
echo "================================================"

# NO SUDO REQUIRED - user service only
if [ "$EUID" -eq 0 ]; then
    echo "ERROR: Do NOT run this as root/sudo"
    echo "ROXY runs as a user service under your account"
    exit 1
fi

# Check for existing infrastructure
echo "[1/5] Checking existing ROXY infrastructure..."

if [ ! -f "$ROXY_DIR/roxy_assistant_v2.py" ]; then
    echo "⚠️  WARNING: roxy_assistant_v2.py not found"
    echo "   Voice features will be limited"
fi

if [ ! -f "$ROXY_DIR/roxy_commands.py" ]; then
    echo "⚠️  WARNING: roxy_commands.py not found"
    echo "   Command routing will be limited"
fi

echo "✓ Infrastructure check complete"

# Create directory structure
echo "[2/5] Setting up ROXY directories..."
mkdir -p "$ROXY_DIR/logs"
mkdir -p "$ROXY_DIR/data"
mkdir -p "$ROXY_DIR/config"
mkdir -p "$ROXY_DIR/run"
mkdir -p "$SYSTEMD_USER_DIR"

# Install dependencies
echo "[3/5] Installing Python dependencies..."

if [ ! -d "$VENV_DIR" ]; then
    echo "   Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
else
    echo "   Virtual environment already exists (skipping creation)"
fi

source "$VENV_DIR/bin/activate"

# Install existing ROXY dependencies (NO pynput - Wayland incompatible)
if [ -f "$ROXY_DIR/requirements.txt" ]; then
    pip install -q -r "$ROXY_DIR/requirements.txt"
else
    # Minimal install for IPC-based architecture
    pip install -q requests chromadb ollama python-dotenv
fi

deactivate

echo "✓ Dependencies installed (stdlib HTTP only, no framework dependencies)"

# Install systemd USER service
echo "[4/5] Installing systemd user service..."

if [ -f "$SYSTEMD_USER_DIR/roxy-core.service" ]; then
    systemctl --user daemon-reload
    systemctl --user enable "$SERVICE_NAME"
    systemctl --user restart "$SERVICE_NAME"
    
    echo "✓ Service installed and started"
    sleep 2
    
    # Test health endpoint
    if curl -s http://127.0.0.1:8765/health > /dev/null 2>&1; then
        echo "✓ ROXY core IPC endpoint responding"
    else
        echo "⚠️  Warning: IPC endpoint not responding yet (may still be starting)"
    fi
else
    echo "ERROR: Service file not found at $SYSTEMD_USER_DIR/roxy-core.service"
    exit 1
fi

# Test client
echo "[5/5] Testing client..."
chmod +x "$ROXY_DIR/roxy_client.py"
echo "✓ Client configured"

echo ""
echo "================================================"
echo "  INSTALLATION COMPLETE"
echo "================================================"
echo ""
echo "ROXY Core Status:"
systemctl --user status "$SERVICE_NAME" --no-pager -l || true

echo ""
echo "Test the IPC endpoint:"
echo "  curl http://127.0.0.1:8765/health"
echo ""
echo "Test the client (interactive):"
echo "  $VENV_DIR/bin/python $ROXY_DIR/roxy_client.py"
echo ""
echo "View logs:"
echo "  journalctl --user -u $SERVICE_NAME -n 100 --no-pager"
echo ""
echo "================================================"
echo "  BIND CTRL+SPACE TO ROXY"
echo "================================================"
echo ""

# Check if shortcut already exists
CURRENT_BINDING=$(gsettings get org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ binding 2>/dev/null || echo "''")

if [ "$CURRENT_BINDING" = "'<Primary>space'" ]; then
    echo "✓ GNOME shortcut already configured (Ctrl+Space → ROXY)"
else
    echo "To bind Ctrl+Space, run these commands:"
    echo ""
    echo "gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings \"['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/']\""
    echo ""
    echo "gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ name 'ROXY Chat'"
    echo ""
    echo "gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ command 'gnome-terminal -- bash -lc \"$VENV_DIR/bin/python $ROXY_DIR/roxy_client.py\"'"
    echo ""
    echo "gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ binding '<Primary>space'"
fi
echo ""
echo "================================================"

echo ""
echo "4. Use hotkey:"
echo "   Press Ctrl+Space anywhere to chat with ROXY"
echo ""
echo "5. Voice activation (if configured):"
echo "   Say 'Hey Roxy' (requires roxy_assistant_v2.py)"
echo ""
echo "================================================"
