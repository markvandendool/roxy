#!/usr/bin/env python3
"""
ROXY Email Thread Manager - Track email conversations
"""
import logging
# Import standard library email module explicitly to avoid conflict
import email as stdlib_email
from typing import Dict, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.email.thread')

class EmailThreadManager:
    """Manage email threads"""
    
    def __init__(self):
        self.threads = {}
    
    def get_thread_id(self, email_msg: Dict) -> Optional[str]:
        """Extract thread ID from email"""
        # Try to get thread ID from headers
        # For Gmail: X-GM-THRID
        # Standard: In-Reply-To or References
        thread_id = email_msg.get('thread_id') or email_msg.get('x-gm-thrid')
        if thread_id:
            return str(thread_id)
        
        # Generate thread ID from subject
        subject = email_msg.get('subject', '')
        if subject.startswith('Re:') or subject.startswith('Fwd:'):
            # Extract original subject
            original_subject = subject.replace('Re:', '').replace('Fwd:', '').strip()
            return f"thread_{hash(original_subject)}"
        
        return None
    
    def add_to_thread(self, email_msg: Dict):
        """Add email to thread"""
        thread_id = self.get_thread_id(email_msg)
        if not thread_id:
            thread_id = f"thread_{hash(email_msg.get('subject', ''))}"
        
        if thread_id not in self.threads:
            self.threads[thread_id] = []
        
        self.threads[thread_id].append({
            'id': email_msg.get('id'),
            'subject': email_msg.get('subject'),
            'from': email_msg.get('from'),
            'date': email_msg.get('date'),
            'body': email_msg.get('body', '')[:500]
        })
    
    def get_thread(self, thread_id: str) -> List[Dict]:
        """Get all emails in a thread"""
        return self.threads.get(thread_id, [])
    
    def list_threads(self) -> Dict[str, List[Dict]]:
        """List all threads"""
        return self.threads










