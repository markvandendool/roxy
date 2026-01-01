#!/bin/bash
# Install Vitals GNOME Extension for Top Bar Monitoring

echo "📊 Installing Vitals Extension for Top Bar..."

# Create extension directory
mkdir -p ~/.local/share/gnome-shell/extensions
cd ~/.local/share/gnome-shell/extensions

# Download Vitals extension
VITALS_UUID="vitals@CoreCoding.com"
if [ ! -d "$VITALS_UUID" ]; then
    echo "Downloading Vitals extension..."
    wget -O vitals.zip "https://extensions.gnome.org/download-extension/vitals@CoreCoding.com.shell-extension.zip?version_tag=latest" 2>/dev/null
    
    if [ -f vitals.zip ]; then
        unzip -q vitals.zip -d "$VITALS_UUID" 2>/dev/null
        rm vitals.zip
        echo "✅ Vitals extension downloaded"
    else
        echo "⚠️  Could not download. Please install manually:"
        echo "   1. Go to: https://extensions.gnome.org/extension/1460/vitals/"
        echo "   2. Click 'Install' in browser"
        echo "   3. Or use: gnome-extensions-app"
        exit 1
    fi
fi

# Enable the extension
echo "Enabling Vitals extension..."
gnome-extensions enable "$VITALS_UUID" 2>&1

# Restart GNOME Shell (or log out/in)
echo ""
echo "✅ Vitals extension installed!"
echo "🔄 Please restart GNOME Shell:"
echo "   Press Alt+F2, type 'r', press Enter"
echo ""
echo "Or configure via: gnome-extensions-app"
