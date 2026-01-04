#!/usr/bin/env python3
"""
MCP Vault Server - Encrypted Secrets Management
================================================
RU-001: Encrypted Vault MCP Server

Uses age encryption for secure credential storage with:
- Zero plaintext exposure
- Audit logging for all operations
- Key rotation support
- Auto-discovery via mcp_*.py pattern

Tools:
- vault_set: Store an encrypted secret
- vault_get: Retrieve and decrypt a secret
- vault_list: List all secret keys (not values)
- vault_delete: Remove a secret
- vault_rotate: Rotate the encryption key

SECURITY INVARIANTS:
1. Secrets are NEVER logged in plaintext
2. Key file has 600 permissions
3. Vault directory has 700 permissions
4. All operations create audit trail
"""

import os
import subprocess
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

# Paths
ROXY_DIR = Path.home() / ".roxy"
VAULT_DIR = ROXY_DIR / "vault"
KEY_FILE = VAULT_DIR / ".age-key"
SECRETS_DIR = VAULT_DIR / "secrets"
AUDIT_LOG = ROXY_DIR / "logs" / "vault_audit.log"

# Ensure directories exist with secure permissions
VAULT_DIR.mkdir(parents=True, exist_ok=True)
SECRETS_DIR.mkdir(parents=True, exist_ok=True)
os.chmod(VAULT_DIR, 0o700)
os.chmod(SECRETS_DIR, 0o700)


