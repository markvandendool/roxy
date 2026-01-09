#!/usr/bin/env python3
"""
ROXY Email Attachment Handler - Process email attachments
"""
import logging
import sys
from typing import List, Dict, Optional
from pathlib import Path

# Import standard library email module explicitly to avoid conflict with services/email/
import email.message as email_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.email.attachment')

class AttachmentHandler:
    """Handle email attachments"""
    
    def __init__(self, download_dir: str = '/home/mark/.roxy/data/email-attachments'):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_attachments(self, email_message_obj: email_message.Message) -> List[Dict]:
        """Extract attachments from email"""
        attachments = []
        
        if email_message_obj.is_multipart():
            for part in email_message_obj.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename:
                        filepath = self.download_dir / filename
                        with open(filepath, 'wb') as f:
                            f.write(part.get_payload(decode=True))
                        
                        attachments.append({
                            'filename': filename,
                            'path': str(filepath),
                            'size': filepath.stat().st_size,
                            'content_type': part.get_content_type()
                        })
        
        return attachments
    
    def process_attachment(self, filepath: str) -> Dict:
        """Process an attachment file"""
        path = Path(filepath)
        if not path.exists():
            return {'error': 'File not found'}
        
        info = {
            'filename': path.name,
            'size': path.stat().st_size,
            'extension': path.suffix,
            'content_type': self._guess_content_type(path)
        }
        
        # Try to extract text from common file types
        if path.suffix in ['.txt', '.md', '.py', '.js', '.json', '.yaml', '.yml']:
            try:
                info['preview'] = path.read_text()[:500]
            except:
                pass
        
        return info
    
    def _guess_content_type(self, path: Path) -> str:
        """Guess content type from extension"""
        content_types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.txt': 'text/plain',
            '.py': 'text/x-python',
        }
        return content_types.get(path.suffix.lower(), 'application/octet-stream')










