#!/usr/bin/env python3
"""
ROXY Task Templates - Reusable task templates
"""
import logging
from typing import Dict, List
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.scheduler.templates')

class TaskTemplate:
    """Task template definition"""
    
    def __init__(self, template_id: str, name: str, description: str,
                 cron_expr: str, handler: str, parameters: Dict = None):
        self.template_id = template_id
        self.name = name
        self.description = description
        self.cron_expr = cron_expr
        self.handler = handler
        self.parameters = parameters or {}
    
    def instantiate(self, task_id: str, **kwargs) -> Dict:
        """Create task instance from template"""
        # Merge template parameters with provided kwargs
        params = {**self.parameters, **kwargs}
        
        return {
            'task_id': task_id,
            'name': self.name,
            'cron_expr': self.cron_expr,
            'handler': self.handler,
            'parameters': params
        }

class TaskTemplates:
    """Manage task templates"""
    
    def __init__(self, templates_file: str = '/home/mark/.roxy/config/task-templates.json'):
        self.templates_file = Path(templates_file)
        self.templates_file.parent.mkdir(parents=True, exist_ok=True)
        self.templates: Dict[str, TaskTemplate] = {}
        self._load_templates()
        self._create_default_templates()
    
    def _load_templates(self):
        """Load templates from file"""
        if self.templates_file.exists():
            try:
                with open(self.templates_file, 'r') as f:
                    templates_data = json.load(f)
                    for template_data in templates_data:
                        template = TaskTemplate(**template_data)
                        self.templates[template.template_id] = template
            except Exception as e:
                logger.error(f"Failed to load templates: {e}")
    
    def _save_templates(self):
        """Save templates to file"""
        try:
            templates_data = [
                {
                    'template_id': t.template_id,
                    'name': t.name,
                    'description': t.description,
                    'cron_expr': t.cron_expr,
                    'handler': t.handler,
                    'parameters': t.parameters
                }
                for t in self.templates.values()
            ]
            with open(self.templates_file, 'w') as f:
                json.dump(templates_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save templates: {e}")
    
    def _create_default_templates(self):
        """Create default task templates"""
        if not self.templates:
            defaults = [
                TaskTemplate(
                    'backup-daily',
                    'Daily Backup',
                    'Backup ROXY data daily',
                    '0 2 * * *',  # 2 AM daily
                    'backup_service.get_backup_service().backup_all'
                ),
                TaskTemplate(
                    'health-check-hourly',
                    'Hourly Health Check',
                    'Check system health every hour',
                    '0 * * * *',
                    'health_monitor.HealthMonitor().check_all'
                ),
            ]
            for template in defaults:
                self.templates[template.template_id] = template
            self._save_templates()
    
    def add_template(self, template: TaskTemplate):
        """Add a new template"""
        self.templates[template.template_id] = template
        self._save_templates()
    
    def get_template(self, template_id: str) -> TaskTemplate:
        """Get a template"""
        return self.templates.get(template_id)
    
    def list_templates(self) -> List[Dict]:
        """List all templates"""
        return [
            {
                'template_id': t.template_id,
                'name': t.name,
                'description': t.description
            }
            for t in self.templates.values()
        ]










