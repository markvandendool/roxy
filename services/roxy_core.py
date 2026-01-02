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
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
from threading import Thread

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
        is_available as prometheus_available
    )
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.debug("Prometheus metrics not available")
# Truth Gate for response validation (prevent hallucinations)
try:
    sys.path.insert(0, str(ROXY_DIR))
    from truth_gate import get_truth_gate
    TRUTH_GATE_AVAILABLE = True
    logger.info("✅ Truth Gate initialized (hallucination prevention)")
except ImportError:
    TRUTH_GATE_AVAILABLE = False
    logger.debug("Truth Gate not available, responses unvalidated")

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
MAX_CONCURRENT_SUBPROCESSES = 3  # Allow max 3 simultaneous roxy_commands.py processes
subprocess_semaphore = threading.Semaphore(MAX_CONCURRENT_SUBPROCESSES)


class RoxyCoreHandler(BaseHTTPRequestHandler):
    """HTTP handler for ROXY core IPC"""
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info("%s - %s" % (self.address_string(), format % args))
    
    def do_GET(self):
        """Health check and streaming endpoints"""
        # Support both versioned and unversioned paths
        path = self.path.split('?')[0]  # Remove query string
        
        if path == "/health" or path == "/v1/health":
            self._handle_health_check()
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
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                health_status["checks"]["ollama"] = "ok"
            else:
                health_status["checks"]["ollama"] = f"unavailable: {response.status_code}"
                all_healthy = False
        except Exception as e:
            health_status["checks"]["ollama"] = f"error: {str(e)[:50]}"
            all_healthy = False
        
        # Return appropriate status code
        if all_healthy:
            self.send_response(200)
        else:
            self.send_response(503)  # Service Unavailable
        
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(health_status).encode())
    
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
                        self.wfile.write(json.dumps(response).encode())
                        if metrics_ctx:
                            metrics_ctx.set_status("rate_limited")
                            metrics_ctx.__exit__(None, None, None)
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
            self._stream_command_response(command)
            
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            # Close metrics context on error
            if METRICS_AVAILABLE and metrics_ctx:
                metrics_ctx.set_status("error")
                metrics_ctx.__exit__(type(e), e, None)
            self.send_error(500, str(e))
    
    def _stream_command_response(self, command: str):
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
                    self.wfile.write(f"data: {event_data}\n\n".encode())
                    self.wfile.flush()
                    time.sleep(0.01)
                self.wfile.write(f"event: complete\ndata: {json.dumps({'done': True})}\n\n".encode())
                self.wfile.flush()
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
                        model="qwen2.5-coder:14b"
                    ):
                        self.wfile.write(sse_event.encode())
                        self.wfile.flush()
                    return
                except Exception as e:
                    logger.debug(f"RAG streaming failed: {e}, falling back to simple response")
                    # Close metrics context on error
                    if METRICS_AVAILABLE and metrics_ctx:
                        metrics_ctx.set_status("error")
                        metrics_ctx.__exit__(type(e), e, None)
            
            # For commands or fallback, execute and stream result
            commands_script = ROXY_DIR / "roxy_commands.py"
            if commands_script.exists():
                result = subprocess.run(
                    ["python3", str(commands_script), command],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=ROXY_DIR
                )
                
                response_text = (result.stdout or result.stderr or "Command completed").strip()
                
                # Stream response character by character for real-time feel
                for char in response_text:
                    event_data = json.dumps({"token": char, "done": False})
                    self.wfile.write(f"data: {event_data}\n\n".encode())
                    self.wfile.flush()
                    time.sleep(0.01)  # Small delay for readability
                
                self.wfile.write(f"event: complete\ndata: {json.dumps({'done': True})}\n\n".encode())
                self.wfile.flush()
            else:
                error_data = json.dumps({"error": "roxy_commands.py not found", "done": True})
                self.wfile.write(f"event: error\ndata: {error_data}\n\n".encode())
                self.wfile.flush()
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            error_data = json.dumps({"error": str(e), "done": True})
            self.wfile.write(f"event: error\ndata: {error_data}\n\n".encode())
            self.wfile.flush()
            # Close metrics context on error
            if METRICS_AVAILABLE and 'metrics_ctx' in locals() and metrics_ctx:
                metrics_ctx.set_status("error")
                metrics_ctx.__exit__(type(e), e, None)
    
    def do_POST(self):
        """Execute command endpoint"""
        # Support both versioned and unversioned paths
        path = self.path.split('?')[0]  # Remove query string
        
        if path == "/run" or path == "/v1/run":
            self._handle_run_command()
        elif path == "/batch" or path == "/v1/batch":
            self._handle_batch_command()
        else:
            self.send_response(404)
            self.end_headers()
    
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
                    self.send_error(403, "Forbidden: Invalid or missing token")
                    logger.warning(f"Unauthorized access attempt from {client_ip}")
                    return
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            command = data.get('command', '').strip()
            if not command:
                self.send_error(400, "No command provided")
                return
            
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
            
            logger.info(f"Executing command: {command}")
            
            # Route through existing roxy_commands.py
            result = self._execute_command(command)
            response_time = time.time() - start_time
            
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
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            response = {
                "status": "success",
                "command": command,
                "result": result,
                "response_time": round(response_time, 3)
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
                    self.send_error(403, "Forbidden: Invalid or missing token")
                    logger.warning(f"Unauthorized batch access attempt from {client_ip}")
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
                futures = {executor.submit(self._execute_command, cmd): cmd for cmd in commands}
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
    
    def _execute_command(self, command: str) -> str:
        """Execute command via roxy_commands.py with caching and validation"""
        
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
                sys.path.insert(0, str(ROXY_DIR))
                from cache import get_cache
                cache = get_cache()
                cached = cache.get(command)
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
                result = subprocess.run(
                    ["python3", str(commands_script), command],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=ROXY_DIR
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
                        sys.path.insert(0, str(ROXY_DIR))
                        from cache import get_cache
                        cache = get_cache()
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
