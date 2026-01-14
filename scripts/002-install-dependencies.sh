#!/bin/bash
#===============================================================================
# LUNA-000 CITADEL - Dependency Installation
# Target: ROXY-1 (Ubuntu 24.04)
# Run as: sudo ./002-install-dependencies.sh
#===============================================================================

set -euo pipefail
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"

echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║  CITADEL DEPENDENCY INSTALLATION                                          ║"
echo "║  Target: Ubuntu 24.04 with AMD GPUs                                       ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"

# Check Ubuntu version
if ! grep -q "24.04" /etc/os-release 2>/dev/null; then
    echo "⚠️  Warning: This script is designed for Ubuntu 24.04"
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
fi

#===============================================================================
echo ""
echo "[1/10] Updating system packages..."
#===============================================================================
apt-get update
apt-get upgrade -y

#===============================================================================
echo ""
echo "[2/10] Installing base dependencies..."
#===============================================================================
apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    pkg-config \
    libssl-dev \
    libffi-dev \
    python3 \
    python3-pip \
    python3-venv \
    ffmpeg \
    jq \
    htop \
    ncdu \
    tree \
    unzip \
    gnome-screenshot \
    wl-clipboard \
    pipewire \
    pipewire-audio \
    wireplumber

#===============================================================================
echo ""
echo "[3/10] Installing Docker..."
#===============================================================================
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker ${SUDO_USER:-$USER}
    systemctl enable docker
    systemctl start docker
    echo "✅ Docker installed"
else
    echo "✅ Docker already installed"
fi

# Docker Compose (plugin)
if ! docker compose version &> /dev/null; then
    apt-get install -y docker-compose-plugin
    echo "✅ Docker Compose plugin installed"
else
    echo "✅ Docker Compose already installed"
fi

#===============================================================================
echo ""
echo "[4/10] Installing gVisor (runsc) for browser sandboxing..."
#===============================================================================
if ! command -v runsc &> /dev/null; then
    curl -fsSL https://gvisor.dev/archive.key | gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" > /etc/apt/sources.list.d/gvisor.list
    apt-get update
    apt-get install -y runsc

    # Configure Docker to use runsc
    cat > /etc/docker/daemon.json << 'EOF'
{
    "runtimes": {
        "runsc": {
            "path": "/usr/bin/runsc"
        }
    }
}
EOF
    systemctl restart docker
    echo "✅ gVisor installed and configured"
else
    echo "✅ gVisor already installed"
fi

#===============================================================================
echo ""
echo "[5/10] Installing ROCm for AMD GPU..."
#===============================================================================
if ! command -v rocm-smi &> /dev/null; then
    # Add ROCm repository
    wget https://repo.radeon.com/amdgpu-install/6.0/ubuntu/jammy/amdgpu-install_6.0.60000-1_all.deb
    apt-get install -y ./amdgpu-install_6.0.60000-1_all.deb
    rm amdgpu-install_6.0.60000-1_all.deb

    amdgpu-install -y --usecase=rocm,graphics --no-dkms

    # Add user to required groups
    usermod -aG render ${SUDO_USER:-$USER}
    usermod -aG video ${SUDO_USER:-$USER}

    echo "✅ ROCm installed (reboot required)"
else
    echo "✅ ROCm already installed"
    rocm-smi --showproductname
fi

#===============================================================================
echo ""
echo "[6/10] Installing Ollama..."
#===============================================================================
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh

    # Configure for AMD GPU
    mkdir -p /etc/systemd/system/ollama.service.d
    cat > /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="HSA_OVERRIDE_GFX_VERSION=10.3.0"
Environment="OLLAMA_HOST=0.0.0.0"
EOF

    systemctl daemon-reload
    systemctl enable ollama
    systemctl restart ollama
    echo "✅ Ollama installed"

    # Pull models
    echo "Pulling llama3:8b model..."
    sudo -u ${SUDO_USER:-$USER} ollama pull llama3:8b
else
    echo "✅ Ollama already installed"
fi

