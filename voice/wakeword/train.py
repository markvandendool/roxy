#!/usr/bin/env python3
"""
ROXY Custom Wake Word Training
Uses OpenWakeWord training pipeline to create custom 'Hey Roxy' model
"""
import os
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROXY_ROOT = os.environ.get("ROXY_ROOT", str(Path.home() / ".roxy"))
SAMPLES_DIR = f"{ROXY_ROOT}/voice/wakeword/samples"
OUTPUT_DIR = f"{ROXY_ROOT}/voice/wakeword/models"
MODEL_NAME = "hey_roxy"

def prepare_training_data():
    """Prepare training data in OpenWakeWord format"""
    positive_dir = Path(SAMPLES_DIR) / "positive"
    negative_dir = Path(SAMPLES_DIR) / "negative"
    
    positive_samples = list(positive_dir.glob("*.wav"))
    negative_samples = list(negative_dir.glob("*.wav"))
    
    logger.info(f"Positive samples: {len(positive_samples)}")
    logger.info(f"Negative samples: {len(negative_samples)}")
    
    return {
        "positive": [str(p) for p in positive_samples],
        "negative": [str(n) for n in negative_samples],
        "model_name": MODEL_NAME,
        "prepared_at": datetime.now().isoformat()
    }

def create_training_config():
    """Create OpenWakeWord training configuration"""
    config = {
        "model_name": MODEL_NAME,
        "target_phrase": "hey roxy",
        "positive_samples_dir": f"{SAMPLES_DIR}/positive",
        "negative_samples_dir": f"{SAMPLES_DIR}/negative",
        "output_dir": OUTPUT_DIR,
        "training_params": {
            "epochs": 100,
            "batch_size": 32,
            "learning_rate": 0.001,
            "validation_split": 0.2,
            "early_stopping_patience": 10
        },
        "augmentation": {
            "noise_injection": True,
            "time_stretch": True,
            "pitch_shift": True,
            "volume_variation": True
        }
    }
    
    config_path = Path(OUTPUT_DIR) / "training_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"Training config saved: {config_path}")
    return config

def main():
    print("=" * 60)
    print("ROXY Wake Word Training Preparation")
    print("=" * 60)
    
    # Prepare data
    data = prepare_training_data()
    print(f"\nDataset ready:")
    print(f"  Positive samples: {len(data['positive'])}")
    print(f"  Negative samples: {len(data['negative'])}")
    
    # Create config
    config = create_training_config()
    print(f"\nTraining config created:")
    print(f"  Model name: {config['model_name']}")
    print(f"  Target phrase: {config['target_phrase']}")
    print(f"  Epochs: {config['training_params']['epochs']}")
    
    # Save manifest
    manifest_path = Path(OUTPUT_DIR) / "training_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nManifest saved: {manifest_path}")
    
    print("\n" + "=" * 60)
    print("TRAINING INSTRUCTIONS")
    print("=" * 60)
    print("""
To train the custom 'Hey Roxy' wake word model:

1. Install training dependencies:
   pip install torch torchaudio openwakeword[training]

2. Run training (requires GPU for reasonable speed):
   python -c "
   from openwakeword.train import train_model
   train_model(
       'hey_roxy',
       f'{ROXY_ROOT}/voice/wakeword/samples/positive',
       f'{ROXY_ROOT}/voice/wakeword/samples/negative',
       f'{ROXY_ROOT}/voice/wakeword/models'
   )
   "

3. After training, update detector to use custom model:
   MODEL_DIR = f'{ROXY_ROOT}/voice/wakeword/models'
   MODELS = [f'{MODEL_DIR}/hey_roxy.onnx']

Alternative: Use existing 'hey_roxy' as interim until GPU training available.

Current interim configuration uses: hey_roxy_v0.1
""")

if __name__ == "__main__":
    main()
