#!/usr/bin/env python3
"""
ROXY Status Endpoint Patch - STORY-002
======================================
This file contains the /status handler code to be patched into roxy_core.py
on the authority host. Returns contract-compliant JSON per ROXY_STATUS_CONTRACT_V1.md.

USAGE: This file is not meant to be executed directly. It is:
  1. Copied to authority host via deploy script
  2. Inserted into ~/.roxy/roxy_core.py by deploy script
  3. Then roxy-core service is restarted

AUTHORITY: ROXY-MONITOR-TUI-V1 STORY-002
CONTRACT: docs/roxy/ROXY_STATUS_CONTRACT_V1.md
SCHEMA: tools/roxy-monitor/src/roxy_monitor/schema/status_v1.json
"""

import json
import time
import os
from datetime import datetime
from typing import Any, Dict

# ==============================================================================
# HANDLER CODE TO INSERT INTO ROXYRequestHandler CLASS
# ==============================================================================

STATUS_ENDPOINT_HANDLER = '''
    def _handle_status(self):
        """
        GET /status - Contract-compliant status endpoint.
        
        Returns unified health/metrics/dependencies JSON.
        Requires X-ROXY-Token header for authentication.
        
        Contract: ROXY_STATUS_CONTRACT_V1.md
        Schema version: 1.0.0
        """
        request_id = str(uuid.uuid4())[:8]
        
        # Auth check - X-ROXY-Token required
        if AUTH_TOKEN:
            provided_token = self.headers.get('X-ROXY-Token')
            if not provided_token or provided_token != AUTH_TOKEN:
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                error_response = {
                    "error": "unauthorized",
                    "message": "Missing or invalid X-ROXY-Token header"
                }
                self.wfile.write(json.dumps(error_response).encode())
                logger.warning(f"[{request_id}] /status 401 - invalid token")
                return
        
        try:
            start_time = time.time()
            
            # Build contract-compliant response
            status_response = self._build_status_response()
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.debug(f"[{request_id}] /status 200 - {elapsed_ms}ms")
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-Request-ID", request_id)
            self.send_header("X-Response-Time-Ms", str(elapsed_ms))
            self.end_headers()
            self.wfile.write(json.dumps(status_response, indent=2).encode())
            
        except Exception as e:
            logger.error(f"[{request_id}] /status 500 - {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "internal_error",
                "message": str(e)[:100]
            }).encode())

    def _build_status_response(self) -> dict:
        """
        Build contract-compliant status response.
        
        Schema version: 1.0.0
        Required: version, timestamp, status, service, dependencies
        Optional: traffic, latency, queues, storage, meta
        """
        import socket
        
        # Determine overall status from dependencies
        dep_status = self._get_dependency_status()
        overall_status = "healthy"
        for dep_name, dep_info in dep_status.items():
            if isinstance(dep_info, dict):
                s = dep_info.get("status", "unknown")
                if s == "down":
                    overall_status = "down"
                    break
                elif s == "degraded" and overall_status != "down":
                    overall_status = "degraded"
        
        # Build response per contract
        response = {
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": overall_status,
            "service": {
                "name": "roxy-core",
                "version": "0.1.0",
                "uptime_seconds": int(time.time() - _server_start_time),
                "pid": os.getpid()
            },
            "dependencies": dep_status
        }
        
        # Add optional traffic metrics if available
        traffic = self._get_traffic_metrics()
        if traffic:
            response["traffic"] = traffic
        
        # Add optional latency metrics if available
        latency = self._get_latency_metrics()
        if latency:
            response["latency"] = latency
        
        # Add meta
        response["meta"] = {
            "host": socket.gethostname(),
            "environment": os.environ.get("ROXY_ENV", "production")
        }
        
        return response

    def _get_dependency_status(self) -> dict:
        """Get status of all dependencies for /status endpoint."""
        deps = {}
        
        # MCP servers status
        mcp_status = {
            "status": "healthy",
            "count": 0,
            "healthy": 0,
            "degraded": 0,
            "down": 0
        }
        try:
            if SERVICE_BRIDGE_AVAILABLE:
                report = get_availability_report()
                services = report.get("services", {})
                for name, info in services.items():
                    mcp_status["count"] += 1
                    if info.get("available"):
                        mcp_status["healthy"] += 1
                    else:
                        mcp_status["down"] += 1
                if mcp_status["down"] > 0:
                    if mcp_status["healthy"] > 0:
                        mcp_status["status"] = "degraded"
                    else:
                        mcp_status["status"] = "down"
        except Exception as e:
            mcp_status["status"] = "unknown"
            mcp_status["error"] = str(e)[:50]
        deps["mcp_servers"] = mcp_status
        
        # WebSocket connections
        ws_status = {
            "status": "healthy",
            "connections": 0
        }
        try:
            # Count active SSE/streaming connections if tracked
            ws_status["connections"] = len(getattr(self.server, '_active_streams', []))
        except:
            pass
        deps["websocket"] = ws_status
        
        # Ollama (LLM backend)
        ollama_status = {"status": "unknown"}
        try:
            import requests
            resp = requests.get("http://localhost:11434/api/tags", timeout=2)
            if resp.status_code == 200:
                ollama_status["status"] = "healthy"
                models = resp.json().get("models", [])
                ollama_status["models_loaded"] = len(models)
            else:
                ollama_status["status"] = "degraded"
        except Exception as e:
            ollama_status["status"] = "down"
            ollama_status["error"] = str(e)[:50]
        deps["ollama"] = ollama_status
        
        # ChromaDB (vector store)
        chroma_status = {"status": "unknown"}
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(ROXY_DIR / "chroma_db"))
            collections = client.list_collections()
            chroma_status["status"] = "healthy"
            chroma_status["collections"] = len(collections)
        except Exception as e:
            chroma_status["status"] = "down"
            chroma_status["error"] = str(e)[:50]
        deps["chromadb"] = chroma_status
        
        return deps

    def _get_traffic_metrics(self) -> dict:
        """Get traffic metrics for /status endpoint if available."""
        try:
            if METRICS_AVAILABLE:
                # Use prometheus counters if available
                from prometheus_metrics import get_request_counts
                counts = get_request_counts()
                return {
                    "requests_total": counts.get("total", 0),
                    "requests_1m": counts.get("last_1m", 0),
                    "requests_5m": counts.get("last_5m", 0),
                    "errors_total": counts.get("errors_total", 0),
                    "errors_1m": counts.get("errors_1m", 0)
                }
        except:
            pass
        return None

    def _get_latency_metrics(self) -> dict:
        """Get latency metrics for /status endpoint if available."""
        try:
            if METRICS_AVAILABLE:
                from prometheus_metrics import get_latency_percentiles
                percentiles = get_latency_percentiles()
                return {
                    "p50_ms": percentiles.get("p50", 0),
                    "p95_ms": percentiles.get("p95", 0),
                    "p99_ms": percentiles.get("p99", 0),
                    "avg_ms": percentiles.get("avg", 0)
                }
        except:
            pass
        return None
'''

