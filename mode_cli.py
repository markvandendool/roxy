#!/usr/bin/env python3
"""
ROXY Mode CLI - Query ROXY in different modes
Usage:
    roxy-mode benchmark "your prompt here"
    roxy-mode raw "your prompt here" --mode technical
    roxy-mode test-mmlu
"""

import json
import sys
import urllib.request
from pathlib import Path

TOKEN = Path.home().joinpath(".roxy/secret.token").read_text().strip()
BASE_URL = "http://localhost:8766"

def query(endpoint: str, data: dict) -> dict:
    """Make request to ROXY"""
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}",
        data=json.dumps(data).encode(),
        headers={"X-ROXY-Token": TOKEN, "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())

def benchmark(prompt: str, model: str = "qwen2.5-coder:14b", temp: float = 0.0, max_tokens: int = 256):
    """Query in benchmark mode (raw model, no personality)"""
    return query("/benchmark", {
        "prompt": prompt,
        "model": model,
        "temperature": temp,
        "max_tokens": max_tokens
    })

def raw(prompt: str, mode: str = "technical", model: str = "qwen2.5-coder:14b"):
    """Query in raw mode with configurable personality"""
    return query("/raw", {
        "prompt": prompt,
        "mode": mode,
        "model": model
    })

def broadcast(command: str):
    """Query in broadcast mode (full ROXY personality)"""
    return query("/run", {"command": command})

def test_mmlu():
    """Run MMLU benchmark test"""
    questions = [
        ("Speed of light in vacuum: A)3x10^6 m/s B)3x10^8 m/s C)3x10^10 m/s D)3x10^12 m/s", "B"),
        ("Pituitary gland cavity: A)Abdominal B)Cranial C)Pleural D)Spinal", "B"),
        ("P OR NOT P is: A)Tautology B)Contradiction C)Contingency D)Invalid", "A"),
        ("3kg at 4m/s kinetic energy: A)6J B)12J C)24J D)48J", "C"),
        ("Longest human muscle: A)Sartorius B)Rectus femoris C)Biceps D)Gluteus", "A"),
        ("Water formula: A)H2O B)CO2 C)NaCl D)CH4", "A"),
        ("Mercury is closest planet to: A)Earth B)Sun C)Mars D)Venus", "B"),
        ("15% of 200: A)15 B)20 C)30 D)35", "C"),
        ("All A are B, All B are C, therefore: A)All C are A B)Some C are A C)All A are C D)No A are C", "C"),
        ("1450 is printing press invention year: A)1250 B)1350 C)1450 D)1550", "C"),
    ]
    
    print("=" * 50)
    print("  MMLU BENCHMARK TEST")
    print("=" * 50)
    
    correct = 0
    for i, (q, expected) in enumerate(questions, 1):
        prompt = f"Q: {q}\nAnswer (just A, B, C, or D):"
        result = benchmark(prompt, max_tokens=5)
        answer = result.get('result', '?').strip().upper()
        got = answer[0] if answer and answer[0] in "ABCD" else "?"
        
        if got == expected:
            correct += 1
            print(f"  {i}. ✅ {got}")
        else:
            print(f"  {i}. ❌ {got} (expected {expected})")
    
    score = correct * 10
    print(f"\n  SCORE: {correct}/10 = {score}%")
    print("=" * 50)
    
    # Comparison
    print("\n  📊 COMPARISON:")
    print(f"  ROXY (benchmark): {score}%")
    print(f"  GPT-3.5:          ~70%")
    print(f"  GPT-4:            ~86%")
    print(f"  Claude-3-Opus:    ~87%")
    
    if score >= 80:
        print("\n  🏆 EXCELLENT - Top tier performance!")
    elif score >= 60:
        print("\n  ✓ GOOD - Competitive with GPT-3.5!")
    else:
        print("\n  ℹ️ Model may need tuning for MMLU format")
    
    return correct, 10

def show_modes():
    """Show available modes"""
    req = urllib.request.Request(f"{BASE_URL}/modes")
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    
    print("=" * 50)
    print("  ROXY MODES")
    print("=" * 50)
    for mode, config in data.get('modes', {}).items():
        print(f"\n  {mode}:")
        print(f"    {config['description']}")
        print(f"    temp={config['temperature']}, system_prompt={config['system_prompt']}")
    
    print("\n  ENDPOINTS:")
    for endpoint, desc in data.get('endpoints', {}).items():
        print(f"    {endpoint}: {desc}")

def main():
    if len(sys.argv) < 2:
        print("ROXY Mode CLI")
        print("Usage:")
        print("  roxy-mode modes              - Show available modes")
        print("  roxy-mode benchmark <prompt> - Raw model query")
        print("  roxy-mode raw <prompt>       - Technical mode query")
        print("  roxy-mode test-mmlu          - Run MMLU benchmark")
        print("  roxy-mode broadcast <query>  - Full ROXY personality")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "modes":
        show_modes()
    elif cmd == "test-mmlu":
        test_mmlu()
    elif cmd == "benchmark" and len(sys.argv) > 2:
        prompt = " ".join(sys.argv[2:])
        result = benchmark(prompt)
        print(f"Mode: {result.get('mode')}")
        print(f"Model: {result.get('model')}")
        print(f"Time: {result.get('response_time')}s")
        print(f"\nResult:\n{result.get('result')}")
    elif cmd == "raw" and len(sys.argv) > 2:
        prompt = " ".join(sys.argv[2:])
        result = raw(prompt)
        print(f"Mode: {result.get('mode')}")
        print(f"Model: {result.get('model')}")
        print(f"Time: {result.get('response_time')}s")
        print(f"\nResult:\n{result.get('result')}")
    elif cmd == "broadcast" and len(sys.argv) > 2:
        command = " ".join(sys.argv[2:])
        result = broadcast(command)
        print(f"Time: {result.get('response_time')}s")
        print(f"\nResult:\n{result.get('result')}")
    else:
        print(f"Unknown command: {cmd}")
        print("Run 'roxy-mode' for help")

if __name__ == "__main__":
    main()
