#!/usr/bin/env python3
"""
Skills Registry - Dynamic Skills Discovery & Loading
=====================================================
RU-010: Skills Registry System

Dynamic skills system for ROXY:
- Auto-discovers skill_*.py modules in skills directory
- Loads/unloads skills at runtime
- Registers skill tools with MCP
- Manages skill dependencies

Features:
- Hot reload support
- Capability-based discovery
- Version tracking
- Dependency resolution

SECURITY INVARIANTS:
1. Skills loaded only from trusted directory
2. No arbitrary code execution
3. All loads/unloads logged
"""

import os
import sys
import json
import importlib
import importlib.util
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional, Dict, List, Callable
from dataclasses import dataclass, asdict, field
import threading

# Paths
ROXY_DIR = Path.home() / ".roxy"
SKILLS_DIR = ROXY_DIR / "skills"
CONFIG_DIR = ROXY_DIR / "config"
AUDIT_LOG = ROXY_DIR / "logs" / "skills_audit.log"

# Ensure skills directory exists
SKILLS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class SkillManifest:
    """Skill metadata structure"""
    name: str
    version: str
    description: str
    author: str = ""
    capabilities: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)


@dataclass
class LoadedSkill:
    """Runtime skill instance"""
    manifest: SkillManifest
    module: Any
    loaded_at: str
    file_path: str
    active: bool = True


# Registry state
_loaded_skills: Dict[str, LoadedSkill] = {}
_skill_tools: Dict[str, Callable] = {}  # tool_name -> handler
_lock = threading.Lock()


def _audit_log(operation: str, details: str = "", success: bool = True):
    """Write to audit log"""
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    log_entry = {
        "timestamp": timestamp,
        "operation": operation,
        "success": success,
        "details": details[:200]
    }
    
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def discover_skills() -> List[Dict]:
    """
    Discover all skill_*.py modules in skills directory
    
    Returns:
        List of skill info dicts (not loaded yet)
    """
    skills = []
    
    for skill_file in SKILLS_DIR.glob("skill_*.py"):
        try:
            # Read file to find SKILL_MANIFEST
            content = skill_file.read_text()
            
            # Quick check for manifest
            if "SKILL_MANIFEST" not in content:
                continue
            
            # Load module temporarily to get manifest
            spec = importlib.util.spec_from_file_location(
                skill_file.stem, 
                skill_file
            )
            module = importlib.util.module_from_spec(spec)
            
            # Don't execute, just parse
            # For safety, we'll extract manifest from file content
            manifest_info = _extract_manifest_from_source(content)
            
            if manifest_info:
                skills.append({
                    "name": manifest_info.get("name", skill_file.stem),
                    "file": str(skill_file),
                    "loaded": skill_file.stem in _loaded_skills,
                    "manifest": manifest_info
                })
        except Exception as e:
            _audit_log("discover_error", f"{skill_file.name}: {e}", False)
    
    return skills


def _extract_manifest_from_source(source: str) -> Optional[Dict]:
    """Extract SKILL_MANIFEST dict from source without executing"""
    import ast
    
    try:
        tree = ast.parse(source)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "SKILL_MANIFEST":
                        # Safely evaluate the manifest dict
                        if isinstance(node.value, ast.Dict):
                            return ast.literal_eval(ast.unparse(node.value))
    except:
        pass
    
    return None


