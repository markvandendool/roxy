#!/bin/bash
# Complete search for macOS OBS scene collections in Time Machine backup

BACKUP="/mnt/macos/root/2025-12-22-051539.interrupted"
OBS_BASE="$BACKUP/Mark's Mac Pro - Data/Library/Application Support/obs-studio"

echo "=== Complete OBS Scene Collection Search ==="
echo ""

# 1. Check all obs-studio directories
echo "[1] Checking all obs-studio directories..."
find "$BACKUP" -type d -name 'obs-studio*' 2>/dev/null | while read dir; do
    echo "  Checking: $(basename $dir)"
    if [ -d "$dir/basic/scene_collections" ]; then
        echo "    ✅ Found scene_collections:"
        ls -1 "$dir/basic/scene_collections/" 2>/dev/null | head -10
    fi
    if [ -d "$dir/basic/scenes" ]; then
        echo "    ✅ Found scenes:"
        ls -1 "$dir/basic/scenes/" 2>/dev/null | head -10
    fi
done

# 2. Search for "Harry Elgato" in all files
echo ""
echo "[2] Searching for 'Harry Elgato' references..."
grep -r -i 'harry.*elgato\|elgato.*harry\|harry.*fall' "$OBS_BASE" 2>/dev/null | head -10

# 3. List all JSON files that might be scene collections
echo ""
echo "[3] All JSON files in OBS directories..."
find "$BACKUP" -path '*obs-studio*' -name '*.json' 2>/dev/null | \
    grep -vE 'plugin|log|error|sentry|temp|profile|deps' | \
    head -20

# 4. Check for exceldro plugin
echo ""
echo "[4] Checking for exceldro/scene collection manager plugin..."
find "$OBS_BASE/plugins" -type d -iname '*excel*' -o -iname '*collection*manager*' 2>/dev/null

echo ""
echo "=== Search Complete ==="

