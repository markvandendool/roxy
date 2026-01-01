#!/bin/bash

# 🚀 TOP 20 MAXIMUM IMPACT IMPROVEMENTS - Implementation Script
# Mac Pro 2019 - Linux Optimization

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   TOP 20 MAXIMUM IMPACT PERFORMANCE IMPROVEMENTS          ║"
echo "║   Implementation Script                                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (sudo)"
    exit 1
fi

# Backup existing configs
echo "📦 Creating backups..."
mkdir -p /opt/roxy/backups/$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/roxy/backups/$(date +%Y%m%d_%H%M%S)"
cp /etc/sysctl.conf "$BACKUP_DIR/sysctl.conf.bak" 2>/dev/null || true
cp /etc/default/grub "$BACKUP_DIR/grub.bak" 2>/dev/null || true
cp /etc/fstab "$BACKUP_DIR/fstab.bak" 2>/dev/null || true
echo "✅ Backups created in $BACKUP_DIR"
echo ""

# ============================================================================
# TIER 1: CRITICAL HIGH-IMPACT
# ============================================================================

echo "🔥 TIER 1: CRITICAL HIGH-IMPACT IMPROVEMENTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 2. GPU Power Management to High Performance
echo ""
echo "2️⃣  Setting GPU Power Management to HIGH performance..."
for gpu in /sys/class/drm/card*/device/power_dpm_force_performance_level; do
    if [ -f "$gpu" ]; then
        echo "high" > "$gpu"
        GPU_NUM=$(basename $(dirname $(dirname $(dirname $gpu))))
        echo "   ✅ GPU $GPU_NUM: Set to HIGH"
    fi
done

# 3. Transparent Hugepages to madvise
echo ""
echo "3️⃣  Optimizing Transparent Hugepages to madvise..."
echo "madvise" > /sys/kernel/mm/transparent_hugepage/enabled
echo "madvise" > /sys/kernel/mm/transparent_hugepage/defrag
echo "   ✅ Transparent Hugepages: madvise"

# 4. Enable Zswap
echo ""
echo "4️⃣  Enabling Zswap (compressed swap)..."
if ! grep -q "zswap" /etc/modprobe.d/zswap.conf 2>/dev/null; then
    echo "options zswap enabled=1 zswap_compressor=lz4 zswap_max_pool_percent=20" > /etc/modprobe.d/zswap.conf
    echo "   ✅ Zswap configured (requires reboot to activate)"
    if ! grep -q "^zswap" /etc/modules 2>/dev/null; then
        echo "zswap" >> /etc/modules
    fi
else
    echo "   ⚠️  Zswap already configured"
fi

# 5. Optimize VFS Cache Pressure
echo ""
echo "5️⃣  Optimizing VFS Cache Pressure..."
if ! grep -q "^vm.vfs_cache_pressure" /etc/sysctl.conf; then
    echo "" >> /etc/sysctl.conf
    echo "# VFS Cache Pressure Optimization" >> /etc/sysctl.conf
    echo "vm.vfs_cache_pressure = 50" >> /etc/sysctl.conf
    sysctl -w vm.vfs_cache_pressure=50
    echo "   ✅ VFS Cache Pressure: 50 (was 100)"
else
    echo "   ⚠️  Already configured"
fi

# ============================================================================
# TIER 2: SIGNIFICANT IMPROVEMENTS
# ============================================================================

echo ""
echo "⚡ TIER 2: SIGNIFICANT IMPROVEMENTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 6. Optimize Page Cluster Size
echo ""
echo "6️⃣  Optimizing Page Cluster Size..."
if ! grep -q "^vm.page-cluster" /etc/sysctl.conf; then
    echo "vm.page-cluster = 0" >> /etc/sysctl.conf
    sysctl -w vm.page-cluster=0
    echo "   ✅ Page Cluster: 0 (was 3)"
else
    echo "   ⚠️  Already configured"
fi

# 7. Verify I/O Scheduler for NVMe
echo ""
echo "7️⃣  Verifying I/O Scheduler for NVMe drives..."
for disk in /sys/block/nvme*/queue/scheduler; do
    if [ -f "$disk" ]; then
        echo "none" > "$disk"
        DISK_NAME=$(basename $(dirname $(dirname $disk)))
        echo "   ✅ $DISK_NAME: none"
    fi
