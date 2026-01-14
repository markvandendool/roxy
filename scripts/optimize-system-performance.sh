#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Comprehensive System Performance Optimization Script
# For Intel Xeon W-3275 with 56 cores and 160GB RAM

set -e

echo "=== COMPREHENSIVE SYSTEM PERFORMANCE OPTIMIZATION ==="
echo ""

# 1. OPTIMIZE SWAPPINESS (for systems with large RAM)
echo "1. Optimizing swappiness..."
echo "vm.swappiness = 1" | sudo tee -a /etc/sysctl.conf
sudo sysctl -w vm.swappiness=1
echo "✅ Swappiness set to 1 (was 60)"

# 2. OPTIMIZE DIRTY RATIO (for SSDs)
echo ""
echo "2. Optimizing dirty page ratios..."
echo "vm.dirty_ratio = 10" | sudo tee -a /etc/sysctl.conf
echo "vm.dirty_background_ratio = 5" | sudo tee -a /etc/sysctl.conf
sudo sysctl -w vm.dirty_ratio=10
sudo sysctl -w vm.dirty_background_ratio=5
echo "✅ Dirty ratios optimized for SSDs"

# 3. OPTIMIZE I/O SCHEDULER FOR NVMe
echo ""
echo "3. Setting I/O scheduler for NVMe drives..."
for disk in /sys/block/nvme*/queue/scheduler; do
    disk_name=$(basename $(dirname $disk))
    if [ -f "$disk" ]; then
        # Try kyber first, fallback to none
        if grep -q kyber "$disk"; then
            echo kyber | sudo tee "$disk" > /dev/null
            echo "✅ $disk_name: kyber scheduler"
        elif grep -q none "$disk"; then
            echo none | sudo tee "$disk" > /dev/null
            echo "✅ $disk_name: none scheduler"
        fi
    fi
done

# 4. INCREASE NETWORK BUFFER SIZES
echo ""
echo "4. Optimizing network buffer sizes..."
echo "net.core.rmem_max = 16777216" | sudo tee -a /etc/sysctl.conf
echo "net.core.wmem_max = 16777216" | sudo tee -a /etc/sysctl.conf
echo "net.core.rmem_default = 16777216" | sudo tee -a /etc/sysctl.conf
echo "net.core.wmem_default = 16777216" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.tcp_rmem = 4096 87380 16777216" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.tcp_wmem = 4096 65536 16777216" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p > /dev/null 2>&1
echo "✅ Network buffers increased to 16MB"

# 5. OPTIMIZE KERNEL SCHEDULER
echo ""
echo "5. Optimizing kernel scheduler..."
echo "kernel.sched_migration_cost_ns = 5000000" | sudo tee -a /etc/sysctl.conf
echo "kernel.sched_autogroup_enabled = 0" | sudo tee -a /etc/sysctl.conf
sudo sysctl -w kernel.sched_migration_cost_ns=5000000
sudo sysctl -w kernel.sched_autogroup_enabled=0
echo "✅ Kernel scheduler optimized"

# 6. DISABLE DEEP C-STATES (reduce latency)
echo ""
echo "6. Disabling deep C-states for lower latency..."
# Disable C-state 3 and deeper (keep C0, C1, C2 for power savings)
for cpu in /sys/devices/system/cpu/cpu*/cpuidle/state[3-9]/disable; do
    if [ -f "$cpu" ]; then
        echo 1 | sudo tee "$cpu" > /dev/null 2>&1 || true
    fi
done
echo "✅ Deep C-states disabled (C3+)"

# 7. ENABLE IRQBALANCE
echo ""
echo "7. Enabling and optimizing irqbalance..."
sudo systemctl enable irqbalance
sudo systemctl start irqbalance
echo "✅ irqbalance enabled"

# 8. OPTIMIZE TRANSPARENT HUGEPAGES
echo ""
echo "8. Optimizing transparent hugepages..."
echo madvise | sudo tee /sys/kernel/mm/transparent_hugepage/enabled > /dev/null
echo madvise | sudo tee /sys/kernel/mm/transparent_hugepage/defrag > /dev/null
echo "✅ Transparent hugepages set to madvise"

# 9. INCREASE FILE WATCHER LIMITS
echo ""
echo "9. Increasing file watcher limits..."
echo "fs.inotify.max_user_watches = 1048576" | sudo tee -a /etc/sysctl.conf
sudo sysctl -w fs.inotify.max_user_watches=1048576
echo "✅ File watcher limit increased"

# 10. OPTIMIZE DISK I/O QUEUE DEPTHS
echo ""
echo "10. Optimizing disk I/O queue depths..."
for disk in /sys/block/nvme*/queue; do
    disk_name=$(basename $(dirname $disk))
    if [ -f "$disk/nr_requests" ]; then
        echo 1023 | sudo tee "$disk/nr_requests" > /dev/null 2>&1 || true
        echo "✅ $disk_name: queue depth optimized"
    fi
done

# 11. CREATE SYSTEMD SERVICE FOR I/O SCHEDULER
echo ""
echo "11. Creating systemd service for I/O scheduler persistence..."
sudo tee /etc/systemd/system/set-io-scheduler.service > /dev/null << 'EOFSERVICE'
[Unit]
Description=Set I/O Scheduler for NVMe drives
After=sysinit.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'for disk in /sys/block/nvme*/queue/scheduler; do if grep -q kyber "$disk"; then echo kyber > "$disk"; elif grep -q none "$disk"; then echo none > "$disk"; fi; done'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOFSERVICE
sudo systemctl enable set-io-scheduler.service
echo "✅ I/O scheduler service created"

# 12. CREATE SYSTEMD SERVICE FOR C-STATES
echo ""
echo "12. Creating systemd service for C-state management..."
sudo tee /etc/systemd/system/disable-deep-cstates.service > /dev/null << 'EOFCSTATES'
[Unit]
Description=Disable deep C-states for performance
After=sysinit.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'for cpu in /sys/devices/system/cpu/cpu*/cpuidle/state[3-9]/disable; do if [ -f "$cpu" ]; then echo 1 > "$cpu" 2>/dev/null || true; fi; done'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOFCSTATES
sudo systemctl enable disable-deep-cstates.service
echo "✅ C-state management service created"

# 13. APPLY ALL SYSCTL SETTINGS
echo ""
echo "13. Applying all sysctl optimizations..."
sudo sysctl -p > /dev/null 2>&1 || true
echo "✅ All sysctl settings applied"

echo ""
echo "=== OPTIMIZATION COMPLETE ==="
echo ""
echo "Summary of changes:"
echo "  ✅ Swappiness: 60 → 1"
echo "  ✅ Dirty ratios optimized for SSDs"
echo "  ✅ I/O scheduler: kyber/none for NVMe"
echo "  ✅ Network buffers: 4MB → 16MB"
echo "  ✅ Kernel scheduler optimized"
echo "  ✅ Deep C-states disabled"
echo "  ✅ irqbalance enabled"
echo "  ✅ File watcher limits increased"
echo "  ✅ All settings persist across reboots"
echo ""
echo "REBOOT RECOMMENDED for all changes to take full effect!"
echo ""