#===============================================================================
echo ""
echo "[7/10] Installing dotool for Wayland automation..."
#===============================================================================
if ! command -v dotool &> /dev/null; then
    # Build from source (more reliable than package)
    cd /tmp
    git clone https://git.sr.ht/~geb/dotool
    cd dotool
    ./build.sh
    cp dotool dotoold /usr/local/bin/
    cd /
    rm -rf /tmp/dotool

    # Configure uinput
    echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' > /etc/udev/rules.d/99-uinput.rules
    udevadm control --reload-rules
    udevadm trigger

    # Add user to input group
    usermod -aG input ${SUDO_USER:-$USER}
    echo "✅ dotool installed"
else
    echo "✅ dotool already installed"
fi

#===============================================================================
echo ""
echo "[8/10] Installing Python packages..."
#===============================================================================
# Create Roxy virtual environment
VENV_PATH="${ROXY_ROOT:-$HOME/.roxy}/venv"
if [ ! -d "$VENV_PATH" ]; then
    python3 -m venv "$VENV_PATH"
    chown -R ${SUDO_USER:-$USER}:${SUDO_USER:-$USER} "$VENV_PATH"
fi

# Install packages
sudo -u ${SUDO_USER:-$USER} "$VENV_PATH/bin/pip" install --upgrade pip
sudo -u ${SUDO_USER:-$USER} "$VENV_PATH/bin/pip" install \
    browser-use \
    langchain-ollama \
    langgraph \
    mem0ai \
    chromadb \
    playwright \
    faster-whisper \
    openwakeword \
    TTS \
    obsws-python \
    nats-py \
    minio \
    fastmcp \
    python-telegram-bot \
    "discord.py" \
    httpx \
    pydantic \
    rich

# Install Playwright browsers
sudo -u ${SUDO_USER:-$USER} "$VENV_PATH/bin/playwright" install chromium firefox
echo "✅ Python packages installed"

#===============================================================================
echo ""
echo "[9/10] Installing Infisical CLI..."
#===============================================================================
if ! command -v infisical &> /dev/null; then
    curl -1sLf 'https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.deb.sh' | bash
    apt-get install -y infisical
    echo "✅ Infisical CLI installed"
else
    echo "✅ Infisical CLI already installed"
fi

#===============================================================================
echo ""
echo "[10/10] Installing SOPS + Age for encryption..."
#===============================================================================
if ! command -v sops &> /dev/null; then
    SOPS_VERSION="3.8.1"
    wget "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops_${SOPS_VERSION}_amd64.deb"
    apt-get install -y "./sops_${SOPS_VERSION}_amd64.deb"
    rm "./sops_${SOPS_VERSION}_amd64.deb"
    echo "✅ SOPS installed"
else
    echo "✅ SOPS already installed"
fi

if ! command -v age &> /dev/null; then
    apt-get install -y age
    echo "✅ Age installed"
else
    echo "✅ Age already installed"
fi

#===============================================================================
echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║  INSTALLATION COMPLETE                                                    ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Installed:                                                               ║"
echo "║  • Docker + Docker Compose                                                ║"
echo "║  • gVisor (runsc) sandbox runtime                                         ║"
echo "║  • ROCm 6.0 for AMD GPU                                                   ║"
echo "║  • Ollama with llama3:8b                                                  ║"
echo "║  • dotool for Wayland automation                                          ║"
echo "║  • Python venv at ${ROXY_ROOT:-$HOME/.roxy}/venv                                          ║"
echo "║  • Infisical CLI                                                          ║"
echo "║  • SOPS + Age encryption                                                  ║"
echo "║                                                                           ║"
echo "║  ⚠️  REBOOT REQUIRED for ROCm and group changes                           ║"
echo "║                                                                           ║"
echo "║  After reboot:                                                            ║"
echo "║  1. Run: rocm-smi (verify GPU visible)                                    ║"
echo "║  2. Run: ollama run llama3:8b \"hello\" (verify GPU inference)             ║"
echo "║  3. Run: echo 'type hello' | dotool (verify input works)                  ║"
echo "║  4. Run: ./003-deploy-foundation.sh                                       ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
