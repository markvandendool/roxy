#!/bin/bash
#
# Benchmark GPU vs CPU Performance
# Tests transcription, LLM inference, and TTS generation
#

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     📊 GPU vs CPU Performance Benchmark                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

cd /opt/roxy
source venv/bin/activate

# Create test audio file if needed
TEST_AUDIO="/tmp/test_audio.wav"
if [ ! -f "$TEST_AUDIO" ]; then
    echo "Creating test audio file..."
    # Generate 10 seconds of silence for testing
    ffmpeg -f lavfi -i "sine=frequency=440:duration=10" "$TEST_AUDIO" -y 2>/dev/null || echo "⚠️  Could not create test audio"
fi

echo "1. Benchmarking Whisper Transcription..."
echo "   (This requires an audio file)"
echo "   To test manually:"
echo "   python3 voice/transcription/service.py $TEST_AUDIO --device cpu"
echo "   python3 voice/transcription/service.py $TEST_AUDIO --device cuda"
echo ""

echo "2. Benchmarking Ollama LLM Inference..."
echo "   Testing GPU inference speed..."
START_TIME=$(date +%s.%N)
ollama run llama3:8b "Say hello in one word" > /dev/null 2>&1
END_TIME=$(date +%s.%N)
ELAPSED=$(echo "$END_TIME - $START_TIME" | bc)
echo "   First inference: ${ELAPSED}s (includes model loading)"
echo ""

# Test multiple inferences
echo "   Running 5 inferences for average..."
TOTAL=0
for i in {1..5}; do
    START_TIME=$(date +%s.%N)
    ollama run llama3:8b "Count to $i" > /dev/null 2>&1
    END_TIME=$(date +%s.%N)
    ELAPSED=$(echo "$END_TIME - $START_TIME" | bc)
    TOTAL=$(echo "$TOTAL + $ELAPSED" | bc)
    echo "   Inference $i: ${ELAPSED}s"
done
AVG=$(echo "scale=2; $TOTAL / 5" | bc)
echo "   Average: ${AVG}s per inference"
echo ""

echo "3. Benchmarking TTS Generation..."
echo "   Testing GPU TTS speed..."
python3 << 'PYTHON_SCRIPT'
import time
from voice.tts.service import RoxyTTS

try:
    tts = RoxyTTS()
    print(f"   Device: {tts.device}")
    
    test_text = "This is a test of the TTS system with GPU acceleration."
    
    start = time.time()
    output = tts.speak(test_text, output_path="/tmp/test_tts_output.wav")
    elapsed = time.time() - start
    
    print(f"   Generation time: {elapsed:.2f}s")
    print(f"   Output: {output}")
except Exception as e:
    print(f"   ⚠️  TTS test failed: {e}")
PYTHON_SCRIPT

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     📊 Benchmark Complete                                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "💡 For detailed benchmarks, run individual component tests"










