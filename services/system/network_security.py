#!/usr/bin/env python3
"""
ROXY Network Security Agent - Monitor network security
"""
import logging
import subprocess
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.system.network_security')

class NetworkSecurity:
    """Monitor network security"""
    
    def check_connections(self) -> Dict:
        """Check network connections"""
        try:
            import psutil
            connections = psutil.net_connections()
            return {
                'total_connections': len(connections),
                'established': len([c for c in connections if c.status == 'ESTABLISHED']),
                'listening': len([c for c in connections if c.status == 'LISTEN'])
            }
        except Exception as e:
            return {'error': str(e)}
    
    def check_firewall(self) -> Dict:
        """Check firewall status"""
        try:
            result = subprocess.run(['ufw', 'status'], capture_output=True, text=True)
            return {
                'firewall_status': result.stdout,
                'active': 'Status: active' in result.stdout
            }
        except Exception as e:
            return {'error': str(e)}










