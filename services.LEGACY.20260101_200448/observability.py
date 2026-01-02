#!/usr/bin/env python3
"""
ROXY Observability - Performance monitoring and metrics
"""
import time
import logging
from typing import Dict, Any, Callable
from functools import wraps
from datetime import datetime
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.observability')

class MetricsCollector:
    """Collect performance metrics"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.counters = defaultdict(int)
        self.gauges = {}
    
    def record_timing(self, name: str, duration: float):
        """Record timing metric"""
        self.metrics[name].append({
            'value': duration,
            'timestamp': datetime.now().isoformat()
        })
        # Keep only last 1000 measurements
        if len(self.metrics[name]) > 1000:
            self.metrics[name] = self.metrics[name][-1000:]
    
    def increment_counter(self, name: str, value: int = 1):
        """Increment counter"""
        self.counters[name] += value
    
    def set_gauge(self, name: str, value: float):
        """Set gauge value"""
        self.gauges[name] = {
            'value': value,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        return {
            'timings': {k: {
                'count': len(v),
                'avg': sum(m['value'] for m in v) / len(v) if v else 0,
                'min': min(m['value'] for m in v) if v else 0,
                'max': max(m['value'] for m in v) if v else 0,
            } for k, v in self.metrics.items()},
            'counters': dict(self.counters),
            'gauges': self.gauges
        }

def timing_metric(name: str):
    """Decorator to record timing metrics"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                collector.record_timing(f"{name}.success", duration)
                return result
            except Exception as e:
                duration = time.time() - start
                collector.record_timing(f"{name}.error", duration)
                collector.increment_counter(f"{name}.errors")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                collector.record_timing(f"{name}.success", duration)
                return result
            except Exception as e:
                duration = time.time() - start
                collector.record_timing(f"{name}.error", duration)
                collector.increment_counter(f"{name}.errors")
                raise
        
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        return sync_wrapper
    return decorator

# Global metrics collector
_metrics_collector: MetricsCollector = None

def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector










