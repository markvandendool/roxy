#!/usr/bin/env python3
"""
ROXY Service Health Agent - Monitor all system services
"""
import logging
import subprocess
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.system.service_health')

class ServiceHealth:
    """Monitor service health"""
    
    def check_all_services(self) -> Dict:
        """Check health of all ROXY services"""
        services = ['roxy.service', 'postgresql.service', 'redis.service', 'nats.service']
        health_status = {}
        
        for service in services:
            try:
                result = subprocess.run(['systemctl', 'is-active', service],
                                      capture_output=True, text=True)
                health_status[service] = {
                    'status': result.stdout.strip(),
                    'healthy': result.stdout.strip() == 'active'
                }
            except Exception as e:
                health_status[service] = {'error': str(e)}
        
        return {
            'services': health_status,
            'healthy_count': sum(1 for s in health_status.values() if s.get('healthy', False)),
            'total_count': len(services)
        }










