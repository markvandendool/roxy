# 📱 iPhone Remote Desktop Setup Guide

This guide will help you access and control your ROXY system from your iPhone using VNC.

## Quick Setup

Run the setup script:

```bash
cd /opt/roxy
./scripts/setup-iphone-vnc.sh
```

The script will:
1. ✅ Verify wayvnc is installed
2. ✅ Set up password authentication
3. ✅ Create and enable systemd service
4. ✅ Start the VNC server

## Connection Details

After setup, you'll need:
- **Server IP**: Your system's IP address (shown during setup)
- **Port**: `5900`
- **Password**: The password you set during setup

## iPhone Apps

### Recommended: VNC Viewer (Free)
1. Install **VNC Viewer** from the App Store (by RealVNC)
2. Open the app
3. Tap the **+** button
4. Enter:
   - **Address**: `YOUR_IP:5900` (e.g., `10.0.0.99:5900`)
   - **Name**: ROXY (or any name you prefer)
5. Tap **Create**
6. Tap the connection to connect
7. Enter your password when prompted

### Alternative Apps
- **Jump Desktop** - Paid, excellent performance and features
- **Screens** - Paid, great for multiple connections
- **Mocha VNC** - Free alternative

## Service Management

### Start/Stop VNC Server

```bash
# Start
systemctl --user start wayvnc

# Stop
systemctl --user stop wayvnc

# Restart
systemctl --user restart wayvnc

# Check status
systemctl --user status wayvnc

# View logs
journalctl --user -u wayvnc -f
```

### Auto-Start on Login

The service is automatically enabled and will start when you log in. To disable:

```bash
systemctl --user disable wayvnc
```

## Troubleshooting

### Can't Connect from iPhone

1. **Check if service is running:**
   ```bash
   systemctl --user status wayvnc
   ```

2. **Check firewall:**
   ```bash
   sudo ufw status
   sudo ufw allow 5900/tcp
   ```

3. **Verify IP address:**
   ```bash
   ip addr show | grep -E "inet " | grep -v "127.0.0.1"
   ```

4. **Check if port is listening:**
   ```bash
   netstat -tlnp | grep 5900
   # or
   ss -tlnp | grep 5900
   ```

5. **View service logs:**
   ```bash
   journalctl --user -u wayvnc -n 50
   ```

### Performance Issues

- **Reduce color depth** in your VNC client app settings
- **Lower resolution** if connection is slow
- **Use WiFi** instead of cellular for better performance
- **Close other apps** on iPhone to free up resources

### Change Password

1. Stop the service:
   ```bash
   systemctl --user stop wayvnc
   ```

2. Edit the config file:
   ```bash
   nano ~/.config/wayvnc/config
   # Change the password= line to your new password
   # Example: password=mynewpassword123
   ```

3. Restart service:
   ```bash
   systemctl --user start wayvnc
   ```

## Security Considerations

1. **Use a strong password** (at least 8 characters, mix of letters, numbers, symbols)
2. **Only enable VNC when needed** - you can stop the service when not in use
3. **Use VPN** for remote access outside your local network
4. **Firewall** - Consider restricting access to specific IPs if possible

## Advanced Configuration

### Change Port

Edit the service file:
```bash
nano ~/.config/systemd/user/wayvnc.service
```

Change the port in the ExecStart line:
```
ExecStart=/usr/bin/wayvnc --output=DP-1 --address=0.0.0.0 --port=5901
```

Then reload and restart:
```bash
systemctl --user daemon-reload
systemctl --user restart wayvnc
```

### Multiple Displays

If you have multiple displays, you can specify which one:
```bash
# List available outputs
swaymsg -t get_outputs

# Edit service to use specific output
nano ~/.config/systemd/user/wayvnc.service
# Change --output=DP-1 to your desired output
```

## Tips for iPhone Usage

1. **Use landscape mode** for better desktop view
2. **Pinch to zoom** to see details
3. **Two-finger scroll** for mouse wheel
4. **Long press** for right-click
5. **Keyboard shortcuts** work through the on-screen keyboard
6. **Copy/paste** works between iPhone and desktop

## Alternative: SSH + Terminal

If you only need command-line access, you can use SSH:

1. Install **Termius** or **Blink Shell** on iPhone
2. Connect via SSH:
   ```bash
   ssh username@YOUR_IP
   ```

This gives you terminal access but not visual desktop control.