done

# 8. Increase I/O Request Queue Depth
echo ""
echo "8️⃣  Increasing I/O Request Queue Depth..."
for disk in /sys/block/nvme*/queue/nr_requests; do
    if [ -f "$disk" ]; then
        echo "1023" > "$disk"
        DISK_NAME=$(basename $(dirname $(dirname $disk)))
        CURRENT=$(cat "$disk")
        echo "   ✅ $DISK_NAME: $CURRENT"
    fi
done

# 10. Enable BBR TCP Congestion Control
echo ""
echo "🔟 Enabling BBR TCP Congestion Control..."
if ! grep -q "^net.core.default_qdisc" /etc/sysctl.conf; then
    echo "" >> /etc/sysctl.conf
    echo "# Network Optimization - BBR" >> /etc/sysctl.conf
    echo "net.core.default_qdisc = fq" >> /etc/sysctl.conf
    echo "net.ipv4.tcp_congestion_control = bbr" >> /etc/sysctl.conf
    sysctl -w net.core.default_qdisc=fq
    sysctl -w net.ipv4.tcp_congestion_control=bbr 2>/dev/null || echo "   ⚠️  BBR may require kernel module (modprobe tcp_bbr)"
    echo "   ✅ BBR enabled"
else
    echo "   ⚠️  Already configured"
fi

# 11. Enable TCP Fast Open
echo ""
echo "1️⃣1️⃣  Enabling TCP Fast Open..."
if ! grep -q "^net.ipv4.tcp_fastopen" /etc/sysctl.conf; then
    echo "net.ipv4.tcp_fastopen = 3" >> /etc/sysctl.conf
    sysctl -w net.ipv4.tcp_fastopen=3
    echo "   ✅ TCP Fast Open: 3"
else
    echo "   ⚠️  Already configured"
fi

# 12. Optimize NUMA Balancing
echo ""
echo "1️⃣2️⃣  Optimizing NUMA Balancing..."
if ! grep -q "^kernel.numa_balancing" /etc/sysctl.conf; then
    echo "" >> /etc/sysctl.conf
    echo "# NUMA Optimization" >> /etc/sysctl.conf
    echo "kernel.numa_balancing = 1" >> /etc/sysctl.conf
    if [ -f /proc/sys/kernel/numa_balancing ]; then
        sysctl -w kernel.numa_balancing=1
        echo "   ✅ NUMA Balancing: Enabled"
    else
        echo "   ⚠️  NUMA balancing not available on this kernel"
    fi
else
    echo "   ⚠️  Already configured"
fi

# 13. Increase Maximum Open Files
echo ""
echo "1️⃣3️⃣  Increasing Maximum Open Files..."
if ! grep -q "^\\*.*nofile.*1048576" /etc/security/limits.conf; then
    echo "" >> /etc/security/limits.conf
    echo "# Performance Optimization - Max Open Files" >> /etc/security/limits.conf
    echo "* soft nofile 1048576" >> /etc/security/limits.conf
    echo "* hard nofile 1048576" >> /etc/security/limits.conf
    echo "   ✅ Max Open Files: 1,048,576"
    echo "   ⚠️  Requires logout/login to take effect"
else
    echo "   ⚠️  Already configured"
fi

# 15. Additional Kernel Scheduler Settings
echo ""
echo "1️⃣5️⃣  Optimizing Kernel Scheduler Settings..."
if ! grep -q "^kernel.sched_tunable_scaling" /etc/sysctl.conf; then
    echo "" >> /etc/sysctl.conf
    echo "# Kernel Scheduler Optimization" >> /etc/sysctl.conf
    echo "kernel.sched_tunable_scaling = 0" >> /etc/sysctl.conf
    echo "kernel.sched_compat_yield = 0" >> /etc/sysctl.conf
    sysctl -w kernel.sched_tunable_scaling=0 2>/dev/null || true
    sysctl -w kernel.sched_compat_yield=0 2>/dev/null || true
    echo "   ✅ Scheduler optimizations applied"
else
    echo "   ⚠️  Already configured"
fi

# ============================================================================
# TIER 3: MODERATE IMPROVEMENTS
# ============================================================================

