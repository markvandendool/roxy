#!/usr/bin/env python3
"""
ROXY Automated System Updates - Manage system updates
"""
import logging
import subprocess
from typing import Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.system.update')

class UpdateManager:
    """Manage system updates"""
    
    def check_updates(self) -> Dict:
        """Check for available updates"""
        try:
            result = subprocess.run(['apt', 'list', '--upgradable'],
                                  capture_output=True, text=True)
            updates = [line for line in result.stdout.split('\n') if line and not line.startswith('Listing')]
            return {
                'updates_available': len(updates),
                'packages': updates[:10],  # First 10
                'status': 'completed'
            }
        except Exception as e:
            return {'error': str(e)}
    
    def update_packages(self, packages: list = None) -> Dict:
        """Update packages"""
        try:
            if packages:
                cmd = ['apt', 'install', '--upgrade', '-y'] + packages
            else:
                cmd = ['apt', 'upgrade', '-y']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            return {
                'returncode': result.returncode,
                'output': result.stdout[:1000],
                'status': 'completed' if result.returncode == 0 else 'failed'
            }
        except Exception as e:
            return {'error': str(e)}










