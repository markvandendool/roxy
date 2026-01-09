#!/bin/bash

# Unigine Superposition Benchmark Launcher

SUPER_DIR=$(find ~ -maxdepth 1 -type d -name "*uperposition*" -o -name "*Superposition*" 2>/dev/null | head -1)

if [ -z "$SUPER_DIR" ]; then
    echo "❌ Superposition not found. Installing..."
    if [ -f ~/Downloads/Unigine_Superposition-1.1.run ]; then
        chmod +x ~/Downloads/Unigine_Superposition-1.1.run
        cd ~
        echo "Running installer... (follow prompts)"
        ~/Downloads/Unigine_Superposition-1.1.run
        SUPER_DIR=$(find ~ -maxdepth 1 -type d -name "*uperposition*" -o -name "*Superposition*" 2>/dev/null | head -1)
    else
        echo "Superposition installer not found. Downloading..."
        cd ~/Downloads
        wget -q --show-progress https://assets.unigine.com/d/Unigine_Superposition-1.1.run -O Unigine_Superposition-1.1.run
        chmod +x ~/Downloads/Unigine_Superposition-1.1.run
        cd ~
        ~/Downloads/Unigine_Superposition-1.1.run
        SUPER_DIR=$(find ~ -maxdepth 1 -type d -name "*uperposition*" -o -name "*Superposition*" 2>/dev/null | head -1)
    fi
fi

if [ -n "$SUPER_DIR" ]; then
    EXECUTABLE=$(find "$SUPER_DIR" -type f -executable -name "*uperposition*" | head -1)
    if [ -n "$EXECUTABLE" ]; then
        echo "✅ Launching Superposition from: $EXECUTABLE"
        cd "$SUPER_DIR"
        "$EXECUTABLE" "$@"
    else
        echo "❌ Superposition executable not found in $SUPER_DIR"
        echo "Please run the installer manually: ~/Downloads/Unigine_Superposition-1.1.run"
        exit 1
    fi
else
    echo "❌ Superposition not installed"
    echo "Please run: ~/Downloads/Unigine_Superposition-1.1.run"
    exit 1
fi
