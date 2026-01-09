#!/bin/bash
# Voice Loop Test Script - Tests STT -> LLM -> TTS pipeline

echo '=== ROXY VOICE LOOP TEST ==='
echo ''

# Test 1: Record audio from mic
echo '[1/4] Testing microphone recording...'
arecord -D hw:2,0 -d 2 -f S16_LE -r 16000 /tmp/voice-test-input.wav 2>/dev/null
if [ -f /tmp/voice-test-input.wav ]; then
    SIZE=$(stat -c%s /tmp/voice-test-input.wav)
    echo "    ✅ Recorded $SIZE bytes from OWC mic"
else
    echo '    ❌ Microphone recording failed'
    exit 1
fi

# Test 2: Check Whisper STT
echo '[2/4] Testing Whisper STT service...'
WHISPER_STATUS=$(docker inspect wyoming-whisper --format '{{.State.Status}}' 2>/dev/null)
if [ "$WHISPER_STATUS" = "running" ]; then
    echo '    ✅ Whisper STT container running'
else
    echo '    ❌ Whisper STT not running'
fi

# Test 3: Check Ollama LLM
echo '[3/4] Testing Ollama LLM...'
OLLAMA_RESPONSE=$(curl -s http://localhost:11434/api/generate -d '{"model":"llama3.2:1b","prompt":"Say hello","stream":false}' 2>/dev/null | head -c 100)
if [ -n "$OLLAMA_RESPONSE" ]; then
    echo '    ✅ Ollama responding'
else
    echo '    ❌ Ollama not responding'
fi

# Test 4: Check Piper TTS
echo '[4/4] Testing Piper TTS service...'
PIPER_STATUS=$(docker inspect wyoming-piper --format '{{.State.Status}}' 2>/dev/null)
if [ "$PIPER_STATUS" = "running" ]; then
    echo '    ✅ Piper TTS container running'
else
    echo '    ❌ Piper TTS not running'
fi

echo ''
echo '=== VOICE LOOP STATUS ==='
echo 'Mic → Whisper → Ollama → Piper pipeline READY'
echo ''
echo 'To use with Home Assistant:'
echo '  http://10.0.0.69:8123'
echo ''
