#!/usr/bin/env python3
"""
Pool Identity - Single Source of Truth for ROXY Pool Configuration

CHIEF DIRECTIVE: Pool names match hardware, not semantic roles.
This prevents "BIG means fast" confusion forever.

All pool-related mappings, aliases, and resolution logic lives here.
Both benchmark_service.py and roxy_core.py import from this module.
"""

import logging
import os
import re
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

# =============================================================================
# CANONICAL POOL DEFINITIONS (Single Source of Truth)
# =============================================================================

CANONICAL_POOLS = {
    "w5700x": {
        "port": 11434,
        "service": "ollama-w5700x.service",
        "gpu": "W5700X",
        "label": "W5700X",
        "env_vars": [
            "ROXY_OLLAMA_W5700X_URL",
            "OLLAMA_BIG_URL",
            "ROXY_OLLAMA_BIG_URL",
        ],
        "legacy_fallback_vars": ["OLLAMA_HOST", "OLLAMA_BASE_URL"],
    },
    "6900xt": {
        "port": 11435,
        "service": "ollama-6900xt.service",
        "gpu": "6900XT",
        "label": "6900XT",
        "env_vars": [
            "ROXY_OLLAMA_6900XT_URL",
            "OLLAMA_FAST_URL",
            "ROXY_OLLAMA_FAST_URL",
        ],
        "legacy_fallback_vars": [],  # No legacy fallback for 6900XT
    },
}

# Backwards compatibility aliases (deprecated, will warn)
POOL_ALIASES = {
    "big": "w5700x",    # Legacy: "big" was port 11434
    "fast": "6900xt",   # Legacy: "fast" was port 11435
    # Identity mappings (canonical names map to themselves)
    "w5700x": "w5700x",
    "6900xt": "6900xt",
    "auto": "auto",
}

# Deprecation warning tracking (log once per process per alias)
_deprecated_alias_warned: set[str] = set()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def normalize_pool_key(pool_requested: str) -> tuple[str, str]:
    """
    Normalize pool input to canonical form.

    Args:
        pool_requested: Raw pool input (e.g., "BIG", "fast", "W5700X")

    Returns:
        Tuple of (raw_input, canonical_key)
        - raw_input: Original input unchanged
        - canonical_key: Lowercase canonical name ("w5700x", "6900xt", "auto")
    """
    raw = pool_requested
    key = pool_requested.lower()

    # Check for legacy aliases (big, fast)
    if key in ("big", "fast"):
        canonical = POOL_ALIASES[key]
        # DEPRECATION WARNING: log once per process per alias
        if key not in _deprecated_alias_warned:
            _deprecated_alias_warned.add(key)
            logger.warning(
                f"Pool alias '{key.upper()}' is deprecated; "
                f"use '{canonical.upper()}' instead (still accepted)"
            )
        return (raw, canonical)

    # Direct canonical or auto
    if key in POOL_ALIASES:
        return (raw, POOL_ALIASES[key])

    # Unknown - return as-is for error handling downstream
    return (raw, key)


def get_pool_url(pool_key: str) -> tuple[str, bool]:
    """
    Get URL for a pool from environment variables.

    Args:
        pool_key: Canonical pool key ("w5700x" or "6900xt")

    Returns:
        Tuple of (url, configured)
        - url: The resolved URL (may be default if not configured)
        - configured: Whether the URL came from an env var
    """
    if pool_key not in CANONICAL_POOLS:
        return (f"http://127.0.0.1:{CANONICAL_POOLS.get('w5700x', {}).get('port', 11434)}", False)

    pool = CANONICAL_POOLS[pool_key]

    # Check pool-specific env vars first
    for var in pool["env_vars"]:
        url = os.getenv(var)
        if url:
            return (_normalize_url(url), True)

    # Check legacy fallback vars (only for w5700x)
    for var in pool.get("legacy_fallback_vars", []):
        url = os.getenv(var)
        if url:
            return (_normalize_url(url), True)

    # Default URL based on port
    return (f"http://127.0.0.1:{pool['port']}", False)


def _normalize_url(url: str) -> str:
    """Normalize localhost variants to 127.0.0.1"""
    return url.replace("localhost", "127.0.0.1").replace("[::1]", "127.0.0.1")


