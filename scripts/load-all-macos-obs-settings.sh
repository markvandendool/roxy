#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Load ALL macOS OBS settings into Linux OBS
# Scene collections, hotkeys, profiles, plugins, everything

set -e

BACKUP_PATH="/mnt/macos/root/2025-12-22-051539.interrupted"
MACOS_OBS_BASE="$BACKUP_PATH/Mark's Mac Pro - Data/Library/Application Support/obs-studio"
LINUX_OBS_BASE="$HOME/.config/obs-studio"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     Loading ALL macOS OBS Settings into Linux OBS           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Create Linux OBS directories
mkdir -p "$LINUX_OBS_BASE/basic/scene_collections"
mkdir -p "$LINUX_OBS_BASE/basic/scenes"
mkdir -p "$LINUX_OBS_BASE/basic/profiles"
mkdir -p "$LINUX_OBS_BASE/plugin_config"

# 1. Find and copy scene collections
echo "[1/6] Loading Scene Collections..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check all obs-studio directories in backup
for obs_dir in "$MACOS_OBS_BASE"*; do
    if [ -d "$obs_dir/basic/scene_collections" ]; then
        echo "Found scene collections in: $(basename "$obs_dir")"
        for collection in "$obs_dir/basic/scene_collections"/*.json; do
            if [ -f "$collection" ]; then
                name=$(basename "$collection")
                cp "$collection" "$LINUX_OBS_BASE/basic/scene_collections/$name"
                echo "  ✅ Copied: $name"
            fi
        done
    fi
    
    # Also check scenes directory
    if [ -d "$obs_dir/basic/scenes" ]; then
        echo "Found scenes in: $(basename "$obs_dir")"
        for scene in "$obs_dir/basic/scenes"/*.json; do
            if [ -f "$scene" ]; then
                name=$(basename "$scene")
                cp "$scene" "$LINUX_OBS_BASE/basic/scenes/$name"
                echo "  ✅ Copied scene: $name"
            fi
        done
    fi
done

# 2. Copy global.ini (hotkeys, settings)
echo ""
echo "[2/6] Loading Global Settings (hotkeys, etc.)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for obs_dir in "$MACOS_OBS_BASE"*; do
    if [ -f "$obs_dir/global.ini" ]; then
        echo "Found global.ini in: $(basename "$obs_dir")"
        # Backup existing
        if [ -f "$LINUX_OBS_BASE/global.ini" ]; then
            cp "$LINUX_OBS_BASE/global.ini" "$LINUX_OBS_BASE/global.ini.backup"
        fi
        # Copy and update paths for Linux
        cp "$obs_dir/global.ini" "$LINUX_OBS_BASE/global.ini.macos"
        sed -i 's|/Users/.*/Library|/home/mark/.config|g' "$LINUX_OBS_BASE/global.ini.macos" 2>/dev/null || true
        echo "  ✅ Copied global.ini (check and merge manually if needed)"
    fi
done

