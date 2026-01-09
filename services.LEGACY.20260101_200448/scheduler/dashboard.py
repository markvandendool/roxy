#!/usr/bin/env python3
"""
ROXY Task Monitoring Dashboard - Visualize task execution
"""
import logging
from typing import Dict, List
from datetime import datetime
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.scheduler.dashboard')

class TaskDashboard:
    """Task execution dashboard"""
    
    def __init__(self, stats_file: str = '/home/mark/.roxy/data/task-stats.json'):
        self.stats_file = Path(stats_file)
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        self.stats = self._load_stats()
    
    def _load_stats(self) -> Dict:
        """Load task statistics"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load stats: {e}")
        return {}
    
    def _save_stats(self):
        """Save task statistics"""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save stats: {e}")
    
    def record_task_execution(self, task_id: str, success: bool, duration: float):
        """Record task execution"""
        if task_id not in self.stats:
            self.stats[task_id] = {
                'total_runs': 0,
                'successful_runs': 0,
                'failed_runs': 0,
                'total_duration': 0,
                'last_run': None
            }
        
        stats = self.stats[task_id]
        stats['total_runs'] += 1
        if success:
            stats['successful_runs'] += 1
        else:
            stats['failed_runs'] += 1
        
        stats['total_duration'] += duration
        stats['last_run'] = datetime.now().isoformat()
        stats['average_duration'] = stats['total_duration'] / stats['total_runs']
        stats['success_rate'] = stats['successful_runs'] / stats['total_runs'] if stats['total_runs'] > 0 else 0
        
        self._save_stats()
    
    def get_dashboard_data(self) -> Dict:
        """Get dashboard data"""
        total_tasks = len(self.stats)
        total_runs = sum(s['total_runs'] for s in self.stats.values())
        total_success = sum(s['successful_runs'] for s in self.stats.values())
        total_failures = sum(s['failed_runs'] for s in self.stats.values())
        
        return {
            'summary': {
                'total_tasks': total_tasks,
                'total_runs': total_runs,
                'successful_runs': total_success,
                'failed_runs': total_failures,
                'success_rate': total_success / total_runs if total_runs > 0 else 0
            },
            'tasks': self.stats
        }










