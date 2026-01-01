# Hey Roxy Wake Word Setup

Custom wake word training for Roxy AI assistant.

## Quick Start

### 1. Record Positive Samples (say "Hey Roxy")
```bash
cd /opt/roxy/wakeword/scripts
python3 record_samples.py positive
```
Record at least 15 samples of you saying "Hey Roxy"

### 2. Record Negative Samples (say other phrases)
```bash
python3 record_samples.py negative
```
Record at least 15 samples of random speech (NOT "Hey Roxy")

### 3. Train the Model
```bash
python3 train_hey_roxy.py
```
Creates a custom verifier that improves detection for your voice.

### 4. Test Detection
```bash
python3 test_listener.py
```
Listens for "Hey Roxy" in real-time.

## Files

| File | Purpose |
|------|---------|
| samples/positive/*.wav | "Hey Roxy" recordings |
| samples/negative/*.wav | Other speech recordings |
| models/hey_roxy_verifier.joblib | Trained verifier model |

## Technical Details

- Base model: hey_jarvis (phonetically similar)
- Audio format: 16kHz, 16-bit, mono WAV
- Microphone: USB Advanced Audio Device (card 9)
- Framework: openWakeWord 0.4.0

## Wyoming Integration

The trained verifier works with Wyoming OpenWakeWord for Home Assistant.
Update docker-compose to mount the custom model.
