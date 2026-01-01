#!/usr/bin/env python3
"""
ROXY Browser Agent - LUNA-S2
Uses browser-use for AI-powered browser automation
"""

import asyncio
import os
from pathlib import Path

# Browser-use imports
try:
    from browser_use import Agent
    from langchain_ollama import ChatOllama
except ImportError as e:
    print(f'Missing dependency: {e}')
    print('Run: pip install browser-use langchain-ollama')
    exit(1)

# Configuration
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
MODEL_NAME = os.getenv('OLLAMA_MODEL', 'llama3:8b')
SESSIONS_DIR = Path('/opt/roxy/secrets/browser-sessions')

async def run_browser_task(task: str, headless: bool = True):
    """Execute a browser automation task using AI"""
    
    # Initialize Ollama LLM
    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_HOST,
        temperature=0.1,
    )
    
    # Create browser agent
    agent = Agent(
        task=task,
        llm=llm,
        headless=headless,
    )
    
    # Run the task
    result = await agent.run()
    return result

async def main():
    """Demo: Search for something"""
    print('🤖 ROXY Browser Agent Starting...')
    print(f'   Model: {MODEL_NAME}')
    print(f'   Ollama: {OLLAMA_HOST}')
    
    # Simple test task
    task = 'Go to google.com and search for "AI browser automation"'
    
    print(f'\n📋 Task: {task}')
    result = await run_browser_task(task, headless=True)
    print(f'\n✅ Result: {result}')

if __name__ == '__main__':
    asyncio.run(main())
