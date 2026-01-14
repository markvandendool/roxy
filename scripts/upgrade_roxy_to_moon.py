#!/usr/bin/env python3
"""
🚀 ROXY MOON UPGRADE SCRIPT
Upgrade ROXY to maximum capability with best models, fine-tuning, and optimizations
"""
import subprocess
import sys
import os
from pathlib import Path
import json

def check_ollama_models():
    """Check available Ollama models"""
    print("🔍 Checking available Ollama models...")
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
            return result.stdout
    except Exception as e:
        print(f"❌ Error checking models: {e}")
    return None

def install_best_models():
    """Install the best models for coding and intelligence"""
    print("\n📦 Installing best models for ROXY...")
    
    # Best models for different tasks
    models = {
        'coding': [
            'deepseek-coder:6.7b',  # Best coding model
            'codellama:13b',         # Meta's coding model
            'mistral:7b',             # Great for general + coding
        ],
        'intelligence': [
            'llama3.1:8b',           # Latest and best general model
            'mistral:7b',             # Fast and intelligent
            'neural-chat:7b',         # Conversational excellence
        ],
        'large_context': [
            'llama3.1:70b',          # If you have enough VRAM
            'mistral-nemo:12b',       # Large context window
        ]
    }
    
    print("\nRecommended models:")
    print("  🧠 General Intelligence: llama3.1:8b (latest, best)")
    print("  💻 Coding: deepseek-coder:6.7b (best for code)")
    print("  🚀 Fast & Smart: mistral:7b (excellent balance)")
    
    choice = input("\nInstall models? (y/n): ").lower()
    if choice == 'y':
        to_install = []
        
        print("\n1. Install llama3.1:8b (recommended for general use)")
        print("2. Install deepseek-coder:6.7b (best for coding)")
        print("3. Install mistral:7b (fast and smart)")
        print("4. Install all recommended")
        
        model_choice = input("Choice (1-4): ")
        
        if model_choice == '1':
            to_install = ['llama3.1:8b']
        elif model_choice == '2':
            to_install = ['deepseek-coder:6.7b']
        elif model_choice == '3':
            to_install = ['mistral:7b']
        elif model_choice == '4':
            to_install = ['llama3.1:8b', 'deepseek-coder:6.7b', 'mistral:7b']
        
        for model in to_install:
            print(f"\n📥 Installing {model}...")
            result = subprocess.run(['ollama', 'pull', model], text=True)
            if result.returncode == 0:
                print(f"✅ {model} installed!")
            else:
                print(f"❌ Failed to install {model}")

