#!/usr/bin/env python3
"""
ROXY System Configuration Agent - Manage system configuration
"""
import logging
from typing import Dict
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.system.config_agent')

class SystemConfigAgent:
    """Manage system configuration"""
    
    def get_system_config(self) -> Dict:
        """Get system configuration"""
        return {
            'hostname': Path('/etc/hostname').read_text().strip() if Path('/etc/hostname').exists() else 'unknown',
            'os': self._get_os_info(),
            'kernel': self._get_kernel_version()
        }
    
    def _get_os_info(self) -> str:
        """Get OS information"""
        try:
            import subprocess
            result = subprocess.run(['lsb_release', '-d'], capture_output=True, text=True)
            return result.stdout.split(':')[1].strip() if result.returncode == 0 else 'unknown'
        except:
            return 'unknown'
    
    def _get_kernel_version(self) -> str:
        """Get kernel version"""
        try:
            import subprocess
            result = subprocess.run(['uname', '-r'], capture_output=True, text=True)
            return result.stdout.strip()
        except:
            return 'unknown'










