#!/bin/bash

# Run Superposition on RX 6900 XT (force GPU selection)

SUPER_DIR="$HOME/superposition"

if [ ! -d "$SUPER_DIR" ]; then
    echo "❌ Superposition not found at $SUPER_DIR"
    exit 1
fi

cd "$SUPER_DIR"

# Force RX 6900 XT (card2, which is DRI_PRIME=1)
export DRI_PRIME=1
export MESA_LOADER_DRIVER_OVERRIDE=radeonsi

echo "🚀 Launching Superposition on RX 6900 XT..."
echo "   DRI_PRIME=1 (using second GPU - RX 6900 XT)"
echo ""

./bin/superposition "$@"
