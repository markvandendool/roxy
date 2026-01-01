#!/bin/bash
# Install Permanent Performance Optimizations
# Ensures all optimizations persist across reboots

set -euo pipefail

echo "🔧 INSTALLING PERMANENT PERFORMANCE OPTIMIZATIONS"
echo "=================================================="
echo ""

# 1. Create comprehensive systemd service for maximum performance
echo "1️⃣  Creating ROXY Maximum Performance systemd service..."
sudo tee /etc/systemd/system/roxy-maximum-performance.service > /dev/null << 'EOFSERVICE'
[Unit]
Description=ROXY Maximum Performance - Apply All Optimizations at Boot
Documentation=https://www.freedesktop.org/software/systemd/man/systemd.service.html
After=sysinit.target local-fs.target
Before=graphical.target
Wants=graphical.target
Conflicts=shutdown.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/opt/roxy/scripts/maximize-system-performance.sh
StandardOutput=journal
StandardError=journal
SyslogIdentifier=roxy-max-performance

# Retry on failure
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
WantedBy=graphical.target
EOFSERVICE
echo "   ✅ Service created"

# 2. Create permanent GPU high power udev rule
echo "2️⃣  Creating permanent GPU high power udev rule..."
sudo tee /etc/udev/rules.d/99-roxy-gpu-high-power-permanent.rules > /dev/null << 'EOFRULE'
# ROXY Permanent GPU High Power Mode
# This rule ensures GPU power mode is set to HIGH immediately when GPU is detected
# Works on boot, hotplug, and resume from suspend

# AMD GPU - Set power mode to HIGH for all cards
ACTION=="add", SUBSYSTEM=="drm", KERNEL=="card*", \
  RUN+="/bin/sh -c 'echo high > /sys/class/drm/%k/device/power_dpm_force_performance_level 2>/dev/null || true'"

# Also set on change (for resume from suspend)
ACTION=="change", SUBSYSTEM=="drm", KERNEL=="card*", \
  RUN+="/bin/sh -c 'echo high > /sys/class/drm/%k/device/power_dpm_force_performance_level 2>/dev/null || true'"
EOFRULE
echo "   ✅ Udev rule created"

# 3. Create permanent CPU performance service
echo "3️⃣  Creating permanent CPU performance service..."
sudo tee /etc/systemd/system/roxy-cpu-performance-permanent.service > /dev/null << 'EOFSERVICE'
[Unit]
Description=ROXY CPU Performance Governor - Permanent
Documentation=https://www.freedesktop.org/software/systemd/man/systemd.service.html
After=sysinit.target
Before=graphical.target

[Service]
Type=oneshot
RemainAfterExit=yes
# Set CPU governor to performance for all CPUs
ExecStart=/bin/bash -c 'for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do [ -f "$cpu" ] && echo performance > "$cpu" 2>/dev/null || true; done'
# Lock CPU frequencies to maximum
ExecStart=/bin/bash -c 'for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_min_freq; do if [ -f "$cpu" ]; then MAX_FREQ=$(cat "${cpu%scaling_min_freq}scaling_max_freq" 2>/dev/null || echo ""); [ -n "$MAX_FREQ" ] && echo "$MAX_FREQ" > "$cpu" 2>/dev/null || true; fi; done'
# Set Intel P-state to maximum
ExecStart=/bin/bash -c '[ -f /sys/devices/system/cpu/intel_pstate/min_perf_pct ] && echo 100 > /sys/devices/system/cpu/intel_pstate/min_perf_pct 2>/dev/null || true'
ExecStart=/bin/bash -c '[ -f /sys/devices/system/cpu/intel_pstate/max_perf_pct ] && echo 100 > /sys/devices/system/cpu/intel_pstate/max_perf_pct 2>/dev/null || true'
ExecStart=/bin/bash -c '[ -f /sys/devices/system/cpu/intel_pstate/no_turbo ] && echo 0 > /sys/devices/system/cpu/intel_pstate/no_turbo 2>/dev/null || true'
StandardOutput=journal
StandardError=journal
SyslogIdentifier=roxy-cpu-performance

[Install]
WantedBy=multi-user.target
WantedBy=graphical.target
EOFSERVICE
echo "   ✅ Service created"

# 4. Create permanent I/O scheduler service
echo "4️⃣  Creating permanent I/O scheduler service..."
sudo tee /etc/systemd/system/roxy-io-scheduler-permanent.service > /dev/null << 'EOFSERVICE'
[Unit]
Description=ROXY I/O Scheduler Optimization - Permanent
Documentation=https://www.freedesktop.org/software/systemd/man/systemd.service.html
After=sysinit.target local-fs.target
Before=graphical.target

