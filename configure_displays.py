#!/usr/bin/env python3
"""
JARVIS-1 Display Configuration
Configures optimal display settings for the triple-monitor setup

Part of LUNA-000 CITADEL
"""

import subprocess
import json

# Display configuration
DISPLAYS = {
    'DP-5': {
        'name': 'Samsung U32R59x',
        'mode': '3840x2160@60.000',
        'scale': 2.0,
        'primary': True,
        'position': (0, 0)
    },
    'DP-6': {
        'name': 'TCL 43S425CA',
        'mode': '3840x2160@60.000',  # Upgrade from 30Hz to 60Hz!
        'scale': 2.0,
        'primary': False,
        'position': (1920, 0)  # Logical position (after scaling)
    },
    'HDMI-1': {
        'name': 'RCA TV',
        'mode': '3840x2160@60.000',  # Upgrade from 30Hz to 60Hz!
        'scale': 2.0,
        'primary': False,
        'position': (3840, 0)  # Logical position
    }
}

def get_gnome_display_state():
    """Get current display configuration from GNOME"""
    cmd = [
        'gdbus', 'call', '--session',
        '--dest', 'org.gnome.Mutter.DisplayConfig',
        '--object-path', '/org/gnome/Mutter/DisplayConfig',
        '--method', 'org.gnome.Mutter.DisplayConfig.GetCurrentState'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, 
                           env={'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/run/user/1000/bus'})
    return result.stdout

def show_current_status():
    """Display current monitor status"""
    print("=" * 60)
    print("  JARVIS-1 Display Status")
    print("=" * 60)
    
    state = get_gnome_display_state()
    
    for connector, config in DISPLAYS.items():
        # Parse state to find current mode
        if f"'{connector}'" in state:
            if "is-current': <true>" in state.split(connector)[1][:2000]:
                current_mode = "Active"
            else:
                current_mode = "Unknown"
        else:
            current_mode = "Not found"
        
        primary = " (PRIMARY)" if config['primary'] else ""
        print(f"\n{connector}: {config['name']}{primary}")
        print(f"  Target: {config['mode']} @ {config['scale']}x scale")
        print(f"  Position: {config['position']}")

def print_instructions():
    """Print manual configuration instructions"""
    print("\n" + "=" * 60)
    print("  CONFIGURATION INSTRUCTIONS")
    print("=" * 60)
    print("""
To optimize your displays:

1. Open GNOME Settings → Displays
2. For each monitor:
   - Set Resolution to 3840 × 2160 (4K)
   - Set Refresh Rate to 60 Hz
   - Set Scale to 200%

3. Arrange monitors: LEFT ─ CENTER (Primary) ─ RIGHT

4. Apply and Keep Changes

PHYSICAL RECOMMENDATION:
========================
Move the RCA TV's HDMI cable from RX 6900 XT to W5700X:
- Use a DP port on the W5700X (DP-1 through DP-4 available)
- This frees RX 6900 XT for 100% AI compute

W5700X has 6 DP ports, currently only 2 used.
""")

def main():
    show_current_status()
    print_instructions()

if __name__ == '__main__':
    main()
