#!/bin/bash
# Load OBS settings directly from macOS if accessible
# Or provide instructions for manual export

echo "=== OBS Settings Loader ==="
echo ""

# Check if macOS is accessible via network
MACOS_IP="10.0.0.XX"  # Update if known
echo "Options to load macOS OBS settings:"
echo ""
echo "1. Export from macOS OBS directly:"
echo "   - Open OBS on macOS"
echo "   - File → Scene Collection → Export"
echo "   - Copy exported file to Roxy"
echo "   - Place in: ~/.config/obs-studio/basic/scene_collections/"
echo ""
echo "2. Copy via network (if macOS accessible):"
echo "   scp user@macos-ip:~/Library/Application\ Support/obs-studio/basic/scene_collections/*.json ~/.config/obs-studio/basic/scene_collections/"
echo ""
echo "3. Check exceldro plugin storage:"
echo "   - exceldro may store scene collections in its own directory"
echo "   - Check: ~/Library/Application Support/exceldro/ on macOS"
echo ""
echo "Current Linux OBS scene collections:"
ls -1 ~/.config/obs-studio/basic/scene_collections/ 2>/dev/null || echo "  (none)"
echo ""
echo "Current Linux OBS scenes:"
ls -1 ~/.config/obs-studio/basic/scenes/ 2>/dev/null | head -10
