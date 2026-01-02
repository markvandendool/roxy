#!/usr/bin/env python3
"""
ROXY Network Manager - Network interface and connection control
"""
import logging
import socket
import subprocess
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.system.network')

class NetworkManager:
    """Manage network operations"""
    
    def get_interfaces(self) -> List[Dict]:
        """Get network interfaces"""
        try:
            result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)
            # Parse ip addr output (simplified)
            interfaces = []
            current_interface = None
            for line in result.stdout.split('\n'):
                if ':' in line and not line.strip().startswith('inet'):
                    if current_interface:
                        interfaces.append(current_interface)
                    parts = line.split(':')
                    if len(parts) >= 2:
                        current_interface = {
                            'name': parts[1].strip().split('@')[0],
                            'status': 'UP' if 'UP' in line else 'DOWN',
                            'addresses': []
                        }
                elif current_interface and 'inet ' in line:
                    addr = line.split('inet ')[1].split()[0]
                    current_interface['addresses'].append(addr)
            if current_interface:
                interfaces.append(current_interface)
            return interfaces
        except Exception as e:
            logger.error(f"Failed to get interfaces: {e}")
            return []
    
    def check_connectivity(self, host: str, port: int = None) -> bool:
        """Check network connectivity"""
        try:
            if port:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((host, port))
                sock.close()
                return result == 0
            else:
                # Ping check
                result = subprocess.run(['ping', '-c', '1', host], 
                                      capture_output=True, timeout=5)
                return result.returncode == 0
        except Exception as e:
            logger.error(f"Connectivity check failed: {e}")
            return False
    
    def get_network_stats(self) -> Dict:
        """Get network statistics"""
        try:
            import psutil
            stats = psutil.net_io_counters()
            return {
                'bytes_sent': stats.bytes_sent,
                'bytes_recv': stats.bytes_recv,
                'packets_sent': stats.packets_sent,
                'packets_recv': stats.packets_recv,
                'errin': stats.errin,
                'errout': stats.errout,
            }
        except Exception as e:
            logger.error(f"Failed to get network stats: {e}")
            return {}










