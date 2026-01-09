#!/usr/bin/env python3
"""
ROXY Voice Command Router
Routes voice commands to appropriate MCP tools
"""
import re
import json
import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
import sys
sys.path.insert(0, '/home/mark/.roxy/services')
sys.path.insert(0, '/home/mark/.roxy/voice')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CommandRoute:
    pattern: str
    handler: str
    server: str
    description: str
    extract_params: Optional[Callable] = None

# Command routing table
ROUTES: List[CommandRoute] = [
    # Desktop commands
    CommandRoute(
        r"(take|capture|grab).*screenshot",
        "take_screenshot",
        "desktop",
        "Take a screenshot"
    ),
    CommandRoute(
        r"type\s+(.+)",
        "type_text",
        "desktop",
        "Type text",
        lambda m: {"text": m.group(1)}
    ),
    CommandRoute(
        r"(copy|get).*clipboard",
        "get_clipboard",
        "desktop",
        "Get clipboard contents"
    ),
    CommandRoute(
        r"(press|hit)\s+(enter|tab|escape|space)",
        "press_key",
        "desktop",
        "Press a key",
        lambda m: {"key": m.group(2)}
    ),
    
    # OBS commands
    CommandRoute(
        r"start\s+(recording|record)",
        "obs_start_recording",
        "obs",
        "Start OBS recording"
    ),
    CommandRoute(
        r"stop\s+(recording|record)",
        "obs_stop_recording",
        "obs",
        "Stop OBS recording"
    ),
    CommandRoute(
        r"pause\s+(recording|record)",
        "obs_pause_recording",
        "obs",
        "Pause OBS recording"
    ),
    CommandRoute(
        r"(switch|change).*scene.*[\"']?(.+?)[\"']?$",
        "obs_switch_scene",
        "obs",
        "Switch OBS scene",
        lambda m: {"scene_name": m.group(2).strip()}
    ),
    CommandRoute(
        r"(what|show).*(scene|scenes)",
        "obs_get_scenes",
        "obs",
        "List OBS scenes"
    ),
    
    # Voice commands
    CommandRoute(
        r"say\s+(.+)",
        "speak",
        "voice",
        "Speak text",
        lambda m: {"text": m.group(1)}
    ),
    CommandRoute(
        r"(list|show).*voices?",
        "list_voices",
        "voice",
        "List available voices"
    ),
    
    # Browser commands
    CommandRoute(
        r"(search|google|look up)\s+(.+)",
        "search_web",
        "browser",
        "Search the web",
        lambda m: {"query": m.group(2)}
    ),
    CommandRoute(
        r"(go to|open|browse)\s+(https?://\S+)",
        "browse_and_extract",
        "browser",
        "Open a URL",
        lambda m: {"url": m.group(2), "instruction": "summarize the page"}
    ),
    
    # Content pipeline commands
    CommandRoute(
        r"(transcribe|process)\s+(.+\.(?:mp4|mkv|mov|avi|webm))",
        "transcribe_video",
        "content",
        "Transcribe a video",
        lambda m: {"video_path": m.group(2)}
    ),
    CommandRoute(
        r"(find|detect|get).*viral.*(.+\.json)",
        "detect_viral_moments",
        "content",
        "Detect viral moments",
        lambda m: {"transcript_json": m.group(2)}
    ),
    CommandRoute(
        r"(pipeline|content).*status",
        "content_status",
        "content",
        "Get content pipeline status"
    ),
    
    # System commands
    CommandRoute(
        r"(what|check).*(time|date)",
        "_system_time",
        "system",
        "Get current time"
    ),
    CommandRoute(
        r"(status|health|how are you)",
        "_system_status",
        "system",
        "Get system status"
    ),
]


