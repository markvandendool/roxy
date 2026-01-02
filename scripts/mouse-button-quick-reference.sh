#!/bin/bash
# Quick reference for mouse button programming commands

cat << 'EOF'
🖱️  MOUSE BUTTON PROGRAMMING - QUICK REFERENCE
==============================================

📋 LAUNCH CONFIGURATION TOOLS
──────────────────────────────
input-remapper-control    # Input Remapper GUI (recommended)
piper                     # Piper GUI (for hardware features)

🔍 IDENTIFY BUTTONS
───────────────────
sudo evtest              # Test which button numbers correspond to physical buttons
ratbagctl list           # List devices detected by libratbag
ratbagctl <device> info  # Get detailed info about your mouse

⚙️  SERVICE MANAGEMENT
───────────────────────
# Input Remapper
sudo systemctl status input-remapper
sudo systemctl restart input-remapper

# ratbagd (Piper)
systemctl --user status ratbagd
systemctl --user restart ratbagd

📖 DOCUMENTATION
────────────────
cat /opt/roxy/LOGITECH_MOUSE_SETUP.md  # Full guide

🎯 COMMON BUTTON MAPPINGS
─────────────────────────
Button 4 → Ctrl+C (Copy)
Button 5 → Ctrl+V (Paste)
Button 6 → Super+Tab (Window switcher)
Button 7 → gnome-terminal (Open terminal)

💡 TIPS
───────
• Use Input Remapper for software-level remapping (macros, commands)
• Use Piper for hardware-level settings (DPI, LED, profiles)
• Both can work together for maximum flexibility
• Settings persist after reboot

EOF



