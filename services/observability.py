#!/usr/bin/env python3
"""
Observability - Request/response logging and performance tracking
"""
import logging
import time
import json
import threading
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger("roxy.observability")

ROXY_DIR = Path.home() / ".roxy"
OBSERVABILITY_DIR = ROXY_DIR / "logs" / "observability"
OBSERVABILITY_DIR.mkdir(parents=True, exist_ok=True)

# Log rotation settings
MAX_LOG_SIZE_MB = 100  # Rotate when log file exceeds 100MB
MAX_LOG_FILES = 7  # Keep last 7 days of logs


class RoxyObservability:
    """Lightweight observability for ROXY"""
    
    def __init__(self):
        self.request_log: List[Dict[str, Any]] = []
        self.max_log_size = 1000
        self._lock = threading.Lock()  # Thread-safe access to request_log
    
    def log_request(self, 
                   command: str,
                   response: str,
                   response_time: float,
                   metadata: Optional[Dict[str, Any]] = None,
                   request_id: Optional[str] = None,
                   endpoint: Optional[str] = None) -> None:
        """Log a request/response with thread safety and request ID"""
        if request_id is None:
            request_id = str(uuid.uuid4())[:8]
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "endpoint": endpoint or "unknown",
            "command": command[:200],
            "response_length": len(response),
            "response_time": round(response_time, 3),
            "metadata": metadata or {}
        }
        
        # Thread-safe append
        with self._lock:
            self.request_log.append(log_entry)
            
            # Keep only last N entries
            if len(self.request_log) > self.max_log_size:
                self.request_log = self.request_log[-self.max_log_size:]
        
        # Also log to file with rotation
        self._log_to_file(log_entry)
    
    def _log_to_file(self, log_entry: Dict[str, Any]) -> None:
        """Log to file with rotation and size limits"""
        try:
            log_file = OBSERVABILITY_DIR / f"requests_{datetime.now().strftime('%Y%m%d')}.jsonl"
            
            # Check file size and rotate if needed
            if log_file.exists():
                size_mb = log_file.stat().st_size / (1024 * 1024)
                if size_mb > MAX_LOG_SIZE_MB:
                    # Rotate: rename current file with timestamp
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    rotated_file = OBSERVABILITY_DIR / f"requests_{datetime.now().strftime('%Y%m%d')}_{timestamp}.jsonl"
                    log_file.rename(rotated_file)
                    logger.info(f"Rotated observability log: {rotated_file.name}")
            
            # Write log entry
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            # Cleanup old log files (keep only last N days)
            self._cleanup_old_logs()
        except Exception as e:
            logger.error(f"Failed to write observability log: {e}")
    
    def _cleanup_old_logs(self) -> None:
        """Remove log files older than MAX_LOG_FILES days"""
        try:
            import time
            cutoff_time = time.time() - (MAX_LOG_FILES * 24 * 60 * 60)
            
            for log_file in OBSERVABILITY_DIR.glob("requests_*.jsonl"):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    logger.debug(f"Removed old log file: {log_file.name}")
        except Exception as e:
            logger.warning(f"Failed to cleanup old logs: {e}")
    
    def log_error(self, command: str, error: str, error_type: Optional[str] = None) -> None:
        """Log an error"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command[:200],
            "error": str(error),
            "error_type": error_type or "unknown"
        }
        
        logger.error(f"Error: {command[:50]} - {error}")
        
        # Log to file
        try:
            log_file = OBSERVABILITY_DIR / f"errors_{datetime.now().strftime('%Y%m%d')}.jsonl"
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write error log: {e}")
    
    def get_latency_stats(self) -> Dict[str, float]:
        """Get latency statistics"""
        if not self.request_log:
            return {"avg": 0, "min": 0, "max": 0, "p95": 0}
        
        response_times = [entry["response_time"] for entry in self.request_log]
        response_times.sort()
        
        return {
            "avg": round(sum(response_times) / len(response_times), 3),
            "min": round(min(response_times), 3),
            "max": round(max(response_times), 3),
            "p95": round(response_times[int(len(response_times) * 0.95)], 3) if response_times else 0
        }
    
    def get_recent_requests(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent requests (thread-safe)"""
        with self._lock:
            return self.request_log[-limit:].copy()


# Global observability instance
_observability_instance = None


def get_observability() -> RoxyObservability:
    """Get global observability instance"""
    global _observability_instance
    if _observability_instance is None:
        _observability_instance = RoxyObservability()
    return _observability_instance









