#!/bin/bash
# GPU and System Stability Fixes for Mac Pro Linux
# Run with: sudo bash setup-gpu-stability.sh

set -e
echo "=========================================="
echo "MAC PRO GPU STABILITY FIXES"
echo "=========================================="

# 1. Remove problematic udev rules
echo "[1/6] Removing faulty udev rules..."
rm -f /etc/udev/rules.d/90-gpu-performance.rules
rm -f /etc/udev/rules.d/30-amdgpu-pm.rules
rm -f /etc/udev/rules.d/60-io-scheduler.rules

# 2. Add kernel parameters for GPU stability
echo "[2/6] Configuring GRUB..."
GRUB_FILE="/etc/default/grub"
if ! grep -q "amdgpu.gpu_recovery=1" "$GRUB_FILE"; then
    cp "$GRUB_FILE" "$GRUB_FILE.bak"
    sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="\([^"]*\)"/GRUB_CMDLINE_LINUX_DEFAULT="\1 amdgpu.gpu_recovery=1 amdgpu.lockup_timeout=5000 amdgpu.job_hang_limit=4 pcie_aspm=off"/' "$GRUB_FILE"
    # Show GRUB menu for recovery
    sed -i 's/GRUB_TIMEOUT=.*/GRUB_TIMEOUT=5/' "$GRUB_FILE"
    sed -i 's/GRUB_TIMEOUT_STYLE=.*/GRUB_TIMEOUT_STYLE=menu/' "$GRUB_FILE"
    update-grub
fi

# 3. Create amdgpu module config
echo "[3/6] Creating amdgpu module config..."
cat > /etc/modprobe.d/amdgpu-stability.conf << 'MODCONF'
# AMDGPU stability for Mac Pro
options amdgpu gpu_recovery=1
options amdgpu lockup_timeout=5000
options amdgpu job_hang_limit=4
options amdgpu deep_color=0
options amdgpu ppfeaturemask=0xfffd7fff
MODCONF

# 4. Configure Ollama for stability
echo "[4/6] Configuring Ollama..."
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/gpu-stability.conf << 'OLLAMA'
[Service]
Environment="OLLAMA_GPU_OVERHEAD=1"
Environment="OLLAMA_KEEP_ALIVE=5m"
Environment="OLLAMA_MAX_VRAM=6000000000"
Restart=on-failure
RestartSec=10
OLLAMA
systemctl daemon-reload

# 5. Disable WiFi P2P (causes brcmfmac errors)
echo "[5/6] Disabling WiFi P2P..."
cat > /etc/modprobe.d/brcmfmac-nowifi-p2p.conf << 'WIFI'
options brcmfmac feature_disable=0x82000
WIFI

# 6. Update initramfs
echo "[6/6] Updating initramfs..."
update-initramfs -u

echo ""
echo "=========================================="
echo "DONE - REBOOT REQUIRED"
echo "=========================================="
