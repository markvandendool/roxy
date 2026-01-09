#!/usr/bin/env python3
"""
ROXY Backup Service - Automated backup system for ROXY state and memory
"""
import logging
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.backup')

class BackupService:
    """Automated backup service"""
    
    def __init__(self):
        self.backup_dir = Path('/home/mark/.roxy/backups/roxy')
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = 30
    
    def backup_memory_db(self) -> Path:
        """Backup memory database"""
        source = Path('/home/mark/.roxy/data/roxy_memory.db')
        if not source.exists():
            logger.warning("Memory database not found, skipping backup")
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f'roxy_memory_{timestamp}.db'
        
        try:
            shutil.copy2(source, backup_file)
            logger.info(f"✅ Memory database backed up to {backup_file}")
            return backup_file
        except Exception as e:
            logger.error(f"Failed to backup memory database: {e}")
            return None
    
    def backup_config(self) -> Path:
        """Backup configuration files"""
        config_dir = Path('/home/mark/.roxy/config')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = self.backup_dir / f'config_{timestamp}'
        
        try:
            if config_dir.exists():
                shutil.copytree(config_dir, backup_dir, dirs_exist_ok=True)
                logger.info(f"✅ Configuration backed up to {backup_dir}")
                return backup_dir
        except Exception as e:
            logger.error(f"Failed to backup configuration: {e}")
            return None
    
    def backup_all(self) -> Dict[str, Path]:
        """Backup all ROXY data"""
        results = {
            'memory_db': self.backup_memory_db(),
            'config': self.backup_config(),
        }
        return results
    
    def cleanup_old_backups(self):
        """Remove backups older than retention period"""
        import time
        cutoff_time = time.time() - (self.retention_days * 24 * 60 * 60)
        
        for backup_file in self.backup_dir.iterdir():
            if backup_file.stat().st_mtime < cutoff_time:
                try:
                    if backup_file.is_file():
                        backup_file.unlink()
                    else:
                        shutil.rmtree(backup_file)
                    logger.info(f"✅ Removed old backup: {backup_file}")
                except Exception as e:
                    logger.error(f"Failed to remove old backup {backup_file}: {e}")
    
    def list_backups(self) -> List[Dict]:
        """List all backups"""
        backups = []
        for backup_file in sorted(self.backup_dir.iterdir(), reverse=True):
            backups.append({
                'name': backup_file.name,
                'path': str(backup_file),
                'size': backup_file.stat().st_size if backup_file.is_file() else 0,
                'modified': datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat()
            })
        return backups

# Global backup service
_backup_service = None

def get_backup_service() -> BackupService:
    """Get or create global backup service"""
    global _backup_service
    if _backup_service is None:
        _backup_service = BackupService()
    return _backup_service










