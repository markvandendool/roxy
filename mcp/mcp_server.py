#!/usr/bin/env python3
"""
Unified MCP Server - Central hub for all MCP tools
Part of LUNA-000 CITADEL P6: MCP Architecture

Runs as HTTP server exposing all MCP tools via JSON-RPC style API.
"""

import json
import importlib.util
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

MCP_DIR = Path(__file__).parent
PORT = 8765

# Load all MCP modules
MODULES = {}
TOOLS = {}

def load_modules():
    """Load all mcp_*.py modules"""
    for path in MCP_DIR.glob("mcp_*.py"):
        if path.name == "mcp_server.py":
            continue
        
        name = path.stem.replace("mcp_", "")
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        MODULES[name] = module
        if hasattr(module, "TOOLS"):
            for tool_name, tool_def in module.TOOLS.items():
                TOOLS[tool_name] = {
                    "module": name,
                    "definition": tool_def
                }

class MCPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode()
        
        try:
            request = json.loads(body)
            tool = request.get("tool")
            params = request.get("params", {})
            
            if tool not in TOOLS:
                result = {"error": f"Unknown tool: {tool}"}
            else:
                module_name = TOOLS[tool]["module"]
                module = MODULES[module_name]
                result = module.handle_tool(tool, params)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def do_GET(self):
        """Return list of available tools"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        tool_list = {
            name: info["definition"]
            for name, info in TOOLS.items()
        }
        self.wfile.write(json.dumps({"tools": tool_list}, indent=2).encode())
    
    def log_message(self, format, *args):
        pass  # Suppress logging

def main():
    load_modules()
    print(f"MCP Server starting on port {PORT}")
    print(f"Loaded {len(TOOLS)} tools from {len(MODULES)} modules:")
    for name in sorted(TOOLS.keys()):
        print(f"  - {name}")
    
    server = HTTPServer(("0.0.0.0", PORT), MCPHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down")
        server.shutdown()

if __name__ == "__main__":
    main()