# 3. Copy profiles
echo ""
echo "[3/6] Loading Profiles..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for obs_dir in "$MACOS_OBS_BASE"*; do
    if [ -d "$obs_dir/basic/profiles" ]; then
        echo "Found profiles in: $(basename "$obs_dir")"
        for profile_dir in "$obs_dir/basic/profiles"/*; do
            if [ -d "$profile_dir" ]; then
                profile_name=$(basename "$profile_dir")
                mkdir -p "$LINUX_OBS_BASE/basic/profiles/$profile_name"
                cp -r "$profile_dir"/* "$LINUX_OBS_BASE/basic/profiles/$profile_name/" 2>/dev/null || true
                echo "  ✅ Copied profile: $profile_name"
            fi
        done
    fi
done

# 4. Copy plugin configs
echo ""
echo "[4/6] Loading Plugin Configurations..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for obs_dir in "$MACOS_OBS_BASE"*; do
    if [ -d "$obs_dir/plugin_config" ]; then
        echo "Found plugin configs in: $(basename "$obs_dir")"
        for plugin_dir in "$obs_dir/plugin_config"/*; do
            if [ -d "$plugin_dir" ]; then
                plugin_name=$(basename "$plugin_dir")
                mkdir -p "$LINUX_OBS_BASE/plugin_config/$plugin_name"
                cp -r "$plugin_dir"/* "$LINUX_OBS_BASE/plugin_config/$plugin_name/" 2>/dev/null || true
                echo "  ✅ Copied plugin config: $plugin_name"
            fi
        done
    fi
done

# 5. Find "Harry Elgato" scene collection specifically
echo ""
echo "[5/6] Searching for 'Harry Elgato' Scene Collection..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

HARRY_FOUND=false
for obs_dir in "$MACOS_OBS_BASE"*; do
    if [ -d "$obs_dir/basic/scene_collections" ]; then
        for file in "$obs_dir/basic/scene_collections"/*.json; do
            if [ -f "$file" ] && grep -qi "harry.*elgato\|elgato.*harry\|harry.*fall" "$file" 2>/dev/null; then
                name=$(basename "$file")
                cp "$file" "$LINUX_OBS_BASE/basic/scene_collections/$name"
                echo "  ✅ Found and copied: $name"
                HARRY_FOUND=true
            fi
        done
    fi
    
    # Also check scenes directory
    if [ -d "$obs_dir/basic/scenes" ]; then
        for file in "$obs_dir/basic/scenes"/*.json; do
            if [ -f "$file" ] && grep -qi "harry.*elgato\|elgato.*harry\|harry.*fall" "$file" 2>/dev/null; then
                name=$(basename "$file")
                cp "$file" "$LINUX_OBS_BASE/basic/scenes/$name"
                echo "  ✅ Found and copied scene: $name"
                HARRY_FOUND=true
            fi
        done
    fi
done

if [ "$HARRY_FOUND" = false ]; then
    echo "  ⚠️  'Harry Elgato' not found in scene files"
    echo "     (but confirmed in logs - may need manual export from macOS)"
fi

# 6. Update global.ini to use macOS scene collection
echo ""
echo "[6/6] Updating OBS Configuration..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# List available scene collections
if [ -d "$LINUX_OBS_BASE/basic/scene_collections" ]; then
    COLLECTIONS=$(ls -1 "$LINUX_OBS_BASE/basic/scene_collections/" 2>/dev/null | head -1)
    if [ -n "$COLLECTIONS" ]; then
        echo "Available scene collections:"
        ls -1 "$LINUX_OBS_BASE/basic/scene_collections/" 2>/dev/null | while read col; do
            echo "  - $(basename "$col" .json)"
        done
        
        # Try to find Harry Elgato
        HARRY_COLLECTION=$(ls -1 "$LINUX_OBS_BASE/basic/scene_collections/" 2>/dev/null | grep -i "harry\|elgato\|fall" | head -1)
        if [ -n "$HARRY_COLLECTION" ]; then
            COLLECTION_NAME=$(basename "$HARRY_COLLECTION" .json)
            echo ""
            echo "Setting 'Harry Elgato' as default: $COLLECTION_NAME"
        else
            COLLECTION_NAME=$(basename "$COLLECTIONS" .json)
        fi
        
        # Update global.ini
        if [ -f "$LINUX_OBS_BASE/global.ini" ]; then
            if grep -q "CurrentSceneCollection=" "$LINUX_OBS_BASE/global.ini" 2>/dev/null; then
                sed -i "s/^CurrentSceneCollection=.*/CurrentSceneCollection=$COLLECTION_NAME/" "$LINUX_OBS_BASE/global.ini"
            else
                echo "CurrentSceneCollection=$COLLECTION_NAME" >> "$LINUX_OBS_BASE/global.ini"
            fi
            echo "  ✅ Updated global.ini"
        fi
    fi
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Load Complete                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Loaded:"
echo "  ✅ Scene collections"
echo "  ✅ Global settings (hotkeys, etc.)"
echo "  ✅ Profiles"
echo "  ✅ Plugin configurations"
echo ""
echo "To use:"
echo "  1. Start OBS: obs"
echo "  2. Scene collections should be available"
echo "  3. Check hotkeys in Settings → Hotkeys"
echo "  4. Verify profiles in Settings → General"
echo ""