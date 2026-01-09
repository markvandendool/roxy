#!/usr/bin/env python3
"""Friday Inference Client - Send prompts to Friday via SSH for processing"""
import subprocess
import sys
import json

FRIDAY_HOST = '10.0.0.65'
FRIDAY_USER = 'mark'
MODEL_PATH = '/home/mark/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf'
LLAMA_CLI = '/home/mark/citadel/llama.cpp/build/bin/llama-cli'

def run_inference(prompt: str, max_tokens: int = 50) -> str:
    cmd = f'ssh -o ConnectTimeout=5 {FRIDAY_USER}@{FRIDAY_HOST} "{LLAMA_CLI} -m {MODEL_PATH} -p \"{prompt}\" -n {max_tokens} 2>/dev/null | tail -3"'
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return 'Error: Timeout'
    except Exception as e:
        return f'Error: {e}'

if __name__ == '__main__':
    prompt = sys.argv[1] if len(sys.argv) > 1 else 'Hello, how are you?'
    print(f'Sending to Friday: {prompt}')
    result = run_inference(prompt)
    print(f'Response: {result}')
