#!/usr/bin/env python3
"""
ROXY Package Manager - apt/snap package management
"""
import logging
import subprocess
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.system.package')

class PackageManager:
    """Manage system packages"""
    
    def list_installed_packages(self, package_name: str = None) -> List[Dict]:
        """List installed packages"""
        try:
            if package_name:
                result = subprocess.run(['dpkg', '-l', package_name],
                                      capture_output=True, text=True)
            else:
                result = subprocess.run(['dpkg', '-l'],
                                      capture_output=True, text=True)
            
            packages = []
            for line in result.stdout.split('\n')[5:]:  # Skip header
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3:
                        packages.append({
                            'status': parts[0],
                            'name': parts[1],
                            'version': parts[2],
                            'description': ' '.join(parts[4:]) if len(parts) > 4 else ''
                        })
            return packages
        except Exception as e:
            logger.error(f"Failed to list packages: {e}")
            return []
    
    def install_package(self, package_name: str) -> bool:
        """Install a package"""
        try:
            result = subprocess.run(['sudo', 'apt', 'install', '-y', package_name],
                                  capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to install package {package_name}: {e}")
            return False
    
    def update_packages(self) -> bool:
        """Update package list"""
        try:
            result = subprocess.run(['sudo', 'apt', 'update'],
                                  capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to update packages: {e}")
            return False
    
    def upgrade_packages(self) -> bool:
        """Upgrade all packages"""
        try:
            result = subprocess.run(['sudo', 'apt', 'upgrade', '-y'],
                                  capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to upgrade packages: {e}")
            return False