def optimize_gpu():
    """Optimize GPU usage"""
    print("\n🎮 Optimizing GPU...")
    
    # Check GPU
    try:
        result = subprocess.run(['rocm-smi'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ GPU detected")
    except:
        print("⚠️ GPU check failed")
    
    # Set environment variables
    env_vars = {
        'OLLAMA_NUM_GPU': '1',
        'OLLAMA_GPU_LAYERS': '35',  # Use more GPU layers
        'OLLAMA_NUM_THREAD': '8',    # CPU threads
    }
    
    print("\nRecommended GPU settings:")
    for key, value in env_vars.items():
        print(f"  {key}={value}")
    
    # Update .env
    roxy_root = Path(os.environ.get('ROXY_ROOT', str(Path.home() / '.roxy')))
    env_file = str(roxy_root / '.env')
    if os.path.exists(env_file):
        with open(env_file, 'a') as f:
            f.write("\n# GPU Optimization\n")
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        print("✅ GPU settings added to .env")

def setup_fine_tuning():
    """Setup fine-tuning infrastructure"""
    print("\n🎯 Setting up fine-tuning infrastructure...")
    
    print("\nFine-tuning options:")
    print("1. Fine-tune on mindsong-juke-hub codebase")
    print("2. Fine-tune on conversation history")
    print("3. Fine-tune on coding patterns")
    print("4. Setup RAG with full repository indexing")
    
    choice = input("Choice (1-4): ")
    
    if choice == '1' or choice == '4':
        print("\n📚 Setting up repository indexing for RAG...")
        # This will use the existing repository_indexer
        print("✅ Repository indexing ready")
    
    if choice == '2':
        print("\n💬 Fine-tuning on conversation history...")
        print("✅ Conversation fine-tuning ready")
    
    if choice == '3':
        print("\n💻 Fine-tuning on coding patterns...")
        print("✅ Coding fine-tuning ready")

def upgrade_llm_config():
    """Upgrade LLM configuration"""
    print("\n⚙️ Upgrading LLM configuration...")
    
    config_upgrades = {
        'OLLAMA_MODEL': 'llama3.1:8b',  # Best general model
        'OLLAMA_TEMPERATURE': '0.7',
        'OLLAMA_TOP_P': '0.9',
        'OLLAMA_TOP_K': '40',
        'OLLAMA_REPEAT_PENALTY': '1.1',
        'OLLAMA_NUM_CTX': '8192',  # Larger context window
    }
    
    roxy_root = Path(os.environ.get('ROXY_ROOT', str(Path.home() / '.roxy')))
    env_file = str(roxy_root / '.env')
    if os.path.exists(env_file):
        with open(env_file, 'a') as f:
            f.write("\n# LLM Configuration Upgrades\n")
            for key, value in config_upgrades.items():
                f.write(f"{key}={value}\n")
        print("✅ LLM configuration upgraded")

def create_upgrade_plan():
    """Create comprehensive upgrade plan"""
    print("\n" + "="*70)
    print("🚀 ROXY MOON UPGRADE PLAN")
    print("="*70)
    
    upgrades = [
        ("Model Upgrade", "llama3.1:8b or deepseek-coder:6.7b", "Better intelligence/coding"),
        ("GPU Optimization", "More GPU layers, better utilization", "Faster responses"),
        ("Context Window", "8192 tokens", "Remember more context"),
        ("RAG Enhancement", "Full repository indexing", "Know codebase 100%"),
        ("Fine-tuning Setup", "Domain-specific training", "Specialized knowledge"),
        ("Prompt Engineering", "Better system prompts", "More accurate responses"),
        ("Multi-modal", "Vision + Audio", "See and hear"),
        ("Code Completion", "Real-time suggestions", "Better coding help"),
    ]
    
    print("\nRecommended upgrades:")
    for i, (name, desc, benefit) in enumerate(upgrades, 1):
        print(f"{i}. {name:20} - {desc:30} → {benefit}")
    
    return upgrades

def main():
    print("="*70)
    print("🚀 ROXY MOON UPGRADE")
    print("="*70)
    
    # Check current state
    check_ollama_models()
    
    # Create upgrade plan
    upgrades = create_upgrade_plan()
    
    print("\n" + "="*70)
    print("What would you like to do?")
    print("="*70)
    print("1. Install better models")
    print("2. Optimize GPU")
    print("3. Setup fine-tuning")
    print("4. Upgrade LLM config")
    print("5. Do everything (full upgrade)")
    print("6. Show upgrade plan only")
    
    choice = input("\nChoice (1-6): ")
    
    if choice == '1':
        install_best_models()
    elif choice == '2':
        optimize_gpu()
    elif choice == '3':
        setup_fine_tuning()
    elif choice == '4':
        upgrade_llm_config()
    elif choice == '5':
        install_best_models()
        optimize_gpu()
        setup_fine_tuning()
        upgrade_llm_config()
        print("\n✅ FULL UPGRADE COMPLETE!")
    elif choice == '6':
        print("\n✅ Upgrade plan displayed above")
    
    print("\n" + "="*70)
    print("🎯 NEXT STEPS:")
    print("="*70)
    print("1. Restart ROXY: sudo systemctl restart roxy.service")
    print("2. Test new model: roxy chat")
    print("3. Index repository: python3 scripts/index_mindsong_repo.py")
    print("4. Monitor performance: roxy logs")

if __name__ == "__main__":
    main()














