#!/usr/bin/env python3
"""
ROXY Core - Always-On Background Service
Runs as systemd user service, no UI, exposes HTTP IPC

Part of LUNA-000 CITADEL - Wayland-correct architecture
"""

import os
import sys
import logging
import signal
import time
import subprocess
import atexit
import uuid
import hashlib
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
from threading import Thread
from typing import Optional, Tuple
from collections import defaultdict, deque

# Logging setup
LOG_DIR = Path.home() / ".roxy" / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "roxy-core.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("roxy-core")

# Configuration - single source of truth
ROXY_DIR = Path.home() / ".roxy"
CONFIG_FILE = ROXY_DIR / "config.json"
TOKEN_FILE = ROXY_DIR / "secret.token"

# Service bridge for advanced services (optional)
try:
    sys.path.insert(0, str(ROXY_DIR))
    from adapters.service_bridge import (
        check_services_availability,
        is_advanced_mode,
        get_availability_report
    )
    SERVICE_BRIDGE_AVAILABLE = True
except ImportError:
    SERVICE_BRIDGE_AVAILABLE = False
    logger.debug("Service bridge not available, using basic mode")
# Import Prometheus metrics (graceful fallback)
try:
    from prometheus_metrics import (
        init_prometheus, MetricsMiddleware,
        record_rag_query, record_cache_hit, record_cache_miss,
        record_ollama_call, record_blocked_command, record_rate_limit,
        is_available as prometheus_available,
        export_metrics,
    )
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.debug("Prometheus metrics not available")
METRICS_BOOT_WARNING_EMITTED = False
# Truth Gate for response validation (prevent hallucinations)
try:
    sys.path.insert(0, str(ROXY_DIR))
    from truth_gate import get_truth_gate
    TRUTH_GATE_AVAILABLE = True
    logger.info("✅ Truth Gate initialized (hallucination prevention)")
except ImportError:
    TRUTH_GATE_AVAILABLE = False
    logger.debug("Truth Gate not available, responses unvalidated")

# Infrastructure Integration (Redis, PostgreSQL, NATS, Expert Router)
try:
    sys.path.insert(0, str(ROXY_DIR))
    from infrastructure import (
        initialize_infrastructure,
        get_infrastructure_status,
        get_cache, get_memory, get_router, get_event_stream, get_feedback,
        cache_query, get_cached_response,
        remember_conversation, recall_conversations,
        route_query, classify_query,
        publish_event, publish_query_event, publish_response_event,
        record_feedback, get_feedback_stats, get_all_stats
    )
    INFRASTRUCTURE_AVAILABLE = True
    # Initialize all infrastructure on import
    _infra_status = initialize_infrastructure()
    logger.info(f"✅ Infrastructure initialized: {sum(_infra_status.values())}/{len(_infra_status)} components")
except ImportError as e:
    INFRASTRUCTURE_AVAILABLE = False
    logger.warning(f"⚠️ Infrastructure not available: {e}")
    # Provide fallback stubs
    def initialize_infrastructure(): return {}
    def get_infrastructure_status(): return {'initialized': False}
    def get_cache(): return None
    def get_memory(): return None
    def get_router(): return None
    def get_event_stream(): return None
    def get_feedback(): return None
    def cache_query(*args, **kwargs): pass
    def get_cached_response(*args, **kwargs): return None
    def remember_conversation(*args, **kwargs): pass
    def recall_conversations(*args, **kwargs): return []
    def route_query(*args, **kwargs): return ""
    def classify_query(*args, **kwargs): return ('general', 0.5)
    def publish_event(*args, **kwargs): pass
    def publish_query_event(*args, **kwargs): pass
    def publish_response_event(*args, **kwargs): pass
    def record_feedback(*args, **kwargs): pass
    def get_feedback_stats(): return {}
    def get_all_stats(): return {}

# Load config
if CONFIG_FILE.exists():
    with open(CONFIG_FILE) as f:
        config = json.load(f)
        IPC_HOST = config.get("host", "127.0.0.1")
        IPC_PORT = int(os.getenv("ROXY_PORT", config.get("port", 8766)))
else:
    IPC_HOST = "127.0.0.1"
    IPC_PORT = int(os.getenv("ROXY_PORT", 8766))
    logger.warning(f"Config file not found at {CONFIG_FILE}, using defaults")

# Load auth token - MANDATORY FOR SECURITY
if TOKEN_FILE.exists():
    AUTH_TOKEN = TOKEN_FILE.read_text().strip()
    if not AUTH_TOKEN:
        logger.error("FATAL: Auth token file exists but is empty")
        logger.error("Set token in ~/.roxy/secret.token or AUTH_TOKEN environment variable")
        logger.error("Generate token: python3 -c 'import secrets; print(secrets.token_urlsafe(32))'")
        sys.exit(1)
    logger.info("✓ Auth token loaded")
elif os.getenv("AUTH_TOKEN"):
    AUTH_TOKEN = os.getenv("AUTH_TOKEN").strip()
    if not AUTH_TOKEN:
        logger.error("FATAL: AUTH_TOKEN environment variable is empty")
        sys.exit(1)
    logger.info("✓ Auth token loaded from environment")
else:
    logger.error("FATAL: AUTH_TOKEN not configured - authentication is MANDATORY")
    logger.error("Set token in ~/.roxy/secret.token or AUTH_TOKEN environment variable")
    logger.error("Generate token: python3 -c 'import secrets; print(secrets.token_urlsafe(32))'")
    logger.error("Security policy: System will not start without authentication")
    sys.exit(1)  # FAIL FAST - DO NOT START WITHOUT AUTH

# Global semaphore to limit concurrent subprocess executions (prevent system overload)
import threading
import urllib.request
import urllib.error

MAX_CONCURRENT_SUBPROCESSES = 3  # Allow max 3 simultaneous roxy_commands.py processes
subprocess_semaphore = threading.Semaphore(MAX_CONCURRENT_SUBPROCESSES)

# ========== MULTI-MODE SYSTEM ==========
# ROXY can operate in multiple modes:
#   - broadcast: Full personality, conversational (default)
#   - technical: Minimal wrapper, precise responses  
#   - benchmark: Raw model access, no personality (for testing)
#   - creative: Higher temperature, more creative

ROXY_MODES = {
    'broadcast': {
        'description': 'Full personality, conversational',
        'system_prompt': True,
        'temperature': 0.7,
    },
    'technical': {
        'description': 'Minimal wrapper, precise responses',
        'system_prompt': False,
        'temperature': 0.1,
    },
    'benchmark': {
        'description': 'Raw model, no personality (for testing)',
        'system_prompt': False,
        'temperature': 0.0,
    },
    'creative': {
        'description': 'Higher temperature, more creative',
        'system_prompt': True,
        'temperature': 0.9,
    },
}

def _resolve_ollama_pools() -> dict:
    """
    Resolve BIG and FAST pools authoritatively from config/env.
    
    Returns:
        {
            "big": {"url": str|None, "configured": bool},
            "fast": {"url": str|None, "configured": bool},
            "default": str (primary URL)
        }
    
    Policy:
    - Normalizes localhost -> 127.0.0.1
    - BIG comes from OLLAMA_BIG_URL (or ROXY_OLLAMA_BIG_URL)
    - FAST comes from OLLAMA_FAST_URL (or ROXY_OLLAMA_FAST_URL)
    - OLLAMA_HOST/OLLAMA_BASE_URL maps to BIG if BIG is unset.
    - NO PORT GUESSING.
    """
    def _norm(url):
        if not url: return None
        url = url.strip().rstrip("/")
        return url.replace("localhost", "127.0.0.1")

    # 1. Read explicit pools first
    big_in = os.getenv("ROXY_OLLAMA_BIG_URL") or os.getenv("OLLAMA_BIG_URL")
    fast_in = os.getenv("ROXY_OLLAMA_FAST_URL") or os.getenv("OLLAMA_FAST_URL")
    
    # OLLAMA_HOST is just the default/fallback if no specific pool is chosen
    default_in = os.getenv("OLLAMA_HOST") or os.getenv("OLLAMA_BASE_URL")

    big_url = _norm(big_in)
    fast_url = _norm(fast_in)
    
    # default fallback if nothing set
    default_url = _norm(default_in) or big_url or fast_url or "http://127.0.0.1:11434"

    return {
        "big": {"url": big_url, "configured": bool(big_url)},
        "fast": {"url": fast_url, "configured": bool(fast_url)},
        "default": default_url
    }

def _get_ollama_base_url() -> str:
    """Resolve Ollama base URL via authentic pool resolution."""
    return _resolve_ollama_pools()["default"]


OLLAMA_HEALTH_LOCK = threading.Lock()
_ollama_health_state = {
    "last_ok_ts": None,
    "last_error": None,
    "last_latency_ms": None,
}


