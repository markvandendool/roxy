#!/usr/bin/env python3
"""
Evaluation Metrics - Simple metrics for ROXY performance
"""
import logging
import json
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger("roxy.evaluation.metrics")

ROXY_DIR = Path.home() / ".roxy"
METRICS_DIR = ROXY_DIR / "logs" / "metrics"
METRICS_DIR.mkdir(parents=True, exist_ok=True)


class MetricsCollector:
    """Collects evaluation metrics"""
    
    def __init__(self):
        self.metrics_file = METRICS_DIR / f"metrics_{datetime.now().strftime('%Y%m%d')}.json"
        self.metrics = self._load_metrics()
    
    def _load_metrics(self) -> List[Dict[str, Any]]:
        """Load existing metrics"""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load metrics: {e}")
        return []
    
    def _save_metrics(self):
        """Save metrics to file"""
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def record_query(self, 
                    query: str,
                    response: str,
                    response_time: float,
                    accuracy_score: float = None,
                    truthfulness_score: float = None,
                    source_attribution: bool = False):
        """Record a query and its metrics"""
        metric = {
            "timestamp": datetime.now().isoformat(),
            "query": query[:200],  # Truncate long queries
            "response_length": len(response),
            "response_time": round(response_time, 3),
            "accuracy_score": accuracy_score,
            "truthfulness_score": truthfulness_score,
            "has_source": source_attribution,
            "cache_hit": False  # Will be set by caller if cached
        }
        
        self.metrics.append(metric)
        
        # Keep only last 1000 metrics
        if len(self.metrics) > 1000:
            self.metrics = self.metrics[-1000:]
        
        self._save_metrics()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics from metrics"""
        if not self.metrics:
            return {
                "total_queries": 0,
                "avg_response_time": 0,
                "avg_accuracy": 0,
                "avg_truthfulness": 0,
                "cache_hit_rate": 0
            }
        
        total = len(self.metrics)
        response_times = [m.get("response_time", 0) for m in self.metrics if m.get("response_time")]
        accuracy_scores = [m.get("accuracy_score") for m in self.metrics if m.get("accuracy_score") is not None]
        truthfulness_scores = [m.get("truthfulness_score") for m in self.metrics if m.get("truthfulness_score") is not None]
        cache_hits = sum(1 for m in self.metrics if m.get("cache_hit", False))
        
        return {
            "total_queries": total,
            "avg_response_time": round(sum(response_times) / len(response_times), 3) if response_times else 0,
            "avg_accuracy": round(sum(accuracy_scores) / len(accuracy_scores), 2) if accuracy_scores else None,
            "avg_truthfulness": round(sum(truthfulness_scores) / len(truthfulness_scores), 2) if truthfulness_scores else None,
            "cache_hit_rate": round(cache_hits / total, 2) if total > 0 else 0,
            "source_attribution_rate": round(sum(1 for m in self.metrics if m.get("has_source", False)) / total, 2) if total > 0 else 0
        }
    
    def get_recent_metrics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent metrics"""
        return self.metrics[-limit:]


# Global metrics collector
_metrics_collector = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector















