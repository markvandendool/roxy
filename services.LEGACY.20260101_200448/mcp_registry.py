#!/usr/bin/env python3
"""
ROXY MCP Server Registry
Central registry for all MCP servers with health monitoring
"""
import os
import json
import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MCP_BASE_DIR = "/home/mark/.roxy/mcp-servers"
REGISTRY_FILE = "/home/mark/.roxy/config/mcp-registry.json"

@dataclass
class MCPServer:
    name: str
    path: str
    description: str
    tools: List[str]
    status: str = "unknown"
    port: Optional[int] = None
    pid: Optional[int] = None

# Server definitions
SERVERS = {
    "browser": {
        "path": f"{MCP_BASE_DIR}/browser/server.py",
        "description": "Web browsing and automation",
        "tools": ["browse_and_extract", "search_web", "fill_form", "screenshot_page"]
    },
    "desktop": {
        "path": f"{MCP_BASE_DIR}/desktop/server.py",
        "description": "Desktop control via ydotool",
        "tools": ["type_text", "press_key", "mouse_move", "mouse_click", 
                  "get_clipboard", "set_clipboard", "take_screenshot", "hotkey", "run_command"]
    },
    "voice": {
        "path": f"{MCP_BASE_DIR}/voice/server.py",
        "description": "Text-to-speech with Piper",
        "tools": ["speak", "synthesize_audio", "list_voices", "test_speaker"]
    },
    "obs": {
        "path": f"{MCP_BASE_DIR}/obs/server.py",
        "description": "OBS Studio control",
        "tools": ["obs_get_status", "obs_start_recording", "obs_stop_recording",
                  "obs_pause_recording", "obs_resume_recording", "obs_get_scenes",
                  "obs_switch_scene", "obs_get_record_directory", "obs_take_screenshot"]
    },
    "content": {
        "path": f"{MCP_BASE_DIR}/content/server.py",
        "description": "Content pipeline control",
        "tools": ["content_status", "transcribe_video", "detect_viral_moments",
                  "extract_clips", "queue_video", "run_full_pipeline"]
    }
}

class MCPRegistry:
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self._load_registry()
    
    def _load_registry(self):
        """Load or initialize the registry"""
        for name, config in SERVERS.items():
            self.servers[name] = MCPServer(
                name=name,
                path=config["path"],
                description=config["description"],
                tools=config["tools"]
            )
        logger.info(f"Registry loaded: {len(self.servers)} servers")
    
    def check_server_health(self, name: str) -> str:
        """Check if a server file exists and is valid Python"""
        server = self.servers.get(name)
        if not server:
            return "not_found"
        
        if not os.path.exists(server.path):
            return "missing"
        
        # Check if it's valid Python
        try:
            result = subprocess.run(
                ["python3", "-m", "py_compile", server.path],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return "ready"
            else:
                return "syntax_error"
        except Exception:
            return "error"
    
    def get_all_tools(self) -> List[Dict]:
        """Get all available tools across all servers"""
        tools = []
        for name, server in self.servers.items():
            for tool in server.tools:
                tools.append({
                    "name": tool,
                    "server": name,
                    "description": f"{tool} from {server.description}"
                })
        return tools
    
    def find_tool(self, tool_name: str) -> Optional[Dict]:
        """Find which server provides a specific tool"""
        for name, server in self.servers.items():
            if tool_name in server.tools:
                return {
                    "tool": tool_name,
                    "server": name,
                    "path": server.path
                }
        return None
    
    def get_status(self) -> Dict:
        """Get status of all servers"""
        status = {}
        for name in self.servers:
            health = self.check_server_health(name)
            self.servers[name].status = health
            status[name] = {
                "status": health,
                "path": self.servers[name].path,
                "tools": len(self.servers[name].tools),
                "description": self.servers[name].description
            }
        return status
    
    def to_claude_config(self) -> Dict:
        """Generate Claude MCP configuration format"""
        config = {
            "mcpServers": {}
        }
        
        for name, server in self.servers.items():
            config["mcpServers"][f"roxy-{name}"] = {
                "command": "python3",
                "args": [server.path],
                "env": {
                    "PYTHONPATH": "/home/mark/.roxy"
                }
            }
        
        return config
    
    def save_claude_config(self, output_path: str = None):
        """Save Claude MCP configuration to file"""
        if output_path is None:
            output_path = "/home/mark/.roxy/config/claude-mcp.json"
        
        config = self.to_claude_config()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Claude MCP config saved: {output_path}")
        return output_path
    
    def export_registry(self, output_path: str = None):
        """Export full registry to JSON"""
        if output_path is None:
            output_path = REGISTRY_FILE
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        data = {
            "servers": {name: asdict(server) for name, server in self.servers.items()},
            "total_tools": len(self.get_all_tools()),
            "status": self.get_status()
        }
        
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Registry exported: {output_path}")
        return output_path


def main():
    registry = MCPRegistry()
    
    print("=" * 60)
    print("ROXY MCP Server Registry")
    print("=" * 60)
    
    # Check all servers
    status = registry.get_status()
    print("\nServer Status:")
    for name, info in status.items():
        icon = "✅" if info["status"] == "ready" else "❌"
        print(f"  {icon} {name}: {info['status']} ({info['tools']} tools)")
        print(f"      {info['description']}")
    
    # List all tools
    tools = registry.get_all_tools()
    print(f"\nTotal Tools: {len(tools)}")
    
    # Generate configs
    registry.export_registry()
    registry.save_claude_config()
    
    print("\nConfigs saved:")
    print(f"  - {REGISTRY_FILE}")
    print(f"  - /home/mark/.roxy/config/claude-mcp.json")


if __name__ == "__main__":
    main()
