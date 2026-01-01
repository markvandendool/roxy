#!/bin/bash

# 🚀 SAFE MITIGATION DISABLING - MAXIMUM PERFORMANCE IMPACT
# Mac Pro 2019 - Workstation Optimization
# WARNING: Only for trusted environments!

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   DISABLE CPU MITIGATIONS - MAXIMUM PERFORMANCE IMPACT    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (sudo)"
    exit 1
fi

echo "⚠️  WARNING: Disabling CPU mitigations reduces security!"
echo "   Only proceed if:"
echo "   - System runs only trusted code"
echo "   - System is isolated from untrusted networks"
echo "   - You understand the security implications"
echo ""
read -p "Continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

# Backup existing grub config
echo "📦 Creating backup..."
cp /etc/default/grub /etc/default/grub.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Backup created"
echo ""

# Read current grub config
GRUB_FILE="/etc/default/grub"
GRUB_CMDLINE=$(grep "^GRUB_CMDLINE_LINUX_DEFAULT" "$GRUB_FILE" | cut -d'"' -f2)

echo "📊 CURRENT BOOT PARAMETERS:"
echo "   $GRUB_CMDLINE"
echo ""

# Option selection
echo "Select mitigation disabling strategy:"
echo ""
echo "1. MAXIMUM IMPACT - Disable ALL mitigations (5-30% gain)"
echo "   → mitigations=off"
echo "   → Risk: HIGH (disables all protections)"
echo ""
echo "2. HIGH IMPACT - Disable high-impact mitigations only (8-20% gain)"
echo "   → spectre_v2=off retbleed=off"
echo "   → Risk: MEDIUM (disables Spectre V2 + Retbleed)"
echo ""
echo "3. SELECTIVE - Disable specific mitigations (custom)"
echo "   → Choose individual mitigations"
echo ""
read -p "Select option (1/2/3): " option

case $option in
    1)
        echo ""
        echo "🔥 OPTION 1: MAXIMUM IMPACT - Disable ALL mitigations"
        NEW_CMDLINE="$GRUB_CMDLINE mitigations=off"
        echo "   → Expected gain: 5-30% CPU performance"
        echo "   → Risk: HIGH - All protections disabled"
        ;;
    2)
        echo ""
        echo "⚡ OPTION 2: HIGH IMPACT - Disable Spectre V2 + Retbleed"
        NEW_CMDLINE="$GRUB_CMDLINE spectre_v2=off retbleed=off"
        echo "   → Expected gain: 8-20% CPU performance"
        echo "   → Risk: MEDIUM - Disables highest-impact mitigations"
        ;;
    3)
        echo ""
        echo "🎯 OPTION 3: SELECTIVE DISABLING"
        echo ""
        echo "Available mitigations to disable:"
        echo "  a) spectre_v2=off (5-15% gain, medium risk)"
        echo "  b) retbleed=off (3-8% gain, medium risk)"
        echo "  c) spectre_v1=off (1-3% gain, low-medium risk)"
        echo "  d) mmio_stale_data=off (1-2% gain, low risk)"
        echo "  e) spec_store_bypass_disable=off (1-2% gain, low risk)"
        echo ""
        read -p "Enter letters (e.g., 'ab' for a+b): " selections
        
        NEW_CMDLINE="$GRUB_CMDLINE"
        for char in $(echo $selections | fold -w1); do
            case $char in
                a) NEW_CMDLINE="$NEW_CMDLINE spectre_v2=off"; echo "   ✅ Added: spectre_v2=off"; ;;
                b) NEW_CMDLINE="$NEW_CMDLINE retbleed=off"; echo "   ✅ Added: retbleed=off"; ;;
                c) NEW_CMDLINE="$NEW_CMDLINE spectre_v1=off"; echo "   ✅ Added: spectre_v1=off"; ;;
                d) NEW_CMDLINE="$NEW_CMDLINE mmio_stale_data=off"; echo "   ✅ Added: mmio_stale_data=off"; ;;
                e) NEW_CMDLINE="$NEW_CMDLINE spec_store_bypass_disable=off"; echo "   ✅ Added: spec_store_bypass_disable=off"; ;;
                *) echo "   ⚠️  Invalid option: $char"; ;;
            esac
        done
        ;;
    *)
        echo "Invalid option. Aborted."
        exit 1
        ;;
esac

echo ""
echo "📝 NEW BOOT PARAMETERS:"
echo "   $NEW_CMDLINE"
echo ""

# Update grub config
sed -i "s|^GRUB_CMDLINE_LINUX_DEFAULT=.*|GRUB_CMDLINE_LINUX_DEFAULT=\"$NEW_CMDLINE\"|" "$GRUB_FILE"

echo "✅ GRUB configuration updated"
echo ""

# Update grub
echo "🔄 Updating GRUB..."
update-grub

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    ✅ CONFIGURATION COMPLETE              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 SUMMARY:"
echo "   ✅ CPU mitigations disabled in GRUB"
echo "   ✅ GRUB updated"
echo ""
echo "⚠️  IMPORTANT:"
echo "   - Changes will take effect after REBOOT"
echo "   - Security protections are REDUCED"
echo "   - Only use in trusted environments"
echo ""
echo "🔄 TO APPLY:"
echo "   sudo reboot"
echo ""
echo "📖 To revert:"
echo "   Restore from backup: /etc/default/grub.backup.*"
echo "   Or edit: /etc/default/grub"
echo ""













