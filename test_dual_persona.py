#!/usr/bin/env python3
"""
TEST DUAL PERSONA - Simulated voice flow test
==============================================
Tests the dual persona system without requiring wake word hardware.

Usage:
    python3 test_dual_persona.py rocky "What's a C major chord?"
    python3 test_dual_persona.py roxy "How do I check disk space?"
    python3 test_dual_persona.py  # Interactive mode
"""

import asyncio
import json
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

ROXY_URL = "http://localhost:8766"

# Load auth token
TOKEN_FILE = Path.home() / ".roxy" / "secret.token"
AUTH_TOKEN = TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else None

PERSONAS = {
    "rocky": {
        "name": "Rocky 🎸",
        "greeting": "Hey! Rocky here - ready to rock some music!",
        "system_prompt": """You are Rocky, an enthusiastic music teacher AI.
You specialize in:
- Guitar, piano, drums, and bass instruction
- Music theory (chords, scales, progressions, rhythm)
- Song analysis and recommendation
- Practice routines and technique tips

Personality: Encouraging, fun, uses music metaphors, celebrates progress.
Style: Casual but knowledgeable. Use emojis sparingly. Keep responses concise.
You have access to music MCP tools - mention when you'd use them."""
    },
    "roxy": {
        "name": "ROXY ⚡",
        "greeting": "ROXY online. How can I assist?",
        "system_prompt": """You are ROXY, a highly capable dev assistant AI.
You specialize in:
- Software development and debugging
- System administration and DevOps
- Code review and architecture
- Research and documentation

Personality: Efficient, precise, helpful, proactive.
Style: Technical but accessible. Direct and actionable responses.
You have access to MCP tools for file operations, git, docker, and more."""
    }
}


def query_roxy(message: str, persona: str) -> str:
    """Send query to ROXY with persona-specific prompt"""
    config = PERSONAS[persona]
    
    # Format as ROXY command with persona context
    full_prompt = f"[PERSONA: {persona.upper()}]\n{config['system_prompt']}\n\nUser: {message}"
    
    payload = {
        "command": full_prompt,
        "mode": "assistant"  # General assistant mode
    }
    
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if AUTH_TOKEN:
        headers["X-ROXY-Token"] = AUTH_TOKEN
    req = Request(
        f"{ROXY_URL}/run",
        data=body,
        headers=headers,
        method="POST"
    )
    
    try:
        with urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode())
            return data.get("response", data.get("result", data.get("message", "No response")))
    except URLError as e:
        return f"Error: {e}"


def test_music_tool(tool: str, params: dict) -> dict:
    """Call a music MCP tool"""
    payload = params
    body = json.dumps(payload).encode()
    req = Request(
        f"{ROXY_URL}/mcp/music_tools/{tool}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except URLError as e:
        return {"error": str(e)}


def interactive_mode():
    """Run interactive dual persona mode"""
    print("=" * 60)
    print("🎭 DUAL PERSONA TEST - Interactive Mode")
    print("=" * 60)
    print("Commands:")
    print("  rocky <message>  - Talk to Rocky (music)")
    print("  roxy <message>   - Talk to ROXY (dev)")
    print("  play <chord>     - Use music tool")
    print("  scale <root>     - Get scale notes")
    print("  quit             - Exit")
    print("-" * 60)
    
    current_persona = "roxy"
    
    while True:
        try:
            user_input = input(f"\n[{current_persona.upper()}] > ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() == "quit":
                print("👋 Goodbye!")
                break
            
            # Parse command
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            
            # Switch persona
            if cmd in PERSONAS:
                current_persona = cmd
                config = PERSONAS[current_persona]
                print(f"\n{config['name']}: {config['greeting']}")
                
                if len(parts) > 1:
                    message = parts[1]
                    print(f"Processing: {message[:50]}...")
                    response = query_roxy(message, current_persona)
                    print(f"\n{config['name']}: {response}")
                continue
            
            # Music tool shortcuts
            if cmd == "play":
                chord = parts[1] if len(parts) > 1 else "C"
                result = test_music_tool("play_chord", {"chord": chord})
                print(f"\n🎵 {result.get('message', result)}")
                continue
                
            if cmd == "scale":
                root = parts[1] if len(parts) > 1 else "C"
                result = test_music_tool("get_scale", {"root": root, "scale_type": "major"})
                print(f"\n🎼 {result.get('message', result)}")
                continue
            
            # Default: send to current persona
            config = PERSONAS[current_persona]
            response = query_roxy(user_input, current_persona)
            print(f"\n{config['name']}: {response}")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except EOFError:
            break


def main():
    if len(sys.argv) < 2:
        interactive_mode()
        return
    
    persona = sys.argv[1].lower()
    if persona not in PERSONAS:
        print(f"Unknown persona: {persona}")
        print(f"Available: {list(PERSONAS.keys())}")
        sys.exit(1)
    
    if len(sys.argv) < 3:
        # Just greet
        config = PERSONAS[persona]
        print(f"{config['name']}: {config['greeting']}")
        return
    
    message = " ".join(sys.argv[2:])
    config = PERSONAS[persona]
    
    print(f"🎭 Persona: {config['name']}")
    print(f"📝 Query: {message}")
    print("-" * 40)
    
    response = query_roxy(message, persona)
    print(f"\n{config['name']}: {response}")


if __name__ == "__main__":
    main()
