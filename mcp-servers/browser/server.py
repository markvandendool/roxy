#!/usr/bin/env python3
"""
ROXY Browser MCP Server - LUNA-S2
Exposes browser automation as MCP tools for Claude
"""

import asyncio
import json
from pathlib import Path
import os
from typing import Any

try:
    from fastmcp import FastMCP
    from browser_use import Agent
    from langchain_ollama import ChatOllama
except ImportError as e:
    print(f'Missing: {e}. Run: pip install fastmcp browser-use langchain-ollama')
    exit(1)

# Initialize MCP server
mcp = FastMCP('roxy-browser')

# Configuration
OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11435')
MODEL_NAME = os.environ.get('OLLAMA_MODEL', 'llama3:8b')
ROXY_ROOT = Path(os.environ.get('ROXY_ROOT', str(Path.home() / '.roxy')))
SESSIONS_DIR = ROXY_ROOT / 'etc' / 'browser-sessions'
DATA_DIR = ROXY_ROOT / 'var' / 'data'
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

def get_llm():
    return ChatOllama(model=MODEL_NAME, base_url=OLLAMA_HOST, temperature=0.1)

@mcp.tool()
async def browse_and_extract(url: str, instruction: str) -> str:
    """
    Navigate to a URL and extract information based on instruction.
    
    Args:
        url: The URL to navigate to
        instruction: What to extract or do on the page
    """
    task = f'Go to {url} and {instruction}'
    agent = Agent(task=task, llm=get_llm(), headless=True)
    result = await agent.run()
    return json.dumps({'url': url, 'result': str(result)})

@mcp.tool()
async def search_web(query: str, engine: str = 'google') -> str:
    """
    Search the web using specified search engine.
    
    Args:
        query: Search query
        engine: Search engine (google, bing, duckduckgo)
    """
    engines = {
        'google': 'https://google.com',
        'bing': 'https://bing.com',
        'duckduckgo': 'https://duckduckgo.com'
    }
    base_url = engines.get(engine, engines['google'])
    task = f'Go to {base_url}, search for "{query}", and summarize the top 3 results'
    agent = Agent(task=task, llm=get_llm(), headless=True)
    result = await agent.run()
    return json.dumps({'query': query, 'engine': engine, 'results': str(result)})

@mcp.tool()
async def fill_form(url: str, form_data: dict) -> str:
    """
    Navigate to a URL and fill out a form.
    
    Args:
        url: The URL with the form
        form_data: Dictionary of field names to values
    """
    fields_desc = ', '.join([f'{k}="{v}"' for k, v in form_data.items()])
    task = f'Go to {url} and fill out the form with: {fields_desc}'
    agent = Agent(task=task, llm=get_llm(), headless=True)
    result = await agent.run()
    return json.dumps({'url': url, 'filled': form_data, 'result': str(result)})

@mcp.tool()
async def screenshot_page(url: str, filename: str = 'screenshot.png') -> str:
    """
    Take a screenshot of a webpage.
    
    Args:
        url: The URL to screenshot
        filename: Output filename
    """
    output_path = str(DATA_DIR / filename)
    task = f'Go to {url}, wait for page to load, and take a screenshot'
    agent = Agent(task=task, llm=get_llm(), headless=True)
    result = await agent.run()
    return json.dumps({'url': url, 'screenshot': output_path, 'result': str(result)})

if __name__ == '__main__':
    print('🌐 ROXY Browser MCP Server')
    print('   Tools: browse_and_extract, search_web, fill_form, screenshot_page')
    mcp.run()
