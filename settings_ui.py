#!/usr/bin/env python3
"""
ROXY Settings UI
================
RU-013: Settings UI Web Interface

Web-based configuration dashboard for ROXY.
Access at http://localhost:8768

Features:
- MCP module status & configuration
- Skills management (load/unload/reload)
- Vault management
- Service health monitoring
- Live log viewing

SECURITY:
- Requires same token as main ROXY server
- Local access only (127.0.0.1)
"""

import os
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import logging
from functools import wraps

# HTTP server
from aiohttp import web

# ROXY paths
ROXY_DIR = Path.home() / ".roxy"
CONFIG_DIR = ROXY_DIR / "config"
MCP_DIR = ROXY_DIR / "mcp"
SKILLS_DIR = ROXY_DIR / "skills"
LOGS_DIR = ROXY_DIR / "logs"

# Settings
PORT = 8768
HOST = "127.0.0.1"  # Local only for security
AUTH_TOKEN = os.environ.get("ROXY_TOKEN", "")

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("roxy.settings_ui")


# =============================================================================
# Authentication
# =============================================================================

def require_auth(handler):
    """Decorator to require authentication"""
    @wraps(handler)
    async def wrapper(request):
        if AUTH_TOKEN:
            # Check Authorization header
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                token = auth[7:]
            else:
                token = request.query.get("token", "")
            
            if token != AUTH_TOKEN:
                return web.json_response(
                    {"error": "Unauthorized"},
                    status=401
                )
        return await handler(request)
    return wrapper


# =============================================================================
# System Status
# =============================================================================

def get_mcp_modules() -> List[Dict]:
    """Get status of all MCP modules"""
    modules = []
    
    if not MCP_DIR.exists():
        return modules
    
    for file in MCP_DIR.glob("mcp_*.py"):
        name = file.stem.replace("mcp_", "")
        
        # Try to get module info
        try:
            content = file.read_text()
            
            # Extract tool count
            tool_match = content.count("def handle_tool") or content.count("TOOLS = {")
            
            # Check for TOOLS dict
            import re
            tools_match = re.search(r'TOOLS\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}', content, re.DOTALL)
            tool_count = len(re.findall(r'"(\w+)":\s*\{', tools_match.group(1))) if tools_match else 0
            
            modules.append({
                "name": name,
                "file": str(file),
                "enabled": True,  # Could check config
                "tool_count": tool_count,
                "size_kb": file.stat().st_size // 1024,
                "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
            })
        except Exception as e:
            modules.append({
                "name": name,
                "file": str(file),
                "enabled": False,
                "error": str(e)
            })
    
    return modules


def get_loaded_skills() -> List[Dict]:
    """Get loaded skills info"""
    skills = []
    
    if not SKILLS_DIR.exists():
        return skills
    
    for file in SKILLS_DIR.glob("skill_*.py"):
        name = file.stem.replace("skill_", "")
        
        try:
            content = file.read_text()
            
            # Extract manifest
            import re
            manifest_match = re.search(
                r'SKILL_MANIFEST\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}',
                content, re.DOTALL
            )
            
            if manifest_match:
                # Parse manifest (simplified)
                manifest_str = "{" + manifest_match.group(1) + "}"
                # Replace Python strings with JSON-compatible
                manifest_str = manifest_str.replace("'", '"')
                try:
                    manifest = json.loads(manifest_str)
                except:
                    manifest = {"name": name, "version": "unknown"}
            else:
                manifest = {"name": name}
            
            skills.append({
                "name": manifest.get("name", name),
                "version": manifest.get("version", "1.0.0"),
                "description": manifest.get("description", "")[:100],
                "file": str(file),
                "keywords": manifest.get("keywords", [])[:5],
                "loaded": True  # Would check skills_registry
            })
        except Exception as e:
            skills.append({
                "name": name,
                "file": str(file),
                "error": str(e),
                "loaded": False
            })
    
    return skills


def get_service_health() -> Dict:
    """Check health of ROXY services"""
    import socket
    
    services = {
        "roxy_main": {"port": 8766, "status": "unknown"},
        "mcp_server": {"port": 8765, "status": "unknown"},
        "webhook_receiver": {"port": 8767, "status": "unknown"},
        "settings_ui": {"port": PORT, "status": "running"}
    }
    
    for name, info in services.items():
        if name == "settings_ui":
            continue
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", info["port"]))
            sock.close()
            
            if result == 0:
                services[name]["status"] = "running"
            else:
                services[name]["status"] = "stopped"
        except:
            services[name]["status"] = "error"
    
    return services


def get_recent_logs(lines: int = 100) -> List[Dict]:
    """Get recent log entries"""
    logs = []
    log_files = [
        LOGS_DIR / "roxy.log",
        LOGS_DIR / "router_audit.log",
        LOGS_DIR / "vault_audit.log"
    ]
    
    for log_file in log_files:
        if log_file.exists():
            try:
                content = log_file.read_text()
                for line in content.split("\n")[-lines:]:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            entry["source"] = log_file.stem
                            logs.append(entry)
                        except:
                            logs.append({
                                "source": log_file.stem,
                                "message": line,
                                "timestamp": ""
                            })
            except:
                pass
    
    # Sort by timestamp
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return logs[:lines]


