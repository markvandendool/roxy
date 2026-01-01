#!/usr/bin/env python3
"""
ROXY System Resource Monitor - Monitor CPU, memory, disk, network
"""
import logging
import psutil
from typing import Dict
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.system.resource_monitor')

class ResourceMonitor:
    """Monitor system resources"""
    
    def get_resources(self) -> Dict:
        """Get current resource usage"""
        return {
            'cpu': {
                'percent': psutil.cpu_percent(interval=1),
                'count': psutil.cpu_count(),
                'per_cpu': psutil.cpu_percent(interval=1, percpu=True)
            },
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'percent': psutil.virtual_memory().percent,
                'used': psutil.virtual_memory().used
            },
            'disk': {
                'total': psutil.disk_usage('/').total,
                'used': psutil.disk_usage('/').used,
                'free': psutil.disk_usage('/').free,
                'percent': psutil.disk_usage('/').percent
            },
            'network': {
                'bytes_sent': psutil.net_io_counters().bytes_sent,
                'bytes_recv': psutil.net_io_counters().bytes_recv,
                'packets_sent': psutil.net_io_counters().packets_sent,
                'packets_recv': psutil.net_io_counters().packets_recv
            },
            'timestamp': datetime.now().isoformat()
        }










