#!/usr/bin/env python3
"""
ROXY Disk Management Agent - Manage disk space and cleanup
"""
import logging
import shutil
from typing import Dict, List
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.system.disk_manager')

class DiskManager:
    """Manage disk space"""
    
    def get_disk_usage(self, path: str = '/') -> Dict:
        """Get disk usage"""
        import psutil
        usage = psutil.disk_usage(path)
        return {
            'total': usage.total,
            'used': usage.used,
            'free': usage.free,
            'percent': usage.percent
        }
    
    def cleanup_old_files(self, directory: str, days: int = 30) -> Dict:
        """Clean up old files"""
        from datetime import datetime, timedelta
        import os
        
        cutoff = datetime.now() - timedelta(days=days)
        cleaned = 0
        freed_space = 0
        
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = Path(root) / file
                    if file_path.stat().st_mtime < cutoff.timestamp():
                        size = file_path.stat().st_size
                        file_path.unlink()
                        cleaned += 1
                        freed_space += size
            
            return {
                'files_cleaned': cleaned,
                'space_freed': freed_space,
                'status': 'completed'
            }
        except Exception as e:
            return {'error': str(e)}