[Service]
Type=oneshot
RemainAfterExit=yes
# Set I/O scheduler to mq-deadline for NVMe drives
ExecStart=/bin/bash -c 'for disk in /sys/block/nvme*/queue/scheduler; do if [ -f "$disk" ]; then echo mq-deadline > "$disk" 2>/dev/null || true; fi; done'
# Set I/O scheduler to mq-deadline for SATA SSDs
ExecStart=/bin/bash -c 'for disk in /sys/block/sd*/queue/scheduler; do if [ -f "$disk" ] && grep -q mq-deadline "$disk"; then echo mq-deadline > "$disk" 2>/dev/null || true; fi; done'
StandardOutput=journal
StandardError=journal
SyslogIdentifier=roxy-io-scheduler

[Install]
WantedBy=multi-user.target
WantedBy=graphical.target
EOFSERVICE
echo "   ✅ Service created"

# 5. Update sysctl.conf with all optimizations
echo "5️⃣  Updating sysctl.conf with all optimizations..."
sudo tee -a /etc/sysctl.conf > /dev/null << 'EOFSYSCTL'

# ============================================
# ROXY MAXIMUM PERFORMANCE SETTINGS
# Applied automatically at boot
# ============================================

# File watcher limit (already set, but ensure it's correct)
fs.inotify.max_user_watches=1048576

# TCP buffer optimizations (maximum performance)
net.core.rmem_max=134217728
net.core.wmem_max=134217728
net.ipv4.tcp_rmem=4096 87380 134217728
net.ipv4.tcp_wmem=4096 65536 134217728

# Network performance
net.core.netdev_max_backlog=5000
net.ipv4.tcp_fastopen=3
net.ipv4.tcp_slow_start_after_idle=0

# Kernel scheduler optimizations
kernel.sched_migration_cost_ns=5000000
kernel.sched_autogroup_enabled=0
kernel.sched_tunable_scaling=0
kernel.sched_compat_yield=0

# Memory optimizations
vm.swappiness=1
vm.dirty_ratio=5
vm.dirty_background_ratio=2
vm.vfs_cache_pressure=50
EOFSYSCTL
echo "   ✅ sysctl.conf updated"

# 6. Fix conflicting udev rules (remove old GPU rules that set to low/auto)
echo "6️⃣  Fixing conflicting GPU udev rules..."
if [ -f /etc/udev/rules.d/90-gpu-performance.rules ]; then
    # Backup old rule
    sudo cp /etc/udev/rules.d/90-gpu-performance.rules /etc/udev/rules.d/90-gpu-performance.rules.backup
    # Remove conflicting settings
    sudo sed -i 's/echo low/echo high/g' /etc/udev/rules.d/90-gpu-performance.rules
    sudo sed -i 's/echo auto/echo high/g' /etc/udev/rules.d/90-gpu-performance.rules
    echo "   ✅ Fixed conflicting GPU rules"
else
    echo "   ℹ️  No conflicting rules found"
fi

# 7. Enable all services
echo "7️⃣  Enabling all services..."
sudo systemctl daemon-reload
sudo systemctl enable roxy-maximum-performance.service
sudo systemctl enable roxy-cpu-performance-permanent.service
sudo systemctl enable roxy-io-scheduler-permanent.service
sudo systemctl enable cursor-max-performance-optimized.service
echo "   ✅ All services enabled"

# 8. Reload udev rules
echo "8️⃣  Reloading udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=drm
echo "   ✅ Udev rules reloaded"

# 9. Start services now (don't wait for reboot)
echo "9️⃣  Starting services now..."
sudo systemctl start roxy-maximum-performance.service
sudo systemctl start roxy-cpu-performance-permanent.service
sudo systemctl start roxy-io-scheduler-permanent.service
echo "   ✅ Services started"

echo ""
echo "=================================================="
echo "✅ PERMANENT OPTIMIZATIONS INSTALLED"
echo ""
echo "📊 Summary:"
echo "   ✅ Systemd service: roxy-maximum-performance.service"
echo "   ✅ GPU udev rule: 99-roxy-gpu-high-power-permanent.rules"
echo "   ✅ CPU service: roxy-cpu-performance-permanent.service"
echo "   ✅ I/O scheduler service: roxy-io-scheduler-permanent.service"
echo "   ✅ sysctl.conf: Updated with all optimizations"
echo "   ✅ All services: Enabled and started"
echo ""
echo "🔄 These optimizations will:"
echo "   - Apply automatically at boot"
echo "   - Persist across reboots"
echo "   - Apply on resume from suspend"
echo "   - Apply on GPU hotplug"
echo ""
echo "💡 To verify after reboot:"
echo "   - GPU power: cat /sys/class/drm/card*/device/power_dpm_force_performance_level"
echo "   - CPU governor: cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
echo "   - I/O scheduler: cat /sys/block/nvme*/queue/scheduler"
echo "   - Services: systemctl status roxy-maximum-performance.service"
echo ""

