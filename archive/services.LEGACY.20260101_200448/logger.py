#!/usr/bin/env python3
"""
ROXY Structured Logger - Enhanced logging with correlation IDs
"""
import logging
import uuid
from typing import Optional
from datetime import datetime

class CorrelationFilter(logging.Filter):
    """Add correlation ID to log records"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        super().__init__()
        self.correlation_id = correlation_id or str(uuid.uuid4())
    
    def filter(self, record):
        record.correlation_id = self.correlation_id
        return True

def setup_roxy_logger(name: str = 'roxy', level: int = logging.INFO, 
                     correlation_id: Optional[str] = None) -> logging.Logger:
    """Setup structured logger for ROXY"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create formatter with correlation ID
    formatter = logging.Formatter(
        '%(asctime)s [%(name)s] [%(correlation_id)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(CorrelationFilter(correlation_id))
    logger.addHandler(console_handler)
    
    # File handler
    from pathlib import Path
    log_dir = Path('/home/mark/.roxy/logs')
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / 'roxy.log')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(CorrelationFilter(correlation_id))
    logger.addHandler(file_handler)
    
    return logger










