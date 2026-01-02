# 📱 iPhone Remote Desktop Setup - GNOME Remote Desktop (RDP)

## ✅ Current Status
- RDP is **enabled** and service is **running**
- Your system IP: **10.0.0.99**
- Port: **3390**
- Remote control is enabled (not view-only)

## 📍 Where to Find Remote Desktop Settings

**In GNOME 46+ (Ubuntu 24.04):**
Remote Desktop is in the **System** section, NOT Sharing!

### Step-by-Step:
1. Open **Settings** (Super key → type "Settings")
2. Look in the left sidebar for **"System"** (not Sharing)
3. Click **"System"**
4. Scroll down to find **"Remote Desktop"**
5. Click on **"Remote Desktop"**

### If You Don't See It:
Try searching in Settings:
- Press **Super key** → type **"Remote Desktop"**
- It should show up in the search results

## 🔐 Setting the Password

Once you're in Remote Desktop settings:
1. Toggle **"Remote Desktop"** to **ON** (if not already)
2. Click **"Set Password"** or **"Authentication"**
3. Enter password: **marknikkisixx** (or your choice)
4. Confirm the password
5. **Done!**

## 📱 iPhone Connection

### App to Use
Install **Microsoft Remote Desktop** from the App Store (free)

### Connection Details
- **Server**: `10.0.0.99:3390`
- **Username**: `mark`
- **Password**: (what you set in Settings)

### Connection Steps
1. Open Microsoft Remote Desktop app
2. Tap **+** (Add PC)
3. Enter:
   - **PC name**: `10.0.0.99:3390`
   - **User account**: `mark`
4. Tap **Save**
5. Tap the connection to connect
6. Enter password when prompted

## Alternative iPhone Apps
- **Jump Desktop** - Excellent RDP client (paid, highly recommended)
- **Screens** - Great RDP/VNC client (paid)

## Multi-Monitor Display

Your system has **3 monitors**:
- **DP-5**: Center (Primary) - 1920x1080
- **DP-3**: Left - 1920x1080  
- **DP-6**: Right - 1920x1080

**Display Mode**: Set to **"extend"** - This shows all 3 displays in one view (like Mocha VNC)

**IMPORTANT**: This setting only affects what you see over RDP. It does NOT change your physical display arrangement or resolution.

To change display mode:
- Go to **Settings → System → Remote Desktop**
- Look for **"Screen Share Mode"** or similar option
- Options: `mirror-primary` (single display) or `extend` (all displays)

## After You Set the Password

Once you've set the password in Settings → System → Remote Desktop, let me know and I can:
- Verify the connection is working
- Test the port
- Help troubleshoot if needed

## Troubleshooting

**Can't find Remote Desktop in System section?**
```bash
# Check if it's enabled
gsettings get org.gnome.desktop.remote-desktop.rdp enable
# Should show: true
```

**Service not running?**
```bash
systemctl --user restart gnome-remote-desktop.service
systemctl --user status gnome-remote-desktop.service
```

**Check if port is listening:**
```bash
ss -tlnp | grep 3390
```