def _audit_log(operation: str, key: str, success: bool, details: str = ""):
    """Write to audit log - NEVER include secret values"""
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    log_entry = {
        "timestamp": timestamp,
        "operation": operation,
        "key": key,
        "success": success,
        "details": details
    }
    
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def _get_or_create_key() -> str:
    """Get existing key or generate new one"""
    if KEY_FILE.exists():
        with open(KEY_FILE, "r") as f:
            return f.read().strip()
    
    # Generate new key
    result = subprocess.run(
        ["age-keygen"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to generate key: {result.stderr}")
    
    # Parse output - age-keygen outputs public key as comment, private key on next line
    lines = result.stdout.strip().split("\n")
    private_key = None
    public_key = None
    
    for line in lines:
        if line.startswith("# public key:"):
            public_key = line.split(": ")[1]
        elif line.startswith("AGE-SECRET-KEY-"):
            private_key = line
    
    if not private_key:
        raise RuntimeError("Failed to parse age key output")
    
    # Save private key securely
    with open(KEY_FILE, "w") as f:
        f.write(private_key + "\n")
    os.chmod(KEY_FILE, 0o600)
    
    # Save public key for reference
    pub_key_file = VAULT_DIR / ".age-key.pub"
    with open(pub_key_file, "w") as f:
        f.write(public_key + "\n")
    
    _audit_log("key_generated", "master", True, "New encryption key generated")
    
    return private_key


def _get_public_key() -> str:
    """Extract public key from private key"""
    private_key = _get_or_create_key()
    
    # Run age-keygen -y to get public key from private
    result = subprocess.run(
        ["age-keygen", "-y"],
        input=private_key,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to derive public key: {result.stderr}")
    
    return result.stdout.strip()


def _secret_path(key: str) -> Path:
    """Get path for a secret (hashed for privacy)"""
    # Use hash to avoid exposing key names in filesystem
    key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
    return SECRETS_DIR / f"{key_hash}.age"


def _key_index_path() -> Path:
    """Path to encrypted key index"""
    return SECRETS_DIR / ".index.age"


def _load_key_index() -> dict:
    """Load the key name -> hash mapping"""
    index_path = _key_index_path()
    if not index_path.exists():
        return {}
    
    # Decrypt index
    try:
        result = subprocess.run(
            ["age", "-d", "-i", str(KEY_FILE)],
            input=index_path.read_bytes(),
            capture_output=True
        )
        if result.returncode == 0:
            return json.loads(result.stdout.decode())
    except Exception:
        pass
    
    return {}


def _save_key_index(index: dict):
    """Save the key name -> hash mapping (encrypted)"""
    public_key = _get_public_key()
    index_json = json.dumps(index).encode()
    
    result = subprocess.run(
        ["age", "-r", public_key],
        input=index_json,
        capture_output=True
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to encrypt index: {result.stderr.decode()}")
    
    index_path = _key_index_path()
    index_path.write_bytes(result.stdout)


def vault_set(key: str, value: str) -> dict:
    """
    Store an encrypted secret
    
    Args:
        key: Secret identifier (e.g., "telegram_bot_token")
        value: Secret value to encrypt
    
    Returns:
        {"success": True, "key": key}
    """
    try:
        public_key = _get_public_key()
        
        # Encrypt the value
        result = subprocess.run(
            ["age", "-r", public_key],
            input=value.encode(),
            capture_output=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Encryption failed: {result.stderr.decode()}")
        
        # Save encrypted data
        secret_path = _secret_path(key)
        secret_path.write_bytes(result.stdout)
        os.chmod(secret_path, 0o600)
        
        # Update index
        index = _load_key_index()
        index[key] = hashlib.sha256(key.encode()).hexdigest()[:16]
        _save_key_index(index)
        
        _audit_log("set", key, True, f"Secret stored ({len(value)} bytes)")
        
        return {"success": True, "key": key}
        
    except Exception as e:
        _audit_log("set", key, False, str(e))
        return {"success": False, "error": str(e)}


def vault_get(key: str) -> dict:
    """
    Retrieve and decrypt a secret
    
    Args:
        key: Secret identifier
    
    Returns:
        {"success": True, "key": key, "value": decrypted_value}
    """
    try:
        secret_path = _secret_path(key)
        
        if not secret_path.exists():
            _audit_log("get", key, False, "Secret not found")
            return {"success": False, "error": f"Secret '{key}' not found"}
        
        # Decrypt
        result = subprocess.run(
            ["age", "-d", "-i", str(KEY_FILE)],
            input=secret_path.read_bytes(),
            capture_output=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Decryption failed: {result.stderr.decode()}")
        
        value = result.stdout.decode()
        
        _audit_log("get", key, True, "Secret retrieved")
        
        return {"success": True, "key": key, "value": value}
        
    except Exception as e:
        _audit_log("get", key, False, str(e))
        return {"success": False, "error": str(e)}


def vault_list() -> dict:
    """
    List all secret keys (not values)
    
    Returns:
        {"success": True, "keys": [list of key names]}
    """
    try:
        index = _load_key_index()
        keys = list(index.keys())
        
        _audit_log("list", "*", True, f"Listed {len(keys)} keys")
        
        return {"success": True, "keys": keys, "count": len(keys)}
        
    except Exception as e:
        _audit_log("list", "*", False, str(e))
        return {"success": False, "error": str(e)}


def vault_delete(key: str) -> dict:
    """
    Delete a secret
    
    Args:
        key: Secret identifier to delete
    
    Returns:
        {"success": True, "key": key}
    """
    try:
        secret_path = _secret_path(key)
        
        if not secret_path.exists():
            _audit_log("delete", key, False, "Secret not found")
            return {"success": False, "error": f"Secret '{key}' not found"}
        
        # Remove file
        secret_path.unlink()
        
        # Update index
        index = _load_key_index()
        if key in index:
            del index[key]
            _save_key_index(index)
        
        _audit_log("delete", key, True, "Secret deleted")
        
        return {"success": True, "key": key}
        
    except Exception as e:
        _audit_log("delete", key, False, str(e))
        return {"success": False, "error": str(e)}


def vault_rotate() -> dict:
    """
    Rotate the encryption key - re-encrypts all secrets with new key
    
    Returns:
        {"success": True, "rotated_count": int}
    """
    try:
        # Load all current secrets
        index = _load_key_index()
        secrets = {}
        
        for key in index.keys():
            result = vault_get(key)
            if result["success"]:
                secrets[key] = result["value"]
        
        # Backup old key
        old_key_backup = KEY_FILE.with_suffix(".old")
        if KEY_FILE.exists():
            KEY_FILE.rename(old_key_backup)
        
        # Generate new key (will create new key since file is gone)
        _get_or_create_key()
        
        # Re-encrypt all secrets
        rotated = 0
        for key, value in secrets.items():
            result = vault_set(key, value)
            if result["success"]:
                rotated += 1
        
        # Remove old key backup
        if old_key_backup.exists():
            old_key_backup.unlink()
        
        _audit_log("rotate", "*", True, f"Key rotated, {rotated} secrets re-encrypted")
        
        return {"success": True, "rotated_count": rotated}
        
    except Exception as e:
        _audit_log("rotate", "*", False, str(e))
        return {"success": False, "error": str(e)}


# =============================================================================
# MCP Server Interface (required for auto-discovery)
# =============================================================================

TOOLS = {
    "set": {
        "description": "Store an encrypted secret in the vault",
        "parameters": {
            "key": {"type": "string", "description": "Secret identifier (e.g., telegram_bot_token)"},
            "value": {"type": "string", "description": "Secret value to encrypt"}
        },
        "required": ["key", "value"]
    },
    "get": {
        "description": "Retrieve and decrypt a secret from the vault",
        "parameters": {
            "key": {"type": "string", "description": "Secret identifier to retrieve"}
        },
        "required": ["key"]
    },
    "list": {
        "description": "List all secret keys stored in the vault (values not exposed)",
        "parameters": {},
        "required": []
    },
    "delete": {
        "description": "Delete a secret from the vault",
        "parameters": {
            "key": {"type": "string", "description": "Secret identifier to delete"}
        },
        "required": ["key"]
    },
    "rotate": {
        "description": "Rotate the encryption key and re-encrypt all secrets",
        "parameters": {},
        "required": []
    }
}


def handle_tool(name: str, params: dict) -> Any:
    """
    MCP tool handler - synchronous interface
    
    Args:
        name: Tool name (set, get, list, delete, rotate)
        params: Tool parameters
    
    Returns:
        Tool result dictionary
    """
    handlers = {
        "set": lambda p: vault_set(p["key"], p["value"]),
        "get": lambda p: vault_get(p["key"]),
        "list": lambda p: vault_list(),
        "delete": lambda p: vault_delete(p["key"]),
        "rotate": lambda p: vault_rotate()
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
        print("Usage: mcp_vault.py <command> [args...]")
        print("Commands: set <key> <value>, get <key>, list, delete <key>, rotate")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "set" and len(sys.argv) >= 4:
        result = vault_set(sys.argv[2], sys.argv[3])
    elif cmd == "get" and len(sys.argv) >= 3:
        result = vault_get(sys.argv[2])
    elif cmd == "list":
        result = vault_list()
    elif cmd == "delete" and len(sys.argv) >= 3:
        result = vault_delete(sys.argv[2])
    elif cmd == "rotate":
        result = vault_rotate()
    else:
        print(f"Unknown command or missing args: {cmd}")
        sys.exit(1)
    
    print(json.dumps(result, indent=2))
