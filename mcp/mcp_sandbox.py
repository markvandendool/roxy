#!/usr/bin/env python3
"""
MCP Sandbox Server - Secure Code Execution
===========================================
RU-003: Sandboxed Execution MCP Server

Uses bubblewrap (bwrap) for secure code execution with:
- No network access
- Memory limit (512MB)
- Time limit (60s)
- Filesystem isolation
- Read-only system mounts

Tools:
- sandbox_python: Execute Python code
- sandbox_bash: Execute bash commands
- sandbox_node: Execute Node.js code

SECURITY INVARIANTS:
1. No network access from sandbox
2. No access to home directory (except /tmp work dir)
3. Memory capped at 512MB
4. Runtime capped at 60s
5. All executions logged
"""

import os
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional
import signal
import resource

# Paths
ROXY_DIR = Path.home() / ".roxy"
SANDBOX_DIR = ROXY_DIR / "sandbox"
AUDIT_LOG = ROXY_DIR / "logs" / "sandbox_audit.log"

# Ensure directories exist
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
os.chmod(SANDBOX_DIR, 0o700)

# Limits
MEMORY_LIMIT_MB = 512
TIME_LIMIT_SECONDS = 60
OUTPUT_LIMIT_BYTES = 1024 * 1024  # 1MB max output


def _audit_log(operation: str, details: str = "", success: bool = True):
    """Write to audit log"""
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    log_entry = {
        "timestamp": timestamp,
        "operation": operation,
        "success": success,
        "details": details[:500]
    }
    
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def _create_work_dir() -> Path:
    """Create isolated work directory"""
    work_dir = Path(tempfile.mkdtemp(prefix="sandbox_", dir=SANDBOX_DIR))
    os.chmod(work_dir, 0o700)
    return work_dir


def _cleanup_work_dir(work_dir: Path):
    """Remove work directory"""
    try:
        shutil.rmtree(work_dir)
    except Exception:
        pass


def _build_bwrap_command(runtime: str, script_path: str, work_dir: Path) -> list:
    """
    Build bubblewrap command with security constraints
    
    Security measures:
    - --unshare-net: No network access
    - --unshare-pid: Isolated PID namespace
    - --unshare-ipc: Isolated IPC
    - --ro-bind: Read-only system mounts
    - --bind work_dir: Writable work directory only
    """
    
    # Runtime executable paths
    runtimes = {
        "python": "/usr/bin/python3",
        "bash": "/bin/bash",
        "node": "/usr/bin/node"
    }
    
    if runtime not in runtimes:
        raise ValueError(f"Unsupported runtime: {runtime}")
    
    runtime_path = runtimes[runtime]
    
    cmd = [
        "bwrap",
        # Namespace isolation
        "--unshare-net",           # No network
        "--unshare-pid",           # Isolated PIDs
        "--unshare-ipc",           # Isolated IPC
        "--unshare-uts",           # Isolated hostname
        
        # Read-only system mounts - bind actual directories
        "--ro-bind", "/usr", "/usr",
        "--ro-bind", "/lib", "/lib",
        "--ro-bind", "/bin", "/bin",
        "--ro-bind", "/etc", "/etc",
    ]
    
    # Add lib64 if it exists
    if os.path.exists("/lib64"):
        cmd.extend(["--ro-bind", "/lib64", "/lib64"])
    
    cmd.extend([
        # Proc/dev minimal
        "--proc", "/proc",
        "--dev", "/dev",
        
        # Writable work directory
        "--bind", str(work_dir), "/work",
        "--chdir", "/work",
        
        # Temp directory
        "--tmpfs", "/tmp",
        
        # Run as current user (unprivileged)
        "--die-with-parent",
        
        # The actual command
        runtime_path, script_path
    ])
    
    return cmd


def _run_sandboxed(runtime: str, code: str, files: Optional[dict] = None) -> dict:
    """
    Execute code in sandbox
    
    Args:
        runtime: python, bash, or node
        code: Code to execute
        files: Optional dict of filename -> content to create
    
    Returns:
        {"success": True, "stdout": str, "stderr": str, "exit_code": int, "runtime_ms": int}
    """
    work_dir = _create_work_dir()
    
    try:
        # Write additional files if provided
        if files:
            for filename, content in files.items():
                # Sanitize filename
                safe_name = Path(filename).name
                if safe_name and not safe_name.startswith('.'):
                    (work_dir / safe_name).write_text(content)
        
        # Write the script
        if runtime == "python":
            script_name = "script.py"
        elif runtime == "bash":
            script_name = "script.sh"
        elif runtime == "node":
            script_name = "script.js"
        else:
            return {"success": False, "error": f"Unknown runtime: {runtime}"}
        
        script_path = work_dir / script_name
        script_path.write_text(code)
        os.chmod(script_path, 0o755)
        
        # Build command
        cmd = _build_bwrap_command(runtime, f"/work/{script_name}", work_dir)
        
        # Execute with timeout
        start_time = datetime.now()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=TIME_LIMIT_SECONDS,
                # Memory limit via ulimit in the script itself
                preexec_fn=lambda: resource.setrlimit(
                    resource.RLIMIT_AS, 
                    (MEMORY_LIMIT_MB * 1024 * 1024, MEMORY_LIMIT_MB * 1024 * 1024)
                ) if hasattr(resource, 'RLIMIT_AS') else None
            )
            
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            stdout = result.stdout.decode('utf-8', errors='replace')[:OUTPUT_LIMIT_BYTES]
            stderr = result.stderr.decode('utf-8', errors='replace')[:OUTPUT_LIMIT_BYTES]
            
            _audit_log(f"sandbox_{runtime}", f"exit={result.returncode}, time={elapsed_ms}ms")
            
            return {
                "success": True,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": result.returncode,
                "runtime_ms": elapsed_ms
            }
            
        except subprocess.TimeoutExpired:
            _audit_log(f"sandbox_{runtime}", f"TIMEOUT after {TIME_LIMIT_SECONDS}s", False)
            return {
                "success": False,
                "error": f"Execution timed out after {TIME_LIMIT_SECONDS} seconds",
                "stdout": "",
                "stderr": "Process killed: timeout exceeded",
                "exit_code": -9,
                "runtime_ms": TIME_LIMIT_SECONDS * 1000
            }
            
    except Exception as e:
        _audit_log(f"sandbox_{runtime}", str(e), False)
        return {"success": False, "error": str(e)}
        
    finally:
        _cleanup_work_dir(work_dir)


