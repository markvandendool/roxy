#!/usr/bin/env python3
"""
ROXY Desktop MCP Server - LUNA-S3
Unified desktop control API for Wayland/X11
"""

import asyncio
import subprocess
import json
import os
from pathlib import Path
from datetime import datetime

try:
    from fastmcp import FastMCP
except ImportError:
    print('Missing fastmcp. Run: pip install fastmcp')
    exit(1)

mcp = FastMCP('roxy-desktop')

# Key codes for common keys (Linux evdev)
KEY_CODES = {
    'enter': 28, 'tab': 15, 'space': 57, 'backspace': 14,
    'escape': 1, 'up': 103, 'down': 108, 'left': 105, 'right': 106,
    'home': 102, 'end': 107, 'pageup': 104, 'pagedown': 109,
    'ctrl': 29, 'alt': 56, 'shift': 42, 'super': 125,
    'f1': 59, 'f2': 60, 'f3': 61, 'f4': 62, 'f5': 63,
    'f6': 64, 'f7': 65, 'f8': 66, 'f9': 67, 'f10': 68,
    'f11': 87, 'f12': 88,
}

def run_ydotool(args: list) -> tuple[bool, str]:
    """Run ydotool command (no sudo needed if service running)"""
    try:
        # Try without sudo first (if ydotool service is running)
        result = subprocess.run(
            ['ydotool'] + args,
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return True, result.stdout + result.stderr
        # Fallback to sudo if needed
        result = subprocess.run(
            ['sudo', 'ydotool'] + args,
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)

@mcp.tool()
async def type_text(text: str, delay_ms: int = 50) -> str:
    """
    Type text using keyboard simulation.
    
    Args:
        text: Text to type
        delay_ms: Delay between keystrokes in milliseconds
    """
    success, output = run_ydotool(['type', '--delay', str(delay_ms), text])
    return json.dumps({'success': success, 'text': text, 'output': output})

@mcp.tool()
async def press_key(key: str, modifiers: list = None) -> str:
    """
    Press a key or key combination.
    
    Args:
        key: Key name (enter, tab, f1, etc.) or single character
        modifiers: List of modifier keys (ctrl, alt, shift, super)
    """
    modifiers = modifiers or []
    
    # Build key sequence
    key_args = []
    
    # Press modifiers
    for mod in modifiers:
        if mod.lower() in KEY_CODES:
            key_args.append(f'{KEY_CODES[mod.lower()]}:1')  # Press
    
    # Press and release main key
    if key.lower() in KEY_CODES:
        code = KEY_CODES[key.lower()]
    elif len(key) == 1:
        # Single character - use type instead
        return await type_text(key)
    else:
        return json.dumps({'success': False, 'error': f'Unknown key: {key}'})
    
    key_args.append(f'{code}:1')  # Press
    key_args.append(f'{code}:0')  # Release
    
    # Release modifiers (reverse order)
    for mod in reversed(modifiers):
        if mod.lower() in KEY_CODES:
            key_args.append(f'{KEY_CODES[mod.lower()]}:0')  # Release
    
    success, output = run_ydotool(['key'] + key_args)
    return json.dumps({'success': success, 'key': key, 'modifiers': modifiers})

@mcp.tool()
async def mouse_move(x: int, y: int, absolute: bool = True) -> str:
    """
    Move mouse cursor.
    
    Args:
        x: X coordinate (or delta if absolute=False)
        y: Y coordinate (or delta if absolute=False)
        absolute: If True, move to absolute position; if False, move relative
    """
    args = ['mousemove']
    if absolute:
        args.extend(['--absolute', '-x', str(x), '-y', str(y)])
    else:
        args.extend(['-x', str(x), '-y', str(y)])
    
    success, output = run_ydotool(args)
    return json.dumps({'success': success, 'x': x, 'y': y, 'absolute': absolute})

@mcp.tool()
async def mouse_click(button: str = 'left', count: int = 1) -> str:
    """
    Click mouse button.
    
    Args:
        button: Button to click (left, right, middle)
        count: Number of clicks (1 for single, 2 for double)
    """
    button_codes = {'left': '0xC0', 'right': '0xC1', 'middle': '0xC2'}
    code = button_codes.get(button.lower(), '0xC0')
    
    args = ['click', code]
    for _ in range(count):
        success, output = run_ydotool(args)
    
    return json.dumps({'success': success, 'button': button, 'count': count})

@mcp.tool()
async def get_clipboard() -> str:
    """Get current clipboard contents."""
    try:
        result = subprocess.run(
            ['wl-paste'], capture_output=True, text=True, timeout=5
        )
        return json.dumps({'success': True, 'content': result.stdout})
    except Exception as e:
        return json.dumps({'success': False, 'error': str(e)})

@mcp.tool()
async def set_clipboard(text: str) -> str:
    """
    Set clipboard contents.
    
    Args:
        text: Text to copy to clipboard
    """
    try:
        result = subprocess.run(
            ['wl-copy'], input=text, text=True, timeout=5
        )
        return json.dumps({'success': result.returncode == 0, 'text': text})
    except Exception as e:
        return json.dumps({'success': False, 'error': str(e)})

@mcp.tool()
async def take_screenshot(filename: str = None, region: str = None) -> str:
    """
    Take a screenshot.
    
    Args:
        filename: Output filename (default: timestamp-based)
        region: Region to capture (format: WxH+X+Y, e.g., 800x600+100+100)
    """
    if filename is None:
        filename = f'screenshot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    
    roxy_root = os.environ.get('ROXY_ROOT', str(Path.home() / '.roxy'))
    output_path = f'{roxy_root}/data/{filename}'
    
    try:
        args = ['gnome-screenshot', '-f', output_path]
        if region:
            # Parse region and use -a for area selection
            args = ['gnome-screenshot', '-a', '-f', output_path]
        
        result = subprocess.run(args, capture_output=True, text=True, timeout=10)
        success = result.returncode == 0 and Path(output_path).exists()
        return json.dumps({'success': success, 'path': output_path})
    except Exception as e:
        return json.dumps({'success': False, 'error': str(e)})

@mcp.tool()
async def hotkey(keys: list) -> str:
    """
    Press a hotkey combination.
    
    Args:
        keys: List of keys to press together (e.g., ['ctrl', 'c'] for copy)
    """
    if not keys:
        return json.dumps({'success': False, 'error': 'No keys provided'})
    
    # Last key is the main key, rest are modifiers
    modifiers = keys[:-1]
    main_key = keys[-1]
    
    return await press_key(main_key, modifiers)

@mcp.tool()
async def run_command(command: str, timeout_sec: int = 30) -> str:
    """
    Run a shell command (with safety restrictions).
    
    Args:
        command: Command to run
        timeout_sec: Timeout in seconds
    """
    # Safety: Block dangerous commands
    blocked = ['rm -rf', 'mkfs', 'dd if=', ':(){', 'chmod -R 777 /']
    for pattern in blocked:
        if pattern in command:
            return json.dumps({'success': False, 'error': 'Command blocked for safety'})
    
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout_sec
        )
        return json.dumps({
            'success': result.returncode == 0,
            'stdout': result.stdout[:5000],  # Limit output
            'stderr': result.stderr[:1000],
            'returncode': result.returncode
        })
    except subprocess.TimeoutExpired:
        return json.dumps({'success': False, 'error': 'Command timed out'})
    except Exception as e:
        return json.dumps({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print('🖥️  ROXY Desktop MCP Server')
    print('   Tools: type_text, press_key, mouse_move, mouse_click,')
    print('          get_clipboard, set_clipboard, take_screenshot,')
    print('          hotkey, run_command')
    mcp.run()
