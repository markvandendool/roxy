#!/bin/bash
#
# Setup FFmpeg with AMD AMF Support
# Note: May require building FFmpeg from source with AMF support
#

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🔧 FFmpeg AMF Setup                                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check current FFmpeg
echo "1. Checking current FFmpeg installation..."
ffmpeg -version 2>&1 | head -3
echo ""

# Check for AMF encoder
echo "2. Checking for AMF encoder support..."
if ffmpeg -encoders 2>&1 | grep -qi "amf"; then
    echo "   ✅ AMF encoder available"
    ffmpeg -encoders 2>&1 | grep -i amf
else
    echo "   ⚠️  AMF encoder not available"
    echo ""
    echo "   To enable AMF encoding, you need to:"
    echo "   1. Install AMD AMF SDK"
    echo "   2. Build FFmpeg from source with --enable-amf"
    echo ""
    echo "   For now, using software encoding (libx264)"
fi
echo ""

# Check for hardware acceleration
echo "3. Checking for hardware acceleration..."
if ffmpeg -hwaccels 2>&1 | grep -qi "d3d11va\|vaapi\|vdpau"; then
    echo "   ✅ Hardware acceleration available"
    ffmpeg -hwaccels 2>&1 | grep -E "d3d11va|vaapi|vdpau"
else
    echo "   ⚠️  Limited hardware acceleration support"
fi
echo ""

echo "📝 Note: GPU encoding presets are configured in encoding_presets.py"
echo "   They will use AMF when available, fallback to software encoding"