def check_reachable(url: str, timeout: float = 2.0) -> bool:
    """Check if an Ollama endpoint is reachable."""
    try:
        req = urllib.request.Request(f"{url}/api/version", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except:
        return False


def get_pool_identity(pool_key: str) -> dict:
    """Get identity info for a pool (service, gpu hints)."""
    if pool_key in CANONICAL_POOLS:
        pool = CANONICAL_POOLS[pool_key]
        return {
            "port": pool["port"],
            "service": pool["service"],
            "gpu": pool["gpu"],
            "label": pool["label"],
        }
    return {
        "port": None,
        "service": None,
        "gpu": None,
        "label": None,
    }


def resolve_pool(pool_requested: str) -> dict:
    """
    Resolve a pool request to full connection details.

    This is the main entry point for pool resolution.

    Args:
        pool_requested: Raw pool input (e.g., "BIG", "W5700X", "AUTO")

    Returns:
        dict with keys:
        - pool_requested_raw: Original input
        - pool_requested_canonical: Canonical form ("w5700x", "6900xt", "auto")
        - pool_used: Actual pool used (may differ for AUTO)
        - base_url: Ollama base URL
        - base_url_chat: Chat completions endpoint
        - reachable: bool
        - error: str or None
        - port: int
        - service: str (systemd service name)
        - gpu_hint: str (GPU identifier)
    """
    # Normalize input
    raw, canonical = normalize_pool_key(pool_requested)

    # Handle AUTO mode
    if canonical == "auto":
        return _resolve_auto(raw, canonical)

    # Handle specific pool
    if canonical not in CANONICAL_POOLS:
        return {
            "pool_requested_raw": raw,
            "pool_requested_canonical": canonical,
            "pool_used": None,
            "base_url": None,
            "base_url_chat": None,
            "reachable": False,
            "error": f"Unknown pool: {pool_requested}. Valid pools: w5700x, 6900xt, auto",
            "port": None,
            "service": None,
            "gpu_hint": None,
        }

    url, configured = get_pool_url(canonical)
    identity = get_pool_identity(canonical)

    # Check configuration
    if not configured:
        env_hint = CANONICAL_POOLS[canonical]["env_vars"][0]
        return {
            "pool_requested_raw": raw,
            "pool_requested_canonical": canonical,
            "pool_used": None,
            "base_url": url,
            "base_url_chat": f"{url}/v1/chat/completions",
            "reachable": False,
            "error": f"{identity['label']} pool not configured. Set {env_hint} environment variable.",
            "port": identity["port"],
            "service": identity["service"],
            "gpu_hint": identity["gpu"],
        }

    # Check reachability
    reachable = check_reachable(url)
    if not reachable:
        return {
            "pool_requested_raw": raw,
            "pool_requested_canonical": canonical,
            "pool_used": None,
            "base_url": url,
            "base_url_chat": f"{url}/v1/chat/completions",
            "reachable": False,
            "error": f"{identity['label']} pool unreachable at {url}. Start {identity['service']}",
            "port": identity["port"],
            "service": identity["service"],
            "gpu_hint": identity["gpu"],
        }

    # Success
    return {
        "pool_requested_raw": raw,
        "pool_requested_canonical": canonical,
        "pool_used": canonical,
        "base_url": url,
        "base_url_chat": f"{url}/v1/chat/completions",
        "reachable": True,
        "error": None,
        "port": identity["port"],
        "service": identity["service"],
        "gpu_hint": identity["gpu"],
    }


def _resolve_auto(raw: str, canonical: str) -> dict:
    """Handle AUTO pool resolution - try w5700x first, then 6900xt."""
    # Try W5700X first
    w5700x_url, w5700x_configured = get_pool_url("w5700x")
    w5700x_identity = get_pool_identity("w5700x")

    if w5700x_configured and check_reachable(w5700x_url):
        return {
            "pool_requested_raw": raw,
            "pool_requested_canonical": canonical,
            "pool_used": "w5700x",
            "base_url": w5700x_url,
            "base_url_chat": f"{w5700x_url}/v1/chat/completions",
            "reachable": True,
            "error": None,
            "port": w5700x_identity["port"],
            "service": w5700x_identity["service"],
            "gpu_hint": w5700x_identity["gpu"],
        }

    # Try 6900XT as fallback
    xt6900_url, xt6900_configured = get_pool_url("6900xt")
    xt6900_identity = get_pool_identity("6900xt")

    if xt6900_configured and check_reachable(xt6900_url):
        return {
            "pool_requested_raw": raw,
            "pool_requested_canonical": canonical,
            "pool_used": "6900xt",
            "base_url": xt6900_url,
            "base_url_chat": f"{xt6900_url}/v1/chat/completions",
            "reachable": True,
            "error": None,
            "port": xt6900_identity["port"],
            "service": xt6900_identity["service"],
            "gpu_hint": xt6900_identity["gpu"],
        }

    # Both unreachable - try unconfigured defaults
    if check_reachable(w5700x_url):
        return {
            "pool_requested_raw": raw,
            "pool_requested_canonical": canonical,
            "pool_used": "w5700x",
            "base_url": w5700x_url,
            "base_url_chat": f"{w5700x_url}/v1/chat/completions",
            "reachable": True,
            "error": None,
            "port": w5700x_identity["port"],
            "service": w5700x_identity["service"],
            "gpu_hint": w5700x_identity["gpu"],
        }

    if check_reachable(xt6900_url):
        return {
            "pool_requested_raw": raw,
            "pool_requested_canonical": canonical,
            "pool_used": "6900xt",
            "base_url": xt6900_url,
            "base_url_chat": f"{xt6900_url}/v1/chat/completions",
            "reachable": True,
            "error": None,
            "port": xt6900_identity["port"],
            "service": xt6900_identity["service"],
            "gpu_hint": xt6900_identity["gpu"],
        }

    # Total failure
    return {
        "pool_requested_raw": raw,
        "pool_requested_canonical": canonical,
        "pool_used": None,
        "base_url": None,
        "base_url_chat": None,
        "reachable": False,
        "error": f"No Ollama pools reachable. Tried: {w5700x_url}, {xt6900_url}",
        "port": None,
        "service": None,
        "gpu_hint": None,
    }


def get_all_pools_status() -> dict:
    """
    Get status of all canonical pools.
    Used by /info endpoint for pool invariants.

    Returns:
        dict with pool_key -> status dict
    """
    result = {}
    for pool_key, pool_info in CANONICAL_POOLS.items():
        url, configured = get_pool_url(pool_key)

        # Quick latency check
        latency_ms = None
        reachable = False
        error = None

        if configured or True:  # Always check, even unconfigured defaults
            import time
            try:
                start = time.time()
                req = urllib.request.Request(f"{url}/api/version", method="GET")
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    if resp.status == 200:
                        reachable = True
                        latency_ms = round((time.time() - start) * 1000, 2)
            except Exception as e:
                error = str(e)

        result[pool_key] = {
            "url": url,
            "configured": configured,
            "reachable": reachable,
            "latency_ms": latency_ms,
            "error": error,
            "port": pool_info["port"],
            "service": pool_info["service"],
            "gpu": pool_info["gpu"],
        }

    return result