def _record_ollama_success(latency_ms: float) -> None:
    with OLLAMA_HEALTH_LOCK:
        _ollama_health_state["last_ok_ts"] = int(time.time())
        _ollama_health_state["last_latency_ms"] = round(latency_ms, 2)
        _ollama_health_state["last_error"] = None


def _record_ollama_error(message: str) -> None:
    with OLLAMA_HEALTH_LOCK:
        _ollama_health_state["last_error"] = message.strip()[:300] if message else ""
        _ollama_health_state["last_latency_ms"] = None


def _snapshot_ollama_health() -> dict:
    with OLLAMA_HEALTH_LOCK:
        return dict(_ollama_health_state)


def query_ollama_direct(prompt: str, model: str = "qwen2.5-coder:14b", 
                        temperature: float = 0.0, max_tokens: int = 512,
                        timeout: int = 60) -> str:
    """Query Ollama directly, bypassing all ROXY layers.
    
    Used for benchmarks and technical mode where raw model output is needed.
    """
    try:
        data = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }).encode()
        
        req = urllib.request.Request(
            f"{_get_ollama_base_url().rstrip('/')}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            return result.get('response', '')
            
    except urllib.error.URLError as e:
        logger.error(f"Ollama connection failed: {e}")
        return f"ERROR: Ollama unavailable - {e}"
    except Exception as e:
        logger.error(f"Direct Ollama query failed: {e}")
        return f"ERROR: {e}"

UNAUTHORIZED_LOG_WINDOW = 60  # seconds
UNAUTHORIZED_LOG_LIMIT = 1
UNAUTHORIZED_RATE_WINDOW = 120  # seconds
UNAUTHORIZED_RATE_LIMIT = 5
_unauthorized_log_tracker = defaultdict(deque)
_unauthorized_rate_tracker = defaultdict(deque)


def _register_unauthorized_attempt(address: str, user_agent: str) -> Tuple[bool, bool]:
    """Track unauthorized attempts and determine logging/rate limits."""
    key = (address, user_agent or "unknown")
    now = time.time()

    log_queue = _unauthorized_log_tracker[key]
    while log_queue and now - log_queue[0] > UNAUTHORIZED_LOG_WINDOW:
        log_queue.popleft()
    should_log = len(log_queue) < UNAUTHORIZED_LOG_LIMIT
    log_queue.append(now)

    rate_queue = _unauthorized_rate_tracker[key]
    while rate_queue and now - rate_queue[0] > UNAUTHORIZED_RATE_WINDOW:
        rate_queue.popleft()
    rate_queue.append(now)
    rate_limited = len(rate_queue) > UNAUTHORIZED_RATE_LIMIT

    return should_log, rate_limited


class RoxyCoreHandler(BaseHTTPRequestHandler):
    """HTTP handler for ROXY core IPC"""
    
    def _safe_write(self, payload: str, request_id: Optional[str] = None) -> bool:
        """Write to client safely, handling disconnects without noise."""
        try:
            self.wfile.write(payload.encode())
            self.wfile.flush()
            return True
        except (BrokenPipeError, ConnectionResetError):
            rid = request_id or "unknown"
            logger.info(f"[STREAM] client disconnected requestId={rid}")
            return False

    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info("%s - %s" % (self.address_string(), format % args))
    
    def do_GET(self):
        """Health check and streaming endpoints"""
        # Support both versioned and unversioned paths
        path = self.path.split('?')[0]  # Remove query string
        
        if path == "/health" or path == "/v1/health":
            self._handle_health_check()
        elif path == "/metrics" or path == "/v1/metrics":
            self._handle_metrics()
        elif path == "/modes" or path == "/v1/modes":
            self._handle_list_modes()
        elif path == "/infrastructure" or path == "/v1/infrastructure":
            self._handle_infrastructure_status()
        elif path == "/infrastructure/stats" or path == "/v1/infrastructure/stats":
            self._handle_infrastructure_stats()
        elif path == "/feedback/stats" or path == "/v1/feedback/stats":
            self._handle_feedback_stats()
        elif path == "/info" or path == "/v1/info":
            self._handle_info()
        elif path.startswith("/stream") or path.startswith("/v1/stream"):
            # Streaming endpoint (SSE)
            self._handle_streaming()
        else:
            self.send_response(404)
            self.end_headers()
    
    def _handle_health_check(self):
        """Health check with dependency verification"""
        health_status = {
            "status": "ok",
            "service": "roxy-core",
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        all_healthy = True
        
        # Check auth token
        if AUTH_TOKEN:
            health_status["checks"]["auth_token"] = "ok"
        else:
            health_status["checks"]["auth_token"] = "missing"
            all_healthy = False
        
        # Check rate limiter
        try:
            sys.path.insert(0, str(ROXY_DIR))
            from rate_limiting import get_rate_limiter
            get_rate_limiter()
            health_status["checks"]["rate_limiter"] = "ok"
        except Exception as e:
            health_status["checks"]["rate_limiter"] = f"error: {str(e)[:50]}"
            all_healthy = False
        
        # Check ChromaDB
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(ROXY_DIR / "chroma_db"))
            # Try to get a collection (doesn't matter if it exists)
            client.list_collections()
            health_status["checks"]["chromadb"] = "ok"
        except Exception as e:
            health_status["checks"]["chromadb"] = f"error: {str(e)[:50]}"
            all_healthy = False
        
        # Check Ollama
        base_url = _get_ollama_base_url()
        snapshot = _snapshot_ollama_health()
        ollama_check = {
            "ok": False,
            "base_url": base_url,
            "latency_ms": snapshot.get("last_latency_ms"),
            "last_ok_ts": snapshot.get("last_ok_ts"),
            "last_error": snapshot.get("last_error"),
        }

        try:
            import requests

            start_time = time.perf_counter()
            response = requests.get(f"{base_url}/api/tags", timeout=3)
            response.raise_for_status()
            latency_ms = (time.perf_counter() - start_time) * 1000
            _record_ollama_success(latency_ms)

            snapshot = _snapshot_ollama_health()
            ollama_check.update({
                "ok": True,
                "latency_ms": snapshot.get("last_latency_ms"),
                "last_ok_ts": snapshot.get("last_ok_ts"),
                "last_error": snapshot.get("last_error"),
            })
        except Exception as e:
            logger.debug(f"Ollama health check failed: {e}")
            _record_ollama_error(str(e))
            snapshot = _snapshot_ollama_health()
            ollama_check.update({
                "ok": False,
                "latency_ms": snapshot.get("last_latency_ms"),
                "last_ok_ts": snapshot.get("last_ok_ts"),
                "last_error": snapshot.get("last_error"),
            })
            all_healthy = False

        health_status["checks"]["ollama"] = ollama_check
        
        # Check Infrastructure (Redis, PostgreSQL, NATS)
        if INFRASTRUCTURE_AVAILABLE:
            infra_status = get_infrastructure_status()
            health_status["checks"]["infrastructure"] = {
                "initialized": infra_status.get('initialized', False)
            }
            for name, component in infra_status.get('components', {}).items():
                if isinstance(component, dict):
                    is_healthy = component.get('healthy', False)
                    health_status["checks"][f"infra_{name}"] = "ok" if is_healthy else "degraded"
                else:
                    health_status["checks"][f"infra_{name}"] = "unknown"
        else:
            health_status["checks"]["infrastructure"] = "not_available"
        
        # Return appropriate status code
        if all_healthy:
            self.send_response(200)
        else:
            self.send_response(503)  # Service Unavailable
        
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(health_status).encode())

    def _handle_info(self):
        """Return server info: time, hostname, git state, ollama status, routing policy.
        
        Chief's Truth Panel - authoritative data for Command Center.
        """
        import socket
        
        info = {
            "server_time_iso": datetime.now().isoformat(),
            "hostname": socket.gethostname(),
            "roxy_core_pid": os.getpid(),
            "git": {},
            "ollama": {},
            "routing_policy": config.get("routing_policy", "auto")
        }
        
        # Git state
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=2, cwd=ROXY_DIR
            )
            info["git"]["branch"] = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=2, cwd=ROXY_DIR
            )
            info["git"]["head_sha"] = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=2, cwd=ROXY_DIR
            )
            info["git"]["dirty"] = bool(result.stdout.strip()) if result.returncode == 0 else None
            
            result = subprocess.run(
                ["git", "log", "-1", "--format=%s"],
                capture_output=True, text=True, timeout=2, cwd=ROXY_DIR
            )
            info["git"]["last_commit_subject"] = result.stdout.strip()[:80] if result.returncode == 0 else ""
        except Exception as e:
            info["git"]["error"] = str(e)
        
        # Ollama state
        pools = _resolve_ollama_pools()
        ollama_base = pools["default"]
        
        # CHIEF'S TRUTH CONTRACT: Expose pool configuration derived from env
        # This allows UI to map URLs to "BIG" or "FAST" labels authoritatively
        info["ollama"]["pools"] = {
            "big": pools["big"]["url"],
            "fast": pools["fast"]["url"]
        }
        info["ollama"]["base_url"] = ollama_base
        # Legacy field for compatibility, but populated correctly now
        info["ollama"]["fast_url"] = pools["fast"]["url"]
        
        try:
            import urllib.request
            start = time.time()
            req = urllib.request.Request(f"{ollama_base}/api/tags", method="GET")
            req.add_header("User-Agent", "roxy-core/info-check")
            with urllib.request.urlopen(req, timeout=2) as resp:
                info["ollama"]["latency_ms"] = round((time.time() - start) * 1000, 2)
                info["ollama"]["ok"] = resp.status == 200
                info["ollama"]["error"] = None
        except Exception as e:
            info["ollama"]["ok"] = False
            info["ollama"]["error"] = str(e)
            info["ollama"]["latency_ms"] = None
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(info, indent=2).encode())

    def _handle_metrics(self):
        """Expose Prometheus metrics with graceful degradation."""
        request_id = str(uuid.uuid4())[:8]

        if not METRICS_AVAILABLE or not prometheus_available():
            global METRICS_BOOT_WARNING_EMITTED
            if not METRICS_BOOT_WARNING_EMITTED:
                logger.warning("[METRICS] Prometheus disabled reason=prometheus_client missing")
                METRICS_BOOT_WARNING_EMITTED = True
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {
                "disabled": True,
                "reason": "prometheus_client missing",
                "request_id": request_id,
            }
            self._safe_write(json.dumps(payload), request_id)
            return

        try:
            metrics_body, content_type = export_metrics()
        except RuntimeError as exc:
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {
                "disabled": True,
                "reason": str(exc),
                "request_id": request_id,
            }
            self._safe_write(json.dumps(payload), request_id)
            return
        except Exception as exc:  # pragma: no cover - unexpected failure
            logger.error(f"Metrics export failed: {exc}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {
                "status": "error",
                "reason": "metrics export failure",
                "request_id": request_id,
            }
            self._safe_write(json.dumps(payload), request_id)
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(metrics_body)
        except (BrokenPipeError, ConnectionResetError):
            logger.info(f"[METRICS] client disconnected requestId={request_id}")
    
    def _handle_streaming(self):
        """Handle Server-Sent Events streaming"""
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        # Track metrics
        if METRICS_AVAILABLE:
            metrics_ctx = MetricsMiddleware(endpoint="/stream")
            metrics_ctx.__enter__()
        else:
            metrics_ctx = None
        metrics_closed = False
        
        try:
            # Rate limiting for streaming endpoint
            rate_limiting_enabled = config.get("rate_limiting_enabled", False)
            if rate_limiting_enabled:
                try:
                    sys.path.insert(0, str(ROXY_DIR))
                    from rate_limiting import get_rate_limiter
                    rate_limiter = get_rate_limiter()
                    client_ip = self.client_address[0]
                    if not rate_limiter.check_rate_limit(client_ip, "/stream"):
                        if METRICS_AVAILABLE:
                            record_rate_limit("/stream")
                        self.send_response(429)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        response = {"status": "error", "message": "Rate limit exceeded"}
                        self._safe_write(json.dumps(response), request_id)
                        if metrics_ctx and not metrics_closed:
                            metrics_ctx.set_status("rate_limited")
                            metrics_ctx.__exit__(None, None, None)
                            metrics_closed = True
                        return
                except Exception as e:
                    logger.warning(f"Rate limiting check failed for streaming: {e}")
            
            # Parse query parameters - accept both 'q' and 'command'
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            command = params.get('q', params.get('command', [''])[0])[0] if params.get('q') else params.get('command', [''])[0]
            
            if not command:
                self.send_error(400, "No command provided (use 'q' or 'command' query parameter)")
                if metrics_ctx:
                    metrics_ctx.set_status("error")
                    metrics_ctx.__exit__(None, None, None)
                    metrics_closed = True
                return
            
            # Validate auth token if configured
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    self.send_error(403, "Forbidden: Invalid or missing token")
                    return
            
            # Set SSE headers
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("X-Accel-Buffering", "no")  # Nginx compatibility
            self.end_headers()
            
            # Stream response
            self._stream_command_response(command, request_id)
            if metrics_ctx and not metrics_closed:
                metrics_ctx.set_status("success")
                metrics_ctx.__exit__(None, None, None)
                metrics_closed = True
            
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            # Close metrics context on error
            if METRICS_AVAILABLE and metrics_ctx:
                metrics_ctx.set_status("error")
                metrics_ctx.__exit__(type(e), e, None)
                metrics_closed = True
            self.send_error(500, str(e))
        finally:
            if metrics_ctx and not metrics_closed:
                metrics_ctx.__exit__(None, None, None)
    
    def _stream_command_response(self, command: str, request_id: str):
        """Stream command response as SSE events with real Ollama streaming"""
        try:
            # Import streaming module
            sys.path.insert(0, str(ROXY_DIR))
            from streaming import get_streamer
            streamer = get_streamer()
            
            # Quick check: if it's a greeting, return fast
            import re
            greeting_patterns = [
                r"^hi\s+roxy", r"^hello\s*$", r"^hey\s+roxy",
                r"^yo\s+roxy", r"^sup\s+roxy"
            ]
            if any(re.match(p, command, re.IGNORECASE) for p in greeting_patterns):
                response = "Hi! I'm ROXY, your resident AI assistant. How can I help you?"
                for char in response:
                    event_data = json.dumps({"token": char, "done": False})
                    if not self._safe_write(f"data: {event_data}\n\n", request_id):
                        return
                    time.sleep(0.01)
                self._safe_write(f"event: complete\ndata: {json.dumps({'done': True})}\n\n", request_id)
                return
            
            # Check if it's a RAG query (not a command)
            is_command = any(cmd in command.lower() for cmd in [
                "git", "obs", "health", "open", "launch", "start", "stop"
            ])
            
            if not is_command:
                # Likely RAG query - get context and stream
                try:
                    # Get RAG context with retry and circuit breaker
                    import chromadb
                    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
                    from roxy_commands import _expand_query
                    
                    # Import resilience utilities
                    try:
                        from retry_utils import retry
                        from circuit_breaker import get_circuit_breaker, CircuitBreakerError
                        RESILIENCE_AVAILABLE = True
                    except ImportError:
                        RESILIENCE_AVAILABLE = False
                    
                    expanded_query = _expand_query(command)
                    ef = DefaultEmbeddingFunction()
                    
                    @retry(max_attempts=3, delay=1.0, backoff=2.0) if RESILIENCE_AVAILABLE else lambda f: f
                    def _get_embedding():
                        return ef([expanded_query])[0]
                    
                    embedding = _get_embedding()
                    
                    @retry(max_attempts=3, delay=1.0, backoff=2.0) if RESILIENCE_AVAILABLE else lambda f: f
                    def _query_chromadb():
                        client = chromadb.PersistentClient(path=str(ROXY_DIR / "chroma_db"))
                        collection = client.get_collection("mindsong_docs", embedding_function=ef)
                        return collection.query(
                            query_embeddings=[embedding],
                            n_results=3,
                            include=["documents", "metadatas"]
                        )
                    
                    # Use circuit breaker if available
                    if RESILIENCE_AVAILABLE:
                        chromadb_circuit = get_circuit_breaker("chromadb", failure_threshold=5, timeout=60.0)
                        try:
                            results = chromadb_circuit.call(_query_chromadb)
                        except CircuitBreakerError as e:
                            logger.error(f"ChromaDB circuit breaker is OPEN: {e}")
                            results = {"documents": [[]], "metadatas": [[]]}
                    else:
                        results = _query_chromadb()
                    
                    context_chunks = results["documents"][0] if results and results["documents"] else []
                    context = "\n\n".join(context_chunks[:3]) if context_chunks else ""
                    
                    # Stream RAG response
                    for sse_event in streamer.stream_rag_response(
                        query=command,
                        context=context,
                        model="qwen2.5-coder:14b",
                        request_id=request_id
                    ):
                        if not self._safe_write(sse_event, request_id):
                            return
                    return
                except Exception as e:
                    logger.debug(f"RAG streaming failed: {e}, falling back to simple response")
            
            # For commands or fallback, execute and stream result
            commands_script = ROXY_DIR / "roxy_commands.py"
            if commands_script.exists():
                env = os.environ.copy()
                if request_id:
                    env["ROXY_REQUEST_ID"] = request_id
                else:
                    env.pop("ROXY_REQUEST_ID", None)

                result = subprocess.run(
                    ["python3", str(commands_script), command],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=ROXY_DIR,
                    env=env
                )
                
                response_text = (result.stdout or result.stderr or "Command completed").strip()
                
                # Stream response character by character for real-time feel
                for char in response_text:
                    event_data = json.dumps({"token": char, "done": False})
                    if not self._safe_write(f"data: {event_data}\n\n", request_id):
                        return
                    time.sleep(0.01)  # Small delay for readability
                
                self._safe_write(f"event: complete\ndata: {json.dumps({'done': True})}\n\n", request_id)
            else:
                error_data = json.dumps({"error": "roxy_commands.py not found", "done": True})
                self._safe_write(f"event: error\ndata: {error_data}\n\n", request_id)
            
        except (BrokenPipeError, ConnectionResetError):
            logger.info(f"[STREAM] client disconnected requestId={request_id}")
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            error_data = json.dumps({"error": str(e), "done": True})
            self._safe_write(f"event: error\ndata: {error_data}\n\n", request_id)
    
    def do_POST(self):
        """Execute command endpoint"""
        # Support both versioned and unversioned paths
        path = self.path.split('?')[0]  # Remove query string
        
        if path == "/run" or path == "/v1/run":
            self._handle_run_command()
        elif path == "/batch" or path == "/v1/batch":
            self._handle_batch_command()
        elif path == "/benchmark" or path == "/v1/benchmark":
            self._handle_benchmark_mode()
        elif path == "/raw" or path == "/v1/raw":
            self._handle_raw_query()
        elif path == "/modes" or path == "/v1/modes":
            self._handle_list_modes()
        elif path == "/feedback" or path == "/v1/feedback":
            self._handle_feedback_submission()
        elif path == "/memory/recall" or path == "/v1/memory/recall":
            self._handle_memory_recall()
        elif path == "/expert" or path == "/v1/expert":
            self._handle_expert_route()
        elif path == "/warmup" or path == "/v1/warmup":
            self._handle_warmup()
        elif path.startswith("/mcp/"):
            self._handle_mcp_tool(path)
        else:
            self.send_response(404)
            self.end_headers()
    
    def _handle_mcp_tool(self, path: str):
        """Handle MCP tool calls - /mcp/{module}/{tool}"""
        try:
            parts = path.strip('/').split('/')
            if len(parts) < 3:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid MCP path. Use /mcp/{module}/{tool}"}).encode())
                return
            
            _, module_name, tool_name = parts[0], parts[1], parts[2]
            
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b'{}'
            params = json.loads(body.decode('utf-8')) if body else {}
            
            # Load MCP module dynamically
            import importlib.util
            mcp_dir = Path.home() / ".roxy" / "mcp"
            module_path = mcp_dir / f"mcp_{module_name}.py"
            
            if not module_path.exists():
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"MCP module not found: {module_name}"}).encode())
                return
            
            spec = importlib.util.spec_from_file_location(f"mcp_{module_name}", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Call tool
            if hasattr(module, 'handle_tool'):
                result = module.handle_tool(tool_name, params)
            else:
                result = {"error": f"Module {module_name} has no handle_tool function"}
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except json.JSONDecodeError as e:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Invalid JSON: {e}"}).encode())
        except Exception as e:
            logger.error(f"MCP tool error: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_feedback_submission(self):
        """Handle user feedback submission"""
        try:
            # Auth check
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                    return
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            query = data.get('query', '')
            response = data.get('response', '')
            feedback_type = data.get('type', 'neutral')  # positive, negative, neutral, correction
            correction = data.get('correction')
            metadata = data.get('metadata', {})
            
            if not query or not response:
                self.send_error(400, "Query and response required")
                return
            
            if INFRASTRUCTURE_AVAILABLE:
                record_feedback(query, response, feedback_type, correction, metadata)
                result = {"status": "recorded", "type": feedback_type}
            else:
                result = {"status": "skipped", "reason": "feedback system unavailable"}
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            logger.error(f"Feedback submission failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def _handle_memory_recall(self):
        """Handle memory recall request"""
        try:
            # Auth check
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                    return
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            query = data.get('query', '').strip()
            k = int(data.get('k', 5))
            
            if not query:
                self.send_error(400, "Query required")
                return
            
            if INFRASTRUCTURE_AVAILABLE:
                memories = recall_conversations(query, k)
            else:
                memories = []
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"memories": memories, "count": len(memories)}).encode())
            
        except Exception as e:
            logger.error(f"Memory recall failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def _handle_expert_route(self):
        """Handle expert model routing"""
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        try:
            # Auth check
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                    return
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            query = data.get('query', '').strip()
            context = data.get('context', {})
            system_prompt = data.get('system')
            
            if not query:
                self.send_error(400, "Query required")
                return
            
            # Classify the query first
            if INFRASTRUCTURE_AVAILABLE:
                query_type, confidence = classify_query(query)
                response_text = route_query(query, context, system_prompt)
            else:
                query_type, confidence = 'general', 0.5
                # Fallback to standard Ollama
                response_text = query_ollama_direct(query)
            
            response_time = time.time() - start_time
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            # Convert query_type to string if it's an enum
            query_type_str = query_type.value if hasattr(query_type, 'value') else str(query_type)
            
            result = {
                "status": "success",
                "mode": "expert",
                "query_type": query_type_str,
                "confidence": confidence,
                "response": response_text,
                "response_time": round(response_time, 3),
                "request_id": request_id
            }
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            logger.error(f"Expert routing failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_benchmark_mode(self):
        """Handle benchmark mode - direct model access for testing"""
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        try:
            # Auth check
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                    return
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            prompt = data.get('prompt', '').strip()
            model = data.get('model', 'qwen2.5-coder:14b')
            temperature = float(data.get('temperature', 0.0))
            max_tokens = int(data.get('max_tokens', 512))
            
            if not prompt:
                self.send_error(400, "No prompt provided")
                return
            
            logger.info(f"[BENCHMARK] model={model} temp={temperature} requestId={request_id}")
            
            # Direct Ollama query - NO personality, NO RAG, NO validation
            result = query_ollama_direct(prompt, model, temperature, max_tokens)
            
            response_time = time.time() - start_time
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            response = {
                "status": "success",
                "mode": "benchmark",
                "model": model,
                "result": result,
                "response_time": round(response_time, 3),
                "request_id": request_id
            }
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            logger.error(f"Benchmark mode failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def _handle_raw_query(self):
        """Handle raw query - technical mode with minimal processing"""
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        try:
            # Auth check
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                    return
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            prompt = data.get('prompt', '').strip()
            model = data.get('model', 'qwen2.5-coder:14b')
            mode = data.get('mode', 'technical')
            
            if mode not in ROXY_MODES:
                mode = 'technical'
            
            mode_config = ROXY_MODES[mode]
            temperature = float(data.get('temperature', mode_config['temperature']))
            max_tokens = int(data.get('max_tokens', 1024))
            
            if not prompt:
                self.send_error(400, "No prompt provided")
                return
            
            logger.info(f"[RAW] mode={mode} model={model} requestId={request_id}")
            
            # Apply system prompt only if mode requires it
            if mode_config['system_prompt']:
                system = "You are ROXY, a helpful AI assistant. Be concise and accurate."
                full_prompt = f"System: {system}\n\nUser: {prompt}\n\nAssistant:"
            else:
                full_prompt = prompt
            
            result = query_ollama_direct(full_prompt, model, temperature, max_tokens)
            response_time = time.time() - start_time
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            response = {
                "status": "success",
                "mode": mode,
                "model": model,
                "result": result,
                "response_time": round(response_time, 3),
                "request_id": request_id
            }
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            logger.error(f"Raw query failed: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_warmup(self):
        """Warm up Ollama by issuing a minimal generate call."""
        base_url = _get_ollama_base_url()
        snapshot = _snapshot_ollama_health()
        result = {
            "ok": False,
            "base_url": base_url,
            "model": None,
            "latency_ms": snapshot.get("last_latency_ms"),
            "last_ok_ts": snapshot.get("last_ok_ts"),
            "last_error": snapshot.get("last_error"),
            "error": None,
        }

        try:
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                    return

            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b"{}"

            try:
                data = json.loads(body.decode('utf-8')) if body else {}
            except json.JSONDecodeError as exc:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {exc}"}).encode())
                return

            config_defaults = config if 'config' in globals() else {}
            model = (data.get("model") or config_defaults.get("default_model") or "qwen2.5-coder:14b").strip()
            result["model"] = model
            prompt = data.get("prompt", "Warmup check.")
            num_predict = max(1, int(data.get("num_predict", 1)))
            timeout = int(data.get("timeout", 30))

            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": num_predict
                }
            }

            import requests

            start_time = time.perf_counter()
            response = requests.post(f"{base_url}/api/generate", json=payload, timeout=timeout)
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200:
                _record_ollama_success(latency_ms)
                snapshot = _snapshot_ollama_health()
                result.update({
                    "ok": True,
                    "model": model,
                    "latency_ms": snapshot.get("last_latency_ms"),
                    "last_ok_ts": snapshot.get("last_ok_ts"),
                    "last_error": snapshot.get("last_error"),
                })
                status_code = 200
            else:
                error_msg = f"Status {response.status_code}: {response.text[:200]}"
                _record_ollama_error(error_msg)
                snapshot = _snapshot_ollama_health()
                result.update({
                    "ok": False,
                    "model": model,
                    "latency_ms": snapshot.get("last_latency_ms"),
                    "last_ok_ts": snapshot.get("last_ok_ts"),
                    "last_error": snapshot.get("last_error"),
                    "error": error_msg,
                })
                status_code = 502

        except Exception as exc:
            error_msg = str(exc)
            _record_ollama_error(error_msg)
            snapshot = _snapshot_ollama_health()
            result.update({
                "ok": False,
                "model": result.get("model"),
                "latency_ms": snapshot.get("last_latency_ms"),
                "last_ok_ts": snapshot.get("last_ok_ts"),
                "last_error": snapshot.get("last_error"),
                "error": error_msg,
            })
            status_code = 500

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())
    
    def _handle_list_modes(self):
        """List available ROXY modes"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        modes_info = {}
        for mode_name, mode_config in ROXY_MODES.items():
            modes_info[mode_name] = {
                "description": mode_config['description'],
                "system_prompt": mode_config['system_prompt'],
                "temperature": mode_config['temperature']
            }
        
        response = {
            "modes": modes_info,
            "default": "broadcast",
            "endpoints": {
                "/run": "Full ROXY with personality (broadcast mode)",
                "/benchmark": "Direct model access, no personality",
                "/raw": "Configurable mode (technical, creative, etc.)",
                "/modes": "List available modes",
                "/infrastructure": "Infrastructure component status",
                "/infrastructure/stats": "Detailed infrastructure statistics",
                "/feedback/stats": "User feedback statistics"
            }
        }
        self.wfile.write(json.dumps(response, indent=2).encode())
    
    def _handle_infrastructure_status(self):
        """Return infrastructure component status"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        if INFRASTRUCTURE_AVAILABLE:
            status = get_infrastructure_status()
        else:
            status = {
                "initialized": False,
                "available": False,
                "message": "Infrastructure module not available"
            }
        
        self.wfile.write(json.dumps(status, indent=2).encode())
    
    def _handle_infrastructure_stats(self):
        """Return detailed infrastructure statistics"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        if INFRASTRUCTURE_AVAILABLE:
            stats = get_all_stats()
        else:
            stats = {
                "error": "Infrastructure not available",
                "timestamp": datetime.now().isoformat()
            }
        
        self.wfile.write(json.dumps(stats, indent=2).encode())
    
    def _handle_feedback_stats(self):
        """Return feedback statistics"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        if INFRASTRUCTURE_AVAILABLE:
            stats = get_feedback_stats()
        else:
            stats = {"error": "Feedback system not available"}
        
        self.wfile.write(json.dumps(stats, indent=2).encode())

    def _handle_run_command(self):
        """Handle single command execution"""
        start_time = time.time()
        client_ip = self.client_address[0]
        request_id = str(uuid.uuid4())[:8]
        
        # Track request metrics
        if METRICS_AVAILABLE:
            metrics_ctx = MetricsMiddleware(endpoint="/run")
            metrics_ctx.__enter__()
        else:
            metrics_ctx = None
        
        try:
            # Rate limiting - CRITICAL SECURITY FEATURE
            rate_limiting_enabled = config.get("rate_limiting_enabled", False)
            if rate_limiting_enabled:
                try:
                    sys.path.insert(0, str(ROXY_DIR))
                    from rate_limiting import get_rate_limiter
                    rate_limiter = get_rate_limiter()
                    if not rate_limiter.check_rate_limit(client_ip, "/run"):
                        if METRICS_AVAILABLE:
                            record_rate_limit("/run")
                        if METRICS_AVAILABLE and metrics_ctx:
                            metrics_ctx.set_status("rate_limited")
                            metrics_ctx.__exit__(None, None, None)
                        self.send_response(429)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        response = {"status": "error", "message": "Rate limit exceeded"}
                        self.wfile.write(json.dumps(response).encode())
                        return
                except ImportError as e:
                    logger.error(f"CRITICAL: Rate limiting module not available: {e}")
                    logger.error("Rate limiting is enabled in config but module is missing")
                    logger.error("Security feature unavailable - request blocked")
                    self.send_response(503)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    response = {"status": "error", "message": "Rate limiting service unavailable"}
                    self.wfile.write(json.dumps(response).encode())
                    return
                except Exception as e:
                    logger.error(f"Rate limiting check failed: {e}", exc_info=True)
                    # Fail secure: block request if rate limiting fails
                    self.send_response(503)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    response = {"status": "error", "message": "Rate limiting service error"}
                    self.wfile.write(json.dumps(response).encode())
                    return
            
            # Validate auth token if configured
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    user_agent = self.headers.get('User-Agent', 'unknown')
                    token_present = bool(provided_token)
                    token_hash_prefix = hashlib.sha256(provided_token.encode()).hexdigest()[:8] if token_present else "none"
                    reason = "missing_token" if not token_present else "invalid_token"
                    should_log, rate_limited = _register_unauthorized_attempt(client_ip, user_agent)
                    log_line = (
                        f"[AUTH] 403 requestId={request_id} ip={client_ip} path=/run "
                        f"ua=\"{user_agent}\" token_present={str(token_present).lower()} "
                        f"token_hash_prefix={token_hash_prefix} reason={reason}"
                    )
                    if rate_limited:
                        if should_log:
                            logger.warning(f"{log_line} action=rate_limited")
                        if METRICS_AVAILABLE and metrics_ctx:
                            metrics_ctx.set_status("rate_limited")
                            metrics_ctx.__exit__(None, None, None)
                        self.send_response(429)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        payload = {
                            "status": "error",
                            "message": "Too many unauthorized attempts",
                            "request_id": request_id,
                        }
                        self._safe_write(json.dumps(payload), request_id)
                        return

                    if should_log:
                        logger.warning(log_line)
                    else:
                        logger.debug(f"{log_line} (suppressed)")

                    if METRICS_AVAILABLE and metrics_ctx:
                        metrics_ctx.set_status("unauthorized")
                        metrics_ctx.__exit__(None, None, None)
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    payload = {
                        "status": "error",
                        "message": "Forbidden: Invalid or missing token",
                        "request_id": request_id,
                    }
                    self._safe_write(json.dumps(payload), request_id)
                    return
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            command = data.get('command', '').strip()
            if not command:
                self.send_error(400, "No command provided")
                return
            
            # Extract explicit mode and pool from request (Chief's operator controls)
            explicit_mode = data.get('mode', '').upper()  # CHAT, RAG, EXEC
            explicit_pool = data.get('pool', '').upper()  # AUTO, FAST, BIG
            model_override = data.get('model', '')  # Optional model override
            
            # Security: Sanitize input - CRITICAL SECURITY FEATURE
            try:
                sys.path.insert(0, str(ROXY_DIR))
                from security import get_security
                security = get_security()
                sanitized = security.sanitize_input(command)
                    
                if sanitized.get("blocked"):
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    response = {
                        "status": "error",
                        "message": "Command blocked for security reasons",
                        "warnings": sanitized.get("warnings", [])
                    }
                    self.wfile.write(json.dumps(response).encode())
                    return
                
                # Use sanitized command
                command = sanitized.get("sanitized", command)
            except ImportError as e:
                logger.error(f"CRITICAL: Security module not available: {e}")
                logger.error("Security feature unavailable - request blocked")
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response = {"status": "error", "message": "Security service unavailable"}
                self.wfile.write(json.dumps(response).encode())
                return
            except Exception as e:
                logger.error(f"Security check failed: {e}", exc_info=True)
                # Fail secure: block request if security check fails
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response = {"status": "error", "message": "Security check error"}
                self.wfile.write(json.dumps(response).encode())
                return
            
            logger.info(f"Executing command: {command} mode={explicit_mode or 'auto'} pool={explicit_pool or 'auto'}")
            
            # Track execution timing for metadata
            exec_start = time.time()
            
            # Route through existing roxy_commands.py with explicit mode/pool
            result = self._execute_command(
                command, 
                request_id=request_id,
                mode=explicit_mode,
                pool=explicit_pool,
                model_override=model_override
            )
            exec_end = time.time()
            response_time = exec_end - start_time
            total_ms = round((exec_end - exec_start) * 1000, 1)
            
            # Record metrics for successful execution
            if METRICS_AVAILABLE and metrics_ctx:
                metrics_ctx.set_status("success")
            
            # Security: Filter output - CRITICAL SECURITY FEATURE
            try:
                sys.path.insert(0, str(ROXY_DIR))
                from security import get_security
                security = get_security()
                filtered = security.filter_output(result)
                result = filtered.get("filtered", result)
                if filtered.get("warnings"):
                    logger.warning(f"Output filtered: {filtered['warnings']}")
            except ImportError as e:
                logger.error(f"CRITICAL: Security module not available for output filtering: {e}")
                logger.error("Output filtering disabled - potential security risk")
                # Don't block response, but log error
            except Exception as e:
                logger.error(f"Output filtering failed: {e}", exc_info=True)
                # Log but don't block - output filtering is less critical than input
            
            # Observability - ALWAYS log (don't swallow errors)
            sys.path.insert(0, str(ROXY_DIR))
            from observability import get_observability
            obs = get_observability()
            obs.log_request(command, result, response_time, 
                           metadata={"request_id": request_id},
                           request_id=request_id,
                           endpoint="/run")
            
            # Evaluation metrics - Non-critical, allow graceful degradation
            try:
                sys.path.insert(0, str(ROXY_DIR))
                from evaluation.metrics import get_metrics_collector
                collector = get_metrics_collector()
                collector.record_query(
                    query=command,
                    response=result,
                    response_time=response_time,
                    source_attribution="📌" in result or "Source:" in result
                )
            except ImportError:
                # Metrics module not available - not critical, continue
                pass
            except Exception as e:
                logger.warning(f"Metrics collection failed: {e}")
                # Non-critical, continue execution
            
            # Infrastructure integration - Cache, Memory, Events (non-blocking)
            if INFRASTRUCTURE_AVAILABLE:
                try:
                    # Cache the response
                    cache_query(command, result)
                    
                    # Store in episodic memory
                    session_id = self.headers.get('X-ROXY-Session', request_id)
                    remember_conversation(command, result, session_id, {
                        'response_time': response_time,
                        'client_ip': client_ip,
                        'endpoint': '/run'
                    })
                    
                    # Publish response event
                    publish_response_event(
                        query=command,
                        response=result,
                        elapsed=response_time,
                        session_id=session_id,
                        cached=False
                    )
                except Exception as e:
                    logger.debug(f"Infrastructure integration failed (non-critical): {e}")
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            # Build response with execution metadata (Chief's Truth Panel)
            exec_meta = getattr(self, '_last_execution_metadata', {})
            response = {
                "status": "success",
                "command": command,
                "result": result,
                "response_time": round(response_time, 3),
                "metadata": {
                    "mode": exec_meta.get("mode", "auto"),
                    "model_used": exec_meta.get("model_used"),
                    "route": exec_meta.get("route", "unknown"),
                    "pool": exec_meta.get("pool", "auto"),
                    "base_url_used": exec_meta.get("base_url_used", _get_ollama_base_url()),
                    "total_ms": total_ms if 'total_ms' in locals() else None,
                    "tools_count": len(exec_meta.get("tools_executed", []))
                }
            }
            self.wfile.write(json.dumps(response).encode())
            
            # Mark metrics as successful and close context
            if METRICS_AVAILABLE and metrics_ctx:
                metrics_ctx.set_status("success")
                metrics_ctx.__exit__(None, None, None)
                
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"Command execution failed: {e}")
            
            # Mark metrics as error and close context
            if METRICS_AVAILABLE and metrics_ctx:
                metrics_ctx.set_status("error")
                metrics_ctx.__exit__(type(e), e, None)
            
            # Log error to observability
            try:
                sys.path.insert(0, str(ROXY_DIR))
                from observability import get_observability
                obs = get_observability()
                obs.log_error(command if 'command' in locals() else "", str(e))
            except:
                pass
            
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"status": "error", "message": str(e)}
            self.wfile.write(json.dumps(response).encode())
    
    def _handle_batch_command(self):
        """Handle batch command execution"""
        start_time = time.time()
        client_ip = self.client_address[0]
        request_id = str(uuid.uuid4())[:8]
        
        # Track request metrics
        if METRICS_AVAILABLE:
            metrics_ctx = MetricsMiddleware(endpoint="/batch")
            metrics_ctx.__enter__()
        else:
            metrics_ctx = None
        
        try:
            # Rate limiting - CRITICAL SECURITY FEATURE
            rate_limiting_enabled = config.get("rate_limiting_enabled", False)
            if rate_limiting_enabled:
                try:
                    sys.path.insert(0, str(ROXY_DIR))
                    from rate_limiting import get_rate_limiter
                    rate_limiter = get_rate_limiter()
                    if not rate_limiter.check_rate_limit(client_ip, "/batch"):
                        if METRICS_AVAILABLE:
                            record_rate_limit("/batch")
                        if METRICS_AVAILABLE and metrics_ctx:
                            metrics_ctx.set_status("rate_limited")
                            metrics_ctx.__exit__(None, None, None)
                        self.send_response(429)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        response = {"status": "error", "message": "Rate limit exceeded"}
                        self.wfile.write(json.dumps(response).encode())
                        return
                except ImportError as e:
                    logger.error(f"CRITICAL: Rate limiting module not available: {e}")
                    logger.error("Rate limiting is enabled in config but module is missing")
                    logger.error("Security feature unavailable - request blocked")
                    self.send_response(503)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    response = {"status": "error", "message": "Rate limiting service unavailable"}
                    self.wfile.write(json.dumps(response).encode())
                    return
                except Exception as e:
                    logger.error(f"Rate limiting check failed: {e}", exc_info=True)
                    # Fail secure: block request if rate limiting fails
                    self.send_response(503)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    response = {"status": "error", "message": "Rate limiting service error"}
                    self.wfile.write(json.dumps(response).encode())
                    return
            
            # Validate auth token if configured
            if AUTH_TOKEN:
                provided_token = self.headers.get('X-ROXY-Token')
                if not provided_token or provided_token != AUTH_TOKEN:
                    user_agent = self.headers.get('User-Agent', 'unknown')
                    token_present = bool(provided_token)
                    token_hash_prefix = hashlib.sha256(provided_token.encode()).hexdigest()[:8] if token_present else "none"
                    reason = "missing_token" if not token_present else "invalid_token"
                    should_log, rate_limited = _register_unauthorized_attempt(client_ip, user_agent)
                    log_line = (
                        f"[AUTH] 403 requestId={request_id} ip={client_ip} path=/batch "
                        f"ua=\"{user_agent}\" token_present={str(token_present).lower()} "
                        f"token_hash_prefix={token_hash_prefix} reason={reason}"
                    )
                    if rate_limited:
                        if should_log:
                            logger.warning(f"{log_line} action=rate_limited")
                        if METRICS_AVAILABLE and metrics_ctx:
                            metrics_ctx.set_status("rate_limited")
                            metrics_ctx.__exit__(None, None, None)
                        self.send_response(429)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        payload = {
                            "status": "error",
                            "message": "Too many unauthorized attempts",
                            "request_id": request_id,
                        }
                        self._safe_write(json.dumps(payload), request_id)
                        return

                    if should_log:
                        logger.warning(log_line)
                    else:
                        logger.debug(f"{log_line} (suppressed)")

                    if METRICS_AVAILABLE and metrics_ctx:
                        metrics_ctx.set_status("unauthorized")
                        metrics_ctx.__exit__(None, None, None)
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    payload = {
                        "status": "error",
                        "message": "Forbidden: Invalid or missing token",
                        "request_id": request_id,
                    }
                    self._safe_write(json.dumps(payload), request_id)
                    return
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            commands = data.get('commands', [])
            if not commands or not isinstance(commands, list):
                self.send_error(400, "No commands provided or invalid format")
                return
            
            logger.info(f"Executing batch: {len(commands)} commands")
            
            # Execute commands in parallel (async batch processing)
            import concurrent.futures
            results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = {
                    executor.submit(self._execute_command, cmd, f"{request_id}:{idx}"): cmd
                    for idx, cmd in enumerate(commands)
                }
                for future in concurrent.futures.as_completed(futures):
                    cmd = futures[future]
                    try:
                        result = future.result(timeout=30)
                        results.append({"command": cmd, "status": "success", "result": result})
                    except Exception as e:
                        results.append({"command": cmd, "status": "error", "error": str(e)})
            
            response_time = time.time() - start_time
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            response = {
                "status": "success",
                "commands": results,
                "total": len(commands),
                "response_time": round(response_time, 3)
            }
            self.wfile.write(json.dumps(response).encode())
            
            # Close metrics context on success
            if METRICS_AVAILABLE and metrics_ctx:
                metrics_ctx.set_status("success")
                metrics_ctx.__exit__(None, None, None)
            
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"Batch command execution failed: {e}")
            
            # Close metrics context on error
            if METRICS_AVAILABLE and metrics_ctx:
                metrics_ctx.set_status("error")
                metrics_ctx.__exit__(type(e), e, None)
            
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"status": "error", "message": str(e)}
            self.wfile.write(json.dumps(response).encode())
    
    def _execute_command(self, command: str, request_id: Optional[str] = None,
                          mode: str = "", pool: str = "", model_override: str = "") -> str:
        """Execute command via roxy_commands.py with caching and validation
        
        Args:
            command: The user command to execute
            request_id: Optional request tracking ID
            mode: Explicit mode (CHAT, RAG, EXEC) - empty means auto-route
            pool: Explicit pool (AUTO, FAST, BIG) - empty means auto
            model_override: Optional model name override
        """
        
        # Initialize execution metadata for this call
        self._last_execution_metadata = {
            "mode": mode.lower() if mode else "auto",
            "model_used": model_override or None,
            "route": "unknown",
            "pool": pool.lower() if pool else "auto",
            "base_url_used": _get_ollama_base_url(),
            "tools_executed": []
        }
        
        # GREETING FASTPATH - Instant response for simple greetings
        import re
        greeting_patterns = [
            r"^hi\s+roxy", r"^hello\s*(roxy)?", r"^hey\s+roxy",
            r"^hi\s*$", r"^hey\s*$", r"^hello\s*$",
            r"^(what'?s?\s+up|sup|wassup|how'?s?\s+it\s+going|howdy)\s*(roxy)?",
            r"^good\s+(morning|afternoon|evening)\s*(roxy)?",
        ]
        if any(re.match(p, command, re.IGNORECASE) for p in greeting_patterns):
            return "Hi! I'm ROXY, your resident AI assistant. How can I help you today?"
        
        # CONVERSATIONAL BYPASS - Detect casual chat (for Truth Gate)
        casual_chat_patterns = [
            r"(how are you|how'?s?\s+you|how do you feel|are you ok)",
            r"(tell me (a joke|something|about yourself))",
            r"(what do you think|your opinion)",
        ]
        is_casual_chat = any(re.search(p, command, re.IGNORECASE) for p in casual_chat_patterns)
        
        # Get context from conversation history
        try:
            sys.path.insert(0, str(ROXY_DIR))
            from context_manager import get_context_manager
            context_mgr = get_context_manager()
            context = context_mgr.get_context(command, include_recent=5)
        except Exception as e:
            logger.debug(f"Context manager failed: {e}")
            context = None
        
        # CHIEF'S CACHE FIX: Never bypass routing for tool-forcing or file queries
        # Cache discipline: only cache AFTER we know mode == "rag" from roxy_commands
        
        # Skip cache for anything that needs preflight routing
        bypass_cache = (
            command.strip().startswith('{') or  # JSON tool calls
            command.startswith('RUN_TOOL ') or  # Explicit tool syntax
            self._is_file_claim_query(command)  # File-existence queries
        )
        
        # Check cache first (for pure RAG queries only)
        if not bypass_cache and self._is_rag_query(command):
            try:
                # Use infrastructure cache (Redis with fallback)
                if INFRASTRUCTURE_AVAILABLE:
                    cached = get_cached_response(command)
                else:
                    sys.path.insert(0, str(ROXY_DIR))
                    from cache import get_cache as get_legacy_cache
                    cache = get_legacy_cache()
                    cached = cache.get(command) if cache else None
                    
                if cached:
                    # Record cache hit
                    if METRICS_AVAILABLE:
                        record_cache_hit()
                    if isinstance(cached, dict):
                        response = cached.get("response", "")
                        similarity = cached.get("similarity", 1.0)
                        if similarity < 0.9:
                            response += f"\n\n(Similar to: {cached.get('cached_query', '')[:50]}...)"
                        return response
                    else:
                        return cached
                else:
                    # Record cache miss
                    if METRICS_AVAILABLE:
                        record_cache_miss()
            except Exception as e:
                logger.debug(f"Cache lookup failed: {e}")
                if METRICS_AVAILABLE:
                    record_cache_miss()
        
        # Define commands script path
        commands_script = ROXY_DIR / "roxy_commands.py"
        if not commands_script.exists():
            return "ERROR: roxy_commands.py not found"
        
        # Acquire semaphore to limit concurrent subprocess spawns (prevent system overload)
        with subprocess_semaphore:
            try:
                env = os.environ.copy()
                if request_id:
                    env["ROXY_REQUEST_ID"] = request_id
                else:
                    env.pop("ROXY_REQUEST_ID", None)
                
                # Pass explicit operator controls as env vars (Chief's mode/pool)
                # --- CHIEF'S LOGIC: Strict Pool Enforcement ---
                effective_mode = mode.upper() if mode else "AUTO"
                effective_pool = pool.upper() if pool else "AUTO"
                pool_config = _resolve_ollama_pools()

                # If CHAT mode and no explicit pool, we MUST use BIG.
                if effective_mode == "CHAT" and effective_pool == "AUTO":
                    if pool_config["big"]["configured"]:
                        effective_pool = "BIG"
                        logger.info(f"CHAT mode -> enforcing BIG pool ({pool_config['big']['url']})")
                    else:
                        # CHIEF'S P0 REQUIREMENT: Do not silently degrade to tiny model.
                        # If BIG is expected but not configured, we fail fast.
                        return "ERROR: CHAT mode requires a configured BIG pool (OLLAMA_BIG_URL). Explicitly set pool=FAST if you want to use the smaller model."
                
                # Validate explicit requests
                if effective_pool == "BIG" and not pool_config["big"]["configured"]:
                    return "ERROR: Pool BIG requested but not configured (OLLAMA_BIG_URL missing)."
                if effective_pool == "FAST" and not pool_config["fast"]["configured"]:
                    return "ERROR: Pool FAST requested but not configured (OLLAMA_FAST_URL missing)."

                # Update metadata so it reflects the forced decision even if parsing fails later
                self._last_execution_metadata["pool"] = effective_pool.lower()
                self._last_execution_metadata["mode"] = effective_mode.lower()
                
                # Set base_url_used based on effective pool
                if effective_pool == "BIG" and pool_config["big"]["configured"]:
                    self._last_execution_metadata["base_url_used"] = pool_config["big"]["url"]
                elif effective_pool == "FAST" and pool_config["fast"]["configured"]:
                    self._last_execution_metadata["base_url_used"] = pool_config["fast"]["url"]
                else:
                    self._last_execution_metadata["base_url_used"] = pool_config["default"]

                if mode:
                    env["ROXY_MODE"] = effective_mode
                
                # Only set ROXY_POOL if it's not AUTO (let roxy_commands decide if truly auto, 
                # but here we might have forced it to BIG)
                if effective_pool != "AUTO":
                    env["ROXY_POOL"] = effective_pool

                if model_override:
                    env["ROXY_MODEL"] = model_override

                result = subprocess.run(
                    ["python3", str(commands_script), command],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=ROXY_DIR,
                    env=env
                )
                
                output = result.stdout or result.stderr or "Command completed (no output)"
                response_text = output.strip()
                
                # Parse structured response (Chief's Phase 2 - replaces JSON footer)
                tools_executed = []
                mode = "unknown"
                metadata = {}
                
                if "__STRUCTURED_RESPONSE__" in response_text:
                    parts = response_text.split("__STRUCTURED_RESPONSE__")
                    response_text = parts[0].strip()  # Text before marker
                    if len(parts) > 1:
                        try:
                            import json
                            structured = json.loads(parts[1].strip())
                            tools_executed = structured.get("tools_executed", [])
                            mode = structured.get("mode", "unknown")
                            metadata = structured.get("metadata", {})
                            logger.debug(f"Parsed structured response: mode={mode}, tools={len(tools_executed)}")
                            
                            # Store metadata for caller (Chief's Truth Panel)
                            existing_meta = self._last_execution_metadata.copy()
                            self._last_execution_metadata = {
                                "mode": mode,
                                "model_used": metadata.get("model", metadata.get("model_used")),
                                "route": mode,  # rag, tool_direct, etc.
                                "pool": metadata.get("pool", effective_pool.lower()),
                                "tools_executed": tools_executed
                            }
                            # Preserve base_url_used from our earlier decision
                            self._last_execution_metadata["base_url_used"] = existing_meta.get("base_url_used", pool_config["default"])
                        except json.JSONDecodeError as e:
                            logger.debug(f"Failed to parse structured response: {e}")
                
                # Backward compatibility: try old JSON footer
                elif "__TOOLS_EXECUTED__" in response_text:
                    parts = response_text.split("__TOOLS_EXECUTED__")
                    response_text = parts[0].strip()
                    if len(parts) > 1:
                        try:
                            import json
                            tools_executed = json.loads(parts[1].strip())
                            logger.debug(f"Extracted {len(tools_executed)} tool executions (legacy footer)")
                        except json.JSONDecodeError as e:
                            logger.debug(f"Failed to parse tools_executed JSON: {e}")
                
                # Apply Truth Gate validation (prevent hallucinations)
                if TRUTH_GATE_AVAILABLE:
                    try:
                        truth_gate = get_truth_gate()
                        # Disable file verification for RAG (files are in context, thus verified)
                        check_files = not self._is_rag_query(command)
                        # Disable action checking for casual chat
                        check_actions = not is_casual_chat
                        response_text = truth_gate.validate_response(
                            response_text, 
                            tools_executed,
                            check_file_claims=check_files,
                            check_action_claims=check_actions
                        )
                        logger.debug(f"Truth Gate applied (file_check={check_files}, action_check={check_actions})")
                    except Exception as e:
                        logger.debug(f"Truth Gate validation failed: {e}")
                
                # Cache response if it's a RAG query
                if self._is_rag_query(command):
                    try:
                        # Use infrastructure cache (Redis with fallback)
                        if INFRASTRUCTURE_AVAILABLE:
                            cache_query(command, response_text)
                        else:
                            sys.path.insert(0, str(ROXY_DIR))
                            from cache import get_cache as get_legacy_cache
                            cache = get_legacy_cache()
                            if cache:
                                cache.set(command, response_text)
                    except Exception as e:
                        logger.debug(f"Cache storage failed: {e}")
                    
                    # Validate response
                    response_text = self._validate_response(response_text, command)
                    
                    # Add to conversation history
                    try:
                        sys.path.insert(0, str(ROXY_DIR))
                        from context_manager import get_context_manager
                        context_mgr = get_context_manager()
                        context_mgr.add_to_history(command, response_text)
                    except Exception as e:
                        logger.debug(f"Context manager add failed: {e}")
                
                return response_text
                
            except subprocess.TimeoutExpired:
                return "ERROR: Command timed out after 30 seconds"
            except Exception as e:
                return f"ERROR: {str(e)}"
    
    def _is_rag_query(self, command: str) -> bool:
        """Check if command is a RAG query"""
        rag_indicators = ["what", "how", "explain", "tell me", "describe", "?"]
        command_lower = command.lower()
        return any(indicator in command_lower for indicator in rag_indicators) or "?" in command
    
    def _is_file_claim_query(self, command: str) -> bool:
        """Check if command is asking about files (needs preflight verification)"""
        import re
        command_lower = command.lower()
        
        # Phrase-based triggers
        file_triggers = [
            "onboarding documents", "onboarding docs", "which onboarding",
            "list onboarding", "what onboarding", "onboarding files",
            "which docs", "list docs", "what docs exist",
            "which files", "list files", "what files"
        ]
        
        if any(trigger in command_lower for trigger in file_triggers):
            return True
        
        # File extension detection (more robust than phrase matching)
        # Match: roxy_assistant.py, START_HERE.md, config.json, etc.
        file_pattern = re.search(r'\b[\w./-]+\.(py|md|js|ts|tsx|jsx|json|yaml|yml|sh|txt|rs|go)\b', command_lower)
        if file_pattern:
            return True
        
        return False
    
    def _validate_response(self, response: str, query: str) -> str:
        """Validate response using validation gates"""
        try:
            sys.path.insert(0, str(ROXY_DIR))
            from validation.fact_checker import FactChecker
            from validation.source_verifier import SourceVerifier
            from validation.confidence_scorer import ConfidenceScorer
            
            fact_checker = FactChecker()
            source_verifier = SourceVerifier()
            confidence_scorer = ConfidenceScorer()
            
            # Fact check
            fact_result = fact_checker.validate_response(response, query)
            
            # Source verify
            source_result = source_verifier.verify_rag_result(
                query, response, 
                context_chunks=response.count("📌") or 1
            )
            
            # Calculate confidence
            confidence = confidence_scorer.calculate_confidence(
                fact_result,
                source_result,
                response_length=len(response),
                has_source="📌" in response or "Source:" in response
            )
            
            # Log validation results (INFO level for visibility)
            logger.info(f"[VALIDATION] fact_check={fact_result.get('is_valid')}, "
                       f"source_check={source_result.get('is_verified')}, "
                       f"confidence={confidence:.2f}")
            
            # Add confidence indicator if low
            if confidence < 0.7:
                confidence_level = confidence_scorer.get_confidence_level(confidence)
                response += f"\n\n⚠️ Confidence: {confidence_level} ({confidence:.0%})"
                if fact_result.get("warnings"):
                    response += f"\n⚠️ Warnings: {', '.join(fact_result['warnings'][:2])}"
            
            return response
        except ImportError:
            # Validation not available, return original response
            logger.debug("Validation modules not available")
            return response
        except Exception as e:
            logger.warning(f"Validation failed: {e}")
            return response


