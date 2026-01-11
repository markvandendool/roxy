#!/usr/bin/env python3
"""
Prometheus metrics for ROXY core
Provides request tracking, latency histograms, and error counters
"""
import time
import logging
from typing import Optional

logger = logging.getLogger("roxy.metrics")

try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        start_http_server,
        REGISTRY,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed. Metrics disabled.")


if PROMETHEUS_AVAILABLE:
    # Request metrics
    request_count = Counter(
        'roxy_requests_total',
        'Total number of requests',
        ['endpoint', 'status']
    )
    
    request_duration = Histogram(
        'roxy_request_duration_seconds',
        'Request duration in seconds',
        ['endpoint'],
        buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
    )
    
    active_requests = Gauge(
        'roxy_active_requests',
        'Number of currently active requests'
    )
    
    # RAG metrics
    rag_queries = Counter(
        'roxy_rag_queries_total',
        'Total RAG queries processed'
    )
    
    rag_latency = Histogram(
        'roxy_rag_latency_seconds',
        'RAG query latency',
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
    )
    
    # Cache metrics
    cache_hits = Counter(
        'roxy_cache_hits_total',
        'Total cache hits'
    )
    
    cache_misses = Counter(
        'roxy_cache_misses_total',
        'Total cache misses'
    )
    
    # LLM metrics
    ollama_calls = Counter(
        'roxy_ollama_calls_total',
        'Total Ollama API calls',
        ['model']
    )
    
    ollama_latency = Histogram(
        'roxy_ollama_latency_seconds',
        'Ollama API call latency',
        ['model'],
        buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
    )
    
    # Error metrics
    errors = Counter(
        'roxy_errors_total',
        'Total errors by type',
        ['error_type', 'endpoint']
    )
    
    # Security metrics
    blocked_commands = Counter(
        'roxy_blocked_commands_total',
        'Total blocked commands',
        ['pattern']
    )
    
    rate_limited = Counter(
        'roxy_rate_limited_total',
        'Total rate limited requests',
        ['endpoint']
    )

    # Pool metrics
    pool_reachable = Gauge(
        'roxy_pool_reachable',
        'Pool reachability (1=reachable, 0=unreachable)',
        ['pool']
    )

    pool_latency = Gauge(
        'roxy_pool_latency_ms',
        'Pool latency in milliseconds',
        ['pool']
    )

    bench_dry_runs = Counter(
        'roxy_bench_dry_runs_total',
        'Total benchmark dry run requests',
        ['pool']
    )

    ready_checks = Counter(
        'roxy_ready_checks_total',
        'Total /ready endpoint checks',
        ['status']  # ready, not_ready
    )


def init_prometheus(port: int = 9091):
    """Initialize Prometheus metrics server"""
    if not PROMETHEUS_AVAILABLE:
        logger.warning("Prometheus not available, skipping metrics server")
        return False
    
    try:
        start_http_server(port)
        logger.info(f"Prometheus metrics server started on port {port}")
        return True
    except OSError as e:
        if "Address already in use" in str(e):
            logger.warning(f"Metrics port {port} already in use, skipping")
        else:
            logger.error(f"Failed to start metrics server: {e}")
        return False


def export_metrics():
    """Return current Prometheus metrics exposition and content type"""
    if not PROMETHEUS_AVAILABLE:
        raise RuntimeError("prometheus_client not installed")

    try:
        data = generate_latest(REGISTRY)
        return data, CONTENT_TYPE_LATEST
    except Exception as exc:
        raise RuntimeError(f"failed to generate metrics: {exc}") from exc


class MetricsMiddleware:
    """Context manager for tracking request metrics"""
    
    def __init__(self, endpoint: str = "unknown"):
        self.endpoint = endpoint
        self.start_time: Optional[float] = None
        self.status = "unknown"
    
    def __enter__(self):
        if not PROMETHEUS_AVAILABLE:
            return self
        
        self.start_time = time.time()
        active_requests.inc()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if not PROMETHEUS_AVAILABLE:
            return
        
        # Record duration
        if self.start_time:
            duration = time.time() - self.start_time
            request_duration.labels(endpoint=self.endpoint).observe(duration)
        
        # Decrement active requests
        active_requests.dec()
        
        # Record error if present
        if exc_type:
            self.status = "error"
            errors.labels(
                error_type=exc_type.__name__,
                endpoint=self.endpoint
            ).inc()
        else:
            self.status = "success"
        
        # Record request count
        request_count.labels(
            endpoint=self.endpoint,
            status=self.status
        ).inc()
    
    def set_status(self, status: str):
        """Set status for the request"""
        self.status = status


def record_rag_query(latency: float):
    """Record a RAG query"""
    if PROMETHEUS_AVAILABLE:
        rag_queries.inc()
        rag_latency.observe(latency)


def record_cache_hit():
    """Record a cache hit"""
    if PROMETHEUS_AVAILABLE:
        cache_hits.inc()


def record_cache_miss():
    """Record a cache miss"""
    if PROMETHEUS_AVAILABLE:
        cache_misses.inc()


def record_ollama_call(model: str, latency: float):
    """Record an Ollama API call"""
    if PROMETHEUS_AVAILABLE:
        ollama_calls.labels(model=model).inc()
        ollama_latency.labels(model=model).observe(latency)


def record_blocked_command(pattern: str):
    """Record a blocked command"""
    if PROMETHEUS_AVAILABLE:
        blocked_commands.labels(pattern=pattern).inc()


def record_rate_limit(endpoint: str):
    """Record a rate limited request"""
    if PROMETHEUS_AVAILABLE:
        rate_limited.labels(endpoint=endpoint).inc()


def record_pool_status(pool: str, reachable: bool, latency_ms: Optional[float] = None):
    """Record pool reachability and latency"""
    if PROMETHEUS_AVAILABLE:
        pool_reachable.labels(pool=pool).set(1 if reachable else 0)
        if latency_ms is not None:
            pool_latency.labels(pool=pool).set(latency_ms)


def record_bench_dry_run(pool: str):
    """Record a benchmark dry run"""
    if PROMETHEUS_AVAILABLE:
        bench_dry_runs.labels(pool=pool).inc()


def record_ready_check(ready: bool):
    """Record a /ready endpoint check"""
    if PROMETHEUS_AVAILABLE:
        ready_checks.labels(status="ready" if ready else "not_ready").inc()


# Global availability flag
def is_available() -> bool:
    """Check if Prometheus metrics are available"""
    return PROMETHEUS_AVAILABLE
