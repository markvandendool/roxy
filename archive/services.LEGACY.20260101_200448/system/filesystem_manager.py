#!/usr/bin/env python3
"""
ROXY File System Manager - Complete file system access and control
"""
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.system.filesystem')

class FileSystemManager:
    """Manage file system operations"""
    
    def read_file(self, path: str) -> Optional[str]:
        """Read file contents"""
        try:
            return Path(path).read_text()
        except Exception as e:
            logger.error(f"Failed to read file {path}: {e}")
            return None
    
    def write_file(self, path: str, content: str) -> bool:
        """Write file contents"""
        try:
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            return True
        except Exception as e:
            logger.error(f"Failed to write file {path}: {e}")
            return False
    
    def list_directory(self, path: str, recursive: bool = False) -> List[Dict]:
        """List directory contents"""
        try:
            dir_path = Path(path)
            if not dir_path.exists():
                return []
            
            items = []
            if recursive:
                for item in dir_path.rglob('*'):
                    items.append({
                        'path': str(item),
                        'name': item.name,
                        'type': 'directory' if item.is_dir() else 'file',
                        'size': item.stat().st_size if item.is_file() else 0,
                    })
            else:
                for item in dir_path.iterdir():
                    items.append({
                        'path': str(item),
                        'name': item.name,
                        'type': 'directory' if item.is_dir() else 'file',
                        'size': item.stat().st_size if item.is_file() else 0,
                    })
            return items
        except Exception as e:
            logger.error(f"Failed to list directory {path}: {e}")
            return []
    
    def create_directory(self, path: str) -> bool:
        """Create directory"""
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False
    
    def delete_file(self, path: str) -> bool:
        """Delete file or directory"""
        try:
            file_path = Path(path)
            if file_path.is_dir():
                shutil.rmtree(file_path)
            else:
                file_path.unlink()
            return True
        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}")
            return False
    
    def move_file(self, source: str, destination: str) -> bool:
        """Move or rename file"""
        try:
            shutil.move(source, destination)
            return True
        except Exception as e:
            logger.error(f"Failed to move {source} to {destination}: {e}")
            return False
    
    def get_file_info(self, path: str) -> Optional[Dict]:
        """Get file information"""
        try:
            file_path = Path(path)
            if not file_path.exists():
                return None
            
            stat = file_path.stat()
            return {
                'path': str(file_path),
                'name': file_path.name,
                'size': stat.st_size,
                'type': 'directory' if file_path.is_dir() else 'file',
                'modified': stat.st_mtime,
                'permissions': oct(stat.st_mode)[-3:],
            }
        except Exception as e:
            logger.error(f"Failed to get file info {path}: {e}")
            return None










