#!/usr/bin/env python3
"""
ROXY Business Automation MCP Server
Phase 7: Business Automation - Supabase CRM, Plane, Chatwoot
Uses Supabase (same as mindsong-juke-hub CRM)
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

# Configuration - Supabase (same as mindsong-juke-hub)
SUPABASE_URL = os.getenv('SUPABASE_URL', os.getenv('VITE_SUPABASE_URL', 'https://rlbltiuswhlzjvszhvsc.supabase.co'))
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY', os.getenv('VITE_SUPABASE_ANON_KEY', ''))
PLANE_API_URL = os.getenv('PLANE_API_URL', 'http://localhost:8000/api/v1')
CHATWOOT_API_URL = os.getenv('CHATWOOT_API_URL', 'http://localhost:3000/api/v1')
PLANE_API_KEY = os.getenv('PLANE_API_KEY', '')
CHATWOOT_ACCESS_TOKEN = os.getenv('CHATWOOT_ACCESS_TOKEN', '')


@mcp.tool()
async def crm_create_contact(
    first_name: str,
    last_name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    stage: str = 'lead'
) -> str:
    """
    Create a contact in Supabase CRM (same as mindsong-juke-hub).
    
    Args:
        first_name: Contact first name
        last_name: Contact last name
        email: Contact email
        phone: Contact phone number
        company: Company name
        stage: Contact stage (subscriber, lead, marketing_qualified_lead, sales_qualified_lead, opportunity, customer)
    """
    try:
        from supabase import create_client, Client
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            return json.dumps({'error': 'Supabase credentials not configured'})
        
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        response = supabase.table('crm_contacts').insert({
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'company': company,
            'stage': stage
        }).execute()
        
        if response.data:
            return json.dumps({'status': 'created', 'contact': response.data[0]})
        return json.dumps({'error': 'Failed to create contact'})
        
    except ImportError:
        # Fallback to REST API if supabase-py not installed
        try:
            import requests
            headers = {
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            }
            response = requests.post(
                f'{SUPABASE_URL}/rest/v1/crm_contacts',
                json={
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone': phone,
                    'company': company,
                    'stage': stage
                },
                headers=headers
            )
            if response.status_code in [200, 201]:
                return json.dumps({'status': 'created', 'contact': response.json()[0] if isinstance(response.json(), list) else response.json()})
            return json.dumps({'error': f'Supabase API error: {response.text}'})
        except Exception as e:
            return json.dumps({'error': f'Error creating contact: {e}'})
    except Exception as e:
        logger.error(f'Error creating contact: {e}')
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
    """Get contacts from Supabase CRM (same as mindsong-juke-hub)."""
    try:
        from supabase import create_client, Client
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            return json.dumps({'error': 'Supabase credentials not configured'})
        
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        response = supabase.table('crm_contacts').select('*').limit(limit).order('created_at', desc=True).execute()
        
        if response.data:
            return json.dumps({'contacts': response.data})
        return json.dumps({'error': 'Failed to fetch contacts'})
        
    except ImportError:
        # Fallback to REST API
        try:
            import requests
            headers = {
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}'
            }
            response = requests.get(
                f'{SUPABASE_URL}/rest/v1/crm_contacts?limit={limit}&order=created_at.desc',
                headers=headers
            )
            if response.status_code == 200:
                return json.dumps({'contacts': response.json()})
            return json.dumps({'error': f'Supabase API error: {response.text}'})
        except Exception as e:
            return json.dumps({'error': str(e)})
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