def load_skill(skill_name: str) -> Dict:
    """
    Load a skill module
    
    Args:
        skill_name: Name of skill (without skill_ prefix) or full filename
    
    Returns:
        {"success": True, "skill": {...}}
    """
    with _lock:
        # Normalize name
        if not skill_name.startswith("skill_"):
            skill_name = f"skill_{skill_name}"
        if skill_name.endswith(".py"):
            skill_name = skill_name[:-3]
        
        # Check if already loaded
        if skill_name in _loaded_skills:
            return {"success": False, "error": f"Skill {skill_name} already loaded"}
        
        # Find skill file
        skill_file = SKILLS_DIR / f"{skill_name}.py"
        if not skill_file.exists():
            return {"success": False, "error": f"Skill file not found: {skill_file}"}
        
        try:
            # Load module
            spec = importlib.util.spec_from_file_location(skill_name, skill_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[skill_name] = module
            spec.loader.exec_module(module)
            
            # Get manifest
            if not hasattr(module, "SKILL_MANIFEST"):
                return {"success": False, "error": "Skill missing SKILL_MANIFEST"}
            
            manifest_dict = module.SKILL_MANIFEST
            manifest = SkillManifest(
                name=manifest_dict.get("name", skill_name),
                version=manifest_dict.get("version", "0.0.0"),
                description=manifest_dict.get("description", ""),
                author=manifest_dict.get("author", ""),
                capabilities=manifest_dict.get("capabilities", []),
                tools=list(manifest_dict.get("tools", {}).keys()),
                dependencies=manifest_dict.get("dependencies", []),
                keywords=manifest_dict.get("keywords", [])
            )
            
            # Check dependencies
            for dep in manifest.dependencies:
                dep_name = f"skill_{dep}" if not dep.startswith("skill_") else dep
                if dep_name not in _loaded_skills:
                    return {"success": False, "error": f"Missing dependency: {dep}"}
            
            # Register tools
            if hasattr(module, "SKILL_MANIFEST") and "tools" in module.SKILL_MANIFEST:
                for tool_name, tool_info in module.SKILL_MANIFEST["tools"].items():
                    full_name = f"{skill_name}.{tool_name}"
                    if hasattr(module, "handle_tool"):
                        _skill_tools[full_name] = lambda n, p, m=module, t=tool_name: m.handle_tool(t, p)
            
            # Store loaded skill
            loaded = LoadedSkill(
                manifest=manifest,
                module=module,
                loaded_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                file_path=str(skill_file),
                active=True
            )
            _loaded_skills[skill_name] = loaded
            
            _audit_log("load_skill", f"{skill_name} v{manifest.version}")
            
            return {
                "success": True,
                "skill": {
                    "name": manifest.name,
                    "version": manifest.version,
                    "tools": manifest.tools,
                    "capabilities": manifest.capabilities
                }
            }
            
        except Exception as e:
            _audit_log("load_error", f"{skill_name}: {e}", False)
            return {"success": False, "error": str(e)}


def unload_skill(skill_name: str) -> Dict:
    """
    Unload a skill module
    
    Args:
        skill_name: Name of skill to unload
    
    Returns:
        {"success": True}
    """
    with _lock:
        # Normalize name
        if not skill_name.startswith("skill_"):
            skill_name = f"skill_{skill_name}"
        
        if skill_name not in _loaded_skills:
            return {"success": False, "error": f"Skill {skill_name} not loaded"}
        
        skill = _loaded_skills[skill_name]
        
        # Check if other skills depend on this
        for other_name, other_skill in _loaded_skills.items():
            if skill_name in [f"skill_{d}" for d in other_skill.manifest.dependencies]:
                return {"success": False, "error": f"Skill {other_name} depends on {skill_name}"}
        
        # Remove tools
        tools_to_remove = [t for t in _skill_tools if t.startswith(f"{skill_name}.")]
        for tool in tools_to_remove:
            del _skill_tools[tool]
        
        # Remove from sys.modules
        if skill_name in sys.modules:
            del sys.modules[skill_name]
        
        # Remove from registry
        del _loaded_skills[skill_name]
        
        _audit_log("unload_skill", skill_name)
        
        return {"success": True}


def reload_skill(skill_name: str) -> Dict:
    """Reload a skill (unload then load)"""
    if not skill_name.startswith("skill_"):
        skill_name = f"skill_{skill_name}"
    
    if skill_name in _loaded_skills:
        result = unload_skill(skill_name)
        if not result["success"]:
            return result
    
    return load_skill(skill_name)


def list_skills() -> Dict:
    """
    List all skills (discovered and loaded)
    
    Returns:
        {"discovered": [...], "loaded": [...]}
    """
    discovered = discover_skills()
    
    loaded = []
    for name, skill in _loaded_skills.items():
        loaded.append({
            "name": skill.manifest.name,
            "version": skill.manifest.version,
            "capabilities": skill.manifest.capabilities,
            "tools": skill.manifest.tools,
            "loaded_at": skill.loaded_at,
            "active": skill.active
        })
    
    return {
        "success": True,
        "discovered": discovered,
        "loaded": loaded
    }


def get_skill(skill_name: str) -> Dict:
    """Get detailed info about a skill"""
    if not skill_name.startswith("skill_"):
        skill_name = f"skill_{skill_name}"
    
    if skill_name not in _loaded_skills:
        return {"success": False, "error": "Skill not loaded"}
    
    skill = _loaded_skills[skill_name]
    
    return {
        "success": True,
        "skill": {
            "name": skill.manifest.name,
            "version": skill.manifest.version,
            "description": skill.manifest.description,
            "author": skill.manifest.author,
            "capabilities": skill.manifest.capabilities,
            "tools": skill.manifest.tools,
            "dependencies": skill.manifest.dependencies,
            "keywords": skill.manifest.keywords,
            "loaded_at": skill.loaded_at,
            "file_path": skill.file_path,
            "active": skill.active
        }
    }


def find_skill_by_capability(capability: str) -> List[str]:
    """Find skills that have a specific capability"""
    matching = []
    for name, skill in _loaded_skills.items():
        if capability in skill.manifest.capabilities:
            matching.append(name)
    return matching


def find_skill_by_keyword(keyword: str) -> List[str]:
    """Find skills matching a keyword"""
    keyword = keyword.lower()
    matching = []
    for name, skill in _loaded_skills.items():
        if keyword in [k.lower() for k in skill.manifest.keywords]:
            matching.append(name)
        elif keyword in skill.manifest.description.lower():
            matching.append(name)
    return matching


def call_skill_tool(skill_name: str, tool_name: str, params: Dict) -> Any:
    """Call a specific tool from a loaded skill"""
    if not skill_name.startswith("skill_"):
        skill_name = f"skill_{skill_name}"
    
    full_name = f"{skill_name}.{tool_name}"
    
    if full_name not in _skill_tools:
        return {"success": False, "error": f"Tool not found: {full_name}"}
    
    try:
        return _skill_tools[full_name](tool_name, params)
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_all_skill_tools() -> Dict[str, Dict]:
    """Get all registered skill tools"""
    tools = {}
    for name, skill in _loaded_skills.items():
        if hasattr(skill.module, "SKILL_MANIFEST"):
            manifest = skill.module.SKILL_MANIFEST
            if "tools" in manifest:
                for tool_name, tool_info in manifest["tools"].items():
                    tools[f"{name}.{tool_name}"] = tool_info
    return tools


# =============================================================================
# MCP Interface
# =============================================================================

TOOLS = {
    "discover": {
        "description": "Discover available skills in skills directory",
        "parameters": {},
        "required": []
    },
    "load": {
        "description": "Load a skill by name",
        "parameters": {
            "skill_name": {"type": "string", "description": "Skill name (e.g., 'web_research')"}
        },
        "required": ["skill_name"]
    },
    "unload": {
        "description": "Unload a skill",
        "parameters": {
            "skill_name": {"type": "string"}
        },
        "required": ["skill_name"]
    },
    "reload": {
        "description": "Reload a skill (hot reload)",
        "parameters": {
            "skill_name": {"type": "string"}
        },
        "required": ["skill_name"]
    },
    "list": {
        "description": "List all discovered and loaded skills",
        "parameters": {},
        "required": []
    },
    "info": {
        "description": "Get detailed skill info",
        "parameters": {
            "skill_name": {"type": "string"}
        },
        "required": ["skill_name"]
    },
    "find_capability": {
        "description": "Find skills with a capability",
        "parameters": {
            "capability": {"type": "string"}
        },
        "required": ["capability"]
    },
    "call_tool": {
        "description": "Call a skill tool",
        "parameters": {
            "skill_name": {"type": "string"},
            "tool_name": {"type": "string"},
            "params": {"type": "object"}
        },
        "required": ["skill_name", "tool_name"]
    }
}


def handle_tool(name: str, params: dict) -> Any:
    """MCP tool handler"""
    handlers = {
        "discover": lambda p: {"success": True, "skills": discover_skills()},
        "load": lambda p: load_skill(p["skill_name"]),
        "unload": lambda p: unload_skill(p["skill_name"]),
        "reload": lambda p: reload_skill(p["skill_name"]),
        "list": lambda p: list_skills(),
        "info": lambda p: get_skill(p["skill_name"]),
        "find_capability": lambda p: {"success": True, "skills": find_skill_by_capability(p["capability"])},
        "call_tool": lambda p: call_skill_tool(p["skill_name"], p["tool_name"], p.get("params", {}))
    }
    
    if name not in handlers:
        return {"success": False, "error": f"Unknown tool: {name}"}
    
    return handlers[name](params)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: skills_registry.py <command> [args...]")
        print("Commands: discover, load <name>, unload <name>, list, info <name>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "discover":
        result = {"skills": discover_skills()}
    elif cmd == "load" and len(sys.argv) >= 3:
        result = load_skill(sys.argv[2])
    elif cmd == "unload" and len(sys.argv) >= 3:
        result = unload_skill(sys.argv[2])
    elif cmd == "list":
        result = list_skills()
    elif cmd == "info" and len(sys.argv) >= 3:
        result = get_skill(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
    
    print(json.dumps(result, indent=2))
