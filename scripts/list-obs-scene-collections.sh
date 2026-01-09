#!/bin/bash
# List all OBS scene collections from macOS backup and current Linux OBS

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        OBS Scene Collection Finder                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

BACKUP_PATH="/mnt/macos/root/2025-12-22-051539.interrupted"
OBS_CONFIG_LINUX="$HOME/.config/obs-studio"

# 1. Check current Linux OBS scene collections
echo "[1/3] Current Linux OBS Scene Collections:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -d "$OBS_CONFIG_LINUX/basic/scene_collections" ]; then
    echo "Scene Collections:"
    ls -1 "$OBS_CONFIG_LINUX/basic/scene_collections/" 2>/dev/null | while read collection; do
        echo "  - $collection"
    done
else
    echo "  No scene collections directory found"
fi

if [ -d "$OBS_CONFIG_LINUX/basic/scenes" ]; then
    echo ""
    echo "Scenes:"
    ls -1 "$OBS_CONFIG_LINUX/basic/scenes/" 2>/dev/null | head -10
fi

# 2. Check macOS backup - all possible locations
echo ""
echo "[2/3] macOS Backup Scene Collections:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Try multiple possible paths
POSSIBLE_PATHS=(
    "$BACKUP_PATH/Mark's Mac Pro - Data/Users/mark/Library/Application Support/obs-studio/basic/scene_collections"
    "$BACKUP_PATH/Mark's Mac Pro - Data/Users/mark/Library/Application Support/obs-studio/basic/scenes"
    "$BACKUP_PATH/Mark's Mac Pro - Data/Library/Application Support/obs-studio/basic/scene_collections"
    "$BACKUP_PATH/Mark's Mac Pro - Data/Library/Application Support/obs-studio/basic/scenes"
)

for path in "${POSSIBLE_PATHS[@]}"; do
    if [ -d "$path" ]; then
        echo "Found: $path"
        ls -la "$path" 2>/dev/null | head -20
        echo ""
    fi
done

# 3. Search for "Harry Elgato" specifically
echo ""
echo "[3/3] Searching for 'Harry Elgato' Scene Collection:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
find "$BACKUP_PATH" -path '*obs-studio*' -type f \( -name '*.json' -o -name '*.ini' \) 2>/dev/null | \
    xargs grep -l -i 'harry.*elgato\|elgato.*harry\|harry.*fall' 2>/dev/null | \
    head -10 | while read file; do
        echo "Found reference in: $file"
        grep -i 'harry\|elgato\|fall' "$file" 2>/dev/null | head -3
        echo ""
    done

# 4. List all scene collection files in backup
echo ""
echo "All Scene Collection Files in Backup:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
find "$BACKUP_PATH" -path '*obs-studio*basic*' -name '*.json' 2>/dev/null | \
    grep -vE 'plugin|log|error|sentry|temp|profile' | \
    head -20 | while read file; do
        echo "  $(basename $(dirname $file))/$(basename $file)"
    done

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Search Complete                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"

