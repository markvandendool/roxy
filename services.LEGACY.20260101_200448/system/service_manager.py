#!/usr/bin/env python3
"""
ROXY Service Manager - Systemd service control and management
"""
import logging
import subprocess
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.system.service')

class ServiceManager:
    """Manage systemd services"""
    
    def list_services(self, state: str = None) -> List[Dict]:
        """List systemd services"""
        try:
            cmd = ['systemctl', 'list-units', '--type=service', '--no-pager', '--no-legend']
            if state:
                cmd.extend(['--state', state])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            services = []
            for line in result.stdout.split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 4:
                        services.append({
                            'name': parts[0],
                            'load': parts[1],
                            'active': parts[2],
                            'sub': parts[3],
                            'description': ' '.join(parts[4:]) if len(parts) > 4 else ''
                        })
            return services
        except Exception as e:
            logger.error(f"Failed to list services: {e}")
            return []
    
    def get_service_status(self, service_name: str) -> Dict:
        """Get service status"""
        try:
            result = subprocess.run(['systemctl', 'status', service_name, '--no-pager'],
                                  capture_output=True, text=True)
            return {
                'name': service_name,
                'status': 'active' if result.returncode == 0 else 'inactive',
                'output': result.stdout
            }
        except Exception as e:
            return {'name': service_name, 'error': str(e)}
    
    def start_service(self, service_name: str) -> bool:
        """Start a service"""
        try:
            result = subprocess.run(['sudo', 'systemctl', 'start', service_name],
                                  capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to start service {service_name}: {e}")
            return False
    
    def stop_service(self, service_name: str) -> bool:
        """Stop a service"""
        try:
            result = subprocess.run(['sudo', 'systemctl', 'stop', service_name],
                                  capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to stop service {service_name}: {e}")
            return False
    
    def restart_service(self, service_name: str) -> bool:
        """Restart a service"""
        try:
            result = subprocess.run(['sudo', 'systemctl', 'restart', service_name],
                                  capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to restart service {service_name}: {e}")
            return False