class RoxyCore:
    """Always-on ROXY background service"""
    
    def __init__(self):
        self.server = None
        self.server_thread = None
        self.running = True
        self.advanced_services = {}
        
        logger.info("=" * 60)
        logger.info("ROXY CORE INITIALIZING")
        logger.info(f"IPC Endpoint: http://{IPC_HOST}:{IPC_PORT}")
        logger.info("=" * 60)
        
        # Initialize Prometheus metrics if available
        if METRICS_AVAILABLE:
            try:
                if init_prometheus(port=9091):
                    logger.info("✓ Prometheus metrics server started on port 9091")
                else:
                    logger.warning("Prometheus metrics server failed to start")
            except Exception as e:
                logger.warning(f"Prometheus initialization failed: {e}")
        
        # Check for advanced services
        if SERVICE_BRIDGE_AVAILABLE:
            try:
                availability = check_services_availability()
                if is_advanced_mode():
                    logger.info("✓ Advanced services available")
                    report = get_availability_report()
                    for service, available in report.items():
                        if available:
                            logger.info(f"  - {service}: available")
                else:
                    logger.info("Using basic mode (advanced services not available)")
            except Exception as e:
                logger.debug(f"Service bridge check failed: {e}")
    
    def start(self):
        """Start the core service"""
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Start HTTP server
        try:
            self.server = HTTPServer((IPC_HOST, IPC_PORT), RoxyCoreHandler)
            logger.info(f"✓ HTTP IPC server listening on {IPC_HOST}:{IPC_PORT}")
            
            # Run server in background thread
            self.server_thread = Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            logger.info("✓ Server thread started")
            
        except OSError as e:
            if "Address already in use" in str(e):
                logger.error(f"ERROR: Port {IPC_PORT} already in use")
                logger.error("Another ROXY core instance may be running")
                logger.error(f"Check with: systemctl --user status roxy-core")
                sys.exit(1)
            raise
        
        # Background monitoring (optional - can add ChromaDB indexing, health checks, etc.)
        self._start_background_tasks()
        
        logger.info("=" * 60)
        logger.info("ROXY CORE RUNNING")
        logger.info("Test with: curl http://127.0.0.1:8765/health")
        logger.info("=" * 60)
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nShutdown signal received")
            self.stop()
    
    def stop(self):
        """Graceful shutdown"""
        logger.info("Stopping ROXY core...")
        self.running = False
        
        if self.server:
            self.server.shutdown()
            logger.info("✓ HTTP server stopped")
        
        logger.info("ROXY core stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle termination signals"""
        logger.info(f"Received signal {signum}")
        self.stop()
        sys.exit(0)
    
    def _start_background_tasks(self):
        """Start optional background monitoring/indexing"""
        # Check if advanced services are available for background tasks
        if SERVICE_BRIDGE_AVAILABLE:
            try:
                from adapters.service_bridge import get_observability
                obs = get_observability()
                if obs:
                    self.advanced_services['observability'] = obs
                    logger.info("✓ Advanced observability enabled")
            except Exception as e:
                logger.debug(f"Observability initialization failed: {e}")
        
        logger.info("Background tasks: ready")


def main():
    """Main entry point"""
    # Verify environment
    roxy_dir = Path.home() / ".roxy"
    if not roxy_dir.exists():
        logger.error(f"ERROR: {roxy_dir} does not exist")
        logger.error("ROXY infrastructure not found")
        sys.exit(1)
    
    # Start core service
    core = RoxyCore()
    core.start()


if __name__ == "__main__":
    main()
