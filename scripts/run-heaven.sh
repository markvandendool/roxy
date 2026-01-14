#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"

# Unigine Heaven Benchmark Launcher

HEAVEN_DIR=$(find ~ -maxdepth 1 -type d -name "*heaven*" -o -name "*Heaven*" 2>/dev/null | head -1)

if [ -z "$HEAVEN_DIR" ]; then
    echo "❌ Heaven not found. Installing..."
    if [ -f ~/Downloads/Unigine_Heaven-4.0.run ]; then
        chmod +x ~/Downloads/Unigine_Heaven-4.0.run
        cd ~
        ~/Downloads/Unigine_Heaven-4.0.run
        HEAVEN_DIR=$(find ~ -maxdepth 1 -type d -name "*heaven*" -o -name "*Heaven*" 2>/dev/null | head -1)
    else
        echo "Heaven installer not found at ~/Downloads/Unigine_Heaven-4.0.run"
        exit 1
    fi
fi

if [ -n "$HEAVEN_DIR" ] && [ -f "$HEAVEN_DIR/heaven" ]; then
    echo "✅ Launching Heaven from: $HEAVEN_DIR"
    cd "$HEAVEN_DIR"
    ./heaven "$@"
else
    echo "❌ Heaven executable not found in $HEAVEN_DIR"
    echo "Please run the installer manually: ~/Downloads/Unigine_Heaven-4.0.run"
    exit 1
fi