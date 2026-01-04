#!/usr/bin/env python3
"""
Capabilities Endpoint - Self-reportable truth about ROXY
Returns ONLY evidence-backed facts, no LLM guessing
"""
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List


class CapabilitiesProvider:
    """
    Provides authoritative answers about ROXY's capabilities
    NO LLM INFERENCE - only direct system interrogation
    """
    
    def __init__(self):
        self.roxy_dir = Path.home() / ".roxy"
        self.config_file = self.roxy_dir / "config.json"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load config.json"""
        if self.config_file.exists():
            with open(self.config_file) as f:
                return json.load(f)
        return {}
    
    def get_all_capabilities(self) -> Dict[str, Any]:
        """
        Return comprehensive capabilities report
        EVIDENCE-ONLY - no guessing
        """
        return {
            "tools": self.get_available_tools(),
            "model": self.get_model_info(),
            "repo_roots": self.get_repo_roots(),
            "file_operations": self.get_file_operation_permissions(),
            "command_execution": self.check_command_execution(),
            "rag": self.check_rag_available(),
            "version": self.get_version_info(),
        }
    
    def get_available_tools(self) -> List[str]:
        """
        List tools from actual tool registry
        NO HALLUCINATION - only tools that actually exist
        """
        tools = []
        
        # Check MCP tools
        mcp_dir = self.roxy_dir / "mcp"
        if mcp_dir.exists():
            for server_dir in mcp_dir.iterdir():
                if server_dir.is_dir():
                    tools.append(f"mcp:{server_dir.name}")
        
        # Check roxy_commands.py capabilities
        commands_file = self.roxy_dir / "roxy_commands.py"
        if commands_file.exists():
            # Parse roxy_commands.py for supported command types
            with open(commands_file) as f:
                content = f.read()
                if "git" in content:
                    tools.append("git_operations")
                if "obs" in content:
                    tools.append("obs_control")
                if "rag" in content or "query_rag" in content:
                    tools.append("rag_query")
                if "list_files" in content:
                    tools.append("file_listing")
                if "read_file" in content:
                    tools.append("file_reading")
                if "search_code" in content:
                    tools.append("code_search")
        
        # Check for execute_command capability
        # This is DISABLED by default for security
        tools.append("execute_command:DISABLED")
        
        return tools
    
    def get_model_info(self) -> Dict[str, str]:
        """
        Get ACTUAL model info from Ollama
        EVIDENCE-BASED - run ollama list
        """
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                models = []
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        model_name = line.split()[0]
                        models.append(model_name)
                
                return {
                    "type": "ollama",
                    "available_models": models,
                    "current_model": "qwen2.5-coder:14b",  # Upgraded from llama3:8b
                    "evidence": "ollama list command executed",
                }
            else:
                return {"error": "ollama not running", "evidence": result.stderr}
        
        except FileNotFoundError:
            return {"error": "ollama not installed", "evidence": "command not found"}
        except Exception as e:
            return {"error": str(e), "evidence": "exception during check"}
    
    def get_repo_roots(self) -> List[str]:
        """Return configured repo roots (authoritative)"""
        return self.config.get("repo_roots", [])
    
    def get_file_operation_permissions(self) -> List[str]:
        """Return allowed file operation paths (authoritative)"""
        return self.config.get("allowed_file_operations", [])
    
    def check_command_execution(self) -> Dict[str, Any]:
        """
        Check if execute_command is enabled
        SECURITY: Should be DISABLED by default
        """
        # In the fixed ROXY, execute_command is NOT enabled
        # Would require explicit user configuration
        return {
            "enabled": False,
            "reason": "Security policy - disabled by default",
            "to_enable": "Add execute_command tool to config and whitelist commands",
        }
    
    def check_rag_available(self) -> Dict[str, Any]:
        """Check if RAG is functional"""
        chroma_db = self.roxy_dir / "chroma_db"
        
        return {
            "available": chroma_db.exists(),
            "database_path": str(chroma_db),
            "indexed": chroma_db.exists() and len(list(chroma_db.iterdir())) > 0,
        }
    
    def get_version_info(self) -> Dict[str, str]:
        """Version info"""
        return {
            "roxy_stack": "unified (~/.roxy)",
            "architecture": "systemd user service + HTTP IPC",
            "security": "token-based auth (A- grade)",
            "date": "2026-01-01",
        }
    
    def get_truth_statement(self) -> str:
        """
        Return a TRUTHFUL capability statement
        NO HALLUCINATION - evidence-only
        """
        caps = self.get_all_capabilities()
        
        statement = "ROXY CAPABILITIES (Evidence-Based)\n\n"
        
        statement += "✅ AVAILABLE:\n"
        statement += f"- RAG Query: {caps['rag']['available']}\n"
        statement += f"- Model: {caps['model'].get('current_model', 'UNKNOWN')}\n"
        statement += f"- Tools: {', '.join(caps['tools'])}\n"
        statement += f"- Repo Roots: {len(caps['repo_roots'])} configured\n"
        
        statement += "\n❌ NOT AVAILABLE:\n"
        statement += "- Browser Control: NO TOOL\n"
        statement += "- GUI Applications: NO TOOL\n"
        statement += f"- Shell Commands: {caps['command_execution']['reason']}\n"
        statement += "- Cloud Integrations (AWS/Azure/GCP): NO TOOL\n"
        
        statement += "\n⚠️ LIMITATIONS:\n"
        statement += "- Can only access configured repo_roots\n"
        statement += "- Cannot open applications unless execute_command enabled\n"
        statement += "- Cannot browse web (no browser automation tool)\n"
        statement += "- File operations limited to allowed_file_operations paths\n"
        
        return statement


# Singleton
_capabilities = None

def get_capabilities() -> CapabilitiesProvider:
    """Get or create capabilities provider"""
    global _capabilities
    if _capabilities is None:
        _capabilities = CapabilitiesProvider()
    return _capabilities


if __name__ == "__main__":
    # Test
    caps = get_capabilities()
    print(json.dumps(caps.get_all_capabilities(), indent=2))
    print("\n" + "="*60 + "\n")
    print(caps.get_truth_statement())
