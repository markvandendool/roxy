# Hey Roxy Wake Word Training

## Current Status
- **Samples Generated:** 61 (20 positive, 41 negative)
- **Method:** Synthetic TTS via Piper (lessac-medium voice)
- **Model Target:** OpenWakeWord custom model

## Directory Structure
```
~/.roxy/wake/
├── hey_roxy/
│   ├── positive/    # "Hey Roxy" variations (20 samples)
│   └── negative/    # Similar but NOT "Hey Roxy" (41 samples)
├── generate_samples.py
├── generate_more_samples.py
└── README.md
```

## Training Process

### Option 1: OpenWakeWord Custom Training (Recommended)
```bash
# Clone OpenWakeWord training repo
git clone https://github.com/dscripka/openWakeWord.git
cd openWakeWord

# Install training dependencies
pip install -e .[train]

# Prepare training config
# See: https://github.com/dscripka/openWakeWord/blob/main/docs/custom_models.md
```

### Option 2: Porcupine Custom Training
- Upload samples to Picovoice Console
- Generate .ppn file
- More accurate but requires account

### Option 3: Use Pre-trained "Hey Jarvis" 
- Already working in roxy_assistant.py
- Rename to "Roxy" later when custom model ready

## Improving Accuracy

### Add Real Voice Samples
Record yourself saying "Hey Roxy" 50+ times in different:
- Distances from mic
- Background noise levels
- Speaking speeds
- Emotional states

### Augmentation
Apply audio augmentations to existing samples:
- Speed variations (0.9x - 1.1x)
- Pitch shifting
- Background noise mixing
- Room reverb simulation

## Quick Test
```python
from openwakeword.model import Model

# Load pre-trained models
oww = Model()

# Test with audio frame (16kHz, int16)
predictions = oww.predict(audio_frame)
for name, score in predictions.items():
    if score > 0.5:
        print(f"Detected: {name}")
```

## Next Steps
1. [ ] Record 50+ real voice samples
2. [ ] Apply audio augmentation
3. [ ] Train custom OpenWakeWord model
4. [ ] Test false positive rate
5. [ ] Deploy to roxy_assistant.py

---
Generated: 2025-12-22
Samples: Piper TTS (lessac-medium)