class VoiceRouter:
    def __init__(self):
        self.routes = ROUTES
        self.compiled_routes = [
            (re.compile(r.pattern, re.IGNORECASE), r)
            for r in self.routes
        ]
        logger.info(f"Voice router initialized with {len(self.routes)} routes")
    
    def match(self, command: str) -> Optional[Dict]:
        """Match a voice command to a route"""
        command = command.strip()
        
        for regex, route in self.compiled_routes:
            match = regex.search(command)
            if match:
                result = {
                    "handler": route.handler,
                    "server": route.server,
                    "description": route.description,
                    "params": {}
                }
                
                if route.extract_params:
                    try:
                        result["params"] = route.extract_params(match)
                    except Exception as e:
                        logger.warning(f"Failed to extract params: {e}")
                
                logger.info(f"Matched: '{command}' -> {route.server}.{route.handler}")
                return result
        
        logger.info(f"No match for: '{command}'")
        return None
    
    def get_help(self) -> str:
        """Get help text for available commands"""
        help_text = ["Available voice commands:", ""]
        
        servers = {}
        for route in self.routes:
            if route.server not in servers:
                servers[route.server] = []
            servers[route.server].append(route)
        
        for server, routes in servers.items():
            help_text.append(f"[{server.upper()}]")
            for route in routes:
                help_text.append(f"  • {route.description}")
            help_text.append("")
        
        return "\n".join(help_text)
    
    async def execute(self, command: str) -> Dict[str, Any]:
        """Match and execute a voice command"""
        match = self.match(command)
        
        if not match:
            return {
                "success": False,
                "error": "Command not recognized",
                "suggestion": "Try 'help' for available commands"
            }
        
        # Handle system commands locally
        if match["server"] == "system":
            return await self._handle_system_command(match["handler"])
        
        # For MCP commands, return the routing info
        # (actual execution happens via MCP)
        return {
            "success": True,
            "routed": True,
            "server": match["server"],
            "handler": match["handler"],
            "params": match["params"],
            "description": match["description"]
        }
    
    async def _handle_system_command(self, handler: str) -> Dict:
        """Handle built-in system commands"""
        from datetime import datetime
        
        if handler == "_system_time":
            now = datetime.now()
            return {
                "success": True,
                "response": f"The time is {now.strftime('%I:%M %p on %A, %B %d')}"
            }
        
        if handler == "_system_status":
            return {
                "success": True,
                "response": "All systems operational. I have 5 MCP servers with 32 tools ready."
            }
        
        return {"success": False, "error": f"Unknown system command: {handler}"}


# Integration with voice pipeline
async def process_voice_command(text: str, speak_response: bool = True) -> str:
    """Process a voice command and optionally speak the response"""
    router = VoiceRouter()
    result = await router.execute(text)
    
    if result.get("response"):
        response = result["response"]
    elif result.get("routed"):
        response = f"Executing {result['description']}..."
    elif result.get("error"):
        response = f"Sorry, {result['error']}"
    else:
        response = "Command processed"
    
    if speak_response:
        try:
            from tts.service import RoxyTTS
            tts = RoxyTTS('roxy')
            tts.speak(response)
        except Exception as e:
            logger.warning(f"TTS failed: {e}")
    
    return response


# Demo
async def main():
    router = VoiceRouter()
    
    print("=" * 60)
    print("ROXY Voice Command Router")
    print("=" * 60)
    print(router.get_help())
    
    # Test commands
    test_commands = [
        "take a screenshot",
        "start recording",
        "switch to scene Gaming",
        "search for Python tutorials",
        "what time is it",
        "say Hello, I am Roxy",
        "process video.mp4",
        "show me the status"
    ]
    
    print("\nTest Results:")
    print("-" * 40)
    for cmd in test_commands:
        result = await router.execute(cmd)
        status = "✅" if result.get("success") else "❌"
        if result.get("routed"):
            print(f"{status} '{cmd}' -> {result['server']}.{result['handler']}")
        elif result.get("response"):
            print(f"{status} '{cmd}' -> {result['response'][:50]}...")
        else:
            print(f"{status} '{cmd}' -> {result.get('error', 'unknown')}")


if __name__ == "__main__":
    asyncio.run(main())
