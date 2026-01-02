#!/usr/bin/env python3
"""
ROXY Process Manager - Full control over system processes
"""
import logging
import subprocess
import psutil
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.system.process')

class ProcessManager:
    """Manage system processes"""
    
    def list_processes(self, filter_name: str = None) -> List[Dict]:
        """List all processes"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                info = proc.info
                if filter_name and filter_name.lower() not in info['name'].lower():
                    continue
                processes.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return processes
    
    def get_process_info(self, pid: int) -> Dict:
        """Get detailed process information"""
        try:
            proc = psutil.Process(pid)
            return {
                'pid': proc.pid,
                'name': proc.name(),
                'status': proc.status(),
                'cpu_percent': proc.cpu_percent(),
                'memory_percent': proc.memory_percent(),
                'memory_info': proc.memory_info()._asdict(),
                'num_threads': proc.num_threads(),
                'create_time': proc.create_time(),
                'cmdline': proc.cmdline(),
            }
        except psutil.NoSuchProcess:
            return {'error': 'Process not found'}
    
    def kill_process(self, pid: int, signal: int = 15) -> bool:
        """Kill a process"""
        try:
            proc = psutil.Process(pid)
            proc.send_signal(signal)
            return True
        except Exception as e:
            logger.error(f"Failed to kill process {pid}: {e}")
            return False
    
    def start_process(self, command: List[str], background: bool = False) -> Optional[int]:
        """Start a new process"""
        try:
            if background:
                proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return proc.pid
            else:
                result = subprocess.run(command, capture_output=True, text=True)
                return result.returncode
        except Exception as e:
            logger.error(f"Failed to start process: {e}")
            return None
    
    def get_system_resources(self) -> Dict:
        """Get system resource usage"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'cpu_count': psutil.cpu_count(),
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'percent': psutil.virtual_memory().percent,
                'used': psutil.virtual_memory().used,
            },
            'disk': {
                'total': psutil.disk_usage('/').total,
                'used': psutil.disk_usage('/').used,
                'free': psutil.disk_usage('/').free,
                'percent': psutil.disk_usage('/').percent,
            }
        }