def sandbox_python(code: str, files: Optional[dict] = None) -> dict:
    """
    Execute Python code in sandbox
    
    Args:
        code: Python code to execute
        files: Optional dict of filename -> content
    
    Returns:
        {"success": True, "stdout": str, "stderr": str, "exit_code": int}
    """
    return _run_sandboxed("python", code, files)


def sandbox_bash(code: str, files: Optional[dict] = None) -> dict:
    """
    Execute bash commands in sandbox
    
    Args:
        code: Bash script to execute
        files: Optional dict of filename -> content
    
    Returns:
        {"success": True, "stdout": str, "stderr": str, "exit_code": int}
    """
    return _run_sandboxed("bash", code, files)


def sandbox_node(code: str, files: Optional[dict] = None) -> dict:
    """
    Execute Node.js code in sandbox
    
    Args:
        code: JavaScript code to execute
        files: Optional dict of filename -> content
    
    Returns:
        {"success": True, "stdout": str, "stderr": str, "exit_code": int}
    """
    return _run_sandboxed("node", code, files)


def sandbox_status() -> dict:
    """
    Get sandbox status and capabilities
    
    Returns:
        {"bwrap_available": bool, "limits": {...}}
    """
    bwrap_path = shutil.which("bwrap")
    
    return {
        "success": True,
        "bwrap_available": bwrap_path is not None,
        "bwrap_path": bwrap_path,
        "limits": {
            "memory_mb": MEMORY_LIMIT_MB,
            "timeout_seconds": TIME_LIMIT_SECONDS,
            "output_bytes": OUTPUT_LIMIT_BYTES
        },
        "runtimes": ["python", "bash", "node"]
    }


# =============================================================================
# MCP Server Interface
# =============================================================================

TOOLS = {
    "python": {
        "description": "Execute Python code in isolated sandbox (no network, 512MB mem, 60s timeout)",
        "parameters": {
            "code": {"type": "string", "description": "Python code to execute"},
            "files": {"type": "object", "description": "Optional dict of filename -> content to create"}
        },
        "required": ["code"]
    },
    "bash": {
        "description": "Execute bash commands in isolated sandbox",
        "parameters": {
            "code": {"type": "string", "description": "Bash script to execute"},
            "files": {"type": "object", "description": "Optional files to create"}
        },
        "required": ["code"]
    },
    "node": {
        "description": "Execute Node.js code in isolated sandbox",
        "parameters": {
            "code": {"type": "string", "description": "JavaScript code to execute"},
            "files": {"type": "object", "description": "Optional files to create"}
        },
        "required": ["code"]
    },
    "status": {
        "description": "Get sandbox status and capabilities",
        "parameters": {},
        "required": []
    }
}


def handle_tool(name: str, params: dict) -> Any:
    """MCP tool handler"""
    handlers = {
        "python": lambda p: sandbox_python(p["code"], p.get("files")),
        "bash": lambda p: sandbox_bash(p["code"], p.get("files")),
        "node": lambda p: sandbox_node(p["code"], p.get("files")),
        "status": lambda p: sandbox_status()
    }
    
    if name not in handlers:
        return {"success": False, "error": f"Unknown tool: {name}"}
    
    return handlers[name](params)


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: mcp_sandbox.py <command> [code]")
        print("Commands: python <code>, bash <code>, node <code>, status")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "status":
        result = sandbox_status()
    elif cmd == "python" and len(sys.argv) >= 3:
        result = sandbox_python(sys.argv[2])
    elif cmd == "bash" and len(sys.argv) >= 3:
        result = sandbox_bash(sys.argv[2])
    elif cmd == "node" and len(sys.argv) >= 3:
        result = sandbox_node(sys.argv[2])
    else:
        print(f"Unknown command or missing args: {cmd}")
        sys.exit(1)
    
    print(json.dumps(result, indent=2))