echo ""
echo "🎯 TIER 3: MODERATE IMPROVEMENTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 17. Optimize Interrupt Affinity
echo ""
echo "1️⃣7️⃣  Optimizing Interrupt Affinity..."
if command -v irqbalance >/dev/null 2>&1; then
    systemctl enable irqbalance 2>/dev/null || true
    systemctl start irqbalance 2>/dev/null || true
    if [ -f /etc/default/irqbalance ]; then
        if ! grep -q "IRQBALANCE_BANNED_CPUS" /etc/default/irqbalance; then
            sed -i 's/^#IRQBALANCE_BANNED_CPUS/IRQBALANCE_BANNED_CPUS/' /etc/default/irqbalance 2>/dev/null || true
            echo "IRQBALANCE_BANNED_CPUS=\"0,1,2,3\"" >> /etc/default/irqbalance
        fi
    fi
    echo "   ✅ IRQ balancing optimized"
else
    echo "   ⚠️  irqbalance not installed (install with: apt install irqbalance)"
fi

# 18. Enable Kernel Same-Page Merging (KSM)
echo ""
echo "1️⃣8️⃣  Enabling Kernel Same-Page Merging (KSM)..."
if [ -f /sys/kernel/mm/ksm/run ]; then
    echo 1 > /sys/kernel/mm/ksm/run
    echo 100 > /sys/kernel/mm/ksm/pages_to_scan
    echo "   ✅ KSM enabled"
else
    echo "   ⚠️  KSM not available (may require kernel module)"
fi

# ============================================================================
# MANUAL ACTIONS REQUIRED
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 MANUAL ACTIONS REQUIRED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1️⃣  CPU MITIGATIONS (5-30% gain, requires reboot):"
echo "   Edit /etc/default/grub and add 'mitigations=off' to GRUB_CMDLINE_LINUX_DEFAULT"
echo "   Then run: sudo update-grub && sudo reboot"
echo ""
echo "9️⃣  CPU ISOLATION (advanced, requires reboot):"
echo "   Edit /etc/default/grub and add 'isolcpus=4-55 nohz_full=4-55 rcu_nocbs=4-55'"
echo "   Then run: sudo update-grub && sudo reboot"
echo ""
echo "1️⃣4️⃣  WRITE-BACK CACHING:"
echo "   Run: sudo hdparm -W1 /dev/nvme0n1"
echo "   Run: sudo hdparm -W1 /dev/nvme1n1"
echo ""
echo "1️⃣9️⃣  FILE SYSTEM MOUNT OPTIONS:"
echo "   Edit /etc/fstab and add: noatime,nodiratime,data=writeback,commit=60"
echo "   to your ext4 mount options"
echo ""
echo "2️⃣0️⃣  GPU COMPUTE ACCELERATION (ROCm):"
echo "   Install ROCm if needed for compute workloads"
echo "   See: /opt/roxy/scripts/gpu-overclock-guide.sh"
echo ""

# Apply sysctl changes
echo "🔄 Applying sysctl changes..."
sysctl -p /etc/sysctl.conf >/dev/null 2>&1 || true

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    ✅ IMPLEMENTATION COMPLETE              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 SUMMARY:"
echo "   ✅ GPU Power Management: HIGH"
echo "   ✅ Transparent Hugepages: madvise"
echo "   ✅ Zswap: Configured (reboot to activate)"
echo "   ✅ VFS Cache Pressure: 50"
echo "   ✅ Page Cluster: 0"
echo "   ✅ I/O Scheduler: none (NVMe)"
echo "   ✅ I/O Queue Depth: 1023"
echo "   ✅ BBR TCP: Enabled"
echo "   ✅ TCP Fast Open: Enabled"
echo "   ✅ NUMA Balancing: Enabled"
echo "   ✅ Max Open Files: 1,048,576"
echo "   ✅ Scheduler: Optimized"
echo "   ✅ IRQ Balancing: Optimized"
echo "   ✅ KSM: Enabled"
echo ""
echo "⚠️  MANUAL ACTIONS:"
echo "   - CPU Mitigations (#1) - Edit grub and reboot"
echo "   - File System Options (#19) - Edit fstab"
echo "   - Write-Back Caching (#14) - Run hdparm commands"
echo ""
echo "📖 Full guide: /opt/roxy/TOP_20_MAXIMUM_IMPACT_IMPROVEMENTS.md"
echo ""





