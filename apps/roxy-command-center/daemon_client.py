#!/usr/bin/env python3
"""
Async daemon client with timeout handling.
ROXY-CMD-STORY-001: Non-blocking HTTP fetches with GLib integration.
"""

import subprocess
import json
import os
import threading
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GLib

DAEMON_PATH = Path.home() / ".config/eww/roxy-panel/scripts/roxy-panel-daemon.py"
DEFAULT_TIMEOUT = 2.0  # 2 second timeout per ORACLE-04 mitigation
MAX_CACHE_AGE = 30.0   # Cache TTL in seconds

@dataclass
class DaemonResponse:
    """Container for daemon response with metadata."""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    source: str = "unknown"
    error: Optional[str] = None
    is_stale: bool = False

class DaemonClient:
    """
    Async daemon client with caching and GLib integration.
    
    Features:
    - Thread pool for non-blocking HTTP fetches
    - 2s timeout to prevent UI freeze (ORACLE-04)
    - Response caching with staleness indicator
    - GLib.idle_add for safe UI updates
    """
    
    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="daemon")
        self._cache: Optional[DaemonResponse] = None
        self._pending = False
        self._callbacks: list = []
        
        # Mode configuration
        self.mode = "auto"
        self.remote_host = "10.0.0.69"
        self.remote_port = 8766
    
    def configure(self, mode: str = "auto", remote_host: str = "10.0.0.69", remote_port: int = 8766):
        """Update daemon connection configuration."""
        self.mode = mode
        self.remote_host = remote_host
        self.remote_port = remote_port
    
    def get_cached(self) -> Optional[DaemonResponse]:
        """Get cached response if available and fresh."""
        if self._cache is None:
            return None
        
        age = time.time() - self._cache.timestamp
        if age > MAX_CACHE_AGE:
            self._cache.is_stale = True
        
        return self._cache
    
    def fetch_async(self, callback: Callable[[DaemonResponse], None]):
        """
        Fetch daemon status asynchronously.
        
        Callback will be invoked on main thread via GLib.idle_add.
        If a fetch is already pending, callback is queued.
        """
        self._callbacks.append(callback)
        
        if self._pending:
            return  # Already fetching, callback will be called when complete
        
        self._pending = True
        self.executor.submit(self._fetch_worker)
    
    def _fetch_worker(self):
        """Worker thread: fetch from daemon and schedule callback."""
        response = self._do_fetch()
        
        # Cache the response
        self._cache = response
        
        # Schedule UI update on main thread
        GLib.idle_add(self._deliver_callbacks, response)
    
    def _deliver_callbacks(self, response: DaemonResponse) -> bool:
        """Deliver response to all waiting callbacks (main thread)."""
        self._pending = False
        callbacks = self._callbacks[:]
        self._callbacks.clear()
        
        for cb in callbacks:
            try:
                cb(response)
            except Exception as e:
                print(f"[DaemonClient] Callback error: {e}")
        
        return False  # Don't repeat
    
    def _do_fetch(self) -> DaemonResponse:
        """Synchronous fetch (runs in worker thread)."""
        env = os.environ.copy()
        env.update({
            "ROXY_MODE": self.mode,
            "ROXY_REMOTE_HOST": self.remote_host,
            "ROXY_REMOTE_PORT": str(self.remote_port),
        })
        
        try:
            result = subprocess.run(
                ["python3", str(DAEMON_PATH), "--mode", "oneshot"],
                env=env,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode != 0:
                return DaemonResponse(
                    error=f"Daemon exit code {result.returncode}: {result.stderr}",
                    timestamp=time.time(),
                    source="error"
                )
            
            data = json.loads(result.stdout)
            return DaemonResponse(
                data=data,
                timestamp=time.time(),
                source=data.get("source", "unknown")
            )
        
        except subprocess.TimeoutExpired:
            return DaemonResponse(
                error=f"Daemon timeout ({self.timeout}s)",
                timestamp=time.time(),
                source="timeout"
            )
        except json.JSONDecodeError as e:
            return DaemonResponse(
                error=f"JSON parse error: {e}",
                timestamp=time.time(),
                source="parse_error"
            )
        except Exception as e:
            return DaemonResponse(
                error=f"Daemon call failed: {e}",
                timestamp=time.time(),
                source="error"
            )
    
    def fetch_sync(self) -> DaemonResponse:
        """
        Synchronous fetch (blocking).
        Use sparingly - prefer fetch_async for UI code.
        """
        return self._do_fetch()
    
    def shutdown(self):
        """Clean shutdown of thread pool."""
        self.executor.shutdown(wait=False)


# Global client instance
_client: Optional[DaemonClient] = None

def get_client() -> DaemonClient:
    """Get or create global daemon client."""
    global _client
    if _client is None:
        _client = DaemonClient()
    return _client

def get_status(mode="auto", remote_host="10.0.0.69", remote_port=8766) -> dict:
    """
    Legacy sync interface for backward compatibility.
    Returns dict with status data or error.
    """
    client = get_client()
    client.configure(mode, remote_host, remote_port)
    response = client.fetch_sync()
    
    if response.error:
        return {"error": response.error}
    return response.data

def fetch_status_async(callback: Callable[[DaemonResponse], None], 
                       mode="auto", remote_host="10.0.0.69", remote_port=8766):
    """
    Async fetch interface.
    Callback receives DaemonResponse on main thread.
    """
    client = get_client()
    client.configure(mode, remote_host, remote_port)
    client.fetch_async(callback)


def normalize_status(raw: dict) -> dict:
    """
    Normalize daemon payload to canonical schema.
    Handles all known variations: gpu/gpus, temp_c/temp, system/stats, etc.
    
    Returns dict with guaranteed keys:
    - mode: str
    - cpu: dict with cpu_pct, load_1m
    - memory: dict with mem_used_gb, mem_total_gb
    - gpus: list of normalized GPU dicts
    - services: dict
    - ollama: dict
    - disk: dict
    - alerts: list
    - _raw: original payload for debugging
    """
    # CPU/System
    sys_data = raw.get("system") or raw.get("stats") or {}
    cpu = {
        "cpu_pct": sys_data.get("cpu_pct") or raw.get("cpu", {}).get("percent") or 0,
        "load_1m": sys_data.get("load_1m") or 0,
    }
    
    # Memory
    memory = {
        "mem_used_gb": sys_data.get("mem_used_gb") or 0,
        "mem_total_gb": sys_data.get("mem_total_gb") or 0,
    }
    
    # Services
    services = raw.get("services") or {}
    
    # GPUs: accept 'gpu' (list) or 'gpus' (list) or dict
    g = raw.get("gpus") or raw.get("gpu")
    gpus = []
    if isinstance(g, list):
        gpus = g
    elif isinstance(g, dict):
        # Some daemons use {"0": {...}, "1": {...}}
        if all(str(k).isdigit() for k in g.keys()):
            for k in sorted(g.keys(), key=lambda x: int(x)):
                gpus.append(g[k])
        else:
            gpus = [g]
    
    # Normalize each GPU's keys
    norm_gpus = []
    for i, gpu in enumerate(gpus):
        if not isinstance(gpu, dict):
            continue
        
        # Handle vram in GB or bytes
        vram_used = gpu.get("vram_used_gb") or 0
        vram_total = gpu.get("vram_total_gb") or 16
        if vram_used == 0 and gpu.get("vram_used_bytes"):
            vram_used = gpu.get("vram_used_bytes") / (1024**3)
        if vram_total == 0 and gpu.get("vram_total_bytes"):
            vram_total = gpu.get("vram_total_bytes") / (1024**3)
        
        norm_gpus.append({
            "index": gpu.get("index", i),
            "name": gpu.get("name") or gpu.get("model") or f"GPU {i}",
            "temp_c": gpu.get("temp_c") or gpu.get("temp") or gpu.get("temperature_c") or 0,
            "utilization_pct": gpu.get("utilization_pct") or gpu.get("gpu_busy_percent") or gpu.get("util") or 0,
            "vram_used_gb": vram_used,
            "vram_total_gb": vram_total,
            "power_w": gpu.get("power_w") or 0,
        })
    
    return {
        "mode": raw.get("mode", "local"),
        "cpu": cpu,
        "memory": memory,
        "gpus": norm_gpus,
        "services": services,
        "ollama": raw.get("ollama") or {},
        "disk": raw.get("disk") or {},
        "alerts": raw.get("alerts") or [],
        "roxy": raw.get("roxy") or {},
        "_raw": raw,  # Keep original for debug
    }