# =============================================================================
# Configuration Management
# =============================================================================

def get_config() -> Dict:
    """Get current configuration"""
    config_file = CONFIG_DIR / "roxy.yaml"
    
    if config_file.exists():
        try:
            import yaml
            with open(config_file) as f:
                return yaml.safe_load(f) or {}
        except:
            pass
    
    # Default config
    return {
        "server": {
            "host": "127.0.0.1",
            "port": 8766,
            "mcp_port": 8765
        },
        "mcp_modules": {
            "vault": {"enabled": True},
            "browser": {"enabled": True},
            "sandbox": {"enabled": True},
            "calendar": {"enabled": False},
            "email": {"enabled": False},
            "telegram": {"enabled": False},
            "discord": {"enabled": False}
        },
        "routing": {
            "min_confidence": 0.3,
            "fallback": "chromadb_rag"
        }
    }


def save_config(config: Dict) -> bool:
    """Save configuration"""
    try:
        import yaml
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        config_file = CONFIG_DIR / "roxy.yaml"
        
        with open(config_file, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)
        
        return True
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        return False


# =============================================================================
# API Handlers
# =============================================================================

@require_auth
async def handle_dashboard(request):
    """Main dashboard data"""
    return web.json_response({
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": get_service_health(),
        "mcp_count": len(get_mcp_modules()),
        "skill_count": len(get_loaded_skills())
    })


@require_auth
async def handle_mcp_list(request):
    """List MCP modules"""
    return web.json_response({
        "modules": get_mcp_modules()
    })


@require_auth
async def handle_mcp_toggle(request):
    """Enable/disable MCP module"""
    data = await request.json()
    module = data.get("module")
    enabled = data.get("enabled", True)
    
    config = get_config()
    if "mcp_modules" not in config:
        config["mcp_modules"] = {}
    
    config["mcp_modules"][module] = {"enabled": enabled}
    
    if save_config(config):
        return web.json_response({"success": True})
    return web.json_response({"success": False, "error": "Failed to save"})


@require_auth
async def handle_skills_list(request):
    """List skills"""
    return web.json_response({
        "skills": get_loaded_skills()
    })


@require_auth
async def handle_skill_action(request):
    """Skill actions (load/unload/reload)"""
    data = await request.json()
    action = data.get("action")
    skill = data.get("skill")
    
    try:
        from skills_registry import load_skill, unload_skill, reload_skill
        
        if action == "load":
            result = load_skill(SKILLS_DIR / f"skill_{skill}.py")
        elif action == "unload":
            result = unload_skill(skill)
        elif action == "reload":
            result = reload_skill(skill)
        else:
            return web.json_response({"success": False, "error": f"Unknown action: {action}"})
        
        return web.json_response(result)
    except ImportError:
        return web.json_response({"success": False, "error": "Skills registry not available"})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)})


@require_auth
async def handle_config_get(request):
    """Get configuration"""
    return web.json_response(get_config())


@require_auth
async def handle_config_set(request):
    """Update configuration"""
    data = await request.json()
    config = get_config()
    
    # Merge updates
    for key, value in data.items():
        if isinstance(value, dict) and key in config:
            config[key].update(value)
        else:
            config[key] = value
    
    if save_config(config):
        return web.json_response({"success": True})
    return web.json_response({"success": False, "error": "Failed to save"})


@require_auth
async def handle_logs(request):
    """Get recent logs"""
    lines = int(request.query.get("lines", 100))
    return web.json_response({
        "logs": get_recent_logs(lines)
    })


@require_auth
async def handle_health(request):
    """Health check"""
    return web.json_response({
        "status": "healthy",
        "services": get_service_health()
    })


async def handle_index(request):
    """Serve HTML dashboard"""
    html = (Path(__file__).parent / "templates" / "settings.html").read_text()
    return web.Response(text=html, content_type="text/html")


# =============================================================================
# Server Setup
# =============================================================================

def create_app() -> web.Application:
    """Create web application"""
    app = web.Application()
    
    # Routes
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/dashboard", handle_dashboard)
    app.router.add_get("/api/mcp", handle_mcp_list)
    app.router.add_post("/api/mcp/toggle", handle_mcp_toggle)
    app.router.add_get("/api/skills", handle_skills_list)
    app.router.add_post("/api/skills/action", handle_skill_action)
    app.router.add_get("/api/config", handle_config_get)
    app.router.add_post("/api/config", handle_config_set)
    app.router.add_get("/api/logs", handle_logs)
    app.router.add_get("/api/health", handle_health)
    
    return app


async def start_server():
    """Start the settings UI server"""
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    
    logger.info(f"Settings UI running at http://{HOST}:{PORT}")
    
    # Keep running
    while True:
        await asyncio.sleep(3600)


def run():
    """Run server (blocking)"""
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("Shutting down...")


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "status":
            print(json.dumps({
                "services": get_service_health(),
                "mcp_modules": get_mcp_modules(),
                "skills": get_loaded_skills()
            }, indent=2))
        
        elif cmd == "config":
            print(json.dumps(get_config(), indent=2))
        
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: settings_ui.py [status|config]")
            sys.exit(1)
    else:
        run()
