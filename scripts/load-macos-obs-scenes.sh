#!/bin/bash
# Load macOS OBS scene collection from Time Machine backup

set -e

BACKUP_PATH="/mnt/macos/root/2025-12-22-051539.interrupted"
OBS_CONFIG_SOURCE="${BACKUP_PATH}/Users/mark/Library/Application Support/obs-studio"
OBS_CONFIG_DEST="$HOME/.config/obs-studio"

echo "=== Loading macOS OBS Scene Collection ==="
echo ""

# Find scene collections
echo "[1/4] Searching for scene collections..."
SCENE_COLLECTIONS=$(find "$OBS_CONFIG_SOURCE" -path "*/basic/scenes/*.json" -o -path "*/basic/scene_collections/*.json" 2>/dev/null | head -10)

if [ -z "$SCENE_COLLECTIONS" ]; then
    echo "⚠️  No scene collections found in backup"
    echo "   Searching alternative locations..."
    SCENE_COLLECTIONS=$(find "$BACKUP_PATH" -path "*obs-studio*" -name "*.json" 2>/dev/null | head -10)
fi

if [ -z "$SCENE_COLLECTIONS" ]; then
    echo "❌ No scene collections found"
    exit 1
fi

echo "Found scene collections:"
echo "$SCENE_COLLECTIONS" | while read collection; do
    echo "  - $collection"
done
echo ""

# Look for "Harry Elgato" or similar
echo "[2/4] Looking for 'Harry Elgato' scene collection..."
HARRY_COLLECTION=$(find "$OBS_CONFIG_SOURCE" -iname "*harry*" -o -iname "*elgato*" 2>/dev/null | grep -iE 'scene|collection|json' | head -1)

if [ -z "$HARRY_COLLECTION" ]; then
    echo "⚠️  'Harry Elgato' not found, using most recent collection"
    HARRY_COLLECTION=$(find "$OBS_CONFIG_SOURCE" -path "*scene*" -name "*.json" 2>/dev/null | head -1)
fi

if [ -z "$HARRY_COLLECTION" ]; then
    echo "❌ No scene collections found"
    exit 1
fi

echo "✅ Found: $HARRY_COLLECTION"
echo ""

# Copy scene collection
echo "[3/4] Copying scene collection..."
mkdir -p "$OBS_CONFIG_DEST/basic/scene_collections"
mkdir -p "$OBS_CONFIG_DEST/basic/scenes"

# Get collection name
COLLECTION_NAME=$(basename "$HARRY_COLLECTION" .json)
echo "Collection name: $COLLECTION_NAME"

# Copy the collection file
cp "$HARRY_COLLECTION" "$OBS_CONFIG_DEST/basic/scene_collections/${COLLECTION_NAME}.json" 2>/dev/null || \
cp "$HARRY_COLLECTION" "$OBS_CONFIG_DEST/basic/scenes/${COLLECTION_NAME}.json" 2>/dev/null || \
echo "⚠️  Could not copy collection file"

# Copy related scene files
SCENE_DIR=$(dirname "$HARRY_COLLECTION")
if [ -d "$SCENE_DIR" ]; then
    echo "Copying scene files from: $SCENE_DIR"
    cp -r "$SCENE_DIR"/* "$OBS_CONFIG_DEST/basic/scenes/" 2>/dev/null || true
fi

echo "✅ Scene collection copied"
echo ""

# Update OBS global.ini to use this collection
echo "[4/4] Setting as default scene collection..."
GLOBAL_INI="$OBS_CONFIG_DEST/global.ini"
if [ -f "$GLOBAL_INI" ]; then
    # Backup
    cp "$GLOBAL_INI" "$GLOBAL_INI.backup"
    
    # Update collection name
    sed -i "s/^CurrentSceneCollection=.*/CurrentSceneCollection=$COLLECTION_NAME/" "$GLOBAL_INI" || \
    echo "CurrentSceneCollection=$COLLECTION_NAME" >> "$GLOBAL_INI"
    
    echo "✅ Set as default collection"
else
    echo "⚠️  global.ini not found, creating..."
    mkdir -p "$OBS_CONFIG_DEST"
    echo "[General]" > "$GLOBAL_INI"
    echo "CurrentSceneCollection=$COLLECTION_NAME" >> "$GLOBAL_INI"
fi

echo ""
echo "=== Complete ==="
echo ""
echo "Scene collection loaded: $COLLECTION_NAME"
echo "Location: $OBS_CONFIG_DEST/basic/scene_collections/"
echo ""
echo "To use:"
echo "1. Start OBS: obs"
echo "2. Scene collection should load automatically"
echo "3. Or: File → Scene Collection → $COLLECTION_NAME"

