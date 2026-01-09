#!/bin/bash
#
# Quick test to verify Whisper uses CPU instead of GPU
#

echo "🧪 Testing Whisper CPU Configuration..."
echo ""

# Check if Python environment is available
if [ ! -f "/opt/roxy/venv/bin/python" ]; then
    echo "❌ Python venv not found at /opt/roxy/venv"
    exit 1
fi

# Create a simple test script
TEST_SCRIPT=$(mktemp /tmp/test_whisper_XXXXXX.py)
cat > "$TEST_SCRIPT" << 'EOF'
import os
import sys
sys.path.insert(0, '/opt/roxy')

# Set environment variable
os.environ['ROXY_WHISPER_DEVICE'] = 'cpu'

from voice.transcription.service import RoxyTranscription

print("🔍 Testing Whisper device selection...")
print("")

# Initialize with auto-detect (should use CPU due to env var)
transcriber = RoxyTranscription(model_size="base", device="auto")

print("")
print("✅ Test complete!")
print(f"   Device: {transcriber.device}")
print(f"   Compute Type: {transcriber.compute_type}")

if transcriber.device == "cpu":
    print("   ✅ SUCCESS: Whisper is using CPU")
else:
    print(f"   ⚠️  WARNING: Whisper is using {transcriber.device} instead of CPU")
EOF

# Run the test
/opt/roxy/venv/bin/python "$TEST_SCRIPT"

# Cleanup
rm -f "$TEST_SCRIPT"

echo ""
echo "📝 Note: This test only verifies configuration."
echo "   For full testing, start the voice service and monitor GPU usage."












