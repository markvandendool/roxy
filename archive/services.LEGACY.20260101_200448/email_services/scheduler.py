#!/usr/bin/env python3
"""
ROXY Email Scheduler - Schedule emails to send later
"""
import logging
from typing import Dict, List
from datetime import datetime, timedelta
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.email.scheduler')

class EmailScheduler:
    """Schedule emails for later sending"""
    
    def __init__(self, schedule_file: str = '/home/mark/.roxy/data/email-schedule.json'):
        self.schedule_file = Path(schedule_file)
        self.schedule_file.parent.mkdir(parents=True, exist_ok=True)
        self.scheduled_emails = self._load_schedule()
    
    def _load_schedule(self) -> List[Dict]:
        """Load scheduled emails"""
        if self.schedule_file.exists():
            try:
                with open(self.schedule_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load schedule: {e}")
        return []
    
    def _save_schedule(self):
        """Save scheduled emails"""
        try:
            with open(self.schedule_file, 'w') as f:
                json.dump(self.scheduled_emails, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save schedule: {e}")
    
    def schedule_email(self, to: str, subject: str, body: str,
                      send_at: datetime, attachments: List[str] = None) -> str:
        """Schedule an email to send later"""
        import uuid
        email_id = str(uuid.uuid4())
        
        scheduled = {
            'id': email_id,
            'to': to,
            'subject': subject,
            'body': body,
            'attachments': attachments or [],
            'send_at': send_at.isoformat(),
            'created_at': datetime.now().isoformat(),
            'sent': False
        }
        
        self.scheduled_emails.append(scheduled)
        self._save_schedule()
        
        logger.info(f"Scheduled email {email_id} to send at {send_at}")
        return email_id
    
    def get_due_emails(self) -> List[Dict]:
        """Get emails that are due to be sent"""
        now = datetime.now()
        due = []
        
        for email in self.scheduled_emails:
            if not email.get('sent', False):
                send_at = datetime.fromisoformat(email['send_at'])
                if send_at <= now:
                    due.append(email)
        
        return due
    
    def mark_sent(self, email_id: str):
        """Mark email as sent"""
        for email in self.scheduled_emails:
            if email['id'] == email_id:
                email['sent'] = True
                email['sent_at'] = datetime.now().isoformat()
                break
        self._save_schedule()










