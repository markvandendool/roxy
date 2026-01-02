#!/usr/bin/env python3
"""
ROXY Business Automation MCP Server
Phase 7: Business Automation - Twenty CRM, Plane, Chatwoot
"""
import asyncio
import json
import logging
import os
from typing import Optional, Dict, List
from datetime import datetime
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP('roxy-business')

# Configuration
TWENTY_API_URL = os.getenv('TWENTY_API_URL', 'http://localhost:3000/api')
PLANE_API_URL = os.getenv('PLANE_API_URL', 'http://localhost:8000/api/v1')
CHATWOOT_API_URL = os.getenv('CHATWOOT_API_URL', 'http://localhost:3000/api/v1')
TWENTY_API_KEY = os.getenv('TWENTY_API_KEY', '')
PLANE_API_KEY = os.getenv('PLANE_API_KEY', '')
CHATWOOT_ACCESS_TOKEN = os.getenv('CHATWOOT_ACCESS_TOKEN', '')


@mcp.tool()
async def twenty_create_contact(
    first_name: str,
    last_name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None
) -> str:
    """
    Create a contact in Twenty CRM.
    
    Args:
        first_name: Contact first name
        last_name: Contact last name
        email: Contact email
        phone: Contact phone number
        company: Company name
    """
    try:
        import requests
        
        headers = {'Authorization': f'Bearer {TWENTY_API_KEY}'} if TWENTY_API_KEY else {}
        response = requests.post(
            f'{TWENTY_API_URL}/contacts',
            json={
                'firstName': first_name,
                'lastName': last_name,
                'email': email,
                'phone': phone,
                'company': company
            },
            headers=headers
        )
        
        if response.status_code in [200, 201]:
            return json.dumps({'status': 'created', 'contact': response.json()})
        return json.dumps({'error': f'Twenty API error: {response.text}'})
        
    except Exception as e:
        logger.error(f'Error creating Twenty contact: {e}')
        return json.dumps({'error': str(e)})


@mcp.tool()
async def plane_create_issue(
    project_id: str,
    name: str,
    description: Optional[str] = None,
    priority: str = 'medium',
    assignee_id: Optional[str] = None
) -> str:
    """
    Create an issue in Plane project management.
    
    Args:
        project_id: Plane project ID
        name: Issue name/title
        description: Issue description
        priority: Priority level (low, medium, high, urgent)
        assignee_id: Optional assignee user ID
    """
    try:
        import requests
        
        headers = {'Authorization': f'Bearer {PLANE_API_KEY}'} if PLANE_API_KEY else {}
        response = requests.post(
            f'{PLANE_API_URL}/projects/{project_id}/issues',
            json={
                'name': name,
                'description': description,
                'priority': priority,
                'assignee_id': assignee_id
            },
            headers=headers
        )
        
        if response.status_code in [200, 201]:
            return json.dumps({'status': 'created', 'issue': response.json()})
        return json.dumps({'error': f'Plane API error: {response.text}'})
        
    except Exception as e:
        logger.error(f'Error creating Plane issue: {e}')
        return json.dumps({'error': str(e)})


@mcp.tool()
async def chatwoot_send_message(
    account_id: str,
    conversation_id: str,
    message: str,
    message_type: str = 'outgoing'
) -> str:
    """
    Send a message via Chatwoot customer messaging.
    
    Args:
        account_id: Chatwoot account ID
        conversation_id: Conversation ID
        message: Message text
        message_type: Message type (incoming, outgoing)
    """
    try:
        import requests
        
        headers = {
            'api_access_token': CHATWOOT_ACCESS_TOKEN,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            f'{CHATWOOT_API_URL}/accounts/{account_id}/conversations/{conversation_id}/messages',
            json={
                'content': message,
                'message_type': message_type
            },
            headers=headers
        )
        
        if response.status_code in [200, 201]:
            return json.dumps({'status': 'sent', 'message': response.json()})
        return json.dumps({'error': f'Chatwoot API error: {response.text}'})
        
    except Exception as e:
        logger.error(f'Error sending Chatwoot message: {e}')
        return json.dumps({'error': str(e)})


@mcp.tool()
async def business_get_contacts(limit: int = 50) -> str:
    """Get contacts from Twenty CRM."""
    try:
        import requests
        headers = {'Authorization': f'Bearer {TWENTY_API_KEY}'} if TWENTY_API_KEY else {}
        response = requests.get(f'{TWENTY_API_URL}/contacts?limit={limit}', headers=headers)
        if response.status_code == 200:
            return json.dumps({'contacts': response.json()})
        return json.dumps({'error': f'Twenty API error: {response.text}'})
    except Exception as e:
        return json.dumps({'error': str(e)})


@mcp.tool()
async def business_get_issues(project_id: str, limit: int = 50) -> str:
    """Get issues from Plane project."""
    try:
        import requests
        headers = {'Authorization': f'Bearer {PLANE_API_KEY}'} if PLANE_API_KEY else {}
        response = requests.get(f'{PLANE_API_URL}/projects/{project_id}/issues?limit={limit}', headers=headers)
        if response.status_code == 200:
            return json.dumps({'issues': response.json()})
        return json.dumps({'error': f'Plane API error: {response.text}'})
    except Exception as e:
        return json.dumps({'error': str(e)})


if __name__ == '__main__':
    mcp.run()

