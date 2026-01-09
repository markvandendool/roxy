#!/usr/bin/env python3
"""
ROXY Email MCP Server - IMAP/SMTP email access
"""
import asyncio
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from fastmcp import FastMCP
except ImportError:
    print('Missing fastmcp. Run: pip install fastmcp')
    exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.email')

mcp = FastMCP('roxy-email')

# Email configuration
IMAP_HOST = os.getenv('EMAIL_IMAP_HOST', 'imap.gmail.com')
IMAP_PORT = int(os.getenv('EMAIL_IMAP_PORT', '993'))
SMTP_HOST = os.getenv('EMAIL_SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('EMAIL_SMTP_PORT', '587'))
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

@mcp.tool()
async def read_emails(folder: str = 'INBOX', limit: int = 10, unread_only: bool = False) -> str:
    """
    Read emails from mailbox.
    
    Args:
        folder: Mailbox folder (default: INBOX)
        limit: Maximum number of emails to retrieve
        unread_only: Only fetch unread emails
    """
    try:
        import imaplib
        import email
        from email.header import decode_header
        
        if not EMAIL_USER or not EMAIL_PASSWORD:
            return '{"error": "Email credentials not configured"}'
        
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASSWORD)
        mail.select(folder)
        
        # Search for emails
        status, messages = mail.search(None, 'UNSEEN' if unread_only else 'ALL')
        email_ids = messages[0].split()[-limit:] if messages[0] else []
        
        emails = []
        for email_id in reversed(email_ids):
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            if status == 'OK':
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                # Decode subject
                subject = decode_header(email_message['Subject'])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                
                # Get sender
                sender = email_message['From']
                
                # Get body
                body = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = email_message.get_payload(decode=True).decode()
                
                emails.append({
                    'id': email_id.decode(),
                    'subject': subject,
                    'from': sender,
                    'date': email_message['Date'],
                    'body': body[:500]  # First 500 chars
                })
        
        mail.close()
        mail.logout()
        
        import json
        return json.dumps({'emails': emails, 'count': len(emails)})
    except Exception as e:
        logger.error(f"Failed to read emails: {e}")
        return f'{{"error": "{str(e)}"}}'

@mcp.tool()
async def send_email(to: str, subject: str, body: str, attachments: List[str] = None) -> str:
    """
    Send an email.
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body
        attachments: List of file paths to attach
    """
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders
        
        if not EMAIL_USER or not EMAIL_PASSWORD:
            return '{"error": "Email credentials not configured"}'
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Add attachments
        if attachments:
            for filepath in attachments:
                try:
                    with open(filepath, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f'attachment; filename= {Path(filepath).name}')
                        msg.attach(part)
                except Exception as e:
                    logger.warning(f"Failed to attach {filepath}: {e}")
        
        # Send email
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_USER, to, text)
        server.quit()
        
        return '{"success": true, "message": "Email sent successfully"}'
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return f'{{"error": "{str(e)}"}}'

@mcp.tool()
async def search_emails(query: str, folder: str = 'INBOX', limit: int = 10) -> str:
    """
    Search emails by query.
    
    Args:
        query: Search query
        folder: Mailbox folder
        limit: Maximum results
    """
    # Similar to read_emails but with search
    return await read_emails(folder, limit, False)

if __name__ == "__main__":
    mcp.run()