# ==============================================================================
# ROUTE REGISTRATION CODE
# ==============================================================================

DO_GET_ROUTE = '''        elif path == "/status" or path == "/v1/status":
            self._handle_status()'''

# ==============================================================================
# GLOBAL VARIABLE (server start time for uptime calculation)
# ==============================================================================

GLOBAL_VAR = '''
# Server start time for /status uptime calculation (added by status_endpoint_patch.py)
_server_start_time = time.time()
'''

# ==============================================================================
# VALIDATION - Can be run standalone to syntax-check this file
# ==============================================================================

if __name__ == "__main__":
    import ast
    import sys
    
    print("Validating status_endpoint_patch.py...")
    
    # Check that STATUS_ENDPOINT_HANDLER is valid Python (as class methods)
    # Wrap in a dummy class to make it parseable
    test_code = f"""
import os
import json
import time
import uuid
from datetime import datetime

AUTH_TOKEN = "test"
SERVICE_BRIDGE_AVAILABLE = False
METRICS_AVAILABLE = False
ROXY_DIR = "."
_server_start_time = time.time()

def get_availability_report():
    return {{"services": {{}}}}

class DummyServer:
    _active_streams = []

class DummyHandler:
    server = DummyServer()
    headers = {{}}
    def send_response(self, code): pass
    def send_header(self, k, v): pass
    def end_headers(self): pass
    class wfile:
        @staticmethod
        def write(data): pass
    
{STATUS_ENDPOINT_HANDLER}
"""
    
    try:
        ast.parse(test_code)
        print("✅ STATUS_ENDPOINT_HANDLER: Valid Python syntax")
    except SyntaxError as e:
        print(f"❌ STATUS_ENDPOINT_HANDLER: Syntax error at line {e.lineno}: {e.msg}")
        sys.exit(1)
    
    # Check DO_GET_ROUTE (elif clause - needs proper context)
    try:
        # elif needs if before it, wrap properly and dedent the route
        route_dedented = DO_GET_ROUTE.replace("        elif", "elif")
        route_test = f"if path == '/health':\n    pass\n{route_dedented}"
        ast.parse(route_test)
        print("✅ DO_GET_ROUTE: Valid Python syntax")
    except SyntaxError as e:
        print(f"❌ DO_GET_ROUTE: Syntax error: {e.msg}")
        sys.exit(1)
    
    # Check GLOBAL_VAR
    try:
        ast.parse(GLOBAL_VAR)
        print("✅ GLOBAL_VAR: Valid Python syntax")
    except SyntaxError as e:
        print(f"❌ GLOBAL_VAR: Syntax error: {e.msg}")
        sys.exit(1)
    
    print("\n✅ All patch components valid. Ready for deployment.")
    sys.exit(0)
